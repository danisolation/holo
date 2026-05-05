# Phase 57: Search Fix - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning
**Mode:** Auto-generated (surgical bug fix — root cause identified in research)

<domain>
## Phase Boundary

Fix ticker search to show all ~400 HOSE tickers instead of only the first 50. Add recent searches with localStorage persistence.

Two bugs found:
1. `ticker-search.tsx:54` — `.slice(0, 50)` truncates rendered items before cmdk filters
2. `trade-entry-dialog.tsx:280` — Same `.slice(0, 50)` pattern
3. `useTickers()` called without limit → backend default is `limit=100` → only 100 of 400 tickers

</domain>

<decisions>
## Implementation Decisions

### Search Fix
- Remove `.slice(0, 50)` from both ticker-search.tsx and trade-entry-dialog.tsx
- Pass `limit=500` to `useTickers()` in search components to fetch all tickers
- cmdk's `shouldFilter={true}` handles client-side filtering — no need to limit rendered items

### Recent Searches
- Store recent searches in localStorage under key `holo-recent-searches`
- Max 5 recent searches, most recent first
- Show recent searches group above main results when search input is empty
- Each recent search stores symbol + name for display

### the agent's Discretion
- Exact localStorage helper implementation
- Recent search UI styling within existing CommandGroup patterns

</decisions>

<code_context>
## Existing Code Insights

### Root Cause Files
- `frontend/src/components/ticker-search.tsx:54` — `.slice(0, 50)` truncation
- `frontend/src/components/trade-entry-dialog.tsx:280` — Same truncation
- `frontend/src/lib/hooks.ts:53` — `useTickers()` accepts limit param
- `backend/app/api/tickers.py:57` — Backend default `limit=100`, accepts up to 500

### Established Patterns
- cmdk (CommandDialog) with shouldFilter={true} for client-side search
- React Query via useTickers hook for data fetching
- Tailwind + shadcn/ui for styling

### Integration Points
- ticker-search.tsx — main search dialog (navbar)
- trade-entry-dialog.tsx — ticker selector in trade entry form

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond fixing the bug and adding recent searches.

</specifics>

<deferred>
## Deferred Ideas

- Search enrichment with sector/industry in results (v12.0+)
- Backend fuzzy search (overkill for 400 items)

</deferred>
