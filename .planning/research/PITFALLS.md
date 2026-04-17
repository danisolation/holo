# Pitfalls Research

**Domain:** Adding reliability, portfolio tracking, and observability features to existing VN stock intelligence platform (HOSE)
**Researched:** 2025-07-17
**Confidence:** HIGH (grounded in actual codebase analysis + domain knowledge)

## Critical Pitfalls

### Pitfall 1: Corporate Actions Adjusting Historical Prices Retroactively Breaks Computed Indicators and AI Analyses

**What goes wrong:**
When a stock split or bonus share event occurs (e.g., VNM 2:1 split), all historical prices before the ex-date must be retroactively adjusted. But the existing `technical_indicators` and `ai_analyses` tables were computed from **unadjusted** prices. If you adjust `daily_prices.adjusted_close` but don't recompute indicators and re-run AI analysis for affected tickers, the system has internally inconsistent data: old indicator values based on unadjusted prices, new indicator values based on adjusted prices, and AI analyses trained on mixed data.

**Why it happens:**
Developers treat price adjustment as a standalone data-fix. They update `daily_prices.adjusted_close` but forget the downstream cascade: indicators use close prices → AI analysis uses indicators → combined uses AI → signals use combined. The chain in `manager.py` (`_on_job_executed`) runs daily but doesn't have a concept of "recompute because historical data changed."

**How to avoid:**
- Store the adjustment factor per corporate action event, not just the adjusted price. This allows forward-compatible re-adjustment.
- When a corporate action is detected/entered, trigger a **targeted recompute pipeline**: adjust prices → recompute indicators for that ticker → invalidate AI analyses for that ticker (or mark as stale).
- Keep `close` (raw) and `adjusted_close` as separate columns (already in schema — good). ALWAYS use `adjusted_close` for indicator computation when available, fall back to `close`.
- Add a `last_adjusted_at` timestamp to a separate `corporate_actions` table to track when adjustments were applied.
- NEVER modify the raw `open/high/low/close` columns — keep them pristine as source-of-truth from vnstock. Only `adjusted_close` gets modified.

**Warning signs:**
- SMA(200) values for a ticker suddenly jump by the split ratio on a specific date
- AI analysis flips from "mua" to "bán" after a split with no real market change
- Bollinger Bands show false breakout on the ex-date
- `adjusted_close != close` for pre-event dates but `adjusted_close IS NULL` for post-event dates — inconsistency

**Phase to address:**
Corporate Actions phase (build this BEFORE portfolio tracking, since P&L needs adjusted prices too)

---

### Pitfall 2: FIFO Cost Basis with Partial Sells Creates Precision and Lot-Tracking Nightmares

**What goes wrong:**
FIFO (First-In, First-Out) cost basis sounds simple until you hit: (a) partial sells that split a lot — you bought 500 shares, sold 300, what's the cost basis of the remaining 200?; (b) multiple buys at different prices then one large sell that spans 3 lots; (c) VND (Vietnamese Dong) has no decimal subunits — prices are in whole VND but computations create fractional cost bases when dividing across lots; (d) stock splits changing the lot sizes retroactively.

**Why it happens:**
Developers implement P&L as `(sell_price - avg_buy_price) * quantity` — which is average cost, not FIFO. Or they implement FIFO but only track current total position instead of individual lots. When they need to handle partial sells or corporate actions that modify lot quantities, the data model doesn't support it.

**How to avoid:**
- Model trades as a `trades` table with individual records: `{ticker_id, date, type (buy/sell), quantity, price, fees}`.
- Model lots explicitly: a `lots` table where each buy creates a lot, and each sell consumes from the oldest open lot. Store `remaining_quantity` per lot.
- When a sell spans multiple lots, create multiple realized P&L records — one per lot consumed.
- Use `Numeric(18, 2)` for all money fields. The existing `Numeric(12, 2)` for daily prices is fine for VND (max ~9,999,999,999.99 VND = ~400K USD), but aggregated portfolio values and cost bases from lot splitting can be fractional and large.
- Corporate actions must adjust lot quantities AND lot costs: a 2:1 split doubles lot quantity and halves lot cost_per_share.
- Build a `replay_lots(ticker_id)` utility function from day one — you WILL need to recompute lots from raw trades when corporate actions are applied retroactively.

**Warning signs:**
- Total portfolio cost basis doesn't equal sum of individual lot cost bases
- Selling all shares of a ticker doesn't zero out the position
- Realized P&L numbers change when you add another buy after a sell (means lots are computed on-the-fly, not tracked)
- Rounding errors: portfolio value off by 1-10 VND from manual calculation

