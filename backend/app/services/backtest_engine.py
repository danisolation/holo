"""Backtest engine: replays historical sessions with Gemini AI analysis.

Date-first iteration: each session processes ALL tickers → evaluate positions → next day.
Checkpoint after each completed day for resume capability.
Cancel flag checked per day for graceful stop.

BT-02: Date-first iteration with D+1 open entry
BT-03: Signal → PENDING → ACTIVE at D+1 open with slippage
BT-04: Position evaluation reusing paper_trade_service pure functions
BT-05: Checkpoint/resume per completed day
BT-06: Cancel flag support
SIM-02: Position sizing from CURRENT cash
SIM-03: Slippage on all entry/exit prices
SIM-04: Per-session equity snapshots
"""
import asyncio
from datetime import date
from decimal import Decimal

from loguru import logger
from sqlalchemy import select, text, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.backtest import (
    BacktestRun, BacktestTrade, BacktestEquity, BacktestAnalysis,
    BacktestStatus,
)
from app.models.daily_price import DailyPrice
from app.models.paper_trade import TradeStatus, TradeDirection
from app.models.ticker import Ticker
from app.schemas.analysis import TickerTradingSignal
from app.services.backtest_analysis_service import BacktestAnalysisService
from app.services.paper_trade_service import (
    calculate_position_size,
    calculate_pnl,
    apply_partial_tp,
    evaluate_long_position,
    evaluate_bearish_position,
    TIMEOUT_TRADING_DAYS,
)


# ------------------------------------------------------------------
# Module-level utility
# ------------------------------------------------------------------


def apply_slippage(price: Decimal, slippage_pct: Decimal, is_buy: bool) -> Decimal:
    """Apply slippage: buying costs more, selling receives less.

    Args:
        price: Original price
        slippage_pct: Slippage percentage (e.g., Decimal("0.5") for 0.5%)
        is_buy: True for buy orders (price goes up), False for sell (price goes down)

    Returns:
        Slippage-adjusted price
    """
    if is_buy:
        return price * (1 + slippage_pct / 100)
    else:
        return price * (1 - slippage_pct / 100)


# ------------------------------------------------------------------
# BacktestEngine
# ------------------------------------------------------------------


