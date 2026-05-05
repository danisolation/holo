---
phase: 52-discovery-engine-schema
verified: 2026-05-04T09:00:00Z
status: human_needed
score: 11/11 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run the full daily pipeline (or trigger daily_discovery_scoring manually) and confirm discovery_results table is populated with scored entries for ~400 tickers"
    expected: "SELECT count(*) FROM discovery_results WHERE score_date = CURRENT_DATE returns ~350-400 rows, each with non-NULL total_score and dimensions_scored >= 2"
    why_human: "Requires running scheduler against live database with real indicator/financial data — cannot verify data flow end-to-end via static code analysis"
---

# Phase 52: Discovery Engine & Schema — Verification Report

**Phase Goal:** A pure-computation discovery engine scores all ~400 HOSE tickers daily on technical and fundamental indicators, persisting results with 14-day retention
**Verified:** 2026-05-04T09:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `discovery_results` table exists with per-dimension score columns (RSI, MACD, ADX, volume, P/E, ROE) and composite total_score | ✓ VERIFIED | Model has 6 `*_score` Numeric(4,2) columns + `total_score` Numeric(5,2) + `dimensions_scored` Integer. Migration 026 creates table with FK to tickers, unique constraint on (ticker_id, score_date) |
| 2 | `sector_group` nullable column exists on `user_watchlist` table | ✓ VERIFIED | Migration 026 line 39: `op.add_column("user_watchlist", sa.Column("sector_group", sa.String(100), nullable=True))` |
| 3 | DiscoveryService can score all active HOSE tickers on 6 dimensions | ✓ VERIFIED | `score_all_tickers()` fetches HOSE tickers via TickerService, runs 3 batch queries (indicators, financials, volumes), applies 6 pure scoring functions (0-10 scale), bulk upserts via INSERT ON CONFLICT |
| 4 | Results older than 14 days are cleaned up at start of each scoring run | ✓ VERIFIED | `_cleanup_old_results()` deletes rows where `score_date < today - 14 days`, called as first step of `score_all_tickers()` |
| 5 | Scoring handles NULL indicator/financial data gracefully (skips dimension, not crash) | ✓ VERIFIED | All 6 scoring functions return `None` when input is `None`. Service counts non-null scores and skips tickers with `< MIN_DIMENSIONS=2` |
| 6 | Discovery scoring job runs daily after indicator_compute completes, before AI analysis | ✓ VERIFIED | manager.py chain: `indicator_compute → daily_discovery_scoring` (line 79-87), then `discovery_scoring → daily_ai_analysis` (line 88-93) |
| 7 | Scheduler chain order: price_crawl → indicators → discovery_scoring → ai_analysis → ... | ✓ VERIFIED | manager.py line 327 log confirms full chain order includes `discovery_scoring` between indicators and AI |
| 8 | Old direct link from indicator_compute to ai_analysis is REPLACED (not duplicated) | ✓ VERIFIED | grep for direct indicator→ai_analysis link returns 0 matches. Chain now goes through discovery_scoring intermediary |
| 9 | Discovery job registered in _JOB_NAMES with triggered and manual variants | ✓ VERIFIED | manager.py lines 26-27: `daily_discovery_scoring_triggered` and `daily_discovery_scoring_manual` present in _JOB_NAMES dict |
| 10 | Unit tests verify all 6 scoring functions return correct values for boundary inputs | ✓ VERIFIED | 33 test methods across 7 test classes: RSI(5), MACD(6), ADX(4), Volume(5), P/E(5), ROE(5), Service(3). Boundary tests include: RSI 100→0, MACD ±5 clamping, P/E exactly 10→10, weak ADX, volume cap |
| 11 | Unit tests verify service handles empty/NULL data without crashing | ✓ VERIFIED | `test_none_returns_none` in each scoring class + `test_tickers_with_insufficient_dimensions_skipped` with all-None inputs |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/alembic/versions/026_discovery_results.py` | Alembic migration creating discovery_results table + sector_group column | ✓ VERIFIED | 44 lines. Creates table with 12 columns, FK, unique constraint. Adds sector_group to user_watchlist. Has downgrade. |
| `backend/app/models/discovery_result.py` | DiscoveryResult SQLAlchemy model | ✓ VERIFIED | 49 lines. 6 per-dimension score columns (Numeric(4,2)), total_score (Numeric(5,2)), dimensions_scored, UniqueConstraint, ForeignKey to tickers |
| `backend/app/services/discovery_service.py` | Discovery scoring engine with 6 scoring functions + service class | ✓ VERIFIED | 311 lines. 6 pure scoring functions + DiscoveryService class with batch queries, bulk upsert, 14-day cleanup |
| `backend/app/models/__init__.py` | DiscoveryResult import registered | ✓ VERIFIED | Line 31: `from app.models.discovery_result import DiscoveryResult` + exported in `__all__` |
| `backend/app/scheduler/jobs.py` | `daily_discovery_scoring` async job function | ✓ VERIFIED | Lines 715-744. Follows existing pattern: JobExecutionService, try/except, _determine_status, _build_summary |
| `backend/app/scheduler/manager.py` | Chain insertion + _JOB_NAMES registration | ✓ VERIFIED | Lines 26-27 (names), lines 79-93 (chain: indicator→discovery→AI), line 327 (log string) |
| `backend/tests/test_discovery_service.py` | Unit tests for scoring functions and service (min 80 lines) | ✓ VERIFIED | 229 lines. 33 test methods across 7 test classes |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `models/__init__.py` | `models/discovery_result.py` | `from app.models.discovery_result import DiscoveryResult` | ✓ WIRED | Line 31 imports + line 33 exports in `__all__` |
| `services/discovery_service.py` | `models/discovery_result.py` | `from app.models.discovery_result import DiscoveryResult` | ✓ WIRED | Line 18 import, used in delete query (line 200), upsert (line 296) |
| `services/discovery_service.py` | `models/technical_indicator.py` | Batch query for indicator data | ✓ WIRED | Line 19 import, used in subquery and join (lines 211-233) |
| `scheduler/manager.py` | `scheduler/jobs.py` | `from app.scheduler.jobs import daily_discovery_scoring` | ✓ WIRED | Line 80 import, line 83 passed to `scheduler.add_job()` |
| `scheduler/jobs.py` | `services/discovery_service.py` | `from app.services.discovery_service import DiscoveryService` | ✓ WIRED | Line 726 import, line 727 instantiated, line 728 `.score_all_tickers()` called |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `discovery_service.py` | `indicators` | `_fetch_latest_indicators()` → `TechnicalIndicator` table via SQLAlchemy | DB query with JOIN on max date | ✓ FLOWING |
| `discovery_service.py` | `financials` | `_fetch_latest_financials()` → `Financial` table via SQLAlchemy | DB query with JOIN on max id | ✓ FLOWING |
| `discovery_service.py` | `volumes` | `_fetch_avg_volumes()` → `DailyPrice` table via SQLAlchemy | DB query with AVG aggregate, 30-day window | ✓ FLOWING |
| `discovery_service.py` | `rows_to_upsert` | Computed from scoring functions | `INSERT ON CONFLICT DO UPDATE` to discovery_results | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Scoring functions importable | `python -c "from app.services.discovery_service import score_rsi, score_macd, score_adx, score_volume, score_pe, score_roe"` | Requires backend venv/context | ? SKIP — no venv in verification env |
| Test suite passes | `pytest backend/tests/test_discovery_service.py` | Requires backend venv + dependencies | ? SKIP — no venv in verification env |
| Score correctness (inline) | `score_rsi(25)=10, score_rsi(50)=5, score_macd(0)=5, score_pe(-5)=0` | Code review confirms math: 25≤30→10.0 ✓, 50→10-(50-30)*0.25=5.0 ✓, 0→(0+2)*2.5=5.0 ✓, -5≤0→0.0 ✓ | ✓ PASS (manual trace) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DISC-01 | 52-01, 52-02 | Hệ thống scan ~400 mã HOSE hàng ngày, tính điểm tiềm năng dựa trên kỹ thuật (RSI, MACD, ADX, volume) + cơ bản (P/E, ROE, tăng trưởng) | ✓ SATISFIED | DiscoveryService.score_all_tickers() with 6 scoring functions + scheduler chain integration running daily after indicator compute |
| DISC-02 | 52-01, 52-02 | Kết quả discovery lưu vào DB, giữ lịch sử 14 ngày | ✓ SATISFIED | discovery_results table via migration 026, bulk upsert to DB, 14-day cleanup in _cleanup_old_results() |

No orphaned requirements — REQUIREMENTS.md maps DISC-01 and DISC-02 to Phase 52, both claimed by plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `discovery_service.py` | 209, 249, 275 | `return {}` | ℹ️ Info | Defensive early-return guards for empty `ticker_ids` input — correct pattern, NOT stubs |

No TODOs, FIXMEs, placeholders, or empty implementations found across all 7 key files.

### Commits Verified

| # | Hash | Message | Status |
|---|------|---------|--------|
| 1 | `5b2ba9e` | feat(52-01): create DiscoveryResult model and migration 026 | ✓ Verified in git log |
| 2 | `be894ad` | test(52-01): add failing tests for DiscoveryService scoring engine | ✓ Verified in git log |
| 3 | `1690cb4` | feat(52-01): implement DiscoveryService scoring engine | ✓ Verified in git log |
| 4 | `d64baf4` | feat(52-02): wire discovery scoring into scheduler chain | ✓ Verified in git log |
| 5 | `a0ff52f` | test(52-02): enhance discovery scoring unit tests | ✓ Verified in git log |

### Human Verification Required

### 1. End-to-End Pipeline Execution

**Test:** Trigger the daily pipeline (or manually invoke `daily_discovery_scoring` via the scheduler admin) and verify `discovery_results` table is populated
**Expected:** `SELECT count(*) FROM discovery_results WHERE score_date = CURRENT_DATE` returns ~350-400 rows, each with `total_score > 0` and `dimensions_scored >= 2`
**Why human:** Requires running the scheduler against a live PostgreSQL database with real indicator and financial data — cannot verify runtime data flow via static code analysis

### Gaps Summary

No gaps found. All 11 must-haves verified through code inspection. All artifacts exist, are substantive (not stubs), properly wired, and data flows through real DB queries. All 5 commits verified in git history. Both requirements (DISC-01, DISC-02) satisfied.

One human verification item remains: confirming the full pipeline produces actual scored rows in production, which requires a running database with real data.

---

_Verified: 2026-05-04T09:00:00Z_
_Verifier: the agent (gsd-verifier)_
