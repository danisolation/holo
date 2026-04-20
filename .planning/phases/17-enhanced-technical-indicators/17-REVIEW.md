---
phase: 17-enhanced-technical-indicators
reviewed: 2026-04-20T22:15:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - backend/tests/test_indicator_service.py
  - backend/alembic/versions/010_enhanced_indicators.py
  - backend/app/models/technical_indicator.py
  - backend/app/services/indicator_service.py
  - backend/app/schemas/analysis.py
  - backend/app/api/analysis.py
  - frontend/src/components/ui/accordion.tsx
  - frontend/src/lib/api.ts
  - frontend/src/components/indicator-chart.tsx
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-04-20T22:15:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 17 adds ATR(14), ADX(14) with +DI/-DI, and Stochastic(14,3) to the existing indicator pipeline. The implementation is solid — it correctly extends the backend computation, migration, model, schema, API, and frontend charts following established patterns.

**Key positives:**
- **Critical warm-up pitfall handled correctly.** The research identified that `ta` library ATR/ADX classes produce `0.0` during warm-up instead of `NaN`. The implementation correctly applies `.replace(0.0, float('nan'))` on all four affected Series (ATR, ADX, +DI, -DI), while leaving Stochastic untouched (it already produces proper NaN). This was the highest-risk item.
- **DB migration is clean.** 6 nullable `Numeric(12,4)` columns added in upgrade, dropped in reverse order in downgrade. Revision chain (009→010) is correct.
- **API response schema is complete.** All 4 layers (migration → model → schema → endpoint mapping) include the 6 new fields in sync.
- **Accordion API usage is correct.** Verified against `@base-ui/react` v1.4.0 type definitions — `multiple` is the correct prop name (not `openMultiple`). `keepMounted` defaults to `false`, so collapsed chart components (ATR, ADX, Stochastic) only mount when expanded — no wasted chart creation.
- **Chart colors/lineWidths exactly match UI-SPEC.** All 6 data lines and 3 reference lines verified.

No critical issues found. One warning about test mock data shape, and three minor info-level items.

## Warnings

### WR-01: Test mock data shape doesn't match updated query columns

**File:** `backend/tests/test_indicator_service.py:148`
**Issue:** The `test_skips_ticker_with_few_data_points` mock returns 2-element tuples `(date, close)`, but the real `compute_for_ticker` query now returns 4 columns `(date, close, high, low)`. The test passes because the `len(rows) < 20` early-exit triggers before DataFrame construction, but the mock is inconsistent with reality. A future developer writing a happy-path test based on this mock pattern would get confusing errors.
**Fix:**
```python
mock_result.fetchall.return_value = [
    (f"2024-01-{i:02d}", 100.0 + i, 102.0 + i, 98.0 + i) for i in range(1, 11)
]
```

## Info

### IN-01: Unused type import `IChartApi`

**File:** `frontend/src/components/indicator-chart.tsx:8`
**Issue:** `type IChartApi` is imported from `lightweight-charts` but never used anywhere in the file.
**Fix:** Remove the unused import:
```typescript
import {
  createChart,
  LineSeries,
  HistogramSeries,
} from "lightweight-charts";
```

### IN-02: ADX accordion legend missing reference line text per UI-SPEC

**File:** `frontend/src/components/indicator-chart.tsx:542-548`
**Issue:** The UI-SPEC copywriting contract specifies the ADX legend should include `25 xu hướng mạnh` (the strong trend reference line label), but the accordion trigger only shows `ADX · +DI · -DI`. The RSI trigger includes its reference line labels (`70 quá mua · 30 quá bán`), so this is an inconsistency.
**Fix:** Add the reference line legend:
```tsx
<span className="text-[#06B6D4]">ADX</span>
{" · "}
<span className="text-[#22C55E]">+DI</span>
{" · "}
<span className="text-[#EF4444]">-DI</span>
{" · "}
<span className="text-white/25">25 xu hướng mạnh</span>
```

### IN-03: Stochastic accordion legend missing reference line text per UI-SPEC

**File:** `frontend/src/components/indicator-chart.tsx:558-561`
**Issue:** Same pattern as IN-02. UI-SPEC specifies `%K · %D · 80 quá mua · 20 quá bán` but the accordion trigger only shows `%K · %D`.
**Fix:** Add overbought/oversold labels:
```tsx
<span className="text-[#EC4899]">%K</span>
{" · "}
<span className="text-[#818CF8]">%D</span>
{" · "}
<span className="text-[#ef5350]/40">80 quá mua</span>
{" · "}
<span className="text-[#26a69a]/40">20 quá bán</span>
```

---

_Reviewed: 2026-04-20T22:15:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
