# Feature Landscape — v1.1 Reliability & Portfolio

**Domain:** Stock Intelligence Platform — v1.1 Milestone Features
**Researched:** 2026-04-16
**Overall Confidence:** HIGH (based on codebase analysis, vnstock API inspection, VN market domain knowledge)

**Context:** v1.0 shipped with data pipeline (400 HOSE tickers OHLCV + financials), 4-type AI analysis (technical + fundamental + sentiment + combined), Telegram bot (7 commands), and Next.js dashboard (charts, heatmap, watchlist). This research covers ONLY the v1.1 features.

---

## 1. Corporate Actions Handling

### Table Stakes

Features required for data integrity. Without these, historical analysis and portfolio P&L are unreliable.

| Feature | Why Expected | Complexity | Dependency | Notes |
|---------|--------------|------------|------------|-------|
| **Fetch corporate events from VCI** | vnstock `Company.events()` returns `OrganizationEvents` with `eventTitle`, `eventListCode`, `ratio`, `value`, `recordDate`, `exrightDate`, `issueDate`, `publicDate` — this is our data source | Low | Existing `VnstockCrawler` | Add `fetch_events(symbol)` method; same `asyncio.to_thread()` pattern as existing crawler. VCI GraphQL returns events per ticker. |
| **Corporate actions DB table** | Store events to track what's been processed and avoid re-applying adjustments | Low | Alembic migration | Table: `corporate_actions` with fields: `ticker_id`, `event_type` (enum: cash_dividend, stock_dividend, bonus_shares, rights_issue, stock_split, reverse_split), `ex_date`, `record_date`, `ratio`, `value`, `is_processed`, `raw_data` (JSONB) |
| **Cash dividend tracking** | Most common corporate action on HOSE. Companies pay 1-4 times/year. Typical VN format: "500 đồng/cổ phiếu" (VND per share). Price drops by dividend amount on ex-date. | Med | Corporate actions table | Store `value` field from VCI events. On ex-date, historical `adjusted_close` should reflect the dividend drop. VN dividends are always in VND (not %). |
| **Stock dividend / bonus shares** | Very common on HOSE — companies issue free shares (e.g., ratio 10:1 = 1 bonus share per 10 held). Price adjusts proportionally on ex-date. | Med | Corporate actions table | VCI `ratio` field contains the issuance ratio. Adjustment factor = `old_shares / (old_shares + new_shares)`. |
| **Stock split handling** | Less common than bonus shares on HOSE but happens. E.g., 1:2 split — price halves, shares double. | Med | Corporate actions table | Mechanically identical to bonus shares from an adjustment perspective. `ratio` from VCI encodes the split factor. |
| **Historical price adjustment (adjusted_close)** | The `adjusted_close` column already exists in `daily_prices` (currently NULL per line 30-32 of daily_price.py). Populate it using cumulative adjustment factors from all corporate actions. | High | All corporate action types parsed | **Critical**: Must apply adjustments cumulatively from newest to oldest. Adjustment factor compounds: if a stock had a 2:1 split AND a 10:1 bonus, the adjustment factor for prices before both events is `(1/2) * (10/11)`. Recalculate for all historical prices per ticker. |
| **Daily corporate actions check** | Crawl events on schedule to detect new corporate actions; process and adjust prices automatically. | Med | Scheduler (APScheduler), crawl job chain | Add to daily pipeline chain after `daily_price_crawl`. Or run weekly — events are announced days/weeks before ex-date. |

### Differentiators

