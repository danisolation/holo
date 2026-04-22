"""Backtest analytics service — on-demand computation of performance metrics,
benchmark comparison, and multi-dimensional breakdowns.

Consumes Phase 32 backtest data (BacktestRun, BacktestTrade, BacktestEquity)
and produces analytics dicts for Phase 33 API endpoints.

Pattern: follows PaperTradeAnalyticsService — session injected via constructor,
returns dicts from each method.
"""
import math
from statistics import mean, stdev

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from loguru import logger

from app.models.backtest import BacktestRun, BacktestTrade, BacktestEquity, BacktestStatus
from app.models.paper_trade import TradeStatus
from app.models.ticker import Ticker
from app.crawlers.vnstock_crawler import VnstockCrawler
from app.services.analytics_base import CLOSED_STATUSES, calc_win_rate, calc_pnl_pct, calc_avg_pnl, calc_max_drawdown


class BacktestAnalyticsService:
    """Analytics engine for completed backtest runs."""

    def __init__(self, session: AsyncSession, crawler: VnstockCrawler | None = None):
        self.session = session
        self.crawler = crawler or VnstockCrawler()

    async def _get_run(self, run_id: int) -> BacktestRun:
        """Fetch and validate a completed backtest run."""
        result = await self.session.execute(
            select(BacktestRun).where(BacktestRun.id == run_id)
        )
        run = result.scalars().first()
        if not run:
            raise HTTPException(status_code=404, detail="Backtest run not found")
        if run.status != BacktestStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Backtest not completed yet")
        return run

    # --- BENCH-02: Performance Summary ---

    async def get_performance_summary(self, run_id: int) -> dict:
        """Core performance metrics: win rate, P&L, drawdown, Sharpe ratio."""
        run = await self._get_run(run_id)

        # Win/loss/P&L from closed trades
        result = await self.session.execute(
            select(
                func.count().label("total"),
                func.count().filter(BacktestTrade.realized_pnl > 0).label("wins"),
                func.sum(BacktestTrade.realized_pnl).label("total_pnl"),
            ).where(
                BacktestTrade.run_id == run_id,
                BacktestTrade.status.in_(CLOSED_STATUSES),
            )
        )
        row = result.one()
        total = row.total or 0
        wins = row.wins or 0
        total_pnl = float(row.total_pnl or 0)
        initial_capital = float(run.initial_capital)

        win_rate = calc_win_rate(wins, total)
        total_pnl_pct = calc_pnl_pct(total_pnl, initial_capital)
        avg_pnl = calc_avg_pnl(total_pnl, total)

        # Max drawdown from equity curve
        equity_result = await self.session.execute(
            select(BacktestEquity.total_equity)
            .where(BacktestEquity.run_id == run_id)
            .order_by(BacktestEquity.date.asc())
        )
        equities = [float(r.total_equity) for r in equity_result.all()]

        max_dd_vnd, max_dd_pct = calc_max_drawdown(equities)

        # Sharpe ratio from daily returns
        returns_result = await self.session.execute(
            select(BacktestEquity.daily_return_pct)
            .where(
                BacktestEquity.run_id == run_id,
                BacktestEquity.daily_return_pct.isnot(None),
            )
        )
        daily_returns = [r.daily_return_pct for r in returns_result.all()]

        if len(daily_returns) >= 2:
            mean_return = mean(daily_returns)
            std_return = stdev(daily_returns)
            sharpe = round((mean_return / std_return) * math.sqrt(252), 4) if std_return > 0 else 0.0
        else:
            sharpe = 0.0

        return {
            "total_trades": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": win_rate,
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": total_pnl_pct,
            "avg_pnl_per_trade": avg_pnl,
            "max_drawdown": round(max_dd_vnd, 2),
            "max_drawdown_pct": max_dd_pct,
            "sharpe_ratio": sharpe,
        }

    # --- BENCH-01: VN-Index Benchmark Comparison ---

    async def get_benchmark_comparison(self, run_id: int) -> dict:
        """AI strategy equity curve vs VN-Index buy-and-hold."""
        run = await self._get_run(run_id)

        # AI equity curve
        equity_result = await self.session.execute(
            select(
                BacktestEquity.date,
                BacktestEquity.total_equity,
                BacktestEquity.cumulative_return_pct,
            )
            .where(BacktestEquity.run_id == run_id)
            .order_by(BacktestEquity.date.asc())
        )
        equity_rows = equity_result.all()

        # Fetch VN-Index data with graceful fallback (T-33-02 mitigation)
        vnindex_map: dict = {}
        vnindex_total_return: float | None = None
        try:
            df = await self.crawler.fetch_ohlcv(
                "VNINDEX", str(run.start_date), str(run.end_date)
            )
            # T-33-04 mitigation: validate DataFrame has expected columns
            if df is not None and not df.empty and "close" in df.columns and "time" in df.columns:
                vnindex_base = float(df.iloc[0]["close"])
                if vnindex_base > 0:
                    for _, row in df.iterrows():
                        d = str(row["time"])[:10]  # YYYY-MM-DD
                        close = float(row["close"])
                        vnindex_map[d] = round((close / vnindex_base - 1) * 100, 4)
                    # Last VN-Index return
                    last_close = float(df.iloc[-1]["close"])
                    vnindex_total_return = round((last_close / vnindex_base - 1) * 100, 2)
            else:
                logger.warning("VN-Index DataFrame missing expected columns or empty")
        except Exception as e:
            logger.error(f"Failed to fetch VN-Index data for benchmark: {e}")

        # Build aligned time-series
        data = []
        for row in equity_rows:
            date_str = str(row.date)
            data.append({
                "date": date_str,
                "ai_equity": float(row.total_equity),
                "ai_return_pct": float(row.cumulative_return_pct) if row.cumulative_return_pct is not None else 0.0,
                "vnindex_return_pct": vnindex_map.get(date_str),
            })

        # Summary
        ai_total_return = float(equity_rows[-1].cumulative_return_pct or 0) if equity_rows else 0.0
        outperformance = round(ai_total_return - vnindex_total_return, 2) if vnindex_total_return is not None else None

        return {
            "initial_capital": float(run.initial_capital),
            "ai_total_return_pct": round(ai_total_return, 2),
            "vnindex_total_return_pct": vnindex_total_return,
            "outperformance_pct": outperformance,
            "data": data,
        }

    # --- BENCH-03: Sector Breakdown ---

    async def get_sector_breakdown(self, run_id: int) -> list[dict]:
        """Per-sector performance stats, grouped by ticker industry."""
        await self._get_run(run_id)

        result = await self.session.execute(
            select(
                func.coalesce(Ticker.industry, "Unknown").label("sector"),
                func.count().label("total"),
                func.count().filter(BacktestTrade.realized_pnl > 0).label("wins"),
                func.sum(BacktestTrade.realized_pnl).label("total_pnl"),
                func.avg(BacktestTrade.realized_pnl).label("avg_pnl"),
            )
            .join(Ticker, BacktestTrade.ticker_id == Ticker.id)
            .where(
                BacktestTrade.run_id == run_id,
                BacktestTrade.status.in_(CLOSED_STATUSES),
            )
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

    # --- BENCH-04: Confidence Breakdown ---

    async def get_confidence_breakdown(self, run_id: int) -> list[dict]:
        """Per-confidence-bucket stats: LOW (1-3), MEDIUM (4-6), HIGH (7-10)."""
        await self._get_run(run_id)

        bracket_expr = case(
            (BacktestTrade.confidence <= 3, "LOW (1-3)"),
            (BacktestTrade.confidence <= 6, "MEDIUM (4-6)"),
            else_="HIGH (7-10)",
        )
        result = await self.session.execute(
            select(
                bracket_expr.label("bracket"),
                func.count().label("total"),
                func.count().filter(BacktestTrade.realized_pnl > 0).label("wins"),
                func.avg(BacktestTrade.realized_pnl).label("avg_pnl"),
                func.avg(BacktestTrade.realized_pnl_pct).label("avg_pnl_pct"),
            )
            .where(
                BacktestTrade.run_id == run_id,
                BacktestTrade.status.in_(CLOSED_STATUSES),
            )
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

    # --- BENCH-05: Timeframe Breakdown ---

    async def get_timeframe_breakdown(self, run_id: int) -> list[dict]:
        """Per-holding-period-bucket stats: SHORT (1-5d), MEDIUM (6-15d), LONG (16+d)."""
        await self._get_run(run_id)

        holding_days = BacktestTrade.closed_date - BacktestTrade.entry_date
        bucket_expr = case(
            (holding_days <= 5, "SHORT (1-5d)"),
            (holding_days <= 15, "MEDIUM (6-15d)"),
            else_="LONG (16+d)",
        )
        result = await self.session.execute(
            select(
                bucket_expr.label("bucket"),
                func.count().label("total"),
                func.count().filter(BacktestTrade.realized_pnl > 0).label("wins"),
                func.avg(holding_days).label("avg_holding_days"),
                func.sum(BacktestTrade.realized_pnl).label("total_pnl"),
                func.avg(BacktestTrade.realized_pnl).label("avg_pnl"),
            )
            .where(
                BacktestTrade.run_id == run_id,
                BacktestTrade.status.in_(CLOSED_STATUSES),
                BacktestTrade.entry_date.isnot(None),
                BacktestTrade.closed_date.isnot(None),
            )
            .group_by(bucket_expr)
        )
        return [
            {
                "bucket": row.bucket,
                "total_trades": row.total,
                "wins": row.wins or 0,
                "win_rate": round((row.wins or 0) / row.total * 100, 2) if row.total > 0 else 0,
                "avg_holding_days": round(float(row.avg_holding_days or 0), 1),
                "total_pnl": round(float(row.total_pnl or 0), 2),
                "avg_pnl": round(float(row.avg_pnl or 0), 2),
            }
            for row in result.all()
        ]
