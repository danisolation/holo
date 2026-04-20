# Domain Pitfalls — v4.0 Paper Trading & Signal Verification

**Domain:** Paper trading simulation, P&L tracking, and AI signal quality analytics for Vietnamese stock market
**Researched:** 2026-04-21
**Confidence:** HIGH (codebase-verified) / MEDIUM (VN market mechanics — domain knowledge)

---

## Critical Pitfalls

Mistakes that cause fundamentally wrong P&L numbers, broken position tracking, or misleading analytics — leading to wrong conclusions about AI signal quality.

---

### Pitfall 1: SL/TP Fill Price Ambiguity with Daily-Only Data

**What goes wrong:** The system only has end-of-day OHLCV data (crawled after 15:30). When checking if SL/TP was hit, it sees that the day's low breached SL and the day's high breached TP1 — but can't determine which happened first. The position monitoring logic picks one (e.g., TP1) when in reality SL was hit first at market open before the recovery.

**Why it happens:** Intraday price path is invisible with daily bars. A stock might gap down to SL at 09:15, then recover past TP1 by 14:30. Or hit TP1 in the morning session, then crash to SL in the afternoon. The daily bar (O=100, H=110, L=88, C=105) contains both events but not their sequence.

**Consequences:** P&L calculations are systematically biased — likely optimistic since the system may choose the favorable fill. Over hundreds of trades, this completely corrupts the win rate, average R:R, and all AI quality metrics. The analytics become useless for validating AI signal quality, which is the entire point of v4.0.

**Prevention:**
1. **Conservative fill rule (MUST):** When both SL and TP are breached in the same bar, ALWAYS assume SL was hit. This introduces a pessimistic bias, which is the correct bias for signal validation — if the AI signals still look good under pessimistic assumptions, they're genuinely good.
2. **Gap detection:** If the day's open is already past SL (gap down for LONG), fill at the open price, not the SL price. Real trading would fill at the gap price, not the limit.
3. **Priority check order:** Check SL first, then TP2, then TP1 — gives conservative execution ordering.
4. **Record fill type:** Store whether fill was `exact`, `gap_through`, or `ambiguous_bar` so analytics can filter or flag uncertain trades.

**Detection:** Query for paper trades where `fill_type = 'ambiguous_bar'`. If >20% of closed trades are ambiguous, the daily-data limitation is significantly impacting analytics quality. Flag this in the analytics dashboard.

---

### Pitfall 2: Partial Take-Profit State Machine Explosion

**What goes wrong:** The partial TP logic (50% at TP1, move SL to breakeven, 50% at TP2) creates a multi-state position lifecycle that's far more complex than a simple open/closed model. States include: `OPEN → TP1_HIT (50% closed, SL moved) → TP2_HIT (fully closed)` but also `OPEN → SL_HIT`, `OPEN → TP1_HIT → SL_AT_BREAKEVEN_HIT`, `OPEN → TIMEOUT`, `OPEN → TP1_HIT → TIMEOUT`. Each state transition needs different P&L calculations. Developer forgets an edge case → corrupted P&L.

**Why it happens:** Partial TP is straightforward on paper but has combinatorial state transitions when combined with timeouts, gap-throughs, and the ambiguous-bar problem from Pitfall 1. Each transition modifies position quantity AND stop-loss level AND remaining TP targets.

**Consequences:** Silent P&L errors. A position that hit TP1 but then timed out needs P&L = (50% × TP1 profit) + (50% × timeout price profit/loss). Missing the SL-to-breakeven move means the remaining 50% uses the original SL, which overstates losses.

