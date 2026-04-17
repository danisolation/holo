# Feature Landscape — v2.0 Full Coverage & Real-Time

**Domain:** Stock Intelligence Platform — v2.0 Expansion Features
**Researched:** 2026-04-17
**Overall Confidence:** HIGH (based on existing codebase analysis, vnstock 3.5.1 source inspection, VN market domain knowledge)

**Context:** v1.0 + v1.1 shipped with: 400 HOSE ticker OHLCV crawling, 12 technical indicators + Gemini AI scoring, CafeF news + 3D recommendations, Telegram bot (10 commands), Next.js dashboard, error recovery (circuit breakers, DLQ, auto-retry), corporate actions (splits, dividends, bonus shares, adjusted prices), portfolio (buy/sell, FIFO lots, realized/unrealized P&L), AI improvements (system_instruction, few-shot, scoring rubric), health dashboard, and Telegram portfolio commands. This research covers ONLY v2.0 NEW features.

---

## Table Stakes

Features users expect given existing v1.x functionality. Missing = platform feels incomplete.

| Feature | Why Expected | Complexity | Req ID | Notes |
|---------|--------------|------------|--------|-------|
| Exchange filter on dashboard | Users seeing 1700 tickers need filtering by HOSE/HNX/UPCOM | Low | MKT-02 | Ticker model already has `exchange` column; add query param + UI tabs |
| Trade edit for mistakes | Manual trade entry will have typos; no edit = frustration | Med | PORT-11 | Only safe for unconsumed BUY trades or latest trades; FIFO chain complicates arbitrary edits |
| Trade delete for mistakes | Same as edit — correcting errors is basic functionality | Med | PORT-11 | Must recalculate FIFO lots after delete; restrict to most-recent or unconsumed trades |
| Adjusted/raw price toggle | Platform computes adjusted_close but never shows it on chart | Low | CORP-09 | `adjusted_close` column exists in `daily_prices`; frontend just needs toggle + API param |
| Telegram health alerts on errors | v1.1 only alerts on complete job failure; stale data silently degrades | Low | HEALTH-10 | Extend existing ERR-05 pattern; add periodic health check job |
| Ex-date alerts for held positions | Platform tracks corporate events + portfolio but doesn't connect them | Med | CORP-07 | Join corporate_events.ex_date with lots.ticker_id WHERE remaining_quantity > 0 |

## Differentiators

Features that set the platform apart from basic stock trackers. Not expected, but valued.

| Feature | Value Proposition | Complexity | Req ID | Notes |
|---------|-------------------|------------|--------|-------|
| Multi-market HNX/UPCOM crawling | ~1300 additional tickers; covers entire VN stock market | Med-High | MKT-01 | vnstock already supports all exchanges via VCI; complexity is in scale (3x crawl time, 3x AI cost) |
| WebSocket real-time streaming | Intraday price visibility during market hours (9:00-14:30 ICT) | High | RT-01, RT-02 | No free VN market WebSocket exists; implement as FastAPI WS endpoint polling VCI at 30s intervals |
| Dividend income tracking | Shows actual cash returns from held positions, not just capital gains | Med | PORT-08 | Cross-reference CorporateEvent (CASH_DIVIDEND) at record_date with Lot holdings; new table needed |
| Portfolio performance chart | Visual P&L over time; most compelling portfolio view | Med | PORT-09 | Compute daily portfolio value from trades + daily_prices; recharts LineChart (already installed) |
| Portfolio allocation chart | Visual breakdown by ticker/sector | Low | PORT-10 | Holdings data already computed; recharts PieChart already used in dashboard; straightforward |
| Broker CSV import | Bulk import trades from VN broker export files | Med-High | PORT-12 | Each VN broker (SSI, VNDirect, TCBS, VCBS) has unique format; need per-broker parsers |
| Gemini API usage tracking | Visibility into free-tier consumption to avoid surprise throttling | Med | HEALTH-08 | Parse `usage_metadata` from Gemini responses; new tracking table; usage vs limits dashboard |
| Pipeline execution timeline | Gantt-style visualization of daily job chain | Med | HEALTH-09 | job_executions already has started_at/completed_at; custom frontend rendering needed |
| Rights issue tracking | Complete corporate action coverage; VN market has frequent rights issues | Med | CORP-06 | New event type RIGHTS_ISSUE; dilution calculation; user decision tracking (exercise/lapse) |
| Event calendar view | Visual upcoming corporate events with date-based navigation | Med | CORP-08 | API + frontend list component grouped by week; filter by held tickers |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| True exchange WebSocket feed | VN exchange WebSocket APIs (SSI, TCBS) require broker registration, API keys, have strict rate limits, are unstable | Poll VCI via vnstock at 30s intervals; push to frontend via FastAPI WebSocket. "Near-real-time" sufficient for personal use |
| Universal CSV parser with AI | Using AI to auto-detect CSV columns is over-engineered and error-prone for financial data | Build explicit parsers for top 4 VN brokers (SSI, VNDirect, TCBS, VCBS) + manual column mapping fallback |
| FullCalendar-style calendar | Heavy library for a single-user view of ~10-20 events/month | Simple list view grouped by week with date badges; use existing shadcn/ui components |
| Real-time portfolio P&L updates | Combining WebSocket prices with portfolio recalculation adds latency and complexity | Update portfolio P&L on page load using latest daily_prices; WebSocket feeds chart only |
| Multi-exchange simultaneous AI analysis | Running AI on 1700 tickers at 15 RPM free tier = 113 minutes of Gemini calls | Analyze only HOSE + watchlisted HNX/UPCOM tickers daily; full HNX/UPCOM analysis weekly or on-demand |
| Automatic rights issue exercise recording | Auto-recording buys for exercised rights requires knowing user intent | Show rights issue alert with "exercise" button that pre-fills /buy command with subscription price |
| Portfolio value snapshot table | Storing daily snapshots of portfolio value is wasteful for single user with <20 holdings | Compute on-the-fly: for each date, recalculate total value from trades + daily_prices |
| Trade edit for any historical trade | Editing a BUY that has been partially sold via FIFO breaks the entire P&L chain | Only allow editing most recent trade, or unconsumed BUY trades. For older trades: delete + re-enter |

