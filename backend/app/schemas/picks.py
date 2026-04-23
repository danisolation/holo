"""Pydantic schemas for daily picks API endpoints."""
from pydantic import BaseModel, Field


class DailyPickResponse(BaseModel):
    """Single pick or almost-selected ticker."""
    pick_date: str
    ticker_symbol: str
    ticker_name: str
    rank: int | None
    composite_score: float
    entry_price: float | None
    stop_loss: float | None
    take_profit_1: float | None
    take_profit_2: float | None
    risk_reward: float | None
    position_size_shares: int | None
    position_size_vnd: int | None
    position_size_pct: float | None
    explanation: str | None
    status: str  # "picked" or "almost"
    rejection_reason: str | None


class DailyPicksResponse(BaseModel):
    """Full response for GET /api/picks/today."""
    date: str
    capital: int
    picks: list[DailyPickResponse]
    almost_selected: list[DailyPickResponse]


class ProfileResponse(BaseModel):
    """User risk profile."""
    capital: int
    risk_level: int = Field(ge=1, le=5)
    broker_fee_pct: float


class ProfileUpdate(BaseModel):
    """PUT /api/profile request body."""
    capital: int = Field(gt=0, description="Investment capital in VND, must be positive")
    risk_level: int = Field(ge=1, le=5, description="Risk level 1-5")
