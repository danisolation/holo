"""Pydantic schemas for goals, weekly prompts, and weekly reviews API."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    """POST /api/goals request body."""
    target_pnl: float = Field(gt=0, le=1_000_000_000, description="Monthly profit target in VND")


class GoalResponse(BaseModel):
    """Single goal with computed progress."""
    id: int
    target_pnl: float
    actual_pnl: float
    month: date
    status: str
    progress_pct: float
    progress_color: str
    created_at: datetime
    updated_at: datetime


class GoalHistoryResponse(BaseModel):
    """GET /api/goals/history response."""
    goals: list[GoalResponse]
    total: int


class WeeklyPromptResponse(BaseModel):
    """GET /api/goals/weekly-prompt response."""
    id: int
    week_start: date
    prompt_type: str
    response: str | None
    risk_level_before: int | None
    risk_level_after: int | None
    created_at: datetime


class WeeklyPromptRespondRequest(BaseModel):
    """POST /api/goals/weekly-prompt/{id}/respond request body."""
    response: Literal["cautious", "unchanged", "aggressive"]


class WeeklyReviewResponse(BaseModel):
    """Single weekly review."""
    id: int
    week_start: date
    week_end: date
    summary_text: str
    highlights: dict  # {"good": [...], "bad": [...]}
    suggestions: list[str]
    trades_count: int
    win_count: int
    total_pnl: float
    created_at: datetime


class WeeklyReviewHistoryResponse(BaseModel):
    """GET /api/goals/weekly-reviews response."""
    reviews: list[WeeklyReviewResponse]
    total: int