---

## Detailed Feature Specifications

### MKT-01: Multi-Market Crawling (HNX/UPCOM)

**How it works in existing codebase:**
- `VnstockCrawler.fetch_listing(exchange)` already accepts exchange param
- `_EXCHANGE_MAP = {"HOSE": "HSX", "HNX": "HNX", "UPCOM": "UPCOM"}` already defined in `vnstock_crawler.py`
- `Quote(symbol)` fetches OHLCV for any symbol regardless of exchange — VCI is exchange-agnostic
- `Ticker.exchange` column exists with `server_default="HOSE"`
- `Listing().symbols_by_exchange()` returns ALL exchanges in one API call (VCI: `/price/symbols/getAll`)
- VCI const `_GROUP_CODE` includes 'HOSE', 'HNX', 'UPCOM' (verified in vnstock source)

**HNX vs HOSE vs UPCOM differences:**
- HNX: ~380 stocks, smaller market cap, different tick sizes (100-500 VND steps), same trading hours (9:00-14:30)
- UPCOM: ~900 stocks, unlisted/registration trading, lower liquidity, same hours
- VCI data source treats all identically — same REST API, same OHLCV format, same response schema
- Corporate events via VNDirect API also cover HNX/UPCOM (same endpoint, filter by ticker code)
- Indicators + AI analysis use same formulas regardless of exchange

**Scale impact:**
- Current: ~400 HOSE tickers × 3.5s delay = ~23 min daily crawl
- After: ~1700 tickers × 3.5s delay = ~99 min daily crawl
- Mitigation: batch by exchange, run HNX/UPCOM crawl at different time slot, or parallelize
- AI analysis: 1700 × 4 types = 6800 analyses at 15 RPM → 7.5 hours. **MUST use selective approach**: full AI for HOSE + watchlisted HNX/UPCOM only; rest weekly or on-demand
- Gemini free tier: 1500 requests/day → 375 tickers × 4 types = limit. Need tiered analysis strategy.

**Implementation approach:**
1. Modify `weekly_ticker_refresh` to fetch all 3 exchanges (already structurally supported)
2. Daily crawl: loop through all active tickers (VCI Quote is exchange-agnostic)
3. Dashboard: add `?exchange=HOSE|HNX|UPCOM` param to `/tickers/` and `/tickers/market-overview`
4. Frontend: tab bar (Tất cả / HOSE / HNX / UPCOM) on market overview and heatmap
5. Heatmap: color grouping by exchange in addition to sector

**Dependencies:** None — builds on existing infrastructure.

### RT-01/RT-02: WebSocket Real-Time Price Streaming

**VN market data landscape (verified via vnstock 3.5.1 source):**
- vnstock `Quote.history(interval='1m')` — REST polling for 1-minute candles via VCI REST API
- No public free WebSocket for VN market price streaming exists
- SSI Fast Connect API has WebSocket but requires broker account + API key registration
- TCBS has similar broker-only restrictions
- VCI (Vietcap) REST API supports intervals: 1m, 5m, 15m, 30m, 1H, 1D, 1W, 1M (verified from `_TIMEFRAME_MAP` in vnstock const.py)

