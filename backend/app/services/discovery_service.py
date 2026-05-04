"""Discovery scoring engine — scores all HOSE tickers on 6 indicator dimensions.

Pure computation: reads pre-computed indicators + financials from DB, applies
scoring functions, upserts results to discovery_results table.

No external API calls. No Gemini. Runs in < 30 seconds for ~400 tickers.
"""
from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import select, func, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_price import DailyPrice
from app.models.discovery_result import DiscoveryResult
from app.models.financial import Financial
from app.models.technical_indicator import TechnicalIndicator
from app.services.ticker_service import TickerService


# ─── Scoring Functions (0-10 scale, None if input is None) ────────────────────


def score_rsi(rsi_14: float | None) -> float | None:
    """RSI score. Oversold (< 30) = high opportunity."""
    if rsi_14 is None:
        return None
    if rsi_14 <= 30:
        return 10.0
    elif rsi_14 <= 50:
        return 10 - (rsi_14 - 30) * 0.25  # 10→5 linear
    elif rsi_14 <= 70:
        return 5 - (rsi_14 - 50) * 0.15  # 5→2 linear
    else:
        return max(0, 2 - (rsi_14 - 70) * 0.1)  # 2→0


def score_macd(macd_histogram: float | None) -> float | None:
    """MACD histogram score. Positive = bullish momentum."""
    if macd_histogram is None:
        return None
    normalized = max(-2, min(2, macd_histogram))
    return (normalized + 2) * 2.5  # Maps [-2, +2] → [0, 10]


def score_adx(adx_14: float | None, plus_di: float | None, minus_di: float | None) -> float | None:
    """ADX score. Strong uptrend = high score."""
    if adx_14 is None:
        return None
    trend_strength = min(10, adx_14 / 5)  # ADX 50 → 10
    if plus_di is not None and minus_di is not None:
        direction_bias = 1.0 if plus_di > minus_di else 0.3
    else:
        direction_bias = 0.5
    return trend_strength * direction_bias


def score_volume(avg_volume: int | None) -> float | None:
    """Volume liquidity score. Higher volume = better."""
    if avg_volume is None or avg_volume == 0:
        return None
    return min(10, avg_volume / 100_000)


def score_pe(pe: float | None) -> float | None:
    """P/E score. Lower P/E = potentially undervalued."""
    if pe is None:
        return None
    if pe <= 0:
        return 0.0
    if pe <= 10:
        return 10.0
    elif pe <= 15:
        return 10 - (pe - 10) * 0.6  # 10→7
    elif pe <= 25:
        return 7 - (pe - 15) * 0.4  # 7→3
    else:
        return max(0, 3 - (pe - 25) * 0.1)


def score_roe(roe: float | None) -> float | None:
    """ROE score. Higher efficiency = better. ROE stored as decimal (0.15 = 15%)."""
    if roe is None:
        return None
    roe_pct = float(roe) * 100
    if roe_pct >= 20:
        return 10.0
    elif roe_pct >= 15:
        return 7 + (roe_pct - 15) * 0.6
    elif roe_pct >= 10:
        return 5 + (roe_pct - 10) * 0.4
    elif roe_pct >= 5:
        return 2 + (roe_pct - 5) * 0.6
    else:
        return max(0, roe_pct * 0.4)


# ─── Discovery Service ────────────────────────────────────────────────────────


