"""WeeklyPrompt model — weekly risk tolerance prompt for the user.

One pending prompt at a time. Response adjusts UserRiskProfile.risk_level.
Auto-expires after 7 days if unanswered.
"""
from datetime import date, datetime

from sqlalchemy import BigInteger, Integer, String, Date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class WeeklyPrompt(Base):
    __tablename__ = "weekly_prompts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    prompt_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="risk_tolerance")
    response: Mapped[str | None] = mapped_column(String(20), nullable=True)  # cautious/aggressive/unchanged/expired
    risk_level_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<WeeklyPrompt(id={self.id}, week={self.week_start}, response={self.response})>"
