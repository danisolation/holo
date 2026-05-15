"""Ticker list management: fetch, filter, rank, and sync tickers per exchange.

Decision: Per-exchange ticker limits — HOSE=400, HNX=200, UPCOM=200.
Suspended/halted tickers excluded. List refreshed weekly.
Deactivation is scoped per-exchange to prevent cross-exchange data corruption.
"""
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, update, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import httpx

from app.crawlers.vnstock_crawler import VnstockCrawler
from app.models.ticker import Ticker
from app.config import settings

# Per-exchange maximum ticker limits
EXCHANGE_MAX_TICKERS: dict[str, int] = {
    "HOSE": 400,
    "HNX": 200,
    "UPCOM": 200,
}

# ICB classification mapping (Vietnam/HOSE numbering via Fireant)
# First 2 digits → Sector (Level 1)
ICB_SECTORS: dict[str, str] = {
    "10": "Công nghệ",
    "15": "Viễn thông",
    "20": "Y tế",
    "25": "Hàng & Dịch vụ CN",
    "30": "Tài chính",
    "35": "Bất động sản",
    "40": "Hàng tiêu dùng",
    "45": "Thực phẩm & Đồ uống",
    "50": "Xây dựng & Vật liệu",
    "55": "Nguyên vật liệu",
    "60": "Dầu khí",
    "65": "Tiện ích",
}

# First 4 digits → Industry (Level 2)
ICB_INDUSTRIES: dict[str, str] = {
    "1010": "Công nghệ thông tin",
    "1510": "Viễn thông",
    "2010": "Dược phẩm & Y tế",
    "2510": "Hàng & Dịch vụ CN",
    "3010": "Ngân hàng",
    "3020": "Chứng khoán",
    "3030": "Bảo hiểm",
    "3510": "Bất động sản",
    "4010": "Ô tô & Phụ tùng",
    "4020": "Hàng cá nhân & Gia dụng",
    "4030": "Truyền thông & Giải trí",
    "4040": "Bán lẻ",
    "4050": "Vận tải & Du lịch",
    "4510": "Thực phẩm & Đồ uống",
    "5010": "Xây dựng & Vật liệu",
    "5510": "Thép & Kim loại",
    "5520": "Hóa chất",
    "6010": "Dầu khí",
    "6510": "Điện, Nước & Khí đốt",
}


def icb_to_sector(icb_code: str) -> str:
    """Map ICB code (first 2 digits) to Vietnamese sector name."""
    if not icb_code or len(icb_code) < 2:
        return "Khác"
    return ICB_SECTORS.get(icb_code[:2], "Khác")


def icb_to_industry(icb_code: str) -> str:
    """Map ICB code (first 4 digits) to Vietnamese industry name."""
    if not icb_code or len(icb_code) < 4:
        return icb_to_sector(icb_code)
    return ICB_INDUSTRIES.get(icb_code[:4], icb_to_sector(icb_code))


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
            logger.warning(f"Failed to fetch industry data from vnstock: {e}. Will try Fireant fallback.")
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

        # If vnstock industry data was unavailable, enrich from Fireant
        if industry_df is None or industry_df.empty:
            try:
                enrich_result = await self.enrich_sectors_from_fireant()
                logger.info(f"Fireant sector fallback: {enrich_result['updated']} tickers enriched")
            except Exception as e:
                logger.warning(f"Fireant sector enrichment failed: {e}")

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

    async def enrich_sectors_from_fireant(self) -> dict:
        """Fetch ICB sector/industry from Fireant API and update tickers.

        Fireant provides icbCode (8-digit ICB) per symbol. We map first 2 digits
        to sector and first 4 digits to industry using Vietnamese ICB naming.

        Returns: {updated: int, failed: list[str], sectors: dict[str, int]}
        """
        token = settings.fireant_token
        if not token:
            logger.warning("Sector enrichment skipped: fireant_token not configured")
            return {"updated": 0, "failed": [], "sectors": {}}

        # Get all active tickers
        result = await self.session.execute(
            select(Ticker.id, Ticker.symbol).where(Ticker.is_active == True).order_by(Ticker.symbol)
        )
        tickers = [(row[0], row[1]) for row in result.fetchall()]
        logger.info(f"Enriching sectors for {len(tickers)} tickers from Fireant...")

        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"}
        updates = {}
        failed = []

        async with httpx.AsyncClient(verify=False, timeout=15, headers=headers) as client:
            for i, (tid, symbol) in enumerate(tickers):
                try:
                    r = await client.get(f"https://restv2.fireant.vn/symbols/{symbol}")
                    if r.status_code == 200:
                        data = r.json()
                        icb = data.get("icbCode", "") or ""
                        updates[symbol] = {
                            "id": tid,
                            "sector": icb_to_sector(icb),
                            "industry": icb_to_industry(icb),
                        }
                    elif r.status_code == 401:
                        logger.error("Fireant token expired during sector enrichment")
                        break
                    else:
                        failed.append(symbol)
                except Exception:
                    failed.append(symbol)

                if (i + 1) % 50 == 0:
                    logger.info(f"  Sector enrichment: {i+1}/{len(tickers)}...")
                await asyncio.sleep(0.2)

        # Apply updates
        for info in updates.values():
            await self.session.execute(
                update(Ticker)
                .where(Ticker.id == info["id"])
                .values(sector=info["sector"], industry=info["industry"])
            )
        await self.session.commit()

        # Count by sector
        sectors: dict[str, int] = {}
        for info in updates.values():
            s = info["sector"]
            sectors[s] = sectors.get(s, 0) + 1

        logger.info(
            f"Sector enrichment complete: {len(updates)} updated, "
            f"{len(failed)} failed, {len(sectors)} sectors"
        )
        return {"updated": len(updates), "failed": failed, "sectors": sectors}
