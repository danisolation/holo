"""Web watchlist — single-user, stores ticker symbols directly.

No chat_id or ticker FK needed. Symbol stored as uppercase string (max 10 chars).
"""
from datetime import datetime

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class UserWatchlist(Base):
    """Watchlist entry storing a ticker symbol for the web dashboard."""
    __tablename__ = "user_watchlist"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    sector_group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<UserWatchlist(symbol={self.symbol})>"
