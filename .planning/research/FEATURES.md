# Feature Landscape — v3.0 Smart Trading Signals

**Domain:** Stock Intelligence Platform — Dual-Direction Trading Plans with Full Entry/Exit Strategy
**Researched:** 2026-04-21
**Confidence:** HIGH (codebase analysis) / MEDIUM (VN market short-selling rules — domain knowledge, not verified against 2026 regulations)

**Context:** v1.0–v2.0 shipped with: 800+ tickers across HOSE/HNX/UPCOM, 12 technical indicators + Gemini AI scoring (technical/fundamental/sentiment/combined), CafeF news, mua/bán/giữ recommendations with confidence 1-10 and Vietnamese explanation, Telegram bot alerts, Next.js dashboard with candlestick charts + indicator overlays, portfolio tracking with FIFO P&L, real-time WebSocket price streaming. This research covers ONLY v3.0 NEW features: upgrading from simple buy/sell/hold to **full trading plans with dual-direction LONG/SHORT analysis**.

---

## Vietnamese Stock Market Rules Affecting Trading Plans

These rules **directly constrain** what trading plan features are possible and how they must be designed. Every feature below was evaluated against these constraints.

### Price Band Limits (Biên độ dao giá)
| Exchange | Daily Limit | Impact on Trading Plans |
|----------|-------------|------------------------|
| HOSE | ±7% from reference price | Stop-loss and take-profit CANNOT exceed ±7% in a single day. Multi-day TP targets are valid but intraday SL may not trigger if price hits floor/ceiling |
| HNX | ±10% from reference price | Wider bands = more room for intraday targets |
| UPCOM | ±15% from reference price | Widest bands, but lowest liquidity |

**Implication:** Trading plan targets must be labeled as "multi-session targets" when they exceed the daily price band. A stop-loss at -10% on HOSE requires 2+ sessions to hit — the system must warn the user that SL is NOT guaranteed intraday.

### Settlement Rules (T+2)
- **All exchanges:** T+2 settlement (as of VSD regulation, effective from 2022)
- Buy on Monday → shares settle on Wednesday → can sell from Wednesday
- **Implication for SHORT direction:** Even if a bearish signal fires, an investor who just bought cannot exit for 2 trading days. The trading plan's "SHORT" scenario must be framed as "AVOID BUYING" or "THOÁT (exit existing position)" — not as "short sell"

### Trading Sessions
| Session | Time (ICT) | Notes |
|---------|-----------|-------|
| ATO (Mở cửa) | 9:00–9:15 | Opening auction — volatile, not ideal for limit entries |
| Continuous 1 | 9:15–11:30 | Main morning session |
| Lunch break | 11:30–13:00 | No trading |
| Continuous 2 | 13:00–14:30 | Afternoon session |
| ATC (Đóng cửa) | 14:30–14:45 | Closing auction |

**Implication:** Timeframe recommendation must account for these sessions. "Scalp" is essentially impossible with T+2. Swing (days-weeks) and Position (weeks-months) are the realistic timeframes.

### Short Selling Reality in Vietnam
- Securities Borrowing and Lending (SBL) exists since 2017, but **extremely limited**:
  - Very few securities are eligible (typically only top-30 large caps)
  - Very few brokers offer SBL to retail (TCBS, SSI partially)
  - Retail participation is negligible — most VN traders have never short-sold
  - Margin interest for SBL: ~10-14% annually
- **Critical design decision:** The "SHORT" direction in dual-analysis does NOT mean "short sell." It means:
  1. **For non-holders:** "Tránh mua — avoid entry, wait for lower prices"
  2. **For holders:** "Thoát — exit/reduce position at these levels"
  3. **Bearish scenario awareness:** "If price drops, these are the key levels"

### Lot Size
- Minimum order: 100 shares on HOSE/HNX (odd lots possible on some brokers at worse pricing)
- **Implication for position sizing:** Must round to nearest 100 shares

### Margin Trading
- Maximum ratio: typically 50% (broker-dependent)
- Margin call: ~130% maintenance ratio
- Force sell: ~120%
- **Implication:** Position sizing calculator should assume cash account by default, with optional margin toggle

---

## Table Stakes

