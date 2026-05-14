"""Unit tests for pick pipeline pure functions.

Tests extract_trading_plan, compute_pick_outcome, compute_safety_score,
compute_position_sizing, generate_rejection_reason — no DB needed.
"""
import pytest
from datetime import date

from app.services.pick_service import (
    extract_trading_plan,
    compute_pick_outcome,
    compute_safety_score,
    compute_position_sizing,
    generate_rejection_reason,
)
from app.models.daily_pick import PickOutcome


# ── TestExtractTradingPlan ───────────────────────────────────────────────────


class TestExtractTradingPlan:
    """Tests for extract_trading_plan: 3 format variants."""

    def test_unified_format(self):
        raw = {
            "entry_price": 50000,
            "stop_loss": 48000,
            "take_profit_1": 55000,
            "take_profit_2": 58000,
            "risk_reward_ratio": 2.5,
            "score": 8,
        }
        result = extract_trading_plan(raw)
        assert result["entry_price"] == 50000
        assert result["stop_loss"] == 48000
        assert result["take_profit_1"] == 55000
        assert result["take_profit_2"] == 58000
        assert result["risk_reward_ratio"] == 2.5
        assert result["confidence"] == 8  # from "score"

    def test_unified_format_defaults(self):
        raw = {"entry_price": 50000, "stop_loss": 48000}
        result = extract_trading_plan(raw)
        assert result["position_size_pct"] == 10  # default
        assert result["confidence"] == 5  # default

    def test_single_direction_format(self):
        raw = {
            "trading_plan": {
                "entry_price": 50000,
                "stop_loss": 48000,
                "take_profit_1": 55000,
                "take_profit_2": 58000,
                "risk_reward_ratio": 2.5,
            },
            "confidence": 7,
        }
        result = extract_trading_plan(raw)
        assert result["entry_price"] == 50000
        assert result["confidence"] == 7

    def test_legacy_dual_direction_format(self):
        raw = {
            "long_analysis": {
                "trading_plan": {
                    "entry_price": 50000,
                    "stop_loss": 48000,
                    "take_profit_1": 55000,
                    "take_profit_2": 58000,
                    "risk_reward_ratio": 2.0,
                },
                "confidence": 6,
            }
        }
        result = extract_trading_plan(raw)
        assert result["entry_price"] == 50000
        assert result["confidence"] == 6

    def test_missing_fields_default_gracefully(self):
        raw = {}
        result = extract_trading_plan(raw)
        assert result["position_size_pct"] == 10
        assert result["confidence"] == 5


# ── TestComputePickOutcome ───────────────────────────────────────────────────


class TestComputePickOutcome:
    """Tests for compute_pick_outcome: SL/TP/EXPIRED/PENDING logic."""

    def test_hit_stop_loss(self):
        result = compute_pick_outcome(
            entry_price=50000, stop_loss=48000,
            take_profit_1=55000, take_profit_2=60000,
            daily_closes=[(date(2024, 1, 2), 47000)],
        )
        assert result["outcome"] == PickOutcome.LOSER
        assert result["hit_stop_loss"] is True
        assert result["actual_return_pct"] < 0

    def test_hit_take_profit_1(self):
        result = compute_pick_outcome(
            entry_price=50000, stop_loss=48000,
            take_profit_1=55000, take_profit_2=60000,
            daily_closes=[(date(2024, 1, 2), 56000)],
        )
        assert result["outcome"] == PickOutcome.WINNER
        assert result["hit_take_profit_1"] is True
        assert result["actual_return_pct"] > 0

    def test_hit_take_profit_2(self):
        result = compute_pick_outcome(
            entry_price=50000, stop_loss=48000,
            take_profit_1=55000, take_profit_2=60000,
            daily_closes=[(date(2024, 1, 2), 61000)],
        )
        assert result["outcome"] == PickOutcome.WINNER
        assert result["hit_take_profit_2"] is True

    def test_expired_after_max_days(self):
        closes = [(date(2024, 1, i + 2), 51000) for i in range(10)]
        result = compute_pick_outcome(
            entry_price=50000, stop_loss=48000,
            take_profit_1=55000, take_profit_2=60000,
            daily_closes=closes,
        )
        assert result["outcome"] == PickOutcome.EXPIRED
        assert result["days_held"] == 10

    def test_pending_empty_closes(self):
        result = compute_pick_outcome(
            entry_price=50000, stop_loss=48000,
            take_profit_1=55000, take_profit_2=None,
            daily_closes=[],
        )
        assert result["outcome"] == PickOutcome.PENDING
        assert result["days_held"] == 0

    def test_pending_not_enough_days(self):
        closes = [(date(2024, 1, 2), 51000), (date(2024, 1, 3), 52000)]
        result = compute_pick_outcome(
            entry_price=50000, stop_loss=48000,
            take_profit_1=55000, take_profit_2=None,
            daily_closes=closes,
        )
        assert result["outcome"] == PickOutcome.PENDING

    def test_unsorted_closes_handled(self):
        # Provide dates out of order — function sorts internally
        closes = [
            (date(2024, 1, 5), 56000),  # TP hit but later date
            (date(2024, 1, 2), 49000),  # Should be processed first (between SL and TP)
        ]
        result = compute_pick_outcome(
            entry_price=50000, stop_loss=48000,
            take_profit_1=55000, take_profit_2=None,
            daily_closes=closes,
        )
        # After sorting: Jan 2 (49000 - between SL and TP), Jan 5 (56000 - hits TP)
        assert result["outcome"] == PickOutcome.WINNER


