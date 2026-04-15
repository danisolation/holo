# Domain Pitfalls

**Domain:** Vietnam Stock Market (HOSE) Intelligence Platform — Crawler + AI Analysis + Dashboard + Telegram Bot
**Researched:** 2026-04-15

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or fundamental architecture failures.

---

### Pitfall 1: Data Source APIs Are Undocumented Internal Endpoints That Break Without Warning

**What goes wrong:** The project plan references "VNDirect API, SSI API, CafeF scraping" as data sources. In reality, the Vietnam stock data ecosystem has shifted significantly. The most active library (`vnstock` v3.x, 3.5.1 as of March 2026) now uses **VietCap/VCI** (`trading.vietcap.com.vn` GraphQL API) and **KB Securities/KBS** (`kbbuddywts.kbsec.com.vn`) — NOT the old VNDirect or SSI APIs directly. These are **undocumented internal APIs** of brokerage platforms, not official public APIs. They can change endpoints, add authentication, or shut down access at any time without notice.

**Why it happens:** Vietnam's stock exchanges (HOSE/HNX) don't offer free public data APIs like US exchanges. All free data comes from reverse-engineering brokerage platform APIs. Every VN stock data library depends on this fragile approach.

**Evidence:**
- vnstock v3 `vci/const.py` shows: `_GRAPHQL_URL = 'https://trading.vietcap.com.vn/data-mt/graphql'` — a GraphQL endpoint on VietCap's trading platform
- vnstock v3 `kbs/const.py` shows: `_IIS_BASE_URL = 'https://kbbuddywts.kbsec.com.vn/iis-server/investment'` — KB Securities internal API
- vnstock GitHub Issue #218: `KeyError: 'data'` when API response structure changed
- vnstock GitHub Issue #182: `price_board` method broke due to upstream API changes
- vnstock jumped from v0.2.x to v3.x — **major breaking changes** in data source architecture

**Consequences:**
- Crawler breaks silently — you think you're collecting data but get empty/malformed responses
- Historical data has gaps you don't notice until analysis produces wrong results
- Rebuilding scraper from scratch when an API shuts down

**Prevention:**
1. **Don't build custom scrapers from scratch.** Use `vnstock` v3.x as a data abstraction layer — when upstream APIs change, the library maintainer (active community) updates the endpoints. Pin to a specific version but monitor releases.
2. **Build a data source abstraction layer** — your code should never call VCI/KBS directly. Wrap vnstock calls so you can swap implementations.
3. **Implement data validation on every crawl** — check row counts, price ranges (HOSE has ±7% daily limit from reference price), and null percentages. Alert when anomalies exceed thresholds.
4. **Store raw API responses** before transformation — enables re-processing when you discover parsing bugs.
5. **Multi-source fallback** — vnstock supports both VCI and KBS sources. Configure automatic failover.

**Detection:** Monitor crawl success rate daily. If >5% of tickers return empty/error for 2+ consecutive runs, the upstream API likely changed.

**Phase relevance:** Phase 1 (Data Infrastructure) — this must be addressed from day one.

**Confidence:** HIGH — verified from vnstock source code and GitHub issues.

---

### Pitfall 2: Ignoring Adjusted Prices Corrupts All Technical Analysis

**What goes wrong:** Vietnamese stock data from VCI/KBS APIs returns **unadjusted (raw) OHLCV prices**. When a company does a stock split, bonus share issuance, or cash dividend, the raw price drops sharply — but this isn't a real price decline. If you calculate moving averages, RSI, MACD, or Bollinger Bands on unadjusted data, every indicator produces **false signals** around corporate action dates.

**Why it happens:** Searching the entire vnstock v3 codebase reveals **zero mentions of "adjusted"** in the price data module. The VCI API returns raw OHLCV with fields: `time, open, high, low, close, volume` — no adjusted close column. Vietnamese brokerages display unadjusted prices by default (unlike Yahoo Finance which defaults to adjusted).

