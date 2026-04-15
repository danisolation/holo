# Feature Landscape

**Domain:** Stock Market Intelligence Platform (Vietnam HOSE)
**Researched:** 2025-07-16
**Overall Confidence:** HIGH (domain well-established, Vietnam-specific sources verified)

---

## Table Stakes

Features that are expected in any stock market intelligence tool. Missing = the product feels broken or incomplete.

### Data Ingestion

| Feature | Why Expected | Complexity | Notes |
|---------|-------------|------------|-------|
| **Daily OHLCV price crawling** | Core data — everything depends on this | Medium | Use vnstock (v3.5.1, 1243★) which wraps VCI/VNDirect APIs. Don't build raw crawlers. |
| **Scheduled automated crawling** | Manual crawl = useless tool. Must run unattended | Medium | APScheduler (v3.11.2) for in-process cron. No need for Celery — personal use, single process. |
| **Historical data backfill** | Need 1-2 years of history for technical analysis to work | Medium | vnstock `history()` supports arbitrary date ranges. One-time backfill + daily incremental. |
| **Financial statement data** | P/E, P/B, revenue, profit — required for fundamental analysis | Medium | vnstock's VCI connector has `financial.py` and `company.py`. Quarterly + annual reports. |
| **Error handling & retry logic** | API failures are inevitable. Silent failures = stale data = bad decisions | Medium | vnstock uses `tenacity` for retries. Add dead-letter logging for failed fetches. |
| **Rate limiting compliance** | VNDirect/VCI APIs will block aggressive crawlers | Low | 400 tickers ÷ reasonable rate = ~10-15 min full crawl. Add configurable delays between requests. |
| **Data gap detection** | If Monday data is missing, you need to know — not silently use Friday's data | Medium | Compare expected trading days vs actual data points. Alert on gaps > 1 day. |

### Dashboard & Visualization

| Feature | Why Expected | Complexity | Notes |
|---------|-------------|------------|-------|
| **Candlestick price charts** | The fundamental visualization of stock data. Non-negotiable. | Medium | Use `lightweight-charts` (v5.1.0, by TradingView) — best performance, native financial chart look. |
| **Technical indicator overlays** | MA, RSI, MACD, Bollinger Bands on charts — users expect to see these | Medium | Compute server-side with `ta` library (5008★), render overlays on lightweight-charts. |
| **Watchlist** | Must be able to mark favorite tickers for quick access | Low | Simple PostgreSQL table. Personal use = one watchlist is fine. |
| **Ticker detail page** | Click a ticker → see price, financials, AI analysis, news | Medium | Single page combining chart + key metrics + AI verdict. This is the core UX. |
| **Responsive layout** | PROJECT.md says "web-first, responsive là đủ" — must work on phone browser | Medium | Next.js + Tailwind CSS. No mobile app needed, but dashboard must be usable on mobile. |
| **Market overview / heatmap** | At-a-glance view of what's up/down today across 400 tickers | Medium | Color-coded grid by sector/market cap. VN30 highlighted. |

### AI Analysis

| Feature | Why Expected | Complexity | Notes |
|---------|-------------|------------|-------|
| **Technical analysis scoring** | RSI, MACD, MA crossovers → bullish/bearish/neutral signal | Medium | Compute indicators with `ta` library, pass structured data to Gemini for synthesis. |
| **Fundamental analysis scoring** | P/E, P/B, revenue growth, debt ratio → health score | Medium | Pull from vnstock financial data. Score relative to sector peers. |
| **Combined buy/sell/hold recommendation** | The whole point — multi-dimensional AI verdict | High | Gemini prompt: structured JSON of technical + fundamental + sentiment → unified recommendation. |
| **Confidence level on recommendations** | "Strong buy" vs "weak buy" — user needs to calibrate trust | Low | Part of prompt engineering. Ask Gemini to output confidence 1-10 with reasoning. |

### Alerts & Notifications

| Feature | Why Expected | Complexity | Notes |
|---------|-------------|------------|-------|
| **Telegram bot for trading signals** | PROJECT.md core requirement. Phone notification = timely action. | Medium | `python-telegram-bot` (v22.7). Send when AI detects signal change (e.g., neutral→buy). |
| **Price alert triggers** | "Tell me when VNM crosses 80,000 VND" — basic alert | Medium | Check after each data fetch. Store alert rules in PostgreSQL. |
| **Daily market summary** | Morning brief before market opens or evening recap | Low | Scheduled Telegram message: top movers, signals changed, watchlist status. |

