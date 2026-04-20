---
phase: 20-trading-plan-dashboard-panel
reviewed: 2026-04-20T05:14:07Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - backend/app/schemas/analysis.py
  - backend/app/api/analysis.py
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/components/analysis-card.tsx
  - frontend/src/components/trading-plan-panel.tsx
  - frontend/src/app/ticker/[symbol]/page.tsx
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 20: Code Review Report

**Reviewed:** 2026-04-20T05:14:07Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 20 adds a Trading Plan Dashboard Panel to the ticker detail page, exposing the `raw_response` JSONB field from the backend through a new dedicated fetch function and React Query hook, then rendering it in a two-column LONG/BEARISH panel component.

**Overall assessment:** Clean, well-structured implementation. The backend change is minimal (one field addition to schema + one line in the endpoint). The frontend follows established patterns (api.ts types → hooks.ts query → component → page integration). The new `TradingPlanPanel` component handles edge cases (invalid signal with `confidence === 0`) and is well-composed. One data inconsistency in the summary endpoint and a few minor items noted below.

## Warnings

### WR-01: Summary endpoint omits `raw_response` for trading_signal — data inconsistency

**File:** `backend/app/api/analysis.py:393-401`
**Issue:** The `/summary` endpoint iterates all analysis types including `TRADING_SIGNAL` but constructs `AnalysisResultResponse` without passing `raw_response`. This means `GET /{symbol}/summary` returns `trading_signal.raw_response: null` while `GET /{symbol}/trading-signal` returns the full JSONB data. A future consumer of the summary endpoint (e.g., a summary card that tries to show TP/SL) would silently get `null` instead of the expected trading plan data.

The current frontend avoids this by using the dedicated `useTradingSignal` hook, so no user-facing bug exists today — but the API inconsistency is a latent trap.

**Fix:**
```python
# In get_analysis_summary(), around line 393, pass raw_response for trading signals:
for analysis_type in [AnalysisType.TECHNICAL, AnalysisType.FUNDAMENTAL,
                      AnalysisType.SENTIMENT, AnalysisType.COMBINED,
                      AnalysisType.TRADING_SIGNAL]:
    # ... existing query ...
    if analysis:
        response_kwargs = dict(
            ticker_symbol=symbol.upper(),
            analysis_type=analysis_type.value,
            analysis_date=analysis.analysis_date.isoformat(),
            signal=analysis.signal,
            score=analysis.score,
            reasoning=analysis.reasoning,
            model_version=analysis.model_version,
        )
        if analysis_type == AnalysisType.TRADING_SIGNAL:
            response_kwargs["raw_response"] = analysis.raw_response
        summary_data[analysis_type.value] = AnalysisResultResponse(**response_kwargs)
```

## Info

### IN-01: `TradingPlanEmpty` component exported but never imported

**File:** `frontend/src/components/trading-plan-panel.tsx:176`
**Issue:** `TradingPlanEmpty` is exported but not imported or used in any file. The page (`page.tsx:307-313`) renders `null` when no trading signal exists instead of showing this empty state. Either the component is dead code or it was intended to be used.
**Fix:** Either import and use it in `page.tsx` for a consistent empty state UX:
```tsx
) : (
  <section>
    <TradingPlanEmpty />
  </section>
)}
```
Or remove it if the "don't render anything" approach is intentional.

### IN-02: `AnalysisResult` frontend type missing `raw_response` field

**File:** `frontend/src/lib/api.ts:58-66`
**Issue:** The `AnalysisResult` interface doesn't include `raw_response`, even though the backend schema (`AnalysisResultResponse`) now returns it. The `fetchTradingSignal` function works around this via an intersection type (`AnalysisResult & { raw_response?: TickerTradingSignal }`), which is correct but means the base type doesn't fully match the backend schema.
**Fix:** Add the optional field to the base interface for type completeness:
```typescript
export interface AnalysisResult {
  ticker_symbol: string;
  analysis_type: string;
  analysis_date: string;
  signal: string;
  score: number;
  reasoning: string;
  model_version: string;
  raw_response?: Record<string, unknown> | null;  // Phase 20
}
```

### IN-03: Magic number threshold for TP2 visibility

**File:** `frontend/src/components/trading-plan-panel.tsx:96`
**Issue:** `Math.abs(plan.take_profit_2 - plan.take_profit_1) > 1` uses a hardcoded `1` as the threshold for deciding whether to show the second take-profit level. While sensible for VND prices (typically thousands), the intent is unclear without context.
**Fix:** Extract to a named constant:
```typescript
/** Minimum VND difference to show TP2 as distinct from TP1 */
const TP2_MIN_DIFF = 1;
// ...
{Math.abs(plan.take_profit_2 - plan.take_profit_1) > TP2_MIN_DIFF && (
```

---

_Reviewed: 2026-04-20T05:14:07Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
