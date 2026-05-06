# Phase 72: N+1 Query Fixes & Pagination - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

List and summary endpoints use batch queries instead of per-item loops, and return paginated results with stable ordering. Fix N+1 in rumor watchlist summary (3 queries per ticker → 1 batch aggregate), fix N+1 in AI context builder (sequential per-ticker DB queries → batch-fetch per dimension), and add pagination to watchlist/rumor/analysis list endpoints.

Requirements: DB-N1-01, DB-N1-02, DB-PAGE-01

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

- `app/api/rumors.py:40-120` — rumor watchlist summary does 3 queries per ticker (Rumor count, RumorScore avg, dominant direction)
- `app/services/analysis/context_builder.py:38-149` — per-ticker sequential DB queries for technical (3 queries), fundamental (1), sentiment (1)
- `app/api/watchlist.py:99-205` — returns all rows without pagination
- `app/api/analysis.py:417-443` — fixed limits without cursor pagination
- Existing pagination pattern: offset/limit with total count in some endpoints

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>
