"""tinnhanhchungkhoan.vn RSS crawler for rumor intelligence.

Fetches RSS feed from Ministry of Finance's financial news site.
High-authority source for stock market analysis and recommendations.

Phase 84: Part of multi-source rumor expansion.
"""
import asyncio
import hashlib
import html
import re
import warnings
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from loguru import logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawlers.types import RumorCrawlResult
from app.models.rumor import Rumor

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Match 2-5 uppercase ASCII letters for ticker extraction
TICKER_RE = re.compile(r"(?<![A-Za-z])([A-Z]{2,5})(?![A-Za-z])")

# Common false positives in financial news
FALSE_POSITIVES = frozenset({
    "PE", "PB", "EPS", "ROE", "ROA", "IPO", "GDP", "CPI", "FDI",
    "USD", "EUR", "VND", "JPY", "CNY", "YTD", "QOQ", "YOY",
    "EBIT", "CEO", "CFO", "CTO", "ETF", "NAV", "OTC", "ATH",
    "HOSE", "HNX", "UPCOM", "VNDS", "TCBS", "FPTS", "BTC",
})

RSS_URL = "https://www.tinnhanhchungkhoan.vn/rss/home.rss"


def _guid_to_post_id(guid: str) -> int:
    """Convert RSS GUID to unique BigInteger post_id.

    Prefix with 8 (8 * 10^9 range) to avoid collision with other sources.
    """
    h = hashlib.md5(guid.encode()).hexdigest()[:12]
    return 8_000_000_000 + int(h, 16) % 1_000_000_000


class TNCKCrawler:
    """Crawls tinnhanhchungkhoan.vn RSS feed for stock mentions."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        }

    async def crawl_articles(self, *, ticker_map: dict[str, int] | None = None) -> RumorCrawlResult:
        """Fetch RSS feed from TNCK, extract tickers, store in rumors table."""
        if ticker_map is None:
            logger.warning("TNCK crawler: no ticker_map provided")
            return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}

        watchlist_symbols = set(ticker_map.keys())
        logger.info(f"Starting TNCK RSS crawl (watchlist: {len(watchlist_symbols)} tickers)")

        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=15, follow_redirects=True, verify=False
            ) as client:
                resp = await client.get(RSS_URL)
                resp.raise_for_status()
                rss_xml = resp.text
        except Exception as e:
            logger.error(f"TNCK RSS fetch failed: {e}")
            return {"success": 0, "failed": 1, "total_posts": 0, "failed_symbols": ["TNCK"]}

        items = await asyncio.to_thread(self._parse_rss, rss_xml)
        if not items:
            logger.debug("TNCK: no RSS items parsed")
            return {"success": 1, "failed": 0, "total_posts": 0, "failed_symbols": []}

        logger.debug(f"TNCK: parsed {len(items)} RSS items")

        # Match tickers in article titles and descriptions
        rows_to_insert: list[dict] = []
        for item in items:
            title = item["title"]
            desc = item.get("description", "")
            text_to_scan = f"{title} {desc}"
            mentioned = (set(TICKER_RE.findall(text_to_scan)) - FALSE_POSITIVES) & watchlist_symbols
            if not mentioned:
                continue

            for symbol in mentioned:
                rows_to_insert.append({
                    "ticker_id": ticker_map[symbol],
                    "post_id": _guid_to_post_id(item["guid"] + symbol),
                    "content": title[:2000],
                    "author_name": "tnck:tinnhanhchungkhoan.vn",
                    "is_authentic": True,
                    "total_likes": 0,
                    "total_replies": 0,
                    "fireant_sentiment": 0,
                    "posted_at": item.get("pub_date", datetime.now(timezone.utc)),
                })

        if not rows_to_insert:
            return {"success": 1, "failed": 0, "total_posts": 0, "failed_symbols": []}

        stmt = insert(Rumor).values(rows_to_insert).on_conflict_do_nothing(
            constraint="uq_rumors_post_id"
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        stored = result.rowcount or 0
        logger.info(f"TNCK: stored {stored} new articles from RSS")
        return {"success": 1, "failed": 0, "total_posts": stored, "failed_symbols": []}

    def _parse_rss(self, xml_text: str) -> list[dict]:
        """Parse RSS XML into list of items with title, guid, pub_date."""
        soup = BeautifulSoup(xml_text, "html.parser")
        items = []
        for item_el in soup.find_all("item"):
            title_el = item_el.find("title")
            link_el = item_el.find("link")
            desc_el = item_el.find("description")
            pub_el = item_el.find("pubdate")

            title = html.unescape(title_el.text.strip()) if title_el else ""
            if not title or len(title) < 10:
                continue

            guid = link_el.text.strip() if link_el else title
            description = html.unescape(desc_el.text.strip()) if desc_el else ""

            pub_date = datetime.now(timezone.utc)
            if pub_el and pub_el.text.strip():
                try:
                    pub_date = parsedate_to_datetime(pub_el.text.strip())
                except Exception:
                    pass

            items.append({
                "title": title,
                "guid": guid,
                "description": description,
                "pub_date": pub_date,
            })
        return items
