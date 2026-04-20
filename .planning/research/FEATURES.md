# Feature Landscape — v4.0 Paper Trading & Signal Verification

**Domain:** Paper trading simulation + AI signal quality analytics for Vietnamese stock intelligence platform
**Researched:** 2026-04-21
**Confidence:** HIGH (well-established domain patterns + full codebase analysis of existing signal infrastructure)

**Context:** v3.0 shipped with dual-direction trading signals (LONG/BEARISH), each with `entry_price`, `stop_loss`, `take_profit_1`, `take_profit_2`, `risk_reward_ratio`, `position_size_pct`, `timeframe` (swing/position). Signals stored in `ai_analyses.raw_response` JSONB with `TickerTradingSignal` schema. Existing portfolio has real `Trade`/`Lot` models with FIFO P&L. This research covers ONLY v4.0 new features: **paper trading simulation that auto-tracks AI signals and analytics that verify AI quality**.

---

## Core Insight: This Is a Verification System, Not a Trading Simulator

The primary purpose is **measuring AI quality** — "Are Holo's trading signals actually profitable?" A generic paper trading simulator lets users practice trading. This system has a different goal: every AI signal becomes a testable prediction with a measurable outcome. The analytics answer: "Should I trust confidence=8 signals? Are LONG signals better than BEARISH? Does sector matter?"

This distinction drives every feature decision below. Features that measure AI quality are table stakes. Features that only serve "practice trading" are differentiators or anti-features.

---

## Table Stakes

Features that are **essential** for a paper trading + signal verification system to be useful. Missing any of these = the feature feels broken or pointless.

### Paper Trading Engine

| Feature | Why Essential | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Auto-track all AI signals as virtual trades** | Core purpose — every signal becomes a testable prediction. Without this, verification requires manual tracking | MEDIUM | `ai_analyses` table (raw_response JSONB), scheduler job chain | On each daily signal generation, create a `paper_trade` record for the recommended direction. Entry at `entry_price`, SL/TP from signal. This is the backbone of the entire system |
| **Virtual trade lifecycle: OPEN → partial close → CLOSED** | Signals have TP1 and TP2 — a trade must track partial exits, not just binary win/loss | MEDIUM | Daily price crawl data | States: `OPEN`, `PARTIAL_TP1` (50% closed at TP1), `CLOSED_TP2`, `CLOSED_SL`, `CLOSED_TIMEOUT`, `CLOSED_MANUAL`. State machine driven by daily price checks |
| **Partial TP logic: 50% at TP1, move SL to breakeven** | The existing signal schema has TP1 + TP2 specifically for staged exits — not using them wastes the signal design | MEDIUM | Virtual trade lifecycle | When price hits TP1: close 50% of position, move SL to entry_price (breakeven). Remaining 50% targets TP2 with zero-risk profile. This is the standard institutional approach |
| **Timeout: close at market price when timeframe expires** | Signals have timeframe (swing=3-15 days, position=weeks+). Without timeout, stale trades accumulate forever and pollute analytics | LOW | `timeframe` field from signal, daily price data | Swing: auto-close after 15 trading days. Position: auto-close after 60 trading days. Close at that day's close price. Record as `CLOSED_TIMEOUT` |
| **Configurable virtual capital** | Position sizing uses `position_size_pct` — needs a capital base to calculate share count. Also needed for drawdown/equity curve | LOW | Settings/config | Default: 1,000,000,000 VND (1 billion — realistic VN retail). Stored in settings table or config. Round position to 100-share lots per VN exchange rules |
| **Daily price check job for TP/SL monitoring** | Signals fire once, but TP/SL may hit days later. Must check daily close against all open paper trades | MEDIUM | Daily price crawl, scheduler chain | New scheduler job chained after `daily_price_crawl`. For each open paper trade, check: did today's high ≥ TP1/TP2? Did today's low ≤ SL? Priority: SL checked first (conservative — assumes worst case in same candle) |
| **Win/loss classification** | Binary outcome per trade is the minimum viable metric | LOW | Trade lifecycle | WIN: hit TP1 or TP2. LOSS: hit SL. TIMEOUT: neither hit within timeframe. Partial: hit TP1 but SL'd on remainder (net depends on math) |
| **Basic P&L per trade** | "This signal made/lost X VND" — without per-trade P&L, analytics are meaningless | LOW | Entry price, exit price(s), position size | For partial TP: P&L = (TP1 - entry) × 50% shares + (exit2 - entry) × 50% shares. Track in VND and as % of entry |

