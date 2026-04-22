"""Equity snapshot tracking for backtesting.

Records per-session portfolio state: cash, positions value, total equity,
daily/cumulative returns.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.backtest import BacktestTrade, BacktestEquity
from app.models.daily_price import DailyPrice
from app.models.paper_trade import TradeStatus


class EquitySnapshot:
    """Records daily equity snapshots for backtest runs."""

    async def record(
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
                continue

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
