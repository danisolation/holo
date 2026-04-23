"""Unit tests for goal service pure functions.

Tests compute_goal_progress (color thresholds, edge cases),
clamp_risk_level (bounds enforcement), build_review_prompt
(Vietnamese content generation), and parse_review_response
(fallback handling). Pure function tests — no database needed.
"""
import pytest

from app.services.goal_service import (
    compute_goal_progress,
    clamp_risk_level,
    build_review_prompt,
    parse_review_response,
)


# ── Goal Progress Tests ──────────────────────────────────────────────────────


class TestComputeGoalProgress:
    """compute_goal_progress returns percentage and color based on thresholds."""

    def test_amber_50_pct(self):
        """50% of target → amber."""
        result = compute_goal_progress(2_500_000, 5_000_000)
        assert result == {"percentage": 50.0, "color": "amber"}

    def test_green_100_pct(self):
        """Exactly 100% → green."""
        result = compute_goal_progress(5_000_000, 5_000_000)
        assert result == {"percentage": 100.0, "color": "green"}

    def test_green_capped_at_200(self):
        """240% capped to 200% → green."""
        result = compute_goal_progress(12_000_000, 5_000_000)
        assert result == {"percentage": 200.0, "color": "green"}

    def test_red_10_pct(self):
        """10% of target → red."""
        result = compute_goal_progress(500_000, 5_000_000)
        assert result == {"percentage": 10.0, "color": "red"}

    def test_zero_actual(self):
        """0 actual → 0% red."""
        result = compute_goal_progress(0, 5_000_000)
        assert result == {"percentage": 0.0, "color": "red"}

    def test_zero_target_guard(self):
        """Zero target → safe fallback 0% red (no division by zero)."""
        result = compute_goal_progress(1_000_000, 0)
        assert result == {"percentage": 0.0, "color": "red"}

    def test_negative_target_guard(self):
        """Negative target → safe fallback 0% red."""
        result = compute_goal_progress(1_000_000, -100)
        assert result == {"percentage": 0.0, "color": "red"}

    def test_negative_actual_shows_zero(self):
        """Negative actual_pnl → clamp to 0%, not negative bar."""
        result = compute_goal_progress(-500_000, 5_000_000)
        assert result == {"percentage": 0.0, "color": "red"}

    def test_just_below_50_is_red(self):
        """49.9% → red (below amber threshold)."""
        result = compute_goal_progress(2_495_000, 5_000_000)
        assert result["color"] == "red"
        assert result["percentage"] == 49.9

    def test_just_below_100_is_amber(self):
        """99% → amber (below green threshold)."""
        result = compute_goal_progress(4_950_000, 5_000_000)
        assert result["color"] == "amber"
        assert result["percentage"] == 99.0


# ── Risk Level Clamping Tests ────────────────────────────────────────────────


class TestClampRiskLevel:
    """clamp_risk_level enforces min=1, max=5 bounds."""

    def test_decrease_normal(self):
        """3 + (-1) = 2."""
        assert clamp_risk_level(3, -1) == 2

    def test_decrease_clamped_at_min(self):
        """1 + (-1) cannot go below 1."""
        assert clamp_risk_level(1, -1) == 1

    def test_increase_clamped_at_max(self):
        """5 + 1 cannot go above 5."""
        assert clamp_risk_level(5, 1) == 5

    def test_unchanged(self):
        """3 + 0 = 3."""
        assert clamp_risk_level(3, 0) == 3

    def test_increase_normal(self):
        """2 + 1 = 3."""
        assert clamp_risk_level(2, 1) == 3

    def test_extreme_negative_delta(self):
        """5 + (-10) clamps to 1."""
        assert clamp_risk_level(5, -10) == 1

    def test_extreme_positive_delta(self):
        """1 + 10 clamps to 5."""
        assert clamp_risk_level(1, 10) == 5


# ── Build Review Prompt Tests ────────────────────────────────────────────────


class TestBuildReviewPrompt:
    """build_review_prompt produces Vietnamese coaching prompt."""

    def test_with_trades_data(self):
        """Prompt includes trade details and Vietnamese instructions."""
        trades = [
            {"ticker": "VNM", "side": "BUY", "pnl": 0},
            {"ticker": "VNM", "side": "SELL", "pnl": 500_000},
        ]
        habits = [{"habit_type": "premature_sell", "ticker": "VNM"}]
        picks = [{"ticker": "FPT", "outcome": "winner"}]
        prompt = build_review_prompt(trades, habits, picks, risk_level=3, goal_progress={"percentage": 60.0, "color": "amber"})

        assert "tiếng Việt" in prompt or "Việt" in prompt
        assert "VNM" in prompt
        assert "500" in prompt  # pnl value referenced

    def test_no_trades_week(self):
        """Prompt mentions no trades for the week."""
        prompt = build_review_prompt([], [], [], risk_level=3, goal_progress=None)

        assert "không có giao dịch" in prompt.lower() or "Không có giao dịch" in prompt

    def test_includes_risk_level(self):
        """Prompt includes current risk level."""
        prompt = build_review_prompt([], [], [], risk_level=4, goal_progress=None)
        assert "4" in prompt


# ── Parse Review Response Tests ──────────────────────────────────────────────


class TestParseReviewResponse:
    """parse_review_response handles valid, None, and malformed data."""

    def test_valid_response(self):
        """Properly structured response passes through."""
        data = {
            "summary_text": "Tuần này bạn đã giao dịch tốt.",
            "highlights": {"good": ["Kỷ luật tốt"], "bad": ["Chốt lời sớm"]},
            "suggestions": ["Giữ vị thế lâu hơn"],
        }
        result = parse_review_response(data)
        assert result["summary_text"] == "Tuần này bạn đã giao dịch tốt."
        assert result["highlights"]["good"] == ["Kỷ luật tốt"]
        assert result["highlights"]["bad"] == ["Chốt lời sớm"]
        assert result["suggestions"] == ["Giữ vị thế lâu hơn"]

    def test_none_response_fallback(self):
        """None response returns Vietnamese fallback."""
        result = parse_review_response(None)
        assert "Không thể tạo nhận xét" in result["summary_text"]
        assert result["highlights"] == {"good": [], "bad": []}
        assert result["suggestions"] == []

    def test_malformed_response_fallback(self):
        """Non-dict response returns fallback."""
        result = parse_review_response("invalid string")
        assert "Không thể tạo nhận xét" in result["summary_text"]
        assert result["highlights"] == {"good": [], "bad": []}

    def test_missing_highlights_keys(self):
        """Response with partial highlights gets filled."""
        data = {
            "summary_text": "Tuần tốt.",
            "highlights": {"good": ["Tốt"]},  # Missing "bad" key
            "suggestions": [],
        }
        result = parse_review_response(data)
        assert result["highlights"]["good"] == ["Tốt"]
        assert result["highlights"]["bad"] == []

    def test_missing_all_optional_fields(self):
        """Response with only summary_text still works."""
        data = {"summary_text": "Bản nhận xét."}
        result = parse_review_response(data)
        assert result["summary_text"] == "Bản nhận xét."
        assert result["highlights"] == {"good": [], "bad": []}
        assert result["suggestions"] == []