**Prevention:**
1. **Explicit state machine with enum:** Define position states as a clear enum: `PENDING`, `OPEN`, `TP1_HIT`, `CLOSED_TP2`, `CLOSED_SL`, `CLOSED_BREAKEVEN`, `CLOSED_TIMEOUT`, `CLOSED_MANUAL`. Every state transition is a method that validates preconditions.
2. **Immutable trade legs:** Don't modify the position record. Instead, create "trade legs" — the initial open, the TP1 partial close, the final close. Each leg has its own entry/exit price and quantity. Total P&L = sum of leg P&Ls.
3. **"Breakeven" definition:** Breakeven = original entry price, NOT entry + fees. Keep it simple. Fees are accounted for in the final P&L calculation, not in the SL adjustment.
4. **Quantity splitting edge case:** 100-share lot sizes mean 50/50 split is clean (50+50). But if the AI recommends position_size_pct that results in odd lots (e.g., 300 shares → 150+150, but 150 isn't a round lot), decide: paper trading ignores lot constraints OR rounds to nearest 100 (200+100 or 100+200). **Recommendation:** Paper trading ignores lot constraints for simplicity — it's simulation, not real execution. Only apply lot rounding in the initial position sizing.
5. **Unit test every state transition:** Write tests for: open→SL, open→TP1→TP2, open→TP1→breakeven, open→TP1→timeout, open→timeout, open→TP1→gap_through_TP2. Minimum 8-10 test cases per position lifecycle.

**Detection:** Aggregate check: sum of all trade leg P&Ls should equal (exit_value - entry_value - fees) for each position. If they diverge, state machine has a bug.

---

### Pitfall 3: Invalid Signals Creating Ghost Paper Trades

**What goes wrong:** The system auto-tracks ALL AI signals, including those that failed validation (score=0, signal='invalid'). These create paper positions with nonsensical entry/SL/TP prices (e.g., entry price that's 20% away from market) that either never trigger or trigger immediately at a loss. They pollute the analytics with guaranteed-loss trades that unfairly penalize AI quality metrics.

**Why it happens:** The existing pipeline stores invalid signals in `ai_analyses` with `score=0` and `signal='invalid'` (see line 651-653 of `ai_analysis_service.py`). A naive auto-tracking implementation that queries "all trading signals today" would include these.

**Consequences:** Win rate drops artificially. Analytics show "AI score 0 has 0% win rate" which is obvious and useless. Worse, if invalid signals are 10-15% of total, they drag down overall metrics meaningfully.

**Prevention:**
1. **Filter on creation:** Auto-tracking query MUST include `WHERE score > 0 AND signal != 'invalid'`. This is the first line of defense.
2. **Minimum score threshold:** Consider only auto-tracking signals with score ≥ 5 (moderate confidence+). Signals with score 1-4 can be tracked manually if the user chooses. This gives cleaner analytics while still allowing manual exploration.
3. **Track but tag:** Alternatively, track ALL valid signals (score > 0) but tag with `auto_tracked = true` vs `manual = true`. Analytics should default to filtering on auto-tracked only.
4. **Deduplication:** Same ticker + same date + same direction should NOT create duplicate positions. Use a unique constraint: `(ticker_id, signal_date, direction)` on the paper_trades table.

**Detection:** Query `paper_trades` joined with `ai_analyses` where score = 0. Should return zero rows.

---

### Pitfall 4: Gap-Through Fills at Wrong Price

**What goes wrong:** Stock gaps past SL or TP on market open. The system records the fill at the SL/TP price level instead of the actual gap price. Example: LONG position with SL at 95,000. Stock gaps down, opens at 90,000. System records fill at 95,000 (5% loss) but reality would be 90,000 (10.5% loss). For TP scenarios: stock gaps up past TP2, system records at TP2 missing the extra upside.

**Why it happens:** Simple comparison `if low <= stop_loss: fill at stop_loss` ignores that the opening price may already be past the stop level. In VN market, gaps are common due to overnight news, especially for mid/small caps on HNX/UPCOM.

**Consequences:** Systematic overstatement of P&L. SL losses appear smaller than reality. Win rate may be accurate (win/loss determination is correct) but P&L magnitude is wrong. Average loss is understated → risk metrics mislead.

**Prevention:**
1. **Open price check first:** Before checking SL/TP against H/L, check if the day's open already breached the level:
   ```python
   # For LONG position:
   if open_price <= stop_loss:
       fill_price = open_price  # Gap-through, fill at open
   elif low <= stop_loss:
       fill_price = stop_loss   # Normal SL hit
   ```
2. **Apply to ALL exit types:** TP1, TP2, SL, and breakeven SL all need gap-through handling.
3. **VN market context:** HOSE has ±7% daily limit. A stock can only gap down to -7% from yesterday's close. Factor this in — the opening price can't be worse than the floor price. For HNX (±10%) and UPCOM (±15%), wider gaps are possible.

**Detection:** Compare fill prices vs SL/TP levels. Positions where fill_price differs from the target SL/TP by >1% should be flagged as gap-through events.

---

### Pitfall 5: Lookahead Bias in Analytics

**What goes wrong:** Analytics compute metrics using data that wouldn't have been available at signal generation time. Example: "AI signals generated on day D performed well when evaluated using the price movement from D to D+10" — but the position monitoring logic uses the actual close price on day D as the entry, when in reality the trader would enter at next-day's open (day D+1).

**Why it happens:** Signals are generated after market close (15:30+). The close price of day D is known at signal generation time. But the actual paper trade entry should be at day D+1's open (when the trader could first act on the signal). Using day D's close as entry is a subtle lookahead bias because it assumes the trader already had the position before the signal existed.

**Consequences:** Entry prices are systematically better than achievable. In trending markets, this inflates returns. Analytics overstate AI quality.

**Prevention:**
1. **Entry timing rule (MUST):** Paper trade entry = next trading day's open price after signal generation. Signal generated on day D → paper trade opens at day D+1's open price. NOT at day D's close, and NOT at the AI's suggested entry price.
2. **Or, entry at AI's suggested price IF it's within range:** Alternative approach — the AI suggests entry at X. If day D+1's price range [low, high] includes X, fill at X. If the open already gaps past X, fill at open (see Pitfall 4). If price never reaches X within a configurable waiting period (e.g., 2 days), the signal expires unfilled and is tracked as `EXPIRED`.
3. **Be explicit in analytics:** Show "entry timing: next-day open" clearly. This is a design choice that must be documented and consistent.
4. **Weekend/holiday handling:** Signal generated on Friday → entry is Monday's open. Not Saturday. Use trading calendar.

**Detection:** Compare signal generation date vs actual entry date. If entry_date = signal_date, lookahead bias is present.

---

### Pitfall 6: Survivorship Bias from Missing Signals

**What goes wrong:** Analytics only measure signals that were tracked. If the auto-tracking starts on day X, all historical signals before day X are missing. The first few weeks of analytics are based on tiny sample sizes. Worse, if auto-tracking fails silently for some tickers (e.g., UPCOM stocks with no price data), those signals are excluded without notice.

**Why it happens:** Auto-tracking requires both a signal AND a next-day price to open a position. Tickers with crawl failures, suspended tickers, or newly-listed stocks may have signals but no prices. The system silently skips them.

**Consequences:** Analytics are based on a non-random subset of signals. If UPCOM signals (which tend to be lower quality due to illiquidity) are systematically excluded, the reported win rate is inflated.

**Prevention:**
1. **Track signal-to-position conversion rate:** Count total valid signals per day vs positions actually opened. Display "Coverage: 780/800 signals tracked (97.5%)" on the analytics dashboard. If coverage drops below 95%, investigate.
2. **Log skipped signals:** When auto-tracking skips a signal (no price data, ticker suspended, etc.), create a `SKIPPED` record with the reason. Include skipped signals in the denominator for win rate calculations.
3. **Backfill mechanism:** When starting v4.0, DON'T try to backfill historical signals as paper trades. The entry prices would be wrong (see Pitfall 5). Start fresh with a clear "analytics start date."
4. **Suspended stock handling:** If a stock is suspended during a paper position, the position stays OPEN. Don't timeout based on calendar days — timeout based on trading days where the stock actually had prices.

**Detection:** Compare count of `ai_analyses WHERE analysis_type='trading_signal' AND score > 0` vs count of `paper_trades` per date. Large discrepancies = coverage gap.

---

## Moderate Pitfalls

---

### Pitfall 7: VN-Specific P&L Calculation Errors

**What goes wrong:** P&L calculation uses wrong fee structure, ignores selling tax, or uses wrong price units.

**Why it happens:** Vietnamese stock market has unique cost structure:
- **Brokerage fee:** 0.15-0.25% per side (varies by broker, applied to both BUY and SELL)
- **Selling tax:** 0.1% on sell transactions only (thuế bán chứng khoán) — unique to VN
- **No decimal prices:** VN stock prices are in whole VND. HOSE: tick size is 10 VND (price < 10,000), 50 VND (10,000-49,950), 100 VND (≥50,000). HNX: 100 VND. UPCOM: 100 VND
- **Price display:** Usually in 1000s VND (e.g., "25.5" means 25,500 VND), but `daily_prices.close` stores actual VND (25500.00)

**Consequences:** Small per-trade errors compound. A 0.1% selling tax omission on 500 trades = significant P&L distortion. Wrong tick size rounding means entry/SL/TP prices don't match actual executable prices.

**Prevention:**
1. **Configurable fee structure:** Store as settings, not hardcoded: `paper_trade_buy_fee_pct = 0.15`, `paper_trade_sell_fee_pct = 0.15`, `paper_trade_sell_tax_pct = 0.1`. User can adjust for their broker.
2. **P&L formula (LONG):**
   ```
   gross_pnl = (exit_price - entry_price) × quantity
   buy_cost = entry_price × quantity × buy_fee_pct / 100
   sell_cost = exit_price × quantity × (sell_fee_pct + sell_tax_pct) / 100
   net_pnl = gross_pnl - buy_cost - sell_cost
   ```
3. **Don't round prices to tick size in paper trading.** The AI signal already provides approximate prices. Applying tick-size rounding adds complexity without value in simulation. Real portfolio (existing Trade model) can handle this separately.
4. **Store all amounts as Decimal, not float.** The existing `Trade` model uses `Numeric(12, 2)` — paper trades should match.
5. **BEARISH positions P&L:** Since VN doesn't have real short-selling, a BEARISH paper trade is hypothetical. Use simple: `gross_pnl = (entry_price - exit_price) × quantity`. Still apply fees both ways. Make sure analytics clearly label these as "hypothetical short."

**Detection:** Spot-check P&L for a known paper trade manually. Build a test case: BUY 1000 shares at 25,000 VND, SELL at 26,500 VND, fee 0.15%, tax 0.1%. Expected net P&L = 1,500,000 - 37,500 - 66,250 = 1,396,250.

---

### Pitfall 8: Position Timeout Logic with Non-Trading Days

**What goes wrong:** Position timeout uses calendar days instead of trading days. A SWING signal with 15-day timeout opened on a Wednesday before a Vietnamese holiday (e.g., Reunification Day April 30 + May Day May 1, plus the weekend = 5 non-trading days) gets timed out before the stock has actually traded for 15 sessions.

**Why it happens:** Simple `timedelta(days=15)` counts weekends and holidays. VN market has ~10 public holidays per year, some creating 4-5 day non-trading stretches.

**Consequences:** Positions close prematurely on the first trading day after the holiday, often at a random price. Timeframe validation is invalidated — "SWING = 3-15 days" should mean 3-15 trading days.

**Prevention:**
1. **Count trading days from price data:** Don't use calendar math. Count distinct dates in `daily_prices` for the ticker after the entry date. When count ≥ max_days, trigger timeout.
   ```sql
   SELECT COUNT(DISTINCT date) FROM daily_prices
   WHERE ticker_id = :tid AND date > :entry_date
   ```
2. **Timeout ranges by timeframe:**
   - SWING: close after 15 trading days (not calendar days)
   - POSITION: close after 40 trading days (~8 weeks)
3. **Don't timeout on first day check after holiday:** If the position should have timed out during the holiday period (by trading day count), close at the first available close price — which is the correct behavior since no one could have exited during the holiday anyway.
4. **Suspended stocks:** If a stock has 0 trading days for an extended period (suspended), the timeout counter freezes. The position stays open until the stock resumes trading.

**Detection:** Cross-reference timeout dates with VN market holiday calendar. Positions timing out on the day after a long holiday are suspicious.

---

### Pitfall 9: Conflating Paper Trades with Real Portfolio

**What goes wrong:** Paper trading tables and real portfolio tables (existing `trades` + `lots`) share similar schemas. A bug in a JOIN or a wrong table reference mixes paper P&L into real portfolio P&L, or vice versa. The user sees inflated/deflated real portfolio numbers.

**Why it happens:** Existing `Trade` model has `side`, `quantity`, `price`, `trade_date` — which is exactly what a paper trade needs. Temptation to reuse the same table with an `is_paper` flag is strong but dangerous.

**Consequences:** Real portfolio P&L contaminated with simulation data. In a tax context (Vietnam doesn't tax stock gains for individuals currently, but this could change), mixing real and paper data is very bad.

**Prevention:**
1. **Separate tables (MUST):** Paper trades go in `paper_trades` and `paper_trade_legs` (or similar). NOT in the existing `trades` table with a flag. Schema similarity is fine — table separation is non-negotiable.
2. **Separate service:** `PaperTradingService` is a new service class. It does NOT inherit from `PortfolioService`. Shared logic (like P&L calculation) should be extracted into utility functions that both services use, not shared through inheritance.
3. **API namespace:** Paper trading endpoints go under `/api/paper-trading/`, NOT under `/api/portfolio/`. Frontend routing should also separate them.
4. **Database constraints:** `paper_trades.ticker_id` FK references `tickers` (shared), but nothing in `paper_trades` references `trades` or `lots`.

**Detection:** Query for any JOINs between `paper_trades` and `trades`/`lots` in the codebase. Should be zero (except possibly in a comparison analytics view, which should be a read-only query).

---

### Pitfall 10: Connection Pool Exhaustion from Position Monitoring

**What goes wrong:** The daily position monitoring job checks ~800 open positions against daily prices. Each check requires 2-3 queries (get position + get price + update status). With pool_size=5 and max_overflow=3 on Aiven, the monitoring job saturates the connection pool, blocking the daily price crawl and AI pipeline.

**Why it happens:** Existing pipeline is designed for sequential batch operations that hold one connection at a time. Position monitoring adds a parallel workload that runs after price crawl (needs latest prices) and may overlap with the AI analysis chain.

**Consequences:** `TimeoutError` from connection pool exhaustion. Jobs fail. Health alerts fire. The entire daily pipeline is disrupted.

**Prevention:**
1. **Single connection, batch processing:** The monitoring job should fetch ALL open positions in one query, ALL relevant daily prices in one query, compute all updates in-memory, then batch-update in one transaction. NOT one query per position.
   ```python
   # Good: 2 queries total
   positions = await session.execute(select(PaperTrade).where(status='OPEN'))
   prices = await session.execute(
       select(DailyPrice).where(
           DailyPrice.ticker_id.in_(ticker_ids),
           DailyPrice.date == today
       )
   )
   # Process in memory, batch update
   
   # Bad: 800 queries
   for position in positions:
       price = await get_latest_price(position.ticker_id)  # N+1!
   ```
2. **Schedule after price crawl completes:** Chain position monitoring in the job chain AFTER `daily_price_crawl_upcom` (parallel with `daily_indicator_compute`), since it only needs today's prices, not indicators or AI analysis.
3. **Monitor connection usage:** Add connection pool stats to the existing health dashboard. Alert when active connections > 6 (out of 8 max).

**Detection:** Monitor `asyncpg` pool stats. If `pool.get_size()` frequently equals `pool.get_max_size()`, pool pressure is real.

---

### Pitfall 11: Analytics on Insufficient Sample Size

**What goes wrong:** After 2 weeks of paper trading, the analytics dashboard shows "Win rate by AI score" with score=9 having 2 trades and 100% win rate. User concludes "AI score 9 is perfect!" but the sample size is meaningless.

**Why it happens:** Eagerness to show analytics before statistical significance. With ~800 tickers and daily signals, there's volume — but sliced by score (10 buckets), direction (2), timeframe (2), sector (20+), the per-bucket counts become tiny.

**Consequences:** Premature conclusions about AI quality. User adjusts their trading strategy based on noise, not signal.

**Prevention:**
1. **Minimum sample size indicators:** Every metric shows `(n=X)` next to it. Grey out or hide metrics where n < 30 (standard statistical minimum for CLT). Show a warning: "Cần thêm dữ liệu (n < 30)" (need more data).
2. **Confidence intervals:** For win rate, show the 95% confidence interval. Win rate 60% with n=10 has CI [26%, 88%] — which makes the uncertainty clear. With n=100, CI narrows to [50%, 70%].
3. **Time-based gating:** Don't show "AI Score Analysis" until at least 30 days of data. Show a "collecting data" placeholder with a progress bar.
4. **Aggregate first, slice later:** The default analytics view should show overall metrics (all signals combined). Score/sector/direction breakdowns should be secondary tabs that the user navigates to — not the primary view.

**Detection:** Not a bug to detect — a UX/design decision to implement from the start.

---

### Pitfall 12: Equity Curve Distortion from Variable Position Sizes

**What goes wrong:** The equity curve shows cumulative P&L but positions have wildly different sizes (100 shares of a 150,000 VND stock = 15M VND vs 1000 shares of a 5,000 VND stock = 5M VND). A single large-cap trade swings the equity curve by 3x more than a small-cap trade, making the curve dominated by position sizing rather than signal quality.

**Why it happens:** AI recommends `position_size_pct` which varies by confidence. Higher confidence → larger position → more impact on equity curve. The equity curve conflates position sizing quality with signal quality.

**Consequences:** Equity curve and max drawdown are dominated by 2-3 large positions. Analytics mislead about signal quality (a single bad large trade masks 10 good small trades).

**Prevention:**
1. **Normalize by R:** Instead of VND P&L, show profit/loss in "R multiples" where 1R = the initial risk (distance from entry to SL × quantity). A trade that risks 500,000 VND and makes 1,000,000 VND = +2R regardless of position size.
2. **Dual equity curves:** Show both absolute VND P&L and R-normalized P&L. The VND curve shows real capital impact. The R curve shows signal quality independent of sizing.
3. **Per-trade R calculation:**
   ```
   R = abs(entry_price - stop_loss) × quantity
   trade_result_R = net_pnl / R
   ```
4. **Store R at trade open time:** Calculate and store 1R when the position opens. Don't recalculate after — the SL may have moved (breakeven after TP1), but the initial risk defines R.

**Detection:** Variance analysis: if the standard deviation of absolute P&L across trades > 3× the mean, position sizing is dominating the distribution. The R-normalized equivalent should have much lower variance ratio.

---

## Minor Pitfalls

---

### Pitfall 13: Stale Position Status After Missed Price Crawl

**What goes wrong:** The daily price crawl fails for a specific exchange (e.g., HNX). Positions in HNX stocks don't get checked that day. If the stock hit SL on the missed day, the position stays OPEN until the next successful crawl, which may show recovery — resulting in a trade that should have been a loss becoming a win.

**Prevention:**
1. When the next day's prices arrive, backfill the gap: check day-by-day in chronological order, not just the latest price.
2. If multiple days of prices are missing, process them sequentially: day 1 data first (may trigger SL), then day 2 (if still open), etc.
3. The position monitoring job should track `last_checked_date` per position and process all unchecked dates, not just "today."

---

### Pitfall 14: Duplicate Paper Trades from Retry/Rerun

**What goes wrong:** The auto-tracking job runs, creates paper trades for today's signals, then the daily pipeline re-runs (due to a manual trigger or job retry). The job creates duplicate paper trades for the same signals.

**Prevention:**
1. **Unique constraint:** `paper_trades(ai_analysis_id)` — one paper trade per AI analysis record. Use `INSERT ... ON CONFLICT DO NOTHING`.
2. **Idempotency check at job level:** Before creating paper trades, check "are there already paper trades for today's signals?" Skip if yes.
3. **Link to source:** Every paper trade MUST have `ai_analysis_id` FK pointing to the specific `ai_analyses` row that generated it. This also enables the analytics join.

---

### Pitfall 15: Calendar Heatmap Timezone Confusion

**What goes wrong:** The calendar heatmap shows trades on the wrong date because the frontend renders in the user's browser timezone (UTC+7) but the database stores dates in UTC. A trade recorded at 23:30 UTC (which is 06:30 UTC+7 the next day) appears on the wrong day.

**Prevention:**
1. **Use DATE type, not TIMESTAMP, for trade dates.** The existing `Trade.trade_date` uses `Date` — follow the same pattern for paper trades. Date has no timezone ambiguity.
2. **All signal and trade dates are VN market dates.** A signal generated at 15:30 Vietnam time is always dated to that calendar day, regardless of UTC offset.
3. **Frontend: don't convert dates.** When the API returns `"2026-04-21"`, render it as April 21. Don't construct `new Date("2026-04-21")` which JavaScript interprets as midnight UTC and may shift to April 20 in certain renderings. Use date strings directly or a date-only library.

---

### Pitfall 16: Streak Calculation Across Weekends and Holidays

**What goes wrong:** A winning streak counter shows "5-day streak" but 2 of those days were Saturday/Sunday with no trades. The streak is actually 3 trading days. Or worse, a gap day (no signals, no trades) is counted as breaking a streak.

**Prevention:**
1. **Streaks count trading days with trades, not calendar days.** A streak of 5 means 5 consecutive trading days where trades were closed profitably.
2. **Days with no closed trades don't break streaks.** Only a losing trade breaks a winning streak. No-trade days are neutral.
3. **Define clearly:** "Winning streak = consecutive closed trades that were profitable" vs "Winning streak = consecutive trading days where daily P&L was positive." Pick ONE definition and stick with it. The former is simpler and more standard.

---

### Pitfall 17: BEARISH Paper Trades Are Misleading for VN Market

**What goes wrong:** The system creates paper "SHORT" positions for BEARISH signals, tracking P&L as if the user sold short. But VN retail investors can't short sell. Showing "your AI bearish signals made +500,000 VND in hypothetical shorts" creates expectations that can't be realized.

**Prevention:**
1. **Label clearly:** All BEARISH paper trades must be labeled "Giả lập xu hướng giảm" (bearish trend simulation), not "Short position."
2. **Separate analytics:** BEARISH signal performance should be in a separate section from LONG, not mixed into overall P&L.
3. **Alternative framing:** Instead of "BEARISH trade profit," show "Price dropped X% as predicted — LONG entry should be avoided at this level." Frame BEARISH accuracy as "correct avoidance" not "profit from shorting."
4. **Consider not creating BEARISH paper positions at all.** Instead, track BEARISH signal accuracy as "did the price drop below entry within the timeframe?" — binary yes/no without P&L. This avoids the entire synthetic short confusion.

---

### Pitfall 18: Limit Up/Down (Trần/Sàn) Trapping Positions

**What goes wrong:** A stock hits limit down (sàn) — the floor price for the day. In reality, you can't sell at the floor because there are no buyers. The paper trading system records SL hit at the floor price, but in real trading, you'd be trapped unable to exit. Next day, the stock continues falling and hits floor again — multi-day lock-in.

**Why it happens:** Paper trading assumes infinite liquidity. In VN market, limit-down scenarios (especially for small caps) often mean zero liquidity at the floor.

**Prevention:**
1. **Flag but don't block:** When SL fill price equals the floor price, flag the trade as `floor_exit = true`. Analytics can show "X% of exits were at floor price (real liquidity risk)."
2. **Calculate floor/ceiling prices:**
   ```python
   # HOSE: ±7% from reference price
   floor_price = reference_price * 0.93
   ceiling_price = reference_price * 1.07
   ```
3. **Display warning in analytics:** "N trades exited at floor price. In live trading, these exits may not have been possible."
4. **Don't over-engineer:** For paper trading purposes, filling at floor price is acceptable. The flag is sufficient for the analytics consumer. Don't simulate order book depth.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| **Database schema design** | Trying to reuse existing `trades`/`lots` tables for paper trading | Separate `paper_trades` + `paper_trade_legs` tables. Share nothing except `tickers` FK. |
| **Auto-tracking job** | Creating positions for invalid signals (score=0) or duplicate positions on job retry | Filter `score > 0 AND signal != 'invalid'`; unique constraint on `ai_analysis_id`; idempotent job design. |
| **Position monitoring** | N+1 queries per position checking; connection pool exhaustion on Aiven (pool=5+3) | Batch-load all positions + prices in 2 queries; process in memory; single transaction update. |
| **Partial TP implementation** | Wrong P&L when TP1 hit + SL moves to breakeven; ambiguous bars where both TP and SL breach | Explicit state machine enum; immutable trade legs; conservative fill rule (SL wins on ambiguous bars). |
| **P&L calculations** | Missing selling tax (0.1%); wrong fee percentages; float precision drift on VND amounts | Configurable fee/tax settings; use `Decimal` everywhere; include tax in P&L formula. |
| **Timeout logic** | Calendar-day timeout vs trading-day timeout; holiday periods causing premature close | Count trading days from `daily_prices` table; track `last_checked_date` per position. |
| **Analytics dashboard** | Small sample size → misleading metrics; survivorship bias from excluded signals | Show `(n=X)` on all metrics; grey out n < 30; track signal-to-position conversion rate. |
| **Calendar heatmap** | JavaScript Date timezone shift; streak counting across weekends | Use date strings, not Date objects; define streaks as consecutive profitable trades. |
| **Equity curve** | Dominated by position sizing not signal quality; single large trade distorts curve | R-multiple normalization; store initial risk at position open time. |
| **VN market specifics** | Limit up/down trapping; T+2.5 not modeled; gap-through fills at wrong price | Flag floor exits; open-price gap check; entry at next-day open to avoid lookahead. |

---

## Integration Risk Matrix

How v4.0 features interact with existing v3.0 components:

| Existing Component | v4.0 Integration | Risk Level | Notes |
|---|---|---|---|
| `ai_analyses` table | Paper trades FK to this table | LOW | Read-only reference. No schema changes needed. |
| `ai_analysis_service.py` | Auto-tracking reads trading signals after pipeline completes | LOW | Consumer, not modifier. Chain position creation after `daily_trading_signal` job. |
| `scheduler/manager.py` | New monitoring job in chain; new auto-tracking job | MEDIUM | Must chain correctly: signals → auto-track → monitoring runs separately after price crawl. |
| `portfolio_service.py` | Must NOT share code via inheritance; shared utility functions OK | MEDIUM | Extract P&L math into utility module used by both portfolio and paper trading. |
| `daily_prices` table | Position monitoring reads latest prices | LOW | Read-only. Same data already consumed by many services. |
| Connection pool (5+3) | Monitoring job adds parallel read pressure | MEDIUM | Batch queries mandatory. Don't hold connections during computation. |
| Frontend `ticker/[symbol]/page.tsx` | New paper trading panel on ticker detail | LOW | Additive component. No changes to existing panels. |
| Telegram bot | TP/SL hit notifications | LOW | New message type using existing `send_message()` pattern. |
| `tickers` table (exchange column) | Needed for exchange-specific price bands (±7%/±10%/±15%) | LOW | Read-only lookup for floor/ceiling calculation. |

---

## Sources

- `backend/app/services/ai_analysis_service.py` — Invalid signal handling (score=0, signal='invalid'), batch processing pattern, connection pool usage via `AsyncSession`
- `backend/app/services/portfolio_service.py` — Existing P&L calculation pattern, FIFO lot model, N+1 query patterns to avoid
- `backend/app/models/ai_analysis.py` — `raw_response` JSONB storage, `score` and `signal` fields for filtering
- `backend/app/models/trade.py` + `lot.py` — Existing portfolio schema, Decimal usage, Date type pattern
- `backend/app/models/ticker.py` — Exchange column for price band determination
- `backend/app/models/daily_price.py` — OHLCV columns, yearly partitioning, `Numeric(12,2)` precision
- `backend/app/scheduler/manager.py` — Job chain pattern, `_on_job_executed` listener, pool_size considerations
- `backend/app/config.py` — Aiven PostgreSQL pool_size=5/max_overflow=3, timezone Asia/Ho_Chi_Minh
- `backend/app/schemas/analysis.py` — `Timeframe` enum (SWING/POSITION), `Direction` enum, validation constraints
- VN market mechanics (T+2.5, ±7%/±10%/±15% price bands, 0.1% selling tax, lot sizes, trading hours) — MEDIUM confidence, domain knowledge
- Price step rules (HOSE: 10/50/100 VND by price bracket; HNX/UPCOM: 100 VND) — MEDIUM confidence, domain knowledge
- VN holiday calendar impact on trading days — domain knowledge, verify specific dates annually
