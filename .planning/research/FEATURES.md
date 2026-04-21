# Feature Landscape — v5.0 E2E Testing & Quality Assurance

**Domain:** End-to-end testing for stock intelligence dashboard (Next.js 16 + FastAPI)
**Researched:** 2025-07-21
**Overall confidence:** HIGH — Playwright is mature, patterns well-established for this stack

## Context: What We're Testing

**Pages (8 routes):**
- `/` — Market overview heatmap with exchange filter, stats cards (800+ ticker cells)
- `/watchlist` — localStorage-backed watchlist table with real-time prices, signal badges
- `/dashboard` — Bảng điều khiển (dashboard hub, likely redirects or minimal content)
- `/dashboard/portfolio` — Trade form dialog, holdings table, P&L summary cards, performance/allocation charts, CSV import dialog
- `/dashboard/paper-trading` — 5-tab interface (overview, trades, analytics, calendar, settings)
- `/dashboard/corporate-events` — Corporate event calendar table
- `/dashboard/health` — Job status cards, Gemini usage, data freshness table, error rate chart, DB pool, pipeline timeline, job trigger buttons
- `/ticker/[symbol]` — Candlestick chart (lightweight-charts canvas), indicator charts, 4 analysis cards, trading plan panel, signal outcomes, watchlist star, analyze-now button

**API surface:** 55 REST endpoints across 7 routers + 1 WebSocket endpoint (`/ws/prices`)
- `system` router: health check, scheduler status, crawl triggers, backfill
- `tickers` router: list, prices, market-overview
- `analysis` router: indicators, 5 analysis types, summary, trading-signal, 7 manual triggers
- `portfolio` router: CRUD trades, holdings, summary, performance, allocation, CSV import
- `health` router: jobs, data-freshness, errors, db-pool, summary, trigger, pipeline-timeline, gemini-usage
- `corporate_events` router: event list
- `paper_trading` router: trades CRUD, follow, config, 12 analytics endpoints, calendar

**Interactive elements:** Trade form dialog (6 fields), CSV import dialog (multi-step with drag-drop), paper trade manual follow, settings form (3 fields), trade edit/delete dialogs, ticker search command palette (⌘K with 800+ tickers), exchange filter buttons, tab navigation, table column sorting, watchlist add/remove star, theme toggle, time range selector on charts, adjusted/raw price toggle

**Data visualization:** Candlestick chart (lightweight-charts canvas), MA/BB/MACD overlays (lightweight-charts), Recharts line/bar/area charts (performance, allocation, error rate, equity curve), calendar heatmap (react-activity-calendar), market heatmap (custom div grid), @tanstack/react-table data tables (6+ instances)

**Real-time:** WebSocket price streaming with exponential backoff reconnect (1s→30s), market-hours awareness, ConnectionStatusIndicator, PriceFlashCell animations

**Existing test coverage:** 560 backend unit tests across 34 test files, 0 frontend/E2E tests

---

## Table Stakes

Features that any serious E2E test suite for this application MUST have. Without these, the test suite doesn't justify its existence.

| Feature | Why Expected | Complexity | Dependencies |
|---------|-------------|------------|--------------|
| **Page smoke tests (all 8 routes)** | Most basic validation — every page loads without crash, renders heading + key structural elements. Catches broken imports, missing env vars, API failures that blank the page. | Low | Running Next.js + FastAPI, database with some data |
| **Navigation flow tests** | Verify all 7 navbar links work, ⌘K ticker search navigates to `/ticker/[symbol]`, back button from ticker detail, row clicks in tables navigate correctly | Low | Navbar has 7 links + ⌘K command palette |
| **API health check tests (all 55 endpoints)** | Backend has 560 unit tests but ZERO integration tests verifying the HTTP/routing layer works. API health checks catch: wrong status codes, broken router registration, serialization errors, database connection issues. Single parametrized test → massive coverage. | Medium | Running FastAPI + database with seed data |
| **Form submission tests** | Portfolio trade form (BUY/SELL with 6 fields), paper trading manual follow, settings form — these are the primary write operations. Form bugs are the #1 class of frontend bug in CRUD apps. | Medium | Portfolio & paper trading API endpoints + seed data for valid tickers |
| **Data table interaction tests** | Column sorting (watchlist, holdings, trade history, paper trades all use @tanstack/react-table with sortable columns), row click navigation to ticker detail | Medium | Tables need data rows to sort — requires seed data |
| **Error state handling tests** | Empty watchlist message, API error cards, loading skeletons, 404/500 on invalid ticker symbol. Users hit these states regularly. | Low | Mock API responses via `page.route()` intercepts |
| **Tab navigation tests** | Paper trading 5 tabs (overview, trades, analytics, calendar, settings) — verify each tab renders its content, switching doesn't lose state | Low | Paper trading page with seed data |
| **Dialog/modal lifecycle tests** | Trade form dialog (open → fill → submit → closes), CSV import (multi-step: upload → preview → confirm), trade edit dialog, delete confirmation — verify full open/interact/close cycle | Medium | Dialog components, valid form data |
| **Mobile responsive smoke tests** | App has responsive breakpoints — mobile hamburger menu (Sheet), hidden table columns (sm: classes), grid layout changes (lg:cols-5 → single column) | Low | Playwright viewport config at 375px width |
| **Theme toggle test** | Dark/light mode via next-themes — verify button toggles, theme persists on reload, no invisible text on either theme | Low | Theme provider in root layout |