Features that ANY trading plan feature must include. Missing these = the upgrade from mua/bán/giữ feels incomplete or amateurish.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Entry price/zone** | "Mua" without a price is useless — every trading plan needs a specific entry | MEDIUM | Gemini must output specific VND price or price range based on support levels and latest close. Must reference actual price data, not hallucinate numbers |
| **Stop-loss level** | Core risk management — any platform suggesting trades without SL is irresponsible | MEDIUM | Must be below entry for LONG, above entry for SHORT-awareness. Must warn when SL exceeds daily price band (±7% HOSE) |
| **Take-profit target (T1)** | Minimum one exit target to complete the plan | MEDIUM | At least one TP level. Based on resistance levels, Fibonacci, or round-number psychology |
| **Risk/reward ratio** | Traders evaluate plans by R:R — standard metric | LOW | Pure calculation: `(TP - Entry) / (Entry - SL)`. Display as "1:X" format. Minimum threshold: highlight R:R < 1:1.5 as unfavorable |
| **Preferred direction** | Must explicitly state LONG or SHORT (tránh mua) preference | LOW | Replaces current mua/bán/giữ with richer signal. Maps to: LONG=mua, SHORT=tránh/thoát, NEUTRAL=giữ/chờ |
| **Direction confidence** | Existing system has confidence 1-10; must carry forward | LOW | Reuse existing confidence rubric. Split into LONG confidence + SHORT confidence, not just one number |
| **Vietnamese reasoning** | Existing combined analysis has Vietnamese explanation; trading plan must too | LOW | Extend current pattern. Reasoning should explain WHY these specific levels, not just repeat numbers |
| **Timeframe recommendation** | "Buy" without "hold for how long" is incomplete | LOW | Enum: swing (2-10 ngày), position (2-8 tuần), trung_han (2-6 tháng). No "scalp" — T+2 makes it impractical |
| **Trading plan panel on ticker detail** | Natural location — user is already viewing the ticker | MEDIUM | New component below existing CombinedRecommendationCard. Must show both LONG and SHORT scenarios side by side |
| **Gemini structured output schema** | Existing Pydantic schema pattern must extend to trading plan | MEDIUM | New `TradingPlanResponse` Pydantic model with nested LONG/SHORT plans. Uses existing `response_schema` pattern in `_call_gemini()` |

## Differentiators

Features that elevate from "has a trading plan" to "has a **good** trading plan."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Multiple take-profit targets (T1, T2, T3)** | Professional plans have staged exits — "take 50% at T1, 30% at T2, hold 20% to T3" | LOW | Just 3 price fields in Pydantic schema. Partial profit-taking percentages as Gemini output |
| **Position sizing calculator** | Answers "How many shares should I buy?" based on risk tolerance + account size | MEDIUM | User inputs account size + risk % (e.g., 2%). Formula: `shares = (account × risk%) / (entry - SL)`. Round to 100-share lots. Display as VND amount + share count |
| **Key levels overlay on chart** | Visualize entry/SL/TP directly on the candlestick chart | MEDIUM | lightweight-charts supports `addPriceLine()` — horizontal lines at entry (blue), SL (red), TP (green). Most impactful visual feature |
| **Price-band-aware warnings** | Alert when SL/TP exceeds daily price band limit | LOW | If `abs(target - reference) / reference > band_limit`, show warning: "⚠️ Mức này vượt biên độ ngày, cần ≥2 phiên" |
| **Trade plan invalidation conditions** | When to CANCEL the plan (not just SL) — e.g., "Plan invalid if price closes below X" | LOW | Gemini outputs an `invalidation` text field describing conditions that void the thesis |
| **Telegram trading plan alert** | Enhanced Telegram signal with full entry/SL/TP instead of just mua/bán/giữ | LOW | Extend existing `signal_change()` formatter. New format includes price levels |
| **Dual-direction side-by-side display** | Show LONG and SHORT scenarios simultaneously so trader sees both perspectives | MEDIUM | Two-column layout on desktop, stacked on mobile. Green card (LONG) + Red card (SHORT) with preferred direction highlighted |
| **Historical plan tracking** | "Did the last plan's TP hit? Was SL triggered?" — track plan outcomes | HIGH | Requires comparing past plan's entry/SL/TP with subsequent price data. Adds credibility but complex to implement correctly |

## Anti-Features

