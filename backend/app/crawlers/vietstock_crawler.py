"""Vietstock RSS crawler for stock news/rumors.

Fetches from multiple Vietstock RSS feeds covering chứng khoán,
cổ phiếu, phân tích thị trường, ý kiến chuyên gia, and giao dịch nội bộ.
Extracts ticker mentions and stores in rumors table.

Vietstock has a comprehensive, undocumented RSS system with
category-ID-based URLs: vietstock.vn/{catID}/{slug}.rss
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

# Multiple high-value feeds from Vietstock
RSS_FEEDS = {
    "chung_khoan": "https://vietstock.vn/144/chung-khoan.rss",
    "co_phieu": "https://vietstock.vn/830/chung-khoan/co-phieu.rss",
    "nhan_dinh": "https://vietstock.vn/1636/nhan-dinh-phan-tich/nhan-dinh-thi-truong.rss",
    "chuyen_gia": "https://vietstock.vn/145/chung-khoan/y-kien-chuyen-gia.rss",
    "noi_bo": "https://vietstock.vn/739/chung-khoan/giao-dich-noi-bo.rss",
}

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


class VietstockCrawler:
    """Crawls multiple Vietstock RSS feeds for stock-relevant news."""

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
        """Fetch all Vietstock RSS feeds, extract ticker-tagged articles.

        Args:
            ticker_map: Pre-loaded {symbol: ticker_id} map. If None, queries DB.
        """
        if ticker_map is None:
            ticker_map = await self._get_watchlist_ticker_map()
        if not ticker_map:
            logger.warning("Vietstock crawler: no watchlist tickers found")
            return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}

        watchlist_symbols = set(ticker_map.keys())
        logger.info(
            f"Starting Vietstock RSS crawl ({len(RSS_FEEDS)} feeds, "
            f"watchlist: {len(watchlist_symbols)} tickers)"
        )

        all_items: list[dict] = []
        seen_guids: set[str] = set()
        feeds_ok = 0
        feeds_failed = 0

        async with httpx.AsyncClient(
            headers=self.headers, timeout=15, follow_redirects=True, verify=False
        ) as client:
            feed_tasks = [
                self._fetch_one_feed(client, name, url)
                for name, url in RSS_FEEDS.items()
            ]
            feed_results = await asyncio.gather(*feed_tasks)

            for feed_name, items, ok in feed_results:
                if ok:
                    feeds_ok += 1
                    for item in items:
                        if item["guid"] not in seen_guids:
                            seen_guids.add(item["guid"])
                            item["feed"] = feed_name
                            all_items.append(item)
                else:
                    feeds_failed += 1

        if not all_items:
            logger.warning("Vietstock: no items from any feed")
            return {"success": 0, "failed": feeds_failed, "total_posts": 0, "failed_symbols": []}

        logger.debug(f"Vietstock: {len(all_items)} unique items from {feeds_ok} feeds")

        rows_to_insert: list[dict] = []
        tickers_found: set[str] = set()

        for item in all_items:
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
                post_id = _guid_to_post_id(f"vietstock:{item['guid']}:{symbol}")
                rows_to_insert.append({
                    "ticker_id": ticker_id,
                    "post_id": post_id,
                    "content": content[:2000],
                    "author_name": f"Vietstock/{item['feed']}",
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
            "failed": feeds_failed,
            "total_posts": stored,
            "failed_symbols": [],
        }
        logger.info(
            f"Vietstock RSS crawl complete: {stored} posts stored for "
            f"{len(tickers_found)} tickers from {feeds_ok}/{len(RSS_FEEDS)} feeds"
        )
        return result_dict

    async def _fetch_one_feed(
        self, client: httpx.AsyncClient, feed_name: str, feed_url: str
    ) -> tuple[str, list[dict], bool]:
        """Fetch and parse one RSS feed. Returns (feed_name, items, success)."""
        try:
            resp = await client.get(feed_url)
            resp.raise_for_status()
            items = await asyncio.to_thread(self._parse_rss, resp.text)
            logger.debug(f"Vietstock {feed_name}: {len(items)} items")
            return (feed_name, items, True)
        except Exception as e:
            logger.warning(f"Vietstock {feed_name} feed failed: {e}")
            return (feed_name, [], False)

    def _parse_rss(self, xml_text: str) -> list[dict]:
        """Parse Vietstock RSS 2.0 XML into list of article dicts."""
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
