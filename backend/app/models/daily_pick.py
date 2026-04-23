"""Daily picks model — AI-selected top tickers for the day.

One row per ticker per day. Status is 'picked' (top 3-5) or 'almost' (runners-up).
Entry/SL/TP inherited from trading signal long_analysis.
"""
import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Integer, BigInteger, String, Text, Date, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class PickStatus(str, enum.Enum):
    PICKED = "picked"
    ALMOST = "almost"


class DailyPick(Base):
    __tablename__ = "daily_picks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pick_date: Mapped[date] = mapped_column(Date, nullable=False)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5 for picked, NULL for almost
    composite_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    take_profit_1: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    take_profit_2: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    risk_reward: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    position_size_shares: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position_size_vnd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    position_size_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)  # "picked" or "almost"
    rejection_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("pick_date", "ticker_id", name="uq_daily_picks_date_ticker"),
    )

    def __repr__(self) -> str:
        return f"<DailyPick(date={self.pick_date}, ticker_id={self.ticker_id}, rank={self.rank})>"