Features to explicitly NOT build. Each has a concrete reason tied to VN market reality.

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| **Short selling execution guidance** | "Dual-direction means I can short sell" | Short selling barely exists in VN retail — SBL covers <30 stocks, <5% of brokers offer it, regulatory barriers | Frame SHORT as "avoid/exit/wait" with specific levels. Label clearly: "Kịch bản giảm giá (không phải bán khống)" |
| **Auto-trade / order placement** | "If the plan says buy at X, place the order for me" | Legal risk (unlicensed advisory), financial risk (slippage, gaps), already explicitly out of scope | Trading plan is informational only. Clear disclaimer: "Chỉ mang tính tham khảo, không phải khuyến nghị đầu tư" |
| **ML price prediction for targets** | "Use machine learning to predict exact entry/SL/TP" | Creates false precision. ML predictions for VN stocks lack sufficient training data and market-making dynamics differ from US/EU markets | Gemini qualitative analysis based on technical levels (support/resistance) + fundamentals. Honest about uncertainty |
| **Real-time scalp signals** | "Give me intraday buy/sell signals" | T+2 settlement makes true scalping impractical. 30s polling latency too high for scalp timing. Creates gambling behavior | Minimum timeframe = swing (2-10 days). System explicitly doesn't support intraday trading signals |
| **Guaranteed R:R claims** | "This trade has 1:3 R:R guaranteed" | R:R is a *plan*, not a guarantee. Stop-loss can gap through. Price bands prevent intraday SL execution beyond ±7% | Display R:R as "Tỷ lệ lợi nhuận/rủi ro dự kiến" (expected), never "guaranteed" |
| **Backtesting engine for plans** | "Show me how past plans would have performed" | Backtesting is a separate product — requires survivorship bias handling, transaction cost modeling, slippage simulation. Massive scope | Simple "plan outcome" tracking: after plan date, check if TP1/SL was hit first. Binary outcome, not full backtest |
| **Options/derivatives strategies** | "Add covered call or put strategies" | VN derivatives market is limited to VN30 index futures + covered warrants. Retail options trading doesn't exist | Stay focused on stock trading plans only. No derivative integration |
| **Personalized risk profiles** | "Different plans for aggressive vs conservative traders" | Single user, adds complexity. Gemini would need multiple prompts per ticker × profile | Single plan with configurable position sizing. User adjusts risk% in calculator (1% conservative, 3% aggressive) |

---

## Detailed Feature Specifications

### SIGNAL-01: Dual-Direction Analysis (LONG + SHORT)

**Current state (what changes):**
- Current: `CombinedBatchResponse` → `recommendation: mua/ban/giu`, `confidence: 1-10`, `explanation: str`
- New: For each ticker, Gemini produces BOTH a LONG thesis and a SHORT thesis, then recommends the preferred direction

**Dual-direction output structure:**
```python
class DirectionPlan(BaseModel):
    """One direction's trading plan."""
    direction: Literal["long", "short"]
    conviction: int = Field(ge=1, le=10)
    entry_price: float = Field(description="Recommended entry price in VND")
    stop_loss: float = Field(description="Stop-loss price in VND")
    take_profit_1: float = Field(description="First take-profit target in VND")
    take_profit_2: float | None = Field(description="Second take-profit target")
    take_profit_3: float | None = Field(description="Third take-profit target")
    timeframe: Literal["swing", "position", "trung_han"]
    reasoning: str = Field(description="Vietnamese explanation, 2-3 sentences")
    invalidation: str = Field(description="Condition invalidating this plan, 1 sentence Vietnamese")

class TickerTradingPlan(BaseModel):
    """Complete dual-direction trading plan for one ticker."""
    ticker: str
    preferred_direction: Literal["long", "short", "neutral"]
    long_plan: DirectionPlan
    short_plan: DirectionPlan
    risk_reward_ratio: float = Field(description="R:R for preferred direction")
    key_support: float = Field(description="Key support level in VND")
    key_resistance: float = Field(description="Key resistance level in VND")
    summary: str = Field(description="Vietnamese overall summary, max 100 words")

class TradingPlanBatchResponse(BaseModel):
    """Batch response for trading plan analysis."""
    plans: list[TickerTradingPlan]
```

**What "SHORT" means in VN context (critical framing):**
- LONG plan: "Kịch bản TĂNG — nếu giá tăng, đây là điểm mua và chốt lời"
- SHORT plan: "Kịch bản GIẢM — nếu giá giảm, đây là mức cần thoát/tránh mua"
- SHORT.entry_price = "Level where bearish thesis confirms" (not "price to short sell at")
- SHORT.stop_loss = "Level where bearish thesis is wrong (price goes up instead)"
- SHORT.take_profit = "Level where price might find support (potential re-entry for longs)"

**Dependencies:** Existing combined analysis pipeline (AI-04), technical context gathering (_get_technical_context), fundamental context, sentiment context.

### SIGNAL-02: Gemini Prompt Restructure for Trading Plans

**Current prompt flow:**
1. `COMBINED_SYSTEM_INSTRUCTION` → "Bạn là chuyên gia tư vấn đầu tư chứng khoán Việt Nam"
2. `COMBINED_FEW_SHOT` → Example with mua/ban/giu output
3. `_build_combined_prompt()` → Feeds tech/fund/sent scores per ticker
4. `CombinedBatchResponse` → Validates output