**Evidence:**
- vnstock `vci/const.py` OHLC map: `{'t': 'time', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}` — no adjusted field
- GitHub search for "adjusted" in thinh-vu/vnstock: 0 results
- HOSE corporate actions are frequent: VN30 stocks regularly do stock splits (e.g., VNM, VHM, FPT have all split in recent years)

**Consequences:**
- MA crossover signals fire falsely on split dates
- RSI shows oversold when stock split happened (not a real decline)
- Backtesting produces garbage results
- AI receives corrupted data → produces confident but wrong analysis
- You make trading decisions on fake signals

**Prevention:**
1. **Build a corporate actions table** — crawl stock split, dividend, bonus share data from CafeF or VNDirect corporate actions pages
2. **Calculate adjustment factors** — for each corporate action, compute the ratio (e.g., 2:1 split = 0.5 factor)
3. **Apply backward adjustment** to historical prices before any indicator calculation
4. **Store both raw and adjusted prices** — raw for data integrity verification, adjusted for analysis
5. **Re-adjust entire history** when new corporate actions are announced (not just append)

**Detection:** Plot any VN30 stock's 1-year price chart. If you see sudden 50% drops that recover instantly, those are stock splits on unadjusted data.

**Phase relevance:** Phase 1-2 (Data Infrastructure → Technical Analysis) — must be solved before any indicator calculation.

**Confidence:** HIGH — verified from source code analysis.

---

### Pitfall 3: HOSE Trading Schedule Is More Complex Than "9:00-14:45"

**What goes wrong:** The project description states trading hours as "9:00-11:30 sáng, 13:00-14:45 chiều." This is an oversimplification that will cause the scheduler to miss data or fire at wrong times.

**Why it happens:** HOSE has multiple distinct sessions with different trading rules:

| Session | Time (UTC+7) | Type | Data Available |
|---------|-------------|------|----------------|
| ATO (Opening) | 09:00-09:15 | Auction | Opening price determined at 09:15 |
| Morning Continuous | 09:15-11:30 | Continuous matching | Real-time ticks |
| Lunch Break | 11:30-13:00 | No trading | No new data |
| Afternoon Continuous | 13:00-14:30 | Continuous matching | Real-time ticks |
| ATC (Closing) | 14:30-14:45 | Auction | Closing price determined at 14:45 |
| Post-Trading / Put-through | 14:45-15:00 | Negotiated deals | Final settlement data |

**Evidence:** vnstock `market.py` source code confirms: `"trading_start": "09:00"`, `"atc_end": "14:45"`, `"trading_end": "15:00"` — the actual end of all activity is **15:00**, not 14:45.

**Consequences:**
- Scheduling daily crawl at 14:45 misses ATC closing price and put-through volume
- Scheduling at 15:00 sharp may catch incomplete settlement data
- Intraday data collection misses the critical ATO/ATC auction periods
- Telegram alerts during lunch break (11:30-13:00) are noise — no trading happening

**Prevention:**
1. **Schedule end-of-day crawl at 15:15-15:30 UTC+7** — gives 15-30 min buffer after all sessions close
2. **Use vnstock's `trading_hours()` utility** to check market status before crawling
3. **Track session boundaries** — ATO price at 09:15, ATC price at 14:45, final data at 15:00+
4. **Suppress Telegram alerts during lunch break** — 11:30-13:00 is dead time

**Detection:** Compare your stored closing prices with official HOSE closing prices. If they differ, you're likely crawling at the wrong time (before ATC settles).

**Phase relevance:** Phase 1 (Scheduling) and Phase 3 (Telegram Bot alerts).

**Confidence:** HIGH — verified from vnstock source code.

---

### Pitfall 4: LLM Hallucination on Vietnam-Specific Financial Data

**What goes wrong:** Google Gemini (or any LLM) will confidently produce **wrong analysis** about Vietnamese stocks because:
- Training data on VN stocks is sparse compared to US/EU markets
- Vietnamese accounting standards (VAS) differ from IFRS — Gemini may apply US GAAP mental models
- VN-specific metrics (room ngoại, tỷ lệ margin, biên lãi gộp in VND) are poorly represented in training data
- Gemini may "invent" financial data points that don't exist

