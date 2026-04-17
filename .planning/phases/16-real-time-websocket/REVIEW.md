---
phase: 16-real-time-websocket
reviewed: 2026-04-17T21:29:33Z
depth: deep
files_reviewed: 15
files_reviewed_list:
  - backend/app/services/realtime_price_service.py
  - backend/app/ws/__init__.py
  - backend/app/ws/prices.py
  - backend/app/crawlers/vnstock_crawler.py
  - backend/app/scheduler/manager.py
  - backend/app/scheduler/jobs.py
  - backend/app/main.py
  - backend/app/config.py
  - frontend/src/lib/use-realtime-prices.ts
  - frontend/src/components/connection-status.tsx
  - frontend/src/components/price-flash-cell.tsx
  - frontend/src/components/navbar.tsx
  - frontend/src/components/watchlist-table.tsx
  - frontend/src/components/holdings-table.tsx
  - frontend/src/app/ticker/[symbol]/page.tsx
  - frontend/src/app/layout.tsx
  - backend/tests/test_realtime_prices.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-04-17T21:29:33Z
**Depth:** deep
**Files Reviewed:** 15 source files + 1 test file
**Status:** issues_found

## Summary

Phase 16 adds WebSocket-based real-time price streaming: a backend polling service (APScheduler → VCI price_board → ConnectionManager → WebSocket broadcast) and a React context/hook system with flash animations. The architecture is clean and well-structured overall. However, there are several bugs: a stale React closure that breaks market-status recovery, a potential crash from NaN values in VCI data, accumulated server-side subscriptions that can never be removed, and a per-invocation service instantiation that defeats the in-memory cache design. One of these (NaN crash) is critical since it silently breaks all price broadcasting.

## Critical Issues

### CR-01: NaN in VCI price data causes ValueError crash or invalid JSON

**File:** `backend/app/crawlers/vnstock_crawler.py:143-150`
**Issue:** If the VCI API returns `NaN` for any field (common for illiquid/suspended tickers), `int(row[("match", "total_volume")])` raises `ValueError: cannot convert float NaN to integer`, crashing the entire poll cycle for all subscribed symbols. Even if volume is valid, `float(NaN)` for price/change fields produces `float('nan')` which serializes to the JavaScript literal `NaN` — not valid JSON — causing `JSON.parse()` failures on every connected frontend client.

This is critical because a single illiquid ticker in anyone's subscription list silently breaks price updates for ALL subscribers.

**Fix:**
```python
        for _, row in df.iterrows():
            sym = row[("listing", "symbol")]
            try:
                match_price = row[("match", "match_price")]
                price_change = row[("match", "price_change")]
                change_pct = row[("match", "price_change_percent")]
                total_vol = row[("match", "total_volume")]

                # Skip symbols with NaN data (suspended/illiquid tickers)
                if pd.isna(match_price) or pd.isna(total_vol):
                    logger.debug(f"Skipping {sym}: NaN in price data")
                    continue

                result[sym] = {
                    "price": float(match_price),
                    "change": float(price_change) if not pd.isna(price_change) else 0.0,
                    "change_pct": float(change_pct) if not pd.isna(change_pct) else 0.0,
                    "volume": int(total_vol),
                }
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping {sym}: invalid data — {e}")
                continue
```

## Warnings

### WR-01: Stale closure prevents recovery from `market_closed` status

**File:** `frontend/src/lib/use-realtime-prices.ts:143-148`
**Issue:** The `ws.onmessage` handler inside `connect()` captures `status` from the closure at the time `connect()` was called. The `useEffect` on line 172–185 has an empty dependency array, so `connect()` is only called once (at mount) when `status` is `"disconnected"`. The condition `else if (status === "market_closed")` on line 146 will **never** be true because the captured `status` is forever `"disconnected"`.

Consequence: When the market reopens and the server sends `{"type": "market_status", "is_open": true}`, the frontend stays stuck on `"market_closed"` status until the user refreshes the page or the WebSocket reconnects.

**Fix:** Use a functional state update to read the current status, or use a ref:
```typescript
case "market_status":
  if (msg.is_open === false) {
    setStatus("market_closed");
  } else {
    // Use functional update to read current status
    setStatus((prev) =>
      prev === "market_closed" ? "connected" : prev
    );
  }
  break;
```

### WR-02: Server-side WebSocket subscriptions accumulate indefinitely — no unsubscribe

