"""Tests for BacktestAnalyticsService — Phase 33 analytics computations.

Pure unit tests with mocked AsyncSession. No real DB needed.
Validates: BENCH-01 (benchmark), BENCH-02 (metrics), BENCH-03 (sector),
BENCH-04 (confidence), BENCH-05 (timeframe).
"""

import math
import pytest
import pandas as pd
from decimal import Decimal
from datetime import date
from statistics import mean, stdev
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.backtest import (
    PerformanceSummaryResponse,
    BenchmarkComparisonResponse,
    BenchmarkPointResponse,
    SectorBreakdownResponse,
    ConfidenceBreakdownResponse,
    TimeframeBreakdownResponse,
    BacktestAnalyticsResponse,
)
from app.models.backtest import BacktestRun, BacktestEquity, BacktestStatus
from app.models.paper_trade import TradeStatus
from app.services.backtest_analytics_service import BacktestAnalyticsService


# ---------------------------------------------------------------------------
# Helpers — create reusable mock objects
# ---------------------------------------------------------------------------

def _mock_run(
    run_id: int = 1,
    status: BacktestStatus = BacktestStatus.COMPLETED,
    initial_capital: Decimal = Decimal("100000000"),
    start_date: date = date(2024, 1, 2),
    end_date: date = date(2024, 3, 29),
) -> MagicMock:
    """Return a MagicMock that behaves like a BacktestRun."""
    run = MagicMock(spec=BacktestRun)
    run.id = run_id
    run.status = status
    run.initial_capital = initial_capital
    run.start_date = start_date
    run.end_date = end_date
    return run


def _mock_row(**kwargs) -> MagicMock:
    """Create a MagicMock with given attributes set directly."""
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


# ===========================================================================
# Schema Validation Tests (pure Pydantic — no mocking)
# ===========================================================================


class TestAnalyticsSchemas:
    """Validate all Phase-33 response schemas with sample data."""

    def test_performance_summary_all_fields(self):
        resp = PerformanceSummaryResponse(
            total_trades=10, wins=6, losses=4, win_rate=60.0,
            total_pnl=5_000_000.0, total_pnl_pct=5.0,
            max_drawdown=-2_000_000.0, max_drawdown_pct=-2.0,
            sharpe_ratio=1.25, avg_pnl_per_trade=500_000.0,
        )
        assert resp.total_trades == 10
        assert resp.win_rate == 60.0
        assert resp.sharpe_ratio == 1.25

    def test_benchmark_comparison_with_none_vnindex(self):
        """VN-Index fields may be None when fetch fails."""
        resp = BenchmarkComparisonResponse(
            initial_capital=100_000_000.0,
            ai_total_return_pct=8.5,
            vnindex_total_return_pct=None,
            outperformance_pct=None,
            data=[],
        )
        assert resp.vnindex_total_return_pct is None
        assert resp.outperformance_pct is None

    def test_benchmark_point_vnindex_optional(self):
        pt = BenchmarkPointResponse(
            date="2024-01-02", ai_equity=100_000_000.0, ai_return_pct=0.0,
        )
        assert pt.vnindex_return_pct is None

    def test_sector_breakdown_validates(self):
        resp = SectorBreakdownResponse(
            sector="Ngân hàng", total_trades=5, wins=3,
            win_rate=60.0, total_pnl=1_500_000.0, avg_pnl=300_000.0,
        )
        assert resp.sector == "Ngân hàng"

    def test_confidence_breakdown_validates(self):
        resp = ConfidenceBreakdownResponse(
            bracket="HIGH (7-10)", total_trades=8, wins=6,
            win_rate=75.0, avg_pnl=400_000.0, avg_pnl_pct=3.2,
        )
        assert resp.bracket == "HIGH (7-10)"

    def test_timeframe_breakdown_validates(self):
        resp = TimeframeBreakdownResponse(
            bucket="SHORT (1-5d)", total_trades=12, wins=7,
            win_rate=58.33, avg_holding_days=3.2,
            total_pnl=2_100_000.0, avg_pnl=175_000.0,
        )
        assert resp.avg_holding_days == 3.2

    def test_analytics_response_composition(self):
        """BacktestAnalyticsResponse wraps all sub-schemas."""
        summary = PerformanceSummaryResponse(
            total_trades=5, wins=3, losses=2, win_rate=60.0,
            total_pnl=1_000_000.0, total_pnl_pct=1.0,
            max_drawdown=-500_000.0, max_drawdown_pct=-0.5,
            sharpe_ratio=0.8, avg_pnl_per_trade=200_000.0,
        )
        resp = BacktestAnalyticsResponse(
            run_id=1,
            summary=summary,
            sectors=[],
            confidence=[],
            timeframes=[],
        )
        assert resp.run_id == 1
        assert resp.summary.total_trades == 5
        assert resp.sectors == []


