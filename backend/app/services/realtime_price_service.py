"""Real-time price service — market hours logic + VCI polling + price cache.

Polls VCI price_board via VnstockCrawler at configurable intervals (default 30s)
during market hours. Stores latest prices in memory and broadcasts to
WebSocket clients via ConnectionManager.

Market hours (HOSE/HNX/UPCOM shared):
  Morning:   09:00 – 11:30  Mon-Fri  (Asia/Ho_Chi_Minh)
  Afternoon: 13:00 – 14:45  Mon-Fri  (Asia/Ho_Chi_Minh)
"""
from __future__ import annotations

from datetime import datetime, time
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from loguru import logger

from app.config import settings

if TYPE_CHECKING:
    from app.crawlers.vnstock_crawler import VnstockCrawler

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

# Market session boundaries (inclusive)
_MORNING_OPEN = time(9, 0)
_MORNING_CLOSE = time(11, 30)
_AFTERNOON_OPEN = time(13, 0)
_AFTERNOON_CLOSE = time(14, 45)


def _now_vn() -> datetime:
    """Current time in VN timezone. Extracted for test patching."""
    return datetime.now(VN_TZ)


def is_market_open() -> bool:
    """Check if VN stock market is currently in a trading session.

    Returns True during weekday morning (9:00-11:30) and afternoon (13:00-14:45).
    """
    now = _now_vn()
    # Weekday check: Monday=0 .. Friday=4
    if now.weekday() > 4:
        return False

    t = now.time()
    return (_MORNING_OPEN <= t <= _MORNING_CLOSE) or (_AFTERNOON_OPEN <= t <= _AFTERNOON_CLOSE)


def get_market_session() -> str:
    """Return current market session name.

    Returns:
        "morning" — during 9:00-11:30 weekdays
        "afternoon" — during 13:00-14:45 weekdays
        "closed" — all other times
    """
    now = _now_vn()
    if now.weekday() > 4:
        return "closed"

    t = now.time()
    if _MORNING_OPEN <= t <= _MORNING_CLOSE:
        return "morning"
    if _AFTERNOON_OPEN <= t <= _AFTERNOON_CLOSE:
        return "afternoon"
    return "closed"


class RealtimePriceService:
    """Manages real-time price polling and in-memory cache.

    Called by APScheduler interval job every N seconds.
    Fetches prices from VCI for all subscribed symbols,
    updates internal cache, and broadcasts to WebSocket clients.
    """

    def __init__(self, crawler: VnstockCrawler, connection_manager, exchange_map: dict[str, str] | None = None) -> None:
        self._crawler = crawler
        self._connection_manager = connection_manager
        self._latest_prices: dict[str, dict] = {}
        self._exchange_map: dict[str, str] = exchange_map or {}

    def set_exchange_map(self, exchange_map: dict[str, str]) -> None:
        """Update the symbol → exchange mapping for priority sorting."""
        self._exchange_map = exchange_map

    async def poll_and_broadcast(self) -> None:
        """Fetch latest prices from VCI and broadcast to WebSocket clients.

        Skips polling if no clients are subscribed.
        Limits symbols to realtime_max_symbols config.
        """
        symbols = self._connection_manager.get_all_subscribed_symbols()
        if not symbols:
            logger.debug("No subscribed symbols — skipping price poll")
            return

        # Sort by exchange priority, then alphabetically within each exchange
        priority = settings.realtime_priority_exchanges

        def _sort_key(sym: str) -> tuple[int, str]:
            exc = self._exchange_map.get(sym, "")
            try:
                rank = priority.index(exc)
            except ValueError:
                rank = len(priority)  # unknown exchange goes last
            return (rank, sym)

        symbols_list = sorted(symbols, key=_sort_key)[:settings.realtime_max_symbols]

        try:
            prices = await self._crawler.fetch_price_board(symbols_list)
        except Exception as e:
            logger.warning(f"Price board poll failed: {e}")
            return

        # Diff detection: only broadcast changed prices
        changed: dict[str, dict] = {}
        for sym, price_data in prices.items():
            cached = self._latest_prices.get(sym)
            if cached != price_data:
                changed[sym] = price_data

        # Always update full cache (for get_latest_prices endpoint)
        self._latest_prices.update(prices)

        if changed:
            logger.debug(f"{len(changed)} of {len(prices)} symbols changed — broadcasting")
            await self._connection_manager.broadcast(changed)
        else:
            logger.debug(f"0 of {len(prices)} symbols changed — skipping broadcast")

    def get_latest_prices(self, symbols: list[str]) -> dict[str, dict]:
        """Return cached prices for requested symbols only."""
        return {s: self._latest_prices[s] for s in symbols if s in self._latest_prices}


# ── Module-level singleton ──────────────────────────────────────────────────

_singleton: RealtimePriceService | None = None


def get_realtime_price_service() -> RealtimePriceService:
    """Return the module-level singleton RealtimePriceService.

    Lazy-initialized on first call. Uses the shared VnstockCrawler and
    connection_manager so the in-memory price cache persists across polls.
    """
    global _singleton
    if _singleton is None:
        from app.crawlers.vnstock_crawler import VnstockCrawler
        from app.ws.prices import connection_manager

        _singleton = RealtimePriceService(
            crawler=VnstockCrawler(),
            connection_manager=connection_manager,
        )
    return _singleton