# ── TestComputeSafetyScore ───────────────────────────────────────────────────


class TestComputeSafetyScore:
    """Tests for compute_safety_score: ATR/ADX/volume → 0-10 score."""

    def test_safe_stock_high_score(self):
        score = compute_safety_score(atr_14=500, adx_14=35, avg_volume=600000, current_price=50000)
        assert score > 5

    def test_risky_stock_low_score(self):
        score = compute_safety_score(atr_14=3000, adx_14=10, avg_volume=50000, current_price=50000)
        assert score < 3

    def test_score_in_range(self):
        for atr, adx, vol in [(100, 50, 1000000), (5000, 5, 10000), (1000, 25, 250000)]:
            score = compute_safety_score(atr, adx, vol, 50000)
            assert 0 <= score <= 10, f"Score {score} out of range for atr={atr}, adx={adx}, vol={vol}"


# ── TestComputePositionSizing ────────────────────────────────────────────────


class TestComputePositionSizing:
    """Tests for compute_position_sizing: lot-aligned, 30% cap."""

    def test_normal_sizing(self):
        result = compute_position_sizing(capital=50_000_000, entry_price=50000, position_pct=20)
        assert result["shares"] % 100 == 0  # lot aligned
        assert result["total_vnd"] <= 10_000_000  # 20% of 50M

    def test_caps_at_30_percent(self):
        result = compute_position_sizing(capital=50_000_000, entry_price=50000, position_pct=50)
        # 50% should be capped to 30% → max spend = 15M
        assert result["total_vnd"] <= 15_000_000

    def test_minimum_one_lot(self):
        # Very expensive stock relative to capital → still gets 1 lot (100 shares)
        result = compute_position_sizing(capital=50_000_000, entry_price=400000, position_pct=1)
        assert result["shares"] == 100  # minimum 1 lot

    def test_shares_multiple_of_100(self):
        result = compute_position_sizing(capital=100_000_000, entry_price=25000, position_pct=25)
        assert result["shares"] % 100 == 0


# ── TestGenerateRejectionReason ──────────────────────────────────────────────


class TestGenerateRejectionReason:
    """Tests for generate_rejection_reason: Vietnamese text output."""

    def test_rsi_overbought(self):
        reason = generate_rejection_reason(rsi=75, atr_pct=2.0, adx=30, avg_volume=500000, composite_score=5.0)
        assert "overbought" in reason.lower() or "overbought" in reason

    def test_high_volatility(self):
        reason = generate_rejection_reason(rsi=50, atr_pct=5.0, adx=30, avg_volume=500000, composite_score=5.0)
        assert "Biến động cao" in reason

    def test_weak_trend(self):
        reason = generate_rejection_reason(rsi=50, atr_pct=2.0, adx=15, avg_volume=500000, composite_score=5.0)
        assert "Xu hướng yếu" in reason

    def test_low_volume(self):
        reason = generate_rejection_reason(rsi=50, atr_pct=2.0, adx=30, avg_volume=50000, composite_score=5.0)
        assert "Volume quá thấp" in reason

    def test_fallback_low_composite(self):
        reason = generate_rejection_reason(rsi=50, atr_pct=2.0, adx=30, avg_volume=500000, composite_score=3.5)
        assert "Điểm tổng hợp" in reason
