# Requirements: Holo v2.0 — Full Coverage & Real-Time

**Defined:** 2026-04-17
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu HOSE real-time để gợi ý trading chính xác và kịp thời qua Telegram.

## v2.0 Requirements

Requirements for v2.0 milestone. Each maps to roadmap phases.

### Market Coverage

- [x] **MKT-01**: User can view OHLCV data for HNX and UPCOM tickers alongside existing HOSE tickers
- [x] **MKT-02**: User can filter market overview, stock lists, and heatmap by exchange (HOSE/HNX/UPCOM/All)
- [x] **MKT-03**: System crawls HNX and UPCOM tickers on the same daily schedule as HOSE with staggered execution
- [x] **MKT-04**: AI analysis runs on tiered schedule — HOSE fully daily, HNX/UPCOM for watchlisted tickers daily, rest on-demand

### Real-Time

- [x] **RT-01**: Dashboard receives price updates via WebSocket during market hours without manual refresh
- [x] **RT-02**: System polls VCI at 30-second intervals during market hours for watchlist and portfolio tickers
- [x] **RT-03**: WebSocket automatically connects during market hours (9:00-11:30, 13:00-14:45 UTC+7) and disconnects outside

### Portfolio Enhancements

- [x] **PORT-08**: User can see dividend income on held positions when corporate events have matching record dates
- [x] **PORT-09**: User can view portfolio total value over time as a line chart
- [x] **PORT-10**: User can view portfolio allocation as a pie chart by ticker or by sector
- [x] **PORT-11**: User can edit or delete existing trades with automatic FIFO lot recalculation
- [x] **PORT-12**: User can import trades from broker CSV files (with format auto-detection and dry-run preview)

### Health Enhancements

- [ ] **HEALTH-08**: Health dashboard shows Gemini API usage (tokens consumed, requests made) vs free tier limits
- [ ] **HEALTH-09**: Health dashboard shows pipeline execution timeline with per-step duration visualization
- [ ] **HEALTH-10**: System sends Telegram notification when health checks detect sustained errors or stale data

### Corporate Actions Enhancements

- [x] **CORP-06**: System tracks rights issues from VNDirect with dilution impact on existing positions
- [x] **CORP-07**: User receives Telegram alerts for upcoming ex-dates on watchlisted and held tickers
- [x] **CORP-08**: User can view corporate events calendar on dashboard with filterable event types
- [x] **CORP-09**: User can toggle between adjusted and raw price display on candlestick charts

## Future Requirements (v3.0)

Deferred to future milestone. Tracked but not in current roadmap.

### Market Coverage
- **MKT-05**: User can compare tickers across exchanges side by side
- **MKT-06**: System supports exchange-specific market hours (UPCOM continuous session)

### Real-Time
- **RT-04**: WebSocket pushes real-time trade/order flow data during market hours

### Portfolio
- **PORT-13**: User can set target allocation per ticker/sector and see rebalancing suggestions

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Auto-trade execution | Legal/financial risk — gợi ý only |
| Broker API integration | VN broker APIs not standardized, fragile |
| Multi-currency / multi-market portfolio | HOSE + VND only for now |
| Tax calculation module | VN flat 0.1% on sell — too simple for a module |
| Options / derivatives tracking | HOSE stocks only |
| Weighted average cost (WAC) | FIFO is VN standard for individuals |
| Fine-tuning Gemini | Requires labeled data + cost, iterate on prompts instead |
| Multi-model AI consensus | Triples cost for marginal benefit |
| Grafana / Prometheus | Overkill for single-user, use built-in health page |
| Message queue (Redis/RabbitMQ) | Overkill for single-user, keep APScheduler |
| Real-time corporate action detection | Events announced weeks ahead, daily check sufficient |
| True WebSocket from exchange | No free VN market WebSocket; 30s polling sufficient for personal use |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| MKT-01 | Phase 12: Multi-Market Foundation | Complete |
| MKT-02 | Phase 12: Multi-Market Foundation | Complete |
| MKT-03 | Phase 12: Multi-Market Foundation | Complete |
| MKT-04 | Phase 12: Multi-Market Foundation | Complete |
| PORT-08 | Phase 13: Portfolio Enhancements | Complete |
| PORT-09 | Phase 13: Portfolio Enhancements | Complete |
| PORT-10 | Phase 13: Portfolio Enhancements | Complete |
| PORT-11 | Phase 13: Portfolio Enhancements | Complete |
| PORT-12 | Phase 13: Portfolio Enhancements | Complete |
| CORP-06 | Phase 14: Corporate Actions Enhancements | Complete |
| CORP-07 | Phase 14: Corporate Actions Enhancements | Complete |
| CORP-08 | Phase 14: Corporate Actions Enhancements | Complete |
| CORP-09 | Phase 14: Corporate Actions Enhancements | Complete |
| HEALTH-08 | Phase 15: Health & Monitoring | Pending |
| HEALTH-09 | Phase 15: Health & Monitoring | Pending |
| HEALTH-10 | Phase 15: Health & Monitoring | Pending |
| RT-01 | Phase 16: Real-Time WebSocket | Complete |
| RT-02 | Phase 16: Real-Time WebSocket | Complete |
| RT-03 | Phase 16: Real-Time WebSocket | Complete |

**Coverage:**
- v2.0 requirements: 17 total
- Mapped to phases: 17 ✓
- Unmapped: 0

---
*Requirements defined: 2026-04-17*
*Last updated: 2026-04-17 — roadmap traceability complete*
