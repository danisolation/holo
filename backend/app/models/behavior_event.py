"""BehaviorEvent model — logs user viewing/interaction events.

Tracks ticker views, search clicks, and pick card clicks for
behavioral analysis on the coach dashboard.
"""
from datetime import datetime

from sqlalchemy import BigInteger, Integer, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class BehaviorEvent(Base):
    __tablename__ = "behavior_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)  # ticker_view, search_click, pick_click
    ticker_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_behavior_events_type_ticker", "event_type", "ticker_id"),
    )

    def __repr__(self) -> str:
        return f"<BehaviorEvent(id={self.id}, type={self.event_type}, ticker_id={self.ticker_id})>"
