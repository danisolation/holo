"""Corporate events (dividends, stock dividends, bonus shares, rights issues).

Stores events crawled from VNDirect REST API.
Four event types per RESEARCH.md (VN market has no traditional SPLIT):
- CASH_DIVIDEND: Cash dividend in VND per share
- STOCK_DIVIDEND: Stock dividend (ratio per 100 existing shares)
- BONUS_SHARES: Bonus shares (ratio per 100 existing shares)
- RIGHTS_ISSUE: Rights issue (ratio per 100 existing shares, no price adjustment)
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Integer, BigInteger, String, Numeric, Date, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class CorporateEvent(Base):
    """Corporate events crawled from VNDirect API."""

    __tablename__ = "corporate_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    event_source_id: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # VNDirect event "id" field (e.g., "119432.VN") — for deduplication
    event_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # CASH_DIVIDEND, STOCK_DIVIDEND, BONUS_SHARES, RIGHTS_ISSUE
    ex_date: Mapped[date] = mapped_column(
        Date, nullable=False
    )  # effectiveDate from VNDirect API — the key date for price adjustment
    record_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )  # expiredDate from API
    announcement_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )  # disclosureDate from API

    # For CASH_DIVIDEND: dividend amount in VND per share (use `dividend` field from API, NOT `ratio`)
    dividend_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    # For STOCK_DIVIDEND / BONUS_SHARES: ratio per 100 shares
    # e.g., 35.0 means 100 old shares → 135 total shares
    ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True
    )

    # Computed adjustment factor (cached after computation)
    adjustment_factor: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 8), nullable=True
    )

    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # For ex-date alert deduplication (CORP-07)
    alert_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("event_source_id", name="uq_corporate_events_source_id"),
        UniqueConstraint(
            "ticker_id", "event_type", "ex_date",
            name="uq_corporate_events_ticker_type_date",
        ),
    )

    def __repr__(self) -> str:
        return f"<CorporateEvent(ticker_id={self.ticker_id}, type={self.event_type}, ex_date={self.ex_date})>"
