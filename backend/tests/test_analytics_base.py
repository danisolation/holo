"""Unit tests for shared analytics utilities (Phase 37: BCK-01)."""
import pytest
from app.services.analytics_base import (
    calc_win_rate,
    calc_pnl_pct,
    calc_avg_pnl,
    calc_max_drawdown,
)


class TestCalcWinRate:
    def test_normal(self):
        assert calc_win_rate(5, 10) == 50.0

    def test_all_wins(self):
        assert calc_win_rate(10, 10) == 100.0

    def test_zero_wins(self):
        assert calc_win_rate(0, 10) == 0.0

    def test_zero_total_returns_zero(self):
        assert calc_win_rate(0, 0) == 0.0


class TestCalcPnlPct:
    def test_positive_pnl(self):
        assert calc_pnl_pct(50_000, 1_000_000) == 5.0

    def test_negative_pnl(self):
        assert calc_pnl_pct(-30_000, 1_000_000) == -3.0

    def test_zero_capital_returns_zero(self):
        assert calc_pnl_pct(100, 0) == 0.0


class TestCalcAvgPnl:
    def test_normal(self):
        assert calc_avg_pnl(150_000, 3) == 50_000.0

    def test_zero_count_returns_zero(self):
        assert calc_avg_pnl(999, 0) == 0.0


class TestCalcMaxDrawdown:
    def test_monotonic_up_no_drawdown(self):
        dd_vnd, dd_pct = calc_max_drawdown([100, 200, 300, 400])
        assert dd_vnd == 0.0
        assert dd_pct == 0.0

    def test_single_peak_trough(self):
        dd_vnd, dd_pct = calc_max_drawdown([100, 200, 150])
        assert dd_vnd == -50.0
        assert dd_pct == -25.0

    def test_multiple_peaks(self):
        dd_vnd, dd_pct = calc_max_drawdown([100, 200, 150, 300, 200])
        assert dd_vnd == -100.0
        assert dd_pct == pytest.approx(-33.33)

    def test_empty_list(self):
        dd_vnd, dd_pct = calc_max_drawdown([])
        assert dd_vnd == 0.0
        assert dd_pct == 0.0

    def test_flat_curve(self):
        dd_vnd, dd_pct = calc_max_drawdown([100, 100, 100])
        assert dd_vnd == 0.0
        assert dd_pct == 0.0
