from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class SimulationConfig(Base):
    """Single-row configuration for paper trading simulation.

    Always exactly one row (id=1). CHECK constraint enforces singleton.
    """
    __tablename__ = "simulation_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, server_default="1")
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(16, 2), nullable=False, server_default="100000000"
    )
    auto_track_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    min_confidence_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="5"
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<SimulationConfig(capital={self.initial_capital}, auto_track={self.auto_track_enabled})>"
