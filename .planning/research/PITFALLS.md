# Domain Pitfalls — v8.0 AI Trading Coach

**Domain:** Adding AI-powered daily picks, trade journal, behavior tracking, and adaptive strategy to existing VN stock intelligence platform
**Researched:** 2025-07-24
**Platform context:** Holo — 800+ tickers, Gemini structured output, PostgreSQL/Aiven, FastAPI + Next.js, single-user personal use
**Market:** Vietnam HOSE/HNX/UPCOM — T+2 settlement, no short selling, lot sizes, price steps, ±7% daily limits

---

## Critical Pitfalls

Mistakes that cause dangerous financial decisions, data corruption, or major rewrites.

---

### Pitfall 1: AI Hallucinated Stock Picks — Phantom Tickers, Impossible Prices

**What goes wrong:** Gemini generates daily picks containing ticker symbols that don't exist on HOSE/HNX/UPCOM (e.g., inventing "VNX" or confusing with NYSE tickers), entry prices outside the ±7% daily limit band, or stop-loss levels that are physically impossible given the exchange's price step rules (e.g., 82,030 VND on HOSE where the step is 10 VND below 10K, 50 VND for 10K-50K, 100 VND for ≥50K).

**Why it happens:** Gemini's training data includes global stock tickers. When asked for "top picks," it may hallucinate tickers from other markets or generate plausible-sounding Vietnamese ticker codes that don't exist. The existing `_validate_trading_signal()` validates entry ±5% and SL within 3×ATR — but daily picks have a different risk profile: they're **actionable recommendations** a beginner will directly trade, not exploratory analysis across 800 tickers.

**Consequences:** Beginner user places orders on tickers that don't exist (wasted effort), or enters at prices that are outside today's tradeable range and the order sits unfilled. Worse: user trusts a hallucinated "safe pick" with a stop-loss the exchange will never match due to price step rounding.

**Prevention:**
- **Hard validation layer:** Every pick ticker MUST exist in the `tickers` table. Reject any ticker not in DB.
- **Price feasibility check:** Entry must be within today's price limit band (previous close ±7% for HOSE, ±10% HNX, ±15% UPCOM). Don't rely on Gemini knowing the limits.
- **Price step normalization:** Round all price targets to valid price steps: 10 VND (< 10,000), 50 VND (10,000–49,950), 100 VND (≥ 50,000 on HOSE). Invalid prices → auto-round, don't reject.
- **Liquidity gate:** Reject picks with average daily volume < 10,000 shares (illiquid stocks trap beginners).
- **Re-use existing validation pattern:** Extend `_validate_trading_signal()` with daily-pick-specific rules. The existing post-validation architecture (entry ±5%, SL ≤3×ATR) is the right pattern — just add VN-market-specific checks.
- **Structured output schema:** Define a Pydantic model for daily picks that constrains Gemini output. The project already uses `response_schema` in `GeminiClient` — apply the same pattern.

**Detection:** Log every validation failure with reason. If >30% of picks fail validation in a week, the prompt needs rewriting.

**Existing code to leverage:** `app/services/analysis/prompts.py::_validate_trading_signal()`, `app/schemas/analysis.py::TickerTradingSignal`, `app/services/analysis/gemini_client.py` structured output pattern.

---

### Pitfall 2: Survivorship Bias When Evaluating Pick Quality

**What goes wrong:** The system tracks daily picks and later shows "65% win rate!" — but this only counts picks the user actually traded. Picks the user skipped (often the losers, because they "felt wrong") aren't in the journal. The AI adapts based on journal results, learning from a biased sample where bad picks are systematically excluded.

**Why it happens:** Natural human behavior — user sees 5 picks, trades the 2 that look safest, skips the 3 that feel risky. Journal records 2 wins. System concludes "100% accuracy" when reality was 2/5 = 40%.