**Phase to address:**
Portfolio Tracking phase — get the data model right FIRST (trades + lots tables), then build P&L calculations on top. Don't try to compute FIFO from trade history on every read.

---

### Pitfall 3: Adding Retry/Circuit-Breaker to Existing Job Chain Without Breaking the EVENT_JOB_EXECUTED Listener

**What goes wrong:**
The current `_on_job_executed` in `manager.py` chains jobs by matching `event.job_id` strings (lines 27-89). If you add retry logic (e.g., tenacity wrapping job functions, or retry at the scheduler level), the retry mechanics interact badly with the chaining:
1. If a job fails on attempt 1, raises, then tenacity retries it, APScheduler sees the first failure and fires `EVENT_JOB_ERROR` — the chain breaks. The retry succeeds, but no chaining happens because `_on_job_executed` only fires once.
2. If you add a circuit breaker that short-circuits a job (returns early without raising), `_on_job_executed` fires with success, chaining the next job — but the data wasn't actually produced. Downstream jobs process stale/missing data.
3. Adding a "dead letter" mechanism that catches failures and logs them somewhere means the exception is swallowed — APScheduler sees success, chains continue on bad data.

**Why it happens:**
The `EVENT_JOB_EXECUTED` listener in APScheduler 3.x fires AFTER the job function returns. It only has two states: success (no exception) or failure (exception). Retry/circuit-breaker patterns blur this binary. APScheduler 3.x has no built-in retry or circuit breaker — these are manual additions that must respect the chaining contract.

**How to avoid:**
- Keep retry logic INSIDE the job functions (already partially done — `tenacity` is on `VnstockCrawler` methods). Don't wrap the job functions themselves with tenacity at the scheduler level.
- Return a result dict from each job (already done: `{"success": N, "failed": M}`). Add a `status` field: `"complete"`, `"partial"`, `"failed"`. The chaining listener can inspect `event.retval` to decide whether to chain.
- For circuit breaker: don't use actual circuit-breaker libraries on the job functions. Instead, implement a simple "health check before running" pattern: at the start of each chained job, verify the prerequisite data exists (e.g., `daily_indicator_compute` checks that today's prices exist before computing).
- For dead-letter: log failed items within the job (already done in `_crawl_batch` with `failed_symbols`), but still let the job return normally with partial success so chaining continues.
- Consider refactoring the listener-based chain into an explicit "pipeline runner" function that calls jobs sequentially with error handling — more readable and testable than event-listener spaghetti.

**Warning signs:**
- Downstream jobs run but produce empty results (no data to process)
- The chain stops completely after one transient failure in an upstream job
- `daily_signal_alert_check` at the end of the chain never fires
- Log shows "Job X failed with exception, not chaining next job" for transient errors

**Phase to address:**
Error Recovery phase — must be designed carefully around the existing chaining mechanism in `manager.py`.

---

### Pitfall 4: Vietnam Market Ex-Date and Record Date Confusion — HOSE Uses T+2 Settlement

**What goes wrong:**
On HOSE, stock settlement is T+2 (you buy on day T, ownership transfers on T+2). This means:
- **Ex-date** (ngày giao dịch không hưởng quyền): The first day a stock trades without the right to the dividend/split. Anyone buying on or after this date does NOT get the corporate action benefit.
- **Record date** (ngày đăng ký cuối cùng): Usually 2 trading days AFTER the ex-date due to T+2 settlement (i.e., ex-date = record_date - 2 trading days). If you use the wrong date for price adjustment, you'll adjust one or two days off.

Many sources report the record date, and the ex-date must be derived (subtract 2 trading days, skipping weekends and holidays). HOSE publishes corporate action announcements via HoSE website with record date; the ex-date is calculated.

Dividends on HOSE are announced as VND per share (e.g., 1,500 VND/share), not as percentage. Stock dividends are announced as ratio (e.g., 10:3 meaning 10 existing shares get 3 new shares). Bonus shares (thưởng) and rights issues (quyền mua) have different adjustment formulas.

**Why it happens:**
Developers from Western market backgrounds use ex-date directly from Yahoo Finance or similar. VN market data from vnstock may not include corporate action events at all (vnstock focuses on price/financial data). Corporate actions must be sourced separately (e.g., from CafeF, vietstock.vn, or HoSE announcements).

