"""Pydantic schemas for backtest API endpoints."""
from datetime import date
from pydantic import BaseModel, Field, model_validator, computed_field


# --- Request Schemas ---

class BacktestStartRequest(BaseModel):
    """Request to start a new backtest run."""
    start_date: date
    end_date: date
    initial_capital: float = Field(default=100_000_000, gt=0)
    slippage_pct: float = Field(default=0.5, ge=0.0, le=5.0)

    @model_validator(mode="after")
    def validate_date_range(self) -> "BacktestStartRequest":
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        delta = (self.end_date - self.start_date).days
        if delta < 20:
            raise ValueError("Date range must be at least 1 month (~20 trading days)")
        if delta > 180:
            raise ValueError("Date range must be at most 6 months (~180 days)")
        return self


# --- Response Schemas ---

class BacktestRunResponse(BaseModel):
    """Response for a backtest run with progress tracking."""
    id: int
    start_date: str
    end_date: str
    initial_capital: float
    slippage_pct: float
    status: str
    last_completed_date: str | None = None
    total_sessions: int
    completed_sessions: int
    is_cancelled: bool
    created_at: str
    updated_at: str

    @computed_field
    @property
    def progress_pct(self) -> float:
        if self.total_sessions > 0:
            return round(self.completed_sessions / self.total_sessions * 100, 1)
        return 0.0


class BacktestTradeResponse(BaseModel):
    """Response for a single backtest trade."""
    id: int
    run_id: int
    symbol: str
    backtest_analysis_id: int | None = None
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


class BacktestEquityResponse(BaseModel):
    """Response for a single equity snapshot."""
    run_id: int
    date: str
    cash: float
    positions_value: float
    total_equity: float
    daily_return_pct: float | None = None
    cumulative_return_pct: float | None = None


class BacktestTradeListResponse(BaseModel):
    """Paginated list of backtest trades."""
    trades: list[BacktestTradeResponse]
    total: int


class BacktestEquityListResponse(BaseModel):
    """List of equity snapshots for a run."""
    equity: list[BacktestEquityResponse]
    total: int
