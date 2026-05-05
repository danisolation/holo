# Phase 52: Discovery Engine & Schema - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

A pure-computation discovery engine scores all ~400 HOSE tickers daily on technical and fundamental indicators, persisting results with 14-day retention. Also adds `sector_group` column to `user_watchlist` table for Phase 54.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key research context:
- Discovery scoring uses PURE indicators (no Gemini) — RSI, MACD, ADX, volume, P/E, ROE
- Existing `compute_composite_score()` and `compute_safety_score()` in pick_service.py can be adapted
- Discovery job must run SEQUENTIALLY after indicators in scheduler chain (DB pool limit 5+3)
- Scheduler chain uses exact string matching on job IDs — one wrong ID silently kills downstream
- `ticker_filter` parameter already exists in AIAnalysisService — preparation for Phase 53

</decisions>

<code_context>
## Existing Code Insights

Codebase context will be gathered during plan-phase research.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>
