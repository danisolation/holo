"""Ticker list management: fetch, filter, rank, and sync tickers per exchange.

Decision: Per-exchange ticker limits — HOSE=400, HNX=200, UPCOM=200.
Suspended/halted tickers excluded. List refreshed weekly.
Deactivation is scoped per-exchange to prevent cross-exchange data corruption.
"""
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.crawlers.vnstock_crawler import VnstockCrawler
from app.models.ticker import Ticker

# Per-exchange maximum ticker limits
EXCHANGE_MAX_TICKERS: dict[str, int] = {
    "HOSE": 400,
    "HNX": 200,
    "UPCOM": 200,
}


class TickerService:
    """Manages the active ticker list in the database."""

    EXCHANGE_MAX_TICKERS = EXCHANGE_MAX_TICKERS

    def __init__(self, session: AsyncSession, crawler: VnstockCrawler | None = None):
        self.session = session
        self.crawler = crawler or VnstockCrawler()

    async def fetch_and_sync_tickers(self, exchange: str = "HOSE") -> dict:
        """Fetch stock listing for given exchange from vnstock and sync to database.

        Strategy for ticker selection:
        1. Fetch all stocks for the exchange via symbols_by_exchange()
        2. Fetch industry classification for sector/industry data
        3. Take first N tickers per EXCHANGE_MAX_TICKERS (HOSE=400, HNX=200, UPCOM=200)
        4. Upsert into tickers table, deactivate tickers no longer in top N
           CRITICAL: Deactivation is scoped per-exchange to prevent cross-exchange corruption

        Returns dict with counts: {synced, deactivated, total}.
        """
        if exchange not in self.EXCHANGE_MAX_TICKERS:
            raise ValueError(
                f"Invalid exchange: {exchange}. "
                f"Must be one of {list(self.EXCHANGE_MAX_TICKERS.keys())}"
            )
        max_tickers = self.EXCHANGE_MAX_TICKERS[exchange]
        logger.info(f"Starting ticker list sync for {exchange} (max {max_tickers})...")

        # Fetch stock listing for the exchange
        listing_df = await self.crawler.fetch_listing(exchange=exchange)
        logger.info(f"Fetched {len(listing_df)} {exchange} stocks from vnstock")

        # Fetch industry classification for sector data
        try:
            industry_df = await self.crawler.fetch_industry_classification()
        except Exception as e:
            logger.warning(f"Failed to fetch industry data: {e}. Proceeding without sectors.")
            industry_df = None

        # Select top N tickers for this exchange
        symbols = listing_df["symbol"].tolist()[:max_tickers]

        # Build sector/industry lookup from industry classification
        sector_map = {}
        industry_map = {}
        if industry_df is not None and not industry_df.empty:
            for _, row in industry_df.iterrows():
                sym = row.get("symbol", "")
                sector_map[sym] = row.get("icb_name2", None)
                industry_map[sym] = row.get("icb_name3", None)

        # Upsert tickers
        synced = 0
        for _, row in listing_df.iterrows():
            sym = row["symbol"]
            if sym not in symbols:
                continue

            name = row.get("organ_name", row.get("organ_short_name", sym))
            stmt = insert(Ticker).values(
                symbol=sym,
                name=str(name),
                sector=sector_map.get(sym),
                industry=industry_map.get(sym),
                exchange=exchange,
                is_active=True,
                last_updated=datetime.now(timezone.utc),
            ).on_conflict_do_update(
                index_elements=["symbol"],
                set_={
                    "name": str(name),
                    "sector": sector_map.get(sym),
                    "industry": industry_map.get(sym),
                    "exchange": exchange,
                    "is_active": True,
                    "last_updated": datetime.now(timezone.utc),
                },
            )
            await self.session.execute(stmt)
            synced += 1

        # Deactivate tickers no longer in top N — SCOPED PER EXCHANGE
        # Without exchange filter, syncing HNX would deactivate ALL HOSE tickers
        deactivate_stmt = (
            update(Ticker)
            .where(
                Ticker.symbol.notin_(symbols),
                Ticker.exchange == exchange,
                Ticker.is_active == True,
            )
            .values(is_active=False, last_updated=datetime.now(timezone.utc))
        )
        result = await self.session.execute(deactivate_stmt)
        deactivated = result.rowcount

        await self.session.commit()
        logger.info(f"Ticker sync complete ({exchange}): {synced} synced, {deactivated} deactivated")
        return {"synced": synced, "deactivated": deactivated, "total": synced}

    async def get_active_symbols(self, exchange: str | None = None) -> list[str]:
        """Return list of active ticker symbols, optionally filtered by exchange."""
        stmt = select(Ticker.symbol).where(Ticker.is_active == True)
        if exchange:
            stmt = stmt.where(Ticker.exchange == exchange)
        result = await self.session.execute(stmt.order_by(Ticker.symbol))
        return [row[0] for row in result.fetchall()]

    async def get_ticker_id_map(self, exchange: str | None = None) -> dict[str, int]:
        """Return {symbol: id} mapping for active tickers, optionally filtered by exchange."""
        stmt = select(Ticker.symbol, Ticker.id).where(Ticker.is_active == True)
        if exchange:
            stmt = stmt.where(Ticker.exchange == exchange)
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.fetchall()}