**How to avoid:**
- Build a `corporate_actions` table with: `{ticker_id, action_type, ex_date, record_date, ratio_numerator, ratio_denominator, cash_dividend_vnd, effective_date, source, raw_data}`.
- For price adjustment: adjust all prices BEFORE ex_date. The ex-date price is already the post-event price (market opens adjusted on ex-date morning).
- Cash dividend adjustment formula: `adjusted_price = close × (1 - dividend / reference_price)` where reference_price is the closing price the day before ex-date. Simple version: `adjusted_price = close - dividend_per_share` for all pre-ex-date prices.
- Stock split/bonus adjustment formula: `adjusted_price = close × old_shares / new_shares` (e.g., for 10:3 bonus, adjust = close × 10/13).
- Start with MANUAL entry of corporate actions (you're the sole user) rather than trying to auto-scrape. Auto-scraping corporate actions from Vietnamese sources is fragile — announcements are PDF files, Vietnamese text with inconsistent formatting.
- Validate: after adjustment, the closing price on the day before ex-date (adjusted) should be close to the opening price on ex-date (within normal ±7% HOSE limit movement).

**Warning signs:**
- Price chart shows sudden 50% drops that aren't real crashes (stock split not adjusted)
- Cost basis calculations are wildly wrong after a dividend payment
- AI analysis triggers "mua mạnh" (strong buy) on every stock that just had a dividend cut (unadjusted price drop looks like a crash)

**Phase to address:**
Corporate Actions phase — the FIRST feature to build in v1.1. Everything else (portfolio P&L, AI accuracy) depends on correct price adjustments.

---

### Pitfall 5: Gemini Structured Output Schema Drift Between Prompt and Response Model

**What goes wrong:**
The existing AI service uses `response_schema` for structured output (Pydantic models like `TechnicalBatchResponse`, `FundamentalBatchResponse`, etc.). When improving prompts in v1.1:
1. You change the prompt to ask for new fields (e.g., "confidence_reason" in addition to "score") but forget to update the Pydantic response model → Gemini may still return the field (unvalidated) or silently drop it.
2. You change the Pydantic model to add new required fields but forget to update the prompt → Gemini invents values for fields it wasn't asked about.
3. `gemini-2.5-flash-lite` (current model in `config.py` line 56) may interpret structured output constraints differently than `gemini-2.0-flash` — model upgrades can break response schemas.
4. Batch responses with 25 tickers (current `gemini_batch_size` in settings) — if ONE ticker's analysis fails Pydantic validation, the entire batch response could be rejected. 25 tickers' worth of Gemini API budget lost.

**Why it happens:**
The prompt text and the `response_schema` Pydantic model are defined in different parts of the code. There's no compile-time check that they're in sync. Gemini's structured output is best-effort — it tries to match the schema but can fail on complex nested structures or when the prompt contradicts the schema.

**How to avoid:**
- Keep the prompt template and the response Pydantic model adjacent in code (already done — both in `ai_analysis_service.py`). Add a comment on each Pydantic field: `# Referenced in prompt as: "..."`.
- Parse batch responses per-ticker with try/except: if one ticker fails validation, log it and continue with the rest. Don't let one bad ticker reject the whole batch.
- Version your prompt templates (e.g., `PROMPT_V2_TECHNICAL = """..."""`) so you can A/B test old vs new.
- When upgrading the Gemini model, run the full pipeline once manually and diff the outputs before switching the scheduled model.
- Test with edge cases: tickers with no data, tickers with extreme values (penny stocks at 1,000 VND, blue chips at 150,000 VND), tickers with Vietnamese characters in the name.
- Make ALL new response fields `Optional[X] = None` initially. Only make them required after confirming Gemini reliably populates them.

**Warning signs:**
- Batch analysis returns fewer tickers than input (some failed validation silently)
- `raw_response` JSONB column shows fields not in the Pydantic model
- Error rate spikes after changing the Gemini model version in settings
- Success count drops from ~400 to ~300 after a prompt change

**Phase to address:**
AI Improvements phase — refactor prompt management with versioning and per-ticker validation before changing any prompt content.

---

### Pitfall 6: Database Connection Pool Exhaustion When Adding Health Monitoring and Portfolio Queries

**What goes wrong:**
Current pool in `database.py`: `pool_size=5, max_overflow=3` = max 8 connections. Aiven has ~20-25 connection limit for the tier. Currently used by: daily cron jobs (1 session each, held for duration of crawl), API endpoints (1 session per request via `get_db()`), Telegram handlers (1 session per command via `async_session()`). This works at v1.0 scale.

v1.1 adds:
- Health monitoring endpoint polling DB for data freshness, error counts, connection status
- Portfolio queries that join trades + lots + prices + tickers (heavier queries)
- `/portfolio` Telegram command doing the same
- P&L computation scanning all trades and current prices
- Daily P&L notification job (new chained job)
- Periodic health checks

Each of these acquires a session. If the health endpoint polls every 30 seconds, and a daily crawl is running (holding a session for ~13 minutes), and someone uses the Telegram bot, and the dashboard is open with React Query auto-refreshing... you hit 8 connections and new requests queue/timeout.

**Why it happens:**
Pool size was correctly conservative for Aiven's connection limits. But each new feature adds another concurrent session consumer. The pool doesn't grow — it was designed for v1.0's workload.

**How to avoid:**
- Do NOT blindly increase `pool_size` beyond 8-10 total. Aiven's connection limit is a hard ceiling.
- Make health checks use a SEPARATE lightweight approach: a single `SELECT 1` via the existing pool (not a dedicated connection), and cache the result for 60s.
- Ensure scheduler jobs commit and close sessions promptly. The current `async with async_session() as session:` pattern is good (auto-closes on block exit). But the 13-minute crawl job holds a session for the full duration — verify it commits per-batch (it does — `_crawl_batch` commits after each batch).
- For portfolio P&L computation: compute once after daily crawl and CACHE the result in a `portfolio_snapshots` table, don't recompute on every API/Telegram request.
- Add connection pool metrics to health monitoring: `engine.pool.checkedout()`, `engine.pool.checkedin()`, `engine.pool.overflow()`.
- Consider `pool_timeout=10` (fail fast with a clear error instead of hanging when pool exhausted).

**Warning signs:**
- API requests timing out during daily crawl hours (15:30-15:45 UTC+7)
- `asyncpg.exceptions.TooManyConnectionsError` from Aiven
- Health endpoint reports "connected" but actual queries hang
- Telegram commands become unresponsive during crawl window

**Phase to address:**
System Health phase — must measure connection usage BEFORE adding more consumers. Add pool metrics first, then add features with awareness of headroom.

---

### Pitfall 7: Dual Watchlist State (localStorage vs PostgreSQL) Leading to Silent Data Divergence

**What goes wrong:**
The frontend watchlist (`useWatchlistStore` in `src/lib/store.ts`) uses `zustand/persist` → localStorage. The Telegram watchlist uses `user_watchlist` table in PostgreSQL (via `/watch` and `/unwatch` commands). These are SEPARATE stores with no sync mechanism. When building portfolio tracking:
- If the portfolio is DB-backed (it must be — trades are financial records), portfolio tickers and watchlist tickers are different concepts stored in different places.
- User adds ticker to watchlist on dashboard (localStorage only) → expects to see it when checking Telegram `/list` → it's not there.
- User watches a ticker on Telegram → expects dashboard to reflect it → dashboard reads localStorage, not DB.
- Portfolio "owned tickers" becomes a THIRD source of truth for "tickers I care about."
- Signal alerts (via `check_signal_changes`) only fire for Telegram watchlist tickers — dashboard-only watchers never get alerts.

**Why it happens:**
v1.0 made a reasonable decision (noted in PROJECT.md Key Decisions as "⚠️ Revisit"): localStorage for single-user dashboard speed, DB for Telegram bot. But portfolio tracking makes the DB the authoritative source for financial data. The split creates confusion about which list drives what.

**How to avoid:**
- Migrate the dashboard watchlist to DB-backed. Single-user means the API is simple: `GET/POST/DELETE /api/watchlist` with no auth. Keep zustand store for client-side caching, but sync from DB on load.
- Clearly separate concepts in the data model: `user_watchlist` = monitoring list (for alerts and tracking), `portfolio_holdings` (computed from `trades` table) = ownership. You might watch VNM without owning it, and own HPG without having it on your watchlist.
- OR: keep localStorage watchlist as a "dashboard view filter" (purely cosmetic) and make Telegram watchlist + portfolio holdings the functional data sources. But document this clearly.

**Warning signs:**
- Dashboard watchlist shows different tickers than Telegram `/list`
- Adding a trade for a ticker doesn't add it to any watchlist automatically
- User confusion about "why doesn't my portfolio ticker show up in signal alerts?"

**Phase to address:**
Portfolio Tracking phase — unify watchlist to DB as a prerequisite step before building portfolio tables.

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Compute FIFO P&L on every request instead of caching | No cache invalidation logic needed | O(n) scan of all trades per request; gets slow as trade count grows | Never for portfolio summary; acceptable for single-ticker detail view with <20 trades |
| Manual corporate action entry only (no auto-scraper) | No fragile scraper to maintain | Must remember to enter events; missed events corrupt data silently | Acceptable for personal use — you'll see the price chart anomaly and fix it. Add a weekly "unadjusted price anomaly" check. |
| Hardcoded Gemini model name in `settings.gemini_model` | Simple config | Model deprecation breaks everything overnight; no fallback | Acceptable but add a startup health check that sends a dummy prompt to verify the model works |
| `asyncio.to_thread()` for vnstock sync calls | Works, non-blocking | Each call occupies a thread from the default ThreadPoolExecutor (max ~32 threads on most systems) | Acceptable for 400 tickers with 3.5s delays between calls; would break if calls were parallelized |
| Single `_gemini_lock` for all analysis types | Prevents rate limit hits | Serializes ALL Gemini calls — a manual trigger via API blocks until the daily batch finishes (can be 30+ minutes for all 4 analysis types) | Acceptable for single-user but be aware: new portfolio-specific Gemini calls will also queue behind this lock |
| Event-listener job chaining instead of explicit pipeline | Works with APScheduler's built-in event system | Hard to test, hard to add branching/retry logic, job ID string matching is fragile | Consider refactoring to explicit pipeline runner in Error Recovery phase |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **APScheduler 3.x + retry** | Wrapping job functions with tenacity at the scheduler level, causing APScheduler to see the initial failure and fire `EVENT_JOB_ERROR` before retry completes | Keep retry INSIDE job functions. Job function should catch all exceptions internally and return result dict. Only `raise` for truly unrecoverable errors that should break the chain. |
| **APScheduler `add_job` in listener** | Adding a job from `_on_job_executed` without `replace_existing=True` raises `ConflictingIdError` if the job ID exists from a previous run | Already handled correctly (all chained jobs use `replace_existing=True`) — preserve this pattern for any new chained jobs. |
| **asyncpg + SQLAlchemy lazy loading** | Accessing lazy-loaded relationships after session close or in a different async context | Current config uses `expire_on_commit=False` (good). For new portfolio joins (trades → lots → ticker), use `selectinload()` or `joinedload()` to eagerly load related objects within the session context. |
| **vnstock + corporate actions** | Expecting vnstock to provide adjusted prices or corporate action data | vnstock provides raw/unadjusted prices only (confirmed in `vnstock_crawler.py` line 62: "No adjusted_close — vnstock returns UNADJUSTED prices only"). Corporate action data must come from a separate source (manual entry, CafeF, or HoSE website). |
| **Gemini 15 RPM + new portfolio analysis** | Adding portfolio-specific Gemini calls (e.g., "analyze my portfolio risk") that compete with the daily 400-ticker batch analysis | All Gemini calls already go through `_gemini_lock`. New portfolio analysis must also acquire this lock. Better: queue portfolio analysis as a chained job AFTER the daily pipeline completes, not during. |
| **Partitioned `daily_prices` + new JOINs** | Writing queries that JOIN `daily_prices` to `trades` or `lots` without a date-range WHERE clause | Always include `WHERE daily_prices.date >= X` in JOINs involving `daily_prices`. Without it, PostgreSQL scans ALL year partitions. This is invisible during development with small data but devastating in production with 2+ years of data. |
| **Telegram bot + heavy commands** | Creating `/portfolio` handler that does heavy P&L computation synchronously in the handler function, blocking the bot's polling loop | Keep handler lightweight: read pre-computed data from DB, format message, reply. If computation is heavy, reply with "⏳ Đang tính toán..." then use `asyncio.create_task()` to compute and edit the message when done. |
| **Alembic + partitioned tables** | Using `alembic revision --autogenerate` which doesn't understand PostgreSQL partitioning — may try to recreate `daily_prices` as a regular (non-partitioned) table | Write partition-aware migrations manually for any `daily_prices` schema changes. Autogenerate is safe for new tables (`trades`, `lots`, `corporate_actions`). |
| **loguru + health metrics** | Parsing loguru log output to extract error counts for the health dashboard | Don't parse logs for metrics. Add explicit counters (a simple in-memory dict, or `collections.Counter`) that track success/failure per job per day. Health endpoint reads counters directly. Logs are for humans, counters are for code. |
| **vnstock freemium migration** | Continuing to crawl 400 tickers daily without checking if vnstock restricts free-tier usage | Monitor vnstock changelog and PyPI releases. The `vnai` telemetry dependency is already concerning (noted in STACK.md). If free tier is restricted, fallback options: reduce to top-100 tickers, increase `crawl_delay_seconds`, or call VCI API directly (vnstock's underlying source). |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Computing P&L from full trade history on every API request | Portfolio endpoint latency grows linearly with trade count | Pre-compute P&L after daily price update; store in `portfolio_snapshots` table. API reads cached snapshot. | After ~200-500 trades per ticker, or ~50 total tickers with trades |
| Health endpoint running `COUNT(*)` on `daily_prices` for freshness check | Query takes 2-5 seconds on partitioned table | Use `SELECT MAX(date) FROM daily_prices WHERE date >= CURRENT_DATE - 7` (partition-pruned) or maintain a `crawl_status` summary row updated by the crawl job. | Immediately — `COUNT(*)` on partitioned table is always slow |
| Frontend polling health endpoint every 5 seconds via React Query | Consumes DB pool connections, adds latency to all other queries | Set `staleTime: 60000` and `refetchInterval: 60000` in React Query for health data. Health doesn't need real-time freshness. | When multiple dashboard tabs are open simultaneously |
| Recomputing ALL 400 tickers' indicators when one corporate action adjusts prices | Indicator computation takes 5-10 minutes for all tickers | Only recompute indicators for the AFFECTED ticker. The `IndicatorService.compute_for_ticker()` method already exists — use it for targeted recomputation. | After any corporate action event |
| N+1 queries in Telegram `/list` and `/portfolio` | Each watched ticker triggers 2 separate queries (analysis + price), visible as 40+ DB queries for 20 tickers | Batch queries: fetch all prices and analyses for the ticker list in one query each using `WHERE ticker_id IN (...)`. The existing `/list` handler (lines 134-183 of `handlers.py`) has this N+1 problem already. | Noticeable with >10 watched tickers |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Portfolio shows unrealized P&L based on yesterday's close without labeling the reference date | User thinks P&L is real-time; makes decisions on stale data | Always show "Giá tham chiếu: [date]" next to P&L. Color-code or dim stale data (>1 trading day old). |
| Corporate action adjusts chart silently — price history changes shape without explanation | User sees chart change and thinks it's a bug or data corruption | Show annotation markers on candlestick charts at ex-dates (lightweight-charts supports markers). Tooltip: "Chia cổ tức 1,500 VND/cp" |
| Daily P&L Telegram notification with absolute number only | "+2,500,000 VND" is meaningless without portfolio size context | Always show: absolute gain + percentage gain + total portfolio value. Format: "+2.5M VND (+1.2%) · Tổng: 210M VND" |
| Health dashboard showing raw error counts instead of error rates | "47 errors" sounds alarming; "47/16,000 = 0.3% error rate" is routine | Show error rate (errors/total), not just absolute count. Include time window: "0.3% (24h)" |
| Trade entry requiring manual price lookup | User must alt-tab to find the exact execution price for a past trade | Auto-fill price from `daily_prices.close` for the trade date. Allow override for exact execution price. Show "Giá đóng cửa: 85,200 VND" as default. |
| Telegram `/portfolio` response for 20+ positions exceeds 4096-char limit | Message gets truncated or fails to send silently | Top-5 positions by value, then "... và N vị thế khác · Tổng: X VND". Link to dashboard for full view. |

## "Looks Done But Isn't" Checklist

- [ ] **Corporate actions — price adjustment:** Works for splits → but did you also adjust `lots` table quantities and cost basis? A 2:1 split means each lot now has 2× shares at ½ cost per share.
- [ ] **Corporate actions — indicator cascade:** Adjusted `adjusted_close` → but did you recompute `technical_indicators` for that ticker? Old RSI/MACD values are based on unadjusted prices.
- [ ] **FIFO P&L — partial sells:** Realized P&L correct for full sells → but does it handle partial sells that split a lot? And does `remaining_quantity` on the lot update correctly?
- [ ] **FIFO P&L — sell spanning lots:** Selling 700 shares when you have lots of 500 + 300 → does it consume 500 from lot 1 and 200 from lot 2, creating two realized P&L records?
- [ ] **Portfolio value — dividend income:** Shows capital gains → but does total return include cash dividends received? Total return = capital gains + dividends.
- [ ] **Error recovery — chain continuity:** Jobs retry on failure → but does the `_on_job_executed` chain still work after a successful retry? Test: mock vnstock to fail 2×, succeed on 3rd. Verify indicators still compute via chaining.
- [ ] **Health monitoring — weekend awareness:** Shows data freshness → but does it distinguish "no crawl today" (Saturday/Sunday/holiday) vs "crawl failed" (Monday error)? HOSE doesn't trade weekends or VN holidays.
- [ ] **AI prompts — regression testing:** New prompt produces better output for test cases → but did you verify it doesn't REGRESS on cases the old prompt handled well? Run both on the same 25-ticker sample and diff.
- [ ] **Health monitoring — pool metrics:** Shows "DB connected" → but does it show how many connections are in use vs available? Pool exhaustion looks like "connected" on health check but hangs on real queries.
- [ ] **Telegram /portfolio — zero holdings:** User sold all shares → does it show realized P&L for closed positions, or does it say "Chưa có vị thế nào"? Should show historical P&L.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong corporate action applied (bad ratio) | MEDIUM | 1. Delete/correct the corporate action record. 2. Revert `adjusted_close` by recalculating from raw `close` + corrected factors. 3. Recompute indicators for affected ticker via `compute_for_ticker()`. 4. AI analyses regenerate on next daily run (or trigger manually). |
| FIFO lots out of sync with trades | HIGH | 1. Delete all lot records for affected ticker. 2. Replay all trades in chronological order to rebuild lots (requires `replay_lots()` utility). 3. Recompute realized P&L from rebuilt lots. Build this replay function from day one. |
| Daily chain completely broken (no data for 3 days) | LOW | 1. Trigger manual backfill for missing days via existing `/api/backfill` endpoint. 2. Manual trigger indicator compute via `/api/crawl/indicators`. 3. Manual trigger AI analysis. Chain self-heals on next successful `daily_price_crawl`. |
| Connection pool exhausted | LOW | 1. Restart FastAPI process (clears pool). 2. Check Aiven console for leaked/idle connections. 3. Add `pool_recycle=300` to engine config to auto-close stale connections. 4. Review which processes are holding sessions too long. |
| Gemini model deprecated / API changed | MEDIUM | 1. Update `gemini_model` in `.env` to new model name. 2. Run one batch manually via API trigger to verify structured output still parses. 3. If schema changed, update Pydantic response models in `schemas/analysis.py`. |
| vnstock free tier restricted | HIGH | 1. Reduce crawl to top-100 tickers by market cap. 2. Increase `crawl_delay_seconds`. 3. If fully blocked: extract VCI API endpoints from vnstock source code and call them directly. 4. Long term: evaluate paid data providers. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Price adjustment cascade (Pitfall 1) | Corporate Actions | After adjusting a test ticker, verify indicators recomputed and chart looks correct. Compare adjusted chart with CafeF's adjusted chart for same ticker. |
| FIFO lot tracking (Pitfall 2) | Portfolio Tracking | Unit test: buy 500 @ 80K, buy 300 @ 85K, sell 600 → verify lot 1 consumed (500), lot 2 partially consumed (100 remaining at 85K), two realized P&L records created. |
| Retry breaking chain (Pitfall 3) | Error Recovery | Integration test: mock vnstock to fail 2× then succeed. Verify full chain completes (prices → indicators → AI → news → sentiment → combined → alerts). |
| VN market ex-date confusion (Pitfall 4) | Corporate Actions | Manual test: enter a known historical corporate action (find a VNM or FPT 2024 event). Verify adjusted chart aligns with TradingView or CafeF. |
| Gemini schema drift (Pitfall 5) | AI Improvements | Before deploying new prompt: run old and new prompts on same 25-ticker batch. Diff outputs. Verify all fields parse into Pydantic model. |
| Connection pool exhaustion (Pitfall 6) | System Health | Stress test: start daily crawl + hit health endpoint in a loop + trigger Telegram commands simultaneously. Monitor `engine.pool.status()`. |
| Dual watchlist divergence (Pitfall 7) | Portfolio Tracking | After DB migration: verify Telegram `/list` and dashboard watchlist show identical tickers. Add a simple sync-check endpoint. |
| N+1 queries in Telegram handlers | Portfolio Tracking | Benchmark: `/list` with 20 tickers should be <500ms. If >1s, batch queries are needed. |
| Health endpoint performance | System Health | Health endpoint should respond in <200ms even during active crawl. If slower, caching or query optimization needed. |

## VN Market-Specific Gotchas

These are specific to HOSE/VN market and NOT generalizable from US/EU market experience:

| Gotcha | Impact | Mitigation |
|--------|--------|------------|
| **VND has no decimal subunits** — prices are whole numbers (e.g., 85,000 VND), but per-share cost basis from lot splitting creates fractional VND | P&L rounding errors accumulate over many trades | Use `Numeric(18, 2)` for cost basis internally. Round final P&L display to whole VND (`ROUND(x, 0)`). Document the rounding policy. |
| **HOSE trading hours: 9:00-11:30 & 13:00-14:45 ICT** — there's a mandatory lunch break | Health monitoring "no data" alarms during lunch break are false positives | Health check must know the HOSE trading schedule including the lunch gap. Don't alarm on missing data between 11:30-13:00 ICT. |
| **Vietnamese holidays differ from Western** — Tết Nguyên Đán (Lunar New Year) is 5-9 days off, plus many other national holidays | Missing crawl on holidays isn't an error, but system may treat multi-day gaps as failures | Maintain a HOSE holiday calendar (or heuristic: if vnstock returns empty for ALL tickers, it's likely a holiday). Don't treat holiday gaps as crawl failures. |
| **Tick sizes on HOSE** — 10 VND for <10K, 50 VND for 10K-50K, 100 VND for >50K stocks | Price alerts set at non-tick-aligned prices will never trigger exactly | Use `>=`/`<=` for alert triggers (already done with direction-based checking). For trade entry: validate price aligns with tick size, or at minimum warn. |
| **Floor/ceiling price limits: ±7% on HOSE** | Stock can't move more than 7% in one day; corporate actions on ex-date can look like limit hits | When a corporate action adjusts the reference price, the visible intraday movement on ex-date can trigger false "floor hit" alerts. Filter out ex-date from anomaly detection. |
| **VN stocks trade in lots of 100 shares (lô chẵn)** on HOSE main board | Invalid trade quantities entered in portfolio | Add validation on trade entry: `quantity % 100 == 0` for HOSE stocks. Odd lots (lô lẻ) trade on a separate mechanism at worse prices — warn if entered. Allow override for odd-lot trades. |
| **vnstock 3.x freemium migration** — vnstock maintainers may restrict free tier API calls | Daily crawl of 400 tickers (400+ API calls) may exceed future free tier limits | Monitor vnstock releases and changelogs. The `vnai` telemetry dependency is a signal of commercial direction. Have a fallback: reduce ticker count, switch to direct VCI API, or cache aggressively. |
| **Dividend payment delay** — dividends announced with ex-date but paid weeks/months later | Portfolio "dividend income" should distinguish announced vs received | Store both `ex_date` and `payment_date` in corporate actions table. Show "pending dividends" separately from "received dividends" in P&L. For simplicity in v1.1: count dividends as income on ex-date (standard accounting practice for individual investors). |
| **Rights issues (quyền mua) are NOT free** — unlike bonus shares, rights issues give the right to BUY at a discounted price | Treating rights issues as bonus shares would overstate portfolio value | Rights issues require separate handling: the adjustment factor accounts for the dilution, and if the user exercises the rights, it's a new BUY trade at the subscription price. Track whether rights were exercised or sold. |

## Sources

- **Codebase analysis:** All backend modules reviewed — `main.py`, `database.py`, `config.py`, `scheduler/manager.py`, `scheduler/jobs.py`, all models, all services, all crawlers, all telegram handlers
- **Specific code references:**
  - `manager.py` lines 17-89: Job chaining via `_on_job_executed` event listener
  - `vnstock_crawler.py` line 62: "No adjusted_close — vnstock returns UNADJUSTED prices only"
  - `database.py` lines 5-11: Connection pool `pool_size=5, max_overflow=3`
  - `config.py` line 56: `gemini_model = "gemini-2.5-flash-lite"`
  - `store.ts`: Zustand localStorage-based watchlist (separate from DB)
  - `daily_price.py` line 32: `adjusted_close` column already exists as nullable
  - PROJECT.md Key Decisions: localStorage watchlist marked "⚠️ Revisit"
- **VN market rules:** HOSE T+2 settlement, ±7% price limits, 100-share lots, tick sizes — standard publicly available HOSE trading regulations
- **Confidence:** HIGH for codebase-grounded pitfalls (verified against actual code lines). MEDIUM for VN market specifics (domain knowledge; specific 2025 HOSE rule changes not verified against official HoSE website).

---
*Pitfalls research for: Holo v1.1 — Reliability & Portfolio features*
*Researched: 2025-07-17*