**Why it happens:** LLMs are trained primarily on English-language financial content about US markets. Vietnamese stock market data is a tiny fraction of training data. The model has no way to say "I don't know this" — it generates plausible-sounding but wrong analysis.

**Consequences:**
- AI says "VNM's P/E ratio of 12 is below industry average of 15" when actual values are different
- AI recommends buying based on hallucinated support levels
- User trusts AI analysis because it sounds authoritative
- Real money lost on fabricated insights

**Prevention:**
1. **NEVER let Gemini generate financial data** — always inject actual data into the prompt. The LLM's job is to _interpret_ data you provide, not to _recall_ data.
2. **Structured prompts with explicit data injection:**
   ```
   Analyze this stock based ONLY on the provided data. Do not use any external knowledge about this company.
   
   Symbol: FPT
   Current Price: 128,500 VND
   P/E: 22.3
   52-week range: 89,200 - 135,000
   RSI(14): 67.2
   MACD: bullish crossover 3 days ago
   Recent news: [injected headlines]
   ```
3. **Add explicit constraints:** "If the provided data is insufficient for a conclusion, say 'Insufficient data' instead of guessing."
4. **Validate AI outputs** — cross-check any specific numbers the AI mentions against your database. If the AI outputs a number you didn't provide, flag it.
5. **Use Vietnamese language prompts** for Vietnamese market context — Gemini handles Vietnamese, and this reduces the chance of US market mental model bleed.

**Detection:** Periodically spot-check AI analysis by verifying 3-5 specific claims per output against your actual database.

**Phase relevance:** Phase 3 (AI Analysis) — design prompt engineering carefully from the start.

**Confidence:** HIGH — well-documented LLM limitation, amplified for low-resource financial domains.

---

### Pitfall 5: Gemini API Cost Explosion With 400 Tickers Daily

**What goes wrong:** Analyzing 400 tickers daily with Gemini API can quickly exhaust free tier limits or generate unexpected costs. Each analysis requires a prompt with OHLCV data, financial ratios, indicators, and news — easily 2,000-5,000 tokens per ticker. 400 tickers × 3,000 avg tokens = **1.2M input tokens per daily run**, plus output tokens.

**Why it happens:** People prototype with 5-10 tickers, it works great, then scale to 400 and hit rate limits or budget surprises.

**Gemini Free Tier Limits (as of early 2026, verify current):**
- Gemini 1.5 Flash: 15 RPM (requests per minute), 1M TPM (tokens per minute), 1,500 RPD (requests per day)
- Gemini 1.5 Pro: 2 RPM, 32K TPM, 50 RPD

**Consequences:**
- 400 tickers at 1 request each = 400 RPD — works for Flash (1,500 RPD limit) but NOT for Pro (50 RPD)
- At 15 RPM, analyzing 400 tickers takes minimum 27 minutes just for rate limiting
- If you add retry logic without backoff, you'll get temporarily blocked
- Paid tier: Gemini 1.5 Flash at $0.075/1M input tokens → 1.2M tokens/day ≈ $0.09/day ≈ $2.70/month (affordable but needs monitoring)

**Prevention:**
1. **Use Gemini Flash, not Pro** — Flash is cheaper, faster, and has much higher rate limits. Pro is overkill for technical analysis summaries.
2. **Batch analysis** — don't analyze 400 tickers individually. Group by sector (20-25 sectors × ~16 tickers each). Send sector batches. This reduces requests from 400 to ~25.
3. **Tiered analysis frequency:**
   - VN30 (30 tickers): Daily full analysis
   - Watchlist (user-defined ~20 tickers): Daily full analysis
   - Remaining ~350 tickers: Weekly scan, or only when indicators trigger alerts
