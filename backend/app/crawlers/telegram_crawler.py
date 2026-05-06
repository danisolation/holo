"""Telegram public channel crawler for Vietnamese stock rumors.

Uses Telethon MTProto client (user account) to read public channels.
Stores in rumors table via same pattern as fireant_crawler.py.

Key decisions (Phase 83):
- StringSession for cloud-compatible auth (no SQLite file on Render)
- Periodic backfill only (no persistent event listener — simpler lifecycle)
- Same Rumor model + ON CONFLICT DO NOTHING deduplication
- post_id = channel_suffix * 10^7 + message_id (avoids collision with Fireant IDs)
- 1.5s delay between channels
- Vietnamese NFC normalization before storage
"""
import asyncio
import re
import unicodedata
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crawlers.types import RumorCrawlResult
from app.models.rumor import Rumor

# Match 2-5 uppercase ASCII letters (covers all HOSE/HNX/UPCOM tickers)
TICKER_RE = re.compile(r"(?<![A-Za-z])([A-Z]{2,5})(?![A-Za-z])")

# Common abbreviations that are NOT stock tickers
FALSE_POSITIVES = frozenset({
    "PE", "PB", "EPS", "ROE", "ROA", "IPO", "GDP", "CPI", "FDI",
    "USD", "EUR", "VND", "JPY", "CNY", "YTD", "QOQ", "YOY",
    "EBIT", "CEO", "CFO", "CTO", "ETF", "NAV", "OTC", "ATH",
    "HOSE", "HNX", "UPCOM", "VNDS", "TCBS", "FPTS",
})


def _normalize_vn(text: str) -> str:
    """Normalize Vietnamese Unicode to NFC (precomposed form)."""
    return unicodedata.normalize("NFC", text).strip()


def _make_post_id(channel_id: int, message_id: int) -> int:
    """Deterministic post_id that won't collide with Fireant/F319 IDs.

    Fireant IDs are typically < 10^9. We use channel_id suffix * 10^7 + message_id.
    """
    chan_suffix = abs(channel_id) % 1_000_000
    return chan_suffix * 10_000_000 + message_id


class TelegramCrawler:
    """Fetches recent messages from configured public Telegram channels."""

    MIN_CONTENT_LENGTH = 20

    def __init__(self, session: AsyncSession, ticker_map: dict[str, int]):
        self.session = session
        self.ticker_map = ticker_map
        self._ticker_set = set(ticker_map.keys())
        self._client = None

    async def _get_client(self):
        """Lazy-init Telethon client using StringSession."""
        if self._client is None:
            from telethon import TelegramClient
            from telethon.sessions import StringSession

            self._client = TelegramClient(
                StringSession(settings.telegram_session_string),
                settings.telegram_api_id,
                settings.telegram_api_hash,
                flood_sleep_threshold=60,
            )
            await self._client.connect()
            if not await self._client.is_user_authorized():
                logger.error("Telegram session not authorized — regenerate TELEGRAM_SESSION_STRING")
                self._client = None
                return None
        return self._client

    async def crawl_channels(self) -> RumorCrawlResult:
        """Crawl all configured Telegram channels for stock mentions."""
        if not settings.telegram_enabled:
            return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}

        if not settings.telegram_session_string:
            logger.warning("Telegram crawl skipped: TELEGRAM_SESSION_STRING not set")
            return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}

        client = await self._get_client()
        if client is None:
            return {"success": 0, "failed": 1, "total_posts": 0, "failed_symbols": ["auth"]}

        success, failed, total = 0, 0, 0
        failed_channels: list[str] = []

        for channel in settings.telegram_channels:
            try:
                stored = await self._crawl_channel(client, channel)
                success += 1
                total += stored
                logger.debug(f"Telegram @{channel}: {stored} new posts stored")
            except Exception as e:
                logger.warning(f"Telegram crawl failed for @{channel}: {e}")
                failed += 1
                failed_channels.append(channel)
            finally:
                await asyncio.sleep(settings.telegram_delay_seconds)

        await self.session.commit()
        logger.info(
            f"Telegram crawl complete: {success} channels OK, "
            f"{failed} failed, {total} posts stored"
        )
        return {
            "success": success,
            "failed": failed,
            "total_posts": total,
            "failed_symbols": failed_channels,
        }

    async def _crawl_channel(self, client, channel: str) -> int:
        """Fetch recent messages from one channel, store ticker-matched ones."""
        entity = await client.get_entity(channel)
        channel_id = entity.id

        rows: list[dict] = []
        async for msg in client.iter_messages(entity, limit=settings.telegram_fetch_limit):
            if not msg.text:
                continue
            content = _normalize_vn(msg.text)
            if len(content) < self.MIN_CONTENT_LENGTH:
                continue

            # Extract ticker mentions
            mentioned = (set(TICKER_RE.findall(content)) - FALSE_POSITIVES) & self._ticker_set
            if not mentioned:
                continue

            # Sender info
            sender_name = "unknown"
            if msg.sender:
                sender_name = (
                    getattr(msg.sender, "username", None)
                    or getattr(msg.sender, "first_name", "unknown")
                )

            post_id_base = _make_post_id(channel_id, msg.id)
            posted_at = msg.date if msg.date.tzinfo else msg.date.replace(tzinfo=timezone.utc)

            # Reactions count
            reactions_count = 0
            if msg.reactions and msg.reactions.results:
                reactions_count = sum(r.count for r in msg.reactions.results)

            replies_count = msg.replies.replies if msg.replies else 0

            for symbol in mentioned:
                rows.append({
                    "ticker_id": self.ticker_map[symbol],
                    "post_id": post_id_base + hash(symbol) % 997,
                    "content": content[:2000],
                    "author_name": f"tg:{sender_name}"[:200],
                    "is_authentic": False,
                    "total_likes": reactions_count,
                    "total_replies": replies_count,
                    "fireant_sentiment": 0,
                    "posted_at": posted_at,
                })

        if not rows:
            return 0

        stmt = insert(Rumor).values(rows).on_conflict_do_nothing(
            constraint="uq_rumors_post_id"
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def close(self):
        """Disconnect Telethon client."""
        if self._client and self._client.is_connected():
            await self._client.disconnect()
            self._client = None
