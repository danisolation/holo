"""Tests for Phase 53 watchlist-gated AI pipeline (WL-01, WL-02).

Verifies that all Gemini-powered AI analysis and daily pick generation
runs only on watchlist tickers, and that empty watchlists skip gracefully.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _mock_job_svc():
    """Create a mock JobExecutionService for job function tests."""
    mock_svc = MagicMock()
    mock_execution = MagicMock()
    mock_execution.status = "running"
    mock_svc.start = AsyncMock(return_value=mock_execution)
    mock_svc.complete = AsyncMock()
    mock_svc.fail = AsyncMock()
    return mock_svc


def _mock_session_ctx():
    """Create mock async session context manager."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.execute = AsyncMock()

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_factory, mock_session


SAMPLE_TICKER_MAP = {"VNM": 1, "FPT": 2, "VCB": 3}


# ── Class 1: TestGetWatchlistTickerMap ───────────────────────────────────────


class TestGetWatchlistTickerMap:
    """Tests for _get_watchlist_ticker_map() helper function."""

    @pytest.mark.asyncio
    async def test_returns_symbol_to_id_map(self):
        """Should return {symbol: ticker_id} dict from JOIN query."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("VNM", 1), ("FPT", 2)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        from app.scheduler.jobs import _get_watchlist_ticker_map

        result = await _get_watchlist_ticker_map(mock_session)
        assert result == {"VNM": 1, "FPT": 2}

    @pytest.mark.asyncio
    async def test_empty_watchlist_returns_empty_dict(self):
        """Should return {} when watchlist has no matching tickers."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        from app.scheduler.jobs import _get_watchlist_ticker_map

        result = await _get_watchlist_ticker_map(mock_session)
        assert result == {}

    @pytest.mark.asyncio
    async def test_single_ticker_watchlist(self):
        """Should handle single-ticker watchlist correctly."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("HPG", 42)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        from app.scheduler.jobs import _get_watchlist_ticker_map

        result = await _get_watchlist_ticker_map(mock_session)
        assert result == {"HPG": 42}


# ── Class 2: TestAIAnalysisGating (WL-01) ───────────────────────────────────


class TestAIAnalysisGating:
    """WL-01: All 4 AI analysis jobs pass watchlist ticker_filter."""

    @pytest.mark.asyncio
    async def test_daily_ai_analysis_passes_ticker_filter(self):
        """daily_ai_analysis must pass ticker_filter from watchlist map."""
        mock_factory, mock_session = _mock_session_ctx()
        mock_job_svc = _mock_job_svc()

        with patch("app.scheduler.jobs.async_session", mock_factory), \
             patch("app.scheduler.jobs.JobExecutionService", return_value=mock_job_svc), \
             patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value=SAMPLE_TICKER_MAP), \
             patch("app.services.ai_analysis_service.AIAnalysisService") as MockAI:

            mock_service = AsyncMock()
            mock_service.analyze_all_tickers = AsyncMock(return_value={
                "technical": {"success": 3, "failed": 0, "failed_symbols": []},
                "fundamental": {"success": 3, "failed": 0, "failed_symbols": []},
            })
            MockAI.return_value = mock_service

            from app.scheduler.jobs import daily_ai_analysis
            await daily_ai_analysis()

            mock_service.analyze_all_tickers.assert_called_once_with(
                analysis_type="both", ticker_filter=SAMPLE_TICKER_MAP
            )

    @pytest.mark.asyncio
    async def test_daily_ai_analysis_skips_on_empty_watchlist(self):
        """daily_ai_analysis must skip with status='skipped' when watchlist empty."""
        mock_factory, mock_session = _mock_session_ctx()
        mock_job_svc = _mock_job_svc()

        with patch("app.scheduler.jobs.async_session", mock_factory), \
             patch("app.scheduler.jobs.JobExecutionService", return_value=mock_job_svc), \
             patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value={}):

            from app.scheduler.jobs import daily_ai_analysis
            await daily_ai_analysis()

            mock_job_svc.complete.assert_called_once()
            call_kwargs = mock_job_svc.complete.call_args
            assert call_kwargs[1]["status"] == "skipped"
            assert call_kwargs[1]["result_summary"]["reason"] == "empty_watchlist"

    @pytest.mark.asyncio
    async def test_daily_sentiment_analysis_passes_ticker_filter(self):
        """daily_sentiment_analysis must pass ticker_filter from watchlist map."""
        mock_factory, mock_session = _mock_session_ctx()
        mock_job_svc = _mock_job_svc()

        with patch("app.scheduler.jobs.async_session", mock_factory), \
             patch("app.scheduler.jobs.JobExecutionService", return_value=mock_job_svc), \
             patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value=SAMPLE_TICKER_MAP), \
             patch("app.services.ai_analysis_service.AIAnalysisService") as MockAI:

            mock_service = AsyncMock()
            mock_service.analyze_all_tickers = AsyncMock(return_value={
                "sentiment": {"success": 3, "failed": 0, "failed_symbols": []},
            })
            MockAI.return_value = mock_service

            from app.scheduler.jobs import daily_sentiment_analysis
            await daily_sentiment_analysis()

            mock_service.analyze_all_tickers.assert_called_once_with(
                analysis_type="sentiment", ticker_filter=SAMPLE_TICKER_MAP
            )

    @pytest.mark.asyncio
    async def test_daily_sentiment_analysis_skips_on_empty_watchlist(self):
        """daily_sentiment_analysis must skip when watchlist empty."""
        mock_factory, mock_session = _mock_session_ctx()
        mock_job_svc = _mock_job_svc()

        with patch("app.scheduler.jobs.async_session", mock_factory), \
             patch("app.scheduler.jobs.JobExecutionService", return_value=mock_job_svc), \
             patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value={}):

            from app.scheduler.jobs import daily_sentiment_analysis
            await daily_sentiment_analysis()

            mock_job_svc.complete.assert_called_once()
            call_kwargs = mock_job_svc.complete.call_args
            assert call_kwargs[1]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_daily_combined_analysis_passes_ticker_filter(self):
        """daily_combined_analysis must pass ticker_filter from watchlist map."""
        mock_factory, mock_session = _mock_session_ctx()
        mock_job_svc = _mock_job_svc()

        with patch("app.scheduler.jobs.async_session", mock_factory), \
             patch("app.scheduler.jobs.JobExecutionService", return_value=mock_job_svc), \
             patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value=SAMPLE_TICKER_MAP), \
             patch("app.services.ai_analysis_service.AIAnalysisService") as MockAI:

            mock_service = AsyncMock()
            mock_service.analyze_all_tickers = AsyncMock(return_value={
                "combined": {"success": 3, "failed": 0, "failed_symbols": []},
            })
            MockAI.return_value = mock_service

            from app.scheduler.jobs import daily_combined_analysis
            await daily_combined_analysis()

            mock_service.analyze_all_tickers.assert_called_once_with(
                analysis_type="combined", ticker_filter=SAMPLE_TICKER_MAP
            )

    @pytest.mark.asyncio
    async def test_daily_combined_analysis_skips_on_empty_watchlist(self):
        """daily_combined_analysis must skip when watchlist empty."""
        mock_factory, mock_session = _mock_session_ctx()
        mock_job_svc = _mock_job_svc()

        with patch("app.scheduler.jobs.async_session", mock_factory), \
             patch("app.scheduler.jobs.JobExecutionService", return_value=mock_job_svc), \
             patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value={}):

            from app.scheduler.jobs import daily_combined_analysis
            await daily_combined_analysis()

            mock_job_svc.complete.assert_called_once()
            call_kwargs = mock_job_svc.complete.call_args
            assert call_kwargs[1]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_daily_trading_signal_analysis_passes_ticker_filter(self):
        """daily_trading_signal_analysis must pass ticker_filter from watchlist map."""
        mock_factory, mock_session = _mock_session_ctx()
        mock_job_svc = _mock_job_svc()

        with patch("app.scheduler.jobs.async_session", mock_factory), \
             patch("app.scheduler.jobs.JobExecutionService", return_value=mock_job_svc), \
             patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value=SAMPLE_TICKER_MAP), \
             patch("app.services.ai_analysis_service.AIAnalysisService") as MockAI:

            mock_service = AsyncMock()
            mock_service.analyze_all_tickers = AsyncMock(return_value={
                "trading_signal": {"success": 3, "failed": 0, "failed_symbols": []},
            })
            MockAI.return_value = mock_service

            from app.scheduler.jobs import daily_trading_signal_analysis
            await daily_trading_signal_analysis()

            mock_service.analyze_all_tickers.assert_called_once_with(
                analysis_type="trading_signal", ticker_filter=SAMPLE_TICKER_MAP
            )

    @pytest.mark.asyncio
    async def test_daily_trading_signal_analysis_skips_on_empty_watchlist(self):
        """daily_trading_signal_analysis must skip when watchlist empty."""
        mock_factory, mock_session = _mock_session_ctx()
        mock_job_svc = _mock_job_svc()

        with patch("app.scheduler.jobs.async_session", mock_factory), \
             patch("app.scheduler.jobs.JobExecutionService", return_value=mock_job_svc), \
             patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value={}):

            from app.scheduler.jobs import daily_trading_signal_analysis
            await daily_trading_signal_analysis()

            mock_job_svc.complete.assert_called_once()
            call_kwargs = mock_job_svc.complete.call_args
            assert call_kwargs[1]["status"] == "skipped"


# ── Class 3: TestPickGenerationGating (WL-02) ───────────────────────────────


class TestPickGenerationGating:
    """WL-02: Pick generation passes watchlist symbols and skips on empty."""

    @pytest.mark.asyncio
    async def test_daily_pick_generation_passes_watchlist_symbols(self):
        """daily_pick_generation must pass watchlist_symbols set to PickService."""
        mock_factory, mock_session = _mock_session_ctx()
        mock_job_svc = _mock_job_svc()

        with patch("app.scheduler.jobs.async_session", mock_factory), \
             patch("app.scheduler.jobs.JobExecutionService", return_value=mock_job_svc), \
             patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value=SAMPLE_TICKER_MAP), \
             patch("app.services.pick_service.PickService") as MockPickSvc:

            mock_service = AsyncMock()
            mock_service.generate_daily_picks = AsyncMock(return_value={
                "picked": 3, "almost": 5, "date": "2025-07-18",
            })
            MockPickSvc.return_value = mock_service

            from app.scheduler.jobs import daily_pick_generation
            await daily_pick_generation()

            mock_service.generate_daily_picks.assert_called_once_with(
                watchlist_symbols=set(SAMPLE_TICKER_MAP.keys())
            )

    @pytest.mark.asyncio
    async def test_daily_pick_generation_skips_on_empty_watchlist(self):
        """daily_pick_generation must skip with status='skipped' when watchlist empty."""
        mock_factory, mock_session = _mock_session_ctx()
        mock_job_svc = _mock_job_svc()

        with patch("app.scheduler.jobs.async_session", mock_factory), \
             patch("app.scheduler.jobs.JobExecutionService", return_value=mock_job_svc), \
             patch("app.scheduler.jobs._get_watchlist_ticker_map", new_callable=AsyncMock, return_value={}):

            from app.scheduler.jobs import daily_pick_generation
            await daily_pick_generation()

            mock_job_svc.complete.assert_called_once()
            call_kwargs = mock_job_svc.complete.call_args
            assert call_kwargs[1]["status"] == "skipped"
            assert call_kwargs[1]["result_summary"]["reason"] == "empty_watchlist"
            assert call_kwargs[1]["result_summary"]["picked"] == 0


# ── Class 4: TestPickServiceWatchlistFilter ──────────────────────────────────


class TestPickServiceWatchlistFilter:
    """Tests for PickService.generate_daily_picks() watchlist_symbols parameter."""

    def test_generate_daily_picks_accepts_watchlist_symbols_param(self):
        """Method signature must accept watchlist_symbols: set[str] | None."""
        import inspect
        from app.services.pick_service import PickService

        sig = inspect.signature(PickService.generate_daily_picks)
        assert "watchlist_symbols" in sig.parameters
        param = sig.parameters["watchlist_symbols"]
        assert param.default is None

    def test_generate_daily_picks_default_is_none(self):
        """watchlist_symbols defaults to None for backward compatibility."""
        import inspect
        from app.services.pick_service import PickService

        sig = inspect.signature(PickService.generate_daily_picks)
        param = sig.parameters["watchlist_symbols"]
        assert param.default is None

    def test_broken_method_removed_from_ai_service(self):
        """analyze_watchlisted_tickers must not exist on AIAnalysisService."""
        from app.services.ai_analysis_service import AIAnalysisService
        assert not hasattr(AIAnalysisService, "analyze_watchlisted_tickers")