**New prompt flow (replaces combined analysis):**
1. New `TRADING_PLAN_SYSTEM_INSTRUCTION` — senior trading advisor persona, outputs both LONG and SHORT plans with specific VND prices
2. New `TRADING_PLAN_FEW_SHOT` — example with dual-direction output including entry/SL/TP in VND
3. Extended context gathering: include latest_close, recent high/low, support/resistance from BB and MAs, volume context
4. `TradingPlanBatchResponse` — Pydantic structured output

**System instruction design:**
```
Bạn là chuyên gia giao dịch chứng khoán Việt Nam (HOSE/HNX/UPCOM). 
Cho mỗi mã, phân tích CẢ HAI kịch bản TĂNG và GIẢM:

LONG (Tăng): entry price, stop-loss, take-profit targets cụ thể bằng VND
SHORT (Giảm): mức giá xác nhận xu hướng giảm, mức thoát lỗ, mức hỗ trợ tiềm năng

Quy tắc:
- Entry/SL/TP phải dựa trên dữ liệu kỹ thuật (hỗ trợ, kháng cự, MA, BB)
- Lưu ý biên độ ngày: HOSE ±7%, HNX ±10%, UPCOM ±15%
- SHORT không phải bán khống — là kịch bản để TRÁNH MUA hoặc THOÁT vị thế
- Timeframe: swing (2-10 ngày), position (2-8 tuần), trung_han (2-6 tháng)
- Risk/reward ratio tối thiểu 1:1.5 cho preferred direction
```

**Few-shot example design:**
```
--- VNM ---
Giá hiện tại: 82,000 VND
Kỹ thuật: signal=buy, strength=7
Cơ bản: health=good, score=8
Tâm lý: sentiment=positive, score=7
SMA(20): 80,500 | SMA(50): 78,000 | BB Upper: 85,000 | BB Lower: 79,000
RSI: 52.1 (neutral) | MACD: bullish crossover
High 20D: 84,500 | Low 20D: 78,500

Output:
{
  "ticker": "VNM",
  "preferred_direction": "long",
  "long_plan": {
    "direction": "long",
    "conviction": 7,
    "entry_price": 81000,
    "stop_loss": 78000,
    "take_profit_1": 85000,
    "take_profit_2": 88000,
    "take_profit_3": null,
    "timeframe": "swing",
    "reasoning": "RSI tăng từ vùng trung tính với MACD vừa cắt lên. Giá trên tất cả MA chính...",
    "invalidation": "Kế hoạch không còn hiệu lực nếu giá đóng cửa dưới SMA(50) = 78,000"
  },
  "short_plan": { ... },
  "risk_reward_ratio": 1.33,
  "key_support": 78000,
  "key_resistance": 85000,
  "summary": "Xu hướng tăng ngắn hạn với momentum tích cực..."
}
```

**Token budget impact:**
- Current combined analysis: ~100-150 tokens output per ticker
- Trading plan: ~400-600 tokens output per ticker (3-4× more)
- At batch_size=25: output goes from ~3,750 to ~15,000 tokens per batch
- **Mitigation:** Reduce batch_size to 10-15 for trading plan analysis, OR run trading plan as a SEPARATE analysis type (not replacing combined, but extending it)
- Gemini 2.5-flash-lite max_output_tokens=16384 — sufficient for 15 tickers × 600 tokens

**Dependencies:** Existing Gemini call infrastructure (`_call_gemini`, `_run_batched_analysis`), existing context gatherers, Pydantic response_schema pattern.

### SIGNAL-03: Extended Context for Price-Level Targets

**Current technical context (from `_get_technical_context`):**
- RSI(14) last 5 days, RSI zone
- MACD line/signal/histogram last 5 days, crossover state
- SMA(20/50/200), EMA(12/26), BB(upper/middle/lower)
- Latest close price, price vs SMA percentages

**Additional context needed for entry/SL/TP generation:**
```python
# New fields to add to technical context
{
    "high_20d": float,        # 20-day high (resistance proxy)
    "low_20d": float,         # 20-day low (support proxy)
    "high_52w": float,        # 52-week high
    "low_52w": float,         # 52-week low
    "avg_volume_20d": float,  # Average volume (for conviction)
    "latest_volume": float,   # Today's volume vs average
    "atr_14": float,          # Average True Range for volatility-based SL
    "exchange": str,          # For price band awareness (HOSE=7%, HNX=10%, UPCOM=15%)
    "price_band_pct": float,  # Specific band for this exchange
}
```