---

## Differentiators

Features that elevate the test suite from "basic coverage" to "actually catches bugs and prevents regressions." Disproportionate value for the investment.

| Feature | Value Proposition | Complexity | Dependencies |
|---------|------------------|------------|--------------|
| **Visual regression testing (4-5 key pages)** | Catches CSS regressions, layout shifts, invisible text, broken chart containers that functional tests miss entirely. Critical for data-dense dashboard where a misaligned column or collapsed section is a real bug. Use Playwright's built-in `toHaveScreenshot()` with `maxDiffPixelRatio` tolerance. | Medium | Baseline screenshots, deterministic data (mock API for visual tests or use seed data) |
| **Critical user flow E2E tests** | Multi-page journeys that prove the app works as a system: (1) Heatmap → click ticker → view analysis → star to watchlist → navigate to watchlist → verify ticker appears. (2) Portfolio → add trade → verify holdings table updates → check P&L card. (3) Paper trading overview → view analytics → calendar tab. These catch integration bugs invisible to page-level tests. | High | Full stack running, seed data, localStorage management for watchlist |
| **Chart rendering verification** | lightweight-charts renders to `<canvas>` — verify container has non-zero dimensions, canvas element exists, time range buttons (1T/3T/6T/1N/2N) switch data range. Can't assert chart content but CAN catch: blank chart, missing canvas, crashed rendering, button click failures. | Medium | Ticker with price data, lightweight-charts loaded |
| **WebSocket connection status test** | Verify ConnectionStatusIndicator shows appropriate state. When backend is running → should show connected/market_closed. This covers the entire real-time infrastructure visibility without needing live market data. | Low-Medium | Backend WebSocket endpoint running |
| **API response contract tests** | Verify API responses have required fields with correct types. Catches backend schema drift (field renamed, type changed, field removed) before frontend renders "undefined" or crashes on null access. Parametrized test across key endpoints. | Medium | Direct API calls via Playwright `request` context |
| **Accessibility (a11y) audit** | Run axe-core on each page to catch missing ARIA labels, contrast issues, keyboard traps. Vietnamese text with special characters makes label accessibility extra important. Low effort — add `@axe-core/playwright`, call `checkA11y()` in each smoke test. | Low | `@axe-core/playwright` npm package |
| **Cross-browser smoke (Firefox)** | lightweight-charts canvas rendering can behave differently in Firefox. Smoke test subset in Firefox catches engine-specific issues. Playwright supports Firefox natively — just add project config. | Low | Playwright Firefox browser install |
| **Performance baseline assertions** | Assert key pages load within threshold. Heatmap with 800+ ticker divs is the stress test. Ticker detail with candlestick chart + 4 analysis cards is the complexity test. Simple: `expect(loadTime).toBeLessThan(5000)`. | Low-Medium | Playwright navigation timing |
| **Exchange filter interaction test** | Heatmap and watchlist both have HOSE/HNX/UPCOM/All filter buttons. Verify filter changes visible data. Catches: filter not applied, wrong exchange shown, filter state not persisted (Zustand store). | Low | Market overview data with mixed exchanges |

---

## Anti-Features

Features to explicitly NOT build. Each sounds useful but costs more than it delivers for a personal project.

