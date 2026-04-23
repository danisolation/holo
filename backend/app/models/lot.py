"""Lot model — tracks buy-side share lots for FIFO P&L matching.

Each BUY trade creates one lot. SELL trades consume lots oldest-first.
remaining_quantity tracks how many shares are still open (not yet sold).
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Integer, Date, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class Lot(Base):
    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("trades.id"), nullable=False)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    buy_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    buy_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Lot(id={self.id}, ticker_id={self.ticker_id}, remaining={self.remaining_quantity}/{self.quantity})>"