**ATR for stop-loss sizing:**
- ATR(14) = Average True Range over 14 days
- Common SL formula: `entry - 1.5 × ATR` (for LONG), `entry + 1.5 × ATR` (for SHORT awareness)
- `ta` library already installed — `AverageTrueRange(high, low, close, window=14)`
- New column in `technical_indicators` table: `atr_14`

**20-day high/low from daily_prices:**
```python
# Query last 20 trading days
high_20d = max(close values over last 20 days)
low_20d = min(close values over last 20 days)
# Already have DailyPrice data — just need to query it
```

**Dependencies:** `ta` library (already installed), `daily_prices` table, `technical_indicators` table (needs ATR column via Alembic migration).

### SIGNAL-04: Trading Plan Dashboard Panel

**Current ticker detail page layout:**
1. Ticker header (name, exchange, price, watchlist toggle)
2. Candlestick chart section
3. Indicator charts section (RSI, MACD)
4. Separator
5. CombinedRecommendationCard (mua/bán/giữ + confidence + reasoning)
6. Analysis cards grid (technical, fundamental, sentiment)

**New layout — add Trading Plan panel:**
1. Ticker header *(unchanged)*
2. Candlestick chart with key level overlays (entry/SL/TP lines) ← **enhanced**
3. Indicator charts *(unchanged)*
4. Separator
5. **NEW: TradingPlanCard** — prominent dual-direction panel replacing CombinedRecommendationCard
6. Analysis cards grid *(unchanged, still shows technical/fundamental/sentiment)*

**TradingPlanCard component design:**

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 KẾ HOẠCH GIAO DỊCH — VNM            ← Swing (2-10 ngày) │
│                                                             │
│  ★ HƯỚNG GỢI Ý: LONG (MUA)  ●●●●●●●○○○  7/10              │
│  "Xu hướng tăng ngắn hạn với momentum tích cực từ MACD..."  │
│                                                             │
│ ┌──────── LONG (Tăng) ────────┐ ┌──────── SHORT (Giảm) ─────┐│
│ │ Conviction: ●●●●●●●○○○ 7   │ │ Conviction: ●●●○○○○○○○ 3  ││
│ │                             │ │                            ││
│ │ 🟢 Entry:    81,000 VND     │ │ 🔴 Entry:    78,000 VND    ││
│ │ 🔴 Stop-Loss: 78,000 VND   │ │ 🟢 Stop-Loss: 82,000 VND  ││
│ │ 🎯 TP1:      85,000 VND    │ │ 🎯 TP1:      75,000 VND   ││
│ │ 🎯 TP2:      88,000 VND    │ │ 🎯 TP2:      72,000 VND   ││
│ │ R:R:         1:1.3          │ │ R:R:         1:1.5         ││
│ │                             │ │                            ││
│ │ "RSI tăng từ vùng trung    │ │ "Nếu giá phá vỡ SMA50,   ││
│ │  tính, MACD cắt lên..."    │ │  xu hướng giảm xác nhận.."││
│ │                             │ │                            ││
│ │ ⚠️ Hủy nếu: Giá đóng cửa  │ │ ⚠️ Hủy nếu: Giá vượt      ││
│ │ dưới SMA(50) = 78,000      │ │ BB Upper = 85,000          ││
│ └─────────────────────────────┘ └────────────────────────────┘│
│                                                             │
│ 📐 Hỗ trợ: 78,000 | Kháng cự: 85,000                       │
│ 📅 Cập nhật: 2026-04-21 | gemini-2.5-flash-lite             │
│                                                             │
│ ⚠️ Chỉ mang tính tham khảo, không phải khuyến nghị đầu tư    │
└─────────────────────────────────────────────────────────────┘
```

**Key design decisions:**
- **Two-column on desktop, stacked on mobile** — use Tailwind `grid grid-cols-1 md:grid-cols-2`
- **Preferred direction highlighted** — border-2 on the preferred side, muted on the other
- **Color coding:** Green border for LONG card, Red border for SHORT card
- **Always show both** — even when one direction has low conviction. This is the point of dual-direction analysis
- **Disclaimer required** — Vietnamese regulatory context requires advisory disclaimer

**Dependencies:** Existing ticker detail page, existing Card/Badge shadcn components, trading plan API endpoint.

### SIGNAL-05: Position Sizing Calculator

**Formula:**
```
risk_amount = account_size × risk_percentage
price_risk = entry_price - stop_loss_price  (for LONG)
raw_shares = risk_amount / price_risk
position_shares = floor(raw_shares / 100) × 100  # Round to VN lot size
position_value = position_shares × entry_price
```

**Example:**
```
Account: 100,000,000 VND
Risk: 2% → risk_amount = 2,000,000 VND
Entry: 81,000 VND, SL: 78,000 VND → price_risk = 3,000 VND
raw_shares = 2,000,000 / 3,000 = 666.67
position_shares = 600 (rounded to nearest 100)
position_value = 600 × 81,000 = 48,600,000 VND (48.6% of account)
```

**UI component:**
```
┌─────────────────────────────────────┐
│ 💰 TÍNH VỊ THẾ                      │
│                                     │
│ Vốn tài khoản: [___100,000,000___] VND │
│ % Rủi ro/lệnh: [___2%___]           │
│                                     │
│ → Rủi ro tối đa: 2,000,000 VND      │
│ → Số lượng: 600 cổ phiếu             │
│ → Giá trị lệnh: 48,600,000 VND      │
│ → % Tài khoản: 48.6%                │
│                                     │
│ ⚠️ Chưa tính phí giao dịch (~0.35%) │
└─────────────────────────────────────┘
```

**Implementation:**
- **Frontend-only calculation** — no backend needed. Uses entry_price and stop_loss from trading plan response
- **localStorage for account size** — persist across sessions (single user, same pattern as watchlist)
- **Default risk%: 2%** — industry standard. Adjustable 0.5%-5% with slider
- **VN broker fee note:** Standard ~0.15% buy + 0.15% sell + 0.1% tax on sell = ~0.35% round-trip

**Dependencies:** Trading plan data (entry_price, stop_loss from SIGNAL-01).

### SIGNAL-06: Key Levels on Chart

**lightweight-charts PriceLine API:**
```typescript
// Already available — lightweight-charts supports price lines natively
const entryLine = candleSeries.createPriceLine({
    price: 81000,
    color: '#2962FF',
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: 'Entry 81,000',
});

