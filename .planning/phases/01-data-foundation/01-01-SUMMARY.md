---
phase: 01-data-foundation
plan: "01"
subsystem: backend-foundation
tags: [fastapi, sqlalchemy, alembic, postgresql, project-scaffold]
dependency_graph:
  requires: []
  provides: [backend-skeleton, orm-models, db-migration, test-infrastructure]
  affects: [01-02, 01-03]
tech_stack:
  added: [fastapi-0.135, sqlalchemy-2.0.49, asyncpg-0.31, alembic-1.18, pydantic-settings-2.13, loguru-0.7, vnstock-3.5.1, apscheduler-3.11, tenacity-9.1, httpx-0.28, pytest-8, pytest-asyncio-0.24]
  patterns: [async-sqlalchemy-engine, pydantic-settings-config, fastapi-lifespan, yearly-table-partitioning]
key_files:
  created:
    - backend/requirements.txt
    - backend/.gitignore
    - backend/.env.example
    - backend/app/__init__.py
    - backend/app/config.py
    - backend/app/database.py
    - backend/app/main.py
    - backend/app/models/__init__.py
    - backend/app/models/ticker.py
    - backend/app/models/daily_price.py
    - backend/app/models/financial.py
    - backend/app/services/__init__.py
    - backend/app/crawlers/__init__.py
    - backend/app/scheduler/__init__.py
    - backend/app/api/__init__.py
    - backend/app/schemas/__init__.py
    - backend/alembic.ini
    - backend/alembic/env.py
    - backend/alembic/script.py.mako
    - backend/alembic/versions/001_initial_schema.py
    - backend/pytest.ini
    - backend/tests/__init__.py
    - backend/tests/conftest.py
  modified: []
decisions:
  - Async SQLAlchemy with asyncpg driver — pool_size=5 max_overflow=3 for Aiven limits
  - Yearly partitioning for daily_prices (2023-2026) — ~100K rows/year manageable
  - Raw DDL in Alembic migration for PARTITION BY (ORM can't express this)
  - Module-level settings = Settings() — requires DATABASE_URL env var at import time
metrics:
  duration: 7m
  completed: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  files_created: 24
  files_modified: 0
---

# Phase 01 Plan 01: Backend Project Scaffold & Database Schema Summary

**One-liner:** FastAPI skeleton with async SQLAlchemy, 3 ORM models (Ticker/DailyPrice/Financial), Alembic migration with yearly-partitioned daily_prices, and pytest foundation — all wired to pydantic-settings config reading from .env.

## What Was Built

### Task 1: Project scaffolding, dependencies & configuration
- Created full `backend/` directory structure with 7 sub-packages (models, services, crawlers, scheduler, api, schemas, tests)
- `requirements.txt` with 13 pinned dependencies including vnstock==3.5.1, fastapi[standard]>=0.135, sqlalchemy>=2.0.49
- `config.py` with pydantic-settings `Settings` class: database_url, crawl params (batch_size, delay, retries), scheduler params (hour, minute, timezone)
- `database.py` with async engine (pool_size=5, max_overflow=3, pool_pre_ping=True, echo=False) and `get_db()` FastAPI dependency
- `main.py` with FastAPI app, lifespan handler (engine.dispose on shutdown), health endpoint
- `.env.example` with documented placeholder values; `.gitignore` excludes .venv/, .env, __pycache__/

### Task 2: SQLAlchemy models, Alembic migration, test foundation
- **Ticker model:** symbol (unique, indexed), name, sector, industry, exchange (default HOSE), market_cap, is_active, timestamps
- **DailyPrice model:** OHLCV with Numeric(12,2), BigInteger volume, adjusted_close (nullable for Phase 2), composite PK (date, id) for partitioning, unique constraint (ticker_id, date)
- **Financial model:** P/E, P/B, EPS, ROE, ROA, revenue, net_profit, growth rates, health ratios — period-based with unique constraint (ticker_id, period)
- **Alembic async env.py:** Uses settings.database_url directly, bypasses alembic.ini sqlalchemy.url
- **Migration 001:** Raw DDL creating tickers, daily_prices (PARTITION BY RANGE date) with 4 yearly partitions (2023-2026), financials with indexes
- **pytest.ini:** asyncio_mode=auto, testpaths=tests
- **conftest.py:** mock_db_session (AsyncMock) and mock_vnstock (MagicMock) fixtures

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | f1b793b | Project scaffolding, dependencies & configuration |
| 2 | 2be1fef | SQLAlchemy models, Alembic migration with yearly partitioning, pytest foundation |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all files are fully implemented per plan specification. The `adjusted_close` column in DailyPrice is intentionally nullable (documented: "NULL until corporate actions handling in Phase 2").

## Threat Mitigations Applied

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-01-01 | .env in .gitignore; .env.example has placeholder values only | ✅ Applied |
| T-01-02 | Migration uses op.execute with literal SQL; no user input interpolation | ✅ Applied |
| T-01-03 | echo=False on engine; database_url not exposed in API responses | ✅ Applied |
| T-01-04 | pool_size=5, max_overflow=3 (max 8 connections for Aiven) | ✅ Applied |

## Verification Results

```
✅ from app.main import app → title = "Holo - Stock Intelligence"
✅ from app.models import Base → tables = ['daily_prices', 'financials', 'tickers']
✅ from app.config import Settings → fields include database_url, vnstock_source, crawl_batch_size, daily_crawl_hour
✅ All 7 __init__.py files exist
✅ Migration file contains PARTITION BY RANGE (date) and 4 yearly partitions
✅ pytest discovers test directory (0 tests collected — expected for foundation)
```

## Self-Check: PASSED

All 24 created files verified on disk. Both task commits (f1b793b, 2be1fef) confirmed in git log.

## Notes for Next Plans

- **Plan 01-02 (OHLCV Crawler):** Will use Ticker model, DailyPrice model, database session, and config settings
- **Plan 01-03 (Scheduler & API):** Will wire APScheduler into FastAPI lifespan and add API routes
- **User action required before Plan 02 or running migrations:** Set `DATABASE_URL` in `backend/.env` with real Aiven connection string (see .env.example for format)
