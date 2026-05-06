# Phase 75: Async Patterns & Bulk Operations - Context

**Gathered:** 2026-05-06
**Status:** Ready for execution
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Move CPU-bound parsing (BeautifulSoup, DataFrame) to asyncio.to_thread() and convert financial service row-by-row upsert to bulk INSERT ON CONFLICT DO UPDATE.

Requirements: PERF-01, PERF-02

</domain>

<decisions>
## Implementation Decisions

All at agent's discretion — pure infrastructure phase.

</decisions>
