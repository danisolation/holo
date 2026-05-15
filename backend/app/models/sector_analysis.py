"""AI-generated sector intelligence results from Gemini.

One row per day — stores full structured sector analysis as JSONB.
Phase 103: Sector strength/weakness and rotation timing analysis.
"""
from datetime import date, datetime

from sqlalchemy import BigInteger, String, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class SectorAnalysis(Base):
    """Daily AI sector intelligence analysis."""
    __tablename__ = "sector_analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    analysis_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
