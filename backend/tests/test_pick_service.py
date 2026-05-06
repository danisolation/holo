"""Tests for daily pick generation service.

Covers all PICK-01 through PICK-07 requirements.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# --- PICK-01: Composite scoring selects 3-5 picks ---

class TestCompositeScoring:
    """PICK-01: Composite score = confidence×0.4 + combined×0.3 + safety×0.3."""

    def test_composite_scoring_formula(self):
        """Score 8 confidence + 7 combined + 6 safety = 8×0.4+7×0.3+6×0.3 = 7.1."""
        from app.services.pick_service import compute_composite_score
        result = compute_composite_score(
            trading_signal_confidence=8,
            combined_score=7,
            safety_score=6.0,
        )
        assert abs(result - 7.1) < 0.01

    def test_composite_scoring_max(self):
        """Max score = 10×0.4+10×0.3+10×0.3 = 10.0."""
        from app.services.pick_service import compute_composite_score
        result = compute_composite_score(10, 10, 10.0)
        assert abs(result - 10.0) < 0.01

    def test_composite_scoring_min(self):
        """Min score with all 1s = 1×0.4+1×0.3+1×0.3 = 1.0."""
        from app.services.pick_service import compute_composite_score
        result = compute_composite_score(1, 1, 1.0)
        assert abs(result - 1.0) < 0.01


# --- PICK-02: Capital filter ---

class TestCapitalFilter:
    """PICK-02: Filter picks by capital — user must afford at least 1 lot (100 shares)."""

    def test_capital_filter_affordable(self):
        """50M capital, 60k price → 100 shares × 60k = 6M ≤ 50M → affordable."""
        from app.services.pick_service import is_affordable
        assert is_affordable(capital=50_000_000, price=60_000) is True

    def test_capital_filter_too_expensive(self):
        """50M capital, 600k price → 100 shares × 600k = 60M > 50M → not affordable."""
        from app.services.pick_service import is_affordable
        assert is_affordable(capital=50_000_000, price=600_000) is False

    def test_capital_filter_exact_boundary(self):
        """50M capital, 500k price → 100 × 500k = 50M = capital → affordable."""
        from app.services.pick_service import is_affordable
        assert is_affordable(capital=50_000_000, price=500_000) is True


# --- PICK-03: Safety scoring ---

class TestSafetyScoring:
    """PICK-03: Safety score penalizes high ATR, low ADX, low volume."""

    def test_safety_score_safe_ticker(self):
        """Low ATR%, high ADX, high volume → high safety score."""
        from app.services.pick_service import compute_safety_score
        score = compute_safety_score(
            atr_14=500.0,        # ATR
            adx_14=35.0,         # Strong trend
            avg_volume=600_000,  # High liquidity
            current_price=50_000.0,  # ATR% = 1.0%
        )
        assert score >= 7.0  # High safety

    def test_safety_score_risky_ticker(self):
        """High ATR%, low ADX, low volume → low safety score."""
        from app.services.pick_service import compute_safety_score
        score = compute_safety_score(
            atr_14=3000.0,       # ATR
            adx_14=10.0,         # Weak trend
            avg_volume=50_000,   # Low liquidity
            current_price=50_000.0,  # ATR% = 6.0%
        )
        assert score <= 4.0  # Low safety

    def test_safety_score_zero_price_guard(self):
        """Price = 0 should not crash (division by zero guard)."""
        from app.services.pick_service import compute_safety_score
        score = compute_safety_score(
            atr_14=500.0, adx_14=25.0, avg_volume=300_000, current_price=0.0,
        )
        assert 0 <= score <= 10


# --- PICK-04: Vietnamese explanations ---

class TestExplanationGeneration:
    """PICK-04: Gemini generates 200-300 word Vietnamese explanation per pick."""

    @pytest.mark.asyncio
    async def test_explanation_prompt_contains_all_picks(self):
        """Prompt to Gemini must include all pick symbols."""
        from app.services.pick_service import build_explanation_prompt
        picks_data = [
            {"symbol": "VNM", "entry_price": 60000, "composite_score": 8.5},
            {"symbol": "FPT", "entry_price": 120000, "composite_score": 7.8},
        ]
        prompt = build_explanation_prompt(picks_data)
        assert "VNM" in prompt
        assert "FPT" in prompt


# --- PICK-05: Entry/SL/TP inheritance ---

class TestEntrySLTPInheritance:
    """PICK-05: Entry/SL/TP inherited from trading signal."""

    def test_extract_trading_plan_new_format(self):
        """Extract entry/SL/TP from new single-direction format."""
        from app.services.pick_service import extract_trading_plan
        raw_response = {
            "ticker": "VNM",
            "recommended_direction": "long",
            "confidence": 8,
            "trading_plan": {
                "entry_price": 60000,
                "stop_loss": 57000,
                "take_profit_1": 66000,
                "take_profit_2": 72000,
                "risk_reward_ratio": 2.0,
                "position_size_pct": 8,
                "timeframe": "swing",
            },
            "reasoning": "Test reasoning",
        }
        plan = extract_trading_plan(raw_response)
        assert plan["entry_price"] == 60000
        assert plan["stop_loss"] == 57000
        assert plan["take_profit_1"] == 66000
        assert plan["take_profit_2"] == 72000
        assert plan["risk_reward_ratio"] == 2.0
        assert plan["position_size_pct"] == 8
        assert plan["confidence"] == 8

    def test_extract_trading_plan_legacy_format(self):
        """Extract entry/SL/TP from legacy dual-direction format (backward compat)."""
        from app.services.pick_service import extract_trading_plan
        raw_response = {
            "ticker": "VNM",
            "recommended_direction": "long",
            "long_analysis": {
                "direction": "long",
                "confidence": 8,
                "trading_plan": {
                    "entry_price": 60000,
                    "stop_loss": 57000,
                    "take_profit_1": 66000,
                    "take_profit_2": 72000,
                    "risk_reward_ratio": 2.0,
                    "position_size_pct": 8,
                    "timeframe": "swing",
                },
                "reasoning": "Test reasoning",
            },
            "bearish_analysis": {
                "direction": "bearish",
                "confidence": 3,
                "trading_plan": {
                    "entry_price": 61000,
                    "stop_loss": 64000,
                    "take_profit_1": 55000,
                    "take_profit_2": 50000,
                    "risk_reward_ratio": 1.5,
                    "position_size_pct": 5,
                    "timeframe": "swing",
                },
                "reasoning": "Test bearish",
            },
        }
        plan = extract_trading_plan(raw_response)
        assert plan["entry_price"] == 60000
        assert plan["stop_loss"] == 57000
        assert plan["take_profit_1"] == 66000
        assert plan["take_profit_2"] == 72000
        assert plan["risk_reward_ratio"] == 2.0
        assert plan["position_size_pct"] == 8
        assert plan["confidence"] == 8


# --- PICK-06: Position sizing ---

class TestPositionSizing:
    """PICK-06: Position sizing in 100-share lots, round down."""

    def test_position_sizing_normal(self):
        """50M capital, 60k price, 8% position → min 1 lot, shares=100."""
        from app.services.pick_service import compute_position_sizing
        result = compute_position_sizing(
            capital=50_000_000, entry_price=60_000, position_pct=8,
        )
        # max_spend = 50M * 8% = 4M. lots = floor(4M / (60k*100)) = floor(0.67) = 0 → min 1
        assert result["shares"] == 100      # minimum 1 lot
        assert result["total_vnd"] == 6_000_000  # 100 × 60,000
        assert 0 < result["capital_pct"] <= 100

    def test_position_sizing_minimum_lot(self):
        """If capital allows exactly 1 lot."""
        from app.services.pick_service import compute_position_sizing
        result = compute_position_sizing(
            capital=10_000_000, entry_price=90_000, position_pct=100,
        )
        assert result["shares"] >= 100  # At least 1 lot
        assert result["shares"] % 100 == 0  # Must be multiple of 100

    def test_position_sizing_cap_at_30pct(self):
        """Position pct should be capped at 30% max per RESEARCH.md."""
        from app.services.pick_service import compute_position_sizing
        result = compute_position_sizing(
            capital=50_000_000, entry_price=10_000, position_pct=50,
        )
        # With 30% cap: max_spend = 15M, lots=150, shares=15000
        # Without cap: max_spend = 25M, lots=250, shares=25000
        assert result["total_vnd"] <= 50_000_000 * 0.30 + 10_000 * 100  # Allow 1 extra lot rounding


# --- PICK-07: Almost-selected with rejection reasons ---

class TestAlmostSelected:
    """PICK-07: Top 5-10 'almost selected' with 1-line rejection reason."""

    def test_rejection_reason_rsi_overbought(self):
        """RSI > 70 → rejection mentions overbought."""
        from app.services.pick_service import generate_rejection_reason
        reason = generate_rejection_reason(
            rsi=78.0, atr_pct=2.0, adx=30.0, avg_volume=500_000, composite_score=6.5,
        )
        assert "RSI" in reason or "overbought" in reason

    def test_rejection_reason_low_volume(self):
        """Volume < 100k → rejection mentions volume."""
        from app.services.pick_service import generate_rejection_reason
        reason = generate_rejection_reason(
            rsi=50.0, atr_pct=2.0, adx=30.0, avg_volume=50_000, composite_score=6.5,
        )
        assert "Volume" in reason or "volume" in reason or "thấp" in reason

    def test_rejection_reason_fallback(self):
        """No specific issue → fallback to composite score."""
        from app.services.pick_service import generate_rejection_reason
        reason = generate_rejection_reason(
            rsi=50.0, atr_pct=2.0, adx=30.0, avg_volume=500_000, composite_score=5.5,
        )
        assert "5.5" in reason or "Điểm" in reason or "điểm" in reason
