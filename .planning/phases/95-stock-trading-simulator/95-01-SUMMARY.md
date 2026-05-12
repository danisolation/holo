---
phase: 95-stock-trading-simulator
plan: 01
one_liner: "Remove all coach/training feature code, update nav to /simulator"
completed: "2026-05-12T09:42:00Z"
duration: ~4min
tasks_completed: 2
tasks_total: 2
key_files:
  modified:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - frontend/src/components/navbar.tsx
    - frontend/src/lib/hooks.ts
    - frontend/src/lib/api.ts
  deleted:
    - backend/app/api/behavior.py
    - backend/app/api/goals.py
    - backend/app/services/behavior_service.py
    - backend/app/services/goal_service.py
    - backend/app/models/behavior_event.py
    - backend/app/models/habit_detection.py
    - backend/app/models/trading_goal.py
    - backend/app/models/weekly_review.py
    - backend/app/models/weekly_prompt.py
    - backend/app/models/risk_suggestion.py
    - backend/app/models/sector_preference.py
    - backend/app/schemas/behavior.py
    - backend/app/schemas/goals.py
    - frontend/src/app/coach/page.tsx
    - frontend/src/components/pick-card.tsx
    - frontend/src/components/almost-selected-list.tsx
    - frontend/src/components/profile-settings-card.tsx
    - frontend/src/components/pick-performance-cards.tsx
    - frontend/src/components/pick-history-table.tsx
    - frontend/src/components/trades-table.tsx
    - frontend/src/components/delete-trade-dialog.tsx
    - frontend/src/components/trade-entry-dialog.tsx
    - frontend/src/components/post-trade-card.tsx
    - frontend/src/components/risk-suggestion-banner.tsx
    - frontend/src/components/habit-detection-card.tsx
    - frontend/src/components/viewing-stats-card.tsx
    - frontend/src/components/sector-preferences-card.tsx
    - frontend/src/components/monthly-goal-card.tsx
    - frontend/src/components/weekly-prompt-card.tsx
    - frontend/src/components/weekly-review-card.tsx
decisions:
  - "Keep UserRiskProfile model (used by pick_service and trade_service)"
  - "Keep accuracy-card.tsx (cleanly separable, reusable for simulator)"
  - "Keep postBehaviorEvent in api.ts (fire-and-forget, used by ticker-search.tsx)"
  - "Keep DailyPickResponse interface (may be reused for simulator signals)"
---

# Phase 95 Plan 01: Remove Coach Feature Summary

Remove all coach/training feature code from backend and frontend, update navigation to point to /simulator.

## Task Results

### Task 1: Remove coach backend code ✅
**Commit:** `8dd5170`

- Deleted 13 backend files: 2 API routers, 2 services, 7 models, 2 schemas
- Cleaned router.py: removed behavior_router and goals_router imports + include_router calls
- Cleaned models/__init__.py: removed 7 model imports and __all__ entries
- Kept UserRiskProfile (still used by pick_service.py and trade_service.py)

### Task 2: Remove coach frontend code and update navigation ✅
**Commit:** `be603fd`

- Deleted frontend/src/app/coach/ directory (page.tsx)
- Deleted 16 coach component files
- Updated navbar: `/coach` → `/simulator`, "Huấn luyện" → "Mô phỏng"
- Removed 19 coach hooks from hooks.ts and their API imports
- Removed coach API functions + interfaces from api.ts (~300 lines)
- Kept accuracy-card.tsx (no coach coupling, uses useAccuracyStats)
- Kept postBehaviorEvent + BehaviorEventCreate (fire-and-forget, used by ticker-search.tsx)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Kept postBehaviorEvent in api.ts**
- **Found during:** Task 2
- **Issue:** ticker-search.tsx and use-behavior-tracking.ts import postBehaviorEvent which was in the removal block
- **Fix:** Retained postBehaviorEvent and BehaviorEventCreate interface in api.ts to avoid broken imports
- **Files modified:** frontend/src/lib/api.ts

## Known Stubs

None — this plan only removes code.

## Metrics

- **Files deleted:** 30
- **Files modified:** 5
- **Lines removed:** ~5,407 (1,958 backend + 3,449 frontend)
- **Duration:** ~4 minutes
