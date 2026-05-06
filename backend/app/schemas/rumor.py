"""Pydantic schemas for Gemini rumor scoring structured output.

These serve dual purpose:
1. Gemini response_schema — constrains LLM output to valid JSON
2. Internal validation — ensures scores within 1-10 range, direction enum

Per RESEARCH.md: Gemini accepts Pydantic BaseModel classes directly
in GenerateContentConfig(response_schema=...) and returns validated
models via response.parsed.
"""
from enum import Enum
from pydantic import BaseModel, Field


class RumorDirection(str, Enum):
    """Directional classification for rumor sentiment."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class TickerRumorScore(BaseModel):
    """Gemini response for one ticker's rumor assessment."""
    ticker: str
    credibility_score: int = Field(ge=1, le=10, description="Độ tin cậy 1-10")
    impact_score: int = Field(ge=1, le=10, description="Mức tác động 1-10")
    direction: RumorDirection
    key_claims: list[str] = Field(description="Danh sách các tuyên bố chính rút trích từ tin đồn")
    reasoning: str = Field(description="Giải thích bằng tiếng Việt về đánh giá")


class RumorBatchResponse(BaseModel):
    """Batch response for rumor scoring (one entry per ticker)."""
    scores: list[TickerRumorScore]


# --- API Response Schemas ---

class RumorPostResponse(BaseModel):
    """Single rumor post in the feed (from Fireant community)."""
    content: str
    author_name: str
    is_authentic: bool
    total_likes: int
    total_replies: int
    posted_at: str


class RumorScoreResponse(BaseModel):
    """Ticker detail response: latest rumor score + recent posts.

    All score fields are Optional because a ticker may have posts but
    no score yet (or no rumor data at all).
    """
    symbol: str
    scored_date: str | None = None
    credibility_score: int | None = None
    impact_score: int | None = None
    direction: str | None = None
    key_claims: list[str] = []
    reasoning: str | None = None
    posts: list[RumorPostResponse] = []
    posts_total: int | None = None


class WatchlistRumorSummary(BaseModel):
    """Watchlist badge data: aggregated rumor stats per ticker (last 7 days)."""
    symbol: str
    rumor_count: int
    avg_credibility: float | None = None
    avg_impact: float | None = None
    dominant_direction: str | None = None


class PaginatedRumorSummaryResponse(BaseModel):
    """Paginated rumor summary response."""
    items: list[WatchlistRumorSummary]
    total: int
    page: int
    per_page: int
