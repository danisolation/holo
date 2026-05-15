"""Pydantic schemas for AI-powered simulator review responses.

Phase 109: Gemini-generated portfolio and trade reviews in Vietnamese.
"""
from pydantic import BaseModel


class PortfolioReviewResponse(BaseModel):
    """Gemini portfolio review — Vietnamese structured output."""
    overall_assessment: str        # Vietnamese paragraph: tổng quan danh mục
    strengths: list[str]           # Vietnamese bullet points: điểm mạnh
    weaknesses: list[str]          # Vietnamese bullet points: điểm yếu
    suggestions: list[str]         # Vietnamese bullet points: gợi ý cải thiện
    risk_assessment: str           # Vietnamese paragraph: đánh giá rủi ro
    score: int                     # 1-10 overall portfolio health


class TradeReviewResponse(BaseModel):
    """Gemini single trade review — Vietnamese structured output."""
    entry_analysis: str            # Was entry timing/price good?
    exit_analysis: str             # Was exit timing/price good?
    what_went_well: list[str]      # Bullet points
    what_could_improve: list[str]  # Bullet points
    pattern_identified: str        # Chart pattern or behavior identified
    overall_verdict: str           # "Tốt" / "Trung bình" / "Cần cải thiện"
