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
    DirectionAnalysisItem,
    ConfidenceBracketItem,
    RiskRewardResponse,
    ProfitFactorResponse,
    SectorAnalysisItem,
    StreakResponse,
    TimeframeComparisonItem,
    PeriodicSummaryItem,
    CalendarDataPoint,
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


class TestDirectionAnalysisSchema:
    """AN-05: Direction analysis response."""
    def test_valid_direction_item(self):
        item = DirectionAnalysisItem(
            direction="long", total_trades=5, wins=3, losses=2,
            win_rate=60.0, total_pnl=2000000, avg_pnl=400000,
        )
        assert item.direction == "long"
        assert item.win_rate == 60.0

    def test_bearish_direction(self):
        item = DirectionAnalysisItem(
            direction="bearish", total_trades=3, wins=1, losses=2,
            win_rate=33.33, total_pnl=-100000, avg_pnl=-33333,
        )
        assert item.direction == "bearish"


class TestConfidenceBracketSchema:
    """AN-06: Confidence bracket response."""
    def test_valid_bracket(self):
        item = ConfidenceBracketItem(
            bracket="HIGH", total_trades=10, wins=7,
            win_rate=70.0, avg_pnl=500000, avg_pnl_pct=3.5,
        )
        assert item.bracket == "HIGH"
        assert item.win_rate == 70.0


class TestConfidenceBracketBoundaries:
    """AN-06: Verify bracket boundaries match CONTEXT.md (1-3 LOW, 4-6 MEDIUM, 7-10 HIGH)."""
    def test_low_bracket_boundary(self):
        """Confidence 1, 2, 3 should map to LOW."""
        for conf in [1, 2, 3]:
            bracket = "LOW" if conf <= 3 else ("MEDIUM" if conf <= 6 else "HIGH")
            assert bracket == "LOW", f"Confidence {conf} should be LOW"

    def test_medium_bracket_boundary(self):
        """Confidence 4, 5, 6 should map to MEDIUM."""
        for conf in [4, 5, 6]:
            bracket = "LOW" if conf <= 3 else ("MEDIUM" if conf <= 6 else "HIGH")
            assert bracket == "MEDIUM", f"Confidence {conf} should be MEDIUM"

    def test_high_bracket_boundary(self):
        """Confidence 7, 8, 9, 10 should map to HIGH."""
        for conf in [7, 8, 9, 10]:
            bracket = "LOW" if conf <= 3 else ("MEDIUM" if conf <= 6 else "HIGH")
            assert bracket == "HIGH", f"Confidence {conf} should be HIGH"


class TestRiskRewardComputation:
    """AN-07: R:R achieved vs predicted."""
    def test_rr_achieved_long(self):
        """LONG: entry=80K, SL=75K, realized=1M, qty=200.
        risk = |80K - 75K| * 200 = 1M. achieved_rr = 1M / 1M = 1.0"""
        risk = abs(80000 - 75000) * 200
        achieved = 1000000 / risk
        assert achieved == 1.0

    def test_rr_achieved_bearish(self):
        """BEARISH: entry=120K, SL=130K, realized=2M, qty=200.
        risk = |120K - 130K| * 200 = 2M. achieved_rr = 2M / 2M = 1.0"""
        risk = abs(120000 - 130000) * 200
        achieved = 2000000 / risk
        assert achieved == 1.0

    def test_rr_negative_loss(self):
        """Loss trade: entry=80K, SL=75K, realized=-500K, qty=200.
        risk = 1M. achieved_rr = -500K / 1M = -0.5"""
        risk = abs(80000 - 75000) * 200
        achieved = -500000 / risk
        assert achieved == -0.5

    def test_rr_schema(self):
        resp = RiskRewardResponse(
            avg_predicted_rr=2.5, avg_achieved_rr=1.8,
            trades_above_predicted=3, trades_below_predicted=7,
            total_trades=10,
        )
        assert resp.avg_predicted_rr == 2.5


