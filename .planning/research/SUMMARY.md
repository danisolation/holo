# Project Research Summary

**Project:** Holo — v12.0 Rumor Intelligence
**Domain:** Community rumor crawling & AI scoring for Vietnamese stock market
**Researched:** 2025-07-21
**Confidence:** HIGH

## Executive Summary

Holo v12.0 adds a rumor intelligence layer by crawling Vietnamese stock community posts from Fireant.vn and scoring them with Gemini AI. The critical discovery is that CafeF's forum is dead (all URLs return 404), reducing scope to a single community source — Fireant.vn — which fortunately has an excellent REST JSON API (`restv2.fireant.vn/posts`) with a long-lived guest JWT (expires 2029). This simplification is a net positive: one clean API source is better than two fragile scraping targets.

The recommended approach requires **zero new Python dependencies**. The existing stack (httpx, tenacity, google-genai, SQLAlchemy) covers HTTP crawling, retry/resilience, AI scoring, and storage. The architecture mirrors the proven CafeF news → AI analysis pipeline exactly — new `FireantCrawler` and `RumorScoringService` classes following established patterns, 2 new DB tables (`community_posts`, `rumor_scores`), and insertion into the APScheduler job chain after existing analysis completes. This is a feature addition, not an architectural change.

The primary risks are: (1) Gemini rate limit contention — rumor scoring adds a 6th analysis type competing for 15 RPM, mitigated by batching posts per-ticker and chaining after existing analysis; (2) Fireant content encoding — HTML entities in Vietnamese text must be decoded before AI processing; (3) noise-to-signal ratio — most community posts are noise, requiring pre-filtering and engagement-weighted prompting. All risks have proven mitigation patterns already in the codebase.

## Key Findings

### Recommended Stack

No new dependencies. The existing `requirements.txt` covers every need for v12.0. This is the cleanest possible outcome — zero dependency risk, zero version conflicts, zero new attack surface.

**Core technologies (all existing):**
- **httpx** (>=0.28): Async HTTP client for Fireant REST API calls
- **tenacity** (>=9.1): Retry logic with exponential backoff for API resilience
- **google-genai** (>=1.73): Gemini AI structured output for rumor scoring
- **SQLAlchemy** (>=2.0.49) + **asyncpg**: ORM + async driver for 2 new tables
- **Python stdlib `html.unescape()`**: HTML entity decoding for Fireant content (no library needed)
- **Python 3.12 `datetime.fromisoformat()`**: Timezone-aware parsing of Fireant timestamps (no library needed)

**Only-if-needed:** `aiolimiter` for async rate limiting if Fireant starts returning 429s. Not needed today.

### Expected Features

**Must have (table stakes):**
- Fireant community post crawling — primary data source, everything depends on this
- Post deduplication via ON CONFLICT DO NOTHING — prevents wasted storage and AI tokens
- AI rumor credibility score (1-10) — core value proposition
- AI impact assessment (1-10) — which rumors matter
- Bullish/bearish/neutral classification — directional signal
- Rumor score display on ticker detail page — must be visible where users look
- Scheduled automated crawling — daily via APScheduler job chain
- Vietnamese language explanations — single user is Vietnamese speaker

**Should have (differentiators):**
- Rumor feed timeline — chronological rumor activity per ticker
- Watchlist rumor badges — at-a-glance rumor activity on watchlist table
- Engagement-weighted scoring — likes/replies as credibility signals
- Verified user boost — Fireant `isAuthentic` flag
- Key claims extraction — AI extracts specific factual claims from noise

**Defer (v2+):**
- Cross-ticker rumor correlation — needs post-MVP analysis, high complexity
- Historical rumor accuracy tracking — needs months of accumulated data
- CafeF forum scraping — forum is dead, permanently out of scope

### Architecture Approach

Mirror the existing CafeF news → sentiment analysis pipeline. No new architectural patterns needed — this is a "copy the pattern, change the source" feature. The job chain extends with two new steps (`fireant_crawl` → `rumor_scoring`) placed after `trading_signal` and before `pick_generation`. All Gemini access serialized through existing `_gemini_lock`. Crawling gated to watchlist tickers only (~15-30, not all 400).

**Major components:**
1. **FireantCrawler** — Fetches posts from Fireant REST API, stores in `community_posts` table. Mirrors CafeFCrawler exactly.
2. **RumorScoringService** — Reads unscored posts, batches by ticker, calls Gemini for structured scoring output. Mirrors AIAnalysisService.
3. **community_posts table** — Raw Fireant posts with dedup on `post_id`. Stores content, engagement metrics, author info.
4. **rumor_scores table** — AI-generated scores per ticker per date: credibility, impact, direction, reasoning.
5. **FastAPI endpoints + Frontend components** — Serve and display rumor data on ticker detail page and watchlist.

### Critical Pitfalls

