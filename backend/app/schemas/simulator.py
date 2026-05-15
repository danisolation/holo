"""Pydantic schemas for simulator API."""
from datetime import date
from pydantic import BaseModel, Field


class SimulatorTradeCreate(BaseModel):
    """POST /api/simulator/trades request body."""
    ticker_symbol: str = Field(..., description="Ticker symbol e.g. VNM")
    side: str = Field(..., pattern=r"^(BUY|SELL)$")
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    trade_date: date
    source: str = Field(default="manual", pattern=r"^(ai_auto|manual)$")
    daily_pick_id: int | None = None
    user_notes: str | None = Field(None, max_length=500)
    portfolio_type: str = Field(default="user", pattern=r"^(ai|user)$")


class SimulatorTradeResponse(BaseModel):
    """Single simulator trade response."""
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
    source: str
    ai_signal_skipped: bool
    user_notes: str | None
    created_at: str
    rationale: str | None = None


class PositionResponse(BaseModel):
    """Single open position."""
    ticker_symbol: str
    ticker_name: str
    quantity: int
    avg_price: float
    current_price: float | None
    market_value: float | None
    unrealized_pnl: float | None
    unrealized_pnl_pct: float | None


class PortfolioResponse(BaseModel):
    """Full portfolio state."""
    starting_capital: float
    current_cash: float
    total_market_value: float
    total_equity: float
    total_pnl: float
    total_pnl_pct: float
    realized_pnl: float
    unrealized_pnl: float
    positions: list[PositionResponse]


class SimulatorTradesListResponse(BaseModel):
    """Paginated trades list."""
    trades: list[SimulatorTradeResponse]
    total: int
    page: int
    page_size: int


class SimulatorStatsResponse(BaseModel):
    """AI accuracy and performance stats."""
    total_trades: int
    ai_trades: int
    manual_trades: int
    ai_win_rate: float  # percentage
    manual_win_rate: float
    ai_avg_return_pct: float
    manual_avg_return_pct: float
    ai_total_pnl: float
    manual_total_pnl: float


class PortfolioResetResponse(BaseModel):
    """Response after portfolio reset."""
    message: str
    starting_capital: float
    current_cash: float


class PendingSignalResponse(BaseModel):
    """A daily pick signal pending execution."""
    daily_pick_id: int
    pick_date: str
    ticker_symbol: str
    ticker_name: str
    entry_price: float | None
    stop_loss: float | None
    take_profit_1: float | None
    composite_score: float
    rank: int | None
    position_size_shares: int | None
    explanation: str | None = None


class ExecuteSignalsRequest(BaseModel):
    """Request to execute specific AI signals."""
    pick_ids: list[int] = Field(..., min_length=1)


# ── Phase 98-02: Equity History & P&L Timeline ──────────────────────────────


class EquityHistoryPoint(BaseModel):
    """Single point on the equity curve."""
    date: str
    equity: float  # total portfolio value (cash + market value) in VND


class EquityHistoryResponse(BaseModel):
    """Equity curve over time."""
    history: list[EquityHistoryPoint]
    starting_capital: float


class PnlTimelineEntry(BaseModel):
    """Single trade entry in P&L timeline."""
    id: int
    trade_date: str
    ticker_symbol: str
    side: str
    quantity: int
    price: float
    net_pnl: float | None
    cumulative_pnl: float
    source: str


class PnlTimelineResponse(BaseModel):
    """All trades with running cumulative P&L."""
    entries: list[PnlTimelineEntry]
    total_realized_pnl: float


# ── Phase 107: Dual Portfolio Schemas ────────────────────────────────────────


class PortfolioSummaryItem(BaseModel):
    """Summary of a single portfolio."""
    name: str
    starting_capital: float
    current_cash: float
    total_equity: float
    total_pnl: float
    total_pnl_pct: float
    position_count: int


class PortfolioListResponse(BaseModel):
    """List of all portfolios."""
    portfolios: list[PortfolioSummaryItem]