**Recommended architecture:**
```
Backend: APScheduler IntervalTrigger (30s during 9:00-14:30 ICT weekdays)
  → vnstock Quote.history(interval='1m', count_back=1) for subscribed tickers
  → Push to connected WebSocket clients via FastAPI WebSocket

Frontend: WebSocket client → update lightweight-charts in real-time
  → Only subscribe to currently-viewed ticker + watchlist
```

**Key design decisions:**
- Poll only during VN market hours: Mon-Fri, 9:00-11:30 (morning session) and 13:00-14:30 (afternoon session)
- Poll only for actively-viewed/subscribed tickers (max 10-20 at a time, not all 1700)
- Use `asyncio.to_thread()` wrapper (same pattern as existing `vnstock_crawler.py`)
- Store intraday quotes in memory only (or lightweight `intraday_prices` table), don't pollute `daily_prices`
- Degrade gracefully: if VCI poll fails, client shows last known price with "stale" indicator
- FastAPI native WebSocket support — no additional library needed

**Rate limiting concern:**
- VCI free tier: 20 req/min (vnstock guest), 60 req/min (with API key)
- Polling 10 tickers at 30s = 20 req/min → at the free tier limit
- Mitigation: register free vnstock API key (60 RPM), or batch ticker queries if VCI supports it
- Alternative: poll only the single ticker being viewed on chart + top-5 watchlist

**Frontend integration with lightweight-charts:**
- `candleSeries.update(barData)` — updates last candle in real-time without full re-render
- Need WebSocket message format: `{ symbol, time, open, high, low, close, volume }`
- Reconnect logic: exponential backoff on disconnect, auto-resubscribe

**Dependencies:** MKT-01 (tickers from all exchanges must be crawlable).

### PORT-08: Dividend Income Tracking

**How it works in stock platforms:**
1. At record_date, check which lots are held for each ticker
2. Compute: `dividend_income = shares_held × dividend_amount_per_share`
3. Track as income (not a trade), separate from capital gains
4. Show in portfolio: total dividend income, per-ticker income history

**Existing infrastructure:**
- `CorporateEvent` has `event_type='CASH_DIVIDEND'`, `dividend_amount` (VND/share), `record_date`
- `Lot` has `remaining_quantity`, `ticker_id`, `buy_date`
- Need: cross-reference at each CASH_DIVIDEND record_date → sum(remaining_qty) for that ticker → income

**Implementation approach:**
1. New `DividendIncome` model: `id, ticker_id, corporate_event_id, shares_held, amount_per_share, total_income, record_date, created_at`
2. Scheduled job (after corporate event crawl): for each new CASH_DIVIDEND event where record_date ≤ today, check Lots held at that date, compute income
3. API: `GET /portfolio/dividends` — list all dividend income records
4. Portfolio summary: add `total_dividend_income` to `get_summary()` response
5. Telegram: include dividend income in daily P&L notification when applicable

**Held shares at record_date calculation:**
```python
# Must compute historical holdings, not current
# At record_date R, shares_held = SUM of lots WHERE buy_date <= R AND
#   (lot is still open OR was sold after R)
# Simplified: SUM(lot.quantity) WHERE buy_date <= R
#   MINUS SUM(consumed shares from sells WHERE sell_date <= R)
```

**Edge cases:**
- Record_date vs Ex-date: Entitlement determined by record_date (must hold on or before). CorporateEvent has both.
- Backdated trades: If user enters a BUY trade dated before a past record_date, need to recompute dividends
- Stock dividends: Not cash income, but increases share count — affects lot tracking. **Defer stock dividend lot adjustment to v3** (complex FIFO impact).

**Dependencies:** Corporate events (CORP-01..05), portfolio lots (PORT-01..07).

### PORT-09: Portfolio Performance Chart

**How it works:**
1. For each trading day, compute total portfolio value = sum(shares_held × close_price) for all tickers
2. Plot as line chart over time
3. Optional overlay: VN-Index benchmark for comparison

**On-the-fly computation (recommended over snapshot table):**
```sql
-- Approach: for each date in range, compute portfolio value
-- Step 1: Get all lots and their effective date ranges
-- Step 2: For each date, join lots held at that date with daily_prices
-- Step 3: SUM(lots.remaining_qty_at_date × daily_prices.close)
```

**Simplified computation for personal use (<20 holdings):**
- Start from first trade date
- For each subsequent trading day with price data:
  - Replay all trades up to that date to determine lots held
  - Multiply each lot's remaining_qty × that day's close price
  - Sum = portfolio value for that date