4. **Implement exponential backoff** — don't just retry immediately on rate limit errors
5. **Cache analysis results** — if data hasn't changed significantly (price within 1% of yesterday), skip re-analysis
6. **Track token usage** — log input/output tokens per request for cost monitoring

**Detection:** Monitor daily API call count and token usage. Alert when approaching 80% of quota.

**Phase relevance:** Phase 3 (AI Analysis) — architect the batching strategy before building.

**Confidence:** MEDIUM — Gemini free tier limits verified from PyPI package availability; specific numbers should be verified against current Google AI pricing page.

---

## Moderate Pitfalls

---

### Pitfall 6: vnstock v3 Moving to Freemium — Free Tier May Have Limitations

**What goes wrong:** vnstock v3.x introduced the "Insiders Program" (paid subscription). GitHub Issue #219 asks "API BÁO LỖI LÀ DO DÙNG BẢN FREE PHẢI KHÔNG Ạ?" (API errors because using free version?). Issue #206 mentions device installation limits. Issue #210 reports deadlocks with `vnai` module (a telemetry/licensing component).

**Why it happens:** Open source project sustainability — the maintainer monetized advanced features. The `vnai` dependency added in v3.x appears to include usage tracking/licensing.

**Prevention:**
1. **Pin vnstock to a specific version** and test thoroughly before upgrading
2. **Have a fallback plan** — if vnstock free tier becomes too restrictive, be prepared to build direct API calls to VCI/KBS using the endpoint patterns documented in vnstock's source code
3. **Consider vnstock v2.x** as a backup — older but fully open source (v2.2.3 was released March 2025)
4. **Monitor the `vnai` dependency** — understand what it does and whether it affects rate limits

**Detection:** Track if API calls start failing with new error types after vnstock updates. Monitor vnstock release notes and GitHub discussions.

**Phase relevance:** Phase 1 (Data Infrastructure) — make this decision early.

**Confidence:** MEDIUM — based on GitHub issues and release notes; exact free tier limitations unclear.

---

### Pitfall 7: PostgreSQL on Aiven — Connection Limits and Time-Series Performance

**What goes wrong:** Aiven's free/hobby PostgreSQL tier typically has strict connection limits (often 20-25 max connections). A FastAPI app with a connection pool + scheduled crawlers + dashboard queries can easily exhaust this. Additionally, vanilla PostgreSQL is not optimized for time-series workloads — querying "last 200 daily candles for 400 tickers" without proper indexing is painfully slow.

**Why it happens:** People treat PostgreSQL as "just a database" without considering the specific access patterns of financial time-series data.

**Consequences:**
- "too many connections" errors during market hours when crawler, API, and dashboard compete
- Dashboard pages take 5-10 seconds to load because of full table scans
- Database storage grows unexpectedly with intraday data (400 tickers × 300+ ticks/day × 252 trading days)

**Prevention:**
1. **Connection pooling is mandatory** — use a small pool (5-8 connections) with `asyncpg` + SQLAlchemy async. Never create connections per-request.
2. **Partition the OHLCV table by year** — `CREATE TABLE ohlcv_2026 PARTITION OF ohlcv FOR VALUES FROM ('2026-01-01') TO ('2027-01-01')`
3. **Composite index strategy:**
   ```sql
   -- Primary query pattern: "Get candles for symbol X in date range"
   CREATE INDEX idx_ohlcv_symbol_date ON ohlcv (symbol, date DESC);
   -- Secondary: "Get all symbols for a specific date" (daily screening)
   CREATE INDEX idx_ohlcv_date ON ohlcv (date DESC);
   ```
4. **Separate daily vs intraday tables** — don't mix 1-day candles with 1-minute ticks in the same table
5. **Consider TimescaleDB extension** if Aiven supports it — it's a PostgreSQL extension purpose-built for time-series (automatic partitioning, compression, continuous aggregates). Check Aiven plan compatibility.
6. **Estimate storage early:**
   - Daily OHLCV: 400 tickers × 252 days × ~100 bytes = ~10 MB/year (trivial)
   - Intraday ticks: 400 tickers × 300 ticks × 252 days × ~50 bytes = ~1.5 GB/year (manageable but plan for it)
   - Financial statements: negligible (quarterly updates)

