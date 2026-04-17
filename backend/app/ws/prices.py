"""WebSocket connection manager and price update endpoint.

Manages WebSocket connections with per-client symbol subscriptions.
Provides a /ws/prices endpoint for real-time price streaming.

Message protocol:
  Client → Server:
    {"type": "subscribe", "symbols": ["VNM", "FPT"]}
  Server → Client:
    {"type": "price_update", "data": {"VNM": {"price": 82500, ...}}}
    {"type": "heartbeat"}
    {"type": "market_status", "is_open": true, "session": "morning"}
"""
from __future__ import annotations

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger


class ConnectionManager:
    """In-memory WebSocket connection manager with symbol subscriptions.

    Tracks active connections and their subscribed symbols.
    Broadcasts price updates filtered to each client's subscriptions.
    """

    def __init__(self) -> None:
        # WebSocket → set of subscribed symbols
        self._connections: dict[WebSocket, set[str]] = {}

    async def connect(self, ws: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        self._connections[ws] = set()
        logger.info(f"WebSocket client connected (total: {len(self._connections)})")

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self._connections.pop(ws, None)
        logger.info(f"WebSocket client disconnected (total: {len(self._connections)})")

    def subscribe(self, ws: WebSocket, symbols: list[str]) -> None:
        """Add symbols to a client's subscription set."""
        if ws in self._connections:
            self._connections[ws].update(symbols)
            logger.debug(f"Client subscribed to {symbols} (total: {len(self._connections[ws])})")

    def get_all_subscribed_symbols(self) -> set[str]:
        """Return union of all clients' subscribed symbols."""
        all_symbols: set[str] = set()
        for syms in self._connections.values():
            all_symbols.update(syms)
        return all_symbols

    async def broadcast(self, prices: dict[str, dict]) -> None:
        """Send price updates to each client, filtered by their subscriptions.

        Dead connections are removed silently.
        """
        dead: list[WebSocket] = []
        for ws, symbols in list(self._connections.items()):
            # Filter to only symbols this client subscribed to
            client_prices = {s: p for s, p in prices.items() if s in symbols}
            if not client_prices:
                continue
            try:
                await ws.send_json({
                    "type": "price_update",
                    "data": client_prices,
                })
            except Exception:
                logger.warning("Failed to send to WebSocket client — removing")
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    async def send_heartbeat(self) -> None:
        """Send heartbeat message to all connected clients."""
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json({"type": "heartbeat"})
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def send_market_status(self, is_open: bool, session: str) -> None:
        """Send market status update to all connected clients."""
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json({
                    "type": "market_status",
                    "is_open": is_open,
                    "session": session,
                })
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


# ── Module-level singleton ──────────────────────────────────────────────────

connection_manager = ConnectionManager()


# ── WebSocket route (mounted on FastAPI app in main.py) ─────────────────────

async def websocket_prices(ws: WebSocket) -> None:
    """WebSocket endpoint at /ws/prices.

    Accepts connection, listens for subscribe messages, removes on disconnect.
    Validates: max 50 symbols per subscribe, symbols must be uppercase.
    """
    await ws.accept()
    await connection_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "subscribe":
                symbols = data.get("symbols", [])
                # Validation
                if not isinstance(symbols, list):
                    await ws.send_json({"type": "error", "message": "symbols must be a list"})
                    continue
                if len(symbols) > 50:
                    await ws.send_json({"type": "error", "message": "max 50 symbols per subscribe"})
                    continue
                # Normalize to uppercase
                clean_symbols = [s.upper().strip() for s in symbols if isinstance(s, str) and s.strip()]
                connection_manager.subscribe(ws, clean_symbols)
                await ws.send_json({
                    "type": "subscribed",
                    "symbols": clean_symbols,
                })
            else:
                await ws.send_json({"type": "error", "message": f"unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        connection_manager.disconnect(ws)
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        connection_manager.disconnect(ws)
