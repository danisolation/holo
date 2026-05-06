# Phase 74: Crawler Efficiency - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Crawlers fetch data in parallel with controlled concurrency, insert in bulk, and share a single ticker map per job run. Parallelize crawler fetch phase with asyncio.Semaphore, use multi-row INSERT ON CONFLICT for rumor/news crawlers, and centralize ticker map lookup to reuse per job run.

Requirements: CRAWL-01, CRAWL-02, CRAWL-03

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Respect existing rate-limiting delays (fireant_delay, cafef_delay) even with parallelism.

</decisions>

<code_context>
## Existing Code Insights

- `app/crawlers/fireant_crawler.py:91-118` — sequential per-ticker fetch
- `app/crawlers/cafef_crawler.py:73-95` — sequential per-ticker fetch
- `app/crawlers/vietstock_crawler.py:94-155` — sequential per-feed fetch
- `app/crawlers/vnexpress_crawler.py` — single RSS feed fetch
- `app/scheduler/jobs.py` — daily_rumor_crawl() runs 4 crawlers sequentially, each creates its own ticker map
- Insert patterns: single-row INSERT per post in fireant/cafef/vietstock crawlers
- `app/services/price_service.py` — already uses bulk upsert (good pattern to follow)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