**Detection:** Monitor query execution time with `pg_stat_statements`. Alert when any query exceeds 500ms.

**Phase relevance:** Phase 1 (Database Setup) — schema design is hard to change later.

**Confidence:** HIGH — standard PostgreSQL best practices for time-series.

---

### Pitfall 8: CafeF Scraping Is Extremely Fragile — Don't Depend On It

**What goes wrong:** CafeF (cafef.vn) is a popular Vietnamese financial news/data site. Scraping it for financial reports, corporate actions, or news is tempting but extremely unreliable:
- HTML structure changes frequently (no API, pure web scraping)
- Anti-bot measures (Cloudflare, CAPTCHAs) block automated access
- Data is in Vietnamese with inconsistent formatting (number formats: 1.234,56 vs 1,234.56)
- Page layouts differ between stock pages, financial report pages, and news pages

**Why it happens:** CafeF is designed for human consumption, not programmatic access. Only 1 GitHub repository exists for CafeF scraping (with 0 stars) — the community has largely moved away from it.

**Prevention:**
1. **Use CafeF only as a last resort** — prefer structured API data from VCI/KBS via vnstock
2. **For financial reports** — vnstock v3's `Finance` class already provides balance sheets, income statements, and cash flow from VCI's GraphQL API
3. **For news/sentiment** — consider structured news APIs from KBS (vnstock `kbs/const.py` shows `_SAS_NEWS_URL`) rather than scraping CafeF
4. **If you must scrape CafeF** — use it only for corporate actions (stock splits, dividends) that aren't available via vnstock APIs. Build with Playwright/Selenium (not requests+BeautifulSoup) to handle dynamic content, and expect it to break monthly.

**Detection:** If your CafeF scraper returns empty results or HTML error pages for >10% of requests, it's likely been blocked or the layout changed.

**Phase relevance:** Phase 1 (Data Sources) — decide data sources early to avoid building throwaway scrapers.

**Confidence:** HIGH — based on GitHub ecosystem evidence (only 1 CafeF scraping repo exists).

---

### Pitfall 9: Vietnamese Market Holiday Calendar Is Unpredictable

**What goes wrong:** Vietnam's market holidays include lunar calendar dates (Tết Nguyên Đán) that shift every year, plus "compensation days" (nghỉ bù) where a regular weekday becomes a holiday. The government announces the exact holiday schedule only a few months in advance. Hardcoding holidays or using a simple "weekends only" check will cause:
- Crawler runs on holidays → gets stale data → stores duplicates
- Crawler skips unexpected trading days (Saturday makeup sessions after long holidays)
- Alert system fires "no data" warnings on holidays, causing alert fatigue

**Evidence:** vnstock v3.5.0 (March 2026) added `market_events.py` with a comprehensive dictionary of Vietnam market holidays from 2000-present, including:
- `"Holiday"` type: regular public holidays
- `"Compensation"` type: make-up holidays (nghỉ bù/hoán đổi) — weekdays off to create long weekends
- Tết Nguyên Đán: 4-7 days off, dates vary by lunar calendar every year

**Prevention:**
1. **Use vnstock's `MARKET_EVENTS` dictionary** as your primary holiday calendar
2. **Supplement with a dynamic check** — before each crawl, verify if the market actually traded today by checking if any data was returned
3. **Don't hardcode future holidays** — fetch/update the holiday list periodically (at least quarterly)
4. **Handle Saturday trading days** — after Tết, the government sometimes designates a Saturday as a working day to compensate. Your scheduler must handle this.
5. **Graceful no-data handling** — if crawler returns empty data, check if it's a holiday before alerting

**Detection:** Keep a "last successful data fetch" timestamp. If it's been >3 business days without data, investigate — it's likely a bug, not a holiday streak.

