# Technology Stack — v9.0 UX Rework & Simplification

**Project:** Holo Stock Intelligence Platform
**Researched:** 2026-04-23
**Scope:** Stack additions, removals, and changes for UX rework milestone

---

## Existing Stack (Validated — No Changes Needed)

These are confirmed working and do NOT need replacement or upgrade:

| Layer | Technology | Version | Status |
|-------|-----------|---------|--------|
| Backend | Python 3.12, FastAPI | 0.135.x | ✓ Keep |
| ORM | SQLAlchemy 2.0 + asyncpg | 2.0.49 / 0.31 | ✓ Keep |
| Migrations | Alembic | 1.18 | ✓ Keep |
| Scheduler | APScheduler | 3.11 | ✓ Keep |
| AI | google-genai | 1.73 | ✓ Keep |
| Indicators | ta | 0.11.0 | ✓ Keep |
| Market Data | vnstock | 3.5.1 | ✓ Keep |
| HTTP | httpx | 0.28 | ✓ Keep |
| Scraping | beautifulsoup4 | 4.12 | ✓ Keep |
| Logging | loguru | 0.7 | ✓ Keep |
| Retry | tenacity | 9.1 | ✓ Keep |
| Frontend | Next.js | 16.2.3 | ✓ Keep |
| UI Kit | shadcn/ui (base-ui) | 4.2.0 | ✓ Keep |
| State | zustand | 5.0.12 | ✓ Keep |
| Data Fetching | @tanstack/react-query | 5.99.0 | ✓ Keep |
| Tables | @tanstack/react-table | 8.21.3 | ✓ Keep |
| Charts | lightweight-charts + recharts | 5.1.0 / 3.8.1 | ✓ Keep |
| Icons | lucide-react | 1.8.0 | ✓ Keep |
| Forms | react-hook-form + zod | 7.73.1 / 4.3.6 | ✓ Keep |
| Styling | Tailwind CSS 4 | 4.x | ✓ Keep |
| Database | PostgreSQL (Aiven) | — | ✓ Keep |
| Deploy | Render (backend), Vercel (frontend) | — | ✓ Keep |

---

## 1. Dependencies to REMOVE After Feature Removal

### Backend Removals

**Confidence: HIGH** — Direct code audit of the codebase confirms these.

| What to Remove | Files | Rationale |
|---------------|-------|-----------|
| Corporate events model | `app/models/corporate_event.py` | Feature being removed entirely |
| Corporate events crawler | `app/crawlers/corporate_event_crawler.py` | No longer needed — was VNDirect API crawler |
| Corporate events API | `app/api/corporate_events.py` | API endpoint `/api/corporate-events` no longer served |
| Corporate events router import | `app/api/router.py` line 8, 19 | Remove from API router |
| VNDirect config settings | `app/config.py` lines 77-79 | `vndirect_delay_seconds`, `vndirect_timeout` — no longer needed |
| VNDirect circuit breaker | `app/resilience.py` | `vndirect_breaker` — remove if only used by corporate events |
| Corporate events scheduler job | `app/scheduler/jobs.py` | Remove crawl_corporate_events job and chain references |
| HNX/UPCOM exchange constants | `app/scheduler/jobs.py` line 28 | `VALID_EXCHANGES` → change to `("HOSE",)` only |
| HNX/UPCOM priority config | `app/config.py` line 83 | `realtime_priority_exchanges` list → simplify to HOSE only |

