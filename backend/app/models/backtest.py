"""Backtest engine models — BacktestRun, BacktestTrade, BacktestEquity, BacktestAnalysis.

Isolated from live paper_trades and ai_analyses tables. Each backtest run
is self-contained with its own trades, analyses, and equity snapshots.
"""
import enum
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import (
    Integer, BigInteger, String, Numeric, Date, Float, Boolean, Text,
    ForeignKey, Enum as SAEnum, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base
from app.models.paper_trade import TradeStatus, TradeDirection  # Reuse existing enums


class BacktestStatus(str, enum.Enum):
    """Backtest run lifecycle states."""
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(16, 2), nullable=False, server_default="100000000"
    )
    slippage_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, server_default="0.5"
    )
    status: Mapped[BacktestStatus] = mapped_column(
        SAEnum(BacktestStatus, name="backtest_status", create_constraint=False,
               native_enum=True, values_callable=lambda e: [m.value for m in e]),
        nullable=False, server_default="running",
    )
    last_completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    completed_sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<BacktestRun(id={self.id}, status={self.status}, {self.start_date} to {self.end_date})>"


class BacktestAnalysis(Base):
    """Mirrors AIAnalysis but scoped to a backtest run.
    analysis_type is String(20) — NOT Enum — to avoid enum dependency."""
    __tablename__ = "backtest_analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("backtest_runs.id"), nullable=False)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(20), nullable=False)
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    signal: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("run_id", "ticker_id", "analysis_type", "analysis_date",
                         name="uq_backtest_analyses_run_ticker_type_date"),
    )

    def __repr__(self) -> str:
        return f"<BacktestAnalysis(run_id={self.run_id}, ticker_id={self.ticker_id}, type={self.analysis_type})>"


class BacktestTrade(Base):
    """Mirrors PaperTrade but scoped to a backtest run."""
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("backtest_runs.id"), nullable=False)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    backtest_analysis_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("backtest_analyses.id"), nullable=True
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
    # Prices (same as PaperTrade)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    take_profit_1: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    take_profit_2: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    adjusted_stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Sizing
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    closed_quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # P&L fields
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

    @property
    def effective_stop_loss(self) -> Decimal:
        """Return adjusted SL (breakeven) if partial TP happened, else original SL."""
        return self.adjusted_stop_loss if self.adjusted_stop_loss is not None else self.stop_loss

    def __repr__(self) -> str:
        return f"<BacktestTrade(id={self.id}, run_id={self.run_id}, dir={self.direction}, status={self.status})>"


class BacktestEquity(Base):
    """Per-session equity snapshot for a backtest run."""
    __tablename__ = "backtest_equity"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("backtest_runs.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    positions_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    total_equity: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    daily_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    cumulative_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("run_id", "date", name="uq_backtest_equity_run_date"),
    )

    def __repr__(self) -> str:
        return f"<BacktestEquity(run_id={self.run_id}, date={self.date}, equity={self.total_equity})>"
