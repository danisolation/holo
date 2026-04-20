"""Technical indicators computed from daily price data.

One row per ticker per date. All indicator columns are nullable
because different indicators have different warm-up periods
(e.g., SMA(200) needs 199 prior data points before producing a value).
NaN from the ta library → NULL in PostgreSQL.
"""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Integer, BigInteger, Numeric, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class TechnicalIndicator(Base):
    """Technical indicators for a ticker on a specific date."""
    __tablename__ = "technical_indicators"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Momentum
    rsi_14: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # Trend — MACD(12, 26, 9)
    macd_line: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    macd_signal: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    macd_histogram: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)

    # Trend — Moving Averages
    sma_20: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    sma_50: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    sma_200: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    ema_12: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    ema_26: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    # Volatility — Bollinger Bands(20, 2)
    bb_upper: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    bb_middle: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    bb_lower: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    # Volatility — ATR(14)
    atr_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    # Trend — ADX(14) with Directional Indicators
    adx_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    plus_di_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    minus_di_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    # Momentum — Stochastic(14, 3)
    stoch_k_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    stoch_d_14: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("ticker_id", "date", name="uq_technical_indicators_ticker_date"),
    )

    def __repr__(self) -> str:
        return f"<TechnicalIndicator(ticker_id={self.ticker_id}, date={self.date}, rsi={self.rsi_14})>"