| Feature | Value Proposition | Complexity | Dependency | Notes |
|---------|-------------------|------------|------------|-------|
| **Rights issue tracking** | Track rights offerings (phat hanh them cho co dong hien huu). Less frequent but impacts dilution and portfolio value. | Med | Corporate actions table | VCI events include rights issues. Ratio + exercise price stored. Does NOT auto-adjust prices (rights have optional exercise). |
| **Corporate action Telegram alerts** | Notify via Telegram when a watched ticker has upcoming ex-date. | Low | Corporate actions table + Telegram bot | Scan for upcoming ex-dates (e.g., within next 7 days) during daily pipeline. |
| **Event calendar on dashboard** | Show upcoming corporate actions on a timeline/calendar view for watchlist tickers. | Med | Corporate actions API endpoint + frontend | Useful for planning trades around ex-dates. |
| **Adjusted vs raw price toggle on chart** | Let user switch between raw OHLCV and adjusted prices in candlestick chart. | Low | `adjusted_close` populated + frontend toggle | Use lightweight-charts `setData()` to swap series. Small UX win. |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Auto-adjust prices from external adjusted data** | vnstock returns UNADJUSTED prices only (confirmed in crawler line 62). Don't try to fetch pre-adjusted data from a paid source. | Calculate adjusted prices ourselves from corporate events — we have the data from VCI `OrganizationEvents`. |
| **Real-time corporate action detection** | Corporate actions are announced days/weeks in advance. Real-time is unnecessary and wastes API calls. | Daily or weekly scan is sufficient. |
| **Handling warrants/convertible bonds** | Out of scope — project covers 400 HOSE stock tickers only. | Ignore non-stock corporate actions. |

### Vietnam-Specific Notes (HOSE Corporate Actions)

**Key terms:**
- **Ngay GDKHQ** (Ngay giao dich khong huong quyen) = Ex-right date — the day trading WITHOUT the right
- **Ngay chot quyen** (Record date) = Who gets the dividend/bonus
- **T+2 settlement**: VN market uses T+2. Ex-date is typically 2 business days before record date.
- **Co tuc tien mat** = Cash dividend (always in VND per share, not percentage)
- **Co tuc co phieu** = Stock dividend / bonus shares (ratio format: 10:1 = 1 new per 10 held)
- **Tach co phieu** = Stock split (ratio format: 1:2 = 1 old becomes 2 new)
- **Phat hanh them** = Rights issue (ratio + exercise price)

**VCI `eventListCode` mapping** (inferred from GraphQL schema):
The `eventListCode` and `eventListName`/`en_EventListName` fields categorize the event type. Common codes include cash dividends, stock dividends, bonus shares, and rights offerings. Map these to our enum during crawl.

**Adjustment formula:**
```
For cash dividend of D VND per share on ex-date E:
  adjustment_factor = (close_before_ex - D) / close_before_ex

For stock dividend/split with ratio N:M (M new shares per N held):
  adjustment_factor = N / (N + M)

Cumulative: multiply all factors for events AFTER a given date
adjusted_close = raw_close * cumulative_factor
```

---

## 2. Portfolio Tracking

### Table Stakes

| Feature | Why Expected | Complexity | Dependency | Notes |
|---------|--------------|------------|------------|-------|
| **Manual trade entry (buy/sell)** | Core of any portfolio tracker. Enter: ticker, quantity, price, date, side (buy/sell), fees/commission. | Med | New `trades` table + API endpoints | Single-user, no auth needed. Telegram `/buy VNM 100 82000` and dashboard form both write to same table. VN brokers charge 0.15-0.25% commission (configurable). |
| **Holdings view (current positions)** | Show aggregated current holdings: ticker, quantity, avg cost, current price, market value, unrealized P&L, P&L %. | Med | `trades` table + `daily_prices` | Aggregate from trades using cost-basis method. Display on dashboard and via Telegram `/portfolio`. |
| **FIFO cost basis** | Standard method in VN for individual investors. First shares bought = first shares sold. | Med | `trades` table, ordered by date | Track remaining lot quantities. When selling, consume oldest lots first. Update avg cost on remaining holdings. |
| **Realized P&L** | Show profit/loss on closed positions. Realized when shares are sold. | Med | FIFO lot matching | `realized_pnl = sell_price * qty - cost_basis_of_lots_consumed - fees`. Track per-trade and aggregate. |
| **Unrealized P&L** | Show paper profit/loss on open positions using latest market price. | Low | Holdings + latest `daily_prices.close` | `unrealized_pnl = (current_price - avg_cost) * remaining_qty`. Updates daily after price crawl. |
| **Portfolio summary (total value, total P&L)** | Aggregate: total invested, total market value, total realized, total unrealized, total return %. | Low | Holdings + realized P&L | Simple aggregation. Core metric for `/portfolio` command. |
| **Trade history** | View list of all entered trades with date, ticker, side, qty, price, fees, P&L (if sell). | Low | `trades` table + API | Sortable/filterable table on dashboard. |

