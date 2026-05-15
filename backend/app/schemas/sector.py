"""Pydantic schemas for sector analysis endpoints.

Two endpoints:
1. Sector Performance — avg % price change per sector for today/7D/30D
2. Sector Flow — net buying/selling volume per sector per day
"""
from pydantic import BaseModel


class SectorPerformanceItem(BaseModel):
    """Single sector performance summary."""
    sector: str
    ticker_count: int
    avg_change_today: float | None = None
    avg_change_7d: float | None = None
    avg_change_30d: float | None = None


class SectorFlowItem(BaseModel):
    """Single sector flow entry (one sector, one day)."""
    sector: str
    date: str  # ISO date string
    net_volume: float
    buy_volume: float
    sell_volume: float
