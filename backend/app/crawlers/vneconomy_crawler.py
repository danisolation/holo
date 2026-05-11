"""VnEconomy RSS crawler for stock news/rumors.

Fetches stock news from VnEconomy RSS feed (chung-khoan.rss).
Provides rich content via `content:encoded` CDATA with full article HTML.
Description field uses HTML numeric entities that need html.unescape().
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


TICKER_PATTERN = re.compile(r"\b([A-Z]{3})\b")

RSS_URL = "https://vneconomy.vn/chung-khoan.rss"

FALSE_POSITIVES = frozenset({
    "CEO", "CFO", "IPO", "ETF", "GDP", "CPI", "FDI", "ODA",
    "USD", "EUR", "JPY", "VND", "THE", "FOR", "AND", "NOT",
    "ALL", "NEW", "TOP", "HOT", "BIG", "LOW", "NET", "TAX",
    "WTO", "IMF", "WHO", "FED", "SEC", "ESG",
})


def _guid_to_post_id(guid: str) -> int:
    """Convert RSS GUID to unique BigInteger post_id."""
    h = hashlib.md5(guid.encode()).hexdigest()[:15]
    return int(h, 16)


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    soup = BeautifulSoup(text, "html.parser")
    return html.unescape(soup.get_text(separator=" ", strip=True))


class VnEconomyCrawler:
    """Crawls VnEconomy RSS feed for stock-relevant news."""

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
        """Fetch VnEconomy RSS, extract ticker-tagged articles, store in rumors.

        Args:
            ticker_map: Pre-loaded {symbol: ticker_id} map. If None, queries DB.
        """
        if ticker_map is None:
            ticker_map = await self._get_watchlist_ticker_map()
        if not ticker_map:
            logger.warning("VnEconomy crawler: no watchlist tickers found")
            return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}

        watchlist_symbols = set(ticker_map.keys())
        logger.info(f"Starting VnEconomy RSS crawl (watchlist: {len(watchlist_symbols)} tickers)")

        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=15, follow_redirects=True, verify=False
            ) as client:
                resp = await client.get(RSS_URL)
                resp.raise_for_status()
                rss_xml = resp.text
        except Exception as e:
            logger.error(f"VnEconomy RSS fetch failed: {e}")
            return {"success": 0, "failed": 1, "total_posts": 0, "failed_symbols": ["RSS"]}

        items = await asyncio.to_thread(self._parse_rss, rss_xml)
        logger.debug(f"VnEconomy: parsed {len(items)} RSS items")

        rows_to_insert: list[dict] = []
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
                post_id = _guid_to_post_id(f"vneconomy:{item['guid']}:{symbol}")
                rows_to_insert.append({
                    "ticker_id": ticker_id,
                    "post_id": post_id,
                    "content": content[:2000],
                    "author_name": "VnEconomy",
                    "is_authentic": True,
                    "total_likes": 0,
                    "total_replies": 0,
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
            f"VnEconomy RSS crawl complete: {stored} posts stored for "
            f"{len(tickers_found)} tickers ({sorted(tickers_found)})"
        )
        return result_dict

    def _parse_rss(self, xml_text: str) -> list[dict]:
        """Parse VnEconomy RSS XML into list of article dicts.

        Extracts content from `content:encoded` if available (richer text
        with more ticker mentions), falls back to description.
        """
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

            # content:encoded has full article HTML — prefer it
            content_encoded = item.find("content:encoded") or item.find("encoded")

            if not (title_tag and guid_tag):
                continue

            title = title_tag.get_text(strip=True)
            guid = guid_tag.get_text(strip=True)

            # Use content:encoded for richer text, fall back to description
            if content_encoded:
                raw = content_encoded.get_text(strip=True)
            elif desc_tag:
                raw = desc_tag.get_text(strip=True)
            else:
                raw = title

            # Decode HTML entities (&#224; etc.) and strip tags
            content = _strip_html(html.unescape(raw))

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
