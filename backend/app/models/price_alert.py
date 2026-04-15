"""Price alert configuration for Telegram bot notifications.

User sets a target price and direction; alert fires when price crosses threshold.
Once triggered, is_triggered=True prevents repeat notifications.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, BigInteger, String, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class PriceAlert(Base):
    """Price threshold alert for a ticker."""
    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(String(50), nullable=False)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    target_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    direction: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # "up" or "down"
    is_triggered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    triggered_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<PriceAlert(chat_id={self.chat_id}, ticker_id={self.ticker_id}, target={self.target_price} {self.direction})>"
