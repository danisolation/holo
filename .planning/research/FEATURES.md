# Feature Landscape — v8.0 AI Trading Coach

**Domain:** Personal AI trading coach for Vietnamese stock market beginners (< 50M VND capital)
**Researched:** 2025-07-21
**Overall confidence:** MEDIUM — based on domain knowledge of trading apps (Edgewonk, Tradervue, MarketSmith, Simplize, FireAnt, TCInvest) + existing Holo system analysis. No external search tools available; findings drawn from training data + codebase inspection.

## Context: What Exists vs What's New

### Existing Foundation (already built — DO NOT rebuild)

| Existing Feature | How v8.0 Builds On It |
|------------------|----------------------|
| AI analysis (tech + fundamental + sentiment + combined) across 800+ tickers | Daily Picks engine filters from these scores — picks are a curated subset, not new analysis |
| Trading signals with entry/SL/TP/R:R/position sizing | Picks inherit signal structure — same `TradingPlanDetail` schema for concrete price targets |
| 27 technical indicators (ATR, ADX, Stochastic, pivot, Fibonacci, etc.) | Safety scoring uses volatility (ATR) and trend strength (ADX) to filter risky tickers |
| Real-time WebSocket price streaming (30s polling) | Pick performance tracking — show live P&L for active picks |
| News integration (CafeF) | Educational explanations reference current news to explain "why this stock?" |
| Market overview heatmap, ticker detail pages | Picks link to existing ticker detail — no need for duplicate analysis views |
| Scheduled job pipeline (crawl → indicators → analysis → signals) | Daily Picks generation chains after existing signal pipeline |
| `raw_response` JSONB on `ai_analyses` table | Proven pattern for storing structured AI output — reuse for picks |
| Gemini structured output via Pydantic schemas | Pick generation uses same `google-genai` → Pydantic pattern |
| Job execution tracking + dead letter queue | Pick generation job integrates into existing monitoring |

### What Was Removed (v7.0) — Relevant Context

Portfolio, paper trading, and backtest features were removed. Trade Journal in v8.0 is their **replacement** — simpler, focused on actual trades, not simulation. This is a fresh start, not a migration.

---

## Table Stakes

Features that a personal trading coach MUST have. Without these, the product is just another signal dashboard (which Holo already is).

| Feature | Why Expected | Complexity | Depends On (Existing) | Notes |
|---------|-------------|------------|----------------------|-------|
| **Daily Picks (3-5 stocks/day)** | The core promise. User opens app → sees "buy these today." Without this, there's no "coach." | High | AI analysis scores, trading signals, ticker data, Gemini API | New Gemini prompt that selects top candidates from pre-analyzed pool. NOT re-analyzing 800 tickers — filter from existing scores. |
| **Capital-aware filtering (< 50M VND)** | A beginner with 50M can't buy blue chips at 80K+/share in meaningful quantity. Picks must be buyable. | Medium | Ticker data (price), daily_prices | Filter by price × min lot (100 shares for HOSE). At 50M: max ~500K/share if buying 100 shares. Realistically 2-3 positions. |
| **Safety-first pick scoring** | Beginners lose money from volatility. Coach must prioritize low-risk picks over high-return speculative ones. | Medium | ATR, ADX, volume, fundamental health score | Penalize high-ATR (volatile), low-ADX (no trend), low-volume (illiquid), weak fundamentals. Favor: stable trends, adequate liquidity, solid financials. |
| **Educational explanation per pick** | "Buy VNM" is useless for a beginner. "Buy VNM because RSI bounced off oversold, strong Q4 earnings, sector rotation into consumer staples" teaches. | Medium | All analysis types (tech + fundamental + sentiment), news | Gemini generates Vietnamese explanation combining all dimensions. Max 200-300 words, conversational tone. |
| **Entry/SL/TP per pick** | A coach tells you exactly when to get in, when to cut losses, and when to take profit. Vague "buy" signals are useless. | Low | Trading signal pipeline (already generates these) | Inherit from existing `TradingPlanDetail`. Possibly adjust position_size_pct for small capital. |
| **Trade Journal — log actual trades** | The bridge between "what AI suggested" and "what I actually did." Without this, no learning happens. | Medium | New DB tables | Fields: ticker, direction (buy/sell), price, quantity, date, fees, linked_pick_id (nullable), notes. |
| **Auto P&L calculation** | Manual P&L math is tedious and error-prone. Auto-calculate from buy/sell pairs. | Medium | Trade journal entries, daily_prices for unrealized P&L | Match buy→sell by FIFO. Realized P&L = (sell_price - buy_price) × quantity - fees. Unrealized = current_price vs avg_cost. |
| **Pick history / track record** | "Did yesterday's picks work?" User needs to see historical pick performance to build trust in the AI. | Medium | Daily picks stored with outcomes, daily_prices | Track: pick date, entry hit?, SL hit?, TP hit?, actual return after N days. |
| **Performance summary** | Win rate, total P&L, average R:R — the scoreboard. | Low | Trade journal data, pick outcomes | Aggregate stats from journal + pick tracking. Simple cards, no complex charts needed initially. |
| **Coach dashboard page** | A single page where beginner opens the app and sees: today's picks, recent performance, active trades. | Medium | All above features | New route `/coach` — the primary landing page for v8.0. Replaces the need to navigate between multiple pages. |