**Phase relevance:** Phase 1 (Scheduling) — implement holiday awareness from the start.

**Confidence:** HIGH — verified from vnstock source code.

---

### Pitfall 10: Technical Indicator Edge Cases on Vietnamese Market Data

**What goes wrong:** Standard technical analysis libraries (`ta` v0.11.0, or manual implementations) assume clean, continuous data. Vietnamese market data has specific edge cases:

1. **Ceiling/Floor price limits** — HOSE stocks can only move ±7% from reference price per day. This means:
   - Bollinger Bands at default 2σ width may never be breached because price is artificially constrained
   - RSI rarely hits extreme values (>90 or <10) in a single day
   - Limit-up/limit-down days have zero volume at the extreme — the stock is "locked" but indicators don't reflect demand

2. **Low liquidity tickers** — outside VN30, many HOSE stocks trade sporadically. Indicators on a stock that trades 100 shares/day are meaningless.

3. **Lookback period edge cases** — 200-day MA requires 200 trading days of data (~10 months in Vietnam with holidays). Newly listed stocks or stocks resuming from suspension won't have enough data.

4. **The `pandas-ta` library is in beta** (v0.4.71b0) — use `ta` (v0.11.0, stable) instead for production reliability.

**Prevention:**
1. **Filter by liquidity** before applying indicators — minimum average daily volume threshold (e.g., >100,000 shares/day)
2. **Handle insufficient data gracefully** — if a ticker has fewer candles than the lookback period, return `null` instead of calculating partial indicators
3. **Adjust Bollinger Band interpretation** for ±7% price limits — consider tighter bands (1.5σ) or percentage-based bands
4. **Track limit-up/limit-down days separately** — these are special events, not normal price action. Flag them in your data.
5. **Use `ta` library (stable)** over `pandas-ta` (perpetual beta)

**Detection:** If your indicator values cluster unnaturally (e.g., RSI always between 40-60), you likely have a data quality or calculation issue.

**Phase relevance:** Phase 2 (Technical Analysis) — must understand these before building indicator pipeline.

**Confidence:** HIGH for ceiling/floor limits (HOSE rule); MEDIUM for library recommendations.

---

## Minor Pitfalls

---

### Pitfall 11: Telegram Bot Anti-Patterns

**What goes wrong:**
- **Rate limiting:** Telegram allows max 30 messages/second to different chats, and 20 messages/minute to the same chat. Sending 400 ticker alerts simultaneously will get your bot throttled.
- **Message formatting:** Telegram MarkdownV2 requires escaping these characters: `_ * [ ] ( ) ~ > # + - = | { } . !` — financial data is full of these (prices with decimals, percentage signs, parentheses for negative numbers). Improperly escaped messages silently fail.
- **Message size:** Max 4096 characters per message. A detailed analysis of one ticker can exceed this.

**Prevention:**
1. **Queue and throttle messages** — send max 1 message per 3 seconds to the same chat. Use `asyncio.Queue` with rate limiting.
2. **Use HTML formatting instead of MarkdownV2** — `parse_mode="HTML"` is less fragile. `<b>bold</b>` is simpler than `*bold*` with escaping.
3. **Batch alerts** — instead of 400 individual messages, send "Top 10 Buy Signals Today" and "Top 10 Sell Signals Today" summary messages.
4. **Split long messages** at logical boundaries (not mid-sentence) when exceeding 4096 chars.
5. **Add inline keyboard buttons** for "Show More Details" rather than sending everything upfront.

**Phase relevance:** Phase 3 (Telegram Bot).

**Confidence:** HIGH for rate limits (well-documented Telegram API behavior).

---

### Pitfall 12: Over-Engineering for Personal Use

**What goes wrong:** This is a personal project for one user. Common over-engineering traps:
- Building a full authentication system (JWT, sessions, roles)
- Implementing microservices architecture (separate containers for crawler, API, dashboard)
- Adding Redis caching layer when PostgreSQL is sufficient
- Building a real-time WebSocket price feed when polling every 30 seconds is fine
- Creating an admin panel to manage crawl schedules when a cron job config file works
- Implementing CI/CD pipeline with staging/production environments