# ===========================================================================
# _get_run helper tests
# ===========================================================================


class TestGetRun:
    """Test the _get_run validation helper."""

    @pytest.mark.asyncio
    async def test_returns_completed_run(self, mock_db_session):
        """Returns run when found and status == COMPLETED."""
        run = _mock_run(status=BacktestStatus.COMPLETED)
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = run
        mock_db_session.execute.return_value = mock_result

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc._get_run(1)

        assert result is run

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self, mock_db_session):
        """Raises HTTPException 404 when run does not exist."""
        from fastapi import HTTPException

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db_session.execute.return_value = mock_result

        svc = BacktestAnalyticsService(mock_db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc._get_run(999)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_400_when_not_completed(self, mock_db_session):
        """Raises HTTPException 400 when run status is not COMPLETED."""
        from fastapi import HTTPException

        run = _mock_run(status=BacktestStatus.RUNNING)
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = run
        mock_db_session.execute.return_value = mock_result

        svc = BacktestAnalyticsService(mock_db_session)
        with pytest.raises(HTTPException) as exc_info:
            await svc._get_run(1)
        assert exc_info.value.status_code == 400


# ===========================================================================
# get_performance_summary tests (BENCH-02)
# ===========================================================================


class TestPerformanceSummary:
    """Test performance summary math: win rate, P&L, drawdown, Sharpe."""

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_win_rate_and_pnl(self, mock_get_run, mock_db_session):
        """3 wins / 5 total = 60%, correct P&L and avg."""
        mock_get_run.return_value = _mock_run(initial_capital=Decimal("100000000"))

        # Mock: trades aggregate (result.one())
        trade_row = _mock_row(total=5, wins=3, total_pnl=Decimal("500000"))
        trade_result = MagicMock()
        trade_result.one.return_value = trade_row

        # Mock: equity curve (result.all())
        equity_result = MagicMock()
        equity_result.all.return_value = [
            _mock_row(total_equity=Decimal("100000000")),
            _mock_row(total_equity=Decimal("100500000")),
        ]

        # Mock: daily returns (result.all())
        returns_result = MagicMock()
        returns_result.all.return_value = [
            _mock_row(daily_return_pct=0.5),
        ]

        mock_db_session.execute.side_effect = [trade_result, equity_result, returns_result]

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_performance_summary(1)

        assert result["total_trades"] == 5
        assert result["wins"] == 3
        assert result["losses"] == 2
        assert result["win_rate"] == 60.0
        assert result["total_pnl"] == 500000.0
        assert result["total_pnl_pct"] == 0.5  # 500k / 100M * 100
        assert result["avg_pnl_per_trade"] == 100000.0  # 500k / 5

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_max_drawdown_from_equity_curve(self, mock_get_run, mock_db_session):
        """Equity [100M, 110M, 95M, 105M] → drawdown = -15M, pct = -13.64%."""
        mock_get_run.return_value = _mock_run()

        trade_result = MagicMock()
        trade_result.one.return_value = _mock_row(total=2, wins=1, total_pnl=Decimal("5000000"))

        equity_result = MagicMock()
        equity_result.all.return_value = [
            _mock_row(total_equity=Decimal("100000000")),
            _mock_row(total_equity=Decimal("110000000")),
            _mock_row(total_equity=Decimal("95000000")),
            _mock_row(total_equity=Decimal("105000000")),
        ]

        returns_result = MagicMock()
        returns_result.all.return_value = []

        mock_db_session.execute.side_effect = [trade_result, equity_result, returns_result]

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_performance_summary(1)

        assert result["max_drawdown"] == -15_000_000.0
        assert result["max_drawdown_pct"] == -13.64

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_sharpe_ratio_known_returns(self, mock_get_run, mock_db_session):
        """Known daily returns → expected Sharpe = (mean/stdev)*sqrt(252)."""
        mock_get_run.return_value = _mock_run()

        daily_returns = [0.5, -0.2, 0.8, -0.1, 0.3]
        expected_mean = mean(daily_returns)
        expected_std = stdev(daily_returns)
        expected_sharpe = round((expected_mean / expected_std) * math.sqrt(252), 4)

        trade_result = MagicMock()
        trade_result.one.return_value = _mock_row(total=3, wins=2, total_pnl=Decimal("300000"))

        equity_result = MagicMock()
        equity_result.all.return_value = [
            _mock_row(total_equity=Decimal("100000000")),
        ]

        returns_result = MagicMock()
        returns_result.all.return_value = [
            _mock_row(daily_return_pct=r) for r in daily_returns
        ]

        mock_db_session.execute.side_effect = [trade_result, equity_result, returns_result]

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_performance_summary(1)

        assert result["sharpe_ratio"] == expected_sharpe  # 9.9232

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_zero_trades_no_division_error(self, mock_get_run, mock_db_session):
        """Zero closed trades → all zeros, no ZeroDivisionError."""
        mock_get_run.return_value = _mock_run()

        trade_result = MagicMock()
        trade_result.one.return_value = _mock_row(total=0, wins=0, total_pnl=None)

        equity_result = MagicMock()
        equity_result.all.return_value = []

        returns_result = MagicMock()
        returns_result.all.return_value = []

        mock_db_session.execute.side_effect = [trade_result, equity_result, returns_result]

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_performance_summary(1)

        assert result["total_trades"] == 0
        assert result["wins"] == 0
        assert result["losses"] == 0
        assert result["win_rate"] == 0.0
        assert result["total_pnl"] == 0.0
        assert result["total_pnl_pct"] == 0.0
        assert result["avg_pnl_per_trade"] == 0.0
        assert result["sharpe_ratio"] == 0.0
        assert result["max_drawdown"] == 0.0
        assert result["max_drawdown_pct"] == 0.0

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_flat_equity_no_drawdown(self, mock_get_run, mock_db_session):
        """Flat equity curve → max_drawdown = 0."""
        mock_get_run.return_value = _mock_run()

        trade_result = MagicMock()
        trade_result.one.return_value = _mock_row(total=1, wins=0, total_pnl=Decimal("0"))

        equity_result = MagicMock()
        equity_result.all.return_value = [
            _mock_row(total_equity=Decimal("100000000")),
            _mock_row(total_equity=Decimal("100000000")),
            _mock_row(total_equity=Decimal("100000000")),
        ]

        returns_result = MagicMock()
        returns_result.all.return_value = [
            _mock_row(daily_return_pct=0.0),
            _mock_row(daily_return_pct=0.0),
        ]

        mock_db_session.execute.side_effect = [trade_result, equity_result, returns_result]

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_performance_summary(1)

        assert result["max_drawdown"] == 0.0
        assert result["max_drawdown_pct"] == 0.0
        # stdev of [0, 0] = 0, so Sharpe should handle div-by-zero
        assert result["sharpe_ratio"] == 0.0


# ===========================================================================
# get_benchmark_comparison tests (BENCH-01)
# ===========================================================================


class TestBenchmarkComparison:
    """Test AI vs VN-Index benchmark comparison."""

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_aligned_ai_and_vnindex_curves(self, mock_get_run, mock_db_session):
        """Returns aligned AI equity + VN-Index curves with correct returns."""
        run = _mock_run(start_date=date(2024, 1, 2), end_date=date(2024, 1, 4))
        mock_get_run.return_value = run

        # AI equity curve with 3 data points
        equity_result = MagicMock()
        equity_result.all.return_value = [
            _mock_row(date=date(2024, 1, 2), total_equity=Decimal("100000000"), cumulative_return_pct=0.0),
            _mock_row(date=date(2024, 1, 3), total_equity=Decimal("102000000"), cumulative_return_pct=2.0),
            _mock_row(date=date(2024, 1, 4), total_equity=Decimal("103000000"), cumulative_return_pct=3.0),
        ]
        mock_db_session.execute.return_value = equity_result

        # VN-Index OHLCV data
        vnindex_df = pd.DataFrame({
            "time": [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)],
            "close": [1000.0, 1050.0, 1020.0],
        })

        mock_crawler = AsyncMock()
        mock_crawler.fetch_ohlcv = AsyncMock(return_value=vnindex_df)

        svc = BacktestAnalyticsService(mock_db_session, crawler=mock_crawler)
        result = await svc.get_benchmark_comparison(1)

        assert result["initial_capital"] == 100_000_000.0
        assert result["ai_total_return_pct"] == 3.0
        # VN-Index: (1020/1000 - 1)*100 = 2.0%
        assert result["vnindex_total_return_pct"] == 2.0
        # Outperformance: 3.0 - 2.0 = 1.0
        assert result["outperformance_pct"] == 1.0

        assert len(result["data"]) == 3
        # First point: vnindex_return = 0.0
        assert result["data"][0]["vnindex_return_pct"] == 0.0
        # Second point: (1050/1000-1)*100 = 5.0
        assert result["data"][1]["vnindex_return_pct"] == 5.0
        # Third point: (1020/1000-1)*100 = 2.0
        assert result["data"][2]["vnindex_return_pct"] == 2.0

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_vnindex_fetch_failure_graceful_fallback(self, mock_get_run, mock_db_session):
        """VN-Index fetch failure → returns data with vnindex_return_pct=None, no exception."""
        run = _mock_run(start_date=date(2024, 1, 2), end_date=date(2024, 1, 3))
        mock_get_run.return_value = run

        equity_result = MagicMock()
        equity_result.all.return_value = [
            _mock_row(date=date(2024, 1, 2), total_equity=Decimal("100000000"), cumulative_return_pct=0.0),
            _mock_row(date=date(2024, 1, 3), total_equity=Decimal("101000000"), cumulative_return_pct=1.0),
        ]
        mock_db_session.execute.return_value = equity_result

        # Crawler raises exception
        mock_crawler = AsyncMock()
        mock_crawler.fetch_ohlcv = AsyncMock(side_effect=Exception("Network error"))

        svc = BacktestAnalyticsService(mock_db_session, crawler=mock_crawler)
        result = await svc.get_benchmark_comparison(1)

        # Should NOT raise — graceful degradation
        assert result["ai_total_return_pct"] == 1.0
        assert result["vnindex_total_return_pct"] is None
        assert result["outperformance_pct"] is None
        # Data should still have AI equity points
        assert len(result["data"]) == 2
        assert result["data"][0]["vnindex_return_pct"] is None

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_empty_equity_curve(self, mock_get_run, mock_db_session):
        """Empty equity curve → empty data list, 0% returns."""
        mock_get_run.return_value = _mock_run()

        equity_result = MagicMock()
        equity_result.all.return_value = []
        mock_db_session.execute.return_value = equity_result

        mock_crawler = AsyncMock()
        mock_crawler.fetch_ohlcv = AsyncMock(return_value=pd.DataFrame())

        svc = BacktestAnalyticsService(mock_db_session, crawler=mock_crawler)
        result = await svc.get_benchmark_comparison(1)

        assert result["data"] == []
        assert result["ai_total_return_pct"] == 0.0

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_vnindex_buy_and_hold_return(self, mock_get_run, mock_db_session):
        """VN-Index buy-and-hold return: (last_close/first_close - 1) * 100."""
        run = _mock_run(start_date=date(2024, 1, 2), end_date=date(2024, 1, 5))
        mock_get_run.return_value = run

        equity_result = MagicMock()
        equity_result.all.return_value = [
            _mock_row(date=date(2024, 1, 2), total_equity=Decimal("100000000"), cumulative_return_pct=0.0),
            _mock_row(date=date(2024, 1, 3), total_equity=Decimal("105000000"), cumulative_return_pct=5.0),
            _mock_row(date=date(2024, 1, 4), total_equity=Decimal("108000000"), cumulative_return_pct=8.0),
            _mock_row(date=date(2024, 1, 5), total_equity=Decimal("110000000"), cumulative_return_pct=10.0),
        ]
        mock_db_session.execute.return_value = equity_result

        vnindex_df = pd.DataFrame({
            "time": [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)],
            "close": [1200.0, 1230.0, 1260.0, 1290.0],
        })

        mock_crawler = AsyncMock()
        mock_crawler.fetch_ohlcv = AsyncMock(return_value=vnindex_df)

        svc = BacktestAnalyticsService(mock_db_session, crawler=mock_crawler)
        result = await svc.get_benchmark_comparison(1)

        # VN-Index total return: (1290/1200 - 1)*100 = 7.5%
        assert result["vnindex_total_return_pct"] == 7.5
        # Outperformance: 10.0 - 7.5 = 2.5
        assert result["outperformance_pct"] == 2.5