**DB migration required:** Drop `corporate_events` table. Mark HNX/UPCOM tickers as `is_active=false` (don't delete — historical data preserved).

**No pip packages to remove for corporate events:** The crawler uses `httpx` (shared) and SQLAlchemy (core ORM). No unique Python packages were added solely for corporate events.

**However — `python-telegram-bot` can be removed:** Still listed in `requirements.txt` line 16 (`python-telegram-bot==22.7`) but Telegram bot was removed in v7.0 post-milestone. This is dead weight.

### Frontend Removals

**Confidence: HIGH** — Direct component audit.

| What to Remove | File(s) | Rationale |
|---------------|---------|-----------|
| Corporate events calendar component | `components/corporate-events-calendar.tsx` | Feature removed |
| Corporate events page | `app/dashboard/corporate-events/page.tsx` | Route removed |
| Corporate events nav link | `components/navbar.tsx` line 29 | Remove `{ href: "/dashboard/corporate-events", label: "Sự kiện" }` |
| Corporate events hooks | `lib/hooks.ts` lines 196-202 | `useCorporateEvents` hook |
| Corporate events API function | `lib/api.ts` | `fetchCorporateEvents` function + `CorporateEventResponse` type |
| Exchange filter component | `components/exchange-filter.tsx` | No longer needed — HOSE only |
| Exchange badge component | `components/exchange-badge.tsx` | No longer needed — all tickers are HOSE |
| Exchange store | `lib/store.ts` lines 41-58 | `useExchangeStore` — no exchange switching needed |
| Exchange column in watchlist | `components/watchlist-table.tsx` lines 119-137 | "Sàn" column unnecessary |
| Exchange filter in home page | `app/page.tsx` line 38 | Remove `<ExchangeFilter />` and exchange-based subtitle logic |

**No npm packages to remove:** All corporate event / exchange components use shared dependencies (shadcn/ui primitives, Tabs, Badge, etc.).

### Summary of Removable Dead Weight

| Category | Items Removed | Impact |
|----------|--------------|--------|
| Backend files | 3 files deleted, 3+ files edited | ~400 LOC removed |
| Frontend files | 3 files deleted, 5+ files edited | ~500 LOC removed |
| DB tables | 1 table dropped | Simpler schema |
| Scheduler jobs | 1 job removed from chain | Faster daily pipeline |
| Config settings | 3+ settings removed | Cleaner config |
| Dead pip package | `python-telegram-bot` | 1 fewer dependency |

---

## 2. Stack Additions for Watchlist DB Migration

### Backend: New Watchlist API Endpoints

**No new packages needed.** The existing stack (FastAPI + SQLAlchemy + asyncpg + Alembic) handles this natively.

| What's Needed | Approach | Existing Tech |
|--------------|----------|---------------|
| New watchlist model | Repurpose/replace existing `user_watchlist` table (currently Telegram-only, has `chat_id` column) | SQLAlchemy model |
| CRUD API endpoints | `GET/POST/DELETE /api/watchlist` | FastAPI router |
| Migration | Alembic migration to create new `watchlist` table | Alembic |

**Watchlist model redesign (recommended):**

The existing `UserWatchlist` model has a `chat_id` column designed for Telegram bot (removed in v7.0). For the frontend watchlist migration, create a new simpler table:

```python
class Watchlist(Base):
    __tablename__ = "watchlist"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), unique=True)
    added_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
```

**Rationale:** Single-user app (per PROJECT.md constraints), no need for `chat_id` or user column. `ticker_id` has UNIQUE constraint since one user = one watchlist. Simpler than repurposing the old Telegram table. Drop old `user_watchlist` table in same migration.

### Frontend: Zustand → React Query Migration for Watchlist

**No new packages needed.** Replace `zustand/persist` localStorage watchlist with `@tanstack/react-query` mutations backed by the new API.

Current flow:
```
User clicks star → zustand.addToWatchlist() → localStorage
```

New flow:
```
User clicks star → useMutation(POST /api/watchlist/{symbol}) → invalidateQueries(["watchlist"])
Watchlist page → useQuery(GET /api/watchlist) → server-synced data
```

**Migration strategy for existing localStorage data:**
1. On first load, check `localStorage["holo-watchlist"]`
2. If exists and API watchlist is empty, POST each symbol to migrate
3. Delete localStorage key after successful migration
4. This is a one-time client-side migration — no new packages needed

**Impact on `lib/store.ts`:**
- Remove `useWatchlistStore` entirely (lines 1-39)
- Remove `useExchangeStore` (lines 41-58) — no longer needed (HOSE only)
- If both stores removed, evaluate if `zustand` dependency is still needed elsewhere
- **Keep zustand** — it may be useful for other local UI state in future, and it's only ~1KB

---

## 3. Stack Additions for UX Improvements (Navigation, Onboarding)

### No New Animation/Transition Libraries Needed

**Confidence: HIGH** — The existing stack already has what's needed.

| UX Need | Existing Solution | Why Not Add More |
|---------|------------------|-----------------|
| Page transitions | CSS transitions + Tailwind `transition-*` classes | Already in use; Next.js App Router handles route transitions |
| Component animations | `tw-animate-css` (already installed v1.4.0) | Already provides enter/exit animations for shadcn/ui |
| Micro-interactions | Tailwind `transition-colors`, `transition-transform` | Already used in navbar, cards, buttons |
| Loading states | shadcn `Skeleton` component | Already used extensively |

### One Potential Addition — Toast Notifications

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `sonner` | ^2.x | Toast notifications | Lightweight (~3KB), shadcn/ui recommended toast solution. Useful for "Đã thêm vào danh mục" / "Đã ghi lệnh" feedback during user flows. |

**Confidence: MEDIUM** — `sonner` is optional. The existing `Dialog` and inline status patterns may suffice. Add only if UX design requires toast-style feedback. This is a "nice to have" not a blocker.

### Navigation Simplification — No Stack Changes

Current navbar has 7 links. After v9.0 removals:

| Current Nav | v9.0 Nav | Change |
|------------|----------|--------|
| Tổng quan | ✓ Keep | — |
| Danh mục | ✓ Keep | — |
| Bảng điều khiển | ⚠️ Evaluate | Merge into Tổng quan or remove |
| Huấn luyện | ✓ Keep | Redesigned content |
| Nhật ký | ✓ Keep | Redesigned flow |
| Sự kiện | ❌ Remove | Corporate events gone |
| Hệ thống | ✓ Keep | Maybe icon-only |

Pure template/routing work — zero new packages.

### Onboarding Flow — No New Libraries

For a single-user personal tool, onboarding should be:
- A first-visit welcome card on the home page (conditional render based on empty watchlist + no trades)
- Empty states with clear CTAs (partially done — see watchlist-table.tsx empty state)
- Progressive disclosure via existing Card/Badge components

**Anti-recommendation:** Do NOT add `react-joyride`, `intro.js`, or any tour library. Single-user personal tool — the user IS the developer. Simple conditional cards are sufficient.

---

## 4. Stack Changes for AI Analysis Improvement

### Gemini Prompt Engineering — No New Packages

**Confidence: HIGH** — Entirely prompt/config changes within existing `google-genai` SDK.

Current system constraints (from `prompts.py` audit):
- Model: `gemini-2.5-flash-lite`
- Default `max_output_tokens`: 16384
- Default `thinking_budget`: 1024 (2048 for trading signals)
- Reasoning caps: "2-3 câu" / "tối đa 200 từ" / "tối đa 300 ký tự"

### Changes to Make AI Output Longer and More Useful

| Change | Current Value | New Value | File |
|--------|-------------|-----------|------|
| Technical reasoning length | "2-3 câu tiếng Việt" | "5-8 câu tiếng Việt, phân tích chi tiết" | `prompts.py` |
| Fundamental reasoning length | "2-3 câu tiếng Việt" | "5-8 câu tiếng Việt, phân tích chi tiết" | `prompts.py` |
| Sentiment reasoning length | "2-3 câu tiếng Việt" | "3-5 câu tiếng Việt" | `prompts.py` |
| Combined explanation cap | "tối đa 200 từ" | "tối đa 500 từ" | `prompts.py` |
| Trading signal reasoning cap | "tối đa 300 ký tự" | "tối đa 800 ký tự" | `prompts.py` |
| Default `max_output_tokens` | 16384 | 32768 | `gemini_client.py` |
| Default `thinking_budget` | 1024 | 2048 | `gemini_client.py` |

### Approach: Keep Single `reasoning` Field, Increase Length via Prompt

**Recommended over schema changes because:**
- No DB migration needed — `reasoning` column is `Text` (unlimited length)
- `raw_response` JSONB already stores the full Gemini response
- Frontend just needs to render longer text (potentially with expand/collapse)
- Lower risk, faster to ship

### Model Consideration

| Model | RPM (Free) | Quality | Recommendation |
|-------|-----------|---------|---------------|
| `gemini-2.5-flash-lite` (current) | 15 RPM | Good for batch | Keep as default for technical/fundamental/sentiment |
| `gemini-2.5-flash` | 15 RPM | Better reasoning | Use for combined + trading_signal for richer output |

**Confidence: MEDIUM** — `gemini-2.5-flash` (non-lite) may produce significantly better long-form analysis. This is a config change (`GEMINI_MODEL` env var or per-analysis-type model selection in code), not a dependency change. Worth A/B testing.

### Frontend Display for Longer AI Output

| Component | Current | Change Needed |
|-----------|---------|--------------|
| `analysis-card.tsx` reasoning | `<p className="text-xs">` | `text-sm`, add expand/collapse for long text |
| `CombinedRecommendationCard` | Single paragraph, inline | Section with line breaks, expandable |
| `trading-plan-panel.tsx` | Compact reasoning | Expandable detail section |

**Potential addition for formatted AI output:**

| Library | Version | Purpose | Add When |
|---------|---------|---------|----------|
| `react-markdown` | ^10.x | Render markdown in AI output | Only if prompts instruct Gemini to use bullet points/headers |
| `remark-gfm` | ^4.x | GFM markdown (tables, lists) | Companion to react-markdown |

**Confidence: MEDIUM** — Only needed if AI prompts produce markdown-formatted text. If plain text with longer content suffices (likely for v9.0), skip these. Evaluate after prompt changes are tested.

---

## 5. No-Stack-Change Work Items

These v9.0 tasks require ZERO new packages — pure application code:

| Task | Approach |
|------|----------|
| Trade Journal flow redesign | Rearrange components, add CTA buttons, improve empty states |
| Coach page rework | Reorder sections, add action buttons, improve layout |
| Navigation simplification | Edit `navbar.tsx` NAV_LINKS array, remove dead routes |
| HNX/UPCOM data cleanup | Alembic migration: `UPDATE tickers SET is_active=false WHERE exchange != 'HOSE'` |
| Remove exchange filter from all pages | Delete components, simplify store |
| Improve error/empty states | Enhance existing error Card patterns with clearer CTAs |

---

## 6. Migration & Database Schema Changes

**All handled by existing Alembic + SQLAlchemy. No new tools.**

| Migration | Type | Detail |
|-----------|------|--------|
| Drop `corporate_events` table | Destructive | `DROP TABLE corporate_events` |
| Create `watchlist` table | Additive | New table with `ticker_id` FK + `added_at` |
| Deactivate HNX/UPCOM tickers | Data migration | `UPDATE tickers SET is_active=false WHERE exchange IN ('HNX', 'UPCOM')` |
| Drop `user_watchlist` table | Destructive | Old Telegram-era table, no longer used |

**Ordering:** Create new `watchlist` table BEFORE deploying frontend that expects it. Deactivating HNX/UPCOM tickers should happen BEFORE removing exchange filter UI (graceful transition).

---

## Recommended Stack Summary

### Additions (Minimal — 0 Required, 3 Optional)

| Library | Version | Required? | Purpose | Confidence |
|---------|---------|-----------|---------|------------|
| `sonner` | ^2.x | Optional | Toast notifications for UX feedback | MEDIUM |
| `react-markdown` | ^10.x | Optional | Render formatted AI text | MEDIUM |
| `remark-gfm` | ^4.x | Optional | GFM support for react-markdown | MEDIUM |

### Removals (5 Items)

| What | Type | Saves |
|------|------|-------|
| `python-telegram-bot` from `requirements.txt` | Dead dependency | ~15MB installed |
| Corporate events (full stack) | Feature removal | ~900 LOC, 1 DB table, 1 scheduler job |
| Exchange filter/badge/store | Feature simplification | ~150 LOC, simpler UI |
| Old `user_watchlist` table | DB cleanup | Simpler schema |
| VNDirect config + circuit breaker | Config cleanup | 3 settings |

### Config-Only Changes (No Packages)

| Change | Impact |
|--------|--------|
| Prompt length caps increased (prompts.py) | Longer AI analysis output |
| Default max_output_tokens: 16384→32768 | More room for AI response |
| Default thinking_budget: 1024→2048 | Better AI reasoning quality |
| Consider `gemini-2.5-flash` for combined/trading_signal | Better output quality at same cost |
| Remove HNX/UPCOM from exchange config | Simpler data pipeline |

---

## Installation Summary

### Backend

```bash
# Remove dead dependency
# Delete from requirements.txt: python-telegram-bot==22.7

# No new packages to install
```

### Frontend

```bash
# Optional additions (add only if UX design requires them)
npm install sonner              # Toast notifications
npm install react-markdown remark-gfm  # AI markdown rendering
```

---

## Sources

| Source | Confidence | What It Confirmed |
|--------|------------|------------------|
| Direct codebase audit (all files above) | HIGH | All removal targets, existing dependencies, current patterns |
| `PROJECT.md` v9.0 goals | HIGH | Feature removal scope, constraints |
| `requirements.txt` | HIGH | `python-telegram-bot` still listed as dead dependency |
| `package.json` | HIGH | Current frontend dependency versions |
| `prompts.py` + `gemini_client.py` | HIGH | Current AI prompt constraints and token limits |
| `store.ts` | HIGH | Current localStorage watchlist implementation |
| `user_watchlist.py` model | HIGH | Old Telegram-era table structure |
