"""Pydantic schemas for market breadth indicators.

Three market-wide health metrics for HOSE:
1. A/D Line — daily advancing vs declining tickers
2. MA Breadth — % of tickers above MA50 and MA200
3. 52-Week Highs/Lows — daily new high/low counts
"""
from pydantic import BaseModel


class ADLineItem(BaseModel):
    """Single day advance/decline data."""
    date: str  # ISO date string
    advancing: int
    declining: int
    unchanged: int
    net: int  # advancing - declining


class MABreadthItem(BaseModel):
    """Single day MA breadth data."""
    date: str
    total_tickers: int
    above_ma50: int
    above_ma200: int
    pct_above_ma50: float  # 0-100
    pct_above_ma200: float  # 0-100


class HighsLowsItem(BaseModel):
    """Single day 52-week highs/lows data."""
    date: str
    new_highs: int
    new_lows: int


class MarketBreadthResponse(BaseModel):
    """Combined response with all 3 breadth metrics."""
    ad_line: list[ADLineItem]
    ma_breadth: list[MABreadthItem]
    highs_lows: list[HighsLowsItem]
    start_date: str
    end_date: str
