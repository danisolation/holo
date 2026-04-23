"""WeeklyReview model — AI-generated weekly performance review.

Generated every Sunday 21:00 via Gemini. Contains Vietnamese narrative,
structured highlights (good/bad habits), and improvement suggestions.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Integer, String, Text, Date, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    highlights: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {"good": [...], "bad": [...]}
    suggestions: Mapped[list] = mapped_column(JSONB, nullable=False)  # [...]
    trades_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    win_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<WeeklyReview(id={self.id}, week={self.week_start}-{self.week_end}, trades={self.trades_count})>"
