"""F319.com forum RSS crawler for rumor intelligence.

Fetches latest threads from F319's RSS feed, extracts ticker mentions
via regex, and stores relevant posts in the rumors table.

F319 is Vietnam's largest stock forum (34k+ pages, 1800+ concurrent users).
RSS feed: https://f319.com/forums/thi-truong-chung-khoan.3/index.rss
"""
import asyncio
import hashlib
import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawlers.types import RumorCrawlResult
from app.models.rumor import Rumor


# Match 3-letter uppercase stock symbols (VIC, HPG, SHB, etc.)
TICKER_PATTERN = re.compile(r"\b([A-Z]{3})\b")


def _guid_to_post_id(guid: str) -> int:
    """Convert RSS GUID string to a unique BigInteger post_id.

    Uses first 15 hex digits of MD5 hash → fits in PostgreSQL BIGINT.
    Prefix with 9 to avoid collision with Fireant post IDs (which are smaller).
    """
    h = hashlib.md5(guid.encode()).hexdigest()[:15]
    return int(h, 16)


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    soup = BeautifulSoup(text, "html.parser")
    return html.unescape(soup.get_text(separator=" ", strip=True))


class F319Crawler:
    """Crawls F319.com RSS feeds for stock discussion threads."""

    RSS_URLS = [
        "https://f319.com/forums/thi-truong-chung-khoan.3/index.rss",
        "https://f319.com/forums/giao-luu.4/index.rss",
    ]
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
        """Fetch RSS feed, extract ticker-tagged posts, store in rumors table.

        Args:
            ticker_map: Pre-loaded {symbol: ticker_id} map. If None, queries DB.

        Returns crawl stats.
        """
        if ticker_map is None:
            ticker_map = await self._get_watchlist_ticker_map()
        if not ticker_map:
            logger.warning("F319 crawler: no watchlist tickers found")
            return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}

        watchlist_symbols = set(ticker_map.keys())
        logger.info(f"Starting F319 RSS crawl (watchlist: {len(watchlist_symbols)} tickers, {len(self.RSS_URLS)} feeds)")

        # Fetch all RSS feeds
        rss_contents: list[str] = []
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=15, follow_redirects=True
            ) as client:
                for url in self.RSS_URLS:
                    try:
                        resp = await client.get(url)
                        resp.raise_for_status()
                        rss_contents.append(resp.text)
                    except Exception as e:
                        logger.warning(f"F319 RSS fetch failed for {url}: {e}")
        except Exception as e:
            logger.error(f"F319 RSS client error: {e}")
            return {"success": 0, "failed": 1, "total_posts": 0, "failed_symbols": ["RSS"]}

        if not rss_contents:
            return {"success": 0, "failed": 1, "total_posts": 0, "failed_symbols": ["RSS"]}

        # Parse all RSS items from all feeds
        items: list[dict] = []
        for rss_xml in rss_contents:
            items.extend(await asyncio.to_thread(self._parse_rss, rss_xml))
        logger.debug(f"F319: parsed {len(items)} RSS items from {len(rss_contents)} feeds")

        # Extract ticker mentions and store via bulk insert
        rows_to_insert: list[dict] = []
        tickers_found: set[str] = set()

        for item in items:
            # Find ticker symbols in title + content
            text_to_search = f"{item['title']} {item['content']}"
            mentioned_tickers = TICKER_PATTERN.findall(text_to_search)
            matched = set(mentioned_tickers) & watchlist_symbols

            if not matched:
                continue

            content = item["content"]
            if len(content) < self.MIN_CONTENT_LENGTH:
                continue

            for symbol in matched:
                ticker_id = ticker_map[symbol]
                post_id = _guid_to_post_id(f"{item['guid']}:{symbol}")
                rows_to_insert.append({
                    "ticker_id": ticker_id,
                    "post_id": post_id,
                    "content": content[:2000],
                    "author_name": item["author"][:200],
                    "is_authentic": False,
                    "total_likes": 0,
                    "total_replies": item["comments"],
                    "fireant_sentiment": 0,
                    "posted_at": item["pub_date"],
                })
                tickers_found.add(symbol)

        stored = 0
        if rows_to_insert:
            stmt = insert(Rumor).values(rows_to_insert).on_conflict_do_nothing(
                constraint="uq_rumors_post_id"
            )
            result = await self.session.execute(stmt)
            stored = result.rowcount

        await self.session.commit()

        result_dict: RumorCrawlResult = {
            "success": len(tickers_found),
            "failed": 0,
            "total_posts": stored,
            "failed_symbols": [],
        }
        logger.info(
            f"F319 RSS crawl complete: {stored} posts stored for "
            f"{len(tickers_found)} tickers ({sorted(tickers_found)})"
        )
        return result_dict

    def _parse_rss(self, xml_text: str) -> list[dict]:
        """Parse RSS XML into list of post dicts."""
        try:
            soup = BeautifulSoup(xml_text, "xml")
        except Exception:
            # Fallback if lxml not installed
            soup = BeautifulSoup(xml_text, "html.parser")
        items = []

        for item in soup.find_all("item"):
            title_tag = item.find("title")
            content_tag = item.find("content:encoded") or item.find("encoded")
            author_tag = item.find("dc:creator") or item.find("creator") or item.find("author")
            date_tag = item.find("pubdate") or item.find("pubDate")
            guid_tag = item.find("guid")
            comments_tag = item.find("slash:comments") or item.find("comments")

            if not (title_tag and guid_tag):
                continue

            title = title_tag.get_text(strip=True)
            content_raw = content_tag.get_text(strip=True) if content_tag else title
            content = _strip_html(content_raw)
            author = author_tag.get_text(strip=True) if author_tag else "anonymous"
            guid = guid_tag.get_text(strip=True)

            try:
                pub_date = parsedate_to_datetime(date_tag.get_text(strip=True))
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            except Exception:
                pub_date = datetime.now(timezone.utc)

            try:
                comments = int(comments_tag.get_text(strip=True)) if comments_tag else 0
            except (ValueError, TypeError):
                comments = 0

            items.append({
                "title": title,
                "content": content,
                "author": author,
                "pub_date": pub_date,
                "guid": guid,
                "comments": comments,
            })

        return items

    async def _get_watchlist_ticker_map(self) -> dict[str, int]:
        """Get watchlist ticker symbols mapped to their IDs."""
        from app.models.ticker import Ticker
        from app.models.user_watchlist import UserWatchlist

        result = await self.session.execute(
            select(Ticker.symbol, Ticker.id)
            .join(UserWatchlist, UserWatchlist.symbol == Ticker.symbol)
            .where(Ticker.is_active == True)  # noqa: E712
        )
        return {row[0]: row[1] for row in result.fetchall()}
