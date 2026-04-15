"""OHLCV price crawling service with batch processing and backfill.

Decisions:
- Backfill 1-2 years in batches of 50 tickers
- 2-second delay between tickers for rate limiting (~13 min for 400)
- 3 retries with exponential backoff via tenacity (on crawler)
- Persistent failures: log and skip, continue with remaining tickers
- Store raw prices; adjusted_close is NULL (corporate actions in Phase 2)
"""
import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config import settings
from app.crawlers.vnstock_crawler import VnstockCrawler
from app.models.daily_price import DailyPrice
from app.services.ticker_service import TickerService


class PriceService:
    """Manages OHLCV price data crawling and storage."""

    def __init__(self, session: AsyncSession, crawler: VnstockCrawler | None = None):
        self.session = session
        self.crawler = crawler or VnstockCrawler()
        self.ticker_service = TickerService(session, self.crawler)

    async def crawl_daily(self) -> dict:
        """Crawl today's OHLCV data for all active tickers.

        Returns: {success: int, failed: int, skipped: int, failed_symbols: list[str]}
        """
        today = date.today().isoformat()
        # Use a date range of 5 days back to catch any missed days
        start = date.today().replace(day=max(1, date.today().day - 5)).isoformat()

        ticker_map = await self.ticker_service.get_ticker_id_map()
        symbols = list(ticker_map.keys())
        logger.info(f"Starting daily crawl for {len(symbols)} tickers")

        return await self._crawl_batch(symbols, ticker_map, start, today)

    async def backfill(self, start_date: str | None = None, end_date: str | None = None) -> dict:
        """Backfill historical OHLCV data for all active tickers.

        Decision: Batches of 50 tickers, 2s delay between tickers.
        Run once on first setup. ~13 min for 400 tickers.

        Args:
            start_date: ISO format, defaults to settings.backfill_start_date (2023-07-01)
            end_date: ISO format, defaults to today
        """
        start = start_date or settings.backfill_start_date
        end = end_date or date.today().isoformat()

        ticker_map = await self.ticker_service.get_ticker_id_map()
        symbols = list(ticker_map.keys())
        logger.info(f"Starting backfill for {len(symbols)} tickers from {start} to {end}")

        return await self._crawl_batch(symbols, ticker_map, start, end)

    async def _crawl_batch(
        self, symbols: list[str], ticker_map: dict[str, int], start: str, end: str
    ) -> dict:
        """Crawl OHLCV for a list of tickers in batches with rate limiting.

        Processes in batches of settings.crawl_batch_size (50).
        2-second delay between individual tickers.
        Failed tickers are logged and skipped — batch continues.
        """
        success = 0
        failed = 0
        skipped = 0
        failed_symbols = []
        batch_size = settings.crawl_batch_size

        for batch_start in range(0, len(symbols), batch_size):
            batch = symbols[batch_start:batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            total_batches = (len(symbols) + batch_size - 1) // batch_size
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} tickers)")

            for symbol in batch:
                try:
                    df = await self.crawler.fetch_ohlcv(symbol, start, end)

                    if df is None or df.empty:
                        logger.warning(f"{symbol}: Empty data returned (holiday or suspended?)")
                        skipped += 1
                        await asyncio.sleep(settings.crawl_delay_seconds)
                        continue

                    rows_inserted = await self._store_ohlcv(symbol, ticker_map[symbol], df)
                    success += 1
                    logger.debug(f"{symbol}: {rows_inserted} rows upserted")

                except Exception as e:
                    logger.error(f"{symbol}: Failed after retries — {type(e).__name__}: {e}")
                    failed += 1
                    failed_symbols.append(symbol)

                await asyncio.sleep(settings.crawl_delay_seconds)

        await self.session.commit()

        result = {
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "failed_symbols": failed_symbols,
        }
        logger.info(f"Crawl complete: {result}")
        return result

    async def _store_ohlcv(self, symbol: str, ticker_id: int, df: pd.DataFrame) -> int:
        """Store OHLCV DataFrame into daily_prices table.

        Uses INSERT ... ON CONFLICT (ticker_id, date) DO UPDATE to handle
        re-crawls and backfill overlap gracefully.

        vnstock returns columns: time, open, high, low, close, volume
        NOTE: No adjusted_close — stored as NULL.
        """
        rows_inserted = 0

        for _, row in df.iterrows():
            # vnstock 'time' column is datetime64 — extract date
            price_date = pd.Timestamp(row["time"]).date()

            stmt = insert(DailyPrice).values(
                ticker_id=ticker_id,
                date=price_date,
                open=Decimal(str(row["open"])),
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                close=Decimal(str(row["close"])),
                volume=int(row["volume"]),
                adjusted_close=None,  # Unadjusted — Phase 2 handles corporate actions
            ).on_conflict_do_update(
                constraint="uq_daily_prices_ticker_date",
                set_={
                    "open": Decimal(str(row["open"])),
                    "high": Decimal(str(row["high"])),
                    "low": Decimal(str(row["low"])),
                    "close": Decimal(str(row["close"])),
                    "volume": int(row["volume"]),
                },
            )
            await self.session.execute(stmt)
            rows_inserted += 1

        return rows_inserted

    async def get_latest_date(self, ticker_id: int) -> date | None:
        """Get the most recent price date for a ticker."""
        result = await self.session.execute(
            select(func.max(DailyPrice.date)).where(DailyPrice.ticker_id == ticker_id)
        )
        return result.scalar_one_or_none()
