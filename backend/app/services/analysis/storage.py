"""Analysis result storage — DB upsert for ai_analyses.

Extracted from AIAnalysisService._store_analysis.
"""
import json
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis import AnalysisType


class AnalysisStorage:
    """Stores analysis results to ai_analyses table."""

    def __init__(self, session: AsyncSession, model: str):
        self.session = session
        self.model = model

    async def store_analysis(
        self,
        ticker_id: int,
        analysis_type: AnalysisType,
        analysis_date: date,
        signal: str,
        score: int,
        reasoning: str,
        raw_response: dict | None,
    ) -> None:
        """Store analysis result with upsert (INSERT ... ON CONFLICT DO UPDATE).

        Uses raw SQL to avoid SQLAlchemy Enum serialization issues with asyncpg.
        """
        raw_json = json.dumps(raw_response) if raw_response else None
        await self.session.execute(
            text("""
                INSERT INTO ai_analyses (ticker_id, analysis_type, analysis_date, signal, score, reasoning, model_version, raw_response)
                VALUES (:tid, CAST(:atype AS analysis_type), :adate, :signal, :score, :reasoning, :model, CAST(:raw AS jsonb))
                ON CONFLICT ON CONSTRAINT uq_ai_analyses_ticker_type_date
                DO UPDATE SET signal = :signal, score = :score, reasoning = :reasoning,
                              model_version = :model, raw_response = CAST(:raw AS jsonb)
            """),
            {
                "tid": ticker_id,
                "atype": analysis_type.value,
                "adate": analysis_date,
                "signal": signal,
                "score": score,
                "reasoning": reasoning,
                "model": self.model,
                "raw": raw_json,
            },
        )