### Differentiators

| Feature | Value Proposition | Complexity | Dependency | Notes |
|---------|-------------------|------------|------------|-------|
| **Dividend income tracking** | Track cash dividends received on held positions. VN dividends are significant (3-8% yield common). | Med | Corporate actions + holdings snapshot at record date | On dividend record date, calculate: `dividend_income = shares_held * dividend_per_share`. Requires knowing holdings AT record date, not just current. Store in `portfolio_dividends` table. |
| **Portfolio P&L on Telegram** | `/portfolio` full summary. `/pnl VNM` for specific ticker. Daily notification with portfolio change. | Med | Portfolio service + Telegram handlers | High personal utility — see P&L without opening dashboard. Daily P&L change notification at 16:00 alongside daily summary. |
| **Position-aware AI alerts** | When AI generates a signal change for a ticker you HOLD (not just watch), elevate alert priority. | Low | Holdings + existing signal alert check | Cross-reference holdings with signal changes. Enhances existing `daily_signal_alert_check` job. |
| **Portfolio performance chart** | Line chart showing portfolio total value over time. | Med | Daily portfolio snapshot table | Requires storing daily portfolio value snapshots. Use Recharts (already in stack) for the chart. |
| **Portfolio allocation pie chart** | Show sector/ticker allocation breakdown. | Low | Holdings + ticker.sector | Use Recharts pie chart. Simple aggregation from holdings x current price. |
| **Trade edit/delete** | Ability to correct mistakes in trade entry. | Low | CRUD on `trades` table | Essential for personal use — will make entry errors. Recalculates P&L after edit. |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Broker API integration / auto-import trades** | VN broker APIs are not standardized, most don't offer them publicly. High complexity, fragile. | Manual entry via Telegram bot and dashboard form. |
| **Multi-currency / multi-market portfolio** | Project scope is HOSE only, VND only. | Hardcode VND. No currency conversion. |
| **Tax calculation module** | VN stock capital gains tax is 0.1% of sell value (flat rate). Not worth building a full tax module. | Show total sell value x 0.1% as a line item if needed. |
| **Options / derivatives tracking** | Out of scope — HOSE stocks only. | Ignore. |
| **Weighted average cost (WAC)** | FIFO is standard for VN individual investors and simpler to implement. | Use FIFO only. |
| **Portfolio import from CSV/Excel** | Premature optimization for single user with maybe 20-50 trades. | Manual entry is fine. Add import later if pain point emerges. |

### Data Model Notes

```
trades table:
  id, ticker_id, trade_date, side (buy/sell), quantity, price,
  fees, notes, created_at

portfolio_holdings (materialized view or computed):
  ticker_id, total_quantity, avg_cost, total_invested

portfolio_daily_snapshot (for performance chart):
  date, total_value, total_cost, realized_pnl, unrealized_pnl

portfolio_dividends:
  id, ticker_id, record_date, dividend_per_share, shares_held,
  total_amount, corporate_action_id
```

---

## 3. AI Prompt Improvements

### Table Stakes

