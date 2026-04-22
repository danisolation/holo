"""Analysis result storage — DB upsert for ai_analyses and backtest_analyses.

Extracted from AIAnalysisService._store_analysis and
BacktestAnalysisService._store_analysis.
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


class BacktestStorage(AnalysisStorage):
    """Stores analysis results to backtest_analyses table with run_id.

    CRITICAL: Writes to backtest_analyses (never ai_analyses).
    Uses self.as_of_date as analysis_date (ignoring the parent's date.today()).
    analysis_type stored as plain string (column is VARCHAR, no CAST needed).
    """

    def __init__(self, session: AsyncSession, model: str, run_id: int, as_of_date: date):
        super().__init__(session, model)
        self.run_id = run_id
        self.as_of_date = as_of_date

    async def store_analysis(
        self,
        ticker_id: int,
        analysis_type,
        analysis_date: date,
        signal: str,
        score: int,
        reasoning: str,
        raw_response: dict | None,
    ) -> None:
        """Store analysis result into backtest_analyses with upsert.

        CRITICAL: Writes to backtest_analyses (never ai_analyses).
        Uses self.as_of_date as analysis_date (ignoring the parent's date.today()).
        analysis_type stored as plain string (column is VARCHAR, no CAST needed).
        """
        # Extract string value from AnalysisType enum if needed
        atype_str = analysis_type.value if hasattr(analysis_type, "value") else str(analysis_type)
        raw_json = json.dumps(raw_response) if raw_response else None

        await self.session.execute(
            text("""
                INSERT INTO backtest_analyses
                    (run_id, ticker_id, analysis_type, analysis_date, signal, score, reasoning, model_version, raw_response)
                VALUES
                    (:run_id, :tid, :atype, :adate, :signal, :score, :reasoning, :model, CAST(:raw AS jsonb))
                ON CONFLICT ON CONSTRAINT uq_backtest_analyses_run_ticker_type_date
                DO UPDATE SET
                    signal = :signal,
                    score = :score,
                    reasoning = :reasoning,
                    model_version = :model,
                    raw_response = CAST(:raw AS jsonb)
            """),
            {
                "run_id": self.run_id,
                "tid": ticker_id,
                "atype": atype_str,
                "adate": self.as_of_date,  # Use as_of_date, NOT the passed analysis_date
                "signal": signal,
                "score": score,
                "reasoning": reasoning,
                "model": self.model,
                "raw": raw_json,
            },
        )