| Anti-Feature | Why Avoid | What to Do Instead |
|-------------|-----------|-------------------|
| **Full WebSocket message testing** | Would need: market-hours timing, subscribe/unsubscribe sequence validation, reconnect scenario simulation with controlled disconnects, price update assertion against known data — massive infrastructure for a 30s polling mechanism | Test connection status indicator UI only. Backend WebSocket is covered by `test_realtime_prices.py` (existing unit test). |
| **Pixel-perfect chart assertion** | lightweight-charts renders to `<canvas>` — pixel comparison is flaky across OS/GPU/font rendering. Chart data changes with real market data. Anti-aliasing differs between CI and local. | Verify chart container renders with non-zero dimensions + canvas element exists. Visual regression at page level catches gross layout breakage. |
| **Screenshot testing every page × viewport × theme** | Combinatorial explosion: 8 pages × 3 viewports × 2 themes = 48 baselines. Each baseline needs updating when data or styles change. Maintenance burden exceeds value. | Visual regression on 4-5 key pages at desktop viewport, light theme only. Separate theme toggle test verifies dark mode isn't broken. |
| **Database state verification in tests** | E2E tests that query PostgreSQL directly to verify writes couple tests to internal schema. Schema changes break tests even when UI works correctly. Creates test-only DB connection management. | Verify through UI: submit form → check that table/card shows new data. Or verify through API response after action. |
| **Mocking entire backend (MSW/full stub)** | Building mock handlers for 55 endpoints creates a parallel API to maintain. When backend changes, must update both real API and mock. Defeats E2E purpose. | Run against real FastAPI + PostgreSQL with seed data. Mock only for specific error state tests via `page.route()` intercepts. |
| **Test retry/quarantine infrastructure** | Auto-retry, test quarantine queues, parallel sharding, flaky test tracking — CI engineering suited for teams, not solo developer. | Run tests sequentially. Fix flaky tests immediately. Use Playwright's built-in `retries: 1` in CI config only. |
| **100% endpoint contract validation** | Validating response shape of all 55 endpoints is 55 individual assertions to maintain. Many endpoints are simple GET-list that are implicitly tested by page smoke tests. | Contract test the 10-15 most critical/complex endpoints. Others are validated implicitly when pages render their data correctly. |
| **Performance benchmark trends** | Historical performance tracking with graphs, percentile analysis, regression detection over time — monitoring infrastructure for a personal project. | Simple threshold assertion: page loads in < N seconds. Check once per test run, no history. |
| **Load/stress testing** | Single-user app. No concurrent user scenarios. No CDN, no load balancer, no connection pool exhaustion under normal use. | One performance smoke test for heaviest page (heatmap with 800+ tickers). |
| **Component-level unit tests (React Testing Library)** | Different testing layer, different tooling, different milestone. RTL tests individual components in isolation — complementary to E2E but separate scope. | Stay focused on E2E. If component tests are needed later, that's a separate effort. |

---

## Feature Dependencies

```
Infrastructure (config, seed data, helpers)
  │
  ├─→ Page Smoke Tests (all 8 routes)
  │     ├─→ Visual Regression (screenshots of smoke-tested pages)
  │     ├─→ Accessibility Audit (axe-core in each smoke test)
  │     └─→ Performance Baselines (timing in smoke tests)
  │
  ├─→ Navigation Tests (navbar, search, row clicks)
  │     └─→ Critical User Flow Tests (multi-page journeys that include navigation)
  │
  ├─→ API Health Checks (all 55 endpoints)
  │     └─→ API Contract Tests (response shape validation on subset)
  │
  ├─→ Form Tests (trade, follow, settings, CSV)
  │     └─→ Critical User Flow Tests (form submit → verify result in UI)
  │
  ├─→ Table Interaction Tests (sort, row click)
  │
  ├─→ Tab/Dialog/Theme/Filter Tests
  │
  ├─→ Chart Rendering Tests (canvas, time range buttons)
  │     └─→ Visual Regression (ticker detail page screenshot includes chart)
  │
  ├─→ WebSocket Status Test
  │
  └─→ Error State Tests (mocked API failures)
  
Cross-browser (Firefox): runs smoke test subset
Mobile viewport: runs smoke test subset at 375px
```

### Infrastructure Prerequisites

| Prerequisite | What | Why |
|-------------|------|-----|
| **Playwright config** | `playwright.config.ts` with `webServer` for both Next.js dev server + FastAPI | Tests need both servers running before any test executes |
| **Seed data** | Python script or fixture that creates deterministic tickers, prices, trades, analysis, paper trades | Tests need predictable data — "VNM" should exist, have prices, have analysis results |
| **Test helpers** | `navigateTo()`, `waitForDataLoad()`, `openDialog()`, common selectors | Reduce duplication across test files, make tests readable |
| **Global setup/teardown** | Start backend, run seed data, verify connectivity before test suite | Playwright `globalSetup` handles this |
| **CI config** | GitHub Actions workflow: install deps, start servers, run tests, upload artifacts | "CI-ready" is explicit project goal |

---

## Detailed Feature Specifications

### Holo-Specific Testing Concerns

These are testing challenges unique to this application's architecture:

