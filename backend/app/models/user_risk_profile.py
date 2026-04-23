"""User risk profile — single-row table for personal trading preferences.

Stores capital, risk level (1-5), and broker fee percentage.
Default: 50M VND capital, risk_level 3, broker fee 0.15%.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class UserRiskProfile(Base):
    __tablename__ = "user_risk_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    capital: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="50000000")
    risk_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    broker_fee_pct: Mapped[Decimal] = mapped_column(Numeric(5, 3), nullable=False, server_default="0.150")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserRiskProfile(capital={self.capital}, risk_level={self.risk_level})>"
