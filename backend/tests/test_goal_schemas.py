"""Unit tests for goal schemas — validates Pydantic constraints.

Tests GoalCreate target_pnl validation (gt=0, le=1B) and
WeeklyPromptRespondRequest Literal validation.
"""
import pytest
from pydantic import ValidationError

from app.schemas.goals import GoalCreate, WeeklyPromptRespondRequest


class TestGoalCreate:
    """GoalCreate rejects target_pnl <= 0 and > 1B."""

    def test_accepts_valid_target(self):
        g = GoalCreate(target_pnl=5_000_000)
        assert g.target_pnl == 5_000_000

    def test_rejects_zero(self):
        with pytest.raises(ValidationError):
            GoalCreate(target_pnl=0)

    def test_rejects_negative(self):
        with pytest.raises(ValidationError):
            GoalCreate(target_pnl=-100)

    def test_rejects_above_1b(self):
        with pytest.raises(ValidationError):
            GoalCreate(target_pnl=1_000_000_001)

    def test_accepts_exactly_1b(self):
        g = GoalCreate(target_pnl=1_000_000_000)
        assert g.target_pnl == 1_000_000_000


class TestWeeklyPromptRespondRequest:
    """WeeklyPromptRespondRequest rejects invalid response values."""

    def test_accepts_cautious(self):
        r = WeeklyPromptRespondRequest(response="cautious")
        assert r.response == "cautious"

    def test_accepts_unchanged(self):
        r = WeeklyPromptRespondRequest(response="unchanged")
        assert r.response == "unchanged"

    def test_accepts_aggressive(self):
        r = WeeklyPromptRespondRequest(response="aggressive")
        assert r.response == "aggressive"

    def test_rejects_invalid(self):
        with pytest.raises(ValidationError):
            WeeklyPromptRespondRequest(response="invalid")

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            WeeklyPromptRespondRequest(response="")
