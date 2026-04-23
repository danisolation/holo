"""Shared trade response schema used by the paper-trading module."""
from pydantic import BaseModel


class TradeBaseResponse(BaseModel):
    """Common fields for all trade responses."""
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
