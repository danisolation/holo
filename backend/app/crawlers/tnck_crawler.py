"""tinnhanhchungkhoan.vn news crawler for rumor intelligence.

Scrapes article listings from Ministry of Finance's financial news site.
High-authority source for stock market analysis and recommendations.

Phase 84: Part of multi-source rumor expansion.
"""
import hashlib
import html
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawlers.types import RumorCrawlResult
from app.models.rumor import Rumor

# Match 2-5 uppercase ASCII letters for ticker extraction
TICKER_RE = re.compile(r"(?<![A-Za-z])([A-Z]{2,5})(?![A-Za-z])")

# Common false positives in financial news
FALSE_POSITIVES = frozenset({
    "PE", "PB", "EPS", "ROE", "ROA", "IPO", "GDP", "CPI", "FDI",
    "USD", "EUR", "VND", "JPY", "CNY", "YTD", "QOQ", "YOY",
    "EBIT", "CEO", "CFO", "CTO", "ETF", "NAV", "OTC", "ATH",
    "HOSE", "HNX", "UPCOM", "VNDS", "TCBS", "FPTS", "BTC",
})

# Article URL pattern: /{slug}-post{NUMERIC_ID}.html
ARTICLE_PATTERN = re.compile(r"href=[\"']([^\"']*-post(\d+)\.html)[\"']")

BASE_URL = "https://www.tinnhanhchungkhoan.vn"
LISTING_URLS = [
    f"{BASE_URL}/chung-khoan/co-phieu",
    f"{BASE_URL}/chung-khoan/phan-tich",
]


def _article_to_post_id(article_id: int) -> int:
    """Convert article numeric ID to a unique post_id.

    Prefix with 8 (8 * 10^9 range) to avoid collision with Fireant and Telegram IDs.
    """
    return 8_000_000_000 + article_id


class TNCKCrawler:
    """Crawls tinnhanhchungkhoan.vn article listings for stock mentions."""

    MIN_CONTENT_LENGTH = 30

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
        """Fetch article listings from TNCK, extract tickers, store in rumors table."""
        if ticker_map is None:
            logger.warning("TNCK crawler: no ticker_map provided")
            return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}

        watchlist_symbols = set(ticker_map.keys())
        logger.info(f"Starting TNCK crawl (watchlist: {len(watchlist_symbols)} tickers)")

        articles: list[dict] = []
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=15, follow_redirects=True
            ) as client:
                for url in LISTING_URLS:
                    try:
                        resp = await client.get(url)
                        resp.raise_for_status()
                        page_articles = self._parse_listing(resp.text, url)
                        articles.extend(page_articles)
                    except Exception as e:
                        logger.warning(f"TNCK fetch failed for {url}: {e}")
        except Exception as e:
            logger.error(f"TNCK client error: {e}")
            return {"success": 0, "failed": 1, "total_posts": 0, "failed_symbols": ["TNCK"]}

        if not articles:
            logger.debug("TNCK: no articles found")
            return {"success": 1, "failed": 0, "total_posts": 0, "failed_symbols": []}

        # Match tickers in article titles
        rows_to_insert: list[dict] = []
        for article in articles:
            title = article["title"]
            mentioned = (set(TICKER_RE.findall(title)) - FALSE_POSITIVES) & watchlist_symbols
            if not mentioned:
                continue

            for symbol in mentioned:
                rows_to_insert.append({
                    "ticker_id": ticker_map[symbol],
                    "post_id": _article_to_post_id(article["article_id"]) + hash(symbol) % 997,
                    "content": title[:2000],
                    "author_name": "tnck:tinnhanhchungkhoan.vn"[:200],
                    "is_authentic": True,  # Official news source
                    "total_likes": 0,
                    "total_replies": 0,
                    "fireant_sentiment": 0,
                    "posted_at": article.get("posted_at", datetime.now(timezone.utc)),
                })

        if not rows_to_insert:
            return {"success": 1, "failed": 0, "total_posts": 0, "failed_symbols": []}

        stmt = insert(Rumor).values(rows_to_insert).on_conflict_do_nothing(
            constraint="uq_rumors_post_id"
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        stored = result.rowcount or 0
        logger.info(f"TNCK: stored {stored} new articles")
        return {"success": 1, "failed": 0, "total_posts": stored, "failed_symbols": []}

    def _parse_listing(self, html_content: str, source_url: str) -> list[dict]:
        """Parse article listing page for article links and titles."""
        soup = BeautifulSoup(html_content, "html.parser")
        articles = []

        # Find article links matching pattern: *-post{ID}.html
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            match = re.search(r"-post(\d+)\.html", href)
            if not match:
                continue

            article_id = int(match.group(1))
            title = link.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            # Deduplicate by article_id
            if any(a["article_id"] == article_id for a in articles):
                continue

            articles.append({
                "article_id": article_id,
                "title": html.unescape(title),
                "url": href if href.startswith("http") else f"{BASE_URL}{href}",
                "posted_at": datetime.now(timezone.utc),
            })

        return articles
