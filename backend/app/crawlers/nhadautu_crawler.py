"""nhadautu.vn RSS crawler for rumor intelligence.

Fetches articles from Nhà Đầu Tư (Investor) news RSS feed.
High-quality investment news source with direct ticker references.

Phase 84: Part of multi-source rumor expansion.
"""
import hashlib
import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawlers.types import RumorCrawlResult
from app.models.rumor import Rumor

# Match 2-5 uppercase ASCII letters for ticker extraction
TICKER_RE = re.compile(r"(?<![A-Za-z])([A-Z]{2,5})(?![A-Za-z])")

FALSE_POSITIVES = frozenset({
    "PE", "PB", "EPS", "ROE", "ROA", "IPO", "GDP", "CPI", "FDI",
    "USD", "EUR", "VND", "JPY", "CNY", "YTD", "QOQ", "YOY",
    "EBIT", "CEO", "CFO", "CTO", "ETF", "NAV", "OTC", "ATH",
    "HOSE", "HNX", "UPCOM", "VNDS", "TCBS", "FPTS", "BTC",
})

RSS_URL = "https://nhadautu.vn/rss"


def _guid_to_post_id(guid: str) -> int:
    """Convert RSS GUID to unique BigInteger post_id.

    Prefix with 7 (7 * 10^9 range) to avoid collision with other sources.
    """
    h = hashlib.md5(guid.encode()).hexdigest()[:15]
    return 7_000_000_000 + (int(h, 16) % 1_000_000_000)


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    soup = BeautifulSoup(text, "html.parser")
    return html.unescape(soup.get_text(separator=" ", strip=True))


class NhaDauTuCrawler:
    """Crawls nhadautu.vn RSS feed for investment news."""

    MIN_CONTENT_LENGTH = 20

    def __init__(self, session: AsyncSession):
        self.session = session
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        }

    async def crawl_rss(self, *, ticker_map: dict[str, int] | None = None) -> RumorCrawlResult:
        """Fetch RSS feed, extract ticker mentions, store in rumors table."""
        if ticker_map is None:
            logger.warning("NhaDauTu crawler: no ticker_map provided")
            return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}

        watchlist_symbols = set(ticker_map.keys())
        logger.info(f"Starting NhaDauTu RSS crawl (watchlist: {len(watchlist_symbols)} tickers)")

        # Fetch RSS
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=15, follow_redirects=True
            ) as client:
                resp = await client.get(RSS_URL)
                resp.raise_for_status()
                rss_xml = resp.text
        except Exception as e:
            logger.error(f"NhaDauTu RSS fetch failed: {e}")
            return {"success": 0, "failed": 1, "total_posts": 0, "failed_symbols": ["RSS"]}

        # Parse RSS
        soup = BeautifulSoup(rss_xml, "html.parser")
        items = soup.find_all("item")
        logger.debug(f"NhaDauTu: parsed {len(items)} RSS items")

        rows_to_insert: list[dict] = []
        for item in items:
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pub_el = item.find("pubdate")

            if not title_el:
                continue

            title = html.unescape(title_el.get_text(strip=True))
            description = _strip_html(desc_el.get_text()) if desc_el else ""
            link = link_el.get_text(strip=True) if link_el else ""
            guid = link or title

            # Parse date
            posted_at = datetime.now(timezone.utc)
            if pub_el:
                try:
                    posted_at = parsedate_to_datetime(pub_el.get_text(strip=True))
                except Exception:
                    pass

            # Extract tickers from title + description
            text_to_search = f"{title} {description}"
            mentioned = (set(TICKER_RE.findall(text_to_search)) - FALSE_POSITIVES) & watchlist_symbols
            if not mentioned:
                continue

            content = f"{title}. {description}"[:2000] if description else title[:2000]
            if len(content) < self.MIN_CONTENT_LENGTH:
                continue

            for symbol in mentioned:
                post_id = _guid_to_post_id(f"{guid}:{symbol}")
                rows_to_insert.append({
                    "ticker_id": ticker_map[symbol],
                    "post_id": post_id,
                    "content": content,
                    "author_name": "ndt:nhadautu.vn"[:200],
                    "is_authentic": True,
                    "total_likes": 0,
                    "total_replies": 0,
                    "fireant_sentiment": 0,
                    "posted_at": posted_at,
                })

        if not rows_to_insert:
            return {"success": 1, "failed": 0, "total_posts": 0, "failed_symbols": []}

        stmt = insert(Rumor).values(rows_to_insert).on_conflict_do_nothing(
            constraint="uq_rumors_post_id"
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        stored = result.rowcount or 0
        logger.info(f"NhaDauTu: stored {stored} new articles")
        return {"success": 1, "failed": 0, "total_posts": stored, "failed_symbols": []}
