from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, BigInteger, Numeric, String, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class IntradayPrice(Base):
    """Intraday price snapshot captured every poll interval.

    Each row is one price observation for one symbol at one point in time.
    Prices are in nghìn đồng (×1000 VND): e.g. 9.97 = 9,970 VND.
    """
    __tablename__ = "intraday_prices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    day_high: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    day_low: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    change: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True, default=0)
    change_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=True, default=0)
    recorded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_intraday_symbol_recorded", "symbol", "recorded_at"),
        Index("ix_intraday_ticker_recorded", "ticker_id", "recorded_at"),
    )

    def __repr__(self) -> str:
        return f"<IntradayPrice(symbol={self.symbol}, price={self.price}, recorded_at={self.recorded_at})>"