class DiscoveryService:
    """Pure-computation discovery engine — scores all HOSE tickers."""

    RETENTION_DAYS = 14
    MIN_DIMENSIONS = 2  # Skip tickers with fewer scoreable dimensions

    def __init__(self, session: AsyncSession):
        self.session = session

    async def score_all_tickers(self) -> dict:
        """Score all active HOSE tickers on 6 dimensions.

        Returns: {success: int, failed: int, skipped: int, failed_symbols: list[str]}
        """
        # 1. Cleanup old results
        cleaned = await self._cleanup_old_results()
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old discovery results")

        # 2. Get active ticker map
        ticker_svc = TickerService(self.session)
        ticker_map = await ticker_svc.get_ticker_id_map(exchange="HOSE")
        ticker_ids = list(ticker_map.values())
        id_to_symbol = {v: k for k, v in ticker_map.items()}
        logger.info(f"Scoring {len(ticker_ids)} active HOSE tickers")

        # 3. Batch fetch all data
        indicators = await self._fetch_latest_indicators(ticker_ids)
        financials = await self._fetch_latest_financials(ticker_ids)
        volumes = await self._fetch_avg_volumes(ticker_ids)

        # 4. Score each ticker
        today = date.today()
        success = 0
        skipped = 0
        failed = 0
        failed_symbols: list[str] = []
        rows_to_upsert: list[dict] = []

        for ticker_id in ticker_ids:
            symbol = id_to_symbol.get(ticker_id, "???")
            try:
                ind = indicators.get(ticker_id, {})
                fin = financials.get(ticker_id, {})
                vol = volumes.get(ticker_id)

                # Compute 6 dimension scores
                scores = {
                    "rsi_score": score_rsi(ind.get("rsi_14")),
                    "macd_score": score_macd(ind.get("macd_histogram")),
                    "adx_score": score_adx(ind.get("adx_14"), ind.get("plus_di_14"), ind.get("minus_di_14")),
                    "volume_score": score_volume(vol),
                    "pe_score": score_pe(fin.get("pe")),
                    "roe_score": score_roe(fin.get("roe")),
                }

                # Count non-NULL dimensions
                available = [v for v in scores.values() if v is not None]
                dimensions_scored = len(available)

                if dimensions_scored < self.MIN_DIMENSIONS:
                    skipped += 1
                    continue

                # Composite = average of available dimensions
                total_score = round(sum(available) / dimensions_scored, 2)

                rows_to_upsert.append({
                    "ticker_id": ticker_id,
                    "score_date": today,
                    **{k: round(v, 2) if v is not None else None for k, v in scores.items()},
                    "total_score": total_score,
                    "dimensions_scored": dimensions_scored,
                })
                success += 1

            except Exception as e:
                logger.warning(f"Failed to score {symbol}: {e}")
                failed += 1
                failed_symbols.append(symbol)

        # 5. Bulk upsert results
        if rows_to_upsert:
            await self._bulk_upsert(rows_to_upsert)
            await self.session.commit()
            logger.info(f"Upserted {len(rows_to_upsert)} discovery results")

        return {
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "failed_symbols": failed_symbols,
        }

    async def _cleanup_old_results(self) -> int:
        """Delete discovery results older than 14 days. Returns rows deleted."""
        cutoff = date.today() - timedelta(days=self.RETENTION_DAYS)
        stmt = delete(DiscoveryResult).where(DiscoveryResult.score_date < cutoff)
        result = await self.session.execute(stmt)
        deleted = result.rowcount
        await self.session.commit()
        return deleted

    async def _fetch_latest_indicators(self, ticker_ids: list[int]) -> dict[int, dict]:
        """Fetch latest technical indicators for all tickers in one batch query."""
        if not ticker_ids:
            return {}
        latest_sq = (
            select(
                TechnicalIndicator.ticker_id,
                func.max(TechnicalIndicator.date).label("max_date"),
            )
            .where(TechnicalIndicator.ticker_id.in_(ticker_ids))
            .group_by(TechnicalIndicator.ticker_id)
            .subquery()
        )
        stmt = (
            select(
                TechnicalIndicator.ticker_id,
                TechnicalIndicator.rsi_14,
                TechnicalIndicator.macd_histogram,
                TechnicalIndicator.adx_14,
                TechnicalIndicator.plus_di_14,
                TechnicalIndicator.minus_di_14,
            )
            .join(
                latest_sq,
                (TechnicalIndicator.ticker_id == latest_sq.c.ticker_id)
                & (TechnicalIndicator.date == latest_sq.c.max_date),
            )
        )
        rows = (await self.session.execute(stmt)).all()
        return {
            row.ticker_id: {
                "rsi_14": float(row.rsi_14) if row.rsi_14 is not None else None,
                "macd_histogram": float(row.macd_histogram) if row.macd_histogram is not None else None,
                "adx_14": float(row.adx_14) if row.adx_14 is not None else None,
                "plus_di_14": float(row.plus_di_14) if row.plus_di_14 is not None else None,
                "minus_di_14": float(row.minus_di_14) if row.minus_di_14 is not None else None,
            }
            for row in rows
        }

    async def _fetch_latest_financials(self, ticker_ids: list[int]) -> dict[int, dict]:
        """Fetch latest P/E and ROE for all tickers in one batch query."""
        if not ticker_ids:
            return {}
        latest_id_sq = (
            select(
                Financial.ticker_id,
                func.max(Financial.id).label("max_id"),
            )
            .where(Financial.ticker_id.in_(ticker_ids))
            .group_by(Financial.ticker_id)
            .subquery()
        )
        stmt = (
            select(Financial.ticker_id, Financial.pe, Financial.roe)
            .join(latest_id_sq, (Financial.ticker_id == latest_id_sq.c.ticker_id) & (Financial.id == latest_id_sq.c.max_id))
        )
        rows = (await self.session.execute(stmt)).all()
        return {
            row.ticker_id: {
                "pe": float(row.pe) if row.pe is not None else None,
                "roe": float(row.roe) if row.roe is not None else None,
            }
            for row in rows
        }

    async def _fetch_avg_volumes(self, ticker_ids: list[int]) -> dict[int, int | None]:
        """Fetch 20-day average volume for all tickers in one batch query."""
        if not ticker_ids:
            return {}
        cutoff_date = date.today() - timedelta(days=30)
        stmt = (
            select(
                DailyPrice.ticker_id,
                func.avg(DailyPrice.volume).label("avg_vol"),
            )
            .where(
                DailyPrice.ticker_id.in_(ticker_ids),
                DailyPrice.date >= cutoff_date,
            )
            .group_by(DailyPrice.ticker_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return {
            row.ticker_id: int(row.avg_vol) if row.avg_vol is not None else None
            for row in rows
        }

    async def _bulk_upsert(self, rows: list[dict]) -> None:
        """Upsert discovery results using PostgreSQL ON CONFLICT DO UPDATE."""
        stmt = insert(DiscoveryResult).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_discovery_results_ticker_date",
            set_={
                "rsi_score": stmt.excluded.rsi_score,
                "macd_score": stmt.excluded.macd_score,
                "adx_score": stmt.excluded.adx_score,
                "volume_score": stmt.excluded.volume_score,
                "pe_score": stmt.excluded.pe_score,
                "roe_score": stmt.excluded.roe_score,
                "total_score": stmt.excluded.total_score,
                "dimensions_scored": stmt.excluded.dimensions_scored,
            },
        )
        await self.session.execute(stmt)