### Signal Verification Analytics

| Feature | Why Essential | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Overall win rate** | The single most important metric: "What % of AI signals are profitable?" Without this, the entire system has no point | LOW | Closed paper trades | `win_count / total_closed_count × 100`. Display prominently. A win rate below 40% means signals need tuning; above 55% is strong for any system |
| **Total P&L (realized)** | "Am I net positive or negative following all AI signals?" — the ultimate AI quality metric | LOW | Per-trade P&L summed | Cumulative VND profit/loss across all closed paper trades. Displayed as both absolute VND and % of initial capital |
| **Win rate by direction (LONG vs BEARISH)** | AI may be better at spotting uptrends than downtrends (or vice versa). Must know which direction to trust | LOW | Paper trades with direction field | Separate win rates for LONG and BEARISH signals. In VN bull market, LONG likely outperforms. If BEARISH win rate is terrible, user knows to ignore bearish signals |
| **Average R:R achieved vs predicted** | AI predicts R:R (stored in signal). Actual R:R may differ wildly. This gap measures signal precision | MEDIUM | Predicted R:R from signal, actual entry/exit prices | Predicted R:R from `risk_reward_ratio` field. Actual R:R = actual profit / actual risk taken. If predicted=2.5 but actual=0.8, AI is overestimating targets |
| **Equity curve** | Visual representation of cumulative P&L over time — the most intuitive way to assess if the system is profitable and consistent | MEDIUM | Time-series of trade closings and P&L | X-axis: date. Y-axis: cumulative P&L (starting from initial capital). A rising curve = working system. A declining curve = broken signals. Use Recharts (already in stack) |
| **Max drawdown** | "What was the worst peak-to-trough decline?" — critical for understanding risk even if overall P&L is positive | MEDIUM | Equity curve data | Calculate from equity curve: max(peak - trough) / peak. Display as % and absolute VND. A system with 60% win rate but 40% drawdown is dangerous |
| **AI score correlation: high vs low confidence performance** | The unique value proposition of this system. "Do confidence=8-10 signals outperform confidence=3-5?" If no correlation, the scoring system is broken | MEDIUM | AI confidence scores (1-10) from signal, trade outcomes | Bucket trades by AI confidence: LOW (1-4), MEDIUM (5-7), HIGH (8-10). Compare win rates and avg P&L per bucket. If HIGH confidence doesn't outperform, the entire AI scoring needs recalibration |
| **Telegram notifications on TP/SL hits** | Existing Telegram bot is the primary alert channel. Paper trade events are just as important as real alerts — user needs to know "Signal X just hit TP1" to build trust in the system | LOW | Telegram bot, paper trade lifecycle | Reuse existing `AlertService` pattern. Message: "🎯 [SYMBOL] LONG hit TP1 @ 25,400 (+3.2%). SL moved to breakeven." or "🔴 [SYMBOL] BEARISH hit SL @ 48,200 (-2.1%)" |

---

## Differentiators

