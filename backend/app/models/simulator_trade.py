"""Simulator trade — paper trades with source tracking (ai_auto vs manual)."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Integer, String, Text, Date, Numeric, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class SimulatorTrade(Base):
    __tablename__ = "simulator_trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("simulator_portfolios.id"), nullable=False)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    daily_pick_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("daily_picks.id"), nullable=True)
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # "BUY" or "SELL"
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    broker_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sell_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default="0")
    total_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    gross_pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    net_pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)  # "ai_auto" or "manual"
    ai_signal_skipped: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
