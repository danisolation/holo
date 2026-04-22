"""Backtest engine: replays historical sessions with Gemini AI analysis.

Orchestrates the backtest loop, delegating to focused sub-modules:
- TradeActivator: D+1 trade activation and signal processing
- PositionEvaluator: SL/TP/timeout evaluation
- EquitySnapshot: Daily equity recording

BT-02: Date-first iteration with D+1 open entry
BT-03: Signal → PENDING → ACTIVE at D+1 open with slippage
BT-04: Position evaluation reusing paper_trade_service pure functions
BT-05: Checkpoint/resume per completed day
BT-06: Cancel flag support
SIM-02: Position sizing from CURRENT cash
SIM-03: Slippage on all entry/exit prices
SIM-04: Per-session equity snapshots
"""
from datetime import date
from decimal import Decimal

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.backtest import BacktestRun, BacktestEquity, BacktestStatus
from app.models.ticker import Ticker
from app.services.backtest.trade_activator import TradeActivator, apply_slippage
from app.services.backtest.position_evaluator import PositionEvaluator
from app.services.backtest.equity_snapshot import EquitySnapshot
from app.services.backtest_analysis_service import BacktestAnalysisService


class BacktestEngine:
    """Backtest engine: replays historical sessions with Gemini AI analysis.

    Orchestrates the date loop and delegates trade/position/equity work to
    focused sub-modules.
    """

    def __init__(self):
        self._trade_activator = TradeActivator()
        self._position_evaluator = PositionEvaluator()
        self._equity_snapshot = EquitySnapshot()

    async def run(self, run_id: int) -> None:
        """Main entry point — called by API's BackgroundTasks.

        Complete flow:
        1. Load run, get trading dates, get tickers
        2. Resume logic: skip completed dates, reload positions, restore cash
        3. Main date loop: AI pipeline → activate pending → evaluate positions →
           new signals → equity snapshot → checkpoint
        4. Set final status (COMPLETED/CANCELLED/FAILED)
        """
        async with async_session() as session:
            try:
                # 1. Load run
                run = await self._load_run(session, run_id)
                if run is None:
                    logger.error(f"Backtest run {run_id} not found")
                    return
                if run.status != BacktestStatus.RUNNING:
                    logger.warning(f"Backtest run {run_id} status is {run.status}, expected RUNNING")
                    return

                slippage_pct = run.slippage_pct

                # 2. Get trading dates
                trading_dates = await self._get_trading_dates(session, run.start_date, run.end_date)
                if not trading_dates:
                    logger.warning(f"No trading dates found between {run.start_date} and {run.end_date}")
                    run.status = BacktestStatus.COMPLETED
                    await session.commit()
                    return

                # 3. Get all active tickers
                ticker_map = await self._get_active_tickers(session)

                # 4. Resume logic
                cash: Decimal
                if run.last_completed_date is not None:
                    trading_dates = [d for d in trading_dates if d > run.last_completed_date]
                    if not trading_dates:
                        logger.info(f"Backtest {run_id}: all dates already completed")
                        run.status = BacktestStatus.COMPLETED
                        await session.commit()
                        return

                    equity_result = await session.execute(
                        select(BacktestEquity.cash)
                        .where(BacktestEquity.run_id == run_id)
                        .order_by(BacktestEquity.date.desc())
                        .limit(1)
                    )
                    last_cash = equity_result.scalar_one_or_none()
                    cash = last_cash if last_cash is not None else run.initial_capital
                    logger.info(
                        f"Backtest {run_id}: resuming from {run.last_completed_date}, "
                        f"cash={cash}, {len(trading_dates)} dates remaining"
                    )
                else:
                    cash = run.initial_capital

                prev_equity: Decimal | None = None
                if run.last_completed_date is not None:
                    eq_result = await session.execute(
                        select(BacktestEquity.total_equity)
                        .where(BacktestEquity.run_id == run_id)
                        .order_by(BacktestEquity.date.desc())
                        .limit(1)
                    )
                    prev_equity = eq_result.scalar_one_or_none()

                # 5. Main date loop
                for session_date in trading_dates:
                    # a. Cancel check
                    cancel_result = await session.execute(
                        select(BacktestRun.is_cancelled)
                        .where(BacktestRun.id == run_id)
                    )
                    is_cancelled = cancel_result.scalar_one_or_none()
                    if is_cancelled:
                        run.status = BacktestStatus.CANCELLED
                        await session.commit()
                        logger.info(f"Backtest {run_id}: cancelled at {session_date}")
                        return

                    # b. Run AI pipeline
                    await self._run_ai_pipeline(session, run_id, session_date, ticker_map)

                    # c. Activate PENDING trades (D+1 entry)
                    cash = await self._trade_activator.activate_pending_trades(
                        session, run_id, session_date, slippage_pct, cash
                    )

                    # d. Evaluate open positions
                    cash = await self._position_evaluator.evaluate_positions(
                        session, run_id, session_date, slippage_pct, cash
                    )

                    # e. Process new signals (create PENDING trades)
                    await self._trade_activator.process_signals(
                        session, run_id, session_date, cash
                    )

                    # f. Record equity snapshot
                    total_equity = await self._equity_snapshot.record(
                        session, run_id, session_date, cash,
                        run.initial_capital, prev_equity,
                    )
                    prev_equity = total_equity

                    # g. Checkpoint
                    run.last_completed_date = session_date
                    run.completed_sessions += 1
                    await session.commit()
                    logger.info(
                        f"Backtest {run_id}: completed {session_date} "
                        f"({run.completed_sessions}/{run.total_sessions})"
                    )

                # 6. After loop: mark completed
                run.status = BacktestStatus.COMPLETED
                await session.commit()
                logger.info(f"Backtest {run_id}: COMPLETED")

            except Exception as e:
                logger.error(f"Backtest {run_id} failed: {type(e).__name__}: {e}")
                try:
                    run_result = await session.execute(
                        select(BacktestRun).where(BacktestRun.id == run_id)
                    )
                    failed_run = run_result.scalars().first()
                    if failed_run:
                        failed_run.status = BacktestStatus.FAILED
                        await session.commit()
                except Exception:
                    logger.error(f"Failed to mark backtest {run_id} as FAILED")
                raise

    # ------------------------------------------------------------------
    # Data loading helpers
    # ------------------------------------------------------------------

    async def _load_run(self, session: AsyncSession, run_id: int) -> BacktestRun | None:
        """Load BacktestRun by ID."""
        result = await session.execute(
            select(BacktestRun).where(BacktestRun.id == run_id)
        )
        return result.scalars().first()

    async def _get_trading_dates(
        self, session: AsyncSession, start_date: date, end_date: date
    ) -> list[date]:
        """Get actual trading dates from daily_prices (weekends/holidays excluded)."""
        result = await session.execute(
            text(
                "SELECT DISTINCT date FROM daily_prices "
                "WHERE date BETWEEN :start AND :end "
                "ORDER BY date ASC"
            ),
            {"start": start_date, "end": end_date},
        )
        return [row[0] for row in result.fetchall()]

    async def _get_active_tickers(self, session: AsyncSession) -> dict[str, int]:
        """Get all active tickers as {symbol: id} map."""
        result = await session.execute(
            select(Ticker.symbol, Ticker.id).where(Ticker.is_active == True)
        )
        return {row[0]: row[1] for row in result.fetchall()}

    # ------------------------------------------------------------------
    # AI Pipeline
    # ------------------------------------------------------------------

    async def _run_ai_pipeline(
        self,
        session: AsyncSession,
        run_id: int,
        session_date: date,
        ticker_map: dict[str, int],
    ) -> None:
        """Run Gemini AI analysis pipeline for a single session date.

        Calls: technical → combined → trading_signal.
        Does NOT call fundamental or sentiment (per RESEARCH.md).
        """
        analysis_svc = BacktestAnalysisService(session, run_id, session_date)

        try:
            await analysis_svc.run_technical_analysis(ticker_filter=ticker_map)
        except Exception as e:
            logger.error(f"Backtest {run_id} date {session_date}: technical analysis failed: {e}")

        try:
            await analysis_svc.run_combined_analysis(ticker_filter=ticker_map)
        except Exception as e:
            logger.error(f"Backtest {run_id} date {session_date}: combined analysis failed: {e}")

        try:
            await analysis_svc.run_trading_signal_analysis(ticker_filter=ticker_map)
        except Exception as e:
            logger.error(f"Backtest {run_id} date {session_date}: trading signal analysis failed: {e}")
