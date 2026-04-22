"""Tests for backtest API schemas and endpoints.

Pure unit tests for Pydantic validation. No real DB needed.
"""
import pytest
from datetime import date, timedelta
from pydantic import ValidationError

from app.schemas.backtest import (
    BacktestStartRequest,
    BacktestRunResponse,
    BacktestTradeResponse,
    BacktestEquityResponse,
    BacktestTradeListResponse,
    BacktestEquityListResponse,
)


class TestBacktestStartRequest:
    """Validation tests for BacktestStartRequest schema."""

    def test_valid_request(self):
        req = BacktestStartRequest(
            start_date="2025-01-01",
            end_date="2025-04-01",
        )
        assert req.start_date == date(2025, 1, 1)
        assert req.end_date == date(2025, 4, 1)

    def test_defaults(self):
        """initial_capital=100_000_000, slippage_pct=0.5."""
        req = BacktestStartRequest(
            start_date="2025-01-01",
            end_date="2025-04-01",
        )
        assert req.initial_capital == 100_000_000
        assert req.slippage_pct == 0.5

    def test_start_date_must_be_before_end_date(self):
        with pytest.raises(ValidationError, match="start_date must be before end_date"):
            BacktestStartRequest(
                start_date="2025-06-01",
                end_date="2025-01-01",
            )

    def test_same_start_end_rejected(self):
        with pytest.raises(ValidationError, match="start_date must be before end_date"):
            BacktestStartRequest(
                start_date="2025-01-01",
                end_date="2025-01-01",
            )

    def test_rejects_date_range_over_6_months(self):
        """Date range > 180 days rejected."""
        with pytest.raises(ValidationError, match="6 months"):
            BacktestStartRequest(
                start_date="2025-01-01",
                end_date="2025-12-31",
            )

    def test_rejects_date_range_under_1_month(self):
        """Date range < 20 days rejected."""
        with pytest.raises(ValidationError, match="1 month"):
            BacktestStartRequest(
                start_date="2025-01-01",
                end_date="2025-01-10",
            )

    def test_exactly_20_days_accepted(self):
        """Minimum boundary: exactly 20 days is accepted."""
        start = date(2025, 1, 1)
        end = start + timedelta(days=20)
        req = BacktestStartRequest(start_date=str(start), end_date=str(end))
        assert req.start_date == start

    def test_exactly_180_days_accepted(self):
        """Maximum boundary: exactly 180 days is accepted."""
        start = date(2025, 1, 1)
        end = start + timedelta(days=180)
        req = BacktestStartRequest(start_date=str(start), end_date=str(end))
        assert req.end_date == end

    def test_slippage_pct_min_boundary(self):
        """slippage_pct >= 0.0."""
        req = BacktestStartRequest(
            start_date="2025-01-01", end_date="2025-04-01", slippage_pct=0.0,
        )
        assert req.slippage_pct == 0.0

    def test_slippage_pct_max_boundary(self):
        """slippage_pct <= 5.0."""
        req = BacktestStartRequest(
            start_date="2025-01-01", end_date="2025-04-01", slippage_pct=5.0,
        )
        assert req.slippage_pct == 5.0

    def test_slippage_pct_above_max_rejected(self):
        with pytest.raises(ValidationError):
            BacktestStartRequest(
                start_date="2025-01-01", end_date="2025-04-01", slippage_pct=5.1,
            )

    def test_slippage_pct_below_min_rejected(self):
        with pytest.raises(ValidationError):
            BacktestStartRequest(
                start_date="2025-01-01", end_date="2025-04-01", slippage_pct=-0.1,
            )

    def test_initial_capital_must_be_positive(self):
        with pytest.raises(ValidationError):
            BacktestStartRequest(
                start_date="2025-01-01", end_date="2025-04-01", initial_capital=0,
            )
        with pytest.raises(ValidationError):
            BacktestStartRequest(
                start_date="2025-01-01", end_date="2025-04-01", initial_capital=-1,
            )


class TestBacktestRunResponse:
    """Test response schema and progress computation."""

    def test_progress_pct_computed(self):
        resp = BacktestRunResponse(
            id=1, start_date="2025-01-01", end_date="2025-04-01",
            initial_capital=100_000_000, slippage_pct=0.5, status="running",
            last_completed_date=None, total_sessions=100, completed_sessions=50,
            is_cancelled=False, created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        assert resp.progress_pct == 50.0

    def test_progress_pct_zero_when_no_sessions(self):
        resp = BacktestRunResponse(
            id=1, start_date="2025-01-01", end_date="2025-04-01",
            initial_capital=100_000_000, slippage_pct=0.5, status="running",
            last_completed_date=None, total_sessions=0, completed_sessions=0,
            is_cancelled=False, created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        assert resp.progress_pct == 0.0

    def test_all_fields_present(self):
        resp = BacktestRunResponse(
            id=1, start_date="2025-01-01", end_date="2025-04-01",
            initial_capital=100_000_000, slippage_pct=0.5, status="completed",
            last_completed_date="2025-04-01", total_sessions=60, completed_sessions=60,
            is_cancelled=False, created_at="2025-01-01T00:00:00Z",
            updated_at="2025-04-01T00:00:00Z",
        )
        assert resp.id == 1
        assert resp.status == "completed"
        assert resp.last_completed_date == "2025-04-01"


class TestBacktestTradeResponse:
    def test_trade_response_fields(self):
        resp = BacktestTradeResponse(
            id=1, run_id=1, symbol="VNM", backtest_analysis_id=10,
            direction="long", status="active",
            entry_price=80000, stop_loss=75000,
            take_profit_1=85000, take_profit_2=90000,
            quantity=100, closed_quantity=0,
            signal_date="2025-01-02", confidence=8,
            timeframe="swing", position_size_pct=10,
            risk_reward_ratio=2.5, created_at="2025-01-02T00:00:00Z",
        )
        assert resp.run_id == 1
        assert resp.backtest_analysis_id == 10
        assert resp.symbol == "VNM"


class TestBacktestEquityResponse:
    def test_equity_response_fields(self):
        resp = BacktestEquityResponse(
            run_id=1, date="2025-01-02",
            cash=95_000_000, positions_value=5_000_000,
            total_equity=100_000_000,
            daily_return_pct=0.0, cumulative_return_pct=0.0,
        )
        assert resp.total_equity == 100_000_000
        assert resp.daily_return_pct == 0.0


class TestListResponses:
    def test_trade_list_response(self):
        resp = BacktestTradeListResponse(trades=[], total=0)
        assert resp.trades == []
        assert resp.total == 0

    def test_equity_list_response(self):
        resp = BacktestEquityListResponse(equity=[], total=0)
        assert resp.equity == []
        assert resp.total == 0