**Prevention:**
1. **Single deployable unit** — monorepo with FastAPI serving both API and scheduled tasks. No need for message queues, separate worker processes, or container orchestration.
2. **No auth** — a single API key in environment variable is sufficient. The project scope explicitly says "chỉ một người dùng."
3. **Simple scheduling** — APScheduler in FastAPI or system cron. No need for Celery, Redis, or RabbitMQ.
4. **Polling over WebSockets** — for personal use, refreshing dashboard data every 30-60 seconds is perfectly adequate. Real-time feeds add enormous complexity.
5. **SQLite for development, PostgreSQL for production** — but since Aiven PostgreSQL is already provisioned, just use PostgreSQL everywhere. Don't add a second database.

**Detection:** If you're spending more time on infrastructure than on the actual analysis logic, you're over-engineering.

**Phase relevance:** All phases — constant vigilance against complexity creep.

**Confidence:** HIGH — universal software engineering principle.

---

### Pitfall 13: Timezone Bugs Between UTC, UTC+7, and Database Storage

**What goes wrong:** The system spans multiple timezone contexts:
- HOSE trades in ICT (UTC+7) — all market times, session boundaries
- PostgreSQL `TIMESTAMP` stores without timezone; `TIMESTAMPTZ` stores in UTC
- Python `datetime` objects may be naive (no timezone) or aware
- Aiven servers likely run in UTC
- Telegram message timestamps are in UTC
- User sees Vietnamese time on dashboard

Mixing these causes: data stored at wrong date, duplicate crawls (or missed crawls) around midnight UTC (which is 7:00 AM in Vietnam — market opening!), and dashboard showing yesterday's data as today's.

**Prevention:**
1. **Store all timestamps as `TIMESTAMPTZ` in PostgreSQL** — always UTC internally
2. **Convert to UTC+7 only at display layer** (dashboard, Telegram messages)
3. **Use `zoneinfo` (Python 3.9+) or `pytz`** — never construct timezones manually
4. **All scheduler triggers in explicit UTC+7:**
   ```python
   # Good
   scheduler.add_job(crawl, 'cron', hour=15, minute=30, timezone='Asia/Ho_Chi_Minh')
   # Bad
   scheduler.add_job(crawl, 'cron', hour=8, minute=30)  # UTC? Local? Who knows?
   ```
5. **Trading date ≠ calendar date** — a HOSE trading day runs 09:00-15:00 UTC+7. Store the _trading date_ (e.g., `2026-04-15`) separately from the timestamp of when you crawled the data.

**Detection:** If your database shows two records for the same ticker on the same trading date, or zero records when the market was open, you have a timezone bug.

**Phase relevance:** Phase 1 (Database + Scheduling) — establish convention immediately.

**Confidence:** HIGH — universal but especially treacherous with UTC+7.

---

### Pitfall 14: Backtesting Bias When Using AI for Trading Signals

**What goes wrong:** When evaluating whether the AI trading assistant "works," you naturally look at historical data and check if the AI's signals would have been profitable. This is fundamentally flawed:
- **Look-ahead bias:** AI prompt includes news or data that wasn't available at signal time
- **Survivorship bias:** You're testing on the 400 tickers currently listed. Delisted companies (which may have gone bankrupt) are excluded, making the market look better than it was
- **Overfitting prompts:** Tuning prompt engineering until it "predicts" past events correctly = memorizing history, not building a useful system
- **Confirmation bias:** Remembering when the AI was right, forgetting when it was wrong