# ===========================================================================
# get_sector_breakdown tests (BENCH-03)
# ===========================================================================


class TestSectorBreakdown:
    """Test per-sector grouping and metrics."""

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_groups_trades_by_industry(self, mock_get_run, mock_db_session):
        """Correct sector grouping with win rate and P&L."""
        mock_get_run.return_value = _mock_run()

        result_mock = MagicMock()
        result_mock.all.return_value = [
            _mock_row(sector="Ngân hàng", total=10, wins=7, total_pnl=Decimal("2000000"), avg_pnl=Decimal("200000")),
            _mock_row(sector="Bất động sản", total=5, wins=2, total_pnl=Decimal("-500000"), avg_pnl=Decimal("-100000")),
        ]
        mock_db_session.execute.return_value = result_mock

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_sector_breakdown(1)

        assert len(result) == 2
        assert result[0]["sector"] == "Ngân hàng"
        assert result[0]["total_trades"] == 10
        assert result[0]["wins"] == 7
        assert result[0]["win_rate"] == 70.0
        assert result[0]["total_pnl"] == 2_000_000.0
        assert result[0]["avg_pnl"] == 200_000.0

        assert result[1]["sector"] == "Bất động sản"
        assert result[1]["win_rate"] == 40.0

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_null_industry_becomes_unknown(self, mock_get_run, mock_db_session):
        """NULL industry → coalesced to 'Unknown' label."""
        mock_get_run.return_value = _mock_run()

        result_mock = MagicMock()
        result_mock.all.return_value = [
            _mock_row(sector="Unknown", total=3, wins=1, total_pnl=Decimal("100000"), avg_pnl=Decimal("33333")),
        ]
        mock_db_session.execute.return_value = result_mock

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_sector_breakdown(1)

        assert len(result) == 1
        assert result[0]["sector"] == "Unknown"
        assert result[0]["total_trades"] == 3

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_sector_win_rate_per_sector(self, mock_get_run, mock_db_session):
        """Each sector has independent win rate calculation."""
        mock_get_run.return_value = _mock_run()

        result_mock = MagicMock()
        result_mock.all.return_value = [
            _mock_row(sector="Công nghệ", total=4, wins=4, total_pnl=Decimal("800000"), avg_pnl=Decimal("200000")),
            _mock_row(sector="Thép", total=6, wins=0, total_pnl=Decimal("-600000"), avg_pnl=Decimal("-100000")),
        ]
        mock_db_session.execute.return_value = result_mock

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_sector_breakdown(1)

        # 100% win rate for tech
        assert result[0]["win_rate"] == 100.0
        # 0% win rate for steel
        assert result[1]["win_rate"] == 0.0


