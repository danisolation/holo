# Phase 16: Real-Time WebSocket — Implementation Decisions

## Phase Goal
Dashboard displays live price updates during market hours without manual page refresh.

## Requirements
- **RT-01**: Dashboard receives price updates via WebSocket during market hours without manual refresh
- **RT-02**: System polls VCI at 30-second intervals during market hours for watchlist and portfolio tickers
- **RT-03**: WebSocket automatically connects during market hours (9:00-11:30, 13:00-14:45 UTC+7) and disconnects outside

## Key Constraint (from Research)
No free VN stock exchange WebSocket feed exists. The approach is:
- Backend polls VCI (vnstock) at 30-second intervals during market hours
- Backend pushes updates to frontend via WebSocket
- This gives "near-real-time" (30s latency) without exchange WebSocket fees

## Implementation Decisions

### D-16-01: Architecture Pattern
**Decision:** FastAPI WebSocket endpoint + APScheduler polling job. Backend is the single source of truth — it polls VCI, stores latest prices in memory (dict), and broadcasts to all connected WebSocket clients. No direct frontend-to-VCI polling.
**Rationale:** Centralizes rate limiting, avoids browser CORS issues with VCI, single polling point prevents duplicate requests.

### D-16-02: WebSocket Endpoint
**Decision:** `ws://host/ws/prices` — single WebSocket endpoint. Client sends a JSON subscribe message with list of symbols. Server pushes price updates only for subscribed symbols. Server sends heartbeat every 15s to keep connection alive.
**Rationale:** Single endpoint simplifies connection management. Symbol filtering reduces bandwidth. Heartbeat prevents proxy/NAT timeouts.

### D-16-03: VCI Polling Strategy
**Decision:** APScheduler interval job `realtime_price_poll` runs every 30 seconds during market hours only. Polls vnstock `stock.trading.price_board()` for unique symbols from all connected clients' subscriptions. Batch into single API call (vnstock supports multi-symbol price board).
**Rationale:** 30s interval stays well within VCI rate limits. Union of all client subscriptions means one API call covers all. vnstock price_board returns current price, change, volume for multiple symbols.

### D-16-04: Market Hours Logic
**Decision:** Market hours check function: `is_market_open()` returns True during 9:00-11:30 AND 13:00-14:45 on weekdays (Mon-Fri), VN timezone. The polling job runs continuously but only polls VCI when market is open. WebSocket stays connected outside market hours but sends no updates (client shows "Thị trường đóng cửa").
**Rationale:** Keeping WebSocket connected avoids reconnection overhead. Backend decides when to poll, not the client. Market hours are fixed (HOSE/HNX/UPCOM share the same sessions).

### D-16-05: Frontend Auto-Connect
**Decision:** React hook `useRealtimePrices(symbols)` manages WebSocket lifecycle. Auto-connects on mount, auto-reconnects on disconnect with exponential backoff (1s, 2s, 4s, max 30s). Shows connection status indicator. Merges real-time prices into react-query cache for seamless integration with existing data.
**Rationale:** Hook pattern matches existing architecture. Cache merging means existing components (watchlist, portfolio, ticker detail) automatically show real-time prices without code changes.

### D-16-06: Price Update Message Format
**Decision:** Server sends JSON: `{ "type": "price_update", "data": { "VNM": { "price": 82500, "change": 1500, "change_pct": 1.85, "volume": 12345678, "updated_at": "..." }, ... } }`. Also `{ "type": "heartbeat" }` and `{ "type": "market_status", "is_open": bool, "session": "morning|afternoon|closed" }`.
**Rationale:** Structured messages with type field allow clean client-side routing. Market status lets UI show session info.

### D-16-07: Connection Manager
**Decision:** In-memory `ConnectionManager` class tracks active WebSocket connections and their symbol subscriptions. Methods: connect(ws), disconnect(ws), subscribe(ws, symbols), broadcast(data). No persistence needed — reconnect re-subscribes.
**Rationale:** Simple pattern, well-documented in FastAPI docs. In-memory is fine for single-user app.

### D-16-08: Dashboard Integration
**Decision:** Real-time price updates appear as flashing green/red backgrounds on price cells in watchlist table, dashboard market overview, and portfolio holdings. Flash lasts 1 second. Connection status indicator in navbar: 🟢 connected / 🟡 reconnecting / 🔴 disconnected / ⚫ market closed.
**Rationale:** Subtle flash animation draws attention without being distracting. Navbar indicator gives persistent visibility of connection state.

### D-16-09: Polling Scope
**Decision:** Poll only tickers that are: (a) in any user's watchlist, OR (b) in portfolio holdings, OR (c) currently viewed on ticker detail page. Maximum ~50 unique symbols per poll. If no clients connected, skip polling entirely.
**Rationale:** Polling 400+ tickers every 30s is wasteful and may hit rate limits. Scoping to active interest keeps requests minimal.

## Out of Scope
- True exchange WebSocket feed (no free option exists)
- Order book / trade flow data
- Real-time technical indicator recomputation (daily is sufficient)
- Multi-user connection isolation (single-user app)
