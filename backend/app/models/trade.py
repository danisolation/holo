"""Trade log for personal portfolio tracking.

Single table for both BUY and SELL trades per D-08-01.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Integer, BigInteger, String, Numeric, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class Trade(Base):
    """A buy or sell trade recorded by the user."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # BUY or SELL
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fees: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, side={self.side}, qty={self.quantity}, price={self.price})>"
