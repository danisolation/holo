"""Paper trade analytics service — async DB queries for CRUD + analytics.

Consumed by Phase 24 API router. Session injected via constructor.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, desc, case, String
from sqlalchemy.sql.expression import extract
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
        timeframe: str | None = None, symbol: str | None = None,
        limit: int = 50, offset: int = 0,
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
        if symbol:
            query = query.where(Ticker.symbol == symbol.upper())
            count_query = count_query.join(
                Ticker, PaperTrade.ticker_id == Ticker.id
            ).where(Ticker.symbol == symbol.upper())

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

    # --- Analytics Methods (AN-01 through AN-04) ---

    async def get_summary(self) -> dict:
        """AN-01, AN-02: Win rate + total P&L."""
        result = await self.session.execute(
            select(
                func.count().label("total"),
                func.count().filter(PaperTrade.realized_pnl > 0).label("wins"),
                func.sum(PaperTrade.realized_pnl).label("total_pnl"),
            ).where(PaperTrade.status.in_(CLOSED_STATUSES))
        )
        row = result.one()
        total = row.total or 0
        wins = row.wins or 0
        total_pnl = float(row.total_pnl or 0)
        win_rate = round(wins / total * 100, 2) if total > 0 else 0.0
        avg_pnl = round(total_pnl / total, 2) if total > 0 else 0.0

        # AN-02: P&L as % of initial capital
        config_result = await self.session.execute(
            select(SimulationConfig.initial_capital).where(SimulationConfig.id == 1)
        )
        initial_capital = float(config_result.scalar_one())
        total_pnl_pct = round(total_pnl / initial_capital * 100, 2) if initial_capital > 0 else 0.0

        return {
            "total_trades": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": win_rate,
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": total_pnl_pct,
            "avg_pnl_per_trade": avg_pnl,
        }

    async def get_equity_curve(self) -> dict:
        """AN-03: Equity curve — cumulative P&L by closed_date."""
        result = await self.session.execute(
            select(
                PaperTrade.closed_date,
                func.sum(PaperTrade.realized_pnl).label("daily_pnl"),
            )
            .where(
                PaperTrade.status.in_(CLOSED_STATUSES),
                PaperTrade.closed_date.isnot(None),
            )
            .group_by(PaperTrade.closed_date)
            .order_by(PaperTrade.closed_date)
        )
        rows = result.all()

        cumulative = 0.0
        curve = []
        for row in rows:
            daily = float(row.daily_pnl or 0)
            cumulative += daily
            curve.append({
                "date": row.closed_date.isoformat(),
                "daily_pnl": round(daily, 2),
                "cumulative_pnl": round(cumulative, 2),
            })

        # Get initial capital for response
        config_result = await self.session.execute(
            select(SimulationConfig.initial_capital).where(SimulationConfig.id == 1)
        )
        initial_capital = float(config_result.scalar_one())

        return {"data": curve, "initial_capital": initial_capital}

    async def get_drawdown(self) -> dict:
        """AN-04: Max drawdown from equity curve."""
        equity_data = await self.get_equity_curve()
        curve = equity_data["data"]

        if not curve:
            return {
                "max_drawdown_vnd": 0, "max_drawdown_pct": 0,
                "current_drawdown_vnd": 0, "current_drawdown_pct": 0,
                "periods": [],
            }

        initial_capital = equity_data["initial_capital"]
        peak = 0.0
        max_dd_vnd = 0.0
        max_dd_pct = 0.0

        for point in curve:
            value = point["cumulative_pnl"]
            if value > peak:
                peak = value
            else:
                dd = value - peak
                if dd < max_dd_vnd:
                    max_dd_vnd = dd
                    equity_at_peak = initial_capital + peak
                    max_dd_pct = round(dd / equity_at_peak * 100, 2) if equity_at_peak > 0 else 0.0

        # Current drawdown
        current_value = curve[-1]["cumulative_pnl"] if curve else 0
        current_dd = current_value - peak
        current_dd_pct = 0.0
        if current_dd < 0 and (initial_capital + peak) > 0:
            current_dd_pct = round(current_dd / (initial_capital + peak) * 100, 2)

        # Build drawdown periods by tracking peak-to-trough-to-recovery
        dd_periods: list[dict] = []
        peak2 = 0.0
        dd_start2 = None
        trough_val = 0.0
        for point in curve:
            value = point["cumulative_pnl"]
            if value >= peak2:
                if dd_start2 is not None:
                    dd_periods.append({
                        "start": dd_start2,
                        "end": point["date"],
                        "drawdown_vnd": round(trough_val - peak2, 2),
                    })
                peak2 = value
                dd_start2 = None
                trough_val = value
            else:
                if dd_start2 is None:
                    dd_start2 = point["date"]
                    trough_val = value
                elif value < trough_val:
                    trough_val = value

        # If still in drawdown at end, add open period
        if dd_start2 is not None:
            dd_periods.append({
                "start": dd_start2,
                "end": None,
                "drawdown_vnd": round(trough_val - peak2, 2),
            })

        return {
            "max_drawdown_vnd": round(max_dd_vnd, 2),
            "max_drawdown_pct": max_dd_pct,
            "current_drawdown_vnd": round(current_dd, 2) if current_dd < 0 else 0,
            "current_drawdown_pct": current_dd_pct if current_dd < 0 else 0,
            "periods": dd_periods[-5:],  # Last 5 drawdown periods
        }

    # --- Breakdown Analytics (AN-05 through AN-09) ---

    async def get_direction_analysis(self) -> list[dict]:
        """AN-05: LONG vs BEARISH performance comparison."""
        result = await self.session.execute(
            select(
                PaperTrade.direction,
                func.count().label("total"),
                func.count().filter(PaperTrade.realized_pnl > 0).label("wins"),
                func.sum(PaperTrade.realized_pnl).label("total_pnl"),
                func.avg(PaperTrade.realized_pnl).label("avg_pnl"),
            )
            .where(PaperTrade.status.in_(CLOSED_STATUSES))
            .group_by(PaperTrade.direction)
        )
        return [
            {
                "direction": row.direction.value,
                "total_trades": row.total,
                "wins": row.wins or 0,
                "losses": row.total - (row.wins or 0),
                "win_rate": round((row.wins or 0) / row.total * 100, 2) if row.total > 0 else 0,
                "total_pnl": round(float(row.total_pnl or 0), 2),
                "avg_pnl": round(float(row.avg_pnl or 0), 2),
            }
            for row in result.all()
        ]

    async def get_confidence_analysis(self) -> list[dict]:
        """AN-06: Performance by confidence bracket (LOW 1-3, MEDIUM 4-6, HIGH 7-10)."""
        bracket_expr = case(
            (PaperTrade.confidence <= 3, "LOW"),
            (PaperTrade.confidence <= 6, "MEDIUM"),
            else_="HIGH",
        )
        result = await self.session.execute(
            select(
                bracket_expr.label("bracket"),
                func.count().label("total"),
                func.count().filter(PaperTrade.realized_pnl > 0).label("wins"),
                func.avg(PaperTrade.realized_pnl).label("avg_pnl"),
                func.avg(PaperTrade.realized_pnl_pct).label("avg_pnl_pct"),
            )
            .where(PaperTrade.status.in_(CLOSED_STATUSES))
            .group_by(bracket_expr)
        )
        return [
            {
                "bracket": row.bracket,
                "total_trades": row.total,
                "wins": row.wins or 0,
                "win_rate": round((row.wins or 0) / row.total * 100, 2) if row.total > 0 else 0,
                "avg_pnl": round(float(row.avg_pnl or 0), 2),
                "avg_pnl_pct": round(float(row.avg_pnl_pct or 0), 2),
            }
            for row in result.all()
        ]

    async def get_risk_reward(self) -> dict:
        """AN-07: R:R achieved vs predicted.

        achieved R:R = realized_pnl / (abs(entry_price - stop_loss) * quantity)
        Uses abs() for both LONG and BEARISH directions.
        """
        result = await self.session.execute(
            select(
                PaperTrade.realized_pnl,
                PaperTrade.entry_price,
                PaperTrade.stop_loss,
                PaperTrade.quantity,
                PaperTrade.risk_reward_ratio,
            ).where(
                PaperTrade.status.in_(CLOSED_STATUSES),
                PaperTrade.realized_pnl.isnot(None),
            )
        )
        rows = result.all()

        if not rows:
            return {
                "avg_predicted_rr": 0, "avg_achieved_rr": 0,
                "trades_above_predicted": 0, "trades_below_predicted": 0,
                "total_trades": 0,
            }

        predicted_rrs = []
        achieved_rrs = []
        above = 0
        below = 0

        for row in rows:
            risk = abs(float(row.entry_price) - float(row.stop_loss)) * row.quantity
            if risk > 0:
                achieved = float(row.realized_pnl) / risk
            else:
                achieved = 0.0

            predicted = row.risk_reward_ratio or 0.0
            predicted_rrs.append(predicted)
            achieved_rrs.append(achieved)

            if achieved >= predicted:
                above += 1
            else:
                below += 1

        avg_predicted = round(sum(predicted_rrs) / len(predicted_rrs), 2) if predicted_rrs else 0
        avg_achieved = round(sum(achieved_rrs) / len(achieved_rrs), 2) if achieved_rrs else 0

        return {
            "avg_predicted_rr": avg_predicted,
            "avg_achieved_rr": avg_achieved,
            "trades_above_predicted": above,
            "trades_below_predicted": below,
            "total_trades": len(rows),
        }

    async def get_profit_factor(self) -> dict:
        """AN-08: Profit factor (gross_profit / abs(gross_loss)) + expected value."""
        result = await self.session.execute(
            select(
                func.sum(PaperTrade.realized_pnl).filter(PaperTrade.realized_pnl > 0).label("gross_profit"),
                func.sum(PaperTrade.realized_pnl).filter(PaperTrade.realized_pnl <= 0).label("gross_loss"),
                func.avg(PaperTrade.realized_pnl).label("expected_value"),
                func.count().label("total"),
            ).where(PaperTrade.status.in_(CLOSED_STATUSES))
        )
        row = result.one()
        gross_profit = float(row.gross_profit or 0)
        gross_loss = float(row.gross_loss or 0)
        total = row.total or 0

        # Profit factor = gross_profit / |gross_loss|. None if no losses (avoid infinity).
        if gross_loss < 0:
            profit_factor = round(gross_profit / abs(gross_loss), 2)
        else:
            profit_factor = None  # No losing trades — infinite factor

        return {
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": profit_factor,
            "expected_value": round(float(row.expected_value or 0), 2),
            "total_trades": total,
        }

    async def get_sector_analysis(self) -> list[dict]:
        """AN-09: Performance by industry sector. JOIN tickers for industry field."""
        result = await self.session.execute(
            select(
                func.coalesce(Ticker.industry, "Unknown").label("sector"),
                func.count().label("total"),
                func.count().filter(PaperTrade.realized_pnl > 0).label("wins"),
                func.sum(PaperTrade.realized_pnl).label("total_pnl"),
                func.avg(PaperTrade.realized_pnl).label("avg_pnl"),
            )
            .join(Ticker, PaperTrade.ticker_id == Ticker.id)
            .where(PaperTrade.status.in_(CLOSED_STATUSES))
            .group_by(Ticker.industry)
            .order_by(func.count().desc())
        )
        return [
            {
                "sector": row.sector,
                "total_trades": row.total,
                "wins": row.wins or 0,
                "win_rate": round((row.wins or 0) / row.total * 100, 2) if row.total > 0 else 0,
                "total_pnl": round(float(row.total_pnl or 0), 2),
                "avg_pnl": round(float(row.avg_pnl or 0), 2),
            }
            for row in result.all()
        ]

    # --- Phase 26: Additional Analytics (UI-02 through UI-06) ---

    async def get_streaks(self) -> dict:
        """UI-03: Win/loss streak tracking.

        Iterates closed trades ordered by (closed_date, id) ASC,
        counts consecutive win/loss runs per-trade.
        """
        result = await self.session.execute(
            select(PaperTrade.realized_pnl)
            .where(PaperTrade.status.in_(CLOSED_STATUSES))
            .order_by(PaperTrade.closed_date, PaperTrade.id)
        )
        rows = result.all()

        current_win = 0
        current_loss = 0
        max_win = 0
        max_loss = 0

        for row in rows:
            pnl = float(row.realized_pnl or 0)
            if pnl > 0:
                current_win += 1
                current_loss = 0
                max_win = max(max_win, current_win)
            else:
                current_loss += 1
                current_win = 0
                max_loss = max(max_loss, current_loss)

        return {
            "current_win_streak": current_win,
            "current_loss_streak": current_loss,
            "longest_win_streak": max_win,
            "longest_loss_streak": max_loss,
            "total_trades": len(rows),
        }

    async def get_timeframe_comparison(self) -> list[dict]:
        """UI-04: Performance by timeframe (swing vs position)."""
        result = await self.session.execute(
            select(
                PaperTrade.timeframe,
                func.count().label("total"),
                func.count().filter(PaperTrade.realized_pnl > 0).label("wins"),
                func.sum(PaperTrade.realized_pnl).label("total_pnl"),
                func.avg(PaperTrade.realized_pnl).label("avg_pnl"),
            )
            .where(PaperTrade.status.in_(CLOSED_STATUSES))
            .group_by(PaperTrade.timeframe)
        )
        return [
            {
                "timeframe": row.timeframe,
                "total_trades": row.total,
                "wins": row.wins or 0,
                "losses": row.total - (row.wins or 0),
                "win_rate": round((row.wins or 0) / row.total * 100, 2) if row.total > 0 else 0,
                "total_pnl": round(float(row.total_pnl or 0), 2),
                "avg_pnl": round(float(row.avg_pnl or 0), 2),
            }
            for row in result.all()
        ]

    async def get_periodic_summary(self, period: str = "weekly") -> list[dict]:
        """UI-06: Weekly or monthly performance summary."""
        if period == "weekly":
            period_expr = func.concat(
                extract("isoyear", PaperTrade.closed_date).cast(String),
                "-W",
                func.lpad(extract("week", PaperTrade.closed_date).cast(String), 2, "0"),
            )
        else:
            period_expr = func.to_char(PaperTrade.closed_date, "YYYY-MM")

        result = await self.session.execute(
            select(
                period_expr.label("period"),
                func.count().label("total"),
                func.count().filter(PaperTrade.realized_pnl > 0).label("wins"),
                func.sum(PaperTrade.realized_pnl).label("total_pnl"),
                func.avg(PaperTrade.risk_reward_ratio).label("avg_rr"),
            )
            .where(
                PaperTrade.status.in_(CLOSED_STATUSES),
                PaperTrade.closed_date.isnot(None),
            )
            .group_by(period_expr)
            .order_by(desc(period_expr))
            .limit(12)
        )
        return [
            {
                "period": row.period,
                "total_trades": row.total,
                "wins": row.wins or 0,
                "losses": row.total - (row.wins or 0),
                "win_rate": round((row.wins or 0) / row.total * 100, 2) if row.total > 0 else 0,
                "total_pnl": round(float(row.total_pnl or 0), 2),
                "avg_rr": round(float(row.avg_rr or 0), 2),
            }
            for row in result.all()
        ]

    async def get_calendar_data(self) -> list[dict]:
        """UI-02: Daily P&L aggregates for calendar heatmap."""
        result = await self.session.execute(
            select(
                PaperTrade.closed_date,
                func.sum(PaperTrade.realized_pnl).label("daily_pnl"),
                func.count().label("trade_count"),
            )
            .where(
                PaperTrade.status.in_(CLOSED_STATUSES),
                PaperTrade.closed_date.isnot(None),
            )
            .group_by(PaperTrade.closed_date)
            .order_by(PaperTrade.closed_date)
        )
        return [
            {
                "date": row.closed_date.isoformat(),
                "daily_pnl": round(float(row.daily_pnl or 0), 2),
                "trade_count": row.trade_count,
            }
            for row in result.all()
        ]

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
