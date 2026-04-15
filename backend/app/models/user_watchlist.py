"""User watchlist for Telegram bot notifications.

Tracks which tickers a user (by chat_id) wants to monitor.
Single-user design per CONTEXT.md — chat_id stored for delivery target.
"""
from datetime import datetime

from sqlalchemy import Integer, BigInteger, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class UserWatchlist(Base):
    """Watchlist entry linking a Telegram chat to a ticker."""
    __tablename__ = "user_watchlist"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(String(50), nullable=False)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("chat_id", "ticker_id", name="uq_user_watchlist_chat_ticker"),
    )

    def __repr__(self) -> str:
        return f"<UserWatchlist(chat_id={self.chat_id}, ticker_id={self.ticker_id})>"
