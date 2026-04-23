"""Tests for pick outcome computation — pure function tests.

Tests compute_pick_outcome with all outcome scenarios:
loser (SL hit), winner (TP1 hit), expired (>10 days), pending (not enough days),
pending (empty closes), TP2 bonus flag detection.
"""
from datetime import date

from app.models.daily_pick import PickOutcome
from app.services.pick_service import compute_pick_outcome


class TestComputePickOutcome:
    """Pure function tests for compute_pick_outcome."""

    def test_loser_stop_loss_hit(self):
        """Close <= stop_loss → LOSER, hit_stop_loss=True."""
        result = compute_pick_outcome(
            entry_price=100.0,
            stop_loss=90.0,
            take_profit_1=115.0,
            take_profit_2=None,
            daily_closes=[(date(2026, 1, 2), 88.0)],
        )
        assert result["outcome"] == PickOutcome.LOSER
        assert result["days_held"] == 1
        assert result["hit_stop_loss"] is True
        assert result["hit_take_profit_1"] is False
        assert result["hit_take_profit_2"] is False
        assert result["actual_return_pct"] == pytest.approx(-12.0)

    def test_winner_take_profit_1_hit(self):
        """Close >= take_profit_1 → WINNER, hit_take_profit_1=True."""
        result = compute_pick_outcome(
            entry_price=100.0,
            stop_loss=90.0,
            take_profit_1=115.0,
            take_profit_2=None,
            daily_closes=[
                (date(2026, 1, 2), 105.0),
                (date(2026, 1, 3), 116.0),
            ],
        )
        assert result["outcome"] == PickOutcome.WINNER
        assert result["days_held"] == 2
        assert result["hit_stop_loss"] is False
        assert result["hit_take_profit_1"] is True
        assert result["actual_return_pct"] == pytest.approx(16.0)

    def test_expired_after_max_trading_days(self):
        """10 days between SL and TP1 → EXPIRED."""
        closes = [
            (date(2026, 1, i + 2), 95.0 + (i % 5))
            for i in range(10)
        ]
        result = compute_pick_outcome(
            entry_price=100.0,
            stop_loss=90.0,
            take_profit_1=115.0,
            take_profit_2=None,
            daily_closes=closes,
        )
        assert result["outcome"] == PickOutcome.EXPIRED
        assert result["days_held"] == 10
        assert result["hit_stop_loss"] is False
        assert result["hit_take_profit_1"] is False
        assert result["actual_return_pct"] is not None

    def test_pending_not_enough_days(self):
        """Only 1 day of data, between SL and TP1 → PENDING."""
        result = compute_pick_outcome(
            entry_price=100.0,
            stop_loss=90.0,
            take_profit_1=115.0,
            take_profit_2=None,
            daily_closes=[(date(2026, 1, 2), 105.0)],
        )
        assert result["outcome"] == PickOutcome.PENDING
        assert result["days_held"] == 1
        # PENDING should not have actual_return_pct
        assert result.get("actual_return_pct") is None

    def test_pending_empty_closes(self):
        """No closes at all → PENDING, days_held=0."""
        result = compute_pick_outcome(
            entry_price=100.0,
            stop_loss=90.0,
            take_profit_1=115.0,
            take_profit_2=None,
            daily_closes=[],
        )
        assert result["outcome"] == PickOutcome.PENDING
        assert result["days_held"] == 0

    def test_tp2_bonus_flag_detected(self):
        """Close >= take_profit_2 → WINNER with hit_take_profit_2=True."""
        result = compute_pick_outcome(
            entry_price=100.0,
            stop_loss=90.0,
            take_profit_1=115.0,
            take_profit_2=130.0,
            daily_closes=[
                (date(2026, 1, 2), 105.0),
                (date(2026, 1, 3), 135.0),  # Exceeds TP2
            ],
        )
        assert result["outcome"] == PickOutcome.WINNER
        assert result["hit_take_profit_1"] is True
        assert result["hit_take_profit_2"] is True
        assert result["actual_return_pct"] == pytest.approx(35.0)

    def test_tp2_not_hit_when_tp1_just_hit(self):
        """Close >= TP1 but < TP2 → hit_take_profit_2=False."""
        result = compute_pick_outcome(
            entry_price=100.0,
            stop_loss=90.0,
            take_profit_1=115.0,
            take_profit_2=130.0,
            daily_closes=[(date(2026, 1, 2), 116.0)],
        )
        assert result["outcome"] == PickOutcome.WINNER
        assert result["hit_take_profit_1"] is True
        assert result["hit_take_profit_2"] is False

    def test_stop_loss_exact_boundary(self):
        """Close == stop_loss → still LOSER (close <= SL)."""
        result = compute_pick_outcome(
            entry_price=100.0,
            stop_loss=90.0,
            take_profit_1=115.0,
            take_profit_2=None,
            daily_closes=[(date(2026, 1, 2), 90.0)],
        )
        assert result["outcome"] == PickOutcome.LOSER
        assert result["hit_stop_loss"] is True

    def test_take_profit_exact_boundary(self):
        """Close == take_profit_1 → WINNER (close >= TP1)."""
        result = compute_pick_outcome(
            entry_price=100.0,
            stop_loss=90.0,
            take_profit_1=115.0,
            take_profit_2=None,
            daily_closes=[(date(2026, 1, 2), 115.0)],
        )
        assert result["outcome"] == PickOutcome.WINNER
        assert result["hit_take_profit_1"] is True


# Need pytest import for approx
import pytest