- Cache result for API response (recompute on trade change)
- Limit to last N months for chart (default: 6 months, max 2 years)

**Frontend:**
- recharts `LineChart` with `ResponsiveContainer` (already in use on dashboard)
- Add realized P&L cumulative line as secondary axis (optional)
- Time range selector reusing same pattern as candlestick chart (1T/3T/6T/1N/2N)

**Dependencies:** Portfolio trades (PORT-01..07), daily prices (DATA-01).

### PORT-10: Portfolio Allocation Pie Chart

**Already proven in codebase:**
- Dashboard `page.tsx` uses recharts `PieChart` for market gainers/losers distribution (lines 240-274)
- `get_holdings()` already returns per-ticker `market_value`
- Ticker model has `sector` field

**Two views:**
1. **By ticker:** Each holding as a slice, sized by market_value
2. **By sector:** Aggregate market_value by `tickers.sector`

**Implementation:**
- Backend: `get_holdings()` already returns per-ticker `market_value`; add `sector` to response (join Ticker)
- Frontend: Reuse existing PieChart pattern, add toggle "Theo mã" / "Theo ngành"
- Colors: assign consistent colors per ticker/sector

**Dependencies:** Portfolio holdings (PORT-02). Complexity: **LOW**.

### PORT-11: Trade Edit/Delete

**FIFO complexity analysis:**

A BUY creates a Lot. A SELL consumes lots FIFO via `_consume_lots_fifo()`. Editing/deleting a BUY that has been partially consumed breaks the chain.

**Safe operations matrix:**
| Operation | Condition | FIFO Impact | Allowed |
|-----------|-----------|-------------|---------|
| Edit latest BUY (unconsumed) | `Lot.remaining_quantity == Lot.quantity` | Update Trade + Lot fields | ✅ Simple |
| Edit latest SELL | No subsequent trades for that ticker | Reverse lot consumption, re-consume with new qty/price | ✅ Medium |
| Delete latest BUY (unconsumed) | `Lot.remaining_quantity == Lot.quantity` | Delete Trade + Lot | ✅ Simple |
| Delete latest SELL | No subsequent trades for that ticker | Reverse lot consumption, delete Trade | ✅ Medium |
| Edit/delete arbitrary historical trade | Other trades depend on it | **FULL RECALCULATION** required | ⚠️ Complex |

**Recommended approach (v2.0):**
1. **Validation first:** Check if trade has been consumed by subsequent sells
2. **Simple path:** Allow edit/delete of unconsumed BUY trades OR the most recent trade per ticker
3. **Full recalculation path (for any trade):**
   - Delete all lots for ticker
   - Replay all trades chronologically
   - Rebuild FIFO chain from scratch
   - Recompute all realized P&L
4. **Confirmation on destructive operations:** "Sửa giao dịch này sẽ tính lại toàn bộ P&L. Tiếp tục?"

**API design:**
- `PUT /portfolio/trades/{id}` — edit trade (body: partial update fields)
- `DELETE /portfolio/trades/{id}` — delete trade
- Both trigger validation → recalculation → return updated portfolio state

**Dependencies:** Portfolio core (PORT-01..07).

### PORT-12: Broker CSV Import

**VN broker CSV format landscape (MEDIUM confidence — should verify with actual exports):**

| Broker | Date Format | Side Labels | Headers | Separator | Encoding | Market Share |
|--------|-------------|-------------|---------|-----------|----------|-------------|
| SSI | DD/MM/YYYY | Mua / Bán | Vietnamese | Comma | UTF-8-BOM | ~15% |
| VNDirect | DD/MM/YYYY | Mua / Bán | Vietnamese | Comma | UTF-8 | ~12% |
| TCBS | YYYY-MM-DD | BUY / SELL | English | Comma | UTF-8 | ~10% |
| VCBS | DD/MM/YYYY | Mua / Bán | Vietnamese | Comma | Windows-1252 | ~8% |

**Common fields across all formats:**
- Trade date (required) — various date formats
- Ticker symbol (required) — always uppercase 3-letter code
- Buy/Sell side (required) — "Mua"/"Bán" or "BUY"/"SELL"
- Quantity (required) — integer
- Price (required) — VND, may have thousand separators (e.g., "82,000" or "82000")
- Fees/Commission (optional) — may be split into broker fee + tax

**Implementation approach:**
1. **Per-broker parsers** for SSI, VNDirect, TCBS, VCBS (top 4)
2. **Generic CSV parser** with user-specified column mapping (dropdown selectors) for other brokers
3. **Preview step:** Parse → show table of detected trades → user confirms before committing
4. **Validation:** Check ticker exists in DB, date is reasonable, qty > 0, price > 0
5. **Batch processing:** Replay imported trades chronologically through `PortfolioService.record_trade()`