---

## Differentiators

Features that transform this from "daily picks app" to "personal trading coach that learns." High value, some technically challenging.

| Feature | Value Proposition | Complexity | Depends On (Existing) | Notes |
|---------|------------------|------------|----------------------|-------|
| **Behavior tracking — viewing patterns** | Track which tickers user browses most, at what times, how long. Reveals unconscious biases (e.g., always looking at bank stocks). | Medium | Frontend event tracking → backend API | Log: ticker views, time-on-page, search queries. Store in new `user_behavior` table. Privacy non-issue (single user). |
| **Behavior tracking — trading habits** | Detect patterns: "sells winners too early," "holds losers too long," "trades impulsively after news." | High | Trade journal with timestamps, pick data | Compare: actual sell time vs optimal exit (TP). Calculate: avg hold time for winners vs losers. Gemini can generate natural-language habit analysis. |
| **Adaptive strategy — risk scaling** | After 3 consecutive losses, AI shifts to more conservative picks. After sustained wins, gradually allows slightly more aggressive picks. | High | Trade journal P&L history, pick generation | Maintain a "risk_level" state (1-5 scale). Recent P&L adjusts it. Risk level feeds into pick generation prompt as context. |
| **Adaptive strategy — sector preference learning** | If user consistently profits from bank stocks and loses on real estate, bias picks toward banks. | Medium | Trade journal with sector data from ticker table | Compute per-sector win rate from journal. Feed top/bottom sectors into pick generation prompt. |
| **Goal setting — monthly profit target** | User sets "I want to make 2M VND this month." App tracks progress. Creates accountability. | Low | Trade journal P&L, new `goals` table | Simple CRUD: target_amount, month, progress_amount (computed). Progress bar on coach dashboard. |
| **Weekly risk tolerance review** | Every Sunday: "Last week you lost 500K. Do you want to: stay the course / reduce risk / take a break?" | Medium | Trade journal, scheduled job, user_settings | Popup/card on coach dashboard. User response adjusts risk_level for next week's picks. Can be a simple 3-option selector, not a chatbot. |
| **Weekly performance review** | AI-generated summary: "This week: 3 trades, 2 wins, +800K. You held VNM 2 days longer than suggested. Consider tighter exits." | Medium | Trade journal, pick data, Gemini API | Gemini generates review from week's data. Store as a weekly report. Displayed on coach dashboard. |
| **Pick-to-trade linkage** | When logging a trade, optionally link it to a daily pick. Enables: "did I follow the pick?" and "how do my deviations perform vs following exactly?" | Low | Trade journal + picks table foreign key | Optional `pick_id` on trade. Analytics: "Trades following picks: 65% win rate. Trades deviating: 40% win rate." |
| **Position sizing for small capital** | Beginner doesn't know how much to buy. AI says "buy 200 shares of XYZ = 12M VND = 24% of your 50M." | Medium | Capital setting, trading signals | Adjust existing `position_size_pct` for absolute VND amounts. Show: "Mua 200 cổ XYZ × 60,000 = 12,000,000 VND (24% vốn)." |
| **"Why not this stock?" explanations** | When a popular stock ISN'T picked, briefly explain why. Prevents FOMO. "HPG not picked today: RSI overbought at 78, wait for pullback." | Medium | AI analysis of non-picked tickers | For top 5-10 "near-miss" tickers, include a 1-sentence rejection reason. Helps beginner learn selection criteria. |

