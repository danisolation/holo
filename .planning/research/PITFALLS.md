# Domain Pitfalls

**Domain:** Watchlist-centric stock discovery integration
**Researched:** 2025-07-23

## Critical Pitfalls

Mistakes that cause pipeline failures, data loss, or broken daily workflows.

### Pitfall 1: Empty Watchlist Crashes the AI Pipeline

**What goes wrong:** User hasn't added any tickers to watchlist yet (or removes all). The AI pipeline receives an empty `ticker_filter`, and depending on implementation, either: (a) crashes with an empty-query error, (b) falls back to analyzing ALL 400 tickers (defeating the purpose), or (c) silently skips and breaks the chain so downstream jobs never run.

**Why it happens:** The watchlist-gating logic is new; existing code assumes there are always tickers to process. `analyze_all_tickers()` with an empty dict behaves differently than with `None` (which means "all tickers").

**Consequences:** Daily pipeline fails silently. No picks generated. User doesn't realize until they check the Coach page and see stale data.

**Prevention:**
1. `WatchlistService.get_watchlist_ticker_map()` returns empty dict when watchlist is empty
2. Each gated job checks `if not ticker_filter: log warning + return normally` (NOT raise)
3. Return normally so the chain continues — downstream jobs (pick_outcome_check, loss_check) should still run on existing data
4. If watchlist is empty, skip AI analysis but still generate a log entry in job_executions as "skipped"

**Detection:** Job execution records showing "skipped" status. Health dashboard shows 0 tickers analyzed.

### Pitfall 2: Chain Fork Breaks Job Execution Tracking

**What goes wrong:** Inserting `daily_discovery_scan` between `daily_indicator_compute` and `daily_ai_analysis` in the chain breaks the `_on_job_executed` listener. If the job ID doesn't exactly match the expected pattern, the next job in the chain never fires.

**Why it happens:** The chain logic in `manager.py` uses exact string matching: `if event.job_id in ("daily_indicator_compute_triggered", "daily_indicator_compute_manual")`. Adding a new intermediate job requires updating BOTH the outgoing chain (indicator to discovery) AND the incoming chain (discovery to AI analysis).

**Consequences:** The entire AI pipeline stops running. No analysis, no picks, no outcome checks. The pipeline silently dies at the fork point.

**Prevention:**
1. Update `_on_job_executed` in exact sequence:
   - `daily_indicator_compute_triggered` chains to `daily_discovery_scan`
   - `daily_discovery_scan_triggered` chains to `daily_ai_analysis`
2. Add `daily_discovery_scan_triggered` and `daily_discovery_scan_manual` to `_JOB_NAMES` dict
3. Test the full chain end-to-end after modification
4. Keep the existing `daily_indicator_compute_manual` behavior (manual triggers should still work)

**Detection:** Health dashboard pipeline timeline shows gap. Job execution records stop after indicator compute.

### Pitfall 3: Discovery Scan Monopolizes DB Pool During AI Pipeline

**What goes wrong:** If discovery scan runs concurrently with AI analysis (parallel fork), both compete for the DB connection pool (pool_size=5, max_overflow=3 = 8 max connections). Discovery reads ~400 tickers of indicators. AI analysis reads contexts + writes results. Pool exhaustion causes connection errors.

**Why it happens:** Aiven PostgreSQL has strict connection limits. The pool settings are intentionally conservative. Two heavy jobs running simultaneously is the exact scenario these limits prevent.

**Consequences:** One or both jobs fail with connection errors. Partial data in both discovery and AI results. Dead letter queue fills with false failures.

**Prevention:** Use sequential chain (recommended architecture). Discovery runs first (no Gemini, fast), then AI pipeline starts. Never run both simultaneously. If discovery takes >30s, investigate — it should be pure computation on cached indicator data.

**Detection:** DB pool monitoring on health dashboard. `asyncpg.exceptions.TooManyConnectionsError` in logs.

## Moderate Pitfalls

### Pitfall 4: Heatmap Shows Stale Data When Watchlist Changes

**What goes wrong:** User adds a ticker to watchlist. The heatmap doesn't show it because the market-overview data (cached by React Query) doesn't include sector_group. Or user removes a ticker but it still appears.

**Prevention:**
1. Invalidate both `watchlist` and `market-overview` React Query caches on watchlist mutation
2. Frontend composition: intersection of watchlist + market data. If either updates, the composition re-runs
3. `useWatchlist()` hook already returns on mutation success via `onSuccess: () => queryClient.invalidateQueries(["watchlist"])`. Extend to also invalidate heatmap-related queries

