# Requirements: Holo v1.1 — Reliability & Portfolio

**Defined:** 2026-04-16
**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu HOSE real-time để gợi ý trading chính xác và kịp thời qua Telegram.

## v1.1 Requirements

Requirements for v1.1 milestone. Each maps to roadmap phases.

### Corporate Actions

- [ ] **CORP-01**: User can see adjusted historical prices that account for stock splits, dividends, and bonus shares
- [ ] **CORP-02**: System crawls corporate events from VCI and stores in database with event type classification
- [ ] **CORP-03**: System computes cumulative adjustment factors and populates `adjusted_close` for all historical prices
- [ ] **CORP-04**: System runs daily corporate action check and auto-adjusts prices on new events
- [ ] **CORP-05**: Cash dividends, stock dividends, bonus shares, and stock splits are each handled with correct VN market formulas

### Portfolio Tracking

- [ ] **PORT-01**: User can manually enter buy/sell trades with ticker, quantity, price, date, and fees
- [ ] **PORT-02**: User can view current holdings with quantity, average cost, market value, and P&L
- [ ] **PORT-03**: System calculates cost basis using FIFO method (first bought = first sold)
- [ ] **PORT-04**: User can see realized P&L on closed positions (per-trade and aggregate)
- [ ] **PORT-05**: User can see unrealized P&L on open positions using latest market price
- [ ] **PORT-06**: User can see portfolio summary: total invested, market value, total return %
- [ ] **PORT-07**: User can view trade history sorted and filtered by date, ticker, side

### AI Improvements

- [ ] **AI-07**: AI prompts use `system_instruction` for persona separation instead of baking into user prompt
- [ ] **AI-08**: AI prompts include few-shot examples for each analysis type for output consistency
- [ ] **AI-09**: Scoring rubric defines explicit anchors (1-2 weak, 3-4 minor, 5-6 moderate, 7-8 strong, 9-10 very strong)
- [ ] **AI-10**: Technical analysis prompt includes latest close price and price-vs-SMA percentages
- [ ] **AI-11**: Vietnamese language usage is consistent across prompt types (English for tech/fund, Vietnamese for combined/sentiment)
- [ ] **AI-12**: Structured output failures trigger one retry at low temperature before falling back to JSON parse
- [ ] **AI-13**: Temperature is tuned per analysis type (technical=0.1, fundamental=0.2, sentiment=0.3)

### Error Recovery

- [ ] **ERR-01**: Failed tickers in AI analysis batches are re-batched for one additional retry attempt
- [ ] **ERR-02**: Permanently failed items are stored in a dead letter table with error details and retry count
- [ ] **ERR-03**: Partial pipeline failures allow remaining tickers to proceed (graceful degradation)
- [ ] **ERR-04**: Every scheduled job logs execution start/end, status, and result summary to `job_executions` table
- [ ] **ERR-05**: Complete crawler failure triggers Telegram notification to user
- [ ] **ERR-06**: Circuit breaker stops calling external APIs after N consecutive failures, auto-resets after cooldown
- [ ] **ERR-07**: Failed jobs are automatically retried once after 30-minute delay (max 3 retries)

### System Health

- [ ] **HEALTH-01**: Health dashboard shows data freshness (last update timestamp per data type) with stale data flags
- [ ] **HEALTH-02**: Health dashboard shows last crawl status per job (green/yellow/red)
- [ ] **HEALTH-03**: Health dashboard shows error rate per job over last 7 days
- [ ] **HEALTH-04**: Health dashboard shows database connection pool status (active/idle)
- [ ] **HEALTH-05**: Health dashboard page exists at `/dashboard/health` with status cards
- [ ] **HEALTH-06**: Scheduler status endpoint is enhanced with last run result
- [ ] **HEALTH-07**: User can manually trigger jobs (crawl, indicators, AI analysis) from health dashboard

### Telegram Portfolio

- [ ] **TBOT-01**: `/buy <ticker> <qty> <price>` command records a buy trade
- [ ] **TBOT-02**: `/sell <ticker> <qty> <price>` command records a sell trade and shows realized P&L
- [ ] **TBOT-03**: `/portfolio` command shows all holdings with current P&L
- [ ] **TBOT-04**: Daily portfolio P&L notification sent at 16:00 alongside market summary
- [ ] **TBOT-05**: `/pnl <ticker>` command shows detailed P&L with FIFO lot breakdown
- [ ] **TBOT-06**: Daily summary highlights owned tickers first with position P&L context

## Future Requirements (v2.0)

Deferred to next milestone. Tracked but not in current roadmap.

### Market Coverage
- **MKT-01**: System crawls HNX and UPCOM tickers in addition to HOSE
- **MKT-02**: User can filter dashboard by exchange (HOSE/HNX/UPCOM)

### Real-Time Features
- **RT-01**: Near-real-time price updates via WebSocket during market hours
- **RT-02**: Faster polling interval (< 1 minute) during market hours

### Portfolio Enhancements
- **PORT-08**: Dividend income tracking on held positions at record date
- **PORT-09**: Portfolio performance chart (total value over time)
- **PORT-10**: Portfolio allocation pie chart by sector/ticker
- **PORT-11**: Trade edit/delete for correcting mistakes
- **PORT-12**: Broker CSV import for bulk trade entry

### Health Enhancements
- **HEALTH-08**: Gemini API usage tracker (tokens, requests vs free tier limits)
- **HEALTH-09**: Pipeline execution timeline (Gantt-style per-step visualization)
- **HEALTH-10**: Telegram health notification on errors

### Corporate Actions Enhancements
- **CORP-06**: Rights issue tracking with dilution impact
- **CORP-07**: Corporate action Telegram alerts for upcoming ex-dates
- **CORP-08**: Event calendar view on dashboard
- **CORP-09**: Adjusted vs raw price toggle on chart

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

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| — | — | — |

**Coverage:**
- v1.1 requirements: 35 total
- Mapped to phases: 0
- Unmapped: 35 ⚠️

---
*Requirements defined: 2026-04-16*
*Last updated: 2026-04-16 after initial definition*