---

## Anti-Features

Features to explicitly NOT build. Each sounds useful but is wrong for a solo beginner with < 50M VND.

| Anti-Feature | Why Avoid | What to Do Instead |
|-------------|-----------|-------------------|
| **Auto-trading / order execution** | Legal risk (no broker API license), financial risk (bugs = real money lost), explicitly out of scope in PROJECT.md. VN brokers don't offer public trading APIs for retail. | Show picks with prices → user manually executes on their broker app (SSI, VnDirect, TCBS). |
| **Complex portfolio analytics** | Removed in v7.0 for good reason. Beginners don't need Sharpe ratios, beta, correlation matrices. Overcomplicates the coaching experience. | Simple P&L, win rate, streak. That's enough for a beginner to learn. |
| **Social features / community** | Single-user app. Social comparison creates FOMO and emotional trading — the exact thing the coach should prevent. | Personal journal with private reflection. |
| **Gamification / badges / XP** | Creates wrong incentives. "Badge for 10 trades this week" encourages overtrading. Beginners should trade LESS, not more. | Celebrate restraint: "You skipped 2 impulsive trades this week — that's discipline." via weekly review. |
| **AI chat / conversational interface** | Massive complexity (conversation state, NLU, context management) for minimal value. A personal coach app isn't a chatbot — it's a structured decision-support tool. | Pre-structured cards and panels. AI generates text content, but UX is widget-based, not conversational. |
| **Intraday / scalping picks** | VN market has T+2.5 settlement. Intraday strategies are irrelevant for a beginner with small capital. Commission per trade (0.15-0.35%) makes frequent trading unprofitable. | Swing (3-15 days) and position (weeks+) timeframes only — already enforced in existing `Timeframe` enum. |
| **Multi-account / family sharing** | Single user, single capital base. Multi-user adds auth, data isolation, RBAC — all explicitly out of scope. | Single user, localStorage + server state as-is. |
| **Notification fatigue (real-time pick alerts)** | Telegram bot was already removed in v7.0. Push notifications for picks encourage impulsive action. Beginner should check picks once at market open, not react to alerts throughout the day. | Coach dashboard shows today's picks. User checks it during their morning routine. No push. |
| **Options / derivatives** | VN retail market has extremely limited derivatives access (VN30F futures only, high margin requirements). Irrelevant for beginner with 50M VND. | Stocks only. |
| **Technical indicator customization** | Beginners don't know what RSI period to use. Letting them customize creates analysis paralysis and false sophistication. | AI uses pre-tuned indicators (already 27 configured). User sees conclusions, not knobs. |
| **Backtesting picks** | Removed in v7.0. Backtesting creates hindsight bias ("I would have bought that!"). Forward performance tracking is more honest and useful. | Track actual pick performance going forward. Show: "Last 30 days, picks had 62% hit rate." |

---

## Feature Dependencies

