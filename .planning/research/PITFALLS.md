# Domain Pitfalls — v12.0 Rumor Intelligence

**Domain:** Community rumor crawling & AI scoring for Vietnamese stock market
**Researched:** 2025-07-21

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: CafeF Forum Is Dead — Don't Build for It
**What goes wrong:** Planning/building CafeF forum scraping for a feature that no longer exists
**Why it happens:** PROJECT.md scope says "CafeF forum" but the forum has been removed
**Consequences:** Wasted development time, blocked feature, scope confusion
**Prevention:** Verified live — all `/hoi-dap/` URLs return 404. Drop CafeF forum from scope entirely. Use Fireant.vn as sole community source. Existing CafeF news article scraping remains unaffected.
**Detection:** Any code referencing CafeF forum URLs or CSS selectors for forum content

### Pitfall 2: Fireant Guest Token Hardcoded Without Refresh
**What goes wrong:** Token hardcoded in code, eventually expires or gets rotated, crawler silently fails
**Why it happens:** Token works today (expires 2029), so no urgency to build refresh
**Consequences:** Crawler returns 401, no new posts crawled, rumor scores go stale with no alert
**Prevention:** 
1. Store token in `.env` / settings (not in source code)
2. Build auto-refresh fallback: if 401 → fetch Fireant homepage → parse `__NEXT_DATA__` → extract new token
3. Circuit breaker will catch repeated 401s and alert via existing health monitoring
**Detection:** 401 responses from Fireant API, circuit breaker opening

### Pitfall 3: Fireant Content Encoding Issues
**What goes wrong:** Vietnamese text from Fireant API appears garbled (mojibake)
**Why it happens:** Fireant returns HTML entities in content (`&#233;`), plus potential double-encoding. Response may use different encoding than expected.
**Consequences:** Garbled text sent to Gemini → garbage rumor scores
**Prevention:**
1. Always decode with `html.unescape()` before storing
2. Ensure httpx response encoding is correct (`response.encoding = 'utf-8'`)
3. Store decoded text in PostgreSQL (UTF-8 by default)
4. Test with real Fireant data before building scoring pipeline
**Detection:** Non-Vietnamese characters in community_posts table content

### Pitfall 4: Gemini Rate Limit Exhaustion
**What goes wrong:** Rumor scoring competes with existing 5 analysis types for 15 RPM Gemini quota
**Why it happens:** Adding a 6th analysis type without accounting for rate budget
**Consequences:** Existing analysis pipeline slows down or fails, rumor scoring times out
**Prevention:**
1. Use existing `_gemini_lock` (asyncio.Lock) to serialize all Gemini access
2. Schedule rumor scoring AFTER other analysis completes (chain, don't parallelize)
3. Batch aggressively: one Gemini call per ticker, not per post
4. Consider lower priority: if Gemini quota is tight, score fewer tickers or skip rumor scoring
**Detection:** Gemini 429 errors increasing, analysis pipeline taking longer than usual

## Moderate Pitfalls

### Pitfall 5: Noise-to-Signal Ratio in Fireant Posts
**What goes wrong:** Most Fireant posts are noise (memes, one-word reactions, spam), AI scores garbage
**Why it happens:** Community forums naturally have low signal-to-noise ratio
**Prevention:**
1. Pre-filter before Gemini: skip posts with content < 20 chars, skip pure emoji posts
2. Weight by engagement: prioritize posts with likes > 0 or replies > 0
3. Prompt Gemini to explicitly identify and ignore noise
4. Include `isAuthentic` flag — verified users may have higher signal
**Detection:** Rumor scores consistently low/uniform across all tickers, reasoning mentions "no substantive content"

### Pitfall 6: Duplicate Scoring on Re-crawl
**What goes wrong:** Same posts re-crawled, re-scored, wasting Gemini tokens
**Why it happens:** Overlapping crawl windows, same posts appearing across runs
**Prevention:**
1. `community_posts` has ON CONFLICT DO NOTHING on `post_id` (dedup at storage)
2. Track which posts have been scored (boolean column or separate tracking)
3. Only send unscored posts to Gemini
**Detection:** Gemini usage metrics show rumor scoring using more tokens than expected

### Pitfall 7: Scoring Stale Posts
**What goes wrong:** Crawling posts from weeks ago, scoring them as current rumors
**Why it happens:** Fireant API returns posts in reverse chronological order with no date filter
**Prevention:**
1. Filter posts by `date` field — only score posts from last N days (configurable, default 3)
2. Mark rumor scores with the date range they cover
3. Frontend shows freshness indicator on rumor scores
**Detection:** Rumor scores referencing events that already resolved

### Pitfall 8: Over-Engineering the Scoring Schema
**What goes wrong:** Complex multi-dimensional scoring schema that's hard to display and interpret
**Why it happens:** Temptation to add many scoring dimensions (credibility, impact, urgency, source quality, corroboration, etc.)
**Prevention:** Keep it simple: credibility (1-10), impact (1-10), direction (bullish/bearish/neutral), reasoning (text). Can always add dimensions later.
**Detection:** Schema has more than 5-6 fields, frontend struggles to display meaningfully

## Minor Pitfalls

### Pitfall 9: Fireant API Schema Changes
**What goes wrong:** Fireant changes their API response structure, crawler breaks
**Prevention:** Parse defensively with `.get()` and defaults. Log unexpected response shapes. Circuit breaker catches systematic failures.

### Pitfall 10: Timezone Handling
**What goes wrong:** Fireant returns `+07:00` timestamps, stored/compared incorrectly
**Prevention:** Python 3.12 `datetime.fromisoformat()` handles timezone offsets natively. Store as timezone-aware datetime in PostgreSQL (`TIMESTAMP WITH TIME ZONE`).

### Pitfall 11: Crawling All Tickers Instead of Watchlist
**What goes wrong:** Crawling 400 tickers × 20 posts = 8000 posts per run
**Prevention:** Gate Fireant crawling to watchlist tickers only (typically 15-30). Same pattern as v10.0 AI pipeline gating.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Fireant Crawler | Content encoding (Pitfall 3) | Test with real data, decode HTML entities |
| Fireant Crawler | Token management (Pitfall 2) | .env storage + auto-refresh fallback |
| Rumor Scoring | Rate limit (Pitfall 4) | _gemini_lock, chain after other analysis |
| Rumor Scoring | Noise filtering (Pitfall 5) | Pre-filter short posts, weight by engagement |
| API + Frontend | Stale scores (Pitfall 7) | Freshness indicator, date filtering |
| Scheduler | Duplicate scoring (Pitfall 6) | Track scored posts, only send new ones |

## Sources

- CafeF forum death: Live tested all URL patterns — 404 (2025-07-21)
- Fireant content encoding: Observed HTML entities in live API response
- Fireant token: JWT decoded, exp=2029, client_id=fireant.tradestation
- Gemini rate limits: Documented in PROJECT.md constraints (15 RPM free tier)
- Existing patterns: CafeFCrawler dedup, _gemini_lock, watchlist gating
