---
phase: 14-corporate-actions-enhancements
plan: 01
subsystem: backend
tags: [corporate-actions, rights-issue, migration, model]
dependency_graph:
  requires: []
  provides: [RIGHTS_ISSUE-event-type, alert_sent-column, migration-008]
  affects: [corporate_event_crawler, corporate_action_service, corporate_event_model]
tech_stack:
  added: []
  patterns: [TDD-red-green, alembic-migration, partial-index]
key_files:
  created:
    - backend/alembic/versions/008_corporate_actions_enhancements.py
    - backend/tests/test_corporate_actions_enhancements.py
  modified:
    - backend/app/models/corporate_event.py
    - backend/app/crawlers/corporate_event_crawler.py
    - backend/app/services/corporate_action_service.py
    - backend/tests/test_corporate_actions.py
decisions:
  - "RIGHTS_ISSUE factor returns 1.0 — rights are voluntary, no price adjustment"
  - "VNDirect API type code 'RIGHT' maps to internal 'RIGHTS_ISSUE'"
  - "alert_sent uses partial index (WHERE alert_sent = FALSE) for efficient unsent alert queries"
metrics:
  duration: ~5m
  completed: "2026-04-17T12:52:42Z"
  tests_added: 16
  tests_total: 37
  files_changed: 6
requirements: [CORP-06]
---

# Phase 14 Plan 01: RIGHTS_ISSUE Type + alert_sent Column Summary

**One-liner:** RIGHTS_ISSUE event type end-to-end (crawler→model→service) with alert_sent boolean for ex-date alert deduplication

## What Was Built

### Migration 008: alert_sent column
- Added `alert_sent BOOLEAN NOT NULL DEFAULT FALSE` to `corporate_events` table
- Partial index `idx_corporate_events_alert_sent` on `(alert_sent) WHERE alert_sent = FALSE` for efficient unsent-alert queries
- Standard revision chain: 008 → 007

### CorporateEvent Model Update
- New field: `alert_sent: Mapped[bool]` with `server_default="false"`
- Updated module docstring and event_type comment to include RIGHTS_ISSUE as 4th event type
- Imported `Boolean` from sqlalchemy

### Crawler RIGHTS_ISSUE Support
- `TYPE_MAP["RIGHT"] = "RIGHTS_ISSUE"` — maps VNDirect API type code
- `RELEVANT_TYPES` updated to include `"RIGHT"` in API query string
- Existing `_store_events` logic already handles non-CASH_DIVIDEND types via `ratio` field — RIGHTS_ISSUE falls into that path naturally

### Factor Formula
- Explicit `RIGHTS_ISSUE` handler in `_compute_single_factor` returns `Decimal("1.0")`
- Per CONTEXT.md: rights are voluntary (user may or may not subscribe) — no price adjustment
- Dilution impact will be displayed separately in UI (future plan)

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1-RED | Failing tests for alert_sent + migration | `42ea417` | tests/test_corporate_actions_enhancements.py |
| 1-GREEN | Migration 008 + model alert_sent | `2e5660c` | 008_migration, corporate_event.py, tests |
| 2-RED | Failing tests for RIGHTS_ISSUE | `5214810` | tests/test_corporate_actions_enhancements.py |
| 2-GREEN | RIGHTS_ISSUE in crawler + service | `105a548` | crawler, service, tests |

## Test Results

**16 new tests** across 4 test classes:

- `TestAlertSentField` (3): model attribute, column properties, docstring
- `TestRightsIssueTypeMapping` (4): TYPE_MAP, RELEVANT_TYPES, size, regression
- `TestRightsIssueFactor` (6): factor=1.0 with ratio, zero ratio, no ratio; regression for CASH_DIVIDEND, STOCK_DIVIDEND, BONUS_SHARES
- `TestMigration008` (3): importable, revision chain, upgrade/downgrade

**21 existing tests** all pass (zero regressions).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing TYPE_MAP size assertion**
- **Found during:** Task 2 GREEN
- **Issue:** `test_corporate_actions.py::TestCrawlerTypeMapping::test_type_mapping` asserted `len(TYPE_MAP) == 3`, now fails with 4 entries
- **Fix:** Updated assertion to `len(TYPE_MAP) == 4` with updated comment
- **Files modified:** `backend/tests/test_corporate_actions.py`
- **Commit:** `105a548`

## Decisions Made

1. **RIGHTS_ISSUE factor = 1.0**: Rights issues are voluntary — user may or may not subscribe. No price adjustment needed. Dilution impact shown separately in UI per CONTEXT.md.
2. **VNDirect "RIGHT" type code**: Mapped to internal "RIGHTS_ISSUE" following established TYPE_MAP pattern.
3. **Partial index on alert_sent**: `WHERE alert_sent = FALSE` optimizes the common query path for unsent alerts (most events will eventually have alert_sent=TRUE).

## Self-Check: PASSED