```
Existing Pipeline (crawl → indicators → analysis → signals)
  │
  ├─→ [NEW] Daily Picks Engine
  │     ├─ Capital-aware filtering
  │     ├─ Safety scoring
  │     ├─ Educational explanation generation
  │     ├─ Entry/SL/TP (inherited from signals)
  │     └─ Pick storage (new table)
  │
  ├─→ [NEW] Trade Journal
  │     ├─ Log trades (buy/sell)
  │     ├─ Auto P&L calculation
  │     ├─ Pick-to-trade linkage (optional FK)
  │     └─ Trade history
  │
  ├─→ [NEW] Pick Performance Tracking
  │     ├─ Monitor active picks vs market prices
  │     ├─ Detect TP/SL hits
  │     └─ Pick track record / history
  │
  ├─→ [NEW] Performance Summary
  │     ├─ Aggregates from journal + picks
  │     └─ Win rate, P&L, streaks
  │
  ├─→ [NEW] Behavior Tracking (depends on journal + frontend events)
  │     ├─ Viewing patterns
  │     └─ Trading habit analysis
  │
  ├─→ [NEW] Adaptive Strategy (depends on journal + behavior + picks)
  │     ├─ Risk level state machine
  │     ├─ Sector preference learning
  │     └─ Feeds back into Pick generation prompt
  │
  ├─→ [NEW] Goal Setting & Review (depends on journal + picks)
  │     ├─ Monthly profit target
  │     ├─ Weekly risk review
  │     └─ Weekly AI-generated performance review
  │
  └─→ [NEW] Coach Dashboard (depends on all above)
        ├─ Today's picks card
        ├─ Active trades card
        ├─ Performance summary
        ├─ Goal progress
        └─ Weekly review card
```

### Critical Path

```
1. Pick Storage Schema + Trade Journal Schema (DB foundation)
   ↓
2. Daily Picks Engine (core feature, generates data for everything else)
   ↓
3. Trade Journal (CRUD for actual trades)
   ↓
4. Pick Performance Tracking (monitors picks against market)
   ↓
5. Coach Dashboard (displays 2 + 3 + 4)
   ↓
6. Behavior Tracking + Adaptive Strategy (requires journal data to exist)
   ↓
7. Goal Setting & Weekly Review (polish layer)
```

---

## Detailed Feature Specifications

### 1. Daily Picks Engine

**What:** Every trading day after the analysis pipeline runs, a new Gemini call selects 3-5 stocks optimized for a beginner with < 50M VND.

**How it works:**
1. Existing pipeline runs: crawl → indicators → analysis → signals (already happens)
2. New job chains after signals: `generate_daily_picks`
3. Job queries today's analysis results: combined score, trading signal confidence, ATR, volume, price
4. Filters: price ≤ 500K (100 shares buyable with 50M budget), volume > 50K/day (liquid), ADX > 20 (has trend), fundamental health ≥ "neutral"
5. Top ~20 candidates sent to Gemini with prompt: "From these pre-analyzed tickers, select 3-5 best for a beginner. Prioritize safety. Explain each pick in Vietnamese."
6. Gemini returns structured response (Pydantic schema)
7. Stored in new `daily_picks` table with JSONB `raw_response`

**New Pydantic schema:**
```python
class DailyPick(BaseModel):
    ticker: str
    pick_reason: str  # Vietnamese, 100-200 words educational
    risk_level: Literal["low", "medium"]  # No "high" for beginners
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size_vnd: int  # Absolute VND, not percentage
    confidence: int  # 1-10
    
class DailyPicksResponse(BaseModel):
    picks: list[DailyPick]
    market_context: str  # Overall market condition today
    avoidance_notes: list[str]  # "Avoid real estate sector today because..."
```

**Gemini API cost:** 1 extra call/day (within 15 RPM free tier — current pipeline uses ~12-13 RPM at peak).

### 2. Trade Journal

**What:** CRUD for logging actual trades the user executes on their broker.

**DB schema (new table `trades`):**
```
id: BigInteger PK
ticker_id: FK → tickers.id
direction: Enum('buy', 'sell')
price: Float
quantity: Integer
total_amount: Float (computed: price × quantity)
fees: Float (default 0)
executed_at: DateTime
pick_id: FK → daily_picks.id (nullable — not all trades follow picks)
notes: Text (nullable)
created_at: Timestamp
```