---

## Differentiators

Features that set Holo apart from basic tools. Not expected, but create significant value.

### AI-Powered Analysis

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Sentiment analysis from news** | Most Vietnam stock tools ignore news sentiment. Gemini can read Vietnamese text natively. | High | Crawl news from CafeF/VNDirect RSS. Feed Vietnamese text directly to Gemini — it handles Vietnamese well. |
| **3-dimensional combined analysis** | Technical + Fundamental + Sentiment in one verdict is rare. Most tools do one dimension only. | High | This is the core differentiator per PROJECT.md. Prompt engineering to weight all three dimensions. |
| **Natural language explanations** | "VNM is bullish because RSI recovered from oversold while Q3 revenue grew 15% and positive press coverage..." | Medium | Gemini generates Vietnamese explanations. Much more useful than numeric scores alone. |
| **Sector-relative scoring** | "P/E of 15 means overvalued for banking but cheap for tech" — context-aware | Medium | Group tickers by ICB industry (vnstock's `industries_icb()`). Score within sector. |
| **AI signal change alerts** | Alert only when recommendation *changes* (buy→sell), not every day. Reduces noise. | Medium | Track previous recommendation in DB. Only trigger Telegram alert on state transition. |

### Data Intelligence

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Foreign ownership tracking** | Vietnam has foreign ownership limits (49% general, 30% banks). Approaching limit = price impact. | Medium | Track room (available foreign buy quota). Data available via vnstock price_board. |
| **T+2 settlement awareness** | Unique to Vietnam. "You bought Monday, cash settles Wednesday." Affects buying power. | Low | Display settlement date on portfolio. Calculate available cash considering pending settlements. |
| **HOSE session-aware scheduling** | Crawl during sessions (9:00-11:30, 13:00-14:45 UTC+7), skip weekends/VN holidays | Medium | APScheduler with Vietnam timezone. Holiday calendar (Tet, National Day, etc.). |
| **Intraday price tracking** | Real-time(ish) prices during trading sessions, not just end-of-day | High | vnstock `intraday()` method. Poll every 1-5 min during sessions. Higher API load. |
| **Price limit awareness** | HOSE has ±7% daily price limit. Floor/ceiling prices affect order placement. | Low | Calculate and display floor/ceiling on ticker detail page. Highlight stocks near limits. |

### Dashboard Enhancements

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Stock screener/filter** | Filter 400 tickers by criteria (P/E < 15, RSI < 30, etc.) — find opportunities faster | High | Multi-criteria filter UI + efficient DB queries. Core discovery tool. |
| **Portfolio tracking with P&L** | Track what you actually own and performance over time | Medium | Manual entry (no broker API). Calculate unrealized P&L, dividends, average cost basis. |
| **VN30/VN100 index comparison** | "Is my stock beating the market?" — basic benchmarking | Low | vnstock has index data. Overlay index performance on ticker charts. |
| **Sector heatmap** | Visual grid showing which sectors are hot/cold today | Medium | Color-coded treemap by sector. Quick pattern recognition across 400 tickers. |

### Telegram Bot Enhancements

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Interactive watchlist management** | `/add VNM`, `/remove VNM`, `/list` — manage watchlist from Telegram | Low | Simple command handlers. Already in python-telegram-bot patterns. |
| **On-demand ticker query** | `/check VNM` → instant AI summary for any ticker via Telegram | Medium | Fetch latest data, run through Gemini, return formatted message. |
| **Chart image in Telegram** | Send candlestick chart as image in Telegram messages | Medium | Generate chart server-side (matplotlib/plotly → PNG), send via Telegram API. |

---

## Anti-Features

Features to deliberately NOT build. Each would waste time or create risk.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Auto-trading / order execution** | PROJECT.md explicitly excludes. Legal risk in Vietnam, financial risk, broker API complexity. | Recommend only. User executes manually on their broker platform. |
| **User authentication / multi-tenancy** | Personal use only. Auth adds complexity with zero value for single user. | Optional: simple env-var token for basic protection. No user management. |
| **HNX/UPCOM exchange data** | Out of scope per PROJECT.md. HOSE has the most liquid, institutional-grade tickers. | Focus 400 HOSE tickers. Can extend later if needed. |
| **Paid data sources** | PROJECT.md says free sources only. FireAnt Pro, Entrade add cost and vendor lock-in. | vnstock (VCI), CafeF scraping, SSI public endpoints — all free and sufficient. |
| **Mobile app** | Web responsive is sufficient. Native mobile = huge effort for marginal gain (one user). | Responsive Next.js dashboard + Telegram bot covers mobile use cases. |
| **Real-time WebSocket streaming** | True real-time requires WebSocket connections to exchange. Overkill for personal analysis. | Poll intraday data every 1-5 min during sessions. Sufficient for decision-making. |
| **ML price prediction models** | Random Forest / LSTM price predictions have dubious accuracy. Creates false confidence. | Use Gemini for qualitative analysis, not quantitative price targets. More honest and useful. |
| **Backtesting engine** | Complex to build properly. Survivorship bias, slippage, etc. — easy to get wrong. | Focus on forward-looking AI analysis. Backtesting is a separate product. |
| **Social features / sharing** | No other users. Social features = wasted effort. | Single-user tool. Telegram is the "social" channel (you can forward messages). |
| **Complex charting editor** | Drawing tools, Fibonacci retracements, annotation layers — TradingView already does this. | Provide read-only charts with key indicators. For deep charting, user opens TradingView. |
| **PDF/Excel report export** | Over-engineering for personal use. You see the dashboard, you don't need reports. | Dashboard IS the report. If needed later, simple CSV export is trivial to add. |

---

## Feature Dependencies

```
[Historical Data Backfill] → [Technical Indicator Calculation] → [AI Technical Analysis]
                          ↘
[Daily OHLCV Crawl] ————→ [Technical Indicator Calculation]
                          → [Candlestick Charts]
                          → [Market Overview / Heatmap]
                          → [Stock Screener]

[Financial Statement Crawl] → [AI Fundamental Analysis]
                            → [Sector-Relative Scoring]
                            → [Stock Screener (fundamental criteria)]

[News Crawl] → [AI Sentiment Analysis]

[AI Technical Analysis] ⎫
[AI Fundamental Analysis] ⎬→ [Combined Buy/Sell/Hold Recommendation]
[AI Sentiment Analysis] ⎭     → [Signal Change Detection] → [Telegram Alert]
                               → [Ticker Detail Page (AI section)]
                               → [Daily Market Summary]

[Watchlist] → [Telegram Alert Filtering] (only alert for watched tickers)
            → [Portfolio Tracking]
            → [Daily Summary Scope]

[Rate Limiting] → [All Crawling Features]
[Error Handling] → [All Crawling Features]
[Scheduled Crawl] → [All Automated Features]
[Data Gap Detection] → [Data Quality Assurance]

[HOSE Session Awareness] → [Intraday Tracking]
                         → [Scheduled Crawl Timing]
```

### Critical Path

The longest dependency chain that blocks the core value:

```
DB Schema → Historical Backfill → TA Indicators → AI Technical Analysis
    ↓
Financial Crawl → AI Fundamental Analysis → Combined Recommendation → Telegram Alert
    ↓
News Crawl → AI Sentiment Analysis ↗
```

**All three analysis dimensions must be ready before the combined recommendation works.** This means data crawling for all three sources (price, financials, news) is the critical foundation.

---

## MVP Recommendation

### Phase 1: Data Foundation (must be first)
1. **Daily OHLCV crawl** via vnstock — the foundation everything depends on
2. **Historical backfill** — need 1-2 years for TA indicators to be meaningful
3. **Financial statement crawl** — quarterly data, less frequent but essential
4. **Scheduled automation** — APScheduler with HOSE session awareness
5. **Error handling + rate limiting** — without this, crawling is unreliable
6. **Data gap detection** — trust your data before analyzing it

### Phase 2: Analysis Engine
1. **Technical indicator calculation** — ta library, compute and store in DB
2. **AI technical analysis** — Gemini + structured indicator data
3. **AI fundamental analysis** — Gemini + financial metrics
4. **Combined recommendation** — the core product value
5. **News crawl + sentiment** (can be MVP-lite without this, add iteratively)

### Phase 3: User Interfaces
1. **Telegram bot with daily summary** — fastest path to daily value
2. **Signal change alerts** — the killer notification feature
3. **Web dashboard with ticker detail page** — candlestick + AI verdict
4. **Watchlist management** — via Telegram first, then web UI
5. **Market overview heatmap**

### Defer to Later
- **Stock screener**: Valuable but complex. Needs solid data first.
- **Portfolio tracking with P&L**: Nice-to-have, not core intelligence value.
- **Intraday tracking**: Higher complexity, higher API load. Add after daily pipeline is stable.
- **Chart images in Telegram**: Polish feature, not core.
- **Sector heatmap**: Visualization enhancement, defer until dashboard basics work.

---

## Vietnam-Specific Feature Notes

### HOSE Trading Sessions (UTC+7)
| Session | Time | Type |
|---------|------|------|
| Morning continuous | 9:15 - 11:30 | Continuous matching |
| Lunch break | 11:30 - 13:00 | No trading |
| Afternoon continuous | 13:00 - 14:30 | Continuous matching |
| ATC (closing) | 14:30 - 14:45 | Periodic matching (closing price) |

**Implication:** Schedule intraday crawls only within these windows. Daily crawl after 15:00.

### Price Limits
- **Standard stocks:** ±7% from reference price
- **First listing day:** ±20%
- **Bonds:** No limit

**Implication:** Calculate and display ceiling/floor prices. Alert when stock is at ceiling (can't buy) or floor (panic selling).

### Settlement: T+2
- Buy Monday → Settled Wednesday → Can sell Wednesday
- Affects available cash and selling ability

**Implication:** Portfolio tracker must account for pending settlements. "Available to sell" vs "owned" distinction.

### Foreign Ownership Limits
- **General:** 49% for most sectors
- **Banking:** 30%
- **Conditional sectors:** Varies (some allow 100% post-CPTPP)
- **At limit:** Foreign investors cannot buy → price suppression or premium

**Implication:** Track foreign ownership room. Alert when approaching limit on watched tickers. Data available via vnstock `price_board()`.

### Vietnamese Holidays (Market Closed)
- Tết Nguyên Đán (Lunar New Year) — ~7-9 days
- Reunification Day (April 30)
- International Workers' Day (May 1)
- National Day (September 2)
- Hung Kings Anniversary (10th March lunar)

**Implication:** Holiday calendar must be coded. Don't alert on missing data during holidays. Don't crawl during holidays.

---

## Sources

| Source | Type | Confidence |
|--------|------|------------|
| vnstock v3.5.1 (github.com/thinh-vu/vnstock, 1243★) | PyPI + GitHub | HIGH — verified API structure, active development |
| vnquant v0.1.23 (github.com/phamdinhkhanh/vnquant, 471★) | PyPI + GitHub | HIGH — alternative data source, VNDirect + CafeF |
| ta v0.11.0 (github.com/bukosabino/ta, 5008★) | PyPI | HIGH — industry standard TA library |
| lightweight-charts v5.1.0 (TradingView) | npm | HIGH — TradingView's official open-source charting |
| python-telegram-bot v22.7 | PyPI | HIGH — most popular Python Telegram library |
| APScheduler v3.11.2 | PyPI | HIGH — well-established scheduling library |
| Wikipedia: Ho Chi Minh City Stock Exchange | Web | MEDIUM — general HOSE rules confirmed |
| AI-Kline (github.com/QuantML-C/AI-Kline, 321★) | GitHub | MEDIUM — reference architecture for AI stock analysis |
| StockBot (github.com/Sachin-dot-py/StockBot) | GitHub | MEDIUM — Telegram bot pattern reference |
| Screeni-py (github.com/pranjal-joshi/Screeni-py, 679★) | GitHub | MEDIUM — screener feature reference |
| ErikThiart/ai-stock-dashboard (72★) | GitHub | MEDIUM — dashboard feature reference |
| HOSE trading hours/sessions | Training data + PROJECT.md context | MEDIUM — session times should be verified against current HOSE announcements |
| Foreign ownership limits | Training data | LOW — specific percentages should be verified with SSC current regulations |
| Vietnamese holiday calendar | Training data | MEDIUM — specific dates vary yearly, need dynamic calendar |
