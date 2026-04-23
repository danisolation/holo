"""Pydantic schemas for daily picks API endpoints."""
from pydantic import BaseModel, Field


class DailyPickResponse(BaseModel):
    """Single pick or almost-selected ticker."""
    id: int
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


# ── Phase 45: Pick history + performance schemas ─────────────────────────────


class PickHistoryItem(BaseModel):
    """Single pick in history with outcome tracking."""
    id: int
    pick_date: str
    ticker_symbol: str
    rank: int | None
    entry_price: float | None
    stop_loss: float | None
    take_profit_1: float | None
    pick_outcome: str  # "pending" | "winner" | "loser" | "expired"
    actual_return_pct: float | None
    days_held: int | None
    has_trades: bool


class PickHistoryListResponse(BaseModel):
    """Paginated pick history response."""
    items: list[PickHistoryItem]
    total: int
    page: int
    per_page: int


class PickPerformanceResponse(BaseModel):
    """Aggregated performance metrics for performance cards."""
    win_rate: float  # percentage e.g. 68.5
    total_pnl: float  # VND, realized from linked trades
    avg_risk_reward: float  # e.g. 2.4
    current_streak: int  # positive = wins, negative = losses
    total_closed: int
    total_winners: int
    total_losers: int
