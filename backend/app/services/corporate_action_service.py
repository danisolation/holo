"""Corporate action price adjustment service.

Computes adjustment factors for corporate events and populates
adjusted_close in daily_prices using backward cumulative adjustment.

Per D-07-07: Full recompute from scratch on each run (idempotent).
Per D-07-03: Backward adjustment — most recent prices equal raw close.
"""
from datetime import date
from decimal import Decimal

from loguru import logger
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corporate_event import CorporateEvent
from app.models.daily_price import DailyPrice
from app.services.ticker_service import TickerService


class CorporateActionService:
    """Compute and apply price adjustments for corporate events."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def adjust_all_tickers(self) -> dict:
        """Recompute adjusted_close for all tickers with corporate events.

        Per D-07-07: Full recompute from scratch.
        Returns: {adjusted: int, skipped: int, failed: int, failed_symbols: list[str]}
        """
        ticker_service = TickerService(self.session)
        ticker_map = await ticker_service.get_ticker_id_map()

        adjusted = 0
        skipped = 0
        failed = 0
        failed_symbols: list[str] = []

        for symbol, ticker_id in ticker_map.items():
            try:
                count = await self.adjust_ticker(ticker_id, symbol)
                if count > 0:
                    adjusted += 1
                    logger.debug(f"{symbol}: {count} prices adjusted")
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"{symbol}: Adjustment failed — {type(e).__name__}: {e}")
                failed += 1
                failed_symbols.append(symbol)

        await self.session.commit()

        result = {
            "adjusted": adjusted,
            "skipped": skipped,
            "failed": failed,
            "failed_symbols": failed_symbols,
        }
        logger.info(f"Corporate action adjustment complete: {result}")
        return result

    async def adjust_ticker(self, ticker_id: int, symbol: str = "") -> int:
        """Recompute adjusted_close for a single ticker.

        Returns number of prices updated.
        """
        # 1. Get all events for this ticker, sorted by ex_date DESC
        events_result = await self.session.execute(
            select(CorporateEvent)
            .where(CorporateEvent.ticker_id == ticker_id)
            .order_by(CorporateEvent.ex_date.desc())
        )
        events = list(events_result.scalars().all())

        # 2. Get all daily prices, sorted by date DESC (most recent first)
        prices_result = await self.session.execute(
            select(DailyPrice.id, DailyPrice.date, DailyPrice.close)
            .where(DailyPrice.ticker_id == ticker_id)
            .order_by(DailyPrice.date.desc())
        )
        prices = prices_result.fetchall()

        if not prices:
            return 0

        # If no events, set adjusted_close = close for all prices
        if not events:
            await self.session.execute(
                update(DailyPrice)
                .where(
                    and_(
                        DailyPrice.ticker_id == ticker_id,
                        DailyPrice.adjusted_close.is_(None),
                    )
                )
                .values(adjusted_close=DailyPrice.close)
            )
            return len(prices)

        # 3. Compute adjustment factors for each event
        factors = await self._compute_event_factors(events, ticker_id)

        # 4. Apply backward cumulative adjustment
        adjustments = self._compute_adjusted_prices(prices, factors)

        # 5. Bulk update adjusted_close
        updated = await self._bulk_update_adjusted_close(ticker_id, adjustments)

        return updated

    async def _compute_event_factors(
        self, events: list[CorporateEvent], ticker_id: int
    ) -> list[tuple[date, Decimal]]:
        """Compute adjustment factor for each event.

        Returns list of (ex_date, factor) tuples sorted by ex_date DESC.
        Factors are < 1.0 — they reduce historical prices.
        """
        factors = []
        for event in events:
            factor = await self._compute_single_factor(event, ticker_id)

            # Sanity check: factors should be between 0.3 and 1.0
            if factor <= Decimal("0") or factor > Decimal("1.0"):
                logger.warning(
                    f"Suspicious factor {factor} for event {event.event_source_id} "
                    f"(type={event.event_type}, ex_date={event.ex_date}) — skipping"
                )
                continue
            if factor < Decimal("0.3"):
                logger.warning(
                    f"Very low factor {factor} for event {event.event_source_id} — applying but flagging"
                )

            # Cache the factor on the event record
            event.adjustment_factor = factor
            factors.append((event.ex_date, factor))

        return factors

    async def _compute_single_factor(self, event: CorporateEvent, ticker_id: int) -> Decimal:
        """Compute adjustment factor for a single corporate event.

        CRITICAL FORMULAS (per 07-RESEARCH.md, corrected from CONTEXT.md):
        - CASH_DIVIDEND: (close_before - dividend) / close_before
        - STOCK_DIVIDEND: 100 / (100 + ratio)  [ratio is per 100 shares]
        - BONUS_SHARES:   100 / (100 + ratio)  [ratio is per 100 shares]
        - RIGHTS_ISSUE:   1.0 (no price adjustment — rights are voluntary,
          user may or may not subscribe; dilution shown separately in UI)
        """
        if event.event_type == "RIGHTS_ISSUE":
            # Per CONTEXT.md: rights are optional, user may or may not subscribe
            # → NO price adjustment for rights issues. Dilution impact is
            # displayed separately in the UI as an info badge.
            return Decimal("1.0")

        if event.event_type == "CASH_DIVIDEND":
            if not event.dividend_amount or event.dividend_amount <= 0:
                return Decimal("1.0")

            close_before = await self._get_close_before(ticker_id, event.ex_date)
            if not close_before or close_before <= 0:
                logger.warning(
                    f"No close_before found for {event.event_source_id} "
                    f"(ex_date={event.ex_date}) — skipping"
                )
                return Decimal("1.0")

            return (close_before - event.dividend_amount) / close_before

        elif event.event_type in ("STOCK_DIVIDEND", "BONUS_SHARES"):
            if not event.ratio or event.ratio <= 0:
                return Decimal("1.0")

            # factor = 100 / (100 + ratio) where ratio = shares per 100 existing
            # Example: ratio=35 → 100/135 = 0.7407
            return Decimal("100") / (Decimal("100") + event.ratio)

        return Decimal("1.0")

    async def _get_close_before(self, ticker_id: int, ex_date: date) -> Decimal | None:
        """Get closing price on the trading day immediately before ex_date."""
        result = await self.session.execute(
            select(DailyPrice.close)
            .where(
                and_(
                    DailyPrice.ticker_id == ticker_id,
                    DailyPrice.date < ex_date,
                )
            )
            .order_by(DailyPrice.date.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row if row is not None else None

    def _compute_adjusted_prices(
        self,
        prices: list,
        factors: list[tuple[date, Decimal]],
    ) -> list[tuple[int, Decimal]]:
        """Apply backward cumulative adjustment.

        prices: sorted by date DESC (most recent first)
        factors: sorted by ex_date DESC (most recent first)

        Returns: list of (price_id, adjusted_close) tuples.
        """
        adjustments = []
        cumulative = Decimal("1.0")
        factor_idx = 0

        for price_id, price_date, close in prices:
            # Apply any events whose ex_date is after this price date
            while factor_idx < len(factors) and factors[factor_idx][0] > price_date:
                cumulative *= factors[factor_idx][1]
                factor_idx += 1

            adjusted = (close * cumulative).quantize(Decimal("0.01"))
            adjustments.append((price_id, adjusted))

        return adjustments

    async def _bulk_update_adjusted_close(
        self, ticker_id: int, adjustments: list[tuple[int, Decimal]]
    ) -> int:
        """Bulk update adjusted_close for a ticker's prices."""
        if not adjustments:
            return 0

        batch_size = 500
        updated = 0

        for i in range(0, len(adjustments), batch_size):
            batch = adjustments[i : i + batch_size]
            for price_id, adj_close in batch:
                await self.session.execute(
                    update(DailyPrice)
                    .where(DailyPrice.id == price_id)
                    .values(adjusted_close=adj_close)
                )
            updated += len(batch)

        return updated
