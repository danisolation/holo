"""FIFO lot tracking for portfolio cost basis.

Each BUY trade creates a lot. SELL trades consume lots oldest-first
by decrementing remaining_quantity. Per D-08-02.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Integer, BigInteger, Numeric, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class Lot(Base):
    """A FIFO lot created from a BUY trade."""

    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("trades.id"), nullable=False
    )
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    buy_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    buy_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Lot(id={self.id}, remaining={self.remaining_quantity}/{self.quantity}, price={self.buy_price})>"
