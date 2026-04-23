"""HabitDetection model — stores detected trading habit patterns.

Records instances of premature profit-taking, holding losers,
and impulsive trading detected during weekly batch analysis.
"""
from datetime import datetime

from sqlalchemy import BigInteger, Integer, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class HabitDetection(Base):
    __tablename__ = "habit_detections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    habit_type: Mapped[str] = mapped_column(String(20), nullable=False)  # premature_sell, holding_losers, impulsive_trade
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    trade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("trades.id"), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_habit_detections_type", "habit_type"),
    )

    def __repr__(self) -> str:
        return f"<HabitDetection(id={self.id}, type={self.habit_type}, trade_id={self.trade_id})>"