**P&L calculation:**
- FIFO matching: first buy matched with first sell
- Realized P&L: sell_total - buy_total - total_fees
- Unrealized P&L: (current_price - avg_buy_price) × remaining_quantity
- Uses existing `daily_prices` or real-time WebSocket price for current price

**API endpoints:**
- `POST /api/trades` — log new trade
- `GET /api/trades` — list trades (with filters: date range, ticker, direction)
- `GET /api/trades/summary` — P&L summary (realized, unrealized, win rate)
- `PUT /api/trades/{id}` — edit trade
- `DELETE /api/trades/{id}` — delete trade

### 3. Pick Performance Tracking

**What:** Scheduled job monitors active picks against real market prices.

**Logic:**
- After market close each day, check all active picks (issued within their timeframe window)
- Compare day's high/low against pick's TP and SL
- If high ≥ TP → mark pick as "hit_tp" (success)
- If low ≤ SL → mark pick as "hit_sl" (stopped out)
- If timeframe expired → mark as "expired" with final P&L
- Store outcome on `daily_picks` table: `status` enum (active/hit_tp/hit_sl/expired), `outcome_pct`, `resolved_at`

### 4. Behavior Tracking

**What:** Frontend sends lightweight events; backend aggregates patterns.

**Events tracked:**
- `ticker_view`: user visits `/ticker/[symbol]` — log symbol + timestamp
- `pick_viewed`: user expands a daily pick for details
- `trade_logged`: user logs a trade (already captured via journal)
- `time_on_coach`: how long user spends on `/coach` page

**Storage:** New `user_events` table (event_type, payload JSONB, created_at). Lightweight — no heavy analytics infra.

**Habit analysis (Gemini):** Weekly job queries events + journal, sends to Gemini with prompt: "Analyze this trader's behavior patterns. Identify: impulsive trading, loss aversion, confirmation bias, FOMO. Provide 2-3 specific observations in Vietnamese."

### 5. Adaptive Strategy

**What:** Risk level state machine that adjusts pick aggressiveness.

**State: `risk_level` (1-5 scale)**
- 1 = Ultra-conservative (only "low" risk picks)
- 3 = Balanced (default for new user)
- 5 = Moderate growth (still no "high" risk — beginner constraint)

**Transitions:**
- 3 consecutive losing trades → risk_level decreases by 1
- Week with > 3% portfolio loss → risk_level decreases by 1
- 2 consecutive winning weeks → risk_level increases by 1
- User manually overrides via weekly review → set directly
- Never exceeds 5 (no aggressive mode for beginners)

**How it feeds picks:** Risk level is injected into the daily picks Gemini prompt as context:
- Level 1-2: "Select ONLY stocks with ATR < 2%, strong fundamentals, high liquidity"
- Level 3: "Balance safety and opportunity"
- Level 4-5: "Can include moderately volatile stocks with strong technical setups"

**Storage:** `user_settings` table or simple key-value config. Single value, updated by automated rules + user override.

### 6. Goal Setting & Weekly Review

**What:** User sets monthly profit target; weekly AI-generated review.

**Goal:**
- `goals` table: `id`, `month` (YYYY-MM), `target_amount` (VND), `created_at`
- Progress computed from trade journal P&L for that month
- Displayed as progress bar on coach dashboard

**Weekly Review:**
- Scheduled job runs every Sunday
- Collects: week's trades, pick outcomes, behavior events
- Sends to Gemini: "Generate a weekly trading review for this beginner trader. Be encouraging but honest. In Vietnamese."
- Stored in `weekly_reviews` table (week_start, review_text, stats_json)
- Includes risk tolerance question: "Tuần tới bạn muốn: (1) Giảm rủi ro (2) Giữ nguyên (3) Tăng nhẹ"
- User's answer updates risk_level for adaptive strategy

---

## MVP Recommendation

**Prioritize (Phase 1-3):**
1. **Daily Picks Engine** — this IS the core feature; everything else is secondary
2. **Trade Journal with P&L** — connects picks to reality; minimal but complete CRUD
3. **Pick Performance Tracking** — builds trust in AI; answers "does this actually work?"
4. **Coach Dashboard** — single page that ties 1+2+3 together

