"""Pydantic schemas for portfolio API endpoints."""
from datetime import date

from pydantic import BaseModel, Field


class TradeRequest(BaseModel):
    """POST /api/portfolio/trades request body."""

    symbol: str = Field(..., min_length=1, max_length=10, description="Ticker symbol e.g. VNM")
    side: str = Field(..., pattern="^(BUY|SELL)$", description="Trade side: BUY or SELL")
    quantity: int = Field(..., gt=0, description="Number of shares")
    price: float = Field(..., gt=0, description="Price per share in VND")
    trade_date: date = Field(..., description="Date of trade")
    fees: float = Field(default=0, ge=0, description="Total fees in VND (default 0)")


class TradeResponse(BaseModel):
    """Trade record returned from API."""

    id: int
    symbol: str
    side: str
    quantity: int
    price: float
    fees: float
    trade_date: str
    created_at: str
    realized_pnl: float | None = None


class HoldingResponse(BaseModel):
    """Single holding position with P&L."""

    symbol: str
    name: str
    quantity: int
    avg_cost: float
    market_price: float | None = None
    market_value: float | None = None
    total_cost: float
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None


class PortfolioSummaryResponse(BaseModel):
    """Aggregated portfolio summary."""

    total_invested: float
    total_market_value: float | None = None
    total_realized_pnl: float
    total_unrealized_pnl: float | None = None
    total_return_pct: float | None = None
    holdings_count: int


class TradeHistoryResponse(BaseModel):
    """Paginated trade history."""

    trades: list[TradeResponse]
    total: int
