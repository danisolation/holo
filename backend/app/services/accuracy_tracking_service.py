"""AI Accuracy Tracking Service — verifies AI predictions against actual prices.

Phase 65: Runs daily after market close. For each combined analysis signal
from 1, 3, and 7 days ago, looks up actual closing price and determines
if the prediction was correct.

Verdict logic:
- mua (buy) + price went up → correct
- ban (sell) + price went down → correct
- giu (hold) + price stayed within ±2% → correct
- Otherwise → incorrect
"""
from datetime import date, timedelta

from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_accuracy import AIAccuracy
from app.models.ai_analysis import AIAnalysis, AnalysisType
from app.models.daily_price import DailyPrice
from app.models.ticker import Ticker


# Thresholds
HOLD_THRESHOLD_PCT = 2.0  # ±2% counts as "hold correct"


def compute_verdict(direction: str, pct_change: float) -> str:
    """Determine if prediction was correct based on direction and price change."""
    direction = direction.lower()
    if direction == "mua":
        return "correct" if pct_change > 0 else "incorrect"
    elif direction == "ban":
        return "correct" if pct_change < 0 else "incorrect"
    elif direction == "giu":
        return "correct" if abs(pct_change) <= HOLD_THRESHOLD_PCT else "incorrect"
    return "pending"