class BacktestEngine:
    """Backtest engine: replays historical sessions with Gemini AI analysis.

    Date-first iteration: each session processes ALL tickers → evaluate positions → next day.
    Checkpoint after each completed day for resume capability.
    """

    def __init__(self):
        pass

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
                    # Resume: filter dates, reload cash from last equity snapshot
                    trading_dates = [d for d in trading_dates if d > run.last_completed_date]
                    if not trading_dates:
                        logger.info(f"Backtest {run_id}: all dates already completed")
                        run.status = BacktestStatus.COMPLETED
                        await session.commit()
                        return

                    # Restore cash from last equity snapshot
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
                    # Fresh start
                    cash = run.initial_capital

                # Track previous equity for daily return calculation
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
                    cash = await self._activate_pending_trades(
                        session, run_id, session_date, slippage_pct, cash
                    )

                    # d. Evaluate open positions
                    cash = await self._evaluate_positions(
                        session, run_id, session_date, slippage_pct, cash
                    )

                    # e. Process new signals (create PENDING trades)
                    await self._process_signals(
                        session, run_id, session_date, cash
                    )

                    # f. Record equity snapshot
                    total_equity = await self._record_equity_snapshot(
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
                    # Try to mark as failed
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

        # Technical analysis
        try:
            await analysis_svc.run_technical_analysis(ticker_filter=ticker_map)
        except Exception as e:
            logger.error(f"Backtest {run_id} date {session_date}: technical analysis failed: {e}")

        # Combined analysis (uses backtest technical results)
        try:
            await analysis_svc.run_combined_analysis(ticker_filter=ticker_map)
        except Exception as e:
            logger.error(f"Backtest {run_id} date {session_date}: combined analysis failed: {e}")

        # Trading signal analysis (generates signals)
        try:
            await analysis_svc.run_trading_signal_analysis(ticker_filter=ticker_map)
        except Exception as e:
            logger.error(f"Backtest {run_id} date {session_date}: trading signal analysis failed: {e}")

    # ------------------------------------------------------------------
    # Trade Activation (D+1 entry)
    # ------------------------------------------------------------------

    async def _activate_pending_trades(
        self,
        session: AsyncSession,
        run_id: int,
        session_date: date,
        slippage_pct: Decimal,
        cash: Decimal,
    ) -> Decimal:
        """Activate PENDING trades at D+1 open price with slippage.

        Per BT-03: signal_date < session_date → eligible for activation.
        """
        result = await session.execute(
            select(BacktestTrade)
            .where(
                BacktestTrade.run_id == run_id,
                BacktestTrade.status == TradeStatus.PENDING,
                BacktestTrade.signal_date < session_date,
            )
        )
        pending_trades = result.scalars().all()

        if not pending_trades:
            return cash

        # Get open prices for all pending tickers on session_date
        ticker_ids = [t.ticker_id for t in pending_trades]
        bar_result = await session.execute(
            select(DailyPrice)
            .where(
                DailyPrice.ticker_id.in_(ticker_ids),
                DailyPrice.date == session_date,
            )
        )
        bars = {b.ticker_id: b for b in bar_result.scalars().all()}

        for trade in pending_trades:
            bar = bars.get(trade.ticker_id)
            if bar is None:
                # Ticker not traded that day — skip, try next day
                continue

            is_buy = trade.direction == TradeDirection.LONG
            slipped_entry = apply_slippage(Decimal(str(bar.open)), slippage_pct, is_buy=is_buy)

            trade.status = TradeStatus.ACTIVE
            trade.entry_price = slipped_entry
            trade.entry_date = session_date

            # Deduct cash
            cost = slipped_entry * trade.quantity
            cash -= cost

        await session.commit()
        return cash

    # ------------------------------------------------------------------
    # Position Evaluation
    # ------------------------------------------------------------------

    async def _evaluate_positions(
        self,
        session: AsyncSession,
        run_id: int,
        session_date: date,
        slippage_pct: Decimal,
        cash: Decimal,
    ) -> Decimal:
        """Evaluate open positions (ACTIVE and PARTIAL_TP) against today's bars.

        Uses paper_trade_service pure functions for SL/TP evaluation.
        """
        result = await session.execute(
            select(BacktestTrade)
            .where(
                BacktestTrade.run_id == run_id,
                BacktestTrade.status.in_([TradeStatus.ACTIVE, TradeStatus.PARTIAL_TP]),
            )
        )
        open_positions = result.scalars().all()

        if not open_positions:
            return cash

        # Get OHLCV bars for all position tickers on session_date
        ticker_ids = [t.ticker_id for t in open_positions]
        bar_result = await session.execute(
            select(DailyPrice)
            .where(
                DailyPrice.ticker_id.in_(ticker_ids),
                DailyPrice.date == session_date,
            )
        )
        price_map = {b.ticker_id: b for b in bar_result.scalars().all()}

        for trade in open_positions:
            bar = price_map.get(trade.ticker_id)
            if bar is None:
                continue

            bar_open = Decimal(str(bar.open))
            bar_high = Decimal(str(bar.high))
            bar_low = Decimal(str(bar.low))

            # Choose evaluator based on direction
            if trade.direction == TradeDirection.LONG:
                new_status, exit_price = evaluate_long_position(
                    status=trade.status,
                    effective_sl=trade.effective_stop_loss,
                    take_profit_1=trade.take_profit_1,
                    take_profit_2=trade.take_profit_2,
                    bar_open=bar_open,
                    bar_high=bar_high,
                    bar_low=bar_low,
                )
            else:
                new_status, exit_price = evaluate_bearish_position(
                    status=trade.status,
                    effective_sl=trade.effective_stop_loss,
                    take_profit_1=trade.take_profit_1,
                    take_profit_2=trade.take_profit_2,
                    bar_open=bar_open,
                    bar_high=bar_high,
                    bar_low=bar_low,
                )

            if new_status is None:
                # No state change — check timeout
                cash = await self._check_timeout(
                    session, trade, session_date, slippage_pct, cash, bar
                )
                continue

            if new_status == TradeStatus.PARTIAL_TP:
                # Partial TP: close ~50%, move SL to breakeven
                is_sell = trade.direction == TradeDirection.LONG
                slipped_tp1 = apply_slippage(exit_price, slippage_pct, is_buy=not is_sell)
                apply_partial_tp(trade, slipped_tp1)
                # Cash += partial exit proceeds
                cash += slipped_tp1 * trade.closed_quantity

            elif new_status in (
                TradeStatus.CLOSED_SL,
                TradeStatus.CLOSED_TP2,
            ):
                # Full close
                is_sell = trade.direction == TradeDirection.LONG
                slipped_exit = apply_slippage(exit_price, slippage_pct, is_buy=not is_sell)
                remaining_qty = trade.quantity - trade.closed_quantity

                trade.exit_price = slipped_exit
                trade.closed_date = session_date
                trade.status = new_status

                # Calculate P&L
                pnl, pnl_pct = calculate_pnl(
                    direction=trade.direction.value if hasattr(trade.direction, "value") else str(trade.direction),
                    entry_price=trade.entry_price,
                    quantity=trade.quantity,
                    partial_exit_price=trade.partial_exit_price,
                    closed_quantity=trade.closed_quantity,
                    exit_price=slipped_exit,
                )
                trade.realized_pnl = pnl
                trade.realized_pnl_pct = pnl_pct

                # Cash += exit proceeds for remaining shares
                cash += slipped_exit * remaining_qty

        await session.commit()
        return cash

    async def _check_timeout(
        self,
        session: AsyncSession,
        trade: BacktestTrade,
        session_date: date,
        slippage_pct: Decimal,
        cash: Decimal,
        bar: DailyPrice,
    ) -> Decimal:
        """Check if a position has exceeded its timeout period.

        Counts actual trading days from daily_prices (not calendar days).
        """
        if trade.entry_date is None:
            return cash

        timeout_days = TIMEOUT_TRADING_DAYS.get(trade.timeframe)
        if timeout_days is None:
            return cash

        # Count trading days between entry and session_date
        count_result = await session.execute(
            text(
                "SELECT COUNT(*) FROM daily_prices "
                "WHERE ticker_id = :tid AND date BETWEEN :start AND :end"
            ),
            {"tid": trade.ticker_id, "start": trade.entry_date, "end": session_date},
        )
        trading_day_count = count_result.scalar() or 0

        if trading_day_count <= timeout_days:
            return cash

        # Timeout: close at today's close with slippage
        close_price = Decimal(str(bar.close))
        is_sell = trade.direction == TradeDirection.LONG
        slipped_exit = apply_slippage(close_price, slippage_pct, is_buy=not is_sell)
        remaining_qty = trade.quantity - trade.closed_quantity

        trade.exit_price = slipped_exit
        trade.closed_date = session_date
        trade.status = TradeStatus.CLOSED_TIMEOUT

        # Calculate P&L
        pnl, pnl_pct = calculate_pnl(
            direction=trade.direction.value if hasattr(trade.direction, "value") else str(trade.direction),
            entry_price=trade.entry_price,
            quantity=trade.quantity,
            partial_exit_price=trade.partial_exit_price,
            closed_quantity=trade.closed_quantity,
            exit_price=slipped_exit,
        )
        trade.realized_pnl = pnl
        trade.realized_pnl_pct = pnl_pct

        # Cash += exit proceeds
        cash += slipped_exit * remaining_qty

        logger.info(
            f"Backtest trade {trade.id}: TIMEOUT after {trading_day_count} trading days "
            f"(limit: {timeout_days}), P&L: {pnl:,.0f} VND ({pnl_pct:.2f}%)"
        )
        return cash

    # ------------------------------------------------------------------
    # Signal Processing (Create PENDING trades)
    # ------------------------------------------------------------------

    async def _process_signals(
        self,
        session: AsyncSession,
        run_id: int,
        session_date: date,
        cash: Decimal,
    ) -> None:
        """Process today's valid trading signals and create PENDING trades.

        Per BT-03: signals on day D create PENDING trades → activated at D+1.
        Per SIM-02: position sizing uses CURRENT cash (not initial capital).
        """
        # Query today's valid trading signals
        result = await session.execute(
            select(BacktestAnalysis)
            .where(
                BacktestAnalysis.run_id == run_id,
                BacktestAnalysis.analysis_type == "trading_signal",
                BacktestAnalysis.analysis_date == session_date,
                BacktestAnalysis.score > 0,
            )
        )
        signals = result.scalars().all()

        for analysis in signals:
            try:
                # Parse raw_response to get structured trading signal
                if analysis.raw_response is None:
                    continue

                signal_data = TickerTradingSignal.model_validate(analysis.raw_response)

                # Get recommended direction and its analysis
                rec_dir = signal_data.recommended_direction.value
                if rec_dir == "long":
                    dir_analysis = signal_data.long_analysis
                else:
                    dir_analysis = signal_data.bearish_analysis

                plan = dir_analysis.trading_plan

                # Calculate position size from CURRENT cash
                entry_price = Decimal(str(plan.entry_price))
                quantity = calculate_position_size(
                    capital=cash,
                    allocation_pct=plan.position_size_pct,
                    entry_price=entry_price,
                )

                if quantity == 0:
                    # Not enough capital — skip
                    continue

                # Create PENDING trade
                trade = BacktestTrade(
                    run_id=run_id,
                    ticker_id=analysis.ticker_id,
                    backtest_analysis_id=analysis.id,
                    direction=TradeDirection.LONG if rec_dir == "long" else TradeDirection.BEARISH,
                    status=TradeStatus.PENDING,
                    entry_price=entry_price,
                    stop_loss=Decimal(str(plan.stop_loss)),
                    take_profit_1=Decimal(str(plan.take_profit_1)),
                    take_profit_2=Decimal(str(plan.take_profit_2)),
                    quantity=quantity,
                    confidence=dir_analysis.confidence,
                    timeframe=plan.timeframe.value if hasattr(plan.timeframe, "value") else str(plan.timeframe),
                    position_size_pct=plan.position_size_pct,
                    risk_reward_ratio=plan.risk_reward_ratio,
                    signal_date=session_date,
                )
                session.add(trade)

            except Exception as e:
                logger.warning(
                    f"Backtest {run_id}: failed to process signal for ticker_id={analysis.ticker_id} "
                    f"on {session_date}: {e}"
                )

        await session.commit()

    # ------------------------------------------------------------------
    # Equity Snapshot
    # ------------------------------------------------------------------

    async def _record_equity_snapshot(
        self,
        session: AsyncSession,
        run_id: int,
        session_date: date,
        cash: Decimal,
        initial_capital: Decimal,
        prev_equity: Decimal | None,
    ) -> Decimal:
        """Record per-session equity snapshot (cash + mark-to-market positions).

        Returns total_equity for daily return tracking.
        """
        # Get all open positions
        result = await session.execute(
            select(BacktestTrade)
            .where(
                BacktestTrade.run_id == run_id,
                BacktestTrade.status.in_([
                    TradeStatus.PENDING,
                    TradeStatus.ACTIVE,
                    TradeStatus.PARTIAL_TP,
                ]),
            )
        )
        open_positions = result.scalars().all()

        positions_value = Decimal("0")
        for trade in open_positions:
            if trade.status == TradeStatus.PENDING:
                # Pending: no market exposure yet
                continue

            # Get close price for ticker on session_date
            price_result = await session.execute(
                select(DailyPrice.close)
                .where(
                    DailyPrice.ticker_id == trade.ticker_id,
                    DailyPrice.date == session_date,
                )
            )
            close_price = price_result.scalar_one_or_none()
            if close_price is None:
                continue

            remaining_qty = trade.quantity - trade.closed_quantity
            positions_value += Decimal(str(close_price)) * remaining_qty

        total_equity = cash + positions_value

        # Compute return percentages
        cumulative_return_pct = float(
            (total_equity - initial_capital) / initial_capital * 100
        ) if initial_capital > 0 else 0.0

        daily_return_pct: float | None = None
        if prev_equity is not None and prev_equity > 0:
            daily_return_pct = float(
                (total_equity - prev_equity) / prev_equity * 100
            )

        equity = BacktestEquity(
            run_id=run_id,
            date=session_date,
            cash=cash,
            positions_value=positions_value,
            total_equity=total_equity,
            daily_return_pct=daily_return_pct,
            cumulative_return_pct=cumulative_return_pct,
        )
        session.add(equity)

        return total_equity
