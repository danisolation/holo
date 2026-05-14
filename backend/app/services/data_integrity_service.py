"""Data integrity checking service.

Detects common data quality issues: price gaps, duplicate entries,
and stale AI analysis for watchlist tickers.
Per DQ-04: Automated data integrity checks.
"""
from datetime import date, timedelta

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_price import DailyPrice
from app.models.ai_analysis import AIAnalysis
from app.models.ticker import Ticker
from app.models.user_watchlist import UserWatchlist


class DataIntegrityService:
    """Runs data integrity checks against the database."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_all(self) -> dict:
        """Run all integrity checks. Returns summary report."""
        gaps = await self.check_price_gaps()
        duplicates = await self.check_duplicates()
        stale = await self.check_stale_analysis()
        issues_count = len(gaps) + len(duplicates) + len(stale)
        return {
            "status": "healthy" if issues_count == 0 else "issues_found",
            "total_issues": issues_count,
            "price_gaps": gaps,
            "duplicates": duplicates,
            "stale_analysis": stale,
        }

    async def check_price_gaps(self, max_gap_days: int = 3) -> list[dict]:
        """Find tickers with gaps > max_gap_days between consecutive daily prices."""
        # UserWatchlist stores symbol, not ticker_id — join via Ticker
        wl_result = await self.session.execute(
            select(Ticker.id, Ticker.symbol)
            .join(UserWatchlist, UserWatchlist.symbol == Ticker.symbol)
        )
        wl_tickers = wl_result.all()
        if not wl_tickers:
            return []

        gaps = []
        cutoff = date.today() - timedelta(days=45)
        for ticker_id, ticker_symbol in wl_tickers[:50]:  # cap to avoid slow query
            result = await self.session.execute(
                select(DailyPrice.date)
                .where(DailyPrice.ticker_id == ticker_id)
                .where(DailyPrice.date >= cutoff)
                .order_by(DailyPrice.date)
            )
            rows = result.all()
            for i in range(1, len(rows)):
                delta = (rows[i][0] - rows[i - 1][0]).days
                if delta > max_gap_days:
                    gaps.append({
                        "ticker_symbol": ticker_symbol,
                        "gap_start": str(rows[i - 1][0]),
                        "gap_end": str(rows[i][0]),
                        "missing_days": delta - 1,
                    })
        return gaps[:20]

    async def check_duplicates(self) -> list[dict]:
        """Find duplicate (ticker_id, date) entries in daily_prices."""
        result = await self.session.execute(
            select(Ticker.symbol, DailyPrice.date, func.count().label("cnt"))
            .join(Ticker, Ticker.id == DailyPrice.ticker_id)
            .group_by(Ticker.symbol, DailyPrice.date)
            .having(func.count() > 1)
            .limit(20)
        )
        return [
            {"ticker_symbol": r[0], "date": str(r[1]), "count": r[2]}
            for r in result.all()
        ]

    async def check_stale_analysis(self) -> list[dict]:
        """Find watchlist tickers whose latest analysis is > 48h old."""
        threshold = date.today() - timedelta(days=2)

        # Subquery: latest analysis date per ticker
        latest = (
            select(
                AIAnalysis.ticker_id,
                func.max(AIAnalysis.analysis_date).label("latest"),
            )
            .group_by(AIAnalysis.ticker_id)
            .subquery()
        )

        # Watchlist tickers with stale or no analysis
        # UserWatchlist stores symbol — join via Ticker
        result = await self.session.execute(
            select(Ticker.symbol, latest.c.latest)
            .join(UserWatchlist, UserWatchlist.symbol == Ticker.symbol)
            .outerjoin(latest, latest.c.ticker_id == Ticker.id)
            .where(sa.or_(latest.c.latest < threshold, latest.c.latest.is_(None)))
            .limit(20)
        )
        return [
            {"ticker_symbol": r[0], "last_analysis": str(r[1]) if r[1] else None}
            for r in result.all()
        ]
