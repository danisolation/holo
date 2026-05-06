"""CafeF news scraper for Vietnamese stock news.

Fetches article titles and metadata from CafeF's AJAX endpoint.
Stores in news_articles table with deduplication via ON CONFLICT DO NOTHING.

Key decisions (from CONTEXT.md):
- CafeF AJAX endpoint for smaller payload (~21KB vs ~78KB full page)
- Titles only — no full-text extraction needed for sentiment
- 1-second delay between ticker requests
- verify=False for SSL (CafeF cert chain issues)
"""
import asyncio
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from app.config import settings
from app.crawlers.types import NewsCrawlResult
from app.models.news_article import NewsArticle
from app.resilience import cafef_breaker
from app.services.ticker_service import TickerService


def _is_retryable(exc: BaseException) -> bool:
    """Retry on transient HTTP failures only."""
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
        return True
    return False


class CafeFCrawler:
    """Scrapes CafeF for Vietnamese stock news articles."""

    BASE_URL = "https://cafef.vn"
    AJAX_URL = f"{BASE_URL}/du-lieu/Ajax/Events_RelatedNews_New.aspx"

    def __init__(self, session: AsyncSession, delay: float | None = None, concurrency: int = 5):
        self.session = session
        self.delay = delay if delay is not None else settings.cafef_delay_seconds
        self.news_days = settings.cafef_news_days
        self.semaphore = asyncio.Semaphore(concurrency)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        }

    async def crawl_all_tickers(self, *, ticker_map: dict[str, int] | None = None) -> NewsCrawlResult:
        """Scrape news for all active tickers.

        Args:
            ticker_map: Pre-loaded {symbol: ticker_id} map. If None, queries DB.

        Returns: {success: int, failed: int, total_articles: int, failed_symbols: list[str]}
        """
        if ticker_map is None:
            ticker_service = TickerService(self.session)
            ticker_map = await ticker_service.get_ticker_id_map()
        logger.info(f"Starting CafeF news crawl for {len(ticker_map)} tickers")

        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=15,
            follow_redirects=True,
            verify=False,  # CafeF SSL cert chain issues (per RESEARCH.md pitfall 2)
        ) as client:
            tasks = [
                self._crawl_one_ticker(client, symbol, ticker_id)
                for symbol, ticker_id in ticker_map.items()
            ]
            results = await asyncio.gather(*tasks)

        success = 0
        failed = 0
        total_articles = 0
        failed_symbols: list[str] = []
        for symbol, stored, ok in results:
            if ok:
                success += 1
                total_articles += stored
            else:
                failed += 1
                failed_symbols.append(symbol)

        await self.session.commit()

        result = {
            "success": success,
            "failed": failed,
            "total_articles": total_articles,
            "failed_symbols": failed_symbols,
        }
        logger.info(f"CafeF news crawl complete: {result}")
        return result

    async def _crawl_one_ticker(
        self, client: httpx.AsyncClient, symbol: str, ticker_id: int
    ) -> tuple[str, int, bool]:
        """Fetch and store news for one ticker, respecting rate limit."""
        async with self.semaphore:
            try:
                articles = await self._fetch_news(client, symbol)
                stored = await self._store_articles(ticker_id, articles)
                if articles:
                    logger.debug(f"{symbol}: {len(articles)} articles fetched, {stored} new stored")
                return (symbol, stored, True)
            except Exception as e:
                logger.warning(f"CafeF crawl failed for {symbol}: {type(e).__name__}: {e}")
                return (symbol, 0, False)
            finally:
                await asyncio.sleep(self.delay)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        retry=retry_if_exception(_is_retryable),
        before_sleep=lambda retry_state: logger.debug(
            f"CafeF retry {retry_state.attempt_number} for "
            f"{retry_state.args[2] if len(retry_state.args) > 2 else '?'}: "
            f"{retry_state.outcome.exception()}"
        ),
        reraise=True,
    )
    async def _fetch_news_raw(self, client: httpx.AsyncClient, symbol: str) -> list[dict]:
        """Internal: raw HTTP fetch without circuit breaker."""
        params = {
            "symbol": symbol.upper(),
            "floorID": "0",
            "configID": "0",
            "PageIndex": "1",
            "PageSize": "30",
            "Type": "2",
        }

        resp = await client.get(self.AJAX_URL, params=params)
        resp.raise_for_status()

        return await asyncio.to_thread(self._parse_articles, resp.text)

    async def _fetch_news(self, client: httpx.AsyncClient, symbol: str) -> list[dict]:
        """Fetch news for a single ticker with circuit breaker protection."""
        return await cafef_breaker.call(self._fetch_news_raw, client, symbol)

    def _parse_articles(self, html: str) -> list[dict]:
        """Parse CafeF HTML fragment for article titles, dates, URLs.

        Per RESEARCH.md verified selectors:
        - <span class="timeTitle"> — publication date (DD/MM/YYYY HH:MM)
        - <a class="docnhanhTitle"> — article title + URL

        Filters to articles within the configured news_days window.
        """
        cutoff = datetime.now() - timedelta(days=self.news_days)
        soup = BeautifulSoup(html, "html.parser")
        articles = []

        for li in soup.find_all("li"):
            time_span = li.find("span", class_="timeTitle")
            link = li.find("a", class_="docnhanhTitle")
            if not (time_span and link):
                continue

            try:
                pub_date = datetime.strptime(
                    time_span.get_text(strip=True), "%d/%m/%Y %H:%M"
                )
            except ValueError:
                continue  # Skip articles with unparseable dates

            if pub_date < cutoff:
                continue  # Outside configured news window

            title = link.get_text(strip=True)
            if not title:
                continue

            url = link.get("href", "")
            if not url:
                continue
            # Normalize relative URLs (per RESEARCH.md pitfall 5)
            if not url.startswith("http"):
                url = f"{self.BASE_URL}{url}"

            articles.append({
                "title": title,
                "url": url,
                "published_at": pub_date,
            })

        return articles

    async def _store_articles(self, ticker_id: int, articles: list[dict]) -> int:
        """Store articles in news_articles table with deduplication.

        Uses bulk INSERT ... ON CONFLICT DO NOTHING on (ticker_id, url) unique constraint.
        Returns: number of newly inserted articles.
        """
        if not articles:
            return 0

        rows = [
            {
                "ticker_id": ticker_id,
                "title": a["title"],
                "url": a["url"],
                "published_at": a["published_at"],
            }
            for a in articles
        ]
        stmt = insert(NewsArticle).values(rows).on_conflict_do_nothing(
            constraint="uq_news_articles_ticker_url"
        )
        result = await self.session.execute(stmt)
        return result.rowcount
