"""Pydantic schemas for watchlist API endpoints."""
from pydantic import BaseModel, Field


class WatchlistItemResponse(BaseModel):
    """Single watchlist item with optional AI signal enrichment."""
    symbol: str
    created_at: str
    ai_signal: str | None = None      # e.g. "buy", "sell", "hold"
    ai_score: int | None = None        # 1-10
    signal_date: str | None = None     # ISO date of the signal


class WatchlistAddRequest(BaseModel):
    """POST /api/watchlist request body."""
    symbol: str = Field(min_length=1, max_length=10, description="Ticker symbol to add")


class WatchlistMigrateRequest(BaseModel):
    """POST /api/watchlist/migrate — bulk add from localStorage migration."""
    symbols: list[str] = Field(max_length=50, description="List of ticker symbols to migrate")
