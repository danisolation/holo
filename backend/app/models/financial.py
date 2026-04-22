from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, String, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class Financial(Base):
    """Financial ratios and metrics per ticker per period.

    Data sourced from vnstock finance.ratio() which returns P/E, P/B, EPS,
    ROE, ROA, growth rates, and health indicators.
    """
    __tablename__ = "financials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    period: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # e.g., 'Q1-2025', 'Q2-2024', 'Y-2024'
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # NULL for annual

    # Valuation
    pe: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    pb: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    eps: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Profitability
    roe: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    roa: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # Growth
    revenue_growth: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    profit_growth: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # Financial health
    current_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    debt_to_equity: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("ticker_id", "period", name="uq_financials_ticker_period"),
    )

    def __repr__(self) -> str:
        return f"<Financial(ticker_id={self.ticker_id}, period={self.period}, pe={self.pe})>"
