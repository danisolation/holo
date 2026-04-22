from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Integer, BigInteger, Numeric, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class DailyPrice(Base):
    """Daily OHLCV price data. Physical table is partitioned by year in PostgreSQL.

    NOTE: Partitioning is done via raw DDL in Alembic migration.
    SQLAlchemy ORM doesn't natively support PARTITION BY.
    The composite PK (date, id) is required for partition key inclusion.
    """
    __tablename__ = "daily_prices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("ticker_id", "date", name="uq_daily_prices_ticker_date"),
    )

    def __repr__(self) -> str:
        return f"<DailyPrice(ticker_id={self.ticker_id}, date={self.date}, close={self.close})>"
