# Technology Stack

**Project:** Holo v10.0 — Watchlist-Centric & Stock Discovery
**Researched:** 2025-07-23

## Recommended Stack

### No New Dependencies Required

v10.0 is an **architectural restructuring** of existing components, not a new technology adoption. The current stack handles all requirements:

### Core (Unchanged)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | existing | REST API + WebSocket | Already serving all endpoints; adding 1 new router |
| PostgreSQL (Aiven) | existing | Primary database | Adding 1 new table + 1 new column via Alembic |
| APScheduler 3.11 | existing | In-process job scheduling | Adding 1 new job to existing chain |
| Google Gemini | gemini-2.5-flash-lite | AI analysis | **Usage decreases** — watchlist gating reduces calls by ~70% |
| SQLAlchemy 2.x | existing | Async ORM | New model + modified queries |
| Alembic | existing | DB migrations | 1 migration for new table + column |

### Frontend (Unchanged)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Next.js | 16 | React framework | Adding 1 new route (/discovery) |
| TypeScript | existing | Type safety | New types for discovery API |
| Tailwind CSS | 4 | Styling | Existing utility classes |
| shadcn/ui | existing | UI components | Cards, badges, tables — all exist |
| TanStack React Query | existing | Data fetching | 1-2 new query hooks |
| TanStack Table | existing | Data tables | Used in watchlist-table.tsx, discovery can reuse |
| lightweight-charts | existing | Candlestick charts | No changes needed |

### Supporting Libraries (Unchanged)

| Library | Version | Purpose | Relevant to v10.0 |
|---------|---------|---------|-------------------|
| `ta` | existing | Technical indicators | Discovery scoring reads indicator data computed by this |
| `vnstock` | 3.5.1 | VN market data | Price crawl unchanged |
| `loguru` | existing | Logging | New service logging |
| `tenacity` | existing | Retry logic | May use for discovery scan resilience |

## What Changes

### Backend Changes (No New Deps)

| Change | Files | Description |
|--------|-------|-------------|
| New SQLAlchemy model | `models/discovery_result.py` | `discovery_results` table model |
| New service | `services/discovery/` | Scoring engine + discovery service |
| New service | `services/watchlist_service.py` | Watchlist query helpers |
| New router | `api/discovery.py` | Discovery REST endpoints |
| Modified model | `models/user_watchlist.py` | Add `sector_group` column |
| Modified scheduler | `scheduler/manager.py`, `scheduler/jobs.py` | Add discovery job, gate AI jobs |
| Modified API | `api/watchlist.py` | Sector group CRUD |
| New migration | `alembic/versions/` | Schema changes |

### Frontend Changes (No New Deps)

| Change | Files | Description |
|--------|-------|-------------|
| New page | `src/app/discovery/page.tsx` | Discovery route |
| New components | `src/components/discovery-*.tsx` | Discovery cards, filters |
| Modified component | `src/components/heatmap.tsx` | Watchlist-only mode |
| Modified component | `src/components/watchlist-table.tsx` | Sector group column |
| Modified component | `src/components/navbar.tsx` | Add nav link |
| Modified lib | `src/lib/api.ts`, `src/lib/hooks.ts` | Types + hooks |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Discovery scoring | Pure computation from indicators | Gemini API scoring | 15 RPM rate limit, 200s+ pipeline time, unnecessary cost |
| Sector grouping | Column on user_watchlist | Separate watchlist_groups table | Over-engineering for single-user; simple column sufficient |
| Heatmap data | Frontend composition | New API endpoint | Duplicates existing market-overview logic |
| Discovery results | Dedicated table | Reuse ai_analyses | Different schema, different retention, different purpose |
| Job scheduling | Sequential chain fork | Parallel execution | DB pool too small (5+3); sequential is safe |

## Installation

```bash
# No new packages needed!
# Backend: existing requirements.txt is sufficient
# Frontend: existing package.json is sufficient

# Only action: run Alembic migration after schema changes
cd backend
alembic upgrade head
```

## Sources

- Codebase analysis of `requirements.txt` and `package.json`
- Config analysis of `config.py` (Gemini settings, DB pool)
- AIAnalysisService existing `ticker_filter` support
