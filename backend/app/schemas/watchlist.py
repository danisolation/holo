"""Pydantic schemas for watchlist API endpoints."""
from pydantic import BaseModel, Field


class WatchlistItemResponse(BaseModel):
    """Single watchlist item with optional AI signal enrichment."""
    symbol: str
    created_at: str
    sector_group: str | None = None
    ai_signal: str | None = None      # e.g. "buy", "sell", "hold"
    ai_score: int | None = None        # 1-10
    signal_date: str | None = None     # ISO date of the signal
    last_analysis_at: str | None = None  # Phase 58: ISO timestamp of most recent AI analysis


class WatchlistUpdateRequest(BaseModel):
    """PATCH /api/watchlist/{symbol} request body."""
    sector_group: str | None = Field(None, max_length=100)


class WatchlistAddRequest(BaseModel):
    """POST /api/watchlist request body."""
    symbol: str = Field(min_length=1, max_length=10, description="Ticker symbol to add")
    sector_group: str | None = Field(None, max_length=100)


class WatchlistMigrateRequest(BaseModel):
    """POST /api/watchlist/migrate — bulk add from localStorage migration."""
    symbols: list[str] = Field(max_length=50, description="List of ticker symbols to migrate")
