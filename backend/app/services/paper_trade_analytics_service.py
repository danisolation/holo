"""Paper trade analytics service — async DB queries for CRUD + analytics.

Consumed by Phase 24 API router. Session injected via constructor.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.paper_trade import PaperTrade, TradeStatus, TradeDirection
from app.models.simulation_config import SimulationConfig
from app.models.ticker import Ticker
from app.services.paper_trade_service import calculate_position_size, validate_transition


CLOSED_STATUSES = [
    TradeStatus.CLOSED_TP2, TradeStatus.CLOSED_SL,
    TradeStatus.CLOSED_TIMEOUT, TradeStatus.CLOSED_MANUAL,
]


class PaperTradeAnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Ticker Resolution ---
    async def _get_ticker_by_symbol(self, symbol: str) -> Ticker:
        result = await self.session.execute(
            select(Ticker).where(Ticker.symbol == symbol.upper())
        )
        ticker = result.scalar_one_or_none()
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker '{symbol}' not found")
        return ticker

    # --- Trade CRUD ---
    async def list_trades(
        self, status: str | None = None, direction: str | None = None,
        timeframe: str | None = None, limit: int = 50, offset: int = 0,
    ) -> dict:
        query = select(PaperTrade).join(Ticker, PaperTrade.ticker_id == Ticker.id)
        count_query = select(func.count(PaperTrade.id))

        if status:
            query = query.where(PaperTrade.status == TradeStatus(status))
            count_query = count_query.where(PaperTrade.status == TradeStatus(status))
        if direction:
            query = query.where(PaperTrade.direction == TradeDirection(direction))
            count_query = count_query.where(PaperTrade.direction == TradeDirection(direction))
        if timeframe:
            query = query.where(PaperTrade.timeframe == timeframe)
            count_query = count_query.where(PaperTrade.timeframe == timeframe)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        result = await self.session.execute(
            query.order_by(desc(PaperTrade.created_at)).offset(offset).limit(limit)
        )
        rows = result.scalars().all()

        # Need ticker symbols — build a ticker_id→symbol map
        ticker_ids = {r.ticker_id for r in rows}
        if ticker_ids:
            ticker_result = await self.session.execute(
                select(Ticker.id, Ticker.symbol).where(Ticker.id.in_(ticker_ids))
            )
            ticker_map = {row.id: row.symbol for row in ticker_result.all()}
        else:
            ticker_map = {}

        trades = []
        for t in rows:
            trades.append(self._trade_to_dict(t, ticker_map.get(t.ticker_id, "???")))

        return {"trades": trades, "total": total}

    async def get_trade(self, trade_id: int) -> dict:
        result = await self.session.execute(
            select(PaperTrade).where(PaperTrade.id == trade_id)
        )
        trade = result.scalar_one_or_none()
        if not trade:
            raise HTTPException(status_code=404, detail=f"Paper trade {trade_id} not found")

        ticker_result = await self.session.execute(
            select(Ticker.symbol).where(Ticker.id == trade.ticker_id)
        )
        symbol = ticker_result.scalar_one_or_none() or "???"
        return self._trade_to_dict(trade, symbol)

    # --- Manual Follow (PT-09) ---
    async def create_manual_follow(self, data: dict) -> dict:
        ticker = await self._get_ticker_by_symbol(data["symbol"])

        config_result = await self.session.execute(
            select(SimulationConfig).where(SimulationConfig.id == 1)
        )
        sim_config = config_result.scalar_one_or_none()
        if not sim_config:
            raise HTTPException(status_code=500, detail="SimulationConfig not found")

        quantity = calculate_position_size(
            capital=sim_config.initial_capital,
            allocation_pct=data["position_size_pct"],
            entry_price=Decimal(str(data["entry_price"])),
        )
        if quantity == 0:
            raise HTTPException(status_code=400, detail="Insufficient capital for minimum 100-share lot")

        entry = Decimal(str(data["entry_price"]))
        sl = Decimal(str(data["stop_loss"]))
        tp1 = Decimal(str(data["take_profit_1"]))
        tp2 = Decimal(str(data["take_profit_2"]))

        # Calculate risk_reward_ratio = |TP2 - entry| / |entry - SL|
        risk = abs(entry - sl)
        reward = abs(tp2 - entry)
        rr_ratio = float(reward / risk) if risk > 0 else 0.0

        paper_trade = PaperTrade(
            ticker_id=ticker.id,
            ai_analysis_id=None,  # Manual — not linked to signal
            direction=TradeDirection(data["direction"]),
            status=TradeStatus.PENDING,
            entry_price=entry,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            quantity=quantity,
            signal_date=date.today(),
            confidence=data["confidence"],
            timeframe=data["timeframe"],
            position_size_pct=data["position_size_pct"],
            risk_reward_ratio=round(rr_ratio, 2),
        )
        self.session.add(paper_trade)
        await self.session.commit()
        await self.session.refresh(paper_trade)
        return self._trade_to_dict(paper_trade, ticker.symbol)

    # --- Manual Close ---
    async def close_trade(self, trade_id: int) -> dict:
        result = await self.session.execute(
            select(PaperTrade).where(PaperTrade.id == trade_id)
        )
        trade = result.scalar_one_or_none()
        if not trade:
            raise HTTPException(status_code=404, detail=f"Paper trade {trade_id} not found")

        if not validate_transition(trade.status, TradeStatus.CLOSED_MANUAL):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot close trade in status '{trade.status.value}'"
            )

        trade.status = TradeStatus.CLOSED_MANUAL
        trade.closed_date = date.today()
        # For manual close, realized_pnl stays as-is (None for PENDING, or partial for PARTIAL_TP)
        await self.session.commit()
        await self.session.refresh(trade)

        ticker_result = await self.session.execute(
            select(Ticker.symbol).where(Ticker.id == trade.ticker_id)
        )
        symbol = ticker_result.scalar_one_or_none() or "???"
        return self._trade_to_dict(trade, symbol)

    # --- Config ---
    async def get_config(self) -> dict:
        result = await self.session.execute(
            select(SimulationConfig).where(SimulationConfig.id == 1)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=500, detail="SimulationConfig not found")
        return {
            "initial_capital": float(config.initial_capital),
            "auto_track_enabled": config.auto_track_enabled,
            "min_confidence_threshold": config.min_confidence_threshold,
        }

    async def update_config(self, data: dict) -> dict:
        result = await self.session.execute(
            select(SimulationConfig).where(SimulationConfig.id == 1)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=500, detail="SimulationConfig not found")

        if data.get("initial_capital") is not None:
            config.initial_capital = Decimal(str(data["initial_capital"]))
        if data.get("auto_track_enabled") is not None:
            config.auto_track_enabled = data["auto_track_enabled"]
        if data.get("min_confidence_threshold") is not None:
            config.min_confidence_threshold = data["min_confidence_threshold"]

        await self.session.commit()
        await self.session.refresh(config)
        return {
            "initial_capital": float(config.initial_capital),
            "auto_track_enabled": config.auto_track_enabled,
            "min_confidence_threshold": config.min_confidence_threshold,
        }

    # --- Helpers ---
    @staticmethod
    def _trade_to_dict(trade: PaperTrade, symbol: str) -> dict:
        return {
            "id": trade.id,
            "symbol": symbol,
            "direction": trade.direction.value,
            "status": trade.status.value,
            "entry_price": float(trade.entry_price),
            "stop_loss": float(trade.stop_loss),
            "take_profit_1": float(trade.take_profit_1),
            "take_profit_2": float(trade.take_profit_2),
            "adjusted_stop_loss": float(trade.adjusted_stop_loss) if trade.adjusted_stop_loss else None,
            "quantity": trade.quantity,
            "closed_quantity": trade.closed_quantity,
            "realized_pnl": float(trade.realized_pnl) if trade.realized_pnl is not None else None,
            "realized_pnl_pct": trade.realized_pnl_pct,
            "exit_price": float(trade.exit_price) if trade.exit_price else None,
            "partial_exit_price": float(trade.partial_exit_price) if trade.partial_exit_price else None,
            "signal_date": trade.signal_date.isoformat(),
            "entry_date": trade.entry_date.isoformat() if trade.entry_date else None,
            "closed_date": trade.closed_date.isoformat() if trade.closed_date else None,
            "confidence": trade.confidence,
            "timeframe": trade.timeframe,
            "position_size_pct": trade.position_size_pct,
            "risk_reward_ratio": trade.risk_reward_ratio,
            "created_at": trade.created_at.isoformat() if trade.created_at else "",
        }
