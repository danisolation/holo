"""Pydantic schemas for behavior tracking API endpoints."""
from pydantic import BaseModel, Field


class BehaviorEventCreate(BaseModel):
    """POST /api/behavior/event request body."""
    event_type: str = Field(..., pattern=r"^(ticker_view|search_click|pick_click)$")
    ticker_symbol: str | None = None  # Resolved to ticker_id in API layer
    metadata: dict | None = None


class ViewingStatItem(BaseModel):
    """Single ticker in viewing stats."""
    ticker_symbol: str
    sector: str | None
    view_count: int
    last_viewed: str


class ViewingStatsResponse(BaseModel):
    """GET /api/behavior/viewing-stats response."""
    items: list[ViewingStatItem]
    total_views: int


class HabitDetectionItem(BaseModel):
    """Single habit type with aggregated count."""
    habit_type: str  # "premature_sell" | "holding_losers" | "impulsive_trade"
    count: int
    latest_ticker: str | None
    latest_date: str | None


class HabitDetectionsResponse(BaseModel):
    """GET /api/behavior/habits response."""
    habits: list[HabitDetectionItem]
    analysis_date: str | None


class SectorPreferenceItem(BaseModel):
    """Single sector performance data."""
    sector: str
    total_trades: int
    win_count: int
    loss_count: int
    net_pnl: float
    win_rate: float
    preference_score: float


class SectorPreferencesResponse(BaseModel):
    """GET /api/behavior/sector-preferences response."""
    sectors: list[SectorPreferenceItem]
    insufficient_count: int  # Sectors with < 3 trades


class RiskSuggestionResponse(BaseModel):
    """GET /api/behavior/risk-suggestion response."""
    id: int
    current_level: int
    suggested_level: int
    reason: str
    status: str
    created_at: str


class RiskSuggestionRespondRequest(BaseModel):
    """POST /api/behavior/risk-suggestion/{id}/respond request body."""
    action: str = Field(..., pattern=r"^(accept|reject)$")
