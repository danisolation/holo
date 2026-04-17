# Domain Pitfalls: Holo v2.0

**Domain:** Expanding VN stock intelligence platform — multi-market, real-time, portfolio & health enhancements
**Researched:** 2025-07-18
**Confidence:** HIGH (grounded in actual codebase analysis of 9,400+ LOC, database schema, and scheduler architecture)

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or system-wide failures.

---

### Pitfall 1: 3.75× Ticker Expansion Exhausts Crawl Pipeline Window and Starves DB Pool

**What goes wrong:**
Adding HNX (~370 stocks) and UPCOM (~900+ stocks) to HOSE (400) grows the ticker universe from 400 to ~1,500+. The current daily price crawl (`price_service.py:_crawl_batch`) processes tickers sequentially with a `crawl_delay_seconds=3.5s` gap. At 400 tickers, this takes ~23 minutes. At 1,500 tickers, it takes **~87 minutes** — nearly 1.5 hours just for OHLCV. The chained pipeline (indicators → AI → news → sentiment → combined → signals) multiplies this further. The pipeline starts at 15:30 and the daily summary sends at 16:00 — a 30-minute window that's already tight at 400 tickers. At 1,500, the pipeline won't finish before midnight.

Meanwhile, the database pool (`pool_size=5, max_overflow=3`) means max 8 connections. The crawl job holds a session for the entire batch duration (87+ minutes). Aiven's limit of ~20-25 connections means the combined load of crawl + indicator compute + AI analysis + API requests + Telegram bot + WebSocket connections (v2.0) will cause connection starvation.

**Why it happens:**
Developers treat multi-market as "just add more tickers to the same loop." They don't realize the O(n) crawl with rate limiting means linear time growth, and the chained pipeline is sequential.

**Consequences:**
- Daily summary at 16:00 contains stale data (pipeline not finished)
- API endpoints timeout waiting for DB connections during crawl window
- Aiven connection limit reached → `TooManyConnections` errors crash the entire app
- Circuit breaker trips on vnstock after consecutive failures, blocking ALL tickers

**Prevention:**
- **Split crawl jobs per exchange**: `daily_price_crawl_hose`, `daily_price_crawl_hnx`, `daily_price_crawl_upcom` — run them in parallel or stagger start times (15:15, 15:25, 15:35)
- **Reduce per-exchange scope**: HOSE top 400, HNX top 200, UPCOM top 200 — that's 800 total, not 1,500. UPCOM penny stocks don't need AI analysis
- **Per-exchange circuit breakers**: Currently `vnstock_breaker` is shared. One exchange's API failure shouldn't block others. Add `vnstock_hose_breaker`, `vnstock_hnx_breaker`, `vnstock_upcom_breaker`
- **Session-per-batch, not session-per-crawl**: The current pattern `async with async_session() as session:` in `daily_price_crawl()` holds one session for the entire run. Use shorter-lived sessions: one per batch of 50 tickers, committed and released
- **Push daily summary to 17:00 or later**: Give pipeline room to finish at 1,500 tickers
- **Consider raising pool_size to 7, max_overflow to 5** (total 12) if Aiven plan supports it

**Detection:**
- Daily summary contains analysis from yesterday (pipeline not finished in time)
- `pool.checkedout()` in health endpoint consistently at max
- Crawl job duration in `job_executions` suddenly 3-4× longer after HNX/UPCOM added
- `CircuitOpenError` in logs for vnstock during multi-exchange crawl

**Phase to address:** Multi-market coverage phase — must redesign crawl architecture BEFORE adding exchanges

---

### Pitfall 2: Trade Edit/Delete on Immutable FIFO Lots Corrupts Realized P&L

**What goes wrong:**
The current system treats trades as **append-only** — `record_trade()` creates trades and lots, `_consume_lots_fifo()` decrements `remaining_quantity` on sells. There's no `updated_at`, no soft delete, no edit history. Adding edit/delete means:

1. **Editing a BUY trade's price** requires updating `Lot.buy_price` AND recalculating every SELL trade's realized P&L that consumed from that lot
2. **Deleting a BUY trade** whose lot is partially consumed (e.g., bought 500, sold 300 — `remaining_quantity=200`) leaves orphaned sell P&L records and 300 shares of realized P&L based on a deleted trade
3. **Deleting a SELL trade** means restoring consumed lot quantities, but which lots? The FIFO consumption order isn't stored — `_consume_lots_fifo` modifies `remaining_quantity` in-place with no audit trail
4. **Editing a trade's date** changes FIFO ordering — a buy that was previously the oldest lot may become the second-oldest, changing which lot gets consumed by sells

**Why it happens:**
The existing `Trade` and `Lot` models were designed for immutable append-only operations. There's no `sell_allocations` join table recording "this sell consumed X shares from lot Y at cost Z." The consumption is implicit in the `remaining_quantity` field.

**Consequences:**
- Realized P&L becomes incorrect after editing/deleting a trade that participated in FIFO matching
- Portfolio summary `total_realized_pnl` doesn't match sum of individual trade P&Ls
- Selling all shares doesn't zero out position after editing buy quantities
- User trusts incorrect P&L numbers for tax/investment decisions