const slLine = candleSeries.createPriceLine({
    price: 78000,
    color: '#ef5350',
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: 'SL 78,000',
});

const tp1Line = candleSeries.createPriceLine({
    price: 85000,
    color: '#26a69a',
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: 'TP1 85,000',
});
```

**Implementation:**
- Read trading plan data from API (entry, SL, TP1, TP2, TP3, support, resistance)
- Create price lines for the **preferred direction only** (avoid visual clutter)
- Toggle: "Hiện mức giá kế hoạch" checkbox to show/hide lines
- Color scheme: Blue=Entry, Red=SL, Green=TP, Gray dashed=Support/Resistance
- Lines auto-remove when trading plan data refreshes

**Dependencies:** Existing CandlestickChart component, trading plan API data, lightweight-charts (already installed).

### SIGNAL-07: Telegram Trading Plan Alert

**Current signal change alert format:**
```
📡 THAY ĐỔI TÍN HIỆU

VNM: mua → BÁN 📉
💪 Độ tin cậy: 7/10
Lý do ngắn gọn...
```

**Enhanced trading plan alert format:**
```
📊 KẾ HOẠCH GIAO DỊCH — VNM

★ LONG (MUA) | Tin cậy: 7/10 | Swing

🟢 Entry:     81,000 VND
🔴 Stop-Loss: 78,000 VND (-3.7%)
🎯 TP1:       85,000 VND (+4.9%)
🎯 TP2:       88,000 VND (+8.6%)
📐 R:R:       1:1.3

💰 Vị thế: 600 CP (48.6M VND @ 2% risk)

📝 RSI tăng từ vùng trung tính với MACD cắt lên.
   Giá trên tất cả MA chính, momentum tích cực.

⚠️ Hủy nếu: Giá đóng cửa dưới SMA(50) = 78,000