**Defer to later phases:**
- **Behavior Tracking:** Needs journal data to exist first. At least 2 weeks of trade data before patterns are detectable. Build after core loop is working.
- **Adaptive Strategy:** Needs pick + journal history. Meaningful after ~1 month of data. Can start with a simple manual risk toggle before implementing the full state machine.
- **Goal Setting & Weekly Review:** Polish feature. The system works without goals. Add after the core coaching loop proves itself.
- **"Why not this stock?" explanations:** Nice-to-have differentiator. Requires additional Gemini calls. Defer unless Gemini rate limit budget allows.

**Build order rationale:** The core coaching loop is: AI picks → user trades → results tracked → AI adapts. Each phase should complete one link in this chain. Don't build adaptive strategy before there's data to adapt on.

---

## Vietnamese Stock Market Constraints (Inform All Features)

| Constraint | Impact on Feature Design |
|-----------|------------------------|
| T+2.5 settlement | No day-trading picks. Minimum hold period is effectively 3 days. Timeframe enum already enforces swing/position only. |
| No short selling (retail) | All picks are BUY only. BEARISH direction in existing signals becomes "avoid" guidance, not actionable picks. |
| Floor/ceiling limits (±7% HOSE, ±10% HNX, ±15% UPCOM) | SL/TP must respect daily price limits. Can't hit 8% SL intraday on HOSE. |
| Lot size: 100 shares (HOSE), 100 shares (HNX), 1 share (UPCOM) | Capital-aware filtering must account for lot sizes. 50M / price / 100 = max lots buyable. |
| Commission: 0.15-0.35% per trade (broker-dependent) | P&L calculation should include configurable fee rate. Default to 0.25%. |
| Market hours: 9:00-15:00 (VN time, UTC+7) | Picks should be ready before 9:00 AM. Generate during post-close pipeline (after 15:00), displayed next morning. |
| Tax: 0.1% on sell transactions | Include in P&L calculations. Sell tax = 0.1% × sell_amount. |

---

## Gemini API Budget Analysis

**Current usage (existing pipeline):**
- Crawl: 0 Gemini calls
- Indicators: 0 Gemini calls
- Technical analysis: ~54 calls (800 tickers / 15 per batch)
- Fundamental analysis: ~54 calls
- Sentiment analysis: ~54 calls
- Combined analysis: ~54 calls
- Trading signals: ~54 calls (batch size 15)
- **Total: ~270 calls/day** (spread across scheduled batches with 4s delays)

**New v8.0 calls:**
- Daily picks generation: **1 call/day** (small — top 20 candidates in one prompt)
- Weekly behavior analysis: **1 call/week**
- Weekly review generation: **1 call/week**
- "Why not" explanations: **1 call/day** (if implemented)
- **Total new: ~2 calls/day + 2/week = negligible**

**Verdict:** v8.0 features add < 1% to Gemini usage. Well within free tier limits. No rate limiting concerns.

---

## Sources & Confidence

| Claim | Source | Confidence |
|-------|--------|------------|
| VN market T+2.5 settlement, no retail short selling | Training data (well-established VN market rules) | HIGH |
| HOSE lot size 100, floor/ceiling ±7% | Training data (standard VN exchange rules) | HIGH |
| Commission range 0.15-0.35% | Training data (typical VN broker fees) | MEDIUM |
| Sell tax 0.1% | Training data (VN stock transaction tax) | HIGH |
| Trade journal feature patterns (Edgewonk, Tradervue) | Training data (domain knowledge of trading journal apps) | MEDIUM |
| Behavior tracking patterns | Training data (general app analytics patterns) | MEDIUM |
| Adaptive strategy concept | Training data (risk management best practices) | MEDIUM |
| Existing Holo codebase analysis | Direct code inspection — schemas, models, APIs | HIGH |
| Gemini API budget analysis | Calculated from existing batch sizes in codebase | HIGH |
| Daily picks as filtered subset (not re-analysis) | Architecture decision based on existing pipeline efficiency | HIGH |
