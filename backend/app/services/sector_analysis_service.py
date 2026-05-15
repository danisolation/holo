"""Sector analysis service — sector-level performance and flow metrics.

Computes two metrics from existing DailyPrice + Ticker tables:
1. Sector Performance — average % price change per sector for today/7D/30D
2. Sector Flow — net buying/selling volume per sector per day

Uses SQL window functions (LAG) for previous close computation.
Groups null/empty sectors as "Khác" via COALESCE.
"""
from datetime import date

from loguru import logger
from sqlalchemy import select, func, case, literal_column, cast, Float, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_price import DailyPrice
from app.models.ticker import Ticker


class SectorAnalysisService:
    """Compute sector-level analysis from DailyPrice and Ticker data."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_sector_performance(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """Get average % price change per sector for today, 7D, and 30D.

        Uses LAG window functions to compute previous close prices,
        then averages % changes per sector. Null sectors → "Khác".

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of dicts with sector, ticker_count, avg_change_today/7d/30d
        """
        sector_col = func.coalesce(
            func.nullif(Ticker.sector, ''), 'Khác'
        ).label("sector")

        # CTE: compute per-ticker daily data with LAG for prev close
        base = (
            select(
                DailyPrice.ticker_id,
                DailyPrice.date,
                DailyPrice.close,
                sector_col,
                func.lag(DailyPrice.close, 1).over(
                    partition_by=DailyPrice.ticker_id,
                    order_by=DailyPrice.date
                ).label("prev_close_1d"),
                func.lag(DailyPrice.close, 5).over(
                    partition_by=DailyPrice.ticker_id,
                    order_by=DailyPrice.date
                ).label("prev_close_5d"),
                func.lag(DailyPrice.close, 22).over(
                    partition_by=DailyPrice.ticker_id,
                    order_by=DailyPrice.date
                ).label("prev_close_22d"),
            )
            .join(Ticker, DailyPrice.ticker_id == Ticker.id)
            .where(Ticker.is_active.is_(True))
        ).cte("price_with_lag")

        # Aggregate: group by sector, compute averages
        # Only include rows in the requested date range for the final aggregation
        pct_today = case(
            (base.c.prev_close_1d > 0,
             (base.c.close - base.c.prev_close_1d) / base.c.prev_close_1d * 100),
            else_=None,
        )
        pct_7d = case(
            (base.c.prev_close_5d > 0,
             (base.c.close - base.c.prev_close_5d) / base.c.prev_close_5d * 100),
            else_=None,
        )
        pct_30d = case(
            (base.c.prev_close_22d > 0,
             (base.c.close - base.c.prev_close_22d) / base.c.prev_close_22d * 100),
            else_=None,
        )

        stmt = (
            select(
                base.c.sector,
                func.count(func.distinct(base.c.ticker_id)).label("ticker_count"),
                func.avg(cast(pct_today, Float)).label("avg_change_today"),
                func.avg(cast(pct_7d, Float)).label("avg_change_7d"),
                func.avg(cast(pct_30d, Float)).label("avg_change_30d"),
            )
            .where(
                base.c.date >= start_date,
                base.c.date <= end_date,
            )
            .group_by(base.c.sector)
            .order_by(base.c.sector)
        )

        result = await self.session.execute(stmt)
        rows = result.fetchall()

        return [
            {
                "sector": row.sector,
                "ticker_count": row.ticker_count,
                "avg_change_today": (
                    round(float(row.avg_change_today), 2)
                    if row.avg_change_today is not None
                    else None
                ),
                "avg_change_7d": (
                    round(float(row.avg_change_7d), 2)
                    if row.avg_change_7d is not None
                    else None
                ),
                "avg_change_30d": (
                    round(float(row.avg_change_30d), 2)
                    if row.avg_change_30d is not None
                    else None
                ),
            }
            for row in rows
        ]

    async def get_sector_flow(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """Get net buying/selling volume per sector per day.

        net_volume = SUM(volume * sign(close - prev_close))
        buy_volume = SUM(volume WHERE close > prev_close)
        sell_volume = SUM(volume WHERE close < prev_close)

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of dicts with sector, date, net_volume, buy_volume, sell_volume
        """
        sector_col = func.coalesce(
            func.nullif(Ticker.sector, ''), 'Khác'
        ).label("sector")

        # CTE: per-ticker daily data with LAG for prev close
        base = (
            select(
                DailyPrice.ticker_id,
                DailyPrice.date,
                DailyPrice.close,
                DailyPrice.volume,
                sector_col,
                func.lag(DailyPrice.close, 1).over(
                    partition_by=DailyPrice.ticker_id,
                    order_by=DailyPrice.date
                ).label("prev_close"),
            )
            .join(Ticker, DailyPrice.ticker_id == Ticker.id)
            .where(Ticker.is_active.is_(True))
        ).cte("price_with_lag")

        # Direction sign: +1 if close > prev, -1 if close < prev, 0 if equal
        direction = case(
            (base.c.close > base.c.prev_close, 1),
            (base.c.close < base.c.prev_close, -1),
            else_=0,
        )

        buy_vol = case(
            (base.c.close > base.c.prev_close, base.c.volume),
            else_=0,
        )

        sell_vol = case(
            (base.c.close < base.c.prev_close, base.c.volume),
            else_=0,
        )

        stmt = (
            select(
                base.c.sector,
                base.c.date,
                cast(func.sum(base.c.volume * direction), Float).label("net_volume"),
                cast(func.sum(buy_vol), Float).label("buy_volume"),
                cast(func.sum(sell_vol), Float).label("sell_volume"),
            )
            .where(
                base.c.date >= start_date,
                base.c.date <= end_date,
                base.c.prev_close.isnot(None),  # skip first day (no prev)
            )
            .group_by(base.c.sector, base.c.date)
            .order_by(base.c.date, base.c.sector)
        )

        result = await self.session.execute(stmt)
        rows = result.fetchall()

        return [
            {
                "sector": row.sector,
                "date": row.date.isoformat() if hasattr(row.date, "isoformat") else str(row.date),
                "net_volume": float(row.net_volume) if row.net_volume else 0.0,
                "buy_volume": float(row.buy_volume) if row.buy_volume else 0.0,
                "sell_volume": float(row.sell_volume) if row.sell_volume else 0.0,
            }
            for row in rows
        ]
