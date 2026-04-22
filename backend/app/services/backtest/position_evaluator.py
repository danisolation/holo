"""Position evaluation for backtesting.

Handles:
- SL/TP/TP2 evaluation using paper_trade_service pure functions
- Trading day timeout checks
"""
from datetime import date
from decimal import Decimal

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backtest import BacktestTrade
from app.models.daily_price import DailyPrice
from app.models.paper_trade import TradeStatus, TradeDirection
from app.services.backtest.trade_activator import apply_slippage
from app.services.paper_trade_service import (
    calculate_pnl,
    apply_partial_tp,
    evaluate_long_position,
    evaluate_bearish_position,
    TIMEOUT_TRADING_DAYS,
)


class PositionEvaluator:
    """Evaluates open positions against daily price bars."""

    async def evaluate_positions(
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
                cash = await self.check_timeout(
                    session, trade, session_date, slippage_pct, cash, bar
                )
                continue

            if new_status == TradeStatus.PARTIAL_TP:
                is_sell = trade.direction == TradeDirection.LONG
                slipped_tp1 = apply_slippage(exit_price, slippage_pct, is_buy=not is_sell)
                apply_partial_tp(trade, slipped_tp1)
                cash += slipped_tp1 * trade.closed_quantity

            elif new_status in (
                TradeStatus.CLOSED_SL,
                TradeStatus.CLOSED_TP2,
            ):
                is_sell = trade.direction == TradeDirection.LONG
                slipped_exit = apply_slippage(exit_price, slippage_pct, is_buy=not is_sell)
                remaining_qty = trade.quantity - trade.closed_quantity

                trade.exit_price = slipped_exit
                trade.closed_date = session_date
                trade.status = new_status

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

                cash += slipped_exit * remaining_qty

        await session.commit()
        return cash

    async def check_timeout(
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

        close_price = Decimal(str(bar.close))
        is_sell = trade.direction == TradeDirection.LONG
        slipped_exit = apply_slippage(close_price, slippage_pct, is_buy=not is_sell)
        remaining_qty = trade.quantity - trade.closed_quantity

        trade.exit_price = slipped_exit
        trade.closed_date = session_date
        trade.status = TradeStatus.CLOSED_TIMEOUT

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

        cash += slipped_exit * remaining_qty

        logger.info(
            f"Backtest trade {trade.id}: TIMEOUT after {trading_day_count} trading days "
            f"(limit: {timeout_days}), P&L: {pnl:,.0f} VND ({pnl_pct:.2f}%)"
        )
        return cash
