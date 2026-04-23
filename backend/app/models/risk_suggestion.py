"""RiskSuggestion model — risk level adjustment suggestions.

After 3 consecutive losing trades, the system suggests reducing risk.
User can accept (applies change) or reject (records response).
Only 1 pending suggestion at a time.
"""
from datetime import datetime

from sqlalchemy import BigInteger, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class RiskSuggestion(Base):
    __tablename__ = "risk_suggestions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    current_level: Mapped[int] = mapped_column(Integer, nullable=False)
    suggested_level: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="pending")  # pending/accepted/rejected
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_risk_suggestions_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<RiskSuggestion(id={self.id}, {self.current_level}→{self.suggested_level}, status={self.status})>"
