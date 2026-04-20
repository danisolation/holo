import enum
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import (
    Integer, BigInteger, String, Numeric, Date, Float,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class TradeStatus(str, enum.Enum):
    """Paper trade lifecycle states."""
    PENDING = "pending"
    ACTIVE = "active"
    PARTIAL_TP = "partial_tp"
    CLOSED_TP2 = "closed_tp2"
    CLOSED_SL = "closed_sl"
    CLOSED_TIMEOUT = "closed_timeout"
    CLOSED_MANUAL = "closed_manual"


class TradeDirection(str, enum.Enum):
    """Trade direction — mirrors Direction enum from schemas/analysis.py."""
    LONG = "long"
    BEARISH = "bearish"


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    ai_analysis_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ai_analyses.id"), nullable=True
    )
    direction: Mapped[TradeDirection] = mapped_column(
        SAEnum(TradeDirection, name="trade_direction", create_constraint=False,
               native_enum=True, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    status: Mapped[TradeStatus] = mapped_column(
        SAEnum(TradeStatus, name="trade_status", create_constraint=False,
               native_enum=True, values_callable=lambda e: [m.value for m in e]),
        nullable=False, server_default="pending",
    )
    # Prices
    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    take_profit_1: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    take_profit_2: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    adjusted_stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Sizing
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    closed_quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # P&L fields (computed when closing)
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    realized_pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Exit tracking
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    partial_exit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Dates
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Metadata from signal
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(20), nullable=False)
    position_size_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_reward_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def effective_stop_loss(self) -> Decimal:
        """Return adjusted SL (breakeven) if partial TP happened, else original SL."""
        return self.adjusted_stop_loss if self.adjusted_stop_loss is not None else self.stop_loss

    def __repr__(self) -> str:
        return f"<PaperTrade(id={self.id}, ticker_id={self.ticker_id}, dir={self.direction}, status={self.status})>"