| Feature | Why Expected | Complexity | Dependency | Notes |
|---------|--------------|------------|------------|-------|
| **System instruction (persona)** | Move the "You are a Vietnamese stock market analyst" text from the user prompt to Gemini's `system_instruction` parameter. Produces more consistent persona behavior. Currently baked into every prompt. | Low | `_call_gemini()` method | `google-genai` supports `system_instruction` in `GenerateContentConfig`. Separate concerns: system = who you are, user = what to analyze. |
| **Few-shot examples in prompts** | Add 1-2 concrete examples of ideal output for each analysis type. Dramatically improves output consistency. | Low | Prompt builder methods | Add a `## Example` section with one ticker analysis example. Keep brief — don't bloat token count (400 tickers x 25/batch = 16 batches). |
| **Explicit scoring rubric** | Current prompts say "score 1-10" but don't define what each number means. Model interprets inconsistently. | Low | Prompt builder methods | Define clear score anchors. Reduces score clustering around 5-7 (common LLM behavior). |
| **Price context in technical prompts** | Current technical prompt sends indicators but NOT the actual price. Model can't assess "price is at SMA(200) support" without knowing the price. | Low | `_get_technical_context()` | Add `latest_close`, `price_vs_sma20_pct`, `price_vs_sma50_pct` to context. Already available from `daily_prices` table. |
| **Vietnamese consistency in combined prompts** | Technical + fundamental prompts use English reasoning; sentiment + combined use Vietnamese. Be explicit about language choice in prompt. | Low | Prompt builder methods | Keep English for tech/fund (Gemini more reliable in English for financial terms), Vietnamese for combined/sentiment only. |

### Differentiators

| Feature | Value Proposition | Complexity | Dependency | Notes |
|---------|-------------------|------------|------------|-------|
| **Structured output validation + retry** | When `response.parsed` returns None (already has JSON fallback), retry the exact same prompt once instead of just falling back to manual parse. | Low | `_analyze_*_batch()` methods | Already partially implemented (JSON fallback exists). Add: if both fail, retry API call once with `temperature=0.1`. |
| **Analysis quality tracking** | Log distribution of scores, signal types, reasoning length per batch. Detect drift: if all tickers suddenly score 5-6. | Med | Logging + optional analytics table | Store structured data. Alert if median score shifts >1.5 points vs 7-day average. |
| **Confidence calibration guidelines** | Combined analysis confidence clusters around 5-7. Add explicit negative examples: "Do NOT give 8+ when sentiment data is missing." | Low | `_build_combined_prompt()` | Refine existing confidence rules. |
| **Sector-relative context** | Add sector average P/E, P/B to fundamental prompt. Currently uses static "Vietnam market P/E ~12-15". | Med | Compute sector averages from `financials` table | Group by `ticker.sector`, compute median P/E and P/B per sector. |
| **Prompt versioning** | Track which prompt version produced each analysis. Compare old vs new quality. | Low | `model_version` field already exists | Extend to include prompt version: "gemini-2.5-flash-lite:prompt-v2". |
| **Temperature tuning per analysis type** | Technical = more deterministic (temp=0.1); sentiment = slightly creative (temp=0.3). Currently all temp=0.2. | Low | `_call_gemini()` method | Pass temperature as parameter. Minor but free improvement. |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Fine-tuning Gemini** | Requires massive labeled datasets and is expensive. | Iterate on prompts + structured schemas (already using Pydantic response_schema). |
| **Multi-model consensus** | Triples API cost for marginal benefit. | Use single model (Gemini) with good prompts. |
| **RAG-based analysis** | Massive complexity, questionable benefit vs direct data feeding. | Continue feeding structured data directly in prompts. |
| **Real-time prompt modification UI** | Overkill for personal use. | Edit prompts in code. Track version in `model_version` field. |

### Prompt Improvement Patterns (Specific to Current Codebase)

**Current weakness 1: No price in technical prompt**
```python
# Current: sends indicators without price reference
"RSI(14) last 5 days: [45.2, 48.1, 52.3, 49.7, 51.1]"
"SMA(20): 82000.0, SMA(50): 80500.0, SMA(200): 78200.0"
# Missing: what is the actual close price?

# Fix: add to _get_technical_context()
"Latest close: 83,500 VND"
"Price vs SMA(20): +1.83%, Price vs SMA(50): +3.73%"
```

