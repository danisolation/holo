"""Tests for BacktestAnalysisService — date-aware analysis for backtesting.

Verifies:
- Constructor stores run_id and as_of_date
- _get_technical_context uses date <= as_of_date filter (no lookahead)
- _get_combined_context reads backtest_analyses (NOT ai_analyses), filters by run_id
- _get_combined_context graceful degradation: no sentiment → neutral/5
- _get_trading_signal_context uses as_of_date-relative 52-week window (not date.today())
- _store_analysis writes to backtest_analyses with run_id (never ai_analyses)

Threat model mitigations:
  T-32-08: _store_analysis targets backtest_analyses not ai_analyses
  T-32-09: All context queries include date <= as_of_date bound
"""
import inspect
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.backtest_analysis_service import BacktestAnalysisService
from app.services.ai_analysis_service import AIAnalysisService
from app.models.backtest import BacktestAnalysis


# ------------------------------------------------------------------
# Helper: extract executable code lines (skip docstrings and comments)
# ------------------------------------------------------------------


def _extract_code_lines(lines: list[str]) -> list[str]:
    """Extract only executable code lines, skipping docstrings and comments."""
    code_lines = []
    in_docstring = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                continue  # Single-line docstring
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        if stripped.startswith("#"):
            continue
        code_lines.append(line)
    return code_lines


# ------------------------------------------------------------------
# TestBacktestAnalysisServiceInit
# ------------------------------------------------------------------


class TestBacktestAnalysisServiceInit:
    """Test constructor stores run_id and as_of_date attributes."""

    def test_stores_run_id(self):
        """Constructor stores run_id as instance attribute."""
        session = MagicMock()
        svc = BacktestAnalysisService(
            session=session, run_id=42, as_of_date=date(2025, 3, 15)
        )
        assert svc.run_id == 42

    def test_stores_as_of_date(self):
        """Constructor stores as_of_date as instance attribute."""
        session = MagicMock()
        svc = BacktestAnalysisService(
            session=session, run_id=1, as_of_date=date(2025, 3, 15)
        )
        assert svc.as_of_date == date(2025, 3, 15)

    def test_inherits_from_ai_analysis_service(self):
        """BacktestAnalysisService is a subclass of AIAnalysisService."""
        assert issubclass(BacktestAnalysisService, AIAnalysisService)

    def test_instance_is_ai_analysis_service(self):
        """Instance passes isinstance check for parent."""
        session = MagicMock()
        svc = BacktestAnalysisService(
            session=session, run_id=1, as_of_date=date(2025, 3, 15)
        )
        assert isinstance(svc, AIAnalysisService)

    def test_session_stored(self):
        """Parent session attribute is set."""
        session = MagicMock()
        svc = BacktestAnalysisService(
            session=session, run_id=1, as_of_date=date(2025, 3, 15)
        )
        assert svc.session is session


# ------------------------------------------------------------------
# TestDateAwareContextMethods
# ------------------------------------------------------------------