**Prevention:**
1. **Forward-test only** — start tracking AI signals from today forward. Record every signal with timestamp. Review accuracy after 1-3 months of live data.
2. **Paper trading log** — record every AI "buy/sell/hold" signal with the price at signal time. Track outcomes without actual money.
3. **Track hit rate honestly** — build a simple table: `signal_date, symbol, signal_type, price_at_signal, price_after_7d, price_after_30d`
4. **Never adjust prompts to match past performance** — adjust based on forward-test results only
5. **Disclaimer mindset** — the AI is a research assistant, not an oracle. It organizes your data and highlights patterns. You make the decision.

**Detection:** If your AI has >70% accuracy on backtests, you almost certainly have a bias problem. Real trading signal accuracy for even the best models is typically 52-58%.

**Phase relevance:** Phase 3-4 (AI Analysis → Dashboard) — important from the moment AI generates signals.

**Confidence:** HIGH — well-established in quantitative finance literature.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **Phase 1: Data Infrastructure** | API endpoints break silently (Pitfall 1) | Use vnstock as abstraction, validate every crawl, multi-source fallback |
| **Phase 1: Data Infrastructure** | Wrong trading schedule (Pitfall 3) | Schedule EOD crawl at 15:30 UTC+7, use vnstock's market status utility |
| **Phase 1: Data Infrastructure** | Timezone bugs (Pitfall 13) | TIMESTAMPTZ everywhere, explicit timezone in all scheduler configs |
| **Phase 1: Database** | PostgreSQL connection exhaustion (Pitfall 7) | Connection pool of 5-8, partition by year, proper composite indexes |
| **Phase 1: Database** | Unadjusted prices stored as ground truth (Pitfall 2) | Build corporate actions table and adjustment pipeline from day one |
| **Phase 2: Technical Analysis** | False signals on ceiling/floor days (Pitfall 10) | Filter by liquidity, flag limit-up/down, handle insufficient lookback |
| **Phase 2: Data Sources** | CafeF scraping breaks monthly (Pitfall 8) | Avoid CafeF; use vnstock VCI/KBS for financial reports and news |
| **Phase 3: AI Analysis** | Gemini hallucination (Pitfall 4) | Inject all data into prompts, never let AI recall financial facts |
| **Phase 3: AI Analysis** | API cost/rate explosion at 400 tickers (Pitfall 5) | Use Flash, batch by sector, tier analysis frequency |
| **Phase 3: Telegram Bot** | Message throttling + formatting failures (Pitfall 11) | HTML parse mode, queue with rate limiting, batch summaries |
| **Phase 3: AI Evaluation** | Backtesting bias (Pitfall 14) | Forward-test only, paper trading log, honest hit rate tracking |
| **All Phases** | Over-engineering (Pitfall 12) | Single deployable, no auth complexity, simple scheduling |
| **Ongoing** | vnstock freemium restrictions (Pitfall 6) | Pin version, have fallback plan for direct API calls |
| **Ongoing** | Holiday calendar misses (Pitfall 9) | Use vnstock MARKET_EVENTS, dynamic no-data detection |

---

## Sources

| Source | Type | Confidence |
|--------|------|------------|
| vnstock v3.5.1 source code (`vci/const.py`, `kbs/const.py`, `market.py`, `market_events.py`) | Primary — GitHub repository | HIGH |
| vnstock GitHub Issues (#218, #219, #210, #206, #182, #209) | Primary — community reports | HIGH |
| vnstock releases (v3.5.0, v3.4.0 changelogs) | Primary — release notes | HIGH |
| `ta` library v0.11.0 on PyPI | Primary — package registry | HIGH |
| `pandas-ta` v0.4.71b0 on PyPI (beta status) | Primary — package registry | HIGH |
| `google-generativeai` v0.8.6 / `google-genai` v1.73.1 on PyPI | Primary — package registry | MEDIUM |
| HOSE trading rules (±7% price limits, session structure) | Training data — verify with HOSE official site | MEDIUM |
| Telegram Bot API rate limits | Training data — verify with core.telegram.org/bots/faq | MEDIUM |
| Gemini API free tier limits | Training data — verify with ai.google.dev/pricing | LOW — verify current pricing page |