**File upload flow:**
```
Frontend: File picker → select broker format → POST /portfolio/import/preview
  → Returns parsed trades as JSON → User reviews table → POST /portfolio/import/confirm
  → Backend: sort by date → record_trade() for each → return results summary
```

**Error handling:**
- Show per-row validation errors in preview
- Allow user to fix/skip invalid rows
- Rollback entire batch on critical failure (database transaction)

**Dependencies:** Portfolio core (PORT-01..07), ticker database (DATA-01).

### HEALTH-08: Gemini API Usage Tracking

**Gemini API response structure (HIGH confidence — from google-genai SDK):**
```python
response.usage_metadata.prompt_token_count      # Input tokens
response.usage_metadata.candidates_token_count   # Output tokens
response.usage_metadata.total_token_count        # Total
```

**Free tier limits (gemini-2.5-flash-lite, per PROJECT.md):**
- 15 requests per minute (RPM)
- 1,000,000 tokens per minute (TPM)
- 1,500 requests per day (RPD)
- Note: Limits may change — v2.0 must handle this gracefully

**Implementation:**
1. New `GeminiUsage` model: `id, timestamp, job_id, ticker_symbol, analysis_type, prompt_tokens, completion_tokens, total_tokens, model, created_at`
2. Intercept in `ai_analysis_service.py`: after each Gemini call, extract `usage_metadata` and log
3. API: `GET /health/gemini-usage?period=day|week|month` — aggregated usage stats
4. Dashboard card: requests today / RPD limit, tokens today / TPM budget, bar chart of daily usage
5. Warning threshold: alert when approaching 80% of daily request limit → triggers HEALTH-10 Telegram alert

**With 1700 tickers (post MKT-01), budget management becomes CRITICAL:**
- 1500 RPD ÷ 4 analysis types = 375 tickers/day at full analysis
- Strategy: prioritize HOSE (400) > watchlisted HNX/UPCOM > rest weekly
- Track and display remaining daily budget on health dashboard

**Dependencies:** AI analysis service (AI-01..13).

### HEALTH-09: Pipeline Execution Timeline (Gantt)

**Existing data that enables this:**
- `job_executions` table: `job_id, started_at, completed_at, status` (per `job_execution.py`)
- Job chain logged by `scheduler/manager.py`: price_crawl → indicators → AI → news → sentiment → combined → signals
- Each step already logged with precise start/end timestamps
- Parallel branches also logged: price_alerts, corporate_action_check

**Visualization concept:**
```
14:30 ───────────────────────────────────── 16:00
 │ daily_price_crawl    ████████████░░░░░░░░░ │
 │ corporate_action     ░░░░██░░░░░░░░░░░░░░░ │
 │ price_alerts         ░░░░█░░░░░░░░░░░░░░░░ │
 │ indicators           ░░░░░░░░░░░██░░░░░░░░ │
 │ ai_analysis          ░░░░░░░░░░░░░████████ │
 │ news_crawl           ░░░░░░░░░░░░░░░░░░██░ │
 │ sentiment            ░░░░░░░░░░░░░░░░░░░██ │
 │ combined             ░░░░░░░░░░░░░░░░░░░░█ │
 │ signal_alerts        ░░░░░░░░░░░░░░░░░░░░█ │
```

**Implementation:**
- API: `GET /health/pipeline-timeline?date=YYYY-MM-DD` — returns all job_executions for that date
- Frontend: Custom SVG component or CSS grid with absolute positioning
  - Each job = horizontal bar, x-position = (started_at - min_start), width = duration
  - Color by status: green = success, yellow = partial, red = failed
  - Tooltip: job name, duration, result_summary preview
- Date picker to navigate between days

**No Gantt library needed** — 8-10 bars with simple horizontal layout. CSS + relative positioning is sufficient. recharts `BarChart` could work but custom SVG gives more control.

**Dependencies:** Job execution logging (ERR-04).

### HEALTH-10: Telegram Health Notifications

**Current state:** Only ERR-05 exists (EVENT_JOB_ERROR → Telegram alert on complete job failure).

