"""Simulator portfolio — tracks virtual cash and capital."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class SimulatorPortfolio(Base):
    __tablename__ = "simulator_portfolios"
    __table_args__ = (
        UniqueConstraint("name", name="uq_simulator_portfolios_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, server_default="user")
    starting_capital: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, server_default="100000000")
    current_cash: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, server_default="100000000")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
