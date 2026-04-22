"""Date-aware Gemini analysis service for backtesting.

Subclasses AIAnalysisService and swaps in BacktestContextBuilder +
BacktestStorage to make all context queries use `as_of_date` instead
of latest data, and store results in `backtest_analyses` instead of
`ai_analyses`.

CRITICAL invariants (no lookahead bias):
- All queries use WHERE date <= self.as_of_date
- 52-week high/low computed relative to as_of_date (not date.today())
- Combined context reads from backtest_analyses (not ai_analyses)
- Storage writes to backtest_analyses with run_id
"""
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_analysis_service import AIAnalysisService
from app.services.analysis.context_builder import BacktestContextBuilder
from app.services.analysis.storage import BacktestStorage


class BacktestAnalysisService(AIAnalysisService):
    """Date-aware analysis service for backtesting.

    Swaps parent's ContextBuilder → BacktestContextBuilder (date-aware queries)
    and AnalysisStorage → BacktestStorage (writes to backtest_analyses with run_id).
    Orchestration and Gemini client remain unchanged from parent.
    """

    def __init__(
        self,
        session: AsyncSession,
        run_id: int,
        as_of_date: date,
        api_key: str | None = None,
    ):
        super().__init__(session, api_key)
        self.run_id = run_id
        self.as_of_date = as_of_date
        # Swap in date-aware components
        self.context_builder = BacktestContextBuilder(session, run_id, as_of_date)
        self.storage = BacktestStorage(session, self.model, run_id, as_of_date)