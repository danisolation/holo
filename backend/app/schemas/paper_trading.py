"""Pydantic schemas for paper trading API endpoints."""
from pydantic import BaseModel, Field


# --- Trade Response ---
class PaperTradeResponse(BaseModel):
    id: int
    symbol: str
    direction: str
    status: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    adjusted_stop_loss: float | None = None
    quantity: int
    closed_quantity: int
    realized_pnl: float | None = None
    realized_pnl_pct: float | None = None
    exit_price: float | None = None
    partial_exit_price: float | None = None
    signal_date: str
    entry_date: str | None = None
    closed_date: str | None = None
    confidence: int
    timeframe: str
    position_size_pct: int
    risk_reward_ratio: float
    created_at: str


class PaperTradeListResponse(BaseModel):
    trades: list[PaperTradeResponse]
    total: int


# --- Manual Follow Request (PT-09) ---
class ManualFollowRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    direction: str = Field(..., pattern="^(long|bearish)$")
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit_1: float = Field(..., gt=0)
    take_profit_2: float = Field(..., gt=0)
    timeframe: str = Field(..., pattern="^(swing|position)$")
    confidence: int = Field(..., ge=1, le=10)
    position_size_pct: int = Field(..., ge=1, le=100)


# --- Config ---
class SimulationConfigResponse(BaseModel):
    initial_capital: float
    auto_track_enabled: bool
    min_confidence_threshold: int


class SimulationConfigUpdateRequest(BaseModel):
    initial_capital: float | None = Field(None, gt=0)
    auto_track_enabled: bool | None = None
    min_confidence_threshold: int | None = Field(None, ge=1, le=10)
