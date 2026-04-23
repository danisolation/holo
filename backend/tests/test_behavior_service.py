"""Unit tests for behavior service pure functions.

Tests premature profit-taking detection, holding losers detection,
impulsive trade detection, sector preference scoring, and
consecutive loss checking. Pure function tests — no database needed.
"""
import pytest
from datetime import datetime, timezone, timedelta


from app.services.behavior_service import (
    detect_premature_profit_taking,
    detect_holding_losers,
    detect_impulsive_trade,
    compute_preference_score,
    check_consecutive_losses_pure,
)


# ── Premature Profit-Taking Tests ────────────────────────────────────────────


class TestPrematureProfitTaking:
    """Detect if price rose >5% after selling at a profit."""

    def test_clear_premature_sell(self):
        """sell_price=60000, post-sell prices rising: [60500, 62000, 63500] → max 63500 = +5.83% → True."""
        result = detect_premature_profit_taking(60000.0, [60500.0, 62000.0, 63500.0])
        assert result is True

    def test_flat_prices_after_sell(self):
        """sell_price=60000, post-sell prices flat: [60100, 59800, 60200] → max 60200 = +0.33% → False."""
        result = detect_premature_profit_taking(60000.0, [60100.0, 59800.0, 60200.0])
        assert result is False

    def test_empty_prices_list(self):
        """Empty prices list → False."""
        result = detect_premature_profit_taking(60000.0, [])
        assert result is False

    def test_exactly_at_threshold(self):
        """Exactly at threshold (5.0%) → False (must exceed, not equal)."""
        # 60000 * 1.05 = 63000.0
        result = detect_premature_profit_taking(60000.0, [63000.0])
        assert result is False

    def test_just_above_threshold(self):
        """Just above 5% threshold → True."""
        result = detect_premature_profit_taking(60000.0, [63001.0])
        assert result is True

    def test_custom_threshold(self):
        """Custom threshold of 10% — 66001 / 60000 = +10.0% → False, 66001 = True."""
        result = detect_premature_profit_taking(60000.0, [66000.0], threshold_pct=10.0)
        assert result is False
        result = detect_premature_profit_taking(60000.0, [66001.0], threshold_pct=10.0)
        assert result is True


# ── Holding Losers Tests ─────────────────────────────────────────────────────


class TestHoldingLosers:
    """Detect open positions with unrealized loss >10% held >5 days."""

    def test_clear_holding_loser(self):
        """buy=60000, current=53000 → -11.67% loss, 7 days → True."""
        result = detect_holding_losers(60000.0, 53000.0, 7)
        assert result is True

    def test_loss_below_threshold(self):
        """buy=60000, current=55000 → -8.33% loss, 7 days → False (loss < 10%)."""
        result = detect_holding_losers(60000.0, 55000.0, 7)
        assert result is False

    def test_days_below_minimum(self):
        """buy=60000, current=53000 → -11.67% loss, 3 days → False (held < 5)."""
        result = detect_holding_losers(60000.0, 53000.0, 3)
        assert result is False

    def test_both_below_threshold(self):
        """Both loss and days below threshold → False."""
        result = detect_holding_losers(60000.0, 55000.0, 3)
        assert result is False

    def test_exactly_at_loss_threshold(self):
        """Exactly 10% loss, exactly 5 days → False (must exceed, not equal)."""
        result = detect_holding_losers(60000.0, 54000.0, 5)  # 10% loss, 5 days
        assert result is False

    def test_exceeds_both(self):
        """Loss >10% and held >5 days → True."""
        result = detect_holding_losers(60000.0, 53999.0, 6)  # 10.0017% loss, 6 days
        assert result is True

    def test_custom_thresholds(self):
        """Custom thresholds."""
        # 15% loss threshold, 3 days minimum
        result = detect_holding_losers(60000.0, 50000.0, 4, loss_threshold_pct=15.0, min_days=3)
        assert result is True  # -16.67%, 4 days
        result = detect_holding_losers(60000.0, 52000.0, 4, loss_threshold_pct=15.0, min_days=3)
        assert result is False  # -13.33%, 4 days


# ── Impulsive Trade Tests ────────────────────────────────────────────────────


