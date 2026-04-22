"""Trade activation and signal processing for backtesting.

Handles:
- D+1 trade activation (PENDING → ACTIVE at open price with slippage)
- Signal → PENDING trade creation from AI trading signals
"""
from datetime import date
from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backtest import BacktestTrade, BacktestAnalysis
from app.models.daily_price import DailyPrice
from app.models.paper_trade import TradeStatus, TradeDirection
from app.schemas.analysis import TickerTradingSignal
from app.services.paper_trade_service import calculate_position_size


def apply_slippage(price: Decimal, slippage_pct: Decimal, is_buy: bool) -> Decimal:
    """Apply slippage: buying costs more, selling receives less."""
    if is_buy:
        return price * (1 + slippage_pct / 100)
    else:
        return price * (1 - slippage_pct / 100)


class TradeActivator:
    """Activates PENDING trades and creates new trades from signals."""

    async def activate_pending_trades(
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
                continue

            is_buy = trade.direction == TradeDirection.LONG
            slipped_entry = apply_slippage(Decimal(str(bar.open)), slippage_pct, is_buy=is_buy)

            trade.status = TradeStatus.ACTIVE
            trade.entry_price = slipped_entry
            trade.entry_date = session_date

            cost = slipped_entry * trade.quantity
            cash -= cost

        await session.commit()
        return cash

    async def process_signals(
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
                if analysis.raw_response is None:
                    continue

                signal_data = TickerTradingSignal.model_validate(analysis.raw_response)

                rec_dir = signal_data.recommended_direction.value
                if rec_dir == "long":
                    dir_analysis = signal_data.long_analysis
                else:
                    dir_analysis = signal_data.bearish_analysis

                plan = dir_analysis.trading_plan

                entry_price = Decimal(str(plan.entry_price))
                quantity = calculate_position_size(
                    capital=cash,
                    allocation_pct=plan.position_size_pct,
                    entry_price=entry_price,
                )

                if quantity == 0:
                    continue

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
                    closed_quantity=0,
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
