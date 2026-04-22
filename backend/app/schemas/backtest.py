"""Pydantic schemas for backtest API endpoints."""
from datetime import date
from pydantic import BaseModel, Field, model_validator, computed_field

from app.schemas.trade import TradeBaseResponse


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


class BacktestTradeResponse(TradeBaseResponse):
    """Response for a single backtest trade — adds run_id and backtest_analysis_id."""
    run_id: int
    backtest_analysis_id: int | None = None


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


# --- Analytics Response Schemas (Phase 33) ---

class PerformanceSummaryResponse(BaseModel):
    """BENCH-02: Core performance metrics."""
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    avg_pnl_per_trade: float


class BenchmarkPointResponse(BaseModel):
    """Single data point in benchmark comparison time-series."""
    date: str
    ai_equity: float
    ai_return_pct: float
    vnindex_return_pct: float | None = None


class BenchmarkComparisonResponse(BaseModel):
    """BENCH-01: AI strategy vs VN-Index buy-and-hold."""
    initial_capital: float
    ai_total_return_pct: float
    vnindex_total_return_pct: float | None = None
    outperformance_pct: float | None = None
    data: list[BenchmarkPointResponse]


class SectorBreakdownResponse(BaseModel):
    """BENCH-03: Per-sector performance stats."""
    sector: str
    total_trades: int
    wins: int
    win_rate: float
    total_pnl: float
    avg_pnl: float


class ConfidenceBreakdownResponse(BaseModel):
    """BENCH-04: Per-confidence-bucket stats."""
    bracket: str
    total_trades: int
    wins: int
    win_rate: float
    avg_pnl: float
    avg_pnl_pct: float


class TimeframeBreakdownResponse(BaseModel):
    """BENCH-05: Per-holding-period-bucket stats."""
    bucket: str
    total_trades: int
    wins: int
    win_rate: float
    avg_holding_days: float
    total_pnl: float
    avg_pnl: float


class BacktestAnalyticsResponse(BaseModel):
    """Combined analytics response for GET /runs/{id}/analytics."""
    run_id: int
    summary: PerformanceSummaryResponse
    sectors: list[SectorBreakdownResponse]
    confidence: list[ConfidenceBreakdownResponse]
    timeframes: list[TimeframeBreakdownResponse]
