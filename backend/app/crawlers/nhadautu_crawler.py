"""nhadautu.vn HTML crawler for rumor intelligence.

Scrapes article listings from Nhà Đầu Tư (Investor) news sections.
High-quality investment news source with direct ticker references.

Phase 84: Part of multi-source rumor expansion.
"""
import asyncio
import hashlib
import html
import re
import warnings
from datetime import datetime, timezone

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

FALSE_POSITIVES = frozenset({
    "PE", "PB", "EPS", "ROE", "ROA", "IPO", "GDP", "CPI", "FDI",
    "USD", "EUR", "VND", "JPY", "CNY", "YTD", "QOQ", "YOY",
    "EBIT", "CEO", "CFO", "CTO", "ETF", "NAV", "OTC", "ATH",
    "HOSE", "HNX", "UPCOM", "VNDS", "TCBS", "FPTS", "BTC",
})

# Article URL pattern: /{slug}-d{NUMERIC_ID}.html
ARTICLE_ID_RE = re.compile(r"-d(\d+)\.html")

LISTING_URLS = [
    "https://nhadautu.vn/chung-khoan/",
    "https://nhadautu.vn/co-phieu/",
]


def _guid_to_post_id(guid: str) -> int:
    """Convert article GUID to unique BigInteger post_id.

    Prefix with 7 (7 * 10^9 range) to avoid collision with other sources.
    """
    h = hashlib.md5(guid.encode()).hexdigest()[:12]
    return 7_000_000_000 + int(h, 16) % 1_000_000_000


class NhaDauTuCrawler:
    """Crawls nhadautu.vn article listings for investment news."""

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
        """Fetch article listings, extract ticker mentions, store in rumors table."""
        if ticker_map is None:
            logger.warning("NhaDauTu crawler: no ticker_map provided")
            return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}

        watchlist_symbols = set(ticker_map.keys())
        logger.info(f"Starting NhaDauTu HTML crawl (watchlist: {len(watchlist_symbols)} tickers)")

        all_articles: list[dict] = []
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=15, follow_redirects=True, verify=False
            ) as client:
                for url in LISTING_URLS:
                    try:
                        resp = await client.get(url)
                        resp.raise_for_status()
                        articles = await asyncio.to_thread(self._parse_listing, resp.text)
                        all_articles.extend(articles)
                    except Exception as e:
                        logger.warning(f"NhaDauTu fetch failed for {url}: {e}")
        except Exception as e:
            logger.error(f"NhaDauTu client error: {e}")
            return {"success": 0, "failed": 1, "total_posts": 0, "failed_symbols": ["NDT"]}

        if not all_articles:
            logger.debug("NhaDauTu: no articles found")
            return {"success": 1, "failed": 0, "total_posts": 0, "failed_symbols": []}

        # Deduplicate by article_id
        seen_ids: set[str] = set()
        unique_articles = []
        for a in all_articles:
            if a["article_id"] not in seen_ids:
                seen_ids.add(a["article_id"])
                unique_articles.append(a)

        logger.debug(f"NhaDauTu: parsed {len(unique_articles)} unique articles")

        rows_to_insert: list[dict] = []
        for article in unique_articles:
            title = article["title"]
            mentioned = (set(TICKER_RE.findall(title)) - FALSE_POSITIVES) & watchlist_symbols
            if not mentioned:
                continue

            for symbol in mentioned:
                post_id = _guid_to_post_id(f"{article['article_id']}:{symbol}")
                rows_to_insert.append({
                    "ticker_id": ticker_map[symbol],
                    "post_id": post_id,
                    "content": title[:2000],
                    "author_name": "ndt:nhadautu.vn",
                    "is_authentic": True,
                    "total_likes": 0,
                    "total_replies": 0,
                    "fireant_sentiment": 0,
                    "posted_at": datetime.now(timezone.utc),
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

    def _parse_listing(self, html_content: str) -> list[dict]:
        """Parse article listing page for article links and titles."""
        soup = BeautifulSoup(html_content, "html.parser")
        articles = []

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            match = ARTICLE_ID_RE.search(href)
            if not match:
                continue

            title = link.get_text(strip=True)
            if not title or len(title) < 20:
                continue

            article_id = match.group(1)
            articles.append({
                "article_id": article_id,
                "title": html.unescape(title),
            })

        return articles