**Expanded health checks:**
| Check | Condition | Alert Message |
|-------|-----------|---------------|
| Stale data | Any data source >48h stale on trading day | "⚠️ Dữ liệu {source} chưa cập nhật >48h" |
| High error rate | >50% failure rate for any job in last 24h | "🔴 Job {name}: {pct}% thất bại trong 24h qua" |
| DB pool exhaustion | checked_out >= pool_size | "⚠️ DB pool bão hòa: {checked_out}/{pool_size}" |
| Gemini quota warning | >80% daily request limit | "⚠️ Gemini API: đã dùng {used}/{limit} requests" |
| Pipeline stall | Job chain hasn't completed by 17:00 on trading day | "🔴 Pipeline chưa hoàn thành lúc 17:00" |

**Implementation:**
1. New scheduled job: `health_check` running every 30 min during market hours (9:00-17:00 Mon-Fri)
2. Queries existing `HealthService` methods: `get_data_freshness()`, `get_error_rates()`, `get_job_statuses()`
3. Also queries new `GeminiUsage` service for quota check
4. Sends Telegram alert only on state CHANGE (debounce — not every check cycle)
5. Track last alert state in-memory dict `{ check_name: last_alert_status }` to prevent alert fatigue
6. Uses existing `telegram_bot.send_message()` pattern (2-retry, never-raises)

**Dependencies:** Health service (HEALTH-01..07), Telegram bot (BOT-01).

### CORP-06: Rights Issue Tracking

**VN market rights issues (quyền mua cổ phiếu):**
- Company issues new shares to existing shareholders at below-market subscription price
- Ratio: e.g., 5:1 means 1 new share per 5 existing shares
- Record date determines eligibility; subscription period typically 2-4 weeks
- Dilution: share count increases → EPS decreases → price typically drops on ex-date
- User must DECIDE whether to exercise (buy new shares at subscription price) or let rights lapse

**VNDirect API verification needed (MEDIUM confidence):**
- Current crawl types: `DIVIDEND, STOCKDIV, KINDDIV` (in `corporate_event_crawler.py`)
- Rights issues may be type `RIGHTS` or `STOCKRIGHTS` in VNDirect API — needs live verification
- If VNDirect doesn't expose, fallback: CafeF scraping for rights issue announcements

**Model extension needed:**
```python
# Add to CorporateEvent or new RightsIssue model
event_type: "RIGHTS_ISSUE"  # New enum value
ratio: Decimal              # new shares per 100 existing (same format as STOCK_DIVIDEND)
subscription_price: Decimal # price to exercise rights (NEW FIELD on CorporateEvent)
subscription_deadline: date # last date to exercise (NEW FIELD on CorporateEvent)
```

**Dilution calculation:**
```
dilution_pct = ratio / (100 + ratio) × 100
# e.g., 20:100 → 20/120 = 16.7% dilution

theoretical_ex_rights_price = (old_price × 100 + subscription_price × ratio) / (100 + ratio)
```

**Price adjustment factor:**
```
factor = (100 × old_price + ratio × subscription_price) / ((100 + ratio) × old_price)
# Only applied if user does NOT exercise (dilution without compensation)
# If user exercises, they buy new shares at subscription_price → no adjustment needed
```

**User interaction flow (alert-driven, NOT automatic):**
1. Crawl rights issue events → store in corporate_events
2. Alert held positions via Telegram: "🔔 {TICKER} phát hành quyền mua: {ratio}:100, giá {subscription_price}, hạn {deadline}"
3. If user exercises: manual `/buy {ticker} {qty} {subscription_price}` with fees=0
4. If user does NOT exercise: rights lapse, price adjustment applied

**Dependencies:** Corporate event crawling (CORP-02), portfolio lots (PORT-01).

### CORP-07: Ex-Date Telegram Alerts

**How it works:**
1. Daily scheduled job (run after corporate event crawl completes, part of job chain)
2. Query: upcoming ex-dates in next 7 days for tickers with open positions
3. Format alert with event details + expected income/impact
4. Send once per event (track sent alerts to avoid duplicates)

**Alert format:**
```
📅 Sự kiện sắp tới cho danh mục:

VNM — Cổ tức tiền mặt 1,500 VND/cp
  Ex-date: 2026-04-20 (còn 3 ngày)
  Bạn đang nắm: 200 cổ phiếu
  Dự kiến nhận: 300,000 VND

HPG — Cổ tức cổ phiếu 10:100
  Ex-date: 2026-04-22 (còn 5 ngày)
  Bạn đang nắm: 500 cổ phiếu
  Dự kiến nhận thêm: 50 cổ phiếu
```

**Implementation:**
1. Track sent alerts: new `sent_event_alert` flag on `CorporateEvent` or separate tracking table
2. Query: `corporate_events WHERE ex_date BETWEEN today AND today+7 AND ticker_id IN (SELECT DISTINCT ticker_id FROM lots WHERE remaining_quantity > 0)`
3. Cross-reference with lots to compute expected income/shares
4. Send via existing `telegram_bot.send_message()` pattern
5. Run as new chain step after `daily_corporate_action_check_triggered`

