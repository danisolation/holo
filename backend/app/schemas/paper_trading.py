"""Pydantic schemas for paper trading API endpoints."""
from pydantic import BaseModel, Field

from app.schemas.trade import TradeBaseResponse


# --- Trade Response ---
class PaperTradeResponse(TradeBaseResponse):
    """Paper trade response — inherits all fields from TradeBaseResponse."""
    pass


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


# --- Analytics Responses (AN-01 through AN-04) ---

class AnalyticsSummaryResponse(BaseModel):
    """AN-01, AN-02: Overall win rate + total P&L."""
    total_trades: int
    wins: int
    losses: int
    win_rate: float          # percentage (0-100)
    total_pnl: float         # VND
    total_pnl_pct: float     # % of initial capital
    avg_pnl_per_trade: float # VND


class EquityCurvePoint(BaseModel):
    """AN-03: Single point on equity curve."""
    date: str
    daily_pnl: float
    cumulative_pnl: float


class EquityCurveResponse(BaseModel):
    data: list[EquityCurvePoint]
    initial_capital: float


class DrawdownPeriod(BaseModel):
    start: str
    end: str | None = None
    drawdown_vnd: float


class DrawdownResponse(BaseModel):
    """AN-04: Max drawdown with periods."""
    max_drawdown_vnd: float
    max_drawdown_pct: float
    current_drawdown_vnd: float
    current_drawdown_pct: float
    periods: list[DrawdownPeriod]


# --- Breakdown Analytics Responses (AN-05 through AN-09) ---

class DirectionAnalysisItem(BaseModel):
    """AN-05: Performance for one direction (LONG or BEARISH)."""
    direction: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_pnl: float


class ConfidenceBracketItem(BaseModel):
    """AN-06: Performance for one confidence bracket."""
    bracket: str   # "LOW", "MEDIUM", "HIGH"
    total_trades: int
    wins: int
    win_rate: float
    avg_pnl: float
    avg_pnl_pct: float


class RiskRewardResponse(BaseModel):
    """AN-07: R:R achieved vs predicted."""
    avg_predicted_rr: float   # from signal's risk_reward_ratio
    avg_achieved_rr: float    # actual P&L / risk
    trades_above_predicted: int
    trades_below_predicted: int
    total_trades: int


class ProfitFactorResponse(BaseModel):
    """AN-08: Profit factor + expected value."""
    gross_profit: float
    gross_loss: float
    profit_factor: float | None  # None if gross_loss == 0
    expected_value: float         # avg P&L per trade
    total_trades: int


class SectorAnalysisItem(BaseModel):
    """AN-09: Performance by industry sector."""
    sector: str
    total_trades: int
    wins: int
    win_rate: float
    total_pnl: float
    avg_pnl: float


# --- Phase 26: Additional Analytics Schemas ---

class StreakResponse(BaseModel):
    """UI-03: Win/loss streak tracking."""
    current_win_streak: int
    current_loss_streak: int
    longest_win_streak: int
    longest_loss_streak: int
    total_trades: int


class TimeframeComparisonItem(BaseModel):
    """UI-04: Performance for one timeframe (swing or position)."""
    timeframe: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_pnl: float


class PeriodicSummaryItem(BaseModel):
    """UI-06: Performance for one period (week or month)."""
    period: str        # "2025-W03" or "2025-01"
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_rr: float


class CalendarDataPoint(BaseModel):
    """UI-02: Daily P&L aggregate for calendar heatmap."""
    date: str          # "YYYY-MM-DD"
    daily_pnl: float
    trade_count: int