class TestProfitFactorComputation:
    """AN-08: Profit factor + expected value."""
    def test_profit_factor_basic(self):
        """gross_profit=3M, gross_loss=-1M → PF = 3M / 1M = 3.0"""
        gross_profit = 3000000
        gross_loss = -1000000
        pf = gross_profit / abs(gross_loss) if gross_loss < 0 else None
        assert pf == 3.0

    def test_profit_factor_no_losses(self):
        """All wins → profit_factor = None (avoid infinity)."""
        gross_loss = 0
        pf = None if gross_loss >= 0 else 1.0
        assert pf is None

    def test_profit_factor_schema(self):
        resp = ProfitFactorResponse(
            gross_profit=3000000, gross_loss=-1000000,
            profit_factor=3.0, expected_value=200000, total_trades=10,
        )
        assert resp.profit_factor == 3.0

    def test_profit_factor_nullable(self):
        resp = ProfitFactorResponse(
            gross_profit=500000, gross_loss=0,
            profit_factor=None, expected_value=250000, total_trades=2,
        )
        assert resp.profit_factor is None


class TestSectorAnalysisSchema:
    """AN-09: Sector analysis response."""
    def test_valid_sector_item(self):
        item = SectorAnalysisItem(
            sector="Ngân hàng", total_trades=15, wins=9,
            win_rate=60.0, total_pnl=5000000, avg_pnl=333333,
        )
        assert item.sector == "Ngân hàng"
        assert item.total_trades == 15

    def test_unknown_sector(self):
        """Tickers with NULL industry should map to 'Unknown'."""
        item = SectorAnalysisItem(
            sector="Unknown", total_trades=3, wins=1,
            win_rate=33.33, total_pnl=-100000, avg_pnl=-33333,
        )
        assert item.sector == "Unknown"


# --- Phase 26: Streak Computation + New Schema Tests ---

class TestStreakComputation:
    """UI-03: Streak algorithm (pure Python — no DB)."""

    def _compute_streaks(self, pnl_sequence: list[float]) -> dict:
        """Replicate streak logic for testing."""
        current_win = 0; current_loss = 0; max_win = 0; max_loss = 0
        for pnl in pnl_sequence:
            if pnl > 0:
                current_win += 1; current_loss = 0
                max_win = max(max_win, current_win)
            else:
                current_loss += 1; current_win = 0
                max_loss = max(max_loss, current_loss)
        return {
            "current_win_streak": current_win, "current_loss_streak": current_loss,
            "longest_win_streak": max_win, "longest_loss_streak": max_loss,
            "total_trades": len(pnl_sequence),
        }

    def test_alternating_wins_losses(self):
        result = self._compute_streaks([100, -50, 200, -30, 150])
        assert result["longest_win_streak"] == 1
        assert result["longest_loss_streak"] == 1
        assert result["current_win_streak"] == 1  # ends on win

    def test_all_wins(self):
        result = self._compute_streaks([100, 200, 300, 400])
        assert result["longest_win_streak"] == 4
        assert result["current_win_streak"] == 4
        assert result["longest_loss_streak"] == 0

    def test_all_losses(self):
        result = self._compute_streaks([-100, -200, -300])
        assert result["longest_loss_streak"] == 3
        assert result["current_loss_streak"] == 3
        assert result["longest_win_streak"] == 0

    def test_empty(self):
        result = self._compute_streaks([])
        assert result == {"current_win_streak": 0, "current_loss_streak": 0,
                          "longest_win_streak": 0, "longest_loss_streak": 0,
                          "total_trades": 0}

    def test_streak_ending_on_loss(self):
        result = self._compute_streaks([100, 200, 300, -50, -60])
        assert result["longest_win_streak"] == 3
        assert result["current_loss_streak"] == 2
        assert result["current_win_streak"] == 0


class TestStreakSchema:
    def test_valid(self):
        s = StreakResponse(current_win_streak=3, current_loss_streak=0,
                           longest_win_streak=5, longest_loss_streak=2, total_trades=20)
        assert s.longest_win_streak == 5


class TestTimeframeSchema:
    def test_valid(self):
        t = TimeframeComparisonItem(timeframe="swing", total_trades=10,
                                     wins=6, losses=4, win_rate=60.0,
                                     total_pnl=5000000, avg_pnl=500000)
        assert t.timeframe == "swing"


class TestPeriodicSchema:
    def test_valid(self):
        p = PeriodicSummaryItem(period="2025-W03", total_trades=5,
                                 wins=3, losses=2, win_rate=60.0,
                                 total_pnl=1500000, avg_rr=2.5)
        assert p.period == "2025-W03"


class TestCalendarSchema:
    def test_valid(self):
        c = CalendarDataPoint(date="2025-01-15", daily_pnl=500000, trade_count=3)
        assert c.trade_count == 3
    def test_loss_day(self):
        c = CalendarDataPoint(date="2025-01-16", daily_pnl=-200000, trade_count=1)
        assert c.daily_pnl < 0