# ===========================================================================
# get_confidence_breakdown tests (BENCH-04)
# ===========================================================================


class TestConfidenceBreakdown:
    """Test confidence bucket grouping: LOW (1-3), MEDIUM (4-6), HIGH (7-10)."""

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_three_confidence_buckets(self, mock_get_run, mock_db_session):
        """All three confidence buckets present with correct labels."""
        mock_get_run.return_value = _mock_run()

        result_mock = MagicMock()
        result_mock.all.return_value = [
            _mock_row(bracket="LOW (1-3)", total=5, wins=1, avg_pnl=Decimal("-50000"), avg_pnl_pct=-1.5),
            _mock_row(bracket="MEDIUM (4-6)", total=8, wins=4, avg_pnl=Decimal("100000"), avg_pnl_pct=2.0),
            _mock_row(bracket="HIGH (7-10)", total=10, wins=8, avg_pnl=Decimal("300000"), avg_pnl_pct=4.5),
        ]
        mock_db_session.execute.return_value = result_mock

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_confidence_breakdown(1)

        assert len(result) == 3
        assert result[0]["bracket"] == "LOW (1-3)"
        assert result[0]["win_rate"] == 20.0  # 1/5*100
        assert result[1]["bracket"] == "MEDIUM (4-6)"
        assert result[1]["win_rate"] == 50.0
        assert result[2]["bracket"] == "HIGH (7-10)"
        assert result[2]["win_rate"] == 80.0

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_confidence_avg_pnl_and_pct(self, mock_get_run, mock_db_session):
        """Per-bucket avg_pnl and avg_pnl_pct are correctly passed through."""
        mock_get_run.return_value = _mock_run()

        result_mock = MagicMock()
        result_mock.all.return_value = [
            _mock_row(bracket="HIGH (7-10)", total=4, wins=3, avg_pnl=Decimal("450000"), avg_pnl_pct=5.2),
        ]
        mock_db_session.execute.return_value = result_mock

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_confidence_breakdown(1)

        assert result[0]["avg_pnl"] == 450_000.0
        assert result[0]["avg_pnl_pct"] == 5.2

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_confidence_zero_wins_no_error(self, mock_get_run, mock_db_session):
        """Bucket with zero wins → win_rate = 0.0, no division error."""
        mock_get_run.return_value = _mock_run()

        result_mock = MagicMock()
        result_mock.all.return_value = [
            _mock_row(bracket="LOW (1-3)", total=3, wins=0, avg_pnl=Decimal("-200000"), avg_pnl_pct=-3.0),
        ]
        mock_db_session.execute.return_value = result_mock

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_confidence_breakdown(1)

        assert result[0]["wins"] == 0
        assert result[0]["win_rate"] == 0.0


