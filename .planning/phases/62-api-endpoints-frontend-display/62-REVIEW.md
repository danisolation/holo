---
phase: 62-api-endpoints-frontend-display
reviewed: 2025-07-18T12:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - backend/app/api/rumors.py
  - backend/app/schemas/rumor.py
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/components/rumor-score-panel.tsx
  - frontend/src/components/rumor-feed.tsx
  - frontend/src/app/ticker/[symbol]/page.tsx
  - frontend/src/components/watchlist-table.tsx
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 62: Code Review Report

**Reviewed:** 2025-07-18T12:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 62 adds two backend GET endpoints (`/rumors/{symbol}` and `/rumors/watchlist/summary`), corresponding frontend fetch functions, React Query hooks, and two display components (`RumorScorePanel`, `RumorFeed`) integrated into the ticker detail page and watchlist table.

**Overall assessment: Clean implementation.** The code is well-structured with no critical issues.

Key positive observations:
- **No SQL injection risk** — all backend queries use SQLAlchemy ORM with parameterized statements; no raw SQL.
- **No XSS risk** — all frontend rendering uses React text interpolation (auto-escaped); no `dangerouslySetInnerHTML` or `innerHTML`.
- **Proper input encoding** — `fetchRumorScores` uses `encodeURIComponent(symbol)` for path parameters.
- **Error/loading states fully covered** — ticker detail page handles loading (skeleton), error (retry button), and empty data for the rumor section.
- **React Query keys are unique** — `["rumor-scores", symbol]` and `["watchlist-rumors"]` have no collisions with existing keys.
- **TypeScript types match backend schemas** — `RumorScoreData`, `RumorPost`, and `WatchlistRumorSummary` interfaces correctly mirror their Pydantic counterparts.
- **Route ordering is correct** — `/watchlist/summary` is defined before `/{symbol}` to prevent FastAPI from matching "watchlist" as a symbol parameter (line 36-37 comment).
- **Graceful degradation** — watchlist rumor column shows "—" when data is missing; score panel shows "Chưa có tin đồn" when no score exists.

## Warnings

### WR-01: API response schema loses enum validation for `direction` field

**File:** `backend/app/schemas/rumor.py:59`
**Issue:** `RumorScoreResponse.direction` and `WatchlistRumorSummary.dominant_direction` are typed as `str | None` instead of `RumorDirection | None`. The `RumorDirection` enum (lines 15-19) already exists in the same file with valid values `bullish`, `bearish`, `neutral`. Using bare `str` means the API contract permits any arbitrary string, making it possible for a future code change to accidentally pass invalid direction values without Pydantic catching it.

The frontend handles this gracefully (rumor-score-panel.tsx line 47-48 uses `?? null` fallback for unknown directions), so this is not a runtime crash risk — but it weakens the API contract.

**Fix:**
```python
# rumor.py line 59
class RumorScoreResponse(BaseModel):
    ...
    direction: RumorDirection | None = None
    ...

# rumor.py line 71
class WatchlistRumorSummary(BaseModel):
    ...
    dominant_direction: RumorDirection | None = None
```

## Info

### IN-01: Index-based React keys for list items

**File:** `frontend/src/components/rumor-feed.tsx:31`
**File:** `frontend/src/components/rumor-score-panel.tsx:87`
**Issue:** Both components use array index (`key={i}`) as the React key for list items. Since these are read-only feeds ordered by `posted_at DESC` and not subject to user reordering/insertion, index keys are functionally safe. However, if posts ever gain a unique `id` field from the backend, switching to stable keys would be preferred.
**Fix:** If backend adds `id` to `RumorPostResponse`, use `key={post.id}` instead of `key={i}`.

### IN-02: `posted_at` uses string type instead of datetime serialization

**File:** `backend/app/schemas/rumor.py:46`
**Issue:** `RumorPostResponse.posted_at` is typed as `str` and manually serialized via `.isoformat()` in `rumors.py:168`. Using `datetime` type with Pydantic's built-in serialization would be more idiomatic and would auto-validate the format. Same applies to `RumorScoreResponse.scored_date` (line 52).
**Fix:** Use `datetime | None` types and let Pydantic handle ISO serialization:
```python
from datetime import datetime

class RumorPostResponse(BaseModel):
    ...
    posted_at: datetime

class RumorScoreResponse(BaseModel):
    ...
    scored_date: datetime | None = None
```
Then in `rumors.py`, pass the raw datetime objects instead of calling `.isoformat()`.

---

_Reviewed: 2025-07-18T12:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