⚠️ Tham khảo, không phải khuyến nghị đầu tư
```

**Trigger conditions (when to send):**
1. **Direction change:** preferred_direction changed from yesterday (mua→thoát, thoát→mua)
2. **Significant level change:** entry/SL/TP moved >3% from previous plan
3. **New high-conviction plan:** conviction ≥ 8 for preferred direction (strong opportunity)
4. **Plan invalidation:** Price hit the invalidation condition of yesterday's plan

**Implementation:** Extend existing `AlertService.check_signal_changes()` to compare trading plan fields instead of just `combined.signal`.

**Dependencies:** Existing Telegram bot, MessageFormatter, AlertService.

### SIGNAL-08: New AnalysisType and Database Storage

**Option A: New analysis_type enum value**
- Add `TRADING_PLAN = "trading_plan"` to `AnalysisType` enum
- Store in existing `ai_analyses` table with `signal = preferred_direction`, `score = conviction`, `reasoning = summary`
- Full structured plan in `raw_response` JSONB column
- **Pro:** Minimal schema change, leverages existing query patterns
- **Con:** JSONB for primary data is harder to query/index

**Option B: New dedicated table**
- New `trading_plans` table with dedicated columns for entry, SL, TP1, TP2, TP3, etc.
- **Pro:** Queryable, indexable, type-safe
- **Con:** More migration work, new service methods

**Recommendation: Option A** because:
1. Single-user platform — no need for complex queries across trading plans
2. `raw_response` JSONB already exists and is populated for all analysis types
3. Frontend reads the full plan from API anyway — just return the JSONB as-is
4. Avoids migration complexity and table proliferation
5. Existing `_store_analysis()` method works with zero changes
6. Alembic migration: just add `'trading_plan'` to the PostgreSQL `analysis_type` enum

**Dependencies:** Existing `ai_analyses` table and `_store_analysis()` method.

---

## Feature Dependencies

```
Existing Analysis Pipeline (AI-01..13, schemas/analysis.py)
    ├──→ SIGNAL-01: Dual-Direction Analysis (extends combined analysis)
    │       ├──→ SIGNAL-02: Gemini Prompt Restructure (new prompt + schema)
    │       │       └──→ SIGNAL-03: Extended Context (ATR, 20d high/low)
    │       ├──→ SIGNAL-04: Dashboard Trading Plan Panel (displays plan)
    │       │       └──→ SIGNAL-06: Key Levels on Chart (overlays on existing chart)
    │       ├──→ SIGNAL-05: Position Sizing Calculator (uses entry/SL from plan)
    │       ├──→ SIGNAL-07: Telegram Trading Plan Alert (enhanced format)
    │       └──→ SIGNAL-08: Database Storage (new enum value + JSONB)
    │
    └──→ SIGNAL-03 depends on:
            └──→ ATR indicator computation (new column in technical_indicators)

SIGNAL-05 (Position Sizing) is frontend-only, no backend dependency beyond plan data
SIGNAL-06 (Chart Overlays) depends on SIGNAL-04 (panel must exist to provide data)
```

### Critical Path

```
Phase 1: Backend Foundation
  SIGNAL-08 (DB enum) → SIGNAL-03 (ATR + context) → SIGNAL-02 (prompt) → SIGNAL-01 (dual-direction)

Phase 2: Frontend Display
  SIGNAL-04 (trading plan panel) → SIGNAL-06 (chart overlays) + SIGNAL-05 (position sizing)

Phase 3: Notifications
  SIGNAL-07 (Telegram alert)
