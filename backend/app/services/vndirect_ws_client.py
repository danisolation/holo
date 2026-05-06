"""VNDirect WebSocket client for real-time stock price data.

Connects to VNDirect's public WebSocket endpoint to receive real-time
Stock Price (SP) and Bid/Ask (BA) updates. Manages lifecycle with
auto-reconnect (exponential backoff) and market hours enforcement.

Protocol:
  Subscribe: {"type": "registConsumer", "data": {"sequence": 0, "params": {"name": "SP"|"BA", "codes": [...]}}}
  Receive:   {"type": "SP"|"BA", "data": "field1|field2|..."}

Reference: github.com/hoangnt2601/Real-time-data-vndirect
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger

from app.services.realtime_price_service import is_market_open

# Default VNDirect WebSocket endpoint
VNDIRECT_WS_URL = "wss://price-cmc-04.vndirect.com.vn/realtime/websocket"

# Backoff constants
_BACKOFF_BASE = 1.0
_BACKOFF_MAX = 60.0
_MAX_CONSECUTIVE_FAILURES = 5  # After this many failures, trigger fallback


def _try_float(x: str) -> float:
    """Convert string to float, returning 0.0 on failure."""
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0


def parse_sp_message(raw: str) -> dict[str, Any] | None:
    """Parse VNDirect SP (Stock Price) pipe-delimited message.

    SP fields (23 total, 0-indexed):
      0: floorCode, 1: tradingDate, 2: time, 3: code (symbol),
      4: companyName, 5: stockType, 6: totalRoom, 7: currentRoom,
      8: basicPrice (ref), 9: openPrice, 10: closePrice,
      11: currentPrice (last match), 12: currentQtty (match volume),
      13: highestPrice, 14: lowestPrice, 15: ceilingPrice, 16: floorPrice,
      17: averagePrice, 18: accumulatedVal, 19: buyForeignQtty,
      20: sellForeignQtty, 21: projectOpen, 22: sequence

    Returns structured dict or None if parsing fails.
    """
    if not raw or not isinstance(raw, str):
        return None
    fields = raw.split("|")
    if len(fields) < 23:
        return None
    try:
        symbol = fields[3].strip()
        if not symbol:
            return None
        ref_price = _try_float(fields[8])
        current_price = _try_float(fields[11])
        change = current_price - ref_price if ref_price else 0.0
        change_pct = (change / ref_price * 100) if ref_price else 0.0

        return {
            "symbol": symbol,
            "price": current_price,
            "ref_price": ref_price,
            "open": _try_float(fields[9]),
            "high": _try_float(fields[13]),
            "low": _try_float(fields[14]),
            "ceiling": _try_float(fields[15]),
            "floor": _try_float(fields[16]),
            "volume": _try_float(fields[12]),
            "accumulated_val": _try_float(fields[18]),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
        }
    except (IndexError, TypeError):
        return None


def parse_ba_message(raw: str) -> dict[str, Any] | None:
    """Parse VNDirect BA (Bid/Ask) pipe-delimited message.

    BA fields (20 total, 0-indexed):
      0: time, 1: code (symbol),
      2: bidPrice01, 3: bidQtty01, 4: bidPrice02, 5: bidQtty02,
      6: bidPrice03, 7: bidQtty03,
      8: offerPrice01, 9: offerQtty01, 10: offerPrice02, 11: offerQtty02,
      12: offerPrice03, 13: offerQtty03,
      14: accumulatedVol, 15: matchPrice, 16: matchQtty, 17: matchValue,
      18: totalOfferQtty, 19: totalBidQtty

    Returns structured dict with bids (descending) and asks (ascending), or None.
    """
    if not raw or not isinstance(raw, str):
        return None
    fields = raw.split("|")
    if len(fields) < 20:
        return None
    try:
        symbol = fields[1].strip()
        if not symbol:
            return None
        bids = [
            {"price": _try_float(fields[2]), "volume": _try_float(fields[3])},
            {"price": _try_float(fields[4]), "volume": _try_float(fields[5])},
            {"price": _try_float(fields[6]), "volume": _try_float(fields[7])},
        ]
        asks = [
            {"price": _try_float(fields[8]), "volume": _try_float(fields[9])},
            {"price": _try_float(fields[10]), "volume": _try_float(fields[11])},
            {"price": _try_float(fields[12]), "volume": _try_float(fields[13])},
        ]
        return {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "match_price": _try_float(fields[15]),
            "match_volume": _try_float(fields[16]),
            "total_bid_volume": _try_float(fields[19]),
            "total_ask_volume": _try_float(fields[18]),
        }
    except (IndexError, TypeError):
        return None


class VNDirectWSClient:
    """WebSocket client for VNDirect real-time price data.

    Manages connection lifecycle:
    - Only connects during market hours (9:00-11:30, 13:00-14:45 weekdays UTC+7)
    - Auto-reconnects with exponential backoff on disconnect
    - Parses SP/BA messages and dispatches to callbacks
    """

    def __init__(
        self,
        symbols: list[str],
        on_price_update: Callable[[dict[str, dict]], Awaitable[None]],
        on_bid_ask_update: Callable[[dict[str, dict]], Awaitable[None]] | None = None,
        ws_url: str = VNDIRECT_WS_URL,
        on_fallback: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._symbols = [s.upper() for s in symbols]
        self._on_price_update = on_price_update
        self._on_bid_ask_update = on_bid_ask_update
        self._ws_url = ws_url
        self._running = False
        self._ws = None
        self._reconnect_attempt = 0
        self._on_fallback = on_fallback
        self._fallback_triggered = False

    def update_symbols(self, symbols: list[str]) -> None:
        """Update the list of symbols to subscribe to."""
        self._symbols = [s.upper() for s in symbols]

    def _should_connect(self) -> bool:
        """Check if we should connect (market hours only)."""
        return is_market_open()

    @staticmethod
    def _calculate_backoff(attempt: int) -> float:
        """Calculate exponential backoff delay: min(2^attempt, 60) seconds."""
        return min(_BACKOFF_BASE * (2 ** attempt), _BACKOFF_MAX)

    async def start(self) -> None:
        """Main loop: connect during market hours, sleep otherwise."""
        self._running = True
        logger.info(f"VNDirect WS client starting for {len(self._symbols)} symbols")

        while self._running:
            if not self._should_connect():
                logger.debug("Market closed — sleeping 60s before recheck")
                await asyncio.sleep(60)
                continue

            try:
                await self._connect_and_listen()
            except asyncio.CancelledError:
                break
            except Exception as e:
                if not self._running:
                    break
                delay = self._calculate_backoff(self._reconnect_attempt)
                logger.warning(
                    f"VNDirect WS disconnected: {e}. "
                    f"Reconnecting in {delay:.1f}s (attempt {self._reconnect_attempt})"
                )
                self._reconnect_attempt += 1

                # Auto-fallback to VCI polling after N consecutive failures
                if (
                    self._reconnect_attempt >= _MAX_CONSECUTIVE_FAILURES
                    and self._on_fallback
                    and not self._fallback_triggered
                ):
                    logger.warning(
                        f"VNDirect WS failed {self._reconnect_attempt} times — "
                        f"activating VCI polling fallback"
                    )
                    self._fallback_triggered = True
                    await self._on_fallback()

                await asyncio.sleep(delay)

        logger.info("VNDirect WS client stopped")

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def _connect_and_listen(self) -> None:
        """Connect to VNDirect WS, subscribe, and listen for messages."""
        import websockets

        logger.info(f"Connecting to VNDirect WS: {self._ws_url}")
        async with websockets.connect(self._ws_url, ssl=True) as ws:
            self._ws = ws
            self._reconnect_attempt = 0
            logger.info("VNDirect WS connected — subscribing")

            await self._subscribe(ws, "SP", self._symbols)
            await self._subscribe(ws, "BA", self._symbols)

            while self._running:
                if not self._should_connect():
                    logger.info("Market closed — disconnecting until next session")
                    break
                try:
                    raw_msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    await self._handle_message(raw_msg)
                except asyncio.TimeoutError:
                    # No message in 30s — send ping or just continue
                    continue

        self._ws = None

    async def _subscribe(self, ws, msg_type: str, codes: list[str]) -> None:
        """Send subscription message to VNDirect WS."""
        msg = json.dumps({
            "type": "registConsumer",
            "data": {
                "sequence": 0,
                "params": {
                    "name": msg_type,
                    "codes": codes,
                },
            },
        })
        await ws.send(msg)
        logger.debug(f"Subscribed to {msg_type} for {len(codes)} symbols")

    async def _handle_message(self, raw_msg: str) -> None:
        """Parse incoming message and dispatch to appropriate callback."""
        try:
            obj = json.loads(raw_msg)
        except (json.JSONDecodeError, TypeError):
            return

        msg_type = obj.get("type")
        data = obj.get("data")
        if not msg_type or not data or not isinstance(data, str):
            return

        if msg_type == "SP":
            parsed = parse_sp_message(data)
            if parsed:
                symbol = parsed["symbol"]
                price_data = {
                    "price": parsed["price"],
                    "change": parsed["change"],
                    "change_pct": parsed["change_pct"],
                    "volume": parsed["volume"],
                    "high": parsed["high"],
                    "low": parsed["low"],
                    "open": parsed["open"],
                    "ref_price": parsed["ref_price"],
                    "ceiling": parsed["ceiling"],
                    "floor": parsed["floor"],
                }
                await self._on_price_update({symbol: price_data})

        elif msg_type == "BA":
            parsed = parse_ba_message(data)
            if parsed and self._on_bid_ask_update:
                symbol = parsed["symbol"]
                await self._on_bid_ask_update({symbol: parsed})
