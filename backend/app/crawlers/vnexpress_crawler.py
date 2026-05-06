"""VnExpress RSS crawler for stock news/rumors.

Fetches business news from VnExpress RSS feed (kinh-doanh.rss),
extracts ticker mentions via regex, and stores relevant posts
in the rumors table alongside Fireant/F319 data.

VnExpress is Vietnam's largest news site — their business feed
covers chứng khoán, tài chính, doanh nghiệp.
"""
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


TICKER_PATTERN = re.compile(r"\b([A-Z]{3})\b")

RSS_URL = "https://vnexpress.net/rss/kinh-doanh.rss"

# Common 3-letter words that are NOT tickers
FALSE_POSITIVES = frozenset({
    "CEO", "CFO", "IPO", "ETF", "GDP", "CPI", "FDI", "ODA",
    "USD", "EUR", "JPY", "VND", "THE", "FOR", "AND", "NOT",
    "ALL", "NEW", "TOP", "HOT", "BIG", "LOW", "NET", "TAX",
    "WTO", "IMF", "WHO", "FED", "SEC", "ESG", "M&A",
})


def _guid_to_post_id(guid: str) -> int:
    """Convert RSS GUID/URL to a unique BigInteger post_id.

    Uses first 15 hex digits of MD5 hash. Prefix ensures no
    collision with Fireant (small IDs) or F319 (different hash).
    """
    h = hashlib.md5(guid.encode()).hexdigest()[:15]
    return int(h, 16)


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    soup = BeautifulSoup(text, "html.parser")
    return html.unescape(soup.get_text(separator=" ", strip=True))


class VnExpressCrawler:
    """Crawls VnExpress RSS feed for stock-relevant business news."""

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

    async def crawl_rss(self) -> RumorCrawlResult:
        """Fetch VnExpress RSS, extract ticker-tagged articles, store in rumors."""
        ticker_map = await self._get_watchlist_ticker_map()
        if not ticker_map:
            logger.warning("VnExpress crawler: no watchlist tickers found")
            return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}

        watchlist_symbols = set(ticker_map.keys())
        logger.info(f"Starting VnExpress RSS crawl (watchlist: {len(watchlist_symbols)} tickers)")

        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=15, follow_redirects=True
            ) as client:
                resp = await client.get(RSS_URL)
                resp.raise_for_status()
                rss_xml = resp.text
        except Exception as e:
            logger.error(f"VnExpress RSS fetch failed: {e}")
            return {"success": 0, "failed": 1, "total_posts": 0, "failed_symbols": ["RSS"]}

        items = self._parse_rss(rss_xml)
        logger.debug(f"VnExpress: parsed {len(items)} RSS items")

        stored = 0
        tickers_found: set[str] = set()

        for item in items:
            text_to_search = f"{item['title']} {item['content']}"
            mentioned = TICKER_PATTERN.findall(text_to_search)
            matched = {t for t in mentioned if t in watchlist_symbols and t not in FALSE_POSITIVES}

            if not matched:
                continue

            content = item["content"]
            if len(content) < self.MIN_CONTENT_LENGTH:
                continue

            for symbol in matched:
                ticker_id = ticker_map[symbol]
                post_id = _guid_to_post_id(f"vnexpress:{item['guid']}:{symbol}")

                try:
                    stmt = insert(Rumor).values(
                        ticker_id=ticker_id,
                        post_id=post_id,
                        content=content[:2000],
                        author_name="VnExpress",
                        is_authentic=True,  # official news source
                        total_likes=0,
                        total_replies=0,
                        fireant_sentiment=0,
                        posted_at=item["pub_date"],
                    ).on_conflict_do_nothing(constraint="uq_rumors_post_id")
                    result = await self.session.execute(stmt)
                    if result.rowcount > 0:
                        stored += 1
                        tickers_found.add(symbol)
                except Exception as e:
                    logger.warning(f"VnExpress: failed to store post for {symbol}: {e}")

        await self.session.commit()

        result_dict: RumorCrawlResult = {
            "success": len(tickers_found),
            "failed": 0,
            "total_posts": stored,
            "failed_symbols": [],
        }
        logger.info(
            f"VnExpress RSS crawl complete: {stored} posts stored for "
            f"{len(tickers_found)} tickers ({sorted(tickers_found)})"
        )
        return result_dict

    def _parse_rss(self, xml_text: str) -> list[dict]:
        """Parse VnExpress RSS 2.0 XML into list of article dicts."""
        try:
            soup = BeautifulSoup(xml_text, "xml")
        except Exception:
            soup = BeautifulSoup(xml_text, "html.parser")

        items = []
        for item in soup.find_all("item"):
            title_tag = item.find("title")
            desc_tag = item.find("description")
            date_tag = item.find("pubDate")
            guid_tag = item.find("guid") or item.find("link")

            if not (title_tag and guid_tag):
                continue

            title = title_tag.get_text(strip=True)
            desc_raw = desc_tag.get_text(strip=True) if desc_tag else title
            content = _strip_html(desc_raw)
            guid = guid_tag.get_text(strip=True)

            try:
                pub_date = parsedate_to_datetime(date_tag.get_text(strip=True))
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            except Exception:
                pub_date = datetime.now(timezone.utc)

            items.append({
                "title": title,
                "content": f"{title}. {content}",
                "pub_date": pub_date,
                "guid": guid,
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