class TestImpulsiveTrade:
    """Detect trades created within 2 hours of a news article."""

    def test_within_window(self):
        """trade at 14:00, news at 13:00 → 1 hour gap → True."""
        trade_time = datetime(2026, 4, 20, 14, 0, tzinfo=timezone.utc)
        news_time = datetime(2026, 4, 20, 13, 0, tzinfo=timezone.utc)
        result = detect_impulsive_trade(trade_time, [news_time])
        assert result is True

    def test_outside_window(self):
        """trade at 14:00, news at 11:00 → 3 hour gap → False."""
        trade_time = datetime(2026, 4, 20, 14, 0, tzinfo=timezone.utc)
        news_time = datetime(2026, 4, 20, 11, 0, tzinfo=timezone.utc)
        result = detect_impulsive_trade(trade_time, [news_time])
        assert result is False

    def test_no_news(self):
        """No matching news articles → False."""
        trade_time = datetime(2026, 4, 20, 14, 0, tzinfo=timezone.utc)
        result = detect_impulsive_trade(trade_time, [])
        assert result is False

    def test_news_after_trade(self):
        """News published AFTER trade → should not match."""
        trade_time = datetime(2026, 4, 20, 14, 0, tzinfo=timezone.utc)
        news_time = datetime(2026, 4, 20, 15, 0, tzinfo=timezone.utc)
        result = detect_impulsive_trade(trade_time, [news_time])
        assert result is False

    def test_multiple_news_one_match(self):
        """Multiple news, one within window → True."""
        trade_time = datetime(2026, 4, 20, 14, 0, tzinfo=timezone.utc)
        news_times = [
            datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),  # 4h gap
            datetime(2026, 4, 20, 13, 30, tzinfo=timezone.utc),  # 30min gap → match
        ]
        result = detect_impulsive_trade(trade_time, news_times)
        assert result is True

    def test_exactly_at_window_boundary(self):
        """Exactly 2 hours → False (must be within, not equal)."""
        trade_time = datetime(2026, 4, 20, 14, 0, tzinfo=timezone.utc)
        news_time = datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc)
        result = detect_impulsive_trade(trade_time, [news_time])
        assert result is False

    def test_custom_window(self):
        """Custom 4-hour window."""
        trade_time = datetime(2026, 4, 20, 14, 0, tzinfo=timezone.utc)
        news_time = datetime(2026, 4, 20, 11, 0, tzinfo=timezone.utc)
        result = detect_impulsive_trade(trade_time, [news_time], window_hours=4.0)
        assert result is True  # 3h gap within 4h window


# ── Sector Preference Scoring Tests ──────────────────────────────────────────


class TestSectorPreferenceScoring:
    """Test preference_score = (win_rate × 0.6) + (normalized_pnl × 0.4).

    Uses centered normalization: subtract mean so poor sectors get score < 0.
    """

    def test_basic_scoring(self):
        """70% win rate, normalized_pnl=0.5 → 0.7*0.6 + 0.5*0.4 = 0.62."""
        result = compute_preference_score(0.7, 0.5)
        assert abs(result - 0.62) < 0.001

    def test_zero_everything(self):
        """0% win rate, 0.0 normalized_pnl → 0."""
        result = compute_preference_score(0.0, 0.0)
        assert result == 0.0

    def test_perfect_win_rate(self):
        """100% win rate, normalized_pnl=1.0 → 1.0*0.6 + 1.0*0.4 = 1.0."""
        result = compute_preference_score(1.0, 1.0)
        assert abs(result - 1.0) < 0.001

    def test_all_losses(self):
        """0% win rate, normalized_pnl=-0.5 → 0.0*0.6 + (-0.5)*0.4 = -0.2."""
        result = compute_preference_score(0.0, -0.5)
        assert abs(result - (-0.2)) < 0.001

    def test_negative_normalized_pnl(self):
        """50% win rate, negative normalized_pnl → mixed."""
        result = compute_preference_score(0.5, -0.3)
        # 0.5*0.6 + (-0.3)*0.4 = 0.3 - 0.12 = 0.18
        assert abs(result - 0.18) < 0.001


# ── Consecutive Loss Check Tests ─────────────────────────────────────────────


class TestConsecutiveLossCheck:
    """Check if last 3 SELL trades are all losses → suggest risk reduction."""

    def test_three_consecutive_losses(self):
        """3 negative P&Ls → returns suggestion dict."""
        result = check_consecutive_losses_pure(
            [-100000.0, -50000.0, -200000.0],
            current_risk_level=3,
            has_pending_suggestion=False,
        )
        assert result is not None
        assert result["current_level"] == 3
        assert result["suggested_level"] == 2
        assert "reason" in result

    def test_not_all_losses(self):
        """Mixed P&Ls → returns None."""
        result = check_consecutive_losses_pure(
            [-100000.0, 50000.0, -200000.0],
            current_risk_level=3,
            has_pending_suggestion=False,
        )
        assert result is None

    def test_fewer_than_three(self):
        """Only 2 SELLs → returns None."""
        result = check_consecutive_losses_pure(
            [-100000.0, -50000.0],
            current_risk_level=3,
            has_pending_suggestion=False,
        )
        assert result is None

    def test_already_pending(self):
        """Already has pending suggestion → returns None."""
        result = check_consecutive_losses_pure(
            [-100000.0, -50000.0, -200000.0],
            current_risk_level=3,
            has_pending_suggestion=True,
        )
        assert result is None

    def test_already_at_minimum(self):
        """Risk level already 1 → returns None (can't go lower)."""
        result = check_consecutive_losses_pure(
            [-100000.0, -50000.0, -200000.0],
            current_risk_level=1,
            has_pending_suggestion=False,
        )
        assert result is None

    def test_empty_list(self):
        """No SELLs → returns None."""
        result = check_consecutive_losses_pure(
            [],
            current_risk_level=3,
            has_pending_suggestion=False,
        )
        assert result is None

    def test_suggested_level_is_one_below(self):
        """Suggested level should be current - 1."""
        result = check_consecutive_losses_pure(
            [-100000.0, -50000.0, -200000.0],
            current_risk_level=5,
            has_pending_suggestion=False,
        )
        assert result is not None
        assert result["suggested_level"] == 4
