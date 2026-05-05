"""AI accuracy tracking — compares predictions against actual price movements.

One row per ticker per analysis_date. Backfilled daily after market close
for signals from 1/3/7 days ago.
"""
from datetime import date, datetime

from sqlalchemy import Integer, BigInteger, String, Date, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class AIAccuracy(Base):
    """Tracks whether AI combined analysis recommendations were correct."""
    __tablename__ = "ai_accuracy"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    direction_predicted: Mapped[str] = mapped_column(
        String(10), nullable=False  # mua/ban/giu
    )
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    price_at_signal: Mapped[float] = mapped_column(Float, nullable=True)
    price_at_1d: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_at_3d: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_at_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_change_1d: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_change_3d: Mapped[float | None] = mapped_column(Float, nullable=True)
    pct_change_7d: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict_1d: Mapped[str | None] = mapped_column(
        String(20), nullable=True  # correct/incorrect/pending
    )
    verdict_3d: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verdict_7d: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "ticker_id", "analysis_date",
            name="uq_ai_accuracy_ticker_date",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AIAccuracy(ticker_id={self.ticker_id}, date={self.analysis_date}, "
            f"pred={self.direction_predicted}, v1d={self.verdict_1d})>"
        )