**Prevention:**
- **Add a `sell_allocations` table**: `{sell_trade_id, lot_id, quantity, realized_pnl}` — records exactly how each sell consumed lots. This is the audit trail needed for reversals.
- **Implement lot replay**: A `replay_lots(ticker_id)` function that wipes all lots and sell_allocations for a ticker, then replays all trades in chronological order, rebuilding FIFO state. Use this after any edit/delete.
- **Soft delete trades**: Add `deleted_at` column. Don't hard-delete — mark as deleted, then replay lots. Keep audit trail.
- **Block editing consumed trades by default**: If a BUY lot has been partially consumed, warn the user that editing will recompute all downstream P&L. Same for deleting.
- **Validate after replay**: After any edit/delete + replay, assert that `sum(lot.remaining_quantity * lot.buy_price) + sum(sell_allocations.realized_pnl) == sum(buy_trades) - sum(sell_trades.fees)`.

**Detection:**
- `total_realized_pnl` in portfolio summary changes unexpectedly after editing an old BUY trade
- `Lot.remaining_quantity` goes negative (should be impossible but happens without proper replay)
- Sum of all `Lot.remaining_quantity` for a ticker doesn't match `total_buys - total_sells`

**Phase to address:** Portfolio Enhancements phase — implement sell_allocations and replay BEFORE adding edit/delete

---

### Pitfall 3: WebSocket Real-Time Layer Without Message Broker Creates Memory Leaks and Event Loop Starvation

**What goes wrong:**
The current architecture is a single FastAPI process with APScheduler, Telegram long-polling, and synchronous vnstock calls wrapped in `asyncio.to_thread()`. Adding WebSocket price streaming means:

1. **Long-lived connections**: Each WebSocket client holds a connection open. Even with 1 user and 5 browser tabs, that's 5 persistent connections competing for the event loop
2. **No pub/sub mechanism**: Without Redis/message broker, price updates must be pushed to WebSocket clients via in-memory state. The "producer" (price crawler or polling loop) must directly manage connected client lists
3. **Event loop contention**: APScheduler jobs use `asyncio.to_thread()` for vnstock (sync) calls. These thread pool tasks, combined with WebSocket heartbeats, Telegram polling, and API requests, create event loop pressure
4. **No VN market WebSocket source**: vnstock doesn't provide streaming data. VCI/SSI don't offer public WebSocket APIs. "Real-time" must be implemented as frequent HTTP polling (every 10-30 seconds), which is NOT the same as WebSocket streaming
5. **DB pool exhaustion from polling**: If polling 1,500 tickers every 30 seconds, that's 50 DB writes per second (batched), consuming connections during market hours

**Why it happens:**
"Add WebSocket" sounds like a frontend feature. In reality it requires a fundamentally different data flow: producer → message channel → consumer. Without a message broker, the producer and consumer are tightly coupled in the same process.

**Consequences:**
- Memory growth as WebSocket connection state accumulates (no cleanup on disconnect)
- Event loop blocked by thread pool exhaustion → API endpoints become unresponsive
- Phantom "real-time" that's actually 10-30 second delayed polling dressed as WebSocket
- DB pool contention during market hours kills all other functionality

**Prevention:**
- **Accept the reality**: For a single-user app, "real-time" via WebSocket is overkill. A better approach: 30-second polling interval during market hours (9:00-11:30, 13:00-14:45 UTC+7) with React Query's `refetchInterval`, keeping the current HTTP architecture
- **If WebSocket is truly wanted**: Use FastAPI's built-in WebSocket support with a simple in-memory `ConnectionManager` class. One background task polls vnstock every 30s, stores to DB, then broadcasts to connected clients. Limit to top 50 tickers (watchlist only), not all 1,500
- **Separate market-hours polling from EOD pipeline**: Don't reuse the daily crawl job. Create a lightweight `market_hours_poller` that fetches only latest price (not full OHLCV history) for watchlist tickers
- **Set explicit thread pool size**: `asyncio.get_event_loop().set_default_executor(ThreadPoolExecutor(max_workers=4))` — bound the thread pool to prevent runaway
- **WebSocket heartbeat with timeout**: Disconnect clients that don't respond to pings within 30 seconds to prevent connection leaks

**Detection:**
- Process memory steadily increases during market hours
- API response times spike during market hours (9:00-14:45)
- `asyncio` warnings about slow callbacks or blocked event loop in logs
- Health endpoint shows all DB connections checked out during market hours

**Phase to address:** Real-Time phase — design the data flow architecture BEFORE implementing WebSocket endpoints

---

### Pitfall 4: Dividend Tracking on Existing Portfolio Requires Retroactive Record-Date Holdings Check

**What goes wrong:**
The v2.0 feature PORT-08 requires tracking dividend income on positions held at the record date. But the current portfolio system only tracks **current** holdings via `Lot.remaining_quantity > 0`. It doesn't know what you held on a specific past date because:

