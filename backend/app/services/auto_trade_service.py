"""Auto-trade service — executes paper trades from AI daily pick signals."""
from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_pick import DailyPick
from app.models.simulator_trade import SimulatorTrade
from app.models.ticker import Ticker
from app.schemas.simulator import SimulatorTradeCreate
from app.services.simulator_service import SimulatorService


class AutoTradeService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_pending_signals(self, days_back: int = 3) -> list[dict]:
        """Get daily picks that haven't been traded yet in the simulator.

        Returns picks from last N days that have no corresponding simulator_trade
        with matching daily_pick_id.
        """
        cutoff = date.today() - timedelta(days=days_back)

        # Get picked signals (not "almost")
        result = await self.session.execute(
            select(DailyPick)
            .where(DailyPick.status == "picked")
            .where(DailyPick.pick_date >= cutoff)
            .where(DailyPick.entry_price.isnot(None))
            .order_by(DailyPick.pick_date.desc(), DailyPick.rank)
        )
        picks = result.scalars().all()

        # Filter out already-traded picks
        traded_pick_ids_result = await self.session.execute(
            select(SimulatorTrade.daily_pick_id)
            .where(SimulatorTrade.daily_pick_id.isnot(None))
        )
        traded_ids = set(r[0] for r in traded_pick_ids_result.all())

        pending = []
        for pick in picks:
            if pick.id in traded_ids:
                continue
            # Get ticker symbol
            ticker_result = await self.session.execute(
                select(Ticker).where(Ticker.id == pick.ticker_id)
            )
            ticker = ticker_result.scalar_one()

            pending.append({
                "daily_pick_id": pick.id,
                "pick_date": str(pick.pick_date),
                "ticker_symbol": ticker.symbol,
                "ticker_name": ticker.name,
                "entry_price": float(pick.entry_price) if pick.entry_price else None,
                "stop_loss": float(pick.stop_loss) if pick.stop_loss else None,
                "take_profit_1": float(pick.take_profit_1) if pick.take_profit_1 else None,
                "composite_score": float(pick.composite_score),
                "rank": pick.rank,
                "position_size_shares": pick.position_size_shares,
                "explanation": pick.explanation,
            })

        return pending

    async def execute_ai_signals(self, pick_ids: list[int]) -> list[dict]:
        """Execute BUY trades for specified daily pick IDs.

        Uses entry_price and position_size_shares from the pick.
        """
        service = SimulatorService(self.session)
        results = []

        for pick_id in pick_ids:
            result = await self.session.execute(
                select(DailyPick).where(DailyPick.id == pick_id)
            )
            pick = result.scalar_one_or_none()
            if not pick or not pick.entry_price:
                logger.warning(f"Pick {pick_id} not found or no entry price")
                continue

            ticker_result = await self.session.execute(
                select(Ticker).where(Ticker.id == pick.ticker_id)
            )
            ticker = ticker_result.scalar_one()

            # Use position_size_shares from pick, or default to 100
            quantity = pick.position_size_shares or 100

            trade_data = SimulatorTradeCreate(
                ticker_symbol=ticker.symbol,
                side="BUY",
                quantity=quantity,
                price=float(pick.entry_price),
                trade_date=pick.pick_date,
                source="ai_auto",
                daily_pick_id=pick.id,
                user_notes=f"Auto-trade from AI pick (rank #{pick.rank}, score {pick.composite_score})",
            )

            try:
                trade_result = await service.create_trade(trade_data, portfolio_name="ai")
                results.append(trade_result)
                logger.info(f"Auto-traded {ticker.symbol} from pick {pick_id}")
            except ValueError as e:
                logger.warning(f"Auto-trade failed for pick {pick_id}: {e}")
                results.append({"error": str(e), "daily_pick_id": pick_id, "ticker_symbol": ticker.symbol})

        return results

    async def skip_signals(self, pick_ids: list[int]) -> int:
        """Mark signals as skipped by not creating trades.

        For MVP, the signal disappears after days_back window expires.
        User can also just ignore them. Returns count of acknowledged skips.
        """
        return len(pick_ids)

    async def execute_sell_signals(self) -> list[dict]:
        """Auto-sell open positions where latest unified AI signal is 'ban' (sell).

        Checks all tickers with open simulator positions against the latest
        unified AI analysis. If signal == "ban", sells all remaining shares
        at the latest daily close price (converted from nghìn đồng to VND).

        Always executes regardless of auto-trade toggle — selling on bearish
        signals is defensive capital protection for existing positions.

        Returns list of executed sell trade results.
        """
        from app.models.ai_analysis import AIAnalysis, AnalysisType
        from app.models.daily_price import DailyPrice

        service = SimulatorService(self.session)
        portfolio = await service.get_or_create_portfolio("ai")
        results: list[dict] = []

        # Get all open lots grouped by ticker
        from app.models.simulator_lot import SimulatorLot
        result = await self.session.execute(
            select(
                SimulatorLot.ticker_id,
                func.sum(SimulatorLot.remaining_quantity).label("total_qty"),
            )
            .where(SimulatorLot.portfolio_id == portfolio.id)
            .where(SimulatorLot.remaining_quantity > 0)
            .group_by(SimulatorLot.ticker_id)
        )
        open_positions = result.all()

        for row in open_positions:
            ticker_id = row.ticker_id
            total_qty = int(row.total_qty)

            # Get latest unified analysis for this ticker
            analysis_result = await self.session.execute(
                select(AIAnalysis)
                .where(AIAnalysis.ticker_id == ticker_id)
                .where(AIAnalysis.analysis_type == AnalysisType.UNIFIED)
                .order_by(AIAnalysis.analysis_date.desc())
                .limit(1)
            )
            analysis = analysis_result.scalar_one_or_none()
            if not analysis or analysis.signal != "ban":
                continue

            # Get latest daily price and convert to VND
            price_result = await self.session.execute(
                select(DailyPrice.close)
                .where(DailyPrice.ticker_id == ticker_id)
                .order_by(DailyPrice.date.desc())
                .limit(1)
            )
            daily_close = price_result.scalar_one_or_none()
            if daily_close is None:
                continue

            close_vnd = Decimal(str(float(daily_close))) * Decimal("1000")

            # Resolve ticker symbol
            ticker_result = await self.session.execute(
                select(Ticker).where(Ticker.id == ticker_id)
            )
            ticker = ticker_result.scalar_one()

            logger.info(
                f"AI sell signal for {ticker.symbol}: signal='{analysis.signal}' "
                f"(date={analysis.analysis_date}), selling {total_qty} shares @ {close_vnd} VND"
            )

            trade_data = SimulatorTradeCreate(
                ticker_symbol=ticker.symbol,
                side="SELL",
                quantity=total_qty,
                price=float(close_vnd),
                trade_date=date.today(),
                source="ai_auto",
                user_notes="Auto-sell: AI signal bán",
            )

            try:
                trade_result = await service.create_trade(trade_data, portfolio_name="ai")
                results.append(trade_result)
                logger.info(f"AI signal auto-sell executed: {ticker.symbol} x{total_qty} @ {close_vnd}")
            except ValueError as e:
                logger.warning(f"AI signal auto-sell failed for {ticker.symbol}: {e}")
                results.append({"error": str(e), "ticker_symbol": ticker.symbol})

        return results
