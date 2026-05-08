"""Real-time price service — VCI polling + price cache + intraday storage.

Polls VCI price_board via VnstockCrawler at configurable intervals (default 15s)
continuously (no market-hours restriction). Stores each snapshot into
intraday_prices table and broadcasts changes to WebSocket clients.

Market hours helper functions are kept for status reporting to clients.
  Morning:   09:00 – 11:30  Mon-Fri  (Asia/Ho_Chi_Minh)
  Afternoon: 13:00 – 14:45  Mon-Fri  (Asia/Ho_Chi_Minh)
"""
from __future__ import annotations

from datetime import datetime, date, time
from decimal import Decimal
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import select

from app.config import settings
from app.database import async_session

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
    """Manages real-time price polling, intraday storage, and in-memory cache.

    Called by APScheduler interval job every N seconds.
    Fetches prices from VCI for ALL HOSE symbols,
    stores snapshots to intraday_prices table,
    updates internal cache, and broadcasts to WebSocket clients.
    """

    def __init__(self, crawler: VnstockCrawler, connection_manager, exchange_map: dict[str, str] | None = None) -> None:
        self._crawler = crawler
        self._connection_manager = connection_manager
        self._latest_prices: dict[str, dict] = {}
        self._exchange_map: dict[str, str] = exchange_map or {}
        # Running day high/low tracking per symbol
        self._day_highs: dict[str, Decimal] = {}
        self._day_lows: dict[str, Decimal] = {}
        self._tracking_date: date | None = None
        # Lazy-loaded ticker map {symbol: ticker_id}
        self._ticker_map: dict[str, int] | None = None

    def set_exchange_map(self, exchange_map: dict[str, str]) -> None:
        """Update the symbol → exchange mapping for priority sorting."""
        self._exchange_map = exchange_map

    async def _ensure_ticker_map(self) -> dict[str, int]:
        """Lazy-load {symbol: ticker_id} mapping from DB."""
        if self._ticker_map is None:
            from app.services.ticker_service import TickerService
            from app.crawlers.vnstock_crawler import VnstockCrawler as _Crawler
            async with async_session() as session:
                svc = TickerService(session, _Crawler())
                self._ticker_map = await svc.get_ticker_id_map(exchange="HOSE")
            logger.info(f"Loaded ticker map: {len(self._ticker_map)} HOSE symbols")
        return self._ticker_map

    def _check_day_reset(self) -> None:
        """Reset day_high/day_low tracking at the start of each new trading day."""
        today = _now_vn().date()
        if self._tracking_date != today:
            self._day_highs.clear()
            self._day_lows.clear()
            self._tracking_date = today
            logger.info(f"Day tracking reset for {today}")

    def _update_day_extremes(self, symbol: str, price: Decimal) -> tuple[Decimal, Decimal]:
        """Update and return (day_high, day_low) for a symbol."""
        if symbol in self._day_highs:
            if price > self._day_highs[symbol]:
                self._day_highs[symbol] = price
            if price < self._day_lows[symbol]:
                self._day_lows[symbol] = price
        else:
            self._day_highs[symbol] = price
            self._day_lows[symbol] = price
        return self._day_highs[symbol], self._day_lows[symbol]

    async def poll_and_broadcast(self) -> None:
        """Fetch latest prices from VCI for ALL HOSE symbols, store snapshots, and broadcast.

        Always polls all symbols regardless of WebSocket subscribers.
        Broadcasts only changed prices to subscribed clients.
        """
        self._check_day_reset()

        ticker_map = await self._ensure_ticker_map()
        all_symbols = sorted(ticker_map.keys())[:settings.realtime_max_symbols]

        if not all_symbols:
            logger.warning("No HOSE symbols in ticker map — skipping poll")
            return

        try:
            prices = await self._crawler.fetch_price_board(all_symbols)
        except Exception as e:
            logger.warning(f"Price board poll failed: {e}")
            return

        if not prices:
            logger.debug("Empty price response — skipping")
            return

        # Save snapshots to DB
        await self._save_intraday_snapshots(prices, ticker_map)

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

    async def _save_intraday_snapshots(self, prices: dict[str, dict], ticker_map: dict[str, int]) -> None:
        """Bulk insert intraday price snapshots into the database."""
        from app.models.intraday_price import IntradayPrice

        rows = []
        now = _now_vn()
        for sym, data in prices.items():
            tid = ticker_map.get(sym)
            if tid is None:
                continue

            price_val = Decimal(str(data.get("close", data.get("price", 0))))
            if price_val <= 0:
                continue

            day_high, day_low = self._update_day_extremes(sym, price_val)

            rows.append(IntradayPrice(
                ticker_id=tid,
                symbol=sym,
                price=price_val,
                volume=int(data.get("volume", 0)),
                day_high=day_high,
                day_low=day_low,
                change=Decimal(str(data.get("change", 0))),
                change_pct=Decimal(str(data.get("change_pct", data.get("pct_change", 0)))),
                recorded_at=now,
            ))

        if not rows:
            return

        try:
            async with async_session() as session:
                session.add_all(rows)
                await session.commit()
            logger.debug(f"Saved {len(rows)} intraday snapshots")
        except Exception as e:
            logger.error(f"Failed to save intraday snapshots: {e}")

    def reset_daily_tracking(self) -> None:
        """Clear day high/low tracking. Called at start of each trading day."""
        self._day_highs.clear()
        self._day_lows.clear()
        self._tracking_date = None

    async def handle_ws_price_update(self, prices: dict[str, dict]) -> None:
        """Handle price updates from VNDirect WebSocket client.

        Same diff-detection logic as poll_and_broadcast but receives
        pre-parsed price data from the WS client callback.
        """
        changed: dict[str, dict] = {}
        for sym, price_data in prices.items():
            cached = self._latest_prices.get(sym)
            if cached != price_data:
                changed[sym] = price_data

        self._latest_prices.update(prices)

        if changed:
            await self._connection_manager.broadcast(changed)

    async def handle_ws_bid_ask_update(self, bid_asks: dict[str, dict]) -> None:
        """Handle bid/ask updates from VNDirect WebSocket client.

        Broadcasts bid/ask data as a separate message type to subscribers.
        """
        await self._connection_manager.broadcast_bid_ask(bid_asks)

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
