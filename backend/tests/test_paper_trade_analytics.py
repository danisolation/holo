"""Tests for paper trade analytics computation.

Tests the drawdown algorithm and analytics response schemas.
No DB — pure function tests + schema validation.
"""
import pytest
from app.schemas.paper_trading import (
    AnalyticsSummaryResponse,
    EquityCurvePoint,
    EquityCurveResponse,
    DrawdownResponse,
    DrawdownPeriod,
)


class TestDrawdownComputation:
    """AN-04: Max drawdown algorithm (pure Python — no DB)."""

    def _compute_drawdown(self, curve_data: list[dict], initial_capital: float = 100000000) -> dict:
        """Replicate the drawdown computation from service for testing."""
        if not curve_data:
            return {"max_drawdown_vnd": 0, "max_drawdown_pct": 0, "current_drawdown_vnd": 0, "current_drawdown_pct": 0, "periods": []}

        peak = 0.0
        max_dd_vnd = 0.0
        max_dd_pct = 0.0

        for point in curve_data:
            value = point["cumulative_pnl"]
            if value > peak:
                peak = value
            else:
                dd = value - peak
                if dd < max_dd_vnd:
                    max_dd_vnd = dd
                    equity_at_peak = initial_capital + peak
                    max_dd_pct = round(dd / equity_at_peak * 100, 2) if equity_at_peak > 0 else 0.0

        current = curve_data[-1]["cumulative_pnl"]
        current_dd = current - peak
        return {
            "max_drawdown_vnd": round(max_dd_vnd, 2),
            "max_drawdown_pct": max_dd_pct,
            "current_drawdown_vnd": round(current_dd, 2) if current_dd < 0 else 0,
            "current_drawdown_pct": 0,
            "periods": [],
        }

    def test_no_drawdown_on_all_gains(self):
        curve = [
            {"date": "2025-01-01", "daily_pnl": 100000, "cumulative_pnl": 100000},
            {"date": "2025-01-02", "daily_pnl": 200000, "cumulative_pnl": 300000},
            {"date": "2025-01-03", "daily_pnl": 150000, "cumulative_pnl": 450000},
        ]
        result = self._compute_drawdown(curve)
        assert result["max_drawdown_vnd"] == 0
        assert result["current_drawdown_vnd"] == 0

    def test_single_drawdown(self):
        curve = [
            {"date": "2025-01-01", "daily_pnl": 500000, "cumulative_pnl": 500000},
            {"date": "2025-01-02", "daily_pnl": -300000, "cumulative_pnl": 200000},
            {"date": "2025-01-03", "daily_pnl": 400000, "cumulative_pnl": 600000},
        ]
        result = self._compute_drawdown(curve)
        assert result["max_drawdown_vnd"] == -300000  # 500K peak → 200K trough

    def test_deeper_second_drawdown(self):
        curve = [
            {"date": "2025-01-01", "daily_pnl": 1000000, "cumulative_pnl": 1000000},
            {"date": "2025-01-02", "daily_pnl": -200000, "cumulative_pnl": 800000},
            {"date": "2025-01-03", "daily_pnl": 500000, "cumulative_pnl": 1300000},
            {"date": "2025-01-04", "daily_pnl": -800000, "cumulative_pnl": 500000},
        ]
        result = self._compute_drawdown(curve)
        assert result["max_drawdown_vnd"] == -800000  # 1.3M peak → 500K trough
        assert result["current_drawdown_vnd"] == -800000

    def test_empty_curve(self):
        result = self._compute_drawdown([])
        assert result["max_drawdown_vnd"] == 0
        assert result["max_drawdown_pct"] == 0

    def test_all_losses(self):
        curve = [
            {"date": "2025-01-01", "daily_pnl": -100000, "cumulative_pnl": -100000},
            {"date": "2025-01-02", "daily_pnl": -200000, "cumulative_pnl": -300000},
        ]
        result = self._compute_drawdown(curve)
        # Peak stays at 0, max drawdown is -300000
        assert result["max_drawdown_vnd"] == -300000


class TestAnalyticsSummarySchema:
    """AN-01, AN-02: Summary response validation."""

    def test_valid_summary(self):
        summary = AnalyticsSummaryResponse(
            total_trades=10, wins=6, losses=4,
            win_rate=60.0, total_pnl=5000000,
            total_pnl_pct=5.0, avg_pnl_per_trade=500000,
        )
        assert summary.win_rate == 60.0
        assert summary.total_pnl_pct == 5.0

    def test_zero_trades(self):
        summary = AnalyticsSummaryResponse(
            total_trades=0, wins=0, losses=0,
            win_rate=0, total_pnl=0,
            total_pnl_pct=0, avg_pnl_per_trade=0,
        )
        assert summary.total_trades == 0


class TestEquityCurveSchema:
    """AN-03: Equity curve point validation."""

    def test_valid_point(self):
        point = EquityCurvePoint(
            date="2025-01-15", daily_pnl=500000, cumulative_pnl=1200000,
        )
        assert point.date == "2025-01-15"
        assert point.cumulative_pnl == 1200000


class TestDrawdownSchema:
    """AN-04: Drawdown response validation."""

    def test_valid_drawdown(self):
        dd = DrawdownResponse(
            max_drawdown_vnd=-500000, max_drawdown_pct=-0.5,
            current_drawdown_vnd=-200000, current_drawdown_pct=-0.2,
            periods=[DrawdownPeriod(start="2025-01-10", end="2025-01-15", drawdown_vnd=-500000)],
        )
        assert dd.max_drawdown_vnd == -500000
        assert len(dd.periods) == 1

    def test_no_drawdown(self):
        dd = DrawdownResponse(
            max_drawdown_vnd=0, max_drawdown_pct=0,
            current_drawdown_vnd=0, current_drawdown_pct=0,
            periods=[],
        )
        assert dd.periods == []