**File:** `backend/app/ws/prices.py:41-44` and `frontend/src/lib/use-realtime-prices.ts:206-218`
**Issue:** The frontend `unsubscribe()` function (line 206) removes symbols from the local `subscribedSymbolsRef` but never sends a message to the server. The server's `ConnectionManager.subscribe()` only adds symbols (line 44: `self._connections[ws].update(symbols)`). There is no server-side unsubscribe handler.

As a user navigates between pages (watchlist → ticker detail → holdings), each page subscribes to its symbols. The server accumulates all subscriptions for the connection's lifetime. This is bounded by `realtime_max_symbols=50` at poll time, but the subscription set itself grows without bound per connection.

**Fix (backend):** Add an unsubscribe method and message handler:
```python
# In ConnectionManager:
def unsubscribe(self, ws: WebSocket, symbols: list[str]) -> None:
    if ws in self._connections:
        self._connections[ws] -= set(symbols)

# In websocket_prices handler, add:
elif msg_type == "unsubscribe":
    symbols = data.get("symbols", [])
    if isinstance(symbols, list):
        clean = [s.upper().strip() for s in symbols if isinstance(s, str)]
        connection_manager.unsubscribe(ws, clean)
```
**Fix (frontend):** Send unsubscribe message in the `unsubscribe` callback:
```typescript
const unsubscribe = useCallback((symbols: string[]) => {
  let changed = false;
  for (const s of symbols) {
    const upper = s.toUpperCase();
    if (subscribedSymbolsRef.current.has(upper)) {
      subscribedSymbolsRef.current.delete(upper);
      changed = true;
    }
  }
  if (changed) {
    setSubscribedSymbols(new Set(subscribedSymbolsRef.current));
    // Notify server
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "unsubscribe", symbols: symbols.map(s => s.toUpperCase()) }));
    }
  }
}, []);
```

### WR-03: RealtimePriceService is re-instantiated every poll — in-memory cache is always empty

**File:** `backend/app/scheduler/jobs.py:710-712`
**Issue:** `realtime_price_poll()` creates a new `VnstockCrawler()` and `RealtimePriceService()` on every invocation (every 30 seconds). Since `RealtimePriceService.__init__` sets `self._latest_prices = {}`, the cache starts empty each time and is discarded when the function returns. The `get_latest_prices()` method is never useful.

Currently the cache isn't used by any active code path (prices are broadcast directly to WS clients), so this doesn't cause user-visible bugs. However, it means any future REST endpoint or code that calls `service.get_latest_prices()` will always get an empty dict.

**Fix:** Make the service a module-level singleton (matching `connection_manager` pattern):
```python
# In realtime_price_service.py, at module level:
_service_instance: RealtimePriceService | None = None

def get_realtime_price_service() -> RealtimePriceService:
    global _service_instance
    if _service_instance is None:
        from app.crawlers.vnstock_crawler import VnstockCrawler
        from app.ws.prices import connection_manager
        _service_instance = RealtimePriceService(
            crawler=VnstockCrawler(),
            connection_manager=connection_manager,
        )
    return _service_instance
```

## Info

### IN-01: No input validation on symbol content in WebSocket subscribe handler

**File:** `backend/app/ws/prices.py:134`
**Issue:** Symbols are normalized to uppercase and stripped, but no validation on length or character content. A client could send symbols like `"A" * 10000` or strings with special characters. These are passed to `VnstockCrawler.fetch_price_board()` which sends them to VCI API. In a personal-use app this is low risk, but adding basic validation is good practice.

**Fix:** Add a simple length/format check:
```python
clean_symbols = [
    s.upper().strip() for s in symbols
    if isinstance(s, str) and s.strip() and len(s.strip()) <= 10
]
```

### IN-02: WebSocket `receive_json` parse failure causes full disconnect

**File:** `backend/app/ws/prices.py:121, 145-147`
**Issue:** If a client sends malformed JSON (or binary data), `ws.receive_json()` raises an exception. The broad `except Exception` on line 145 catches it and calls `disconnect()`, terminating the connection for what could be a transient client-side error. A more resilient approach would catch JSON decode errors specifically and send an error message back instead of disconnecting.

**Fix:**
```python
try:
    while True:
        try:
            data = await ws.receive_json()
        except ValueError:
            await ws.send_json({"type": "error", "message": "invalid JSON"})
            continue
        # ... rest of handler
```

---

_Reviewed: 2026-04-17T21:29:33Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: deep_