```

**Why this order:**
1. DB migration (SIGNAL-08) must happen first — schema foundation
2. ATR computation (SIGNAL-03) feeds into Gemini prompts — must exist before prompts generate targets
3. Gemini prompt (SIGNAL-02) + dual-direction logic (SIGNAL-01) are the core backend work
4. Frontend display (SIGNAL-04/05/06) can only start after API returns plan data
5. Telegram (SIGNAL-07) is last because it depends on plan data AND stable format

---

## Gemini API Budget Impact

| Metric | Current (combined) | After v3.0 (trading plan) | Impact |
|--------|-------------------|--------------------------|--------|
| Output tokens per ticker | ~100-150 | ~400-600 | 3-4× increase |
| Batch size (at max_output=16384) | 25 tickers | 10-15 tickers | 1.7-2.5× more batches |
| Total batches for 400 HOSE tickers | 16 batches | 27-40 batches | 1.7-2.5× more API calls |
| Time (at 4s delay between batches) | ~64s | ~108-160s | +1-1.5 min |
| RPD impact (trading_plan only) | ~16 RPD | ~27-40 RPD | Manageable within 1500 RPD |

**Recommendation:** Run trading plan as a **5th analysis type** (alongside technical, fundamental, sentiment, combined) rather than replacing combined. This preserves backward compatibility and allows independent scheduling.

**Alternative:** Run trading plan ONLY for watchlisted tickers + top movers (not all 800+). Most tickers don't need full trading plans — only the ones the user is actively watching.

---

## MVP Recommendation

### Launch With (v3.0 MVP)

- [x] **SIGNAL-08: Database enum migration** — foundation, trivial
- [x] **SIGNAL-03: ATR computation + extended context** — data prerequisite
- [x] **SIGNAL-02: Gemini prompt restructure** — core intelligence
- [x] **SIGNAL-01: Dual-direction analysis** — the headline feature
- [x] **SIGNAL-04: Trading plan panel** — the headline UI
- [x] **SIGNAL-05: Position sizing calculator** — immediate practical value, frontend-only

### Add After Validation (v3.x)

- [ ] **SIGNAL-06: Key levels on chart** — high-impact visual, but validate data quality first
- [ ] **SIGNAL-07: Telegram trading plan alert** — only after plan quality is proven stable
- [ ] **Historical plan tracking** — track outcomes to build confidence in plan quality

### Future Consideration (v4+)

- [ ] **Sector-relative analysis** — compare plan vs sector momentum
- [ ] **Plan quality scoring** — automated tracking of TP/SL hit rates over time
- [ ] **Multi-timeframe plans** — same ticker, different plans for swing vs position
- [ ] **VN-Index correlation warning** — "Plan may be invalid in broad market selloff"

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Risk | Priority |
|---------|-----------|-------------------|------|----------|
| SIGNAL-01: Dual-direction analysis | HIGH | HIGH | MED (Gemini output quality) | P1 |
| SIGNAL-02: Gemini prompt restructure | HIGH | MED | MED (prompt engineering iteration) | P1 |
| SIGNAL-03: Extended context (ATR) | MED | LOW | LOW | P1 |
| SIGNAL-04: Trading plan panel | HIGH | MED | LOW | P1 |
| SIGNAL-05: Position sizing calc | HIGH | LOW | LOW | P1 |
| SIGNAL-06: Chart level overlays | MED | LOW | LOW | P2 |
| SIGNAL-07: Telegram alert | MED | LOW | LOW | P2 |
| SIGNAL-08: DB migration | LOW (invisible) | LOW | LOW | P1 (prerequisite) |
| Historical plan tracking | MED | HIGH | MED (data comparison logic) | P3 |
| Multiple TP targets (T1/T2/T3) | MED | LOW | LOW | P1 (built into schema) |
| Price band warnings | MED | LOW | LOW | P1 (built into panel) |
| Trade invalidation conditions | MED | LOW | LOW | P1 (built into schema) |

---

## Sources

| Finding | Source | Confidence |
|---------|--------|------------|
| HOSE ±7%, HNX ±10%, UPCOM ±15% price band limits | VN stock market domain knowledge (established since HOSE founding 2000) | HIGH — these are foundational exchange rules, stable for 20+ years |
| T+2 settlement across all VN exchanges | VSD regulation effective ~2022, replacing T+3 for HOSE | HIGH — well-established regulation |
| Short selling extremely limited in VN retail | SBL framework exists but <5% broker participation | MEDIUM — domain knowledge, not verified against 2026 regulatory changes |
| Trading sessions: ATO 9:00-9:15, Continuous 9:15-11:30, 13:00-14:30, ATC 14:30-14:45 | Standard HOSE/HNX trading hours | HIGH — stable schedule |
| Lot size 100 shares minimum | Exchange regulation for HOSE/HNX | HIGH |
| Existing AIAnalysis model has `raw_response JSONB` column | Direct inspection of `models/ai_analysis.py` line 50 | HIGH |
| Existing AnalysisType enum: TECHNICAL, FUNDAMENTAL, SENTIMENT, COMBINED | Direct inspection of `models/ai_analysis.py` lines 19-24 | HIGH |
| Existing Gemini structured output uses Pydantic response_schema | Direct inspection of `schemas/analysis.py` and `ai_analysis_service.py` line 633 | HIGH |
| `ta` library already installed with ATR support (`ta.volatility.AverageTrueRange`) | `ta` is in requirements.txt; ATR is a standard volatility indicator in the library | HIGH |
| lightweight-charts supports `createPriceLine()` for horizontal overlays | lightweight-charts API documentation (standard feature since v3) | HIGH |
| Gemini max_output_tokens currently set to 16384 | Direct inspection of `ai_analysis_service.py` line 635 | HIGH |
| Existing batch_size = 25, delay = 4.0s between batches | Direct inspection of `config.py` lines 57-58 | HIGH |
| CombinedRecommendationCard is a prominent component on ticker detail | Direct inspection of `ticker/[symbol]/page.tsx` lines 282-286 | HIGH |
| MessageFormatter.signal_change() handles signal alerts | Direct inspection of `telegram/formatter.py` lines 158-166 | HIGH |
| Vietnamese broker fee ~0.15% buy + 0.15% sell + 0.1% tax | VN stock market standard fee structure | MEDIUM — varies by broker tier |
| Gemini 2.5-flash-lite thinking_budget set to 1024 | Direct inspection of `ai_analysis_service.py` lines 624-625 | HIGH |

---
*Feature research for: v3.0 Smart Trading Signals — Holo Stock Intelligence Platform*
*Researched: 2026-04-21*
