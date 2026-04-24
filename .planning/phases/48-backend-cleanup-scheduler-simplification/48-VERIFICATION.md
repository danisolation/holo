---
phase: 48-backend-cleanup-scheduler-simplification
verified: 2026-04-24T13:57:29Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 48: Backend Cleanup & Scheduler Simplification Verification Report

**Phase Goal:** All dead features are fully removed — corporate events, HNX/UPCOM support, and telegram dependency — and the scheduler pipeline is simplified to a reliable HOSE-only chain
**Verified:** 2026-04-24T13:57:29Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The daily scheduler pipeline runs end-to-end on HOSE tickers only, with chain trigger rewired from UPCOM to HOSE completion | ✓ VERIFIED | `manager.py` line 68: `event.job_id == "daily_price_crawl_hose"` triggers chain. `EXCHANGE_CRAWL_SCHEDULE` has only `"HOSE"`. Chain log messages confirm full flow: hose → indicators → AI → news → sentiment → combined → trading_signal → pick_generation → outcome_check → loss_check. No dead branches (corporate_action_check, hnx_upcom_analysis). `jobs.py` line 28: `VALID_EXCHANGES = ("HOSE",)`. Behavioral spot-check: `_JOB_NAMES` has no upcom/hnx/corporate keys — confirmed via Python import. |
| 2 | Corporate events are fully removed: DB table dropped via Alembic migration, API endpoints return 404, scheduler jobs removed, frontend page and nav link gone | ✓ VERIFIED | **DB:** Alembic 024 `op.drop_table("corporate_events")` with downgrade. **API:** `router.py` has no `corporate_events_router`. `corporate_events.py`, `corporate_event.py`, `corporate_event_crawler.py` all deleted. **Models:** `__init__.py` has no `CorporateEvent`. **Scheduler:** `daily_corporate_action_check` not in jobs.py or manager.py. **Frontend:** `corporate-events/page.tsx` dir deleted, `corporate-events-calendar.tsx` deleted, `navbar.tsx` NAV_LINKS has 6 items (no Sự kiện). `api.ts` and `hooks.ts` have no corporate events references. E2E tests have no corporate-events references. |
| 3 | All HNX/UPCOM references removed: exchange filter component, exchange badge, exchange store, tickers deactivated in DB, no frontend traces remain | ✓ VERIFIED | **Components:** `exchange-filter.tsx` and `exchange-badge.tsx` deleted. **Store:** `store.ts` has no `useExchangeStore` or `Exchange` type; includes `localStorage.removeItem("holo-exchange-filter")`. **Pages:** `page.tsx`, `dashboard/page.tsx`, `watchlist/page.tsx` have no ExchangeFilter/useExchangeStore. `ticker/[symbol]/page.tsx` has no ExchangeBadge or AnalyzeNowButton. `heatmap.tsx` has no ExchangeBadge/EXCHANGE_BORDER_COLORS. `watchlist-table.tsx` and `ticker-search.tsx` have no ExchangeBadge. **Layout:** metadata says "(HOSE)" only. **DB:** Migration 024 `UPDATE tickers SET is_active = false WHERE exchange IN ('HNX', 'UPCOM')`. **Backend API:** `tickers.py` line 49: `ALLOWED_EXCHANGES = {"HOSE"}`. **Grep:** Zero matches for ExchangeFilter/ExchangeBadge/useExchangeStore/CorporateEvent in frontend/src. Zero HNX/UPCOM in frontend/src. Only HNX/UPCOM mention in backend is a comment in manager.py line 124. |
| 4 | `python-telegram-bot` is removed from requirements.txt and the backend starts cleanly without it | ✓ VERIFIED | `requirements.txt` has 16 clean lines, no `telegram`. Behavioral spot-check: `from app.scheduler.manager import configure_jobs; from app.api.router import api_router; from app.models import Base` — all succeed without error. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/scheduler/manager.py` | HOSE-only scheduler chain | ✓ VERIFIED | `daily_price_crawl_hose` triggers chain, `EXCHANGE_CRAWL_SCHEDULE` HOSE-only, no dead job names |
| `backend/app/scheduler/jobs.py` | HOSE-only valid exchanges | ✓ VERIFIED | `VALID_EXCHANGES = ("HOSE",)`, no `daily_corporate_action_check` or `daily_hnx_upcom_analysis` functions |
| `backend/alembic/versions/024_drop_corporate_events.py` | Migration to drop corporate_events and deactivate HNX/UPCOM | ✓ VERIFIED | Contains `op.drop_table("corporate_events")` in upgrade, `UPDATE tickers SET is_active = false WHERE exchange IN ('HNX', 'UPCOM')`, proper downgrade |
| `backend/requirements.txt` | Clean dependencies without telegram | ✓ VERIFIED | 16 lines, no `python-telegram-bot` |
| `backend/app/api/router.py` | No corporate events router | ✓ VERIFIED | 8 routers registered, none corporate events |
| `backend/app/models/__init__.py` | No CorporateEvent model | ✓ VERIFIED | 20 models imported, no CorporateEvent |
| `backend/app/api/tickers.py` | HOSE-only ALLOWED_EXCHANGES | ✓ VERIFIED | Line 49: `ALLOWED_EXCHANGES = {"HOSE"}` |
| `frontend/src/components/navbar.tsx` | No corporate events nav link | ✓ VERIFIED | NAV_LINKS has 6 entries, no `/dashboard/corporate-events` |
| `frontend/src/lib/store.ts` | Watchlist store only, no exchange store | ✓ VERIFIED | Only `useWatchlistStore`, `localStorage.removeItem("holo-exchange-filter")` cleanup present |
| `frontend/src/app/page.tsx` | Home page without exchange filter | ✓ VERIFIED | No ExchangeFilter, no useExchangeStore, `<Heatmap data={data} />` with no exchange prop, static subtitle |
| `frontend/src/components/heatmap.tsx` | Heatmap without exchange badges | ✓ VERIFIED | No ExchangeBadge import, no EXCHANGE_BORDER_COLORS, clean `HeatmapProps` with only `data` |
| Deleted: `backend/app/api/corporate_events.py` | Should not exist | ✓ VERIFIED | File gone |
| Deleted: `backend/app/models/corporate_event.py` | Should not exist | ✓ VERIFIED | File gone |
| Deleted: `backend/app/crawlers/corporate_event_crawler.py` | Should not exist | ✓ VERIFIED | File gone |
| Deleted: `frontend/src/app/dashboard/corporate-events/` | Should not exist | ✓ VERIFIED | Directory gone |
| Deleted: `frontend/src/components/corporate-events-calendar.tsx` | Should not exist | ✓ VERIFIED | File gone |
| Deleted: `frontend/src/components/exchange-filter.tsx` | Should not exist | ✓ VERIFIED | File gone |
| Deleted: `frontend/src/components/exchange-badge.tsx` | Should not exist | ✓ VERIFIED | File gone |
| Deleted: `backend/tests/test_corporate_actions.py` | Should not exist | ✓ VERIFIED | File gone |
| Deleted: `backend/tests/test_corporate_actions_enhancements.py` | Should not exist | ✓ VERIFIED | File gone |
| Deleted: `backend/tests/test_corporate_events_api.py` | Should not exist | ✓ VERIFIED | File gone |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `manager.py` | `jobs.py` | EVENT_JOB_EXECUTED chaining on `daily_price_crawl_hose` | ✓ WIRED | Line 68: `event.job_id == "daily_price_crawl_hose"` → imports `daily_indicator_compute` from jobs → schedules it. Full chain verified via log messages. |
| `manager.py` chain | `daily_pick_generation` | Direct chain from `daily_trading_signal_triggered` | ✓ WIRED | Line 123-131: `trading_signal_triggered` → `daily_pick_generation`. No intermediate `hnx_upcom_analysis` step. |
| `navbar.tsx` | NAV_LINKS | No `/dashboard/corporate-events` entry | ✓ WIRED | NAV_LINKS array has 6 entries: /, /watchlist, /dashboard, /coach, /journal, /dashboard/health |
| `store.ts` | localStorage | Cleanup of `holo-exchange-filter` | ✓ WIRED | Line 6: `localStorage.removeItem("holo-exchange-filter")` runs at module import |
| `page.tsx` | `Heatmap` | No exchange prop | ✓ WIRED | Line 120: `<Heatmap data={data} />` — no exchange prop passed |
| `page.tsx` | `useMarketOverview` | No exchange arg | ✓ WIRED | Line 11: `useMarketOverview()` — no exchange argument |
| `dashboard/page.tsx` | `useMarketOverview` | No exchange arg | ✓ WIRED | Line 32: `useMarketOverview()` — no exchange argument |
| `watchlist-table.tsx` | `useMarketOverview` | No exchange arg | ✓ WIRED | Line 77: `useMarketOverview()` — no exchange argument |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Manager imports cleanly, no dead job IDs | `python -c "from app.scheduler.manager import _JOB_NAMES; assert 'daily_price_crawl_upcom' not in _JOB_NAMES"` | `manager import OK` | ✓ PASS |
| VALID_EXCHANGES is HOSE-only | `python -c "from app.scheduler.jobs import VALID_EXCHANGES; assert VALID_EXCHANGES == ('HOSE',)"` | `VALID_EXCHANGES OK` | ✓ PASS |
| Dead functions removed from jobs.py | `python -c "import app.scheduler.jobs as j; assert not hasattr(j, 'daily_corporate_action_check')"` | `dead functions removed OK` | ✓ PASS |
| Router + models import cleanly | `python -c "from app.api.router import api_router; from app.models import Base"` | `router + models import OK` | ✓ PASS |
| Migration 024 has correct content | `python -c "...assert 'drop_table' in txt..."` | `migration OK` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| CLN-01 | 48-01, 48-02 | Xóa toàn bộ tính năng corporate events (DB tables, API endpoints, scheduler jobs, frontend pages) | ✓ SATISFIED | Alembic 024 drops table, API endpoint removed from router, scheduler jobs removed, frontend page+calendar+nav link deleted, API types/hooks cleaned |
| CLN-02 | 48-01, 48-02 | Xóa hỗ trợ sàn HNX & UPCOM (chỉ giữ HOSE), rewire scheduler chain an toàn từ UPCOM→HOSE trigger | ✓ SATISFIED | Chain fires from `daily_price_crawl_hose`, EXCHANGE_CRAWL_SCHEDULE HOSE-only, VALID_EXCHANGES HOSE-only, ALLOWED_EXCHANGES HOSE-only, exchange filter/badge deleted, exchange store removed, tickers deactivated in migration, layout metadata updated |
| CLN-03 | 48-01 | Xóa python-telegram-bot khỏi requirements.txt (dead dependency từ v7.0) | ✓ SATISFIED | `requirements.txt` has 16 lines, no `python-telegram-bot`. Backend imports succeed cleanly. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | Zero TODO/FIXME/PLACEHOLDER/stub patterns detected across all modified files |

### Human Verification Required

No human verification items needed. All truths are programmatically verified through file inspection, grep scans, and Python import spot-checks.

### Gaps Summary

No gaps found. All 4 success criteria verified. All 3 requirements satisfied. All deleted files confirmed gone. All modified files confirmed clean of dead references. Backend imports succeed. Full scheduler chain wired correctly from HOSE through to consecutive_loss_check.

---

_Verified: 2026-04-24T13:57:29Z_
_Verifier: the agent (gsd-verifier)_
