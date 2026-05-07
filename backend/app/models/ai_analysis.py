"""AI-generated analysis results from Gemini.

One row per ticker per analysis_type per date.
analysis_type enum accommodates Phase 3 sentiment.
"""
import enum
from datetime import date, datetime

from sqlalchemy import Integer, BigInteger, String, Text, Date, ForeignKey, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class AnalysisType(str, enum.Enum):
    """Types of AI analysis. Matches PostgreSQL analysis_type ENUM."""
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"  # Phase 3 — included now for forward compatibility
    COMBINED = "combined"    # Phase 3 — holistic mua/bán/giữ recommendation
    TRADING_SIGNAL = "trading_signal"  # Phase 19 — dual-direction trading plan
    UNIFIED = "unified"  # Phase 88 / v19.0 — single prompt replaces all above


class AIAnalysis(Base):
    """AI analysis result for a ticker."""
    __tablename__ = "ai_analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    analysis_type: Mapped[AnalysisType] = mapped_column(
        SAEnum(
            AnalysisType,
            name="analysis_type",
            create_constraint=False,
            native_enum=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    signal: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-10, CHECK in DDL
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "ticker_id", "analysis_type", "analysis_date",
            name="uq_ai_analyses_ticker_type_date",
        ),
    )

    def __repr__(self) -> str:
        return f"<AIAnalysis(ticker_id={self.ticker_id}, type={self.analysis_type}, signal={self.signal})>"