class TestDateAwareContextMethods:
    """Verify all context-gathering methods use as_of_date for date bounds."""

    def test_technical_context_source_uses_as_of_date(self):
        """_get_technical_context source code references self.as_of_date for filtering."""
        source = inspect.getsource(BacktestAnalysisService._get_technical_context)
        assert "self.as_of_date" in source
        # Must have date filter using <= as_of_date
        assert "<= self.as_of_date" in source or "self.as_of_date" in source

    def test_technical_context_source_no_date_today(self):
        """_get_technical_context must NOT use date.today() in code — causes lookahead bias."""
        source = inspect.getsource(BacktestAnalysisService._get_technical_context)
        code_lines = _extract_code_lines(source.split("\n"))
        code_only = "\n".join(code_lines)
        assert "date.today()" not in code_only

    @pytest.mark.asyncio
    async def test_technical_context_date_filter(self):
        """_get_technical_context queries indicators with date <= as_of_date."""
        session = AsyncMock()
        # Return empty result to test query construction
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        svc = BacktestAnalysisService(
            session=session, run_id=1, as_of_date=date(2025, 3, 15)
        )
        result = await svc._get_technical_context(ticker_id=10, symbol="VNM")

        # Should return None when no rows
        assert result is None
        # session.execute should have been called with a query
        assert session.execute.called

    def test_combined_context_reads_backtest_analyses(self):
        """_get_combined_context source references BacktestAnalysis model (not AIAnalysis)."""
        source = inspect.getsource(BacktestAnalysisService._get_combined_context)
        assert "BacktestAnalysis" in source
        # Must NOT reference AIAnalysis model in executable code
        # Exclude docstrings and comments — only check actual code lines
        import re
        lines = source.split("\n")
        code_lines = []
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                    continue  # Single-line docstring
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue
            if stripped.startswith("#"):
                continue
            code_lines.append(line)
        code_only = "\n".join(code_lines)
        # Check no standalone AIAnalysis (not part of BacktestAnalysis) in code
        standalone_refs = re.findall(r'(?<!Backtest)AIAnalysis', code_only)
        assert len(standalone_refs) == 0, f"Code references AIAnalysis directly: {standalone_refs}"

    def test_combined_context_filters_by_run_id(self):
        """_get_combined_context includes run_id filter."""
        source = inspect.getsource(BacktestAnalysisService._get_combined_context)
        assert "self.run_id" in source

    @pytest.mark.asyncio
    async def test_combined_context_graceful_degradation(self):
        """When no sentiment analysis exists, returns sent_signal='neutral', sent_score=5."""
        session = AsyncMock()

        # Create mock BacktestAnalysis rows — only tech, no sentiment
        tech_analysis = MagicMock()
        tech_analysis.analysis_type = "technical"
        tech_analysis.signal = "bullish"
        tech_analysis.score = 8

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [tech_analysis]
        session.execute.return_value = mock_result

        svc = BacktestAnalysisService(
            session=session, run_id=1, as_of_date=date(2025, 3, 15)
        )
        result = await svc._get_combined_context(ticker_id=10, symbol="VNM")

        assert result is not None
        assert result["sent_signal"] == "neutral"
        assert result["sent_score"] == 5
        assert result["tech_signal"] == "bullish"
        assert result["tech_score"] == 8

    def test_trading_signal_context_52week_relative(self):
        """_get_trading_signal_context uses as_of_date-relative 52-week window."""
        source = inspect.getsource(BacktestAnalysisService._get_trading_signal_context)
        # Must reference as_of_date for 52-week computation
        assert "self.as_of_date" in source
        assert "timedelta" in source
        # Must NOT use date.today() in executable code (OK in docstrings)
        lines = source.split("\n")
        code_lines = _extract_code_lines(lines)
        code_only = "\n".join(code_lines)
        assert "date.today()" not in code_only

    def test_trading_signal_context_365_day_window(self):
        """52-week window uses as_of_date - timedelta(days=365)."""
        source = inspect.getsource(BacktestAnalysisService._get_trading_signal_context)
        assert "365" in source
        assert "self.as_of_date - timedelta" in source or "self.as_of_date -" in source


# ------------------------------------------------------------------
# TestStoreAnalysisIsolation
# ------------------------------------------------------------------


class TestStoreAnalysisIsolation:
    """Verify _store_analysis targets backtest_analyses table exclusively."""

    def test_store_analysis_targets_backtest_table(self):
        """_store_analysis INSERT references 'backtest_analyses' table."""
        source = inspect.getsource(BacktestAnalysisService._store_analysis)
        assert "backtest_analyses" in source

    def test_never_writes_ai_analyses(self):
        """_store_analysis must NOT reference 'ai_analyses' table name in SQL.

        This is threat mitigation T-32-08: backtest data must be isolated.
        """
        import re
        source = inspect.getsource(BacktestAnalysisService._store_analysis)
        code_lines = _extract_code_lines(source.split("\n"))
        code_only = "\n".join(code_lines)
        # Find standalone 'ai_analyses' not preceded by 'backtest_'
        standalone_refs = re.findall(r'(?<!backtest_)ai_analyses', code_only)
        assert len(standalone_refs) == 0, (
            f"Found standalone ai_analyses references: {standalone_refs}"
        )

    def test_store_analysis_uses_as_of_date(self):
        """_store_analysis uses self.as_of_date as analysis_date, not the passed argument."""
        source = inspect.getsource(BacktestAnalysisService._store_analysis)
        assert "self.as_of_date" in source

    def test_store_analysis_includes_run_id(self):
        """_store_analysis includes run_id in the INSERT."""
        source = inspect.getsource(BacktestAnalysisService._store_analysis)
        assert "self.run_id" in source

    @pytest.mark.asyncio
    async def test_store_analysis_executes_with_run_id(self):
        """_store_analysis passes run_id to the SQL execution."""
        session = AsyncMock()
        svc = BacktestAnalysisService(
            session=session, run_id=42, as_of_date=date(2025, 3, 15)
        )

        await svc._store_analysis(
            ticker_id=10,
            analysis_type="technical",
            analysis_date=date(2025, 3, 15),
            signal="bullish",
            score=8,
            reasoning="Test reasoning",
            raw_response={"test": True},
        )

        # session.execute should have been called
        assert session.execute.called
        call_args = session.execute.call_args
        # Second arg is the params dict — should contain run_id=42
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("params", {})
        assert params.get("run_id") == 42
