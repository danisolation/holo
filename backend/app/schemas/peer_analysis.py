"""Pydantic schema for AI peer analysis response.

Phase 106: Structured output from Gemini comparing a ticker against sector peers.
Also used as Gemini response_schema for structured output.
"""
from pydantic import BaseModel


class PeerAnalysisResponse(BaseModel):
    """AI-generated peer analysis — all fields in Vietnamese."""
    symbol: str
    sector: str
    overall_verdict: str       # e.g. "Vượt trội so với ngành" or "Thua kém ngành"
    strengths: list[str]       # Vietnamese bullet points where ticker outperforms
    weaknesses: list[str]      # Vietnamese bullet points where ticker underperforms
    peer_position: str         # Vietnamese paragraph on relative standing
    recommendation: str        # Vietnamese actionable suggestion
