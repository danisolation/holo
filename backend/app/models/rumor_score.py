"""AI-generated rumor scores per ticker per day.

One row per (ticker_id, scored_date) — stores Gemini's credibility/impact
assessment of community rumors for that ticker on that date.
"""
from datetime import date, datetime

from sqlalchemy import (
    Integer, BigInteger, String, Text, Date, ForeignKey,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func, text
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB

from app.models import Base


class RumorScore(Base):
    """Gemini rumor credibility/impact score for a ticker on a given date."""
    __tablename__ = "rumor_scores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    scored_date: Mapped[date] = mapped_column(Date, nullable=False)
    credibility_score: Mapped[int] = mapped_column(Integer, nullable=False)
    impact_score: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    key_claims: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    post_ids: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("ticker_id", "scored_date", name="uq_rumor_scores_ticker_date"),
        Index("ix_rumor_scores_ticker_date", "ticker_id", text("scored_date DESC")),
    )

    def __repr__(self) -> str:
        return f"<RumorScore(ticker_id={self.ticker_id}, date={self.scored_date})>"