1. `Lot.remaining_quantity` is the **current** state — it gets decremented on every sell. There's no history of what it was on a given date
2. A user could have held 1,000 VNM on the record date (2025-03-15), sold 500 on 2025-03-20, and the current `remaining_quantity` is 500. But the dividend should be calculated on 1,000 shares
3. The `CorporateEvent` table has `record_date` but the portfolio has no mechanism to query "what was my position on date X?"
4. Cash dividends should NOT affect cost basis in FIFO (they're income, not capital return), but if incorrectly added as a "trade" they'll pollute the lot tracking

**Why it happens:**
Developers implement dividends as a new trade type (`DIVIDEND`) in the existing trades table, which creates a lot with `buy_price=0`. This corrupts FIFO ordering and average cost calculations.

**Consequences:**
- Dividend income calculated on current holdings instead of record-date holdings → incorrect amounts
- If dividends are modeled as trades, FIFO cost basis gets polluted (lots with buy_price=0 absorb sells)
- Total return % is wrong because dividend income isn't captured or is double-counted

**Prevention:**
- **Separate `dividend_payments` table**: `{id, ticker_id, corporate_event_id, shares_held, amount_per_share, total_amount, record_date, payment_date}` — NOT in the trades table
- **Point-in-time holdings query**: Build a function `get_holdings_at_date(ticker_id, date)` that replays trades up to that date to determine the position. Since trades are chronologically ordered and few in number (personal use), this is cheap to compute
- **Auto-detect dividends**: When daily corporate action check finds a new CASH_DIVIDEND event with `record_date <= today`, check holdings at record_date and auto-create a `dividend_payment` record. Alert user via Telegram
- **Don't modify cost basis**: Dividend payments are income, not cost reduction. Display separately in portfolio: "Total Return = Capital Gains + Dividend Income"

**Detection:**
- Dividend income shows 0 for a stock you held at record date but sold before today
- Average cost per share drops to nonsensical values (dividend "trade" with price=0 averaged in)
- Portfolio P&L summary doesn't match manual calculation

**Phase to address:** Portfolio Enhancements — build dividend_payments table and holdings-at-date function BEFORE dividend tracking logic

---

### Pitfall 5: Broker CSV Import Without Format Normalization Creates Duplicate and Ghost Trades

**What goes wrong:**
Vietnamese brokers (VPS, SSI, TCBS, VNDirect, MBS, DNSE) each export CSV/Excel in wildly different formats:

1. **Date formats**: `DD/MM/YYYY` (VPS), `YYYY-MM-DD` (SSI), `DD-MM-YYYY` (MBS), Excel serial dates
2. **Number formats**: `85,000` vs `85.000` vs `85000` (VND uses dot as thousands separator, comma as decimal — opposite of US)
3. **Column names**: Vietnamese headers (`Ngày GD`, `Mã CK`, `KL`, `Giá`) vary between brokers
4. **Side encoding**: `Mua`/`Bán`, `M`/`B`, `Buy`/`Sell`, `1`/`2`
5. **Fee inclusion**: Some CSVs include fees as separate rows, some embed fees in price, some omit fees entirely
6. **Symbol variations**: Some use `VNM`, some `VNM.HM`, some `VNM.VN`
7. **Dividend rows**: Some brokers include dividend receipts as transactions — these are NOT trades and must be filtered out
8. **Duplicate detection**: Importing the same CSV twice should not create duplicate trades, but without a dedup key (broker CSVs don't have unique transaction IDs), matching on `(symbol, date, side, quantity, price)` can fail if you made two identical trades on the same day

**Why it happens:**
Developers build an importer for their own broker, ship it, and then discover other broker formats are completely different. Or they skip duplicate detection assuming users won't import twice.

**Consequences:**
- Duplicated trades → doubled position → incorrect P&L
- Wrong date parsing (DD/MM vs MM/DD) → trades on wrong dates → FIFO order corrupted
- Dividend rows imported as BUY trades → phantom positions with price=0
- Symbol mismatch → `ValueError: Ticker 'VNM.HM' not found` on import

**Prevention:**
- **Start with ONE broker format**: Pick the broker used (likely VPS or SSI), build and test thoroughly. Add others later as separate parsers
- **Broker-specific parser pattern**: Each broker gets a parser class with `parse(file) → list[NormalizedTrade]`. The `NormalizedTrade` has: `symbol: str, side: BUY|SELL, quantity: int, price: Decimal, trade_date: date, fees: Decimal, source_row: int`
- **Symbol normalization**: Strip suffixes (`.HM`, `.VN`, `.HN`) before matching against `tickers.symbol`
- **Dry-run mode**: Parse CSV and show preview of trades to be imported WITHOUT saving. User confirms before commit
- **Dedup via import batches**: Create an `import_batches` table with `{id, filename, broker, imported_at, trade_count}`. Each trade gets `import_batch_id`. To "undo" an import, delete all trades from that batch (then replay lots)
- **VND number parsing**: Always strip dots AND commas, then parse as integer. VN stock prices are always whole numbers (VND, no decimals)
- **Reject rows that don't match known tickers**: Log them with row numbers for user review

**Detection:**
- Portfolio suddenly doubles after import (duplicate trades)
- Trades appear in January that should be in October (DD/MM vs MM/DD confusion)
- `Lot.remaining_quantity` goes negative after import (sell trades imported without corresponding buys)
- Import succeeds but 30% of rows silently skipped (unmatched symbols)

**Phase to address:** Portfolio Enhancements — build CSV import AFTER trade edit/delete (need undo capability for bad imports)

---

## Moderate Pitfalls

Mistakes that cause significant rework or degraded functionality.

---

### Pitfall 6: Rights Issue Tracking Requires Optional Exercise Modeling — Not Just Another Corporate Event

**What goes wrong:**
Rights issues are fundamentally different from dividends and stock splits:
- Splits/dividends are **automatic** — all shareholders get the adjustment
- Rights issues are **optional** — the shareholder CHOOSES whether to subscribe for new shares at a discount price
- The dilution impact depends on whether you exercise or not
- The cost basis of new shares from rights is the subscription price, NOT the market price

Developers add `RIGHTS_ISSUE` as another `event_type` in `CorporateEvent` and try to handle it like stock dividends. But without tracking whether the user exercised, the system can't correctly compute position size or cost basis.

**Why it happens:**
Corporate action code (`corporate_action_service.py`) uses a uniform `adjust_ticker()` pattern: fetch events → compute factors → adjust prices. Rights issues don't fit this pattern because the adjustment depends on user action.

**Prevention:**
- **Model rights issues with user interaction**: Add `exercised: bool | None` field to rights events. `None` = pending (within subscription period), `True` = exercised, `False` = lapsed
- **Auto-create BUY trade on exercise**: When user marks a rights issue as exercised, automatically create a BUY trade at the subscription price for the correct quantity
- **Price adjustment only if needed**: The reference price adjustment on ex-date happens regardless of individual exercise — this is a market-wide adjustment. But the user's position size only changes if they exercise
- **Show pending rights in portfolio view**: "You have rights to buy 200 VNM @ 50,000 VND (deadline: 2025-08-15)" — separate from regular holdings
- **For v2.0, keep it simple**: Track the event + auto-alert via Telegram. Let user manually `/buy` if they exercise. Don't automate the exercise modeling yet

**Detection:**
- Position size wrong after rights ex-date (applied dilution without exercise)
- Cost basis includes subscription price for unexercised rights
- Adjusted prices over-correct for rights issues (treating them like stock dividends)

**Phase to address:** Corporate Actions Enhancements — implement AFTER basic corporate actions are solid

---

### Pitfall 7: Adjusted/Raw Price Toggle Breaks Indicator Consistency on Chart

**What goes wrong:**
CORP-09 adds a toggle on the candlestick chart to switch between adjusted and raw prices. But the technical indicators (SMA, Bollinger, MACD, RSI) in the existing `technical_indicators` table were computed from a specific price series. If indicators were computed from `close` (raw), toggling the chart to show `adjusted_close` creates a visual mismatch: the candlesticks show adjusted prices but the SMA overlays show raw-price-based moving averages.

The existing chart (`candlestick-chart.tsx`) overlays SMA 20/50/200 and Bollinger Bands from `indicatorData`. These indicator values are fetched from the backend's `technical_indicators` table. There's no separate set of "adjusted indicators."

**Why it happens:**
The toggle is implemented as a frontend-only feature (swap `d.close` for `d.adjusted_close` in chart data), but nobody adjusts the indicator overlays to match.

**Consequences:**
- SMA lines don't align with candlestick bodies in adjusted mode (SMA computed from raw prices is higher/lower than adjusted candlesticks)
- Bollinger Bands appear to have false breakouts in adjusted mode
- User makes trading decisions based on visually inconsistent data

**Prevention:**
- **Option A (simple, recommended for v2.0)**: When toggling to adjusted prices, HIDE indicator overlays. Show a note: "Chỉ báo kỹ thuật chỉ hiển thị trên giá gốc" (Indicators only shown on raw prices). This is honest and avoids confusion
- **Option B (complex)**: Compute indicators from both raw and adjusted prices, store separately, and fetch the matching set based on toggle state. Doubles indicator storage and computation time — overkill for personal use
- **Option C (middle ground)**: Recompute indicators client-side from the adjusted price series using a lightweight JS library. SMA and Bollinger are simple enough to compute in the browser from the price array

**Detection:**
- SMA 200 line is 5-10% above candlestick high on tickers with recent splits (adjusted prices lower, SMA from raw prices higher)
- User reports "BB kênh quá rộng" (BB bands too wide) in adjusted mode

**Phase to address:** Corporate Actions Enhancements — define the toggle behavior BEFORE implementing the frontend switch

---

### Pitfall 8: Pipeline Timeline Visualization Requires Explicit Pipeline Run ID — Current Chaining Has No Concept of a "Run"

**What goes wrong:**
HEALTH-09 wants a Gantt-style pipeline timeline showing each step's duration. But the current job chaining (`manager.py:_on_job_executed`) is implicit — when `daily_price_crawl` finishes, it triggers `daily_indicator_compute` via `scheduler.add_job()`. Each job creates its own `job_executions` row independently. There's no shared `pipeline_run_id` linking them.

To build a timeline, you need to query: "Show me all jobs that ran as part of the pipeline triggered at 15:30 on 2025-07-18." Currently, you'd have to infer this from timestamps (find a price crawl that finished around X, then an indicator compute that started around X+1 second, etc.). This is fragile — manual triggers, retries, and overlapping runs make timestamp-based inference unreliable.

**Why it happens:**
The EVENT_JOB_EXECUTED chaining was designed for reliability (if price crawl succeeds, trigger indicators), not observability. Adding observability after the fact requires threading context through the chain.

**Prevention:**
- **Add `pipeline_run_id` to `job_executions`**: UUID generated at the start of the first job in a chain (daily_price_crawl). Passed through the chain via a context mechanism
- **Pass context via scheduler job kwargs**: When chaining, pass the pipeline_run_id: `scheduler.add_job(func, kwargs={"pipeline_run_id": run_id})`
- **Modify each job function signature**: Add optional `pipeline_run_id: str | None = None` parameter. If present, store it in the job_execution row
- **Frontend timeline**: Query `job_executions WHERE pipeline_run_id = X ORDER BY started_at`, render as horizontal bars on a time axis
- **Handle orphans**: Manual triggers don't have a pipeline_run_id — show them as standalone in the timeline

**Detection:**
- Timeline visualization shows disconnected bars with no relationship
- Cannot answer "how long did today's full pipeline take?" without manual timestamp math

**Phase to address:** Health Enhancements — add pipeline_run_id to schema BEFORE building the timeline UI

---

### Pitfall 9: Telegram Health Notifications Become Spam Without Dedup and Cooldown

**What goes wrong:**
HEALTH-10 adds Telegram notifications for health issues (stale data, failed jobs, degraded status). Combined with the existing ERR-05 (failure alerts), the bot can bombard the user:
- Daily crawl partial failure → ERR-05 alert
- Indicators fail (chained from partial crawl) → another alert
- AI analysis fails → another alert
- Health check detects stale data → health notification
- That's 4 messages within minutes about the same root cause

The existing `_on_job_error` in `manager.py` fires on every `EVENT_JOB_ERROR` with no dedup. Adding health notifications multiplies this.

**Why it happens:**
Each notification source (job failure, health check, pipeline status) is implemented independently without awareness of what other sources have already reported.

**Consequences:**
- User mutes the Telegram bot due to notification fatigue → misses real critical alerts
- Bot hits Telegram's rate limits (30 messages/second per chat, but sustained bursts trigger throttling)
- Same root cause generates 5+ messages

**Prevention:**
- **Notification cooldown**: Track last notification time per category. Don't send another `job_failure` notification within 30 minutes of the last one. Store in-memory dict: `{category: last_sent_time}`
- **Aggregate pipeline failures**: If price crawl partially fails AND downstream jobs fail, send ONE summary: "🔴 Pipeline 15:30: crawl partial (5 failed), indicators skipped, AI skipped" instead of 3 separate messages
- **Health notification schedule**: Don't trigger health notifications on every health check. Run a periodic (hourly) health summary check. Only send if status changed from healthy → degraded or degraded → critical
- **Priority levels**: CRITICAL (complete pipeline failure, all data stale) = always send. WARNING (partial failure) = max 1 per hour. INFO (recovered) = once when status returns to healthy
- **Add `/health` Telegram command**: Let user pull health status on-demand instead of pushing every issue

**Detection:**
- Telegram bot sends >5 messages in 10 minutes about different symptoms of the same problem
- User reports bot is "too noisy" and mutes it
- Telegram API returns 429 (rate limited) in bot logs

**Phase to address:** Health Enhancements — design notification aggregation BEFORE implementing individual notification triggers

---

### Pitfall 10: Gemini API Usage Tracking Must Intercept the SDK — Not Just Count Requests

**What goes wrong:**
HEALTH-08 wants to track Gemini API usage (tokens, requests) against free tier limits. But the Gemini free tier limits are:
- 15 RPM (requests per minute) — already managed via `gemini_delay_seconds=4.0`
- **1 million tokens per minute** and **1,500 requests per day** (for gemini-2.0-flash)
- Token usage varies per request (prompt size depends on number of tickers in batch, news article lengths, indicator data)

Simply counting requests isn't enough — you need actual token counts from Gemini's response metadata. The `google-genai` SDK returns `usage_metadata` on each response with `prompt_token_count`, `candidates_token_count`, and `total_token_count`.

Developers often build a counter that increments on each API call but doesn't capture actual token usage. The counter shows "142 requests today" but not "847,000 / 1,000,000 tokens used this minute."

**Why it happens:**
Token tracking requires intercepting the response object at the point of API call, not just counting function invocations.

**Prevention:**
- **Wrap Gemini calls with usage extraction**: In `ai_analysis_service.py`, after each `client.models.generate_content()` call, extract `response.usage_metadata` and log/store token counts
- **Create `gemini_usage_log` table**: `{id, timestamp, request_type (technical/fundamental/sentiment/combined), prompt_tokens, completion_tokens, total_tokens, model}`
- **Aggregate in health endpoint**: Sum tokens in current minute (RPM check), sum requests today (daily limit check), show as percentage of limit
- **Alert when approaching limit**: At 80% of daily request limit, send Telegram warning. At 90%, switch to reduced-scope analysis (skip UPCOM tickers)
- **Don't track in real-time for dashboard**: The health dashboard can query the usage_log table on page load. No need for live WebSocket updates of API usage

**Detection:**
- Usage tracker shows "150 requests" but Gemini returns 429 (actual usage higher due to retries not counted)
- Token usage spikes after adding HNX/UPCOM tickers (more tickers per batch = more prompt tokens)

**Phase to address:** Health Enhancements — add usage extraction to Gemini service BEFORE building the dashboard widget

---

## Minor Pitfalls

Issues that cause friction, bugs, or technical debt but don't require rewrites.

---

### Pitfall 11: Exchange Filter on Dashboard Requires Backend Changes — Not Just Frontend Filtering

**What goes wrong:**
MKT-02 adds exchange filter to the dashboard. The current `tickers.py:list_tickers` endpoint has sector filtering but no exchange filtering. The current `tickers.py:market_overview` endpoint returns all active tickers with no exchange filter. The frontend `ticker-search.tsx` searches all tickers.

Developers implement exchange filtering purely on the frontend: fetch all 1,500 tickers, filter in JavaScript. At 1,500 tickers, the `market-overview` endpoint (which uses a window function over `daily_prices`) becomes slow — the `ROW_NUMBER() OVER (PARTITION BY ticker_id ORDER BY date DESC)` subquery scans all 1,500 tickers' prices.

**Prevention:**
- Add `exchange: str | None = Query(None)` parameter to `/tickers/` and `/tickers/market-overview` endpoints
- Filter in SQL: `WHERE tickers.exchange = :exchange` — let PostgreSQL optimize the join
- Add index on `tickers.exchange` (not currently indexed, only `symbol` has a unique index)
- Frontend: exchange filter as tabs (HOSE | HNX | UPCOM | All), default to "All" or user's last selection (zustand store)

**Detection:**
- Dashboard takes 3+ seconds to load market overview after adding HNX/UPCOM
- Frontend renders 1,500 heatmap cells → browser lag

**Phase to address:** Multi-market coverage — add backend filtering in the same phase as exchange support

---

### Pitfall 12: Performance Chart (PORT-09) Requires Daily Portfolio Snapshots — Can't Compute Retroactively from Trades Alone

**What goes wrong:**
PORT-09 wants a portfolio value-over-time chart. To plot "my portfolio was worth X on date Y," you need the market prices of all held tickers on each historical date. Computing this retroactively means: for every date in the range, determine holdings-at-date (replay trades), look up closing prices for each held ticker on that date, multiply and sum.

For a 1-year chart with 250 trading days and 10 holdings, that's 2,500 price lookups. This is doable but slow — and the query would be a nightmare of cross-joins between trades, lots, and daily_prices.

**Why it happens:**
Developers try to compute the chart data on-the-fly from raw trades and prices. This works for small portfolios but is fragile and slow.

**Prevention:**
- **Create `portfolio_snapshots` table**: `{id, date, total_market_value, total_cost, total_realized_pnl, total_unrealized_pnl, holdings_json}`. One row per trading day
- **Daily snapshot job**: After the daily summary at 16:00, compute current portfolio state and insert a snapshot. This is cheap (one query for current holdings + latest prices)
- **Backfill on demand**: When user first views the chart, compute snapshots retroactively for the past year. Cache the result. This is a one-time cost
- **Chart renders from snapshots**: Simple `SELECT date, total_market_value FROM portfolio_snapshots ORDER BY date` — fast, no complex joins
- **Use Recharts line chart**: Already in the stack (`recharts ~3.x`). Simple `<LineChart>` with date on X-axis, value on Y-axis

**Detection:**
- Performance chart API endpoint takes >5 seconds to respond
- Chart shows gaps on dates when no trades occurred (but portfolio still had value)

**Phase to address:** Portfolio Enhancements — create snapshot table and daily job BEFORE building the chart component

---

### Pitfall 13: Allocation Pie Chart (PORT-10) Needs Sector Data on Holdings — Current Holdings Query Doesn't Include It

**What goes wrong:**
PORT-10 wants portfolio allocation by sector/ticker. The current `get_holdings()` in `portfolio_service.py` returns `symbol`, `name`, `quantity`, `avg_cost`, `market_price`, `market_value`, `unrealized_pnl` — but NOT `sector` or `exchange`. To build a sector pie chart, the frontend needs sector data.

The `Ticker` model has `sector` and `industry` columns. But the holdings query only fetches `Ticker.symbol` and `Ticker.name` in the N+1 inner loop (line 120-124 of `portfolio_service.py`).

**Prevention:**
- Add `sector`, `industry`, and `exchange` to the holdings response
- Refactor the N+1 query in `get_holdings()`: instead of querying `Ticker` per row inside the loop, join `Lot` with `Ticker` in the initial aggregate query using `select(...).join(Ticker, Lot.ticker_id == Ticker.id)`
- This also fixes a latent performance issue — the current code does one DB query per holding inside a loop
- Pie chart: use Recharts `<PieChart>` with data grouped by sector. Show "Unclassified" for tickers without sector data

**Detection:**
- Allocation chart shows "Unknown" for all sectors
- Holdings API response time increases linearly with number of holdings (N+1 queries)

**Phase to address:** Portfolio Enhancements — refactor holdings query BEFORE building allocation chart

---

### Pitfall 14: Ex-Date Alerts (CORP-07) Fire Too Late If Checked After Market Close

**What goes wrong:**
CORP-07 sends Telegram alerts for upcoming corporate action ex-dates. The current `daily_corporate_action_check` runs as part of the post-market pipeline chain (triggered after price crawl at ~15:30). But ex-date alerts need to fire BEFORE the ex-date, not on the ex-date.

If a stock has ex-date tomorrow (2025-07-19) and the alert fires today at 16:00 (2025-07-18), that's fine. But if the corporate event was just crawled today, the system needs to immediately check for upcoming ex-dates within the next N days.

The current `corporate_event_crawler.py:crawl_all_tickers()` fetches events but doesn't trigger alerts — it just stores them.

**Prevention:**
- **Separate alert check from event crawling**: After new events are stored, scan for events with `ex_date BETWEEN today AND today + 5 days` and send alerts
- **Run alert check twice**: Once after corporate event crawl (catch newly discovered events), and once in the morning (8:30 AM) as a "today's ex-dates" reminder
- **Track sent alerts**: Add `alert_sent_at` column to `corporate_events` table (or a separate `sent_alerts` table). Don't send the same alert twice
- **Include actionable info**: "⚠️ VNM — Ex-date cổ tức tiền mặt: 2025-07-19 (ngày mai). Cần mua TRƯỚC ngày hôm nay để nhận quyền."

**Detection:**
- User learns about ex-date from the market (stock price drops) before receiving the alert
- Duplicate alerts for the same event on consecutive days

**Phase to address:** Corporate Actions Enhancements — implement alert tracking table alongside the alert logic

---

### Pitfall 15: Event Calendar View (CORP-08) Date Range Query on Unindexed ex_date Column

**What goes wrong:**
CORP-08 adds an event calendar showing corporate actions. The calendar needs efficient queries like `SELECT * FROM corporate_events WHERE ex_date BETWEEN '2025-07-01' AND '2025-07-31'`. The current `corporate_events` table has a unique constraint on `(ticker_id, event_type, ex_date)` and on `event_source_id`, but `ex_date` alone is not indexed.

At 1,500 tickers × 5-10 events each = 7,500-15,000 rows. PostgreSQL will do a sequential scan for date range queries without an index on `ex_date`.

**Prevention:**
- Add index: `CREATE INDEX ix_corporate_events_ex_date ON corporate_events (ex_date)`
- Calendar API endpoint: `GET /corporate-actions/calendar?start=2025-07-01&end=2025-07-31` returns events grouped by date
- Frontend: Use a lightweight calendar component or a simple date-grouped list (not a full calendar library — overkill for corporate events)
- Include exchange filter for multi-market: `WHERE ex_date BETWEEN :start AND :end AND ticker_id IN (SELECT id FROM tickers WHERE exchange = :exchange)`

**Detection:**
- Calendar page takes 1+ second to load (sequential scan on 15K rows)
- EXPLAIN ANALYZE shows `Seq Scan on corporate_events` instead of `Index Scan`

**Phase to address:** Corporate Actions Enhancements — add migration for index in same phase as calendar endpoint

---

### Pitfall 16: vnstock Freemium Model May Rate-Limit HNX/UPCOM Differently

**What goes wrong:**
The PROJECT.md notes vnstock is "moving to freemium model." The current `crawl_delay_seconds=3.5` was tuned for 400 HOSE tickers on VCI source. With HNX/UPCOM added:
- vnstock may impose different rate limits per exchange
- The VCI source may not support HNX/UPCOM tickers (VCI = Vietnam Credit Information, primarily HOSE)
- The `vnstock_breaker` circuit breaker shares state across all exchanges — one exchange's rate limit trips the breaker for all
- vnstock 3.5.1 `vnai` telemetry dependency may phone home with usage data, triggering quota checks

**Prevention:**
- **Test HNX/UPCOM fetching before committing to the architecture**: Run `Quote("PVS").history(start="2025-01-01")` for an HNX ticker and `Quote("BSR").history(start="2025-01-01")` for UPCOM in a test script. Verify the VCI source returns data
- **If VCI doesn't support HNX/UPCOM**: May need SSI source — `vnstock.explorer.ssi.quote.Quote` — which has different rate limits and response format
- **Per-exchange rate limit configuration**: `crawl_delay_hose=3.5`, `crawl_delay_hnx=5.0`, `crawl_delay_upcom=5.0` — start conservative for new exchanges
- **Monitor vnstock changelog**: Pin to 3.5.1 but watch for 3.6.x releases that may change API behavior or add freemium restrictions
- **Have a fallback**: If vnstock blocks heavy usage, the VNDirect REST API (already used for corporate events) also has OHLCV endpoints. Build the crawler abstraction to support multiple data sources

**Detection:**
- HNX/UPCOM crawl returns empty DataFrames or raises `KeyError`
- Rate limit errors spike after adding new exchanges
- vnstock raises new authentication/subscription errors after update

**Phase to address:** Multi-market coverage — validate data source compatibility FIRST, before building multi-exchange crawl jobs

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Multi-market coverage (HNX/UPCOM) | **Pitfall 1** (crawl time explosion), **Pitfall 16** (vnstock source compatibility), **Pitfall 11** (backend filtering needed) | Validate vnstock HNX/UPCOM support first. Split crawl per exchange. Add exchange filter to all API endpoints. Limit to top N per exchange. |
| Real-time WebSocket | **Pitfall 3** (no message broker, event loop contention) | Consider enhanced polling (30s React Query refetchInterval) instead of true WebSocket. If WebSocket needed, use in-memory ConnectionManager with watchlist-only scope. |
| Dividend tracking | **Pitfall 4** (record-date holdings check) | Build `dividend_payments` table and `get_holdings_at_date()` function. Do NOT model dividends as trades. |
| Performance chart | **Pitfall 12** (retroactive computation) | Build `portfolio_snapshots` table with daily snapshot job. Backfill on first view. |
| Allocation chart | **Pitfall 13** (missing sector in holdings) | Refactor holdings query to JOIN Ticker for sector data. Fix N+1 query pattern. |
| Trade edit/delete | **Pitfall 2** (FIFO lot corruption) | Add `sell_allocations` table. Implement lot replay. Soft delete trades. |
| Broker CSV import | **Pitfall 5** (format chaos, duplicates) | One broker first. Dry-run preview. Import batch tracking. Symbol normalization. |
| Gemini usage tracking | **Pitfall 10** (need SDK response interception) | Extract `usage_metadata` from Gemini responses. Store in `gemini_usage_log` table. |
| Pipeline timeline | **Pitfall 8** (no pipeline run ID) | Add `pipeline_run_id` to `job_executions`. Pass through job chain. |
| Telegram health notifications | **Pitfall 9** (notification spam) | Cooldown per category. Aggregate pipeline failures. Priority levels. |
| Rights issue tracking | **Pitfall 6** (optional exercise modeling) | Keep simple: track event + alert. Let user manually /buy on exercise. |
| Ex-date alerts | **Pitfall 14** (timing, dedup) | Morning alert check. Track sent alerts. Actionable Vietnamese messages. |
| Event calendar | **Pitfall 15** (unindexed ex_date) | Add index on ex_date. Calendar API with date range and exchange filter. |
| Adjusted/raw price toggle | **Pitfall 7** (indicator mismatch) | Hide indicators in adjusted mode, or compute client-side. |

---

## Integration Risk: Compound Effect of All v2.0 Features

The biggest meta-pitfall is attempting all v2.0 features simultaneously. Each feature alone is manageable, but the compound effect creates emergent risks:

| Compound Risk | Features Involved | Why Dangerous |
|---------------|-------------------|---------------|
| DB pool exhaustion | Multi-market + WebSocket + all enhanced queries | 1,500 tickers × longer crawls + persistent WS connections + snapshot queries + usage logging = pool starvation |
| Pipeline time explosion | Multi-market + AI analysis + corporate actions for all | 1,500 tickers × (crawl + indicators + AI + corporate actions) = 3-4 hour pipeline |
| Gemini quota exhaustion | Multi-market + AI analysis | 1,500 tickers at 25/batch = 60 batches × 4 analysis types = 240 Gemini calls/day. Free tier is 1,500/day. Add retries and you're at 50%+ quota. |
| Telegram message flood | Ex-date alerts + health notifications + portfolio P&L + daily summary | 5-10 messages/day per feature = 20-40 messages/day |
| Migration complexity | All new tables + columns + indexes | 5+ Alembic migrations that must be applied in order with data backfill |

**Mitigation:** Implement features in strict dependency order. Multi-market first (affects everything downstream). Portfolio enhancements second (independent from market coverage). Health enhancements third (observes the expanded system). Corporate actions enhancements last (builds on both market and portfolio).

---

## Sources

- Codebase analysis: `backend/app/` (models, services, crawlers, scheduler, telegram, api)
- Database schema: `models/daily_price.py`, `models/trade.py`, `models/lot.py`, `models/corporate_event.py`
- Pipeline architecture: `scheduler/manager.py`, `scheduler/jobs.py`
- Connection pool config: `database.py` (pool_size=5, max_overflow=3)
- Frontend components: `components/candlestick-chart.tsx`, `components/holdings-table.tsx`
- vnstock crawler: `crawlers/vnstock_crawler.py` (VCI source, exchange map)
- Corporate event crawler: `crawlers/corporate_event_crawler.py` (VNDirect REST API)
- Gemini integration: `services/ai_analysis_service.py` (batch size, delay, structured output)
- v1.0/v1.1 pitfalls: `.planning/research/PITFALLS.md` (prior research)
- Confidence: HIGH — all pitfalls derived from actual code patterns and database schema, not theoretical