# ===========================================================================
# get_timeframe_breakdown tests (BENCH-05)
# ===========================================================================


class TestTimeframeBreakdown:
    """Test timeframe bucket grouping: SHORT (1-5d), MEDIUM (6-15d), LONG (16+d)."""

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_three_timeframe_buckets(self, mock_get_run, mock_db_session):
        """All three timeframe buckets present with correct labels."""
        mock_get_run.return_value = _mock_run()

        result_mock = MagicMock()
        result_mock.all.return_value = [
            _mock_row(bucket="SHORT (1-5d)", total=6, wins=4, avg_holding_days=3.2,
                       total_pnl=Decimal("600000"), avg_pnl=Decimal("100000")),
            _mock_row(bucket="MEDIUM (6-15d)", total=8, wins=5, avg_holding_days=10.5,
                       total_pnl=Decimal("1200000"), avg_pnl=Decimal("150000")),
            _mock_row(bucket="LONG (16+d)", total=4, wins=2, avg_holding_days=22.0,
                       total_pnl=Decimal("400000"), avg_pnl=Decimal("100000")),
        ]
        mock_db_session.execute.return_value = result_mock

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_timeframe_breakdown(1)

        assert len(result) == 3
        assert result[0]["bucket"] == "SHORT (1-5d)"
        assert result[0]["avg_holding_days"] == 3.2
        assert result[0]["win_rate"] == pytest.approx(66.67)
        assert result[1]["bucket"] == "MEDIUM (6-15d)"
        assert result[1]["avg_holding_days"] == 10.5
        assert result[2]["bucket"] == "LONG (16+d)"
        assert result[2]["avg_holding_days"] == 22.0

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_timeframe_pnl_totals(self, mock_get_run, mock_db_session):
        """Per-bucket total_pnl and avg_pnl are correctly computed."""
        mock_get_run.return_value = _mock_run()

        result_mock = MagicMock()
        result_mock.all.return_value = [
            _mock_row(bucket="SHORT (1-5d)", total=3, wins=2, avg_holding_days=2.0,
                       total_pnl=Decimal("900000"), avg_pnl=Decimal("300000")),
        ]
        mock_db_session.execute.return_value = result_mock

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_timeframe_breakdown(1)

        assert result[0]["total_pnl"] == 900_000.0
        assert result[0]["avg_pnl"] == 300_000.0
        assert result[0]["total_trades"] == 3

    @pytest.mark.asyncio
    @patch.object(BacktestAnalyticsService, "_get_run", new_callable=AsyncMock)
    async def test_timeframe_zero_wins_handling(self, mock_get_run, mock_db_session):
        """Bucket with zero wins → win_rate = 0.0, negative P&L."""
        mock_get_run.return_value = _mock_run()

        result_mock = MagicMock()
        result_mock.all.return_value = [
            _mock_row(bucket="LONG (16+d)", total=5, wins=0, avg_holding_days=25.0,
                       total_pnl=Decimal("-1500000"), avg_pnl=Decimal("-300000")),
        ]
        mock_db_session.execute.return_value = result_mock

        svc = BacktestAnalyticsService(mock_db_session)
        result = await svc.get_timeframe_breakdown(1)

        assert result[0]["wins"] == 0
        assert result[0]["win_rate"] == 0.0
        assert result[0]["total_pnl"] == -1_500_000.0
        assert result[0]["avg_pnl"] == -300_000.0