### Pitfall 5: Sector Group Defaults Don't Match vnstock Sector Names

**What goes wrong:** User adds ticker from discovery. System auto-fills `sector_group` from `Ticker.sector` (vnstock ICB classification). But vnstock sector names are long, inconsistent, or in English. User sees unexpected group names in heatmap.

**Prevention:**
1. Map vnstock sector names to consistent Vietnamese short names in the auto-suggest logic
2. Make sector_group user-editable (inline edit on watchlist table) — user can fix any bad default
3. Keep a small mapping dict server-side
4. If no mapping exists, use the raw vnstock sector name as-is

### Pitfall 6: Discovery Scoring Produces Unintuitive Rankings

**What goes wrong:** Pure technical scoring ranks a low-volume penny stock as "strong buy" because it has RSI < 30 + MACD crossover. But the ticker is illiquid garbage. User loses trust in discovery.

**Prevention:**
1. Include volume and market cap as scoring factors (like `pick_service.py`'s `compute_safety_score`)
2. Filter out tickers with avg daily volume < 100,000 shares from discovery results
3. Include ADX (trend strength) — strong signals in non-trending markets are noise
4. Show the score breakdown in the UI so user understands the ranking logic

### Pitfall 7: AI Analysis for Newly-Added Watchlist Tickers is Missing Until Next Day

**What goes wrong:** User adds ticker from discovery page at 10 AM. The daily AI pipeline ran at 15:30 yesterday and won't run again until 15:30 today. The ticker has no AI analysis until then.

**Prevention:**
1. When user adds ticker, show existing AI analysis if any exists (the system may have analyzed it before watchlist-gating)
2. Offer the "Phan tich ngay" button (already exists as `POST /api/analysis/{symbol}/analyze-now`) for immediate on-demand analysis
3. Set appropriate expectations in UI: "AI se phan tich ma nay vao phien toi (15:30)"
4. Don't block the add-to-watchlist flow on missing analysis

### Pitfall 8: Discovery Results Table Grows Unbounded

**What goes wrong:** 400 rows/day with no cleanup. Not catastrophic, but unnecessary storage on Aiven.

**Prevention:**
1. Retention policy: keep 7-14 days of discovery results
2. Add cleanup to the discovery job: `DELETE FROM discovery_results WHERE scan_date < NOW() - INTERVAL '14 days'`
3. Inline the cleanup in the discovery scan job for simplicity

## Minor Pitfalls

### Pitfall 9: Navigation Gets Crowded Again

**What goes wrong:** v9.0 reduced navigation from 7 to 5 items. Adding "Kham pha" (Discovery) makes it 6.

**Prevention:** Discovery is high-value enough to justify a nav slot. Alternatively, make it a tab on the existing home/overview page. But a dedicated route is cleaner.

### Pitfall 10: Sector Group Names Aren't Validated

**What goes wrong:** User types different spellings for the same sector. Heatmap shows two separate groups.

**Prevention:**
1. Provide a dropdown/combobox with existing group names + free text option
2. Show existing sector_group values as suggestions
3. Case-normalize on save

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| DB Migration | Column added NOT NULL without default | `sector_group` must be NULLABLE (existing rows have no value) |
| Discovery scheduler job | Job ID mismatch breaks chain | Exact string match in _on_job_executed; test full chain |
| Watchlist-gating AI jobs | Empty watchlist crashes pipeline | Guard clause in every gated job; return normally |
| Heatmap rework | Stale data after watchlist change | React Query cache invalidation on mutation |
| Discovery page | No discovery data on first deploy | Discovery job must run at least once; handle empty state in UI |
| Sector grouping | Inconsistent naming | Combobox with existing values as suggestions |
| Add-to-watchlist from discovery | Missing sector_group assignment | Auto-suggest from Ticker.sector; user can edit |

## Sources

- Scheduler chain analysis: `manager.py` lines 58-162 (exact job ID matching)
- DB pool config: `config.py` pool_size=5, max_overflow=3
- AIAnalysisService ticker_filter behavior: `ai_analysis_service.py` line 87-98
- Existing safety scoring pattern: `pick_service.py` compute_safety_score
- Watchlist cache invalidation: `hooks.ts` useMutation onSuccess patterns
- React Query stale data: `hooks.ts` staleTime settings
