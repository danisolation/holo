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


class TradeUpdateRequest(BaseModel):
    """PUT /api/portfolio/trades/{id} request body."""

    side: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    trade_date: date
    fees: float = Field(default=0, ge=0)


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
    dividend_income: float = 0
    sector: str | None = None


class PortfolioSummaryResponse(BaseModel):
    """Aggregated portfolio summary."""

    total_invested: float
    total_market_value: float | None = None
    total_realized_pnl: float
    total_unrealized_pnl: float | None = None
    total_return_pct: float | None = None
    holdings_count: int
    dividend_income: float = 0


class TradeHistoryResponse(BaseModel):
    """Paginated trade history."""

    trades: list[TradeResponse]
    total: int


class PerformanceDataPoint(BaseModel):
    """Single data point for portfolio performance chart."""

    date: str
    value: float


class PerformanceResponse(BaseModel):
    """Portfolio performance chart data."""

    data: list[PerformanceDataPoint]
    period: str


class AllocationItem(BaseModel):
    """Single allocation item (ticker or sector)."""

    name: str
    value: float
    percentage: float


class AllocationResponse(BaseModel):
    """Portfolio allocation breakdown."""

    data: list[AllocationItem]
    mode: str
    total_value: float


class CSVPreviewRow(BaseModel):
    """Single row in CSV dry-run preview with validation status."""

    row_number: int
    symbol: str
    side: str
    quantity: int
    price: float
    trade_date: str
    fees: float
    status: str  # "valid", "warning", "error"
    message: str | None = None


class CSVDryRunResponse(BaseModel):
    """CSV dry-run validation result with per-row status and summary."""

    format_detected: str
    rows: list[CSVPreviewRow]
    total_valid: int
    total_warnings: int
    total_errors: int


class CSVImportResponse(BaseModel):
    """Result of CSV import operation."""

    trades_imported: int
    tickers_recalculated: int
