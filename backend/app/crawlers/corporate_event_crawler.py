"""Corporate events crawler — VNDirect REST API.

Fetches dividends, stock dividends, and bonus shares from VNDirect's
public events API. Stores with deduplication via event_source_id.

CRITICAL: Uses VNDirect REST API directly, NOT vnstock Company.events()
which is broken (VCI GraphQL returns empty {}). Per 07-RESEARCH.md.
"""
import asyncio
from datetime import date

import httpx
from loguru import logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.corporate_event import CorporateEvent
from app.resilience import vndirect_breaker
from app.services.ticker_service import TickerService

VNDIRECT_EVENTS_URL = "https://api-finfo.vndirect.com.vn/v4/events"
RELEVANT_TYPES = "DIVIDEND,STOCKDIV,KINDDIV,RIGHT"

# Map VNDirect API type codes to our internal event types
TYPE_MAP = {
    "DIVIDEND": "CASH_DIVIDEND",
    "STOCKDIV": "STOCK_DIVIDEND",
    "KINDDIV": "BONUS_SHARES",
    "RIGHT": "RIGHTS_ISSUE",
}


class CorporateEventCrawler:
    """Crawls corporate events from VNDirect REST API."""

    def __init__(self, session: AsyncSession, delay: float | None = None):
        self.session = session
        self.delay = delay if delay is not None else settings.vndirect_delay_seconds

    async def crawl_all_tickers(self) -> dict:
        """Crawl events for all active tickers.

        Returns: {success: int, failed: int, total_events: int, new_events: int, failed_symbols: list[str]}
        """
        ticker_service = TickerService(self.session)
        ticker_map = await ticker_service.get_ticker_id_map()
        logger.info(f"Starting VNDirect corporate events crawl for {len(ticker_map)} tickers")

        success = 0
        failed = 0
        total_events = 0
        new_events = 0
        failed_symbols: list[str] = []

        async with httpx.AsyncClient(
            timeout=settings.vndirect_timeout,
            verify=False,
        ) as client:
            for i, (symbol, ticker_id) in enumerate(ticker_map.items()):
                try:
                    events = await self._fetch_events(client, symbol)
                    stored = await self._store_events(ticker_id, events)
                    total_events += len(events)
                    new_events += stored
                    success += 1

                    if events:
                        logger.debug(f"{symbol}: {len(events)} events fetched, {stored} new stored")

                except Exception as e:
                    logger.warning(f"Corporate event crawl failed for {symbol}: {type(e).__name__}: {e}")
                    failed += 1
                    failed_symbols.append(symbol)

                # Rate limiting between tickers (except after last)
                if i < len(ticker_map) - 1:
                    await asyncio.sleep(self.delay)

            await self.session.commit()

        result = {
            "success": success,
            "failed": failed,
            "total_events": total_events,
            "new_events": new_events,
            "failed_symbols": failed_symbols,
        }
        logger.info(f"Corporate events crawl complete: {result}")
        return result

    async def _fetch_events_raw(self, client: httpx.AsyncClient, symbol: str) -> list[dict]:
        """Raw HTTP fetch from VNDirect — no circuit breaker."""
        all_events = []
        page = 1
        page_size = 100

        while True:
            resp = await client.get(
                VNDIRECT_EVENTS_URL,
                params={
                    "q": f"code:{symbol}~type:{RELEVANT_TYPES}~locale:VN",
                    "size": page_size,
                    "page": page,
                    "sort": "effectiveDate:DESC",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            events = data.get("data", [])
            all_events.extend(events)

            total_pages = data.get("totalPages", 1)
            if page >= total_pages:
                break
            page += 1

        return all_events

    async def _fetch_events(self, client: httpx.AsyncClient, symbol: str) -> list[dict]:
        """Fetch events with circuit breaker protection."""
        return await vndirect_breaker.call(self._fetch_events_raw, client, symbol)

    async def _store_events(self, ticker_id: int, events: list[dict]) -> int:
        """Store events with dedup on event_source_id. Returns count of newly inserted."""
        if not events:
            return 0

        stored = 0
        for event in events:
            event_type = TYPE_MAP.get(event.get("type"))
            if not event_type:
                continue

            event_source_id = event.get("id")
            if not event_source_id:
                continue

            effective_date = event.get("effectiveDate")
            if not effective_date:
                continue

            ex_date = self._parse_date(effective_date)
            if not ex_date:
                continue

            record_date = self._parse_date(event.get("expiredDate"))
            announcement_date = self._parse_date(event.get("disclosureDate"))

            # CRITICAL: For CASH_DIVIDEND, use `dividend` field (VND/share), NOT `ratio`
            # For STOCK_DIVIDEND/BONUS_SHARES/RIGHTS_ISSUE, use `ratio` (shares per 100 existing)
            dividend_amount = None
            ratio = None
            if event_type == "CASH_DIVIDEND":
                dividend_amount = event.get("dividend")
            else:
                ratio = event.get("ratio")

            note = event.get("note", "")
            if note and len(note) > 500:
                note = note[:497] + "..."

            stmt = insert(CorporateEvent).values(
                ticker_id=ticker_id,
                event_source_id=str(event_source_id),
                event_type=event_type,
                ex_date=ex_date,
                record_date=record_date,
                announcement_date=announcement_date,
                dividend_amount=dividend_amount,
                ratio=ratio,
                note=note,
            ).on_conflict_do_nothing(
                constraint="uq_corporate_events_source_id"
            )
            result = await self.session.execute(stmt)
            stored += result.rowcount

        return stored

    @staticmethod
    def _parse_date(date_str: str | None) -> date | None:
        """Parse YYYY-MM-DD date string, return None on failure."""
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str[:10])
        except (ValueError, TypeError):
            return None