**Consequences:** False confidence in AI quality. Adaptive strategy overfits to the surviving picks, recommending similar patterns. User increases position sizes based on inflated win rate. Eventually, a correlated loss wipes out gains.

**Prevention:**
- **Track ALL picks, not just traded ones.** Every daily pick gets a row in the database regardless of whether the user trades it. Fields: `pick_date`, `ticker`, `entry_suggested`, `outcome` (tracked automatically via price data).
- **Two win rates:** Display "Traded win rate" AND "All picks win rate" side by side. Make the user see the gap.
- **Auto-evaluate untraded picks:** Use closing prices on the pick's target date to simulate what would have happened. This is straightforward since the system already crawls daily OHLCV for 800+ tickers.
- **Survivorship flag in adaptive strategy:** When the adaptive engine learns from results, weight ALL picks equally, not just traded ones.

**Detection:** If "Traded win rate" exceeds "All picks win rate" by >15 percentage points for >2 weeks, show a warning: "Bạn đang chọn lọc kết quả — xem lại tất cả gợi ý."

---

### Pitfall 3: P&L Calculation Errors with VN Market Rules

**What goes wrong:** P&L calculations show incorrect profit/loss because they ignore VN-specific rules: T+2 settlement, lot sizes of 100, price steps, trading fees, and the mandatory 0.1% personal income tax on sells.

**Why it happens:** Developer uses simple (sell - buy) × quantity formula from textbooks or US market tutorials. VN market has unique mechanics that silently corrupt P&L.

**Consequences:** User thinks they made 500K VND profit, but after fees/tax the real profit is 350K. Or worse: user tries to sell shares they bought yesterday (T+0) and can't, but the journal doesn't reflect that the position is locked until T+2.

**Specific VN market rules that MUST be implemented:**

| Rule | Detail | P&L Impact |
|------|--------|------------|
| **Lot size = 100 shares** | HOSE requires orders in multiples of 100. HNX allows odd lots in some sessions. | Position size must be rounded to 100-share lots. Suggested capital / entry price → round DOWN to nearest 100 shares. |
| **Price steps** | HOSE: 10₫ (<10K), 50₫ (10K-49.95K), 100₫ (≥50K). HNX: 100₫ all prices. | Entry/SL/TP must be valid price steps. Invalid prices → order rejected by exchange. |
| **T+2 settlement** | Shares bought on Monday available to sell on Wednesday (T+2 = 2 business days). HOSE has T+2, technically T+2.5 historically but now aligned to T+2. | Journal must track `buy_date` and `sellable_date = buy_date + 2 business days`. Show "locked" status before sellable date. |
| **Trading fees** | Broker fee: 0.15-0.25% per side (varies by broker, typical ~0.15% for online). | P&L = (sell × qty) - (buy × qty) - buy_fee - sell_fee - sell_tax. User should configure their broker fee rate. |
| **Sell tax** | 0.1% of gross sell value (personal income tax, mandatory). | Applied on every sell transaction. Must be subtracted from P&L. |
| **Daily price limits** | HOSE: ±7%, HNX: ±10%, UPCOM: ±15% from reference price. | Stop-loss or take-profit outside limit → won't execute in one day. SL beyond -7% may take 2+ days to trigger (gap down risk). |
| **No fractional shares** | Unlike US markets, no partial share trading. | Position sizing must produce whole multiples of 100 shares. Small capital (<50M VND) severely limits diversification. |

**Prevention:**
- **Create a `VNMarketRules` utility class** with methods: `round_to_lot_size(qty)`, `round_to_price_step(price, exchange)`, `calculate_fees(value, side, fee_rate)`, `calculate_tax(sell_value)`, `get_sellable_date(buy_date)`, `get_limit_prices(ref_price, exchange)`.
- **Store fee rate in user settings** (default 0.15%, configurable). This already has precedent — v4.0 paper trading had settings (now removed but the pattern existed).
- **Always show gross P&L and net P&L** separately. Beginners need to understand the fee drag.
- **Business day calendar:** VN market holidays affect T+2 calculation. Either maintain a holiday list or use a simple "weekday-only" approximation with a note that holidays may shift dates.

