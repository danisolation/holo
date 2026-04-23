"""TradingGoal model — monthly profit target tracking.

One active goal per month. Stores target_pnl and status.
actual_pnl is computed at query time from trades table.
"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, String, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class TradingGoal(Base):
    __tablename__ = "trading_goals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    target_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    month: Mapped[date] = mapped_column(Date, nullable=False)  # First day of month
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="active")  # active/completed/missed
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<TradingGoal(id={self.id}, target={self.target_pnl}, month={self.month}, status={self.status})>"
