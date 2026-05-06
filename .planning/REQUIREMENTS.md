# Requirements: Holo v16.0 Real-Time Price

**Defined:** 2026-05-06
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment + tin đồn) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua web dashboard.

## v16.0 Requirements

### WebSocket Data

- [ ] **WS-01**: System connects to VNDirect WebSocket and receives Stock Price (SP) messages
- [ ] **WS-02**: System parses Bid/Ask (BA) messages for watchlist tickers
- [ ] **WS-03**: System auto-reconnects with exponential backoff on disconnect
- [ ] **WS-04**: System only operates during market hours (9:00-11:30, 13:00-14:45 UTC+7)

### Backend Broadcasting

- [ ] **BC-01**: Backend WebSocket server broadcasts real-time prices to connected frontend clients
- [ ] **BC-02**: New clients receive latest snapshot of all subscribed tickers on connect
- [ ] **BC-03**: Subscription filtered to watchlist tickers only

### Frontend Display

- [ ] **FE-01**: Dashboard shows real-time price with flash animation (green up / red down)
- [ ] **FE-02**: Live candlestick chart updates intraday bar in real-time
- [ ] **FE-03**: Bid/Ask depth displayed on ticker detail page

## Future Requirements

None identified.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full order book | VNDirect WS only provides top 3 bid/ask levels |
| Price alerts via WebSocket | Existing APScheduler polling alerts sufficient |
| Historical tick data storage | OHLCV daily data already covers analysis needs |
| Multi-exchange real-time | Focus HOSE only — HNX/UPCOM volume too low |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| WS-01 | Phase 76 | Pending |
| WS-02 | Phase 76 | Pending |
| WS-03 | Phase 76 | Pending |
| WS-04 | Phase 76 | Pending |
| BC-01 | Phase 77 | Pending |
| BC-02 | Phase 77 | Pending |
| BC-03 | Phase 77 | Pending |
| FE-01 | Phase 78 | Pending |
| FE-02 | Phase 78 | Pending |
| FE-03 | Phase 79 | Pending |

**Coverage:**
- v15.0 requirements: 12 total
- Mapped to phases: 12 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-06*
*Last updated: 2026-05-06 after initial definition*
