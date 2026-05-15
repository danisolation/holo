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


# --- Phase 103: AI Sector Intelligence schemas ---

class SectorStrengthItem(BaseModel):
    """Single sector AI analysis result."""
    sector: str
    strength: str  # "strong" | "neutral" | "weak"
    trend: str  # "improving" | "stable" | "declining"
    money_flow: str  # "inflow" | "neutral" | "outflow"
    reasoning: str  # Vietnamese explanation, 2-3 sentences


class SectorRotationTiming(BaseModel):
    """Rotation timing recommendation."""
    attracting: list[str]  # sector names gaining money
    losing: list[str]  # sector names losing money
    recommendation: str  # Vietnamese rotation advice, 3-5 sentences


class SectorIntelligenceResponse(BaseModel):
    """Gemini structured output for sector intelligence."""
    market_sentiment: str  # overall market sentiment summary (Vietnamese)
    sectors: list[SectorStrengthItem]
    rotation: SectorRotationTiming
    top_strong: list[str]  # top 3 strongest sector names
    top_weak: list[str]  # top 3 weakest sector names


class SectorAnalysisAPIResponse(BaseModel):
    """API response wrapping the AI output + metadata."""
    analysis_date: str
    model_version: str
    analysis: SectorIntelligenceResponse
