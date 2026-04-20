---
phase: 24-api-analytics-engine
plan: "01"
subsystem: paper-trading-api
tags: [api, crud, paper-trading, manual-follow, config]
dependency_graph:
  requires: [22-01, 22-02, 23-01]
  provides: [paper-trading-api-router, paper-trade-schemas, paper-trade-analytics-service]
  affects: [24-02]
tech_stack:
  added: []
  patterns: [session-per-request, pydantic-v2-schemas, service-class-injection]
key_files:
  created:
    - backend/app/schemas/paper_trading.py
    - backend/app/services/paper_trade_analytics_service.py
    - backend/app/api/paper_trading.py
    - backend/tests/test_paper_trade_api.py
  modified:
    - backend/app/api/router.py
decisions:
  - POST /trades/follow placed before GET /trades/{trade_id} to avoid FastAPI path conflict
  - Schema tests (no DB mocks) — validates Pydantic input constraints directly
  - 12 tests cover all ManualFollowRequest validators + SimulationConfigUpdateRequest bounds
metrics:
  duration: 3 min
  completed: 2026-04-20
  tasks_completed: 2
  tasks_total: 2
  test_count: 12
  test_pass: 12
  files_created: 4
  files_modified: 1
---

# Phase 24 Plan 01: Paper Trading CRUD API + Manual Follow Summary

Paper trading REST API with 6 endpoints (trade list/detail/follow/close + config get/put), Pydantic v2 schemas with field validators, analytics service class, and 12 schema validation tests all passing.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `65a535b` | Pydantic schemas + PaperTradeAnalyticsService with CRUD + manual follow + config methods |
| 2 | `28bc151` | 6 API endpoints, router registration, 12 schema validation tests |

## What Was Built

### Pydantic Schemas (`backend/app/schemas/paper_trading.py`)
- **ManualFollowRequest** (PT-09): symbol, direction (long|bearish), entry_price (>0), stop_loss (>0), take_profit_1/2 (>0), timeframe (swing|position), confidence (1-10), position_size_pct (1-100)
- **PaperTradeResponse**: Full trade detail with symbol resolution, all price/date/status fields
- **PaperTradeListResponse**: Paginated trade list with total count
- **SimulationConfigResponse**: initial_capital, auto_track_enabled, min_confidence_threshold
- **SimulationConfigUpdateRequest**: Partial update with nullable fields + validators

### Analytics Service (`backend/app/services/paper_trade_analytics_service.py`)
- **list_trades**: Filtered query with status/direction/timeframe + pagination (max 200), batch ticker resolution
- **get_trade**: Single trade by ID with 404 handling
- **create_manual_follow** (PT-09): Ticker resolution → position sizing via calculate_position_size() → R:R calc → PaperTrade with ai_analysis_id=None, status=PENDING
- **close_trade**: State transition validation via validate_transition() → CLOSED_MANUAL
- **get_config / update_config**: Singleton SimulationConfig (id=1) read/partial-update

### API Router (`backend/app/api/paper_trading.py`)
6 endpoints at `/api/paper-trading/*`:
1. `GET /trades` — List with filters + pagination
2. `POST /trades/follow` — Manual follow (PT-09), status 201
3. `GET /trades/{trade_id}` — Single trade detail
4. `POST /trades/{trade_id}/close` — Manual close
5. `GET /config` — Simulation config
6. `PUT /config` — Partial config update

### Tests (`backend/tests/test_paper_trade_api.py`)
12 tests in 2 classes:
- **TestManualFollowSchema** (8 tests): valid long/bearish, invalid direction, confidence bounds, entry_price positive, position_size_pct bounds, invalid timeframe, model_dump
- **TestConfigUpdateSchema** (4 tests): partial update, empty update, min_confidence bounds, initial_capital positive

## Threat Mitigations Applied

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-24-01 Tampering ManualFollowRequest | Pydantic Field validators on all inputs | ✅ Verified by 8 tests |
| T-24-02 Tampering DB queries | SQLAlchemy ORM parameterized queries only | ✅ No raw SQL |
| T-24-03 DoS list_trades | Pagination limit max=200 via Query(ge=1, le=200) | ✅ |
| T-24-04 Tampering query params | Pattern validators on Query params + enum conversion | ✅ |

## Deviations from Plan

### Auto-added (Rule 2 - Missing Functionality)

**1. [Rule 2] Added extra test coverage beyond plan spec**
- **Found during:** Task 2
- **Issue:** Plan specified 8 tests but additional edge cases (invalid timeframe, model_dump, config bounds) improve coverage
- **Fix:** Added 4 extra tests: test_invalid_timeframe_rejected, test_model_dump_produces_dict, test_min_confidence_bounds, test_initial_capital_must_be_positive
- **Files modified:** backend/tests/test_paper_trade_api.py
- **Commit:** 28bc151

## Known Stubs

None — all endpoints are wired to real service methods with DB queries.

## Self-Check: PASSED
