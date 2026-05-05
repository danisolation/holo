# Technology Stack

**Project:** Holo v11.0 UX & Reliability Overhaul
**Researched:** 2026-05-06

## Recommended Stack

**No stack changes for v11.0.** The existing stack handles all requirements. This document confirms what stays and lists the minimal additions.

### Existing Stack (No Changes)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| FastAPI | ~0.135 | Backend API | ✅ Keep |
| APScheduler | 3.11.2 | Job scheduling + chaining | ✅ Keep |
| SQLAlchemy | ~2.0 | Async ORM | ✅ Keep |
| asyncpg | ~0.31 | PostgreSQL driver | ✅ Keep |
| PostgreSQL (Aiven) | — | Primary database | ✅ Keep |
| google-genai | ~1.73 | Gemini AI SDK | ✅ Keep |
| Next.js | 16 | Frontend framework | ✅ Keep |
| TanStack Query | ~5.x | Data fetching/caching | ✅ Keep |
| cmdk (via shadcn/ui Command) | — | Search dialog | ✅ Keep (fix usage) |
| Tailwind CSS | ~4.x | Styling | ✅ Keep |

### New Additions (Minimal)

| Technology | Purpose | Why |
|------------|---------|-----|
| **UptimeRobot or cron-job.org** | External keep-alive pinger | Free, zero code changes, prevents Render sleep |

### Explicitly NOT Adding

| Technology | Why Not |
|------------|---------|
| Redis/Valkey | Single-user app — Python dict cache is equivalent |
| Celery | APScheduler handles multiple cron triggers fine |
| Render paid tier | External pinger + query optimization solves 95% |
| Backend search endpoint | 400 tickers searchable client-side |
| Vercel Cron | Hobby plan may be limited to daily frequency |

## Installation

No new packages to install. All v11.0 changes use existing dependencies.

```bash
# Backend — no new dependencies
# Frontend — no new dependencies
```

## Sources

- Direct codebase analysis of `requirements.txt` and `package.json` — HIGH confidence
- All technology decisions based on existing proven stack — HIGH confidence