**Detection:** Automated test: create a journal entry for buying 100 shares of VNM at 82,000 and selling at 83,000. Expected net P&L should be: (83,000 - 82,000) × 100 - (82,000 × 100 × 0.0015) - (83,000 × 100 × 0.0015) - (83,000 × 100 × 0.001) = 100,000 - 12,300 - 12,450 - 8,300 = **66,950 VND** (not 100,000). If the test shows 100,000, fees are missing.

---

### Pitfall 4: Over-Trading Recommendations Burning Small Capital

**What goes wrong:** AI generates 3-5 picks daily. Beginner user tries to trade all of them. With <50M VND capital and lot size of 100 shares, buying 5 stocks means ~10M per position → 100-share lots of mid-cap stocks. Trading fees eat into profits at this scale. Frequent trading creates a psychological cycle: loss → revenge trade → bigger loss.

**Why it happens:** The feature spec says "3-5 picks daily." A beginner interprets this as "trade all 5 every day." AI doesn't understand the user's capital constraints or emotional state.

**Consequences:** User over-trades, fees compound, small losses accumulate, capital depletes faster than expected. The system designed to help becomes the cause of losses.

**Prevention:**
- **Capital-aware pick count:** With <50M VND, recommend MAX 1-2 positions at a time (not 5). Calculate: `capital / avg_pick_entry_price / 100 × 100` = max concurrent positions at minimum lot size. Show this on the picks page.
- **"Pick of the Day" primary mode:** Show 1 highest-conviction pick prominently. Show 2-4 additional picks as "also watching" with explicit "chỉ xem, không nhất thiết phải giao dịch" (watch only, don't necessarily trade).
- **Position limit enforcement:** If user has 3 open journal trades, show a warning before allowing a 4th. "Bạn đang giữ 3 vị thế — mở thêm tăng rủi ro."
- **Cooldown after losses:** If the journal shows 2 consecutive losing trades, the daily pick section should show a "pause and review" message instead of new picks. This is the adaptive strategy's most important safety feature.
- **Fee impact preview:** Before each pick, show: "Phí giao dịch ước tính: 24,750 VND (nếu mua 100 cổ @ 82,000)" so the user sees the cost of trading.

**Detection:** Track `trades_per_week` metric. If >5 trades/week for capital <50M, surface a behavioral warning.

---

### Pitfall 5: Gemini Rate Limit Exhaustion — Daily Picks Pipeline Competing with Existing Pipelines

**What goes wrong:** The existing daily pipeline already consumes most of the 15 RPM Gemini quota: technical analysis (800 tickers / 25 per batch = 32 calls), fundamental (32), sentiment (32), combined (32), trading signals (800/15 = 54 calls). That's ~182 Gemini calls with 4s delays = ~12 minutes. Adding daily picks (even just scanning 50 candidates to select 5) adds more calls that push the pipeline past rate limits, causing failures and partial results.

**Why it happens:** Developer adds the daily picks generation as another scheduled job without accounting for the total Gemini budget across all pipelines.

**Consequences:** Either daily picks fail silently (no picks generated), or existing analysis pipelines get disrupted (partial analysis for 800 tickers). The `_gemini_lock` (module-level asyncio.Lock in `ai_analysis_service.py`) serializes access, but doesn't prevent quota exhaustion.

**Prevention:**
- **Don't make daily picks a separate Gemini call for 50+ tickers.** Instead, **derive daily picks from existing analysis data:** filter today's combined recommendations where signal=mua, confidence≥8, and trading_signal has long_confidence≥7. This requires ZERO additional Gemini calls.
- **If AI must generate picks:** Use a single Gemini call with the top 10-15 pre-filtered candidates (not 50+). The pre-filter uses existing technical + fundamental + sentiment scores already in the DB.
- **Budget accounting:** Add a `daily_gemini_budget` config (e.g., max 5 calls for daily picks). The picks pipeline checks remaining budget before calling.
- **Schedule after existing pipeline completes:** Use job chaining (EVENT_JOB_EXECUTED pattern already in `scheduler/jobs.py`) to ensure daily picks run AFTER all 5 analysis types complete. Don't run in parallel.
- **Cache picks for the day:** Generate once in the morning (after ~15:30 when data is fresh). If user views picks page later, serve from DB, don't regenerate.

**Existing infrastructure to leverage:** The job chaining pattern via `EVENT_JOB_EXECUTED` in `scheduler/manager.py`, the `_gemini_lock` serialization, the `GeminiUsage` tracking table for monitoring.

**Detection:** Monitor `gemini_usage` table. If daily total exceeds 200 calls or error rate spikes above 10%, the pipeline is overloaded.

---

### Pitfall 6: Adaptive Strategy Creating a Dangerous Feedback Loop

**What goes wrong:** The adaptive strategy learns from user's journal results and adjusts future picks. If the user had 3 winning trades in banking stocks, the AI starts recommending more banking stocks. Banking sector has a correction → all concentrated positions lose simultaneously. The AI learned a pattern that was actually market-wide momentum, not stock-specific alpha.

**Why it happens:** Small sample sizes. With 1-2 trades per week, after a month you have ~8 data points. Any "pattern" in 8 trades is noise, not signal. The AI doesn't know the difference.

**Consequences:** Sector concentration risk. False sense of "the AI is learning me" when it's actually overfitting to recent market conditions. User loses more than they would with random diversified picks.

**Prevention:**
- **Minimum sample size gate:** Don't activate adaptive strategy until at least 20 completed trades. Before that, use default safety-first parameters.
- **Sector diversification constraint:** Never recommend >2 picks from the same industry sector in a single week, regardless of what the adaptive model suggests. The existing trading signals already have sector data.
- **Adaptation speed limit:** Don't change strategy parameters more than once per week (weekly review, not per-trade adjustment). Prevents whipsawing.
- **Recency decay, not recency obsession:** Weight last 20 trades equally. Don't over-weight the last 3 trades. A simple moving average of results is better than exponential weighting for small samples.
- **Hard safety rails that adaptation can NEVER override:** Max position size ≤20% of capital, max concurrent positions ≤3, only stocks with average volume >50,000/day. These constraints persist regardless of how "confident" the adaptive model becomes.
- **Transparency:** Show the user what the adaptive strategy changed and why: "Giảm mức rủi ro từ 3% → 2% vì 2 lệnh gần nhất lỗ." Don't silently adjust.

**Detection:** If the adaptive model recommends >50% of capital in a single sector for >2 consecutive weeks, something is wrong.

---

## Moderate Pitfalls

---

### Pitfall 7: Trade Journal Entry Timing vs Actual Execution Mismatch

**What goes wrong:** User enters a journal trade as "bought VNM at 82,000 on Monday." But the actual execution might have been at 82,100 (partial fill, price moved) or the order was placed Monday but filled Tuesday. The journal records the intended price, not the actual execution price. Over time, this creates phantom P&L that doesn't match the user's real brokerage account.

**Why it happens:** The system is a manual journal, not connected to a brokerage API. Users round prices, forget exact fill times, enter trades retroactively. Vietnam has no public retail brokerage API for automated import.

**Prevention:**
- **Make entry price a required field with reasonable validation** — must be within the trading day's OHLCV range. If user says "bought at 82,000" but the day's low was 82,500, flag it.
- **Suggest the day's close price as default** — reduces friction and is usually close to actual fill.
- **Allow price range tolerance** — validate entry_price is within [day_low, day_high] from `daily_prices` table. Reject obviously wrong prices (typos like 8,200 instead of 82,000).
- **"Approximate" flag:** Let user mark entries as approximate. Don't include approximate entries in precision P&L stats, but include in directional analysis (win/loss).
- **Date validation:** `buy_date` must be a trading day (not weekend/holiday). Check against existing `daily_prices` data — if no price data exists for that date, it wasn't a trading day.

**Detection:** Compare journal entries against daily_prices OHLCV. If >20% of entries have prices outside the day's range, user is entering inaccurate data.

---

### Pitfall 8: Behavior Tracking Data Explosion and Storage Bloat

**What goes wrong:** Behavior tracking records every ticker the user views, every time they visit the picks page, every filter change. With 800+ tickers and multiple daily visits, this generates hundreds of rows per day. On Aiven PostgreSQL with pool_size=5, the behavior_tracking table grows to millions of rows within months, slowing down queries that power the adaptive strategy.

**Why it happens:** "Track everything, analyze later" mentality. Developer logs raw events without considering aggregation strategy or retention policy.

**Consequences:** Database bloat on Aiven (free/small tier has storage limits). Slow behavior analysis queries. Pool exhaustion during bulk inserts. The `pool_size=5, max_overflow=3` constraint in `database.py` means only 8 concurrent DB connections — behavior tracking inserts compete with price crawling and analysis storage.

**Prevention:**
- **Aggregate, don't log raw events.** Instead of logging "user viewed VNM at 14:32:05, 14:32:18, 14:33:01," store a daily summary: `{"date": "2025-07-24", "ticker": "VNM", "view_count": 3, "total_seconds": 45}`.
- **Frontend aggregation:** Batch behavior events in the browser (localStorage or in-memory), send a single summary API call per session close or every 5 minutes. Don't fire an API call per click.
- **Retention policy:** Keep daily aggregates for 90 days, weekly aggregates beyond that. Auto-purge raw data older than 7 days (if stored at all).
- **Separate table with partition:** `behavior_daily` table partitioned by month. Easy to drop old partitions (the project already uses yearly partitioning for `daily_prices`).
- **Connection-conscious writes:** Use a dedicated low-priority write path for behavior data. Don't block price crawling connections.

**Detection:** Monitor table size weekly. If `behavior_daily` exceeds 100K rows, check retention policy.

---

### Pitfall 9: False Confidence from AI's Fluent Reasoning

**What goes wrong:** Gemini provides a beautifully written Vietnamese explanation for why VNM is a great buy: "RSI đang hồi phục từ vùng quá bán, kết hợp với MACD cắt lên..." The reasoning sounds professional and authoritative. Beginner user trusts it completely because they can't evaluate the technical claims. But the reasoning may be generic template text that Gemini applies to any stock with RSI > 30.

**Why it happens:** LLMs are trained to produce fluent, confident text. Gemini doesn't flag uncertainty the way a human analyst would ("I'm not sure about this one"). The existing analysis pipeline already has this risk for the 800-ticker analysis, but daily picks amplify it because they're **prescriptive** ("buy this") rather than **descriptive** ("here's the analysis").

**Consequences:** User develops blind trust in AI recommendations. Doesn't develop their own analytical skills. When the AI is wrong (which will happen regularly), user has no framework to recognize it.

**Prevention:**
- **Confidence score gates with visible thresholds:** Only show picks with combined confidence ≥7. Show the raw confidence score prominently, not just the reasoning text.
- **Counter-argument mandatory:** For every pick, require Gemini to also state the bear case: "Rủi ro: Volume giao dịch thấp, hỗ trợ yếu tại 80,000." The existing dual-direction (long + bearish) pattern from trading signals is perfect for this.
- **Historical accuracy display:** Show "AI picks accuracy last 30 days: 55%." Seeing the actual hit rate prevents blind trust.
- **Educational framing:** Prefix every pick with: "Đây là gợi ý phân tích, không phải lời khuyên đầu tư. Hãy tự nghiên cứu trước khi quyết định." This isn't just legal CYA — it psychologically frames the AI as a tool, not an oracle.
- **Link to raw data:** Each pick should link to the ticker detail page where the user can see the actual chart, indicators, and analysis cards. Encourage verification, not blind follow.

**Detection:** If user trades every pick without visiting the ticker detail page first, the behavior tracker should flag this pattern.

---

### Pitfall 10: Goal Setting That Creates Pressure for Unsafe Behavior

**What goes wrong:** User sets a monthly profit goal of 5M VND. After 3 weeks, they're at 1M. The system shows "Progress: 20% — 1 tuần còn lại." This creates pressure to take larger positions and riskier trades to "catch up," exactly the opposite of safety-first approach.

**Why it happens:** Goal tracking is borrowed from productivity/fitness apps where falling behind schedule means "work harder." In trading, falling behind schedule means "take more risk" — which is destructive.

**Consequences:** User increases position sizes late in the month, takes on trades they wouldn't normally take, compounds losses trying to recover.

**Prevention:**
- **Goals should be process-based, not outcome-based.** Good goals: "Follow my SL rules 100% of the time," "Review every pick before trading," "Max 2 trades per week." Bad goals: "Make 5M VND this month."
- **If P&L goals exist, make them annual, not monthly.** Monthly goals create monthly pressure cycles. Annual goals allow for bad months.
- **No "catch up" framing.** Never show "bạn cần kiếm 4M trong 7 ngày." Instead show: "Tháng này: +1M VND. Trung bình tháng: +1.5M VND." Neutral reporting, not deficit highlighting.
- **Risk review should DECREASE risk after losses, not increase it.** Weekly review that detects losses should suggest: "Giảm size vị thế tuần tới" not "Tăng số lệnh để bù lỗ."
- **Circuit breaker for capital drawdown:** If total capital drops >10% from peak, auto-pause daily picks for 1 week with message: "Tạm nghỉ để đánh giá lại chiến lược."

**Detection:** Track if position sizes increase after losing periods. This is a behavioral red flag.

---

### Pitfall 11: Small Capital Position Sizing Producing Unviable Trades

**What goes wrong:** AI recommends "position_size_pct: 8%" for a pick with entry at 120,000 VND. With 50M VND capital, 8% = 4M VND. 4,000,000 / 120,000 = 33.3 shares. Rounded to lot size of 100 → 0 shares (can't buy less than 100). The pick is unviable but the system doesn't tell the user.

**Why it happens:** Position sizing formulas assume infinite divisibility. VN lot sizes make many small-capital recommendations impossible.

**Consequences:** User either can't trade the pick (frustrating) or buys the minimum 100 shares which is 12M VND = 24% of capital (too concentrated for a "safe" pick).

**Prevention:**
- **Pre-calculate viability for each pick:** `min_investment = entry_price × 100 × (1 + fee_rate)`. If `min_investment > capital × max_position_pct`, mark pick as "Vốn chưa đủ cho mã này."
- **Show actual share count and actual % of capital:** "100 cổ × 120,000₫ = 12,000,000₫ (24% vốn)." Let the user see the real concentration.
- **Prefer lower-priced stocks for small capital:** When generating picks, filter out stocks where 100 shares > 20% of user's capital. With 50M VND, this means stocks under 100,000 VND (100 shares = 10M = 20%).
- **Suggest fractional strategy:** "Với vốn 50M, nên chia 2-3 mã giá dưới 50,000₫ để đa dạng hóa."

**Detection:** If >50% of daily picks fail the viability check for the user's capital, the filtering isn't capital-aware enough.

---

## Minor Pitfalls

---

### Pitfall 12: Database Schema Sprawl from New Feature Tables

**What goes wrong:** v8.0 adds 5+ new tables (daily_picks, trade_journal, behavior_events, strategy_params, goals) to a database that already has tickers, daily_prices (partitioned), technical_indicators, ai_analyses, corporate_events, news_articles, financials, gemini_usage, job_executions, failed_jobs. Alembic migrations become complex. Foreign key relationships between new and existing tables create migration ordering issues.

**Prevention:**
- **Plan all new tables in one migration batch.** Don't add tables one-by-one across phases — migration ordering becomes fragile.
- **New tables should reference `tickers.id`, not `ticker_symbol`.** Follow existing pattern (all existing tables use `ticker_id` FK).
- **JSONB for flexible data:** Store behavior aggregates and strategy parameters as JSONB columns. Avoids schema changes when adding new tracking dimensions.
- **Index strategy upfront:** Journal queries will filter by date range + ticker. Add composite indexes at table creation, not retroactively.

---

### Pitfall 13: Frontend State Complexity from Multiple New Views

**What goes wrong:** Adding 5 new feature areas (picks, journal, behavior, strategy, goals) to the existing Next.js app creates route proliferation and shared state challenges. The journal needs to know about picks (to link trades to picks). Behavior tracking needs to know about journal (to correlate viewing patterns with trading outcomes). Goals need to know about journal P&L.

**Prevention:**
- **Single new route group:** `/dashboard/coach/` with sub-routes: `/picks`, `/journal`, `/review`, `/goals`. Don't scatter across existing routes.
- **Server-side data joining:** Let the API return pre-joined data (pick + journal entry + outcome) rather than making the frontend orchestrate 3 API calls.
- **URL state for filters:** Use URL search params for date ranges, status filters — enables sharing/bookmarking of specific views and avoids hidden state bugs.
- **Avoid global state for coach features.** Each page fetches its own data via React Query. Don't add Zustand stores for coach-specific state.

---

### Pitfall 14: Ignoring VN Market Calendar Edge Cases

**What goes wrong:** T+2 settlement calculation breaks on Lunar New Year (Tết, 5-7 business days off), September 2 National Day, April 30 Reunification Day. Shares bought on the Friday before Tết aren't sellable until the following Tuesday (not Monday, because Monday is still Tết). P&L date ranges and weekly reviews cross holidays incorrectly.

**Prevention:**
- **Start with weekday-only T+2** (skip Saturday/Sunday). Good enough for 95% of cases.
- **Add a `market_holidays` config** — a simple list of dates updated annually. VN market publishes the holiday calendar each December for the following year.
- **Test T+2 calculation explicitly** around known multi-day holidays.

---

### Pitfall 15: Prompt Injection via Journal Notes

**What goes wrong:** The trade journal has a free-text "notes" field. If this text is later included in a Gemini prompt (e.g., "analyze my recent trades and their notes"), a malicious or accidental prompt injection could alter the AI's behavior. Even for single-user, a habit of including special characters or Vietnamese text with certain patterns could confuse the prompt.

**Prevention:**
- **Never include raw user text in Gemini prompts** without sanitization. The existing pattern in `AIQ-03` (sanitize news titles before Gemini) applies here too.
- **Separate user notes from AI context:** When the adaptive strategy analyzes journal data, pass structured fields (ticker, entry, exit, P&L, date) to Gemini, not free-text notes.
- **Max length on notes:** 500 characters. Prevents massive text injection.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **Daily Picks Generation** | Rate limit exhaustion (Pitfall 5), hallucinated tickers (Pitfall 1) | Derive picks from existing analysis data first. If Gemini call needed, pre-filter to 10-15 candidates MAX. Validate every ticker against DB. |
| **Trade Journal** | P&L calculation errors (Pitfall 3), entry timing mismatch (Pitfall 7) | Build `VNMarketRules` utility FIRST, write comprehensive unit tests for fee/tax/lot calculations BEFORE building the journal UI. |
| **Behavior Tracking** | Storage bloat (Pitfall 8), connection pool competition | Frontend aggregation + daily summary tables. Never raw event logging. Batch API calls. |
| **Adaptive Strategy** | Feedback loop (Pitfall 6), survivorship bias (Pitfall 2), small sample overfitting | 20-trade minimum before activation. Track ALL picks (traded and untraded). Hard safety rails that can't be overridden. |
| **Goal Setting & Review** | Unsafe pressure creation (Pitfall 10), position sizing issues (Pitfall 11) | Process goals over outcome goals. No "catch up" framing. Capital drawdown circuit breaker. |
| **AI Pick Display** | False confidence (Pitfall 9), over-trading (Pitfall 4) | Show bear case alongside bull case. Display accuracy metrics. Capital-aware pick count. |
| **Schema Design** | Migration complexity (Pitfall 12), FK ordering | Design all tables together in phase 1. Use JSONB for flexible fields. Follow existing ticker_id FK pattern. |
| **Frontend Integration** | Route/state sprawl (Pitfall 13) | Single `/dashboard/coach/` route group. Server-side data joining. React Query per-page, no new global stores. |

---

## Integration Pitfalls with Existing System

These are specific to ADDING coach features to the existing Holo codebase.

### Integration 1: Scheduler Job Ordering

**Risk:** Daily picks job must run AFTER all 5 analysis types complete (technical, fundamental, sentiment, combined, trading_signal). The existing scheduler uses `EVENT_JOB_EXECUTED` chaining. Adding a 6th job in the chain requires careful wiring.

**Prevention:** Add daily picks as the final job in the existing chain: `crawl_prices → compute_indicators → analyze_technical → ... → analyze_trading_signal → generate_daily_picks`. Don't create a separate schedule — chain it.

### Integration 2: Gemini Model Context Window

**Risk:** If daily picks prompt includes the user's full trade history (20+ trades with notes), the context window fills up. `gemini-2.5-flash-lite` has a large context but token costs scale with input size on free tier.

**Prevention:** Summarize trade history into structured stats (win rate, avg P&L, preferred sectors, avg holding period) and pass the summary to Gemini, not raw trade data. Keep pick generation prompts under 2,000 tokens input.

### Integration 3: Existing Post-Validation Pattern

**Risk:** Daily picks need validation (Pitfall 1), but the existing `_validate_trading_signal()` in `prompts.py` is specific to trading signals (checks long + bearish analysis structure). Copy-pasting and modifying it creates divergent validation logic.

**Prevention:** Extract shared validation functions: `validate_price_bounds(price, current, pct)`, `validate_atr_distance(price, ref, atr, multiplier)`. Both trading signal validation and daily pick validation compose from these primitives.

### Integration 4: Frontend Route Structure

**Risk:** Existing routes are `/`, `/watchlist`, `/dashboard/*`, `/ticker/[symbol]`. Coach features need multiple sub-pages. Adding them at top level (`/picks`, `/journal`, `/goals`) pollutes the navbar.

**Prevention:** Nest under `/dashboard/coach/*` matching the existing `/dashboard/*` pattern. Add a single "Coach" nav item that expands to sub-navigation.

---

## Sources

- **HIGH confidence:** Direct codebase analysis — `app/services/analysis/prompts.py`, `app/schemas/analysis.py`, `app/config.py`, `app/database.py`, `app/scheduler/jobs.py`
- **HIGH confidence:** VN market rules — HOSE trading regulations (lot sizes, price steps, T+2, daily limits, fee structure)
- **HIGH confidence:** Existing Gemini integration patterns — structured output, post-validation, rate limiting, batch processing
- **MEDIUM confidence:** Behavioral finance pitfalls (over-trading, loss aversion, goal pressure) — well-established in trading psychology literature
- **MEDIUM confidence:** LLM hallucination patterns in financial contexts — observed in Gemini and other LLMs when generating specific financial recommendations
- **LOW confidence:** Exact Aiven storage limits for free/small tier — varies by plan, verify actual limits