1. **CafeF forum is dead** — All `/hoi-dap/` URLs return 404. Drop entirely from scope. Don't write any code targeting CafeF forums.
2. **Fireant token without refresh fallback** — Guest JWT expires 2029 but could be rotated. Store in `.env`, build auto-refresh: on 401 → fetch homepage → parse `__NEXT_DATA__` → extract new token.
3. **Vietnamese content encoding** — Fireant returns HTML entities (`&#233;`). Always `html.unescape()` before storing. Test with real data before building scoring pipeline.
4. **Gemini rate limit contention** — 6th analysis type competing for 15 RPM. Mitigate: use `_gemini_lock`, chain after other analysis, batch aggressively (one call per ticker, not per post).
5. **Noise-to-signal ratio** — Most Fireant posts are memes/spam. Pre-filter posts < 20 chars, weight by engagement, prompt Gemini to identify and ignore noise.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Database & Fireant Crawler
**Rationale:** Everything depends on having posts in the database. Crawler + storage is the foundation with zero AI complexity.
**Delivers:** `community_posts` table, Alembic migration, `FireantCrawler` class, working post ingestion for watchlist tickers.
**Addresses:** Fireant crawling, post deduplication, scheduled crawling (table stakes)
**Avoids:** Content encoding pitfall (test with real data here), token management pitfall (build .env storage + refresh fallback)
**Stack:** httpx, tenacity, SQLAlchemy, html.unescape() — all existing

### Phase 2: AI Rumor Scoring
**Rationale:** Requires Phase 1 posts to exist. This is the core value — raw posts without scoring are noise.
**Delivers:** `rumor_scores` table, `RumorScoringService`, Pydantic schema, Gemini prompt, scoring integration into job chain.
**Addresses:** Credibility scoring, impact assessment, direction classification, key claims extraction (table stakes + differentiators)
**Avoids:** Gemini rate limit pitfall (use _gemini_lock, batch per ticker), noise filtering pitfall (pre-filter + engagement weighting), duplicate scoring pitfall (track scored posts)
**Stack:** google-genai, SQLAlchemy — all existing

### Phase 3: API Endpoints & Frontend Display
**Rationale:** Requires Phase 2 scores to exist. No point building UI without data.
**Delivers:** FastAPI endpoints for rumor data, ticker detail page rumor panel, watchlist rumor badges.
**Addresses:** Rumor score display on ticker page, watchlist badges, rumor feed timeline (table stakes + differentiators)
**Avoids:** Stale scores pitfall (freshness indicators, date filtering in UI)

### Phase 4: Scheduler Integration & Polish
**Rationale:** Wire everything into the daily automated pipeline. Can be tested manually before automation.
**Delivers:** APScheduler job chain integration, end-to-end automated daily rumor intelligence.
**Addresses:** Automated scheduled crawling, chain ordering (after trading_signal, before pick_generation)
**Avoids:** Job chain string-based matching fragility (test chain ordering carefully)

### Phase Ordering Rationale

- **Strict dependency chain:** Posts must exist before scoring, scores must exist before display, display must work before automation.
- **Risk front-loading:** Phase 1 validates Fireant API integration with real data — if content encoding or token issues surface, they're caught before AI complexity enters.
- **Gemini budget safety:** Phase 2 can be tested in isolation before wiring into the full pipeline, ensuring rate limit budgets are verified.
- **Frontend last:** UI is the thinnest layer — mirrors existing ticker detail page patterns with minimal unknowns.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (AI Scoring):** Gemini prompt engineering for Vietnamese rumor classification needs iteration. Optimal batch size (posts per Gemini call) is unknown — test with real data from Phase 1.
- **Phase 4 (Scheduler):** Job chain string-based matching is fragile (flagged as critical pitfall). Need to understand exact chain mechanism in `scheduler/manager.py` before modifying.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Crawler):** Directly mirrors CafeFCrawler — pattern is well-established, API is verified working.
- **Phase 3 (API + Frontend):** Standard CRUD endpoints + React components — no novel patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | Zero new dependencies. All libraries already battle-tested across 560 tests. Fireant API verified live. |
| Features | **HIGH** | Feature set is clear, grounded in existing patterns. CafeF removal simplifies scope. |
| Architecture | **HIGH** | Direct mirror of existing CafeF → AI pipeline. No architectural innovation needed. |
| Pitfalls | **HIGH** | All pitfalls identified from live testing (CafeF 404, Fireant API responses) or known codebase constraints (Gemini RPM). |

**Overall confidence:** HIGH

### Gaps to Address

- **Gemini prompt quality for Vietnamese rumors:** No precedent in codebase for rumor-specific scoring. Prompt will need iteration — include this as explicit task in Phase 2.
- **Optimal batch size for Gemini calls:** Unknown whether 20 posts per ticker in one Gemini call produces good results or overwhelms context. Test empirically in Phase 2.
- **Fireant API undocumented rate limits:** No rate limiting observed in testing, but production crawling of 30 tickers may trigger throttling. Monitor in Phase 1.
- **Job chain insertion point:** Exact mechanism for adding steps to APScheduler chain (`EVENT_JOB_EXECUTED` listener) needs code review during Phase 4 planning. String-based job name matching is flagged as fragile.

## Sources

### Primary (HIGH confidence)
- Fireant.vn REST API — live tested `restv2.fireant.vn/posts?symbol=VNM` (2025-07-21), response structure documented
- Fireant guest JWT — decoded from page HTML `__NEXT_DATA__`, exp=2029-11-17, scopes verified
- CafeF forum — live tested all `/hoi-dap/` URL patterns, all return 404 (2025-07-21)
- Existing codebase — `cafef_crawler.py`, `ai_analysis_service.py`, `resilience.py`, `scheduler/manager.py`, `config.py`

### Secondary (MEDIUM confidence)
- Gemini RPM budget estimate (~21 calls/day with rumor scoring) — calculated from known usage patterns, not measured
- Fireant rate limiting behavior — no throttling observed in light testing, production behavior unknown

---
*Research completed: 2025-07-21*
*Ready for roadmap: yes*