class AccuracyTrackingService:
    """Tracks AI prediction accuracy by comparing against actual prices."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def backfill_accuracy(self, today: date | None = None) -> dict:
        """Main entry point: backfill accuracy data for signals from 1/3/7 days ago.

        Returns summary dict with counts.
        """
        today = today or date.today()
        lookback_days = [1, 3, 7]
        total_created = 0
        total_updated = 0

        for days_ago in lookback_days:
            target_date = today - timedelta(days=days_ago)
            created, updated = await self._process_date(target_date, today, days_ago)
            total_created += created
            total_updated += updated

        await self.session.commit()
        return {
            "created": total_created,
            "updated": total_updated,
            "date": str(today),
        }

    async def _process_date(
        self, analysis_date: date, today: date, days_ago: int
    ) -> tuple[int, int]:
        """Process all combined analyses for a specific date.

        Creates AIAccuracy rows for new analyses, updates existing ones
        with price data for the appropriate lookback period.
        """
        # Get combined analyses for this date
        analyses = await self.session.execute(
            select(AIAnalysis)
            .where(
                and_(
                    AIAnalysis.analysis_type == AnalysisType.COMBINED,
                    AIAnalysis.analysis_date == analysis_date,
                )
            )
        )
        analysis_rows = analyses.scalars().all()
        if not analysis_rows:
            return 0, 0

        # Get ticker IDs and their symbols for logging
        ticker_ids = [a.ticker_id for a in analysis_rows]

        # Get signal-day closing prices
        signal_prices = await self._get_prices_for_date(ticker_ids, analysis_date)
        # Get today's closing prices (the "actual" price after N days)
        current_prices = await self._get_prices_for_date(ticker_ids, today)

        created = 0
        updated = 0

        for analysis in analysis_rows:
            tid = analysis.ticker_id
            signal_price = signal_prices.get(tid)
            current_price = current_prices.get(tid)

            if not signal_price or not current_price:
                continue

            pct_change = ((current_price - signal_price) / signal_price) * 100
            direction = analysis.signal  # mua/ban/giu
            verdict = compute_verdict(direction, pct_change)

            # Determine which column to update based on days_ago
            price_col = f"price_at_{days_ago}d"
            pct_col = f"pct_change_{days_ago}d"
            verdict_col = f"verdict_{days_ago}d"

            # Upsert: create if not exists, update price/verdict columns
            existing = await self.session.execute(
                select(AIAccuracy).where(
                    and_(
                        AIAccuracy.ticker_id == tid,
                        AIAccuracy.analysis_date == analysis_date,
                    )
                )
            )
            row = existing.scalar_one_or_none()

            if row is None:
                row = AIAccuracy(
                    ticker_id=tid,
                    analysis_date=analysis_date,
                    direction_predicted=direction,
                    confidence=analysis.score,
                    price_at_signal=signal_price,
                )
                self.session.add(row)
                await self.session.flush()
                created += 1

            # Set the appropriate day's data
            setattr(row, price_col, current_price)
            setattr(row, pct_col, round(pct_change, 2))
            setattr(row, verdict_col, verdict)
            updated += 1

        logger.info(
            f"Accuracy backfill for {analysis_date} ({days_ago}d): "
            f"{created} created, {updated} updated"
        )
        return created, updated

    async def _get_prices_for_date(
        self, ticker_ids: list[int], target_date: date
    ) -> dict[int, float]:
        """Get closing prices for tickers on a specific date.

        If exact date has no data (weekend/holiday), looks back up to 3 days.
        """
        result = await self.session.execute(
            select(DailyPrice.ticker_id, DailyPrice.close)
            .where(
                and_(
                    DailyPrice.ticker_id.in_(ticker_ids),
                    DailyPrice.date >= target_date - timedelta(days=3),
                    DailyPrice.date <= target_date,
                )
            )
            .order_by(DailyPrice.date.desc())
        )
        # Keep the most recent price per ticker (closest to target_date)
        prices: dict[int, float] = {}
        for row in result.all():
            if row.ticker_id not in prices:
                prices[row.ticker_id] = float(row.close)
        return prices

    async def get_accuracy_stats(self, days: int = 30) -> dict:
        """Get accuracy statistics for the dashboard.

        Returns overall %, per-direction %, and rolling trend data.
        """
        cutoff = date.today() - timedelta(days=days)

        rows = await self.session.execute(
            select(AIAccuracy)
            .where(AIAccuracy.analysis_date >= cutoff)
            .where(AIAccuracy.verdict_7d.isnot(None))
        )
        records = rows.scalars().all()

        if not records:
            return {
                "total": 0,
                "overall_accuracy_pct": 0,
                "by_direction": {},
                "period_days": days,
            }

        total = len(records)
        correct = sum(1 for r in records if r.verdict_7d == "correct")

        # Per-direction breakdown
        by_direction: dict[str, dict] = {}
        for direction in ("mua", "ban", "giu"):
            dir_records = [r for r in records if r.direction_predicted == direction]
            if dir_records:
                dir_correct = sum(1 for r in dir_records if r.verdict_7d == "correct")
                by_direction[direction] = {
                    "total": len(dir_records),
                    "correct": dir_correct,
                    "accuracy_pct": round(dir_correct / len(dir_records) * 100, 1),
                }

        # Per-timeframe accuracy
        by_timeframe: dict[str, dict] = {}
        for tf, col in [("1d", "verdict_1d"), ("3d", "verdict_3d"), ("7d", "verdict_7d")]:
            tf_records = [r for r in records if getattr(r, col) is not None]
            if tf_records:
                tf_correct = sum(1 for r in tf_records if getattr(r, col) == "correct")
                by_timeframe[tf] = {
                    "total": len(tf_records),
                    "correct": tf_correct,
                    "accuracy_pct": round(tf_correct / len(tf_records) * 100, 1),
                }

        return {
            "total": total,
            "correct": correct,
            "overall_accuracy_pct": round(correct / total * 100, 1) if total else 0,
            "by_direction": by_direction,
            "by_timeframe": by_timeframe,
            "period_days": days,
        }

    async def get_ticker_accuracy(self, ticker_id: int, days: int = 30) -> dict:
        """Get accuracy stats for a specific ticker."""
        cutoff = date.today() - timedelta(days=days)

        rows = await self.session.execute(
            select(AIAccuracy)
            .where(
                and_(
                    AIAccuracy.ticker_id == ticker_id,
                    AIAccuracy.analysis_date >= cutoff,
                    AIAccuracy.verdict_7d.isnot(None),
                )
            )
            .order_by(AIAccuracy.analysis_date.desc())
        )
        records = rows.scalars().all()

        if not records:
            return {"total": 0, "accuracy_pct": 0, "history": []}

        total = len(records)
        correct = sum(1 for r in records if r.verdict_7d == "correct")

        history = [
            {
                "date": str(r.analysis_date),
                "predicted": r.direction_predicted,
                "confidence": r.confidence,
                "pct_change_7d": r.pct_change_7d,
                "verdict": r.verdict_7d,
            }
            for r in records[:20]
        ]

        return {
            "total": total,
            "correct": correct,
            "accuracy_pct": round(correct / total * 100, 1) if total else 0,
            "history": history,
        }
