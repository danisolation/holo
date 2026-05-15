"""Pydantic schemas for screener, peer comparison, and sector detail endpoints.

Three endpoints:
1. Screener — filtered/sorted/paginated ticker list with metrics
2. Peer Comparison — ranked metrics for all tickers in same sector
3. Sector Detail — all tickers in a sector with 7D/30D performance
"""
from pydantic import BaseModel


class ScreenerTickerItem(BaseModel):
    """Single ticker in screener results."""
    symbol: str
    name: str
    sector: str | None = None
    industry: str | None = None
    close: float | None = None
    volume: int | None = None
    change_1d: float | None = None   # % change vs prev close
    change_7d: float | None = None
    change_30d: float | None = None
    pe: float | None = None          # from Financial table, nullable
    market_cap: float | None = None


class ScreenerResponse(BaseModel):
    """Paginated screener results."""
    items: list[ScreenerTickerItem]
    total: int
    offset: int
    limit: int


class PeerComparisonItem(BaseModel):
    """Single peer in comparison."""
    symbol: str
    name: str
    close: float | None = None
    volume: int | None = None
    change_1d: float | None = None
    pe: float | None = None
    market_cap: float | None = None
    rank_pe: int | None = None
    rank_volume: int | None = None
    rank_change: int | None = None
    rank_market_cap: int | None = None
    is_target: bool = False  # True for the queried ticker


class PeerComparisonResponse(BaseModel):
    """Peer comparison results."""
    symbol: str
    sector: str
    peers: list[PeerComparisonItem]


class SectorDetailTickerItem(BaseModel):
    """Single ticker in sector detail."""
    symbol: str
    name: str
    industry: str | None = None
    close: float | None = None
    volume: int | None = None
    change_7d: float | None = None
    change_30d: float | None = None
    market_cap: float | None = None


class SectorDetailResponse(BaseModel):
    """Sector detail results."""
    sector: str
    ticker_count: int
    tickers: list[SectorDetailTickerItem]
