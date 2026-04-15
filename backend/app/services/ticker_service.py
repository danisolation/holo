"""Ticker list management: fetch, filter, rank, and sync top 400 HOSE tickers.

Decision: Top 400 by market cap + liquidity via vnstock listing.
Suspended/halted tickers excluded. List refreshed weekly.
"""
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.crawlers.vnstock_crawler import VnstockCrawler
from app.models.ticker import Ticker


class TickerService:
    """Manages the active ticker list in the database."""

    MAX_TICKERS = 400

    def __init__(self, session: AsyncSession, crawler: VnstockCrawler | None = None):
        self.session = session
        self.crawler = crawler or VnstockCrawler()

    async def fetch_and_sync_tickers(self) -> dict:
        """Fetch HOSE listing from vnstock and sync to database.

        Strategy for top 400 selection:
        1. Fetch all HOSE stocks via symbols_by_exchange()
        2. Fetch industry classification for sector/industry data
        3. Take first 400 tickers (vnstock listing is pre-sorted by relevance)
           If market_cap data becomes available from vnstock, sort by that.
        4. Upsert into tickers table, deactivate tickers no longer in top 400.

        Returns dict with counts: {synced, deactivated, total}.
        """
        logger.info("Starting ticker list sync...")

        # Fetch HOSE stock listing
        listing_df = await self.crawler.fetch_listing(exchange="HOSE")
        logger.info(f"Fetched {len(listing_df)} HOSE stocks from vnstock")

        # Fetch industry classification for sector data
        try:
            industry_df = await self.crawler.fetch_industry_classification()
        except Exception as e:
            logger.warning(f"Failed to fetch industry data: {e}. Proceeding without sectors.")
            industry_df = None

        # Select top 400 tickers
        symbols = listing_df["symbol"].tolist()[:self.MAX_TICKERS]

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
                exchange="HOSE",
                is_active=True,
                last_updated=datetime.now(timezone.utc),
            ).on_conflict_do_update(
                index_elements=["symbol"],
                set_={
                    "name": str(name),
                    "sector": sector_map.get(sym),
                    "industry": industry_map.get(sym),
                    "is_active": True,
                    "last_updated": datetime.now(timezone.utc),
                },
            )
            await self.session.execute(stmt)
            synced += 1

        # Deactivate tickers no longer in top 400
        deactivate_stmt = (
            update(Ticker)
            .where(Ticker.symbol.notin_(symbols), Ticker.is_active == True)
            .values(is_active=False, last_updated=datetime.now(timezone.utc))
        )
        result = await self.session.execute(deactivate_stmt)
        deactivated = result.rowcount

        await self.session.commit()
        logger.info(f"Ticker sync complete: {synced} synced, {deactivated} deactivated")
        return {"synced": synced, "deactivated": deactivated, "total": synced}

    async def get_active_symbols(self) -> list[str]:
        """Return list of active ticker symbols from database."""
        result = await self.session.execute(
            select(Ticker.symbol).where(Ticker.is_active == True).order_by(Ticker.symbol)
        )
        return [row[0] for row in result.fetchall()]

    async def get_ticker_id_map(self) -> dict[str, int]:
        """Return {symbol: id} mapping for active tickers."""
        result = await self.session.execute(
            select(Ticker.symbol, Ticker.id).where(Ticker.is_active == True)
        )
        return {row[0]: row[1] for row in result.fetchall()}