**Dependencies:** Corporate events (CORP-01..05), portfolio lots (PORT-01), Telegram bot (BOT-01).

### CORP-08: Event Calendar View

**Design decisions:**
- Simple list view grouped by week — NOT a heavy FullCalendar widget (anti-feature)
- Filter: Tất cả / Đang nắm giữ / By exchange / By event type
- Each event row: ticker symbol, event type badge, ex-date, record_date, amount/ratio
- Highlight events for held positions (bold or colored border)

**API:**
```
GET /corporate-events/calendar?from=2026-04-01&to=2026-04-30&held_only=false&exchange=HOSE
```
Returns events grouped by ISO week, with `is_held` flag for portfolio cross-reference.

**Frontend:**
- Use existing Card/Table shadcn components
- Group by week with date section headers
- Badge colors by event type: 🟢 cash dividend, 🔵 stock dividend, 🟠 rights issue, ⚪ bonus shares
- Toggle: "Chỉ mã đang nắm" checkbox filter

**Dependencies:** Corporate events (CORP-01..05).

### CORP-09: Adjusted vs Raw Price Toggle

**Current state (verified in codebase):**
- `DailyPrice` model has both `close` (raw) and `adjusted_close` (adjusted after corporate actions)
- Frontend `lib/api.ts` `PriceData` interface: `date, open, high, low, close, volume` — NO adjusted_close
- `CandlestickChart` component uses `d.close` exclusively for rendering
- `CorporateActionService.adjust_all_tickers()` already populates `adjusted_close`

**Implementation:**
1. **API change:** Add `?adjusted=true` query param to `/tickers/{symbol}/prices`
   - When `adjusted=true`, return adjusted OHLC (compute proportionally from close/adjusted_close ratio)
   - When `adjusted=false` (default), return raw OHLC as today
2. **Adjusted OHLC computation:**
   ```python
   if adjusted and adjusted_close and close:
       ratio = adjusted_close / close
       return {open: open*ratio, high: high*ratio, low: low*ratio, close: adjusted_close}
   ```
3. **Frontend:** Toggle button in CandlestickChart header: "Giá gốc" / "Giá điều chỉnh"
4. Pass `adjusted` param to `fetchPrices()` call
5. lightweight-charts: just `candleSeries.setData()` with new data (same pattern as time range change)

**Dependencies:** Corporate action adjustment (CORP-01..05), candlestick chart (DASH-01). Complexity: **LOW**.

---

## Feature Dependencies

```
MKT-01 (Multi-market crawl) → MKT-02 (Exchange filter UI)
MKT-01 → RT-01/RT-02 (WebSocket needs multi-exchange tickers)

PORT-01..07 (Existing portfolio) → PORT-08 (Dividend tracking)
PORT-01..07 → PORT-09 (Performance chart)
PORT-01..07 → PORT-10 (Allocation chart)
PORT-01..07 → PORT-11 (Trade edit/delete)
PORT-01..07 → PORT-12 (CSV import uses record_trade)
PORT-08 → CORP-07 (Ex-date alerts compute expected dividend income)

CORP-01..05 (Existing corp actions) → CORP-06 (Rights issues)
CORP-01..05 → CORP-07 (Ex-date alerts)
CORP-01..05 → CORP-08 (Event calendar)
CORP-01..05 → CORP-09 (Adjusted price toggle)

ERR-04 (Job execution logging) → HEALTH-09 (Pipeline timeline)
AI-01..13 (Existing AI) → HEALTH-08 (Gemini usage tracking)
HEALTH-01..07 (Existing health) → HEALTH-10 (Telegram health alerts)
HEALTH-08 → HEALTH-10 (Gemini quota check in health alerts)
```

### Critical Path

1. **MKT-01 first** — Expanding ticker universe is foundational; WebSocket and AI scaling depend on it
2. **Portfolio enhancements (PORT-08..12) after MKT-01** — Need all tickers for CSV import; dividend tracking needs corp events for all exchanges
3. **Health enhancements (HEALTH-08..10) alongside or after portfolio** — Gemini usage tracking becomes critical when ticker count triples
4. **Corp action enhancements (CORP-06..09) can be parallel** — Independent of multi-market, depend only on existing v1.1 corp action infrastructure
5. **WebSocket (RT-01/02) last** — Highest complexity, most infrastructure change, lowest dependency on other v2.0 features

---

## Scale & Capacity Concerns