**Current weakness 2: Score anchors undefined**
```python
# Current: "strength: 1-10 (confidence in the signal)"
# Fix: Add rubric
# "strength scoring rubric:
#  1-2 = extremely weak signal, barely detectable
#  3-4 = weak signal, minor indicators align
#  5-6 = moderate signal, some indicators support
#  7-8 = strong signal, most indicators agree
#  9-10 = very strong signal, all indicators strongly aligned"
```

**Current weakness 3: System instruction not separated**
```python
# Current: persona baked into user prompt
"You are a Vietnamese stock market (HOSE) technical analyst..."

# Fix: Use google-genai system_instruction
config = types.GenerateContentConfig(
    system_instruction="You are a senior Vietnamese stock market (HOSE) analyst...",
    response_mime_type="application/json",
    response_schema=schema,
    ...
)
```

---

## 4. Error Recovery & Pipeline Resilience

### Table Stakes

| Feature | Why Expected | Complexity | Dependency | Notes |
|---------|--------------|------------|------------|-------|
| **Granular retry with tenacity** | Batch-level failures in AI analysis skip entire batches. Need per-ticker retry for individual failures. | Med | `_run_batched_analysis()` | Already handles 429 and 503 at batch level. Add: re-batch only failed tickers for one more attempt. |
| **Dead letter queue for failed tickers** | When a ticker fails after all retries, store in `failed_jobs` table with error details. | Med | New `failed_jobs` table | Fields: `job_type`, `ticker_id`, `error_message`, `failed_at`, `retry_count`, `resolved_at`. |
| **Graceful degradation on partial pipeline failure** | If indicator compute fails for 5 tickers, the remaining 395 should still proceed. Currently works but failures aren't tracked. | Low | Already mostly implemented | Need to store partial results and log which tickers were skipped. |
| **Job execution logging** | Log start/end time, success/fail count for every scheduled job. Queryable via API. | Med | New `job_executions` table | Fields: `job_id`, `started_at`, `completed_at`, `status`, `result_summary` (JSONB), `error_message`. |
| **Crawler failure notification** | Telegram alert if daily price crawl fails completely. | Low | Jobs + Telegram bot | Add try/catch that sends Telegram on critical failure. |

### Differentiators

| Feature | Value Proposition | Complexity | Dependency | Notes |
|---------|-------------------|------------|------------|-------|
| **Automatic retry of failed jobs** | Schedule retry (30 min later) for failed tickers only. | Med | Dead letter queue + APScheduler | Only retry items with `retry_count < 3`. |
| **Circuit breaker for external APIs** | If vnstock/VCI is down, stop hammering after N failures. | Med | Tenacity or custom | Already partially implemented for vnstock. Add for VCI company events. |
| **Rate limit tracking** | Track Gemini API usage (RPM, tokens consumed). | Low | Already logging token counts | Aggregate from logs or store in DB. Show on health dashboard. |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Message queue (Redis/RabbitMQ)** | Overkill for single-user app. Adds infrastructure dependency. | Keep APScheduler job chaining pattern. |
| **Kubernetes-style health probes** | No container orchestration needed. | Simple `/health` endpoint (already exists). |

---

## 5. System Health Dashboard

### Table Stakes

| Feature | Why Expected | Complexity | Dependency | Notes |
|---------|--------------|------------|------------|-------|
| **Data freshness indicator** | Show when data was last updated for each type: prices, financials, news, AI analysis. | Low | Query latest timestamps from each table | Flag stale data (>1 business day for prices). |
| **Last crawl status** | Show success/failure/partial for last execution of each job. | Med | `job_executions` table | Green (success), yellow (partial), red (failed). |
| **Scheduler status (enhanced)** | Already exists. Enhance with last run result and human-readable schedule. | Low | Existing endpoint | Add `last_run_result` to response. |
| **Error rate display** | Show error count per job over last 7 days. | Med | `job_executions` table | Simple aggregation. Display as table or chart. |
| **Database connection pool status** | Show active/idle connections. Aiven pool_size=5, max_overflow=3. | Low | SQLAlchemy engine `pool.status()` | Expose via API endpoint. |
| **Health dashboard page** | Frontend page with all health metrics. Status cards with green/yellow/red indicators. | Med | All health API endpoints + new frontend page | Route: `/dashboard/health`. Use shadcn Card components. |

