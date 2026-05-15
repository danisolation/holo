"""Market breadth computation service — market-wide health indicators for HOSE.

Computes 3 breadth metrics from existing DailyPrice and TechnicalIndicator tables:
1. A/D Line — daily advancing vs declining tickers (close vs previous close)
2. MA Breadth — % of tickers above SMA50 and SMA200
3. 52-Week Highs/Lows — daily new high/low counts (rolling 252 trading days)

Uses pandas for efficient batch computation. No new DB tables needed.
"""
from datetime import date, timedelta

import pandas as pd
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_price import DailyPrice
from app.models.technical_indicator import TechnicalIndicator
from app.services.ticker_service import TickerService


class MarketBreadthService:
    """Compute market-wide breadth indicators for HOSE tickers."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_hose_ticker_ids(self) -> list[int]:
        """Get list of active HOSE ticker IDs."""
        ticker_svc = TickerService(self.session)
        ticker_map = await ticker_svc.get_ticker_id_map(exchange="HOSE")
        return list(ticker_map.values())

    async def get_ad_line(self, start_date: date, end_date: date) -> list[dict]:
        """Compute advance/decline line for date range.

        For each date, counts tickers where close > previous close (advancing),
        close < previous close (declining), and close == previous close (unchanged).
        Fetches one extra day before start_date for the diff calculation.
        """
        ticker_ids = await self._get_hose_ticker_ids()
        if not ticker_ids:
            return []

        # Fetch prices with 1-day buffer before start for diff
        buffer_start = start_date - timedelta(days=10)  # calendar days buffer
        stmt = (
            select(DailyPrice.ticker_id, DailyPrice.date, DailyPrice.close)
            .where(
                DailyPrice.ticker_id.in_(ticker_ids),
                DailyPrice.date >= buffer_start,
                DailyPrice.date <= end_date,
            )
            .order_by(DailyPrice.ticker_id, DailyPrice.date)
        )
        result = await self.session.execute(stmt)
        rows = result.fetchall()

        if not rows:
            return []

        df = pd.DataFrame(
            [(r.ticker_id, r.date, float(r.close)) for r in rows],
            columns=["ticker_id", "date", "close"],
        )

        # Compute daily change per ticker
        df["change"] = df.groupby("ticker_id")["close"].diff()

        # Filter to requested date range (drop buffer days)
        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
        df = df.dropna(subset=["change"])

        if df.empty:
            return []

        # Group by date and count
        def _classify(group):
            return pd.Series({
                "advancing": int((group["change"] > 0).sum()),
                "declining": int((group["change"] < 0).sum()),
                "unchanged": int((group["change"] == 0).sum()),
            })

        daily = df.groupby("date").apply(_classify, include_groups=False).reset_index()
        daily["net"] = daily["advancing"] - daily["declining"]
        daily = daily.sort_values("date")

        return [
            {
                "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                "advancing": int(row["advancing"]),
                "declining": int(row["declining"]),
                "unchanged": int(row["unchanged"]),
                "net": int(row["net"]),
            }
            for _, row in daily.iterrows()
        ]

    async def get_ma_breadth(self, start_date: date, end_date: date) -> list[dict]:
        """Compute MA breadth — % of tickers above SMA50 and SMA200.

        Joins DailyPrice with TechnicalIndicator to compare close vs SMA values.
        Tickers with NULL SMA are excluded from the respective metric.
        """
        ticker_ids = await self._get_hose_ticker_ids()
        if not ticker_ids:
            return []

        # Join DailyPrice with TechnicalIndicator
        stmt = (
            select(
                DailyPrice.ticker_id,
                DailyPrice.date,
                DailyPrice.close,
                TechnicalIndicator.sma_50,
                TechnicalIndicator.sma_200,
            )
            .join(
                TechnicalIndicator,
                (DailyPrice.ticker_id == TechnicalIndicator.ticker_id)
                & (DailyPrice.date == TechnicalIndicator.date),
            )
            .where(
                DailyPrice.ticker_id.in_(ticker_ids),
                DailyPrice.date >= start_date,
                DailyPrice.date <= end_date,
            )
            .order_by(DailyPrice.date)
        )
        result = await self.session.execute(stmt)
        rows = result.fetchall()

        if not rows:
            return []

        df = pd.DataFrame(
            [
                (r.ticker_id, r.date, float(r.close),
                 float(r.sma_50) if r.sma_50 is not None else None,
                 float(r.sma_200) if r.sma_200 is not None else None)
                for r in rows
            ],
            columns=["ticker_id", "date", "close", "sma_50", "sma_200"],
        )

        results = []
        for dt, group in df.groupby("date"):
            total = len(group)

            # MA50: only count tickers with non-null sma_50
            ma50_valid = group.dropna(subset=["sma_50"])
            above_ma50 = int((ma50_valid["close"] > ma50_valid["sma_50"]).sum())

            # MA200: only count tickers with non-null sma_200
            ma200_valid = group.dropna(subset=["sma_200"])
            above_ma200 = int((ma200_valid["close"] > ma200_valid["sma_200"]).sum())

            pct_ma50 = round(above_ma50 / total * 100, 1) if total > 0 else 0.0
            pct_ma200 = round(above_ma200 / total * 100, 1) if total > 0 else 0.0

            results.append({
                "date": dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
                "total_tickers": total,
                "above_ma50": above_ma50,
                "above_ma200": above_ma200,
                "pct_above_ma50": pct_ma50,
                "pct_above_ma200": pct_ma200,
            })

        return sorted(results, key=lambda x: x["date"])

    async def get_highs_lows(self, start_date: date, end_date: date) -> list[dict]:
        """Compute daily new 52-week highs and lows.

        For each date in range, checks if each ticker's close equals its
        rolling 252-day max (new high) or min (new low).
        Tickers with fewer than 252 trading days are excluded.
        """
        ticker_ids = await self._get_hose_ticker_ids()
        if not ticker_ids:
            return []

        # 370 calendar day buffer for ~252 trading days
        buffer_start = start_date - timedelta(days=370)
        stmt = (
            select(DailyPrice.ticker_id, DailyPrice.date, DailyPrice.close)
            .where(
                DailyPrice.ticker_id.in_(ticker_ids),
                DailyPrice.date >= buffer_start,
                DailyPrice.date <= end_date,
            )
            .order_by(DailyPrice.ticker_id, DailyPrice.date)
        )
        result = await self.session.execute(stmt)
        rows = result.fetchall()

        if not rows:
            return []

        df = pd.DataFrame(
            [(r.ticker_id, r.date, float(r.close)) for r in rows],
            columns=["ticker_id", "date", "close"],
        )

        # Compute rolling 252-day max/min per ticker
        all_results = []
        for ticker_id, ticker_df in df.groupby("ticker_id"):
            if len(ticker_df) < 252:
                continue  # insufficient history

            ticker_df = ticker_df.sort_values("date").reset_index(drop=True)
            ticker_df["rolling_max"] = ticker_df["close"].rolling(252, min_periods=252).max()
            ticker_df["rolling_min"] = ticker_df["close"].rolling(252, min_periods=252).min()

            # Filter to requested date range
            mask = (ticker_df["date"] >= start_date) & (ticker_df["date"] <= end_date)
            filtered = ticker_df[mask].dropna(subset=["rolling_max", "rolling_min"])

            filtered = filtered.copy()
            filtered["is_new_high"] = filtered["close"] >= filtered["rolling_max"]
            filtered["is_new_low"] = filtered["close"] <= filtered["rolling_min"]
            all_results.append(filtered[["date", "is_new_high", "is_new_low"]])

        if not all_results:
            return []

        combined = pd.concat(all_results, ignore_index=True)
        daily = combined.groupby("date").agg(
            new_highs=("is_new_high", "sum"),
            new_lows=("is_new_low", "sum"),
        ).reset_index()
        daily = daily.sort_values("date")

        return [
            {
                "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                "new_highs": int(row["new_highs"]),
                "new_lows": int(row["new_lows"]),
            }
            for _, row in daily.iterrows()
        ]

    async def get_all_breadth(self, start_date: date, end_date: date) -> dict:
        """Get all 3 breadth metrics in one call.

        Orchestrates A/D line, MA breadth, and 52-week highs/lows.
        Returns dict matching MarketBreadthResponse shape.
        """
        ad_line = await self.get_ad_line(start_date, end_date)
        ma_breadth = await self.get_ma_breadth(start_date, end_date)
        highs_lows = await self.get_highs_lows(start_date, end_date)

        return {
            "ad_line": ad_line,
            "ma_breadth": ma_breadth,
            "highs_lows": highs_lows,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