| Concern | Why It Matters | Testing Approach |
|---------|---------------|-----------------|
| **Vietnamese text rendering** | All UI text is Vietnamese (diacritics: ắ, ể, ố, ụ, etc.). Assertion strings must use exact Vietnamese. Wrong encoding = invisible text bugs. | Use exact Vietnamese strings in assertions: `expect(heading).toContainText('Tổng quan thị trường')` |
| **localStorage watchlist** | Watchlist is stored in localStorage, not API. Tests that add/remove watchlist items affect other tests. | `page.evaluate(() => localStorage.clear())` in test setup. Or use `storageState` in Playwright fixtures. |
| **Canvas-based charts** | lightweight-charts renders to `<canvas>` — no DOM nodes for chart content. Can't assert "candlestick shows VNM price at 82,500". | Assert container div exists + has non-zero `offsetHeight`. Assert `<canvas>` child element exists. Visual regression for gross failures. |
| **Recharts SVG charts** | Recharts renders to SVG — slightly more testable than canvas. Can assert SVG exists, has paths, but not specific data values. | Assert `<svg>` element inside chart container. Visual regression for appearance. |
| **Exchange filter state (Zustand)** | Exchange filter uses Zustand store — persisted state could leak between tests. | Reset between tests or use fresh browser context per test. |
| **API cooldowns** | On-demand analysis has 5-minute server-side cooldown (`429` response). Tests that trigger analysis will hit cooldown on reruns. | Don't test actual analysis triggering (that's backend logic). Test the button UI state and error handling for 429. |
| **Dynamic data** | Market data changes daily. Tests against production data will have different numbers each day. | Seed data for deterministic tests. Or use `toContainText()` patterns instead of exact value matching. |
| **WebSocket market-hours awareness** | WebSocket shows `market_closed` outside trading hours (9:00-15:00 ICT). Test behavior depends on when tests run. | Assert either `connected` or `market_closed` — both are valid. Don't assert specific state. |

---

## MVP Recommendation

### Phase 1 — Infrastructure (must have before any tests)
1. Playwright setup + config (`webServer` for Next.js + FastAPI)
2. Seed data script (deterministic tickers, prices, trades, analysis)
3. Test helpers / common patterns

### Phase 2 — Smoke & Health (highest ROI per test line)
4. Page smoke tests for all 8 routes (verify load + key elements)
5. API health checks for all 55 endpoints (parametrized)
6. Navigation flow tests (navbar + search + row clicks)

### Phase 3 — Interaction Tests (catches most form/table bugs)
7. Form submission tests (portfolio trade, paper trading follow, settings update)
8. Data table interaction tests (column sort, row click)
9. Tab navigation + dialog lifecycle tests
10. Error state tests (mocked API failures → verify error UI)

### Phase 4 — Visual & Advanced (regression prevention + polish)
11. Visual regression on 4-5 key pages
12. Chart rendering verification (canvas + time range)
13. Critical user flow tests (2-3 multi-page journeys)
14. Accessibility audit (axe-core)
15. Mobile responsive smoke + theme toggle
16. Cross-browser smoke (Firefox)
17. WebSocket status + exchange filter tests
18. Performance baselines + API contract tests

### Phase ordering rationale
- **Infrastructure first** — literally cannot write tests without Playwright config and seed data
- **Smoke tests second** — maximum bug discovery per line of test code. If heatmap page 500s, we find out immediately.
- **Interaction tests third** — form/table bugs are the most common class of frontend bugs in CRUD dashboards, and are invisible to smoke tests
- **Visual/advanced last** — depend on stable pages that don't change between runs, require baseline management, are additive value not foundational

---

## Scope Estimate

| Category | Est. Test Count | Est. Effort | Priority |
|---------|----------------|-------------|----------|
| Infrastructure (config, seed, helpers) | — | 4-6 hours | P1 |
| Page smoke tests | 8-10 | 1-2 hours | P2 |
| API health checks | 1 parametrized (55 cases) | 2-3 hours | P2 |
| Navigation tests | 5-8 | 1-2 hours | P2 |
| Form submission tests | 6-8 | 3-4 hours | P3 |
| Table/tab/dialog tests | 8-12 | 3-4 hours | P3 |
| Error state tests | 4-6 | 2-3 hours | P3 |
| Visual regression | 4-5 screenshots | 2-3 hours | P4 |
| Chart rendering tests | 3-4 | 1-2 hours | P4 |
| Critical user flows | 2-3 | 3-4 hours | P4 |
| A11y + theme + mobile + cross-browser | 5-8 | 2-3 hours | P4 |
| WebSocket + filter + perf + contracts | 5-8 | 3-4 hours | P4 |
| **Total** | **~55-75 tests** | **~27-38 hours** | — |

---

## Sources

- **Codebase analysis** (HIGH confidence): Inventoried all 8 routes (`frontend/src/app/`), 55 API endpoints (`backend/app/api/*.py`), 35+ components (`frontend/src/components/`), 34 backend test files (560 tests)
- **Playwright capabilities** (HIGH confidence): `toHaveScreenshot()`, `webServer`, `request` context, `page.route()` interception, axe-core integration — all stable, well-documented features
- **@axe-core/playwright** (HIGH confidence): Standard accessibility integration, trivial setup
- **Domain knowledge** (HIGH confidence): Financial dashboard testing patterns — canvas chart verification, real-time data handling, form-heavy CRUD operations, Vietnamese text encoding considerations
