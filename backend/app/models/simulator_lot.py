"""Simulator lot — FIFO inventory tracking for simulator positions."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Integer, Date, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class SimulatorLot(Base):
    __tablename__ = "simulator_lots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("simulator_portfolios.id"), nullable=False)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    trade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("simulator_trades.id"), nullable=False)
    buy_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    buy_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
