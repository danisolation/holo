"""Discovery results — daily scored tickers for stock discovery.

One row per ticker per date. Scores on 6 dimensions (0-10 scale each).
Composite total_score is average of non-NULL dimensions.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Integer, BigInteger, Numeric, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class DiscoveryResult(Base):
    """Daily discovery score for a ticker across 6 indicator dimensions."""
    __tablename__ = "discovery_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    score_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Per-dimension scores (0-10 scale, NULL if data unavailable)
    rsi_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    macd_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    adx_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    volume_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    pe_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    roe_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)

    # Composite score (average of available dimensions)
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    # How many dimensions were scoreable (2-6)
    dimensions_scored: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("ticker_id", "score_date", name="uq_discovery_results_ticker_date"),
    )

    def __repr__(self) -> str:
        return f"<DiscoveryResult(ticker_id={self.ticker_id}, date={self.score_date}, score={self.total_score})>"