Features that elevate from "tracks signals" to "powerful AI quality dashboard." Not expected, but significantly increase insight.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| **Sector analysis** | "AI is great at banking stocks but terrible at real estate" — identifies blind spots in the AI model | MEDIUM | `tickers.sector` field (already exists), closed paper trades | Group win rate and P&L by sector. Bar chart or table. May reveal that AI prompt context is insufficient for certain sectors (e.g., doesn't understand commodity cycles for steel stocks) |
| **Manual paper trade (follow a signal)** | Auto-track captures ALL signals, but user may want to selectively follow specific ones with custom entry/SL/TP | MEDIUM | Paper trade engine, signal data | "Follow" button on trading plan panel. Creates a separate manual paper trade linked to the signal but with user-adjustable entry/SL/TP. Tracks independently. Answers: "Am I better at picking which signals to follow than the AI's own confidence score?" |
| **Calendar heatmap** | Visual pattern recognition: "Are Mondays profitable? Is end-of-month bad?" | MEDIUM | Trade outcomes by date | GitHub-style heatmap grid: rows=weekdays, columns=weeks. Green=profitable day, red=losing day, intensity=magnitude. Uses Recharts or custom SVG. Reveals temporal patterns in AI quality (e.g., signals after earnings season may be stronger) |
| **Streak tracking** | "Current: 5 wins in a row" / "Worst streak: 8 consecutive losses" — gamification + risk awareness | LOW | Ordered trade outcomes | Win streaks, loss streaks, current streak. Displayed as badges/counters. Losing streaks >5 should trigger a visual warning ("AI may be in a weak phase — consider reducing position sizes") |
| **Analysis by timeframe** | "Are swing signals more accurate than position signals?" | LOW | `timeframe` field from signal | Compare win rate: swing vs position. If swing is significantly better, user should weight short-term signals more heavily |
| **Signal outcome history on ticker detail page** | When viewing a ticker, see past signals and whether they hit TP or SL — "LONG signal on Apr 15: TP1 hit ✅, TP2 missed ❌" | MEDIUM | Paper trades linked to tickers, trading plan panel component | Integrates into existing ticker detail page below trading plan panel. List of past 10 signals with outcome icons. Builds confidence: "This ticker's signals are usually accurate" |
| **Monthly/weekly performance summary** | Aggregated performance periods — "This week: 7 wins, 3 losses, +2.1M VND" | LOW | Time-bucketed trade outcomes | Table with rows per week/month. Columns: win rate, P&L, trade count, avg R:R. Useful for spotting trends over time |
| **Drawdown visualization on equity curve** | Shade the drawdown periods on the equity curve chart — visually shows pain periods | LOW | Equity curve + drawdown calculation | Red shading between peak and trough on the Recharts equity curve. Makes risk visceral, not just a number |
| **Profit factor** | `gross_profit / gross_loss` — more nuanced than win rate because it accounts for magnitude | LOW | Per-trade P&L data | Profit factor > 1.5 is solid. > 2.0 is excellent. Combined with win rate, gives complete picture: high win rate + low profit factor = many small wins with rare large losses |
| **Expected value per trade** | `(win_rate × avg_win) - (loss_rate × avg_loss)` — the single number that tells if the system has edge | LOW | Win/loss stats | Positive EV = system has edge. Display in VND. This is the most sophisticated single metric for signal quality |

---

## Anti-Features

Features to explicitly NOT build. Each has a specific reason tied to this system's purpose (AI verification, not general trading practice).

| Anti-Feature | Why Someone Might Want It | Why Avoid | What to Do Instead |
|--------------|--------------------------|-----------|-------------------|
| **Slippage/commission simulation** | "Real trades have fees and slippage" | Adds complexity for marginal accuracy gain. This is a signal verification tool, not a P&L predictor. VN brokerage fees (~0.15-0.25%) are noise compared to TP/SL magnitudes (3-10%). Slippage modeling needs order book data we don't have | Ignore fees in paper trades. Note in UI: "Paper P&L does not include transaction costs (~0.2%)" |
| **Limit/market order types** | "I want to simulate placing a limit order" | Order type simulation requires tick-by-tick data and order book depth. We have daily OHLCV only. Adds massive complexity for no insight into AI quality | All paper entries execute at signal's `entry_price` on the day the close price crosses it (or next open if gap). Simple and sufficient |
| **Manual position sizing override for auto-tracked trades** | "I want to simulate putting more money on high-conviction signals" | Auto-track must be uniform to measure AI quality fairly. If user over-weights favorites, the analytics no longer reflect signal quality — they reflect user judgment | Keep auto-track at fixed position sizing from AI recommendation. Manual paper trades (differentiator above) allow custom sizing for user-judgment testing |
| **Short selling simulation** | "BEARISH signals should simulate short positions" | VN retail cannot short sell (see v3.0 research). Simulating shorts creates a false picture — user can't replicate these trades with real money. Pollutes analytics with unrealizable returns | BEARISH signals track "exit existing position" or "avoided loss by not buying." BEARISH P&L = theoretical loss avoided if user held, NOT short-sale profit |
| **Portfolio rebalancing / allocation optimization** | "Automatically adjust virtual portfolio weights" | This is a portfolio management feature, not a signal verification feature. Scope creep into robo-advisor territory | Virtual capital is simple: each signal gets `position_size_pct` of remaining capital. No rebalancing logic |
| **Backtesting on historical signals** | "Run paper trading on last 6 months of signals" | Explicitly out of scope per PROJECT.md. Backtesting requires careful handling of survivorship bias, look-ahead bias, and is a separate product. Historical signals may have been generated with different prompts/models | Only track forward — signals generated from today onward. Clean and unbiased |
| **Real-time paper trade updates via WebSocket** | "Show me paper trade P&L updating live with 30s price polling" | Adds significant complexity (WebSocket price events → check every open paper trade → broadcast updates). Daily price check is sufficient for swing/position timeframes (3-60 day holding periods) | Daily close-based TP/SL check. Intraday monitoring is false precision for swing/position trades anyway |
| **Multiple virtual accounts / strategies** | "Compare aggressive vs conservative" | Single user, single AI model. Multiple accounts add UI complexity and split analytics. The AI itself doesn't have strategy variants | One virtual account tracks all signals uniformly. User can filter analytics by confidence level to simulate "only follow high-conviction" |

---

## Feature Dependencies

```
FOUNDATION (must build first):
  paper_trades table + model
    → auto-track job (creates paper trades from signals)
    → daily TP/SL check job (updates paper trade status)
      → partial TP logic (50% at TP1, SL→breakeven)
      → timeout logic (close after timeframe expires)

ANALYTICS (requires closed trades):
  trade lifecycle (OPEN → CLOSED)
    → win rate calculation
    → per-trade P&L
      → total P&L
      → equity curve
        → max drawdown
        → drawdown visualization
      → profit factor
      → expected value
    → win rate by direction
    → avg R:R achieved vs predicted
    → AI score correlation

NOTIFICATIONS (parallel with analytics):
  daily TP/SL check
    → Telegram TP/SL notifications (reuse AlertService pattern)

ADVANCED ANALYTICS (requires base analytics):
  base analytics
    → sector analysis (needs enough trades per sector)
    → calendar heatmap (needs date-indexed outcomes)
    → streak tracking (needs ordered outcomes)
    → timeframe analysis (needs both swing and position trades)

MANUAL PAPER TRADING (independent branch):
  paper_trades table + model
    → manual follow API endpoint
    → "Follow" button on trading plan panel

DASHBOARD (requires all analytics):
  all analytics computations
    → paper trading dashboard page
    → signal outcome history on ticker detail
```

---

## Detailed Feature Specifications

### PT-01: Paper Trade Data Model

**New table: `paper_trades`**

```
paper_trades:
  id: BigInteger PK
  signal_id: BigInteger FK → ai_analyses.id  (the signal that triggered this trade)
  ticker_id: Integer FK → tickers.id
  direction: Enum('long', 'bearish')
  source: Enum('auto', 'manual')  -- auto-tracked vs user-followed

  # Entry
  entry_price: Numeric(12,2)  -- from signal's entry_price
  entry_date: Date  -- date signal was generated
  quantity: Integer  -- calculated from virtual capital + position_size_pct, rounded to 100-lot
  position_value: Numeric(15,2)  -- entry_price × quantity

  # Targets (from signal)
  stop_loss: Numeric(12,2)
  stop_loss_current: Numeric(12,2)  -- may change after TP1 hit (moves to breakeven)
  take_profit_1: Numeric(12,2)
  take_profit_2: Numeric(12,2)
  ai_confidence: Integer  -- copied from signal for analytics

  # Status
  status: Enum('open', 'partial_tp1', 'closed_tp1_only', 'closed_tp2', 'closed_sl', 'closed_timeout', 'closed_manual')
  
  # Partial close tracking
  tp1_hit_date: Date | null
  tp1_hit_price: Numeric(12,2) | null
  tp1_pnl: Numeric(15,2) | null  -- P&L on the 50% closed at TP1

  # Final close
  exit_date: Date | null
  exit_price: Numeric(12,2) | null
  exit_reason: String  -- 'tp1', 'tp2', 'sl', 'timeout', 'manual'
  
  # Computed P&L
  realized_pnl: Numeric(15,2) | null  -- total P&L including partial closes
  realized_pnl_pct: Numeric(8,4) | null  -- % return
  predicted_rr: Numeric(6,2)  -- from signal's risk_reward_ratio
  actual_rr: Numeric(6,2) | null  -- computed on close

  # Metadata
  timeframe_days: Integer  -- max days before timeout (swing=15, position=60)
  created_at: Timestamp
  updated_at: Timestamp
```

**Key design decisions:**
- `stop_loss_current` separate from `stop_loss` (original) because it changes after TP1 hit
- `ai_confidence` denormalized from signal for fast analytics queries (avoids joining ai_analyses + parsing JSONB)
- `source` enum distinguishes auto-tracked from manual — critical for comparing "AI picks all" vs "user cherry-picks"
- No FIFO lots needed — paper trades are simple position tracking, not tax accounting

### PT-02: Auto-Track Job

**Scheduler integration:** New job `daily_paper_trade_create` chained after `daily_trading_signal_analysis` via existing `EVENT_JOB_EXECUTED` pattern.

**Logic:**
1. Query today's `ai_analyses` where `analysis_type = 'trading_signal'`
2. For each signal, extract `recommended_direction` from `raw_response` JSONB
3. Get the recommended direction's `TradingPlanDetail` (entry, SL, TP1, TP2)
4. Calculate quantity: `virtual_capital × position_size_pct / 100 / entry_price`, round down to nearest 100
5. Insert `paper_trade` with status='open'
6. Skip if paper trade already exists for this signal_id (idempotency)

**Edge cases:**
- Signal with `score=0` (failed validation): skip — don't track known-bad signals
- Insufficient virtual capital: skip with warning log (shouldn't happen with reasonable sizing)
- Signal already has paper trade (re-run protection): upsert with ON CONFLICT DO NOTHING

### PT-03: Daily TP/SL Check Job

**Scheduler integration:** New job `daily_paper_trade_check` chained after `daily_price_crawl` (needs latest prices).

**Logic for each open paper trade:**
1. Get today's OHLCV for the ticker
2. **SL check first** (conservative — assume worst case):
   - LONG: if `low ≤ stop_loss_current` → SL hit
   - BEARISH: if `high ≥ stop_loss_current` → SL hit (for bearish, SL is above entry)
3. **TP1 check** (if status='open'):
   - LONG: if `high ≥ take_profit_1` → TP1 hit
   - BEARISH: if `low ≤ take_profit_1` → TP1 hit
4. **TP2 check** (if status='partial_tp1'):
   - LONG: if `high ≥ take_profit_2` → TP2 hit
   - BEARISH: if `low ≤ take_profit_2` → TP2 hit
5. **Timeout check**: if `(today - entry_date).business_days > timeframe_days` → timeout

**SL-first priority rationale:** On a volatile day, both SL and TP could be within the candle range. Checking SL first is the conservative assumption (price hit SL before TP). This is standard practice in paper trading systems and avoids overly optimistic results.

**On TP1 hit:**
- Close 50% of position at TP1 price
- Record `tp1_pnl`
- Set `stop_loss_current = entry_price` (breakeven)
- Update status → `partial_tp1`

**On TP2 hit:**
- Close remaining 50% at TP2 price
- Calculate total `realized_pnl = tp1_pnl + tp2_pnl`
- Update status → `closed_tp2`

**On SL hit:**
- If status='open': close 100% at SL → `closed_sl`
- If status='partial_tp1': close remaining 50% at SL (but SL is now breakeven, so remainder P&L ≈ 0) → `closed_sl`

**On timeout:**
- Close remaining position at today's close price
- Calculate P&L at close price
- Update status → `closed_timeout`

### PT-04: BEARISH Direction Handling

**Critical VN market consideration:** BEARISH signals cannot be short-sold. Two possible interpretations for paper trading:

**Recommended approach — "Avoided Loss" tracking:**
- BEARISH paper trade entry = the signal's entry_price (the level the AI says confirms bearish thesis)
- If price drops from entry to TP1 → BEARISH signal was correct → record as WIN with theoretical P&L
- Track as "loss the user would have incurred by buying" → useful for measuring AI's bearish prediction accuracy
- Display differently in UI: "⚠️ Lệnh giả lập — xu hướng giảm (không phải bán khống)"

**Why this works:** The goal is measuring AI quality, not simulating real trades. If the AI says "bearish, price will drop from 25,000 to 23,500" and it does, that's a correct prediction regardless of whether user can profit from it. The analytics answer: "AI correctly identified 65% of bearish scenarios" — valuable for knowing when to avoid buying.

### PT-05: Virtual Capital Management

**Settings:**
```python
# In Settings class or new paper_trading_settings table
paper_trading_capital: int = 1_000_000_000  # 1 billion VND
paper_trading_max_positions: int = 20  # max concurrent open paper trades
paper_trading_auto_track: bool = True  # can be disabled
```

**Capital tracking:**
- Start with initial capital
- On new trade: deduct `position_value` from available capital
- On close: add back `position_value + realized_pnl`
- Track `available_capital` and `invested_capital` separately
- If available capital < minimum position value (e.g., 10M VND), skip auto-tracking with log

### PT-06: Analytics Computation

**Analytics should be computed on-demand, not pre-aggregated** — the dataset is small (maybe 5-20 signals/day × 30 days = 150-600 trades). SQL queries with proper indexes are instant.

**Core metrics (SQL-computable):**
```sql
-- Win rate
SELECT 
  COUNT(*) FILTER (WHERE realized_pnl > 0) AS wins,
  COUNT(*) FILTER (WHERE realized_pnl <= 0) AS losses,
  COUNT(*) AS total
FROM paper_trades WHERE status != 'open';

-- By direction
SELECT direction, 
  COUNT(*) FILTER (WHERE realized_pnl > 0)::float / COUNT(*) AS win_rate
FROM paper_trades WHERE status != 'open'
GROUP BY direction;

-- AI score correlation
SELECT 
  CASE WHEN ai_confidence <= 4 THEN 'low'
       WHEN ai_confidence <= 7 THEN 'medium'
       ELSE 'high' END AS confidence_bucket,
  AVG(realized_pnl_pct) AS avg_return,
  COUNT(*) FILTER (WHERE realized_pnl > 0)::float / COUNT(*) AS win_rate
FROM paper_trades WHERE status != 'open'
GROUP BY 1;
```

**Equity curve:** Requires ordered time-series — query all closed trades ordered by exit_date, compute running sum of realized_pnl.

**Max drawdown:** Computed from equity curve in Python — iterate through equity values, track peak, compute max (peak - current) / peak.

### PT-07: Dashboard Page

**New route: `/dashboard/paper-trading`**

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  PAPER TRADING ANALYTICS                         │
│                                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐│
│  │Win Rate │ │Total P&L│ │Drawdown │ │Trades  ││
│  │  62.3%  │ │+45.2M   │ │ -8.1%   │ │  127   ││
│  └─────────┘ └─────────┘ └─────────┘ └────────┘│
│                                                  │
│  ┌──────────────────────────────────────────────┐│
│  │ Equity Curve (Recharts AreaChart)            ││
│  │ [chart with drawdown shading]                 ││
│  └──────────────────────────────────────────────┘│
│                                                  │
│  ┌──────────────────┐ ┌─────────────────────────┐│
│  │ AI Score vs       │ │ Direction Analysis      ││
│  │ Performance       │ │ LONG: 68% | BEAR: 51%  ││
│  │ [bar chart]       │ │ [comparison bars]       ││
│  └──────────────────┘ └─────────────────────────┘│
│                                                  │
│  ┌──────────────────┐ ┌─────────────────────────┐│
│  │ Calendar Heatmap │ │ Sector Performance      ││
│  │ [green/red grid]  │ │ [horizontal bar chart]  ││
│  └──────────────────┘ └─────────────────────────┘│
│                                                  │
│  ┌──────────────────────────────────────────────┐│
│  │ Recent Paper Trades (table)                   ││
│  │ Symbol | Dir | Entry | Exit | P&L | Status    ││
│  └──────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

---

## VN Market Constraints on Paper Trading

These constraints from v3.0 research carry forward and affect paper trading design:

| Constraint | Impact on Paper Trading |
|------------|------------------------|
| **±7% HOSE daily price band** | SL/TP beyond band cannot trigger intraday. Paper trade check uses daily OHLCV which already accounts for this (high/low are within band). No special handling needed |
| **T+2 settlement** | Irrelevant for paper trading — no real settlement. But timeframe minimum stays at swing (3+ days) per signal design |
| **100-share lot size** | Virtual position quantity must round to nearest 100. `quantity = floor(capital × pct / 100 / entry_price / 100) × 100` |
| **No short selling for retail** | BEARISH paper trades are theoretical tracking, not real short positions. Clearly labeled in UI |
| **Market hours 9:00-14:45** | Paper trade checks run on daily close (after market). No intraday checks needed for swing/position trades |

---

## MVP Recommendation

**Phase 1 (Minimum viable paper trading):**
1. Paper trade data model + migration
2. Auto-track job (creates paper trades from daily signals)
3. Daily TP/SL check job with partial TP logic
4. Basic API endpoints: list paper trades, get summary stats
5. Telegram notifications on TP/SL hits

**Phase 2 (Core analytics dashboard):**
1. Win rate, total P&L, trade count summary cards
2. Equity curve chart
3. Max drawdown calculation
4. Win rate by direction (LONG vs BEARISH)
5. AI confidence correlation chart
6. Paper trading dashboard page

**Phase 3 (Advanced analytics + manual trading):**
1. Sector analysis
2. Calendar heatmap
3. Streak tracking
4. Manual "follow signal" feature
5. Signal outcome history on ticker detail page
6. Profit factor, expected value

**Defer entirely:**
- Slippage/commission: adds false precision for verification purpose
- Real-time paper P&L: daily check is sufficient for swing/position trades
- Historical backtesting: explicitly out of scope
- Multiple virtual accounts: single-user, one account is sufficient

**Rationale for this ordering:**
- Phase 1 creates data (must exist before analytics are possible)
- Phase 2 uses that data (needs ~2 weeks of trades to be meaningful)
- Phase 3 adds depth (needs larger dataset to show statistical patterns)
- Each phase is independently valuable — Phase 1 alone already answers "did the signal hit TP or SL?"

---

## Sources

- **Codebase analysis** (HIGH confidence): Full review of `ai_analyses` model, `TradingPlanDetail`/`DirectionAnalysis`/`TickerTradingSignal` schemas, `Trade`/`Lot` models, scheduler job chaining, `AlertService` notification pattern, `realtime_price_service` market hours logic, frontend components (`trading-plan-panel.tsx`, `performance-chart.tsx`, `holdings-table.tsx`)
- **VN market rules** (HIGH confidence): Carried forward from v3.0 research — ±7% HOSE band, T+2, 100-lot minimum, no retail short selling
- **Paper trading domain patterns** (HIGH confidence — training data): SL-first priority, partial TP with breakeven move, timeframe-based timeout, equity curve + drawdown calculation, profit factor, expected value formulas — these are industry-standard practices used by every paper trading platform (TradingView, Thinkorswim, Interactive Brokers paper mode)
- **Signal verification analytics** (HIGH confidence — training data): AI score correlation analysis, direction-specific performance, sector decomposition — standard patterns for evaluating trading system quality from quantitative finance literature
