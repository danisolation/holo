---
phase: 55-discovery-frontend
reviewed: 2025-01-28T12:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - backend/app/api/discovery.py
  - backend/app/api/router.py
  - frontend/e2e/fixtures/test-helpers.ts
  - frontend/e2e/interact-discovery.spec.ts
  - frontend/src/app/discovery/page.tsx
  - frontend/src/components/discovery-table.tsx
  - frontend/src/components/navbar.tsx
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 55: Code Review Report

**Reviewed:** 2025-01-28T12:00:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

The discovery feature is well-structured overall: the backend endpoint is clean with proper parameterized queries, the frontend uses `@tanstack/react-table` with good empty/loading/error state handling, and the API client correctly builds query strings. The main concern is a data consistency bug where the page header and the filtered table show different result counts, plus a flaky e2e test pattern.

## Warnings

### WR-01: Page header badge shows unfiltered count while table is filtered

**File:** `frontend/src/app/discovery/page.tsx:8`
**Issue:** `DiscoveryPage` calls `useDiscovery()` with no parameters (line 8), while `DiscoveryTable` (line 149 of `discovery-table.tsx`) calls `useDiscovery({ sector, signal_type })` with active filters. These are separate React Query cache entries. When a user filters by sector or signal, the page header badge still displays the total unfiltered count (e.g., "50 mã") and the unfiltered `score_date`, which is misleading.
**Fix:** Remove the duplicate `useDiscovery()` call from `page.tsx` and either lift the filter state up so the page can use the same filtered query, or move the badge/date display into `DiscoveryTable` where the filtered data is available:

```tsx
// Option A: Move badge + date into DiscoveryTable (simplest)
// In page.tsx — remove useDiscovery hook, just render structure:
export default function DiscoveryPage() {
  return (
    <div data-testid="discovery-page">
      <h2 className="text-2xl font-bold tracking-tight mb-2">
        Khám phá cổ phiếu
      </h2>
      <DiscoveryTable />
    </div>
  );
}

// In discovery-table.tsx — add badge + date using the already-fetched filtered data
```

### WR-02: Flaky e2e test uses hardcoded timeout instead of condition-based wait

**File:** `frontend/e2e/interact-discovery.spec.ts:19`
**Issue:** `page.waitForTimeout(3000)` is a hardcoded sleep that makes the test flaky — it may pass or fail depending on network/server speed. This directly affects test reliability.
**Fix:** Replace with a condition-based wait that checks for the actual state transition:

```typescript
// Wait for skeleton to disappear (loading finished)
await expect(page.locator('.space-y-2 .animate-pulse').first())
  .toBeHidden({ timeout: 10000 });

// Or wait for either rows or empty state to appear
await expect(
  page.locator('[data-testid="discovery-table"] table tbody tr, text=Chưa có dữ liệu khám phá').first()
).toBeVisible({ timeout: 10000 });
```

## Info

### IN-01: Invalid signal_type values are silently ignored

**File:** `backend/app/api/discovery.py:93`
**Issue:** When `signal_type` is provided but not in `SIGNAL_COLUMNS` (e.g., `?signal_type=invalid`), the filter is silently skipped and unfiltered results are returned. This could confuse API consumers who think they're filtering but aren't.
**Fix:** Return a 422 for invalid signal types:

```python
if signal_type and signal_type not in SIGNAL_COLUMNS:
    from fastapi import HTTPException
    raise HTTPException(status_code=422, detail=f"Invalid signal_type: {signal_type}. Must be one of: {', '.join(SIGNAL_COLUMNS.keys())}")
```

Alternatively, use a `Literal` type or `Enum` in the query parameter to let FastAPI validate automatically.

### IN-02: Stale data check does not account for weekends or holidays

**File:** `frontend/src/components/discovery-table.tsx:125-132`
**Issue:** `isStaleData` uses a flat 1.5-day threshold. Data scored on Friday will show as stale on Monday (~2.5 days), causing a false "Dữ liệu cũ" warning every Monday morning. Vietnamese stock market holidays will also trigger false warnings.
**Fix:** A simple improvement is to check the day-of-week and extend the threshold for weekends:

```typescript
function isStaleData(scoreDate: string): boolean {
  const today = new Date();
  const score = new Date(scoreDate);
  const diffMs = today.getTime() - score.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  // Allow extra days for weekends (Sat/Sun)
  const dayOfWeek = today.getDay(); // 0=Sun, 1=Mon
  const threshold = dayOfWeek <= 1 ? 3.5 : 1.5; // Mon/Sun: allow 3.5 days
  return diffDays > threshold;
}
```

---

_Reviewed: 2025-01-28T12:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