### Differentiators

| Feature | Value Proposition | Complexity | Dependency | Notes |
|---------|-------------------|------------|------------|-------|
| **Gemini API usage tracker** | Show daily token consumption, requests, errors vs free tier limits. | Med | Log aggregation or usage table | Show as line chart over last 30 days. |
| **Pipeline execution timeline** | Visual timeline: crawl -> indicators -> AI -> alerts with duration per step. | Med | `job_executions` table | Gantt-style timeline for today's pipeline. |
| **Telegram health notification** | Daily or on-error health summary via Telegram. | Low | Health data + Telegram bot | Add to daily summary or separate notification. |
| **Manual job trigger from dashboard** | Buttons to re-trigger crawl, indicators, AI analysis. | Low | Existing `/crawl/*` endpoints + frontend buttons | Wire existing POST endpoints to UI buttons. |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Grafana / Prometheus monitoring** | Requires additional infrastructure. Overkill for personal use. | Build simple health page in existing Next.js dashboard. |
| **APM (Sentry, DataDog, etc.)** | Adds cost and complexity. | Loguru structured logging + health endpoint. |
| **Distributed tracing** | Single process app — nothing to trace. | Loguru with correlation IDs if needed. |

---

## 6. Portfolio on Telegram

### Table Stakes

| Feature | Why Expected | Complexity | Dependency | Notes |
|---------|--------------|------------|------------|-------|
| **`/buy <ticker> <qty> <price>` command** | Primary trade entry. "/buy VNM 100 82000" | Low | Portfolio service + `trades` table | Same validation pattern as `/alert` handler. |
| **`/sell <ticker> <qty> <price>` command** | Close/reduce positions. "/sell VNM 50 85000" | Low | Portfolio service + FIFO logic | Validate against holdings. Show realized P&L on sell. |
| **`/portfolio` command** | Show all holdings with P&L. | Med | Portfolio service | Format as table. Truncate for Telegram 4096 char limit. |
| **Daily portfolio P&L notification** | At 16:00 alongside daily summary. | Low | Portfolio snapshot + daily summary job | Add to existing `daily_summary_send` job. |

### Differentiators

| Feature | Value Proposition | Complexity | Dependency | Notes |
|---------|-------------------|------------|------------|-------|
| **`/pnl <ticker>` command** | Detailed P&L with FIFO lot breakdown. | Med | Portfolio service with lot-level detail | Useful before deciding to sell. |
| **Position-aware daily summary** | Highlight owned tickers first with P&L context. | Low | Portfolio + daily summary | Small modification to existing `build_daily_summary()`. |
| **`/trades` command** | Show recent trade history (last 10). | Low | `trades` table | Simple query + format. |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Inline keyboard trade confirmation** | Over-engineering for single user. | Execute immediately. Add `/trades` to review. |
| **Natural language trade input** | Parsing ambiguity. | Strict format: `/buy VNM 100 82000`. |

---

## Feature Dependencies

```
Corporate Actions --> Adjusted Price Calc --> More Accurate AI Analysis
                 \-> Dividend Income --> Full P&L Reporting

Trades Table --> Holdings --> Unrealized P&L --> Portfolio Summary
            \-> FIFO Lots --> Realized P&L -/
                                             \-> Telegram /portfolio
                                             \-> Dashboard Portfolio Page

Job Executions Table --> Health Dashboard
                    \-> Error Tracking --> Dead Letter Queue --> Auto Retry

AI Prompt Improvements --> Better Analysis Quality (independent, no hard deps)

System Health --> Data Freshness (requires existing tables only)
            \-> Job Monitoring (requires job_executions table)
```

