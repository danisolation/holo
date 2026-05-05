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
