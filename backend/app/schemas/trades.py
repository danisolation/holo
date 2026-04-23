"""Pydantic schemas for trade journal API endpoints."""
from datetime import date

from pydantic import BaseModel, Field


class TradeCreate(BaseModel):
    """POST /api/trades request body."""
    ticker_symbol: str = Field(..., description="Ticker symbol e.g. VNM")
    side: str = Field(..., pattern=r"^(BUY|SELL)$")
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    trade_date: date
    user_notes: str | None = Field(None, max_length=500)
    daily_pick_id: int | None = None
    broker_fee_override: float | None = Field(None, ge=0)
    sell_tax_override: float | None = Field(None, ge=0)


class TradeResponse(BaseModel):
    """Single trade response with ticker info and P&L."""
    id: int
    ticker_symbol: str
    ticker_name: str
    daily_pick_id: int | None
    side: str
    quantity: int
    price: float
    broker_fee: float
    sell_tax: float
    total_fee: float
    gross_pnl: float | None
    net_pnl: float | None
    trade_date: str
    user_notes: str | None
    created_at: str


class TradeStatsResponse(BaseModel):
    """Aggregated trade statistics."""
    total_trades: int
    realized_gross_pnl: float
    realized_net_pnl: float
    open_positions: int  # count of tickers with remaining lots > 0


class TradesListResponse(BaseModel):
    """Paginated trades list response."""
    trades: list[TradeResponse]
    total: int
    page: int
    page_size: int
