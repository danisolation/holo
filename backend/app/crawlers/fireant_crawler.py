"""Fireant.vn community post crawler for rumor intelligence.

Fetches posts from Fireant REST API for watchlist tickers.
Stores in rumors table with deduplication via ON CONFLICT DO NOTHING.

Key decisions (from 60-CONTEXT.md):
- Fireant REST API at restv2.fireant.vn/posts with guest JWT
- Watchlist-gated crawling only (not all 400 tickers)
- html.unescape() for Vietnamese content encoding
- 1.5s delay between ticker requests
- 30-day retention — delete older posts on each crawl
"""
import asyncio
import html
from datetime import datetime, timedelta, timezone

import httpx
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from app.config import settings
from app.crawlers.types import RumorCrawlResult
from app.models.rumor import Rumor
from app.resilience import fireant_breaker


def _is_retryable(exc: BaseException) -> bool:
    """Retry on transient HTTP failures only."""
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
        return True
    return False


class FireantCrawler:
    """Fetches community posts from Fireant.vn REST API for watchlist tickers."""

    API_URL = "https://restv2.fireant.vn/posts"
    MIN_CONTENT_LENGTH = 20

    def __init__(self, session: AsyncSession, delay: float | None = None, concurrency: int = 3):
        self.session = session
        self.delay = delay if delay is not None else settings.fireant_delay_seconds
        self.post_limit = settings.fireant_post_limit
        self.retention_days = settings.fireant_retention_days
        self.semaphore = asyncio.Semaphore(concurrency)
        self.headers = {
            "Authorization": f"Bearer {settings.fireant_token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

    async def crawl_watchlist_tickers(self, *, ticker_map: dict[str, int] | None = None) -> RumorCrawlResult:
        """Crawl Fireant posts for all watchlist tickers.

        Args:
            ticker_map: Pre-loaded {symbol: ticker_id} map. If None, queries DB.

        Returns: {success: int, failed: int, total_posts: int, failed_symbols: list[str]}
        """
        if not settings.fireant_token:
            logger.warning("Fireant crawl skipped: fireant_token not configured")
            return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}

        if ticker_map is None:
            from app.models.user_watchlist import UserWatchlist
            from app.models.ticker import Ticker

            stmt = (
                select(Ticker.symbol, Ticker.id)
                .join(UserWatchlist, UserWatchlist.symbol == Ticker.symbol)
                .where(Ticker.is_active == True)  # noqa: E712
            )
            result = await self.session.execute(stmt)
            ticker_map = {row[0]: row[1] for row in result.fetchall()}

        if not ticker_map:
            logger.warning("Fireant crawl: no watchlist tickers found — skipping")
            return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}

        logger.info(f"Starting Fireant crawl for {len(ticker_map)} watchlist tickers")

        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=15,
        ) as client:
            tasks = [
                self._crawl_one_ticker(client, symbol, ticker_id)
                for symbol, ticker_id in ticker_map.items()
            ]
            results = await asyncio.gather(*tasks)

        success = 0
        failed = 0
        total_posts = 0
        failed_symbols: list[str] = []
        for symbol, stored, ok in results:
            if ok:
                success += 1
                total_posts += stored
            else:
                failed += 1
                failed_symbols.append(symbol)

        # Cleanup old posts after all tickers processed
        await self._cleanup_old_posts()

        # Commit all changes
        await self.session.commit()

        result_dict: RumorCrawlResult = {
            "success": success,
            "failed": failed,
            "total_posts": total_posts,
            "failed_symbols": failed_symbols,
        }
        logger.info(f"Fireant crawl complete: {result_dict}")
        return result_dict

    async def _crawl_one_ticker(
        self, client: httpx.AsyncClient, symbol: str, ticker_id: int
    ) -> tuple[str, int, bool]:
        """Fetch and store posts for one ticker, respecting rate limit."""
        async with self.semaphore:
            try:
                posts = await self._fetch_posts(client, symbol)
                stored = await self._store_posts(ticker_id, posts)
                if posts:
                    logger.debug(f"{symbol}: {len(posts)} posts fetched, {stored} new stored")
                return (symbol, stored, True)
            except Exception as e:
                logger.warning(f"Fireant crawl failed for {symbol}: {type(e).__name__}: {e}")
                return (symbol, 0, False)
            finally:
                await asyncio.sleep(self.delay)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        retry=retry_if_exception(_is_retryable),
        before_sleep=lambda retry_state: logger.debug(
            f"Fireant retry {retry_state.attempt_number} for "
            f"{retry_state.args[2] if len(retry_state.args) > 2 else '?'}: "
            f"{retry_state.outcome.exception()}"
        ),
        reraise=True,
    )
    async def _fetch_posts_raw(
        self, client: httpx.AsyncClient, symbol: str
    ) -> list[dict]:
        """Internal: raw HTTP fetch without circuit breaker."""
        params = {
            "symbol": symbol.upper(),
            "offset": 0,
            "limit": self.post_limit,
        }

        resp = await client.get(self.API_URL, params=params)
        resp.raise_for_status()

        return await asyncio.to_thread(self._parse_posts, resp.json())

    async def _fetch_posts(
        self, client: httpx.AsyncClient, symbol: str
    ) -> list[dict]:
        """Fetch posts for a single ticker with circuit breaker protection."""
        return await fireant_breaker.call(self._fetch_posts_raw, client, symbol)

    def _parse_posts(self, posts_json: list[dict]) -> list[dict]:
        """Parse Fireant JSON response into normalized post dicts.

        Applies html.unescape() for Vietnamese content encoding (e.g. &#225; → á).
        Filters out posts shorter than MIN_CONTENT_LENGTH characters.
        """
        if not isinstance(posts_json, list):
            logger.warning(f"Fireant API returned non-list response: {type(posts_json)}")
            return []

        parsed = []
        for post in posts_json:
            try:
                content = html.unescape(post.get("content", "")).strip()
                if len(content) < self.MIN_CONTENT_LENGTH:
                    continue

                parsed.append({
                    "post_id": post["postID"],
                    "content": content,
                    "author_name": post.get("user", {}).get("name", "Unknown"),
                    "is_authentic": post.get("user", {}).get("isAuthentic", False),
                    "total_likes": post.get("totalLikes", 0),
                    "total_replies": post.get("totalReplies", 0),
                    "fireant_sentiment": post.get("sentiment", 0),
                    "posted_at": datetime.fromisoformat(post["date"]),
                })
            except (KeyError, ValueError, AttributeError) as e:
                logger.debug(f"Skipping malformed Fireant post: {e}")
                continue

        return parsed

    async def _store_posts(self, ticker_id: int, posts: list[dict]) -> int:
        """Store posts in rumors table with deduplication.

        Uses bulk INSERT ... ON CONFLICT DO NOTHING on post_id unique constraint.
        Returns: number of newly inserted posts.
        """
        if not posts:
            return 0

        rows = [{"ticker_id": ticker_id, **post} for post in posts]
        stmt = insert(Rumor).values(rows).on_conflict_do_nothing(
            constraint="uq_rumors_post_id"
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def _cleanup_old_posts(self) -> None:
        """Delete posts older than retention_days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        stmt = delete(Rumor).where(Rumor.posted_at < cutoff)
        result = await self.session.execute(stmt)
        if result.rowcount > 0:
            logger.info(f"Cleaned up {result.rowcount} old Fireant posts (>{self.retention_days} days)")