### Critical Path

1. **Corporate Actions table -> Price adjustment -> Portfolio tracking** — Portfolio P&L requires adjusted prices for accuracy. Build corporate actions first.
2. **Trades table + FIFO -> Portfolio view -> Telegram commands** — Backend before bot.
3. **Job executions table -> Health dashboard** — Need to log executions before displaying them.
4. **AI prompt improvements** — Independent, can be done in parallel with anything.

---

## MVP Recommendation

### Phase 1: Must ship (table stakes across all areas)

1. **Corporate actions crawl + storage** — Foundation for data integrity
2. **Historical price adjustment** — Fills the existing `adjusted_close` NULL column
3. **Trades table + buy/sell entry** — Core portfolio feature
4. **FIFO cost basis + realized/unrealized P&L** — Core portfolio calculation
5. **`/buy`, `/sell`, `/portfolio` Telegram commands** — Primary consumption channel
6. **AI prompt improvements** (system instruction, few-shot, scoring rubric, price context) — Low effort, high impact
7. **Job execution logging** — Foundation for health monitoring
8. **Data freshness + basic health page** — Operational visibility

### Phase 2: Differentiators (ship after table stakes work)

1. **Dividend income tracking** — Depends on corporate actions + portfolio
2. **Position-aware AI alerts** — Cross-references holdings with signals
3. **Portfolio performance chart** — Needs daily snapshots
4. **Dead letter queue + auto retry** — Pipeline resilience
5. **Pipeline timeline visualization** — Health dashboard enhancement
6. **Corporate action Telegram alerts** — Scan for upcoming ex-dates

### Defer

- **Portfolio import from CSV** — add only if manual entry becomes painful
- **Event calendar on dashboard** — nice but not critical for v1.1
- **Sector-relative AI context** — meaningful but higher complexity
- **Gemini usage tracking** — nice-to-have, not blocking

---

## Sources

| Finding | Source | Confidence |
|---------|--------|------------|
| vnstock `Company.events()` returns OrganizationEvents with exrightDate, recordDate, ratio, value | Direct inspection of `vnstock.explorer.vci.company` source code | HIGH |
| VCI GraphQL fields: eventTitle, eventListCode, en_EventListName, publicDate, issueDate, recordDate, exrightDate, ratio, value | Direct inspection of GraphQL payload in Company._fetch_data() | HIGH |
| vnstock has NO built-in price adjustment (returns unadjusted OHLCV only) | Confirmed in existing `vnstock_crawler.py` comment line 62 | HIGH |
| `adjusted_close` column already exists in DailyPrice model, currently NULL | Confirmed in `daily_price.py` line 30-32 | HIGH |
| Current prompts embed persona in user message, no system_instruction used | Confirmed in `ai_analysis_service.py` prompt builder methods | HIGH |
| Current prompts lack price data in technical analysis | Confirmed in `_build_technical_prompt()` — sends indicators but not close price | HIGH |
| Existing health endpoint at `/health` with DB + scheduler checks | Confirmed in `api/system.py` | HIGH |
| APScheduler job chaining via EVENT_JOB_EXECUTED | Confirmed in `scheduler/manager.py` | HIGH |
| Gemini structured output via Pydantic response_schema already working | Confirmed in `_call_gemini()` and `schemas/analysis.py` | HIGH |
| VN market T+2 settlement, cash dividends in VND per share | Standard HOSE market knowledge | HIGH |
| VN individual stock capital gains tax is 0.1% of sell value | Standard VN tax regulation | HIGH |
| FIFO as standard VN cost basis method | Standard accounting practice for VN individual investors | MEDIUM |
| VN broker commission range 0.15-0.25% | General market knowledge, varies by broker and tier | MEDIUM |