| Concern | Current (v1.x) | After v2.0 | Mitigation |
|---------|-----------------|------------|------------|
| Ticker count | ~400 (HOSE only) | ~1700 (all exchanges) | Selective AI analysis; batch crawl by exchange |
| Daily crawl time | ~23 min | ~99 min | Split into exchange-specific jobs; start earlier (14:45) |
| Gemini API calls/day | ~1600 (400×4) | ~6800 if all tickers | HOSE full + watchlisted HNX/UPCOM only = ~1500/day |
| DB pool pressure | Low (pool_size=5) | Higher (WebSocket + more jobs) | Consider pool_size=8, monitor via HEALTH-10 |
| WebSocket connections | 0 | 1 (single user) | Minimal concern; manage lifecycle properly |
| daily_prices growth | ~400 rows/day | ~1700 rows/day | Yearly partitioning already in place ✓ |
| Pipeline total time | ~30 min | ~2+ hours | Parallel branches where possible; tiered analysis |

---

## MVP Recommendation

**Prioritize:**
1. MKT-01 + MKT-02 (Multi-market) — Foundation for all else
2. CORP-09 (Adjusted/raw toggle) — Trivial, immediate value
3. PORT-11 (Trade edit/delete) — Reduces friction
4. PORT-10 (Allocation chart) — Low complexity, reuses existing PieChart
5. HEALTH-10 (Telegram health alerts) — Quick, high operational value

**Then:**
6. PORT-08 (Dividend income) — Medium complexity, high value
7. PORT-09 (Performance chart) — Medium complexity, most requested
8. HEALTH-08 (Gemini usage) — Critical with 3x ticker count
9. CORP-07 (Ex-date alerts) — Connects corp events to portfolio

**Then:**
10. PORT-12 (CSV import) — High utility but needs broker format verification
11. CORP-06 (Rights issues) — Needs VNDirect API verification
12. CORP-08 (Event calendar) — Pure frontend, lower priority
13. HEALTH-09 (Pipeline timeline) — Nice-to-have visualization

**Last (highest complexity):**
14. RT-01 + RT-02 (WebSocket) — Build after everything else is stable

**Defer to v3:**
- Stock dividend lot adjustment (STOCK_DIVIDEND increasing lot share count)
- Historical WebSocket data replay
- More than 4 broker CSV formats
- VN-Index benchmark overlay on performance chart

---

## Sources

| Finding | Source | Confidence |
|---------|--------|------------|
| vnstock supports all exchanges (HOSE/HNX/UPCOM) via same VCI API | Inspected `vnstock.explorer.vci.listing.py` and `const.py` `_GROUP_CODE` | HIGH |
| `_EXCHANGE_MAP` already defined in `vnstock_crawler.py` for all 3 exchanges | Direct codebase inspection | HIGH |
| VCI Quote works exchange-agnostically (any symbol, any exchange) | Inspected `vnstock.explorer.vci.quote.py` — validates symbol, not exchange | HIGH |
| VCI supports 1-minute intervals for intraday data | Verified `_TIMEFRAME_MAP` in vnstock const.py: includes '1m', '5m', '15m', '30m' | HIGH |
| No free public WebSocket for VN stock market | Inspected vnstock source — only REST API; SSI/TCBS require broker auth | HIGH |
| Ticker model already has `exchange` column with server_default "HOSE" | Direct inspection of `models/ticker.py` line 20 | HIGH |
| DailyPrice has both `close` and `adjusted_close` columns | Direct inspection of `models/daily_price.py` lines 28-32 | HIGH |
| CorporateEvent has `record_date`, `ex_date`, `dividend_amount`, `ratio` | Direct inspection of `models/corporate_event.py` | HIGH |
| Frontend uses recharts PieChart (already in dashboard for market stats) | Inspected `dashboard/page.tsx` lines 240-274 and `package.json` | HIGH |
| Frontend uses lightweight-charts for candlestick (supports real-time update) | Inspected `candlestick-chart.tsx` | HIGH |
| Job chain: price_crawl → indicators → AI → news → sentiment → combined → signals | Inspected `scheduler/manager.py` _on_job_executed() | HIGH |
| job_executions table has started_at, completed_at, status, result_summary | Inspected `models/job_execution.py` | HIGH |
| Gemini response.usage_metadata has prompt/completion/total token counts | google-genai SDK documentation | HIGH |
| Gemini free tier: 15 RPM, 1500 RPD | google-genai SDK / AI Studio docs | MEDIUM |
| VN broker CSV formats (SSI, VNDirect, TCBS, VCBS) | Domain knowledge of VN brokerage export patterns | MEDIUM — verify with actual exports |
| VNDirect API rights issue type availability | Inferred from existing event types — needs live verification | LOW |
