"""SectorPreference model — learned sector performance from trades.

Tracks win/loss rates and net P&L per sector. Preference scores
bias future pick generation toward profitable sectors.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Integer, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class SectorPreference(Base):
    __tablename__ = "sector_preferences"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sector: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    win_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    loss_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    net_pnl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    preference_score: Mapped[Decimal] = mapped_column(Numeric(5, 3), nullable=False, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<SectorPreference(sector={self.sector}, score={self.preference_score})>"
