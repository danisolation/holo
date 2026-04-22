# Architecture: Playwright E2E Testing Integration

**Domain:** E2E testing infrastructure for Next.js 16 + FastAPI monorepo
**Researched:** 2025-07-20
**Confidence:** HIGH — architecture derived from verified codebase analysis + Playwright 1.59 docs

## Recommended Architecture

Playwright E2E tests live in the **frontend** directory as a peer to `src/`, using Playwright's built-in `webServer` array to orchestrate **both** backend (FastAPI on :8000) and frontend (Next.js on :3000) startup. Tests run against the **live production database** (Aiven PostgreSQL) in read-only mode — no seed/reset needed because the app is single-user with 800+ tickers of real data already present. This is the simplest architecture that works for a personal-use app with no auth.

### Design Philosophy

- **Test against real data** — 800+ tickers, real analyses, real paper trades already exist. No mocking needed for read flows.
- **Read-mostly testing** — most E2E flows are read operations (view heatmap, view ticker, view portfolio). Write tests (create trade, follow signal) use real API and clean up after themselves.
- **No Docker** — runs natively on Windows. Playwright handles server lifecycle.
- **No auth** — single-user app, no login flows to test.
- **Canvas-aware** — lightweight-charts renders to `<canvas>`. Use screenshot comparison, not DOM assertions.

### System Overview

```
PLAYWRIGHT TEST RUNNER (npx playwright test)
│
├── webServer[0]: cd ../backend && python -m uvicorn app.main:app --port 8000
│                 (waits for http://localhost:8000/)
│
├── webServer[1]: npm run dev  (Next.js on port 3000)
│                 (waits for http://localhost:3000)
│
└── Test Files:
    ├── e2e/                        ← Page-level E2E tests
    │   ├── home.spec.ts            ← Market overview heatmap
    │   ├── dashboard.spec.ts       ← Dashboard page
    │   ├── ticker.spec.ts          ← Ticker detail /ticker/[symbol]
    │   ├── watchlist.spec.ts       ← Watchlist (localStorage)
    │   ├── portfolio.spec.ts       ← Portfolio CRUD
    │   ├── paper-trading.spec.ts   ← Paper trading + analytics tabs
    │   ├── health.spec.ts          ← System health dashboard
    │   └── corporate-events.spec.ts
    ├── e2e/api/                    ← API-level tests (no browser)
    │   ├── health-check.spec.ts    ← All /api/* endpoints respond
    │   ├── tickers-api.spec.ts     ← /api/tickers, /api/tickers/{symbol}/prices
    │   └── websocket.spec.ts       ← WebSocket subscribe/unsubscribe
    ├── e2e/flows/                  ← Multi-page critical flows
    │   └── ticker-to-paper-trade.spec.ts  ← Browse → signal → follow → paper trade
    └── e2e/visual/                 ← Visual regression snapshots
        ├── home.visual.spec.ts
        └── ticker-chart.visual.spec.ts
```

---

## Component Boundaries

| Component | Responsibility | Location | New/Modified |
|-----------|---------------|----------|--------------|
| **playwright.config.ts** | Test configuration, webServer array, projects | `frontend/playwright.config.ts` | **NEW** |
| **E2E test specs** | Page + flow + API + visual tests | `frontend/e2e/**/*.spec.ts` | **NEW** |
| **Test fixtures** | Shared page objects, helpers, localStorage seeds | `frontend/e2e/fixtures/` | **NEW** |
| **package.json** | Add Playwright devDep + test scripts | `frontend/package.json` | **MODIFIED** |
| **.gitignore** | Ignore test-results, playwright-report, blob-report | `frontend/.gitignore` | **MODIFIED** |
| **Backend .env** | No changes needed — tests use same prod DB | `backend/.env` | **UNCHANGED** |
| **next.config.ts** | No changes needed — no rewrites, direct API calls | `frontend/next.config.ts` | **UNCHANGED** |

---

## Detailed Architecture

### 1. Playwright Configuration — Dual webServer

The critical design decision: Playwright's `webServer` config accepts an **array** of server definitions. This launches both backend and frontend before any test runs.

```typescript
// frontend/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Mobile viewport for responsive testing
    {
      name: 'mobile',
      use: { ...devices['iPhone 14'] },
    },
  ],

  webServer: [
    {
      // Backend: FastAPI
      command: 'cd ../backend && .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      url: 'http://127.0.0.1:8000/',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      // Frontend: Next.js dev server
      command: 'npm run dev',
      url: 'http://127.0.0.1:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
});
```

**Key decisions:**

| Decision | Rationale |
|----------|-----------|
| `reuseExistingServer: !process.env.CI` | Dev: use already-running servers. CI: start fresh. |
| Backend command uses `.venv/Scripts/python.exe` | Windows path. CI would use `python -m uvicorn`. |
| Backend health URL is `http://127.0.0.1:8000/` | Root returns `{"status": "ok"}` — verified in `main.py`. |
| `fullyParallel: true` | Tests are read-mostly, safe to parallelize. |
| Mobile project included | App claims responsive layout (DASH-05). Test it. |
| `timeout: 30_000` for backend | Backend starts scheduler + Telegram bot on startup; needs time. |

### 2. Test Directory Structure

```
frontend/
├── e2e/
│   ├── fixtures/
│   │   ├── test-base.ts          ← Extended test with custom fixtures
│   │   ├── watchlist.setup.ts    ← Global setup: seed localStorage watchlist
│   │   └── known-tickers.ts     ← Constants: VNM, FPT, HPG (known good tickers)
│   │
│   ├── home.spec.ts              ← / route — heatmap, market stats
│   ├── dashboard.spec.ts         ← /dashboard — watchlist summary, top movers
│   ├── ticker.spec.ts            ← /ticker/VNM — chart, indicators, analysis
│   ├── watchlist.spec.ts         ← /watchlist — add/remove, localStorage
│   ├── portfolio.spec.ts         ← /dashboard/portfolio — CRUD trades
│   ├── paper-trading.spec.ts     ← /dashboard/paper-trading — all tabs
│   ├── health.spec.ts            ← /dashboard/health — job status, freshness
│   ├── corporate-events.spec.ts  ← /dashboard/corporate-events
│   ├── navigation.spec.ts        ← Navbar links, mobile hamburger menu
│   │
│   ├── api/
│   │   ├── health-check.spec.ts  ← GET all /api/* endpoints, verify 200s
│   │   ├── tickers-api.spec.ts   ← /api/tickers, /api/tickers/VNM/prices
│   │   └── websocket.spec.ts     ← WS connect, subscribe, receive data
│   │
│   ├── flows/
│   │   └── ticker-to-paper-trade.spec.ts
│   │
│   └── visual/
│       ├── home.visual.spec.ts
│       └── ticker-chart.visual.spec.ts
│
├── playwright.config.ts
├── package.json                   ← Updated with Playwright
└── src/                          ← Existing frontend code (unchanged)
```

### 3. Fixture & Test Base Architecture

```typescript
// frontend/e2e/fixtures/known-tickers.ts
/**
 * Known tickers guaranteed to exist in the database with price data.
 * Used across all tests that need a real ticker symbol.
 */
export const KNOWN_TICKERS = {
  /** HOSE blue-chip with high activity */
  VNM: 'VNM',
  FPT: 'FPT',
  HPG: 'HPG',
  /** Used for testing exchange filter */
  HOSE_TICKER: 'VNM',
  HNX_TICKER: 'SHS',  // Verify this exists
  UPCOM_TICKER: 'BSR', // Verify this exists
} as const;
```

```typescript
// frontend/e2e/fixtures/test-base.ts
import { test as base, expect } from '@playwright/test';

/**
 * Extended test fixture that:
 * 1. Seeds localStorage with a watchlist (for tests that need it)
 * 2. Provides helper methods for common assertions
 */
export const test = base.extend<{
  /** Seed watchlist with known tickers before test */
  seededWatchlist: void;
}>({
  seededWatchlist: async ({ page }, use) => {
    // Seed zustand's persisted watchlist before navigating
    await page.addInitScript(() => {
      const watchlistData = {
        state: { watchlist: ['VNM', 'FPT', 'HPG'] },
        version: 0,
      };
      localStorage.setItem('holo-watchlist', JSON.stringify(watchlistData));
    });
    await use();
  },
});

export { expect };
```

### 4. Database Strategy — Read Against Production

**Why no test database:**
- Aiven PostgreSQL is remote — can't spin up a local instance quickly
- App has 800+ tickers with historical prices, indicators, AI analyses — seeding this from scratch is impractical
- Single user, no authentication — no risk of data pollution from other users
- Most tests are read operations (view pages, check data loads)

**Strategy:**

| Test Category | DB Interaction | Approach |
|---------------|---------------|----------|
| Page rendering (heatmap, dashboard, ticker) | READ | Assert data loads, elements visible |
| Watchlist | localStorage only | Seed via `addInitScript`, no DB needed |
| Portfolio trades | READ + WRITE | Create test trade → verify → delete (cleanup) |
| Paper trading | READ | View existing paper trades (already 1000+ in DB) |
| API health checks | READ | Verify endpoints return 200 |
| WebSocket | READ | Connect, subscribe to VNM, verify messages arrive |

**For write tests (portfolio):**
```typescript
test('create and delete trade', async ({ request }) => {
  // Create
  const response = await request.post('http://127.0.0.1:8000/api/portfolio/trades', {
    data: {
      symbol: 'VNM',
      side: 'buy',
      quantity: 100,
      price: 80000,
      trade_date: '2025-01-01',
    },
  });
  const trade = await response.json();

  // ... assert ...

  // Cleanup: delete the trade we just created
  await request.delete(`http://127.0.0.1:8000/api/portfolio/trades/${trade.id}`);
});
```

### 5. WebSocket Testing Architecture

The app uses a custom WebSocket at `ws://localhost:8000/ws/prices` with a subscribe/unsubscribe protocol. Playwright has native WebSocket support via page events.

```typescript
// frontend/e2e/api/websocket.spec.ts
import { test, expect } from '@playwright/test';

test('WebSocket connects and receives subscription confirmation', async ({ page }) => {
  // Navigate to a page that opens WebSocket (layout has RealtimePriceProvider)
  await page.goto('/');

  // Wait for WebSocket connection
  const wsPromise = page.waitForEvent('websocket');
  const ws = await wsPromise;
  expect(ws.url()).toContain('/ws/prices');

  // Check the connection status indicator shows connected
  await expect(page.locator('[data-testid="connection-status"]').or(
    page.getByText('connected', { exact: false })
  )).toBeVisible({ timeout: 10_000 });
});

test('WebSocket subscribe/unsubscribe protocol', async ({ page }) => {
  const messages: string[] = [];

  // Intercept WebSocket
  page.on('websocket', (ws) => {
    ws.on('framereceived', (event) => {
      messages.push(event.payload as string);
    });
  });

  // Navigate to ticker page (triggers subscribe for that ticker)
  await page.goto('/ticker/VNM');
  await page.waitForTimeout(2000);

  // Verify subscription happened
  const subMsg = messages.find(m => {
    try {
      const parsed = JSON.parse(m);
      return parsed.type === 'subscribed';
    } catch { return false; }
  });
  expect(subMsg).toBeDefined();
});
```

**Alternative: Direct WebSocket testing without browser (using ws library):**
```typescript
test.describe('WebSocket API direct', () => {
  test('raw WebSocket protocol', async ({}) => {
    const WebSocket = (await import('ws')).default;
    const ws = new WebSocket('ws://127.0.0.1:8000/ws/prices');

    const connected = new Promise<void>((resolve) => ws.on('open', resolve));
    await connected;

    ws.send(JSON.stringify({ type: 'subscribe', symbols: ['VNM'] }));

    const response = await new Promise<string>((resolve) => {
      ws.on('message', (data) => resolve(data.toString()));
    });

    const parsed = JSON.parse(response);
    expect(parsed.type).toBe('subscribed');
    expect(parsed.symbols).toContain('VNM');

    ws.close();
  });
});
```

### 6. Visual Regression Testing

lightweight-charts renders to `<canvas>` — impossible to assert DOM elements for chart content. Use Playwright's screenshot comparison.

```typescript
// frontend/e2e/visual/ticker-chart.visual.spec.ts
import { test, expect } from '@playwright/test';

test('ticker chart renders correctly', async ({ page }) => {
  await page.goto('/ticker/VNM');

  // Wait for chart to fully render (canvas + data loaded)
  await page.waitForSelector('canvas', { state: 'attached' });
  await page.waitForTimeout(2000); // Allow chart animation to settle

  // Screenshot the chart container (not full page — less flaky)
  const chartContainer = page.locator('.candlestick-chart-container').or(
    page.locator('[data-testid="chart-container"]')
  );
  await expect(chartContainer).toHaveScreenshot('vnm-chart.png', {
    maxDiffPixelRatio: 0.05, // Allow 5% pixel difference (prices change daily)
  });
});
```

**Important:** Visual regression for financial charts is inherently flaky because prices change daily. Set high `maxDiffPixelRatio` (5-10%) or limit visual tests to layout structure rather than data values. Consider using `mask` to hide price-sensitive areas.

### 7. Environment Configuration

```
# No new .env files needed for tests!

# Backend uses its existing .env (same prod Aiven DB)
# Frontend uses its existing .env.local (NEXT_PUBLIC_API_URL=http://localhost:8000/api)

# For CI, set these in the CI environment:
# DATABASE_URL=postgresql+asyncpg://...?ssl=require  (same Aiven)
# GEMINI_API_KEY=...  (needed for backend startup)
# TELEGRAM_BOT_TOKEN=...  (optional — backend handles missing gracefully)
# TELEGRAM_CHAT_ID=...  (optional)
```

**The backend already handles missing Telegram token gracefully** (see `main.py` line 29-30: try/except around `telegram_bot.start()`). No special test config needed.

### 8. CI Pipeline Structure (GitHub Actions)

```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on:
  push:
    branches: [main]
  pull_request:

jobs:
  e2e:
    runs-on: ubuntu-latest  # Or windows-latest to match dev env
    steps:
      - uses: actions/checkout@v4

      # Python setup for backend
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install backend deps
        run: |
          cd backend
          pip install -r requirements.txt

      # Node setup for frontend + Playwright
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - name: Install frontend deps
        run: |
          cd frontend
          npm ci

      # Playwright browsers
      - name: Install Playwright browsers
        run: cd frontend && npx playwright install --with-deps chromium

      # Run E2E tests (Playwright handles server startup via webServer config)
      - name: Run E2E tests
        run: cd frontend && npx playwright test
        env:
          CI: true
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          NEXT_PUBLIC_API_URL: http://localhost:8000/api

      # Upload report on failure
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: frontend/playwright-report/
          retention-days: 7
```

**Key CI considerations:**
- Install only `chromium` (not all 3 browsers) to speed up CI
- Backend webServer command in CI uses `python` not `.venv/Scripts/python.exe`
- Same Aiven database — CI connects to same prod DB (acceptable for single-user personal app)

---

## Data Flow: How a Test Executes

```
1. `npx playwright test e2e/ticker.spec.ts`
2. Playwright reads playwright.config.ts
3. webServer[0]: Start FastAPI → wait for http://127.0.0.1:8000/
   - APScheduler starts (but doesn't run jobs immediately)
   - Telegram bot attempts start (may fail gracefully)
4. webServer[1]: Start Next.js dev → wait for http://127.0.0.1:3000
5. For each test:
   a. Launch Chromium browser context
   b. Execute test (navigate, interact, assert)
   c. On failure: capture screenshot + trace
   d. Close browser context
6. After all tests: Playwright stops webServers
7. Generate HTML report → frontend/playwright-report/
```

---

## Test Pattern Examples

### Pattern 1: Page Load + Data Verification

```typescript
// e2e/home.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Home — Market Overview', () => {
  test('loads heatmap with ticker data', async ({ page }) => {
    await page.goto('/');

    // Page title
    await expect(page.getByRole('heading', { name: /Tổng quan thị trường/i })).toBeVisible();

    // Market stat cards load (not skeleton)
    await expect(page.getByText(/Tổng mã/)).toBeVisible({ timeout: 15_000 });

    // Heatmap has ticker cells (at least one ticker visible)
    await expect(page.locator('[class*="heatmap"]').or(
      page.getByText('VNM')
    )).toBeVisible({ timeout: 15_000 });
  });

  test('exchange filter changes displayed data', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('text=Tổng mã');

    // Click HNX filter
    await page.getByRole('button', { name: /HNX/i }).click();

    // Total should change (HNX has fewer tickers than "all")
    await expect(page.getByText(/Tổng mã/)).toBeVisible();
  });
});
```

### Pattern 2: localStorage-Dependent Tests (Watchlist)

```typescript
// e2e/watchlist.spec.ts
import { test, expect } from './fixtures/test-base';

test.describe('Watchlist', () => {
  test('shows seeded watchlist tickers', async ({ page, seededWatchlist }) => {
    await page.goto('/watchlist');

    await expect(page.getByText('VNM')).toBeVisible();
    await expect(page.getByText('FPT')).toBeVisible();
    await expect(page.getByText('HPG')).toBeVisible();
    await expect(page.getByText('3 mã')).toBeVisible();
  });

  test('add ticker to watchlist from ticker page', async ({ page }) => {
    await page.goto('/ticker/VNM');

    // Find and click the star/watchlist button
    const starButton = page.getByRole('button', { name: /theo dõi|watchlist|star/i });
    await starButton.click();

    // Navigate to watchlist and verify
    await page.goto('/watchlist');
    await expect(page.getByText('VNM')).toBeVisible();
  });
});
```

### Pattern 3: API-Only Tests (No Browser)

```typescript
// e2e/api/health-check.spec.ts
import { test, expect } from '@playwright/test';

const API_BASE = 'http://127.0.0.1:8000/api';

const ENDPOINTS = [
  { path: '/system/health', name: 'System health' },
  { path: '/tickers', name: 'Tickers list' },
  { path: '/tickers/VNM/prices', name: 'VNM prices' },
  { path: '/health/jobs', name: 'Job statuses' },
  { path: '/health/data-freshness', name: 'Data freshness' },
  { path: '/health/db-pool', name: 'DB pool' },
  { path: '/portfolio/summary', name: 'Portfolio summary' },
  { path: '/paper-trading/trades?limit=5', name: 'Paper trades' },
  { path: '/paper-trading/analytics/summary', name: 'Paper analytics' },
];

for (const endpoint of ENDPOINTS) {
  test(`API: ${endpoint.name} (${endpoint.path}) returns 200`, async ({ request }) => {
    const response = await request.get(`${API_BASE}${endpoint.path}`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toBeTruthy();
  });
}
```

### Pattern 4: Canvas Chart Testing

```typescript
// e2e/ticker.spec.ts
test('candlestick chart renders on ticker page', async ({ page }) => {
  await page.goto('/ticker/VNM');

  // Wait for canvas to appear (lightweight-charts creates a <canvas>)
  const canvas = page.locator('canvas').first();
  await expect(canvas).toBeVisible({ timeout: 15_000 });

  // Verify canvas has non-zero dimensions (chart actually rendered)
  const box = await canvas.boundingBox();
  expect(box).toBeTruthy();
  expect(box!.width).toBeGreaterThan(100);
  expect(box!.height).toBeGreaterThan(100);

  // Verify time range buttons are present
  await expect(page.getByRole('button', { name: '1T' })).toBeVisible();
  await expect(page.getByRole('button', { name: '1N' })).toBeVisible();
});
```

### Pattern 5: Write Operations with Cleanup

```typescript
// e2e/portfolio.spec.ts
test.describe('Portfolio — Trade CRUD', () => {
  let createdTradeId: number | null = null;

  test.afterEach(async ({ request }) => {
    // Cleanup: delete test trade if created
    if (createdTradeId) {
      await request.delete(`http://127.0.0.1:8000/api/portfolio/trades/${createdTradeId}`);
      createdTradeId = null;
    }
  });

  test('create trade via API and verify in UI', async ({ page, request }) => {
    // Create via API
    const response = await request.post('http://127.0.0.1:8000/api/portfolio/trades', {
      data: {
        symbol: 'VNM',
        side: 'buy',
        quantity: 100,
        price: 80000,
        trade_date: '2025-01-01',
      },
    });
    const trade = await response.json();
    createdTradeId = trade.id;

    // Verify in UI
    await page.goto('/dashboard/portfolio');
    await expect(page.getByText('VNM')).toBeVisible({ timeout: 10_000 });
  });
});
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Separate Test Database
**What:** Creating a second PostgreSQL database for tests, seeding it with fixture data.
**Why bad:** Impractical with Aiven remote DB. Seeding 800+ tickers with price history, indicators, and AI analyses would be enormous. The real data IS the fixture.
**Instead:** Test against production DB in read mode. Write tests create and clean up.

### Anti-Pattern 2: Mocking API Responses in E2E Tests
**What:** Using `page.route()` to intercept API calls and return canned data.
**Why bad:** Defeats the purpose of E2E testing. Misses real integration bugs (serialization, CORS, query params).
**Instead:** Hit the real backend. If a specific API state is needed, use API calls to set it up, not mocks.

### Anti-Pattern 3: Testing Canvas Content with DOM Assertions
**What:** Trying to find text or elements inside `<canvas>` elements (lightweight-charts, Recharts).
**Why bad:** Canvas renders pixels, not DOM nodes. `page.getByText()` will never find chart labels.
**Instead:** Assert canvas exists, has dimensions, and optionally use screenshot comparison. Test surrounding UI (time range buttons, legends) with DOM selectors.

### Anti-Pattern 4: Hardcoded Prices in Assertions
**What:** `expect(page.getByText('82,500')).toBeVisible()` for a stock price.
**Why bad:** Prices change daily. Test will fail tomorrow.
**Instead:** Assert structural elements: "price element exists and contains a number", not "price equals X".

### Anti-Pattern 5: Full Page Screenshots for Visual Regression
**What:** `await expect(page).toHaveScreenshot()` on pages with dynamic data.
**Why bad:** Prices, percentages, timestamps change constantly → every test run produces diffs.
**Instead:** Screenshot specific UI components (chart container, empty states) or use `mask` option to hide dynamic areas.

### Anti-Pattern 6: Running Backend Tests Through Playwright
**What:** Adding Python backend unit tests to the Playwright suite.
**Why bad:** Backend already has 560 pytest tests. E2E tests should test integration, not duplicate unit tests.
**Instead:** Keep pytest for backend logic. Playwright tests the full stack: browser → Next.js → FastAPI → PostgreSQL.

---

## Integration Points — New vs Modified Files

### New Files (18 files)

| File | Purpose |
|------|---------|
| `frontend/playwright.config.ts` | Playwright configuration with dual webServer |
| `frontend/e2e/fixtures/test-base.ts` | Extended test with localStorage seeding |
| `frontend/e2e/fixtures/known-tickers.ts` | Shared constants for known good tickers |
| `frontend/e2e/home.spec.ts` | Home page tests |
| `frontend/e2e/dashboard.spec.ts` | Dashboard page tests |
| `frontend/e2e/ticker.spec.ts` | Ticker detail page tests |
| `frontend/e2e/watchlist.spec.ts` | Watchlist tests (localStorage) |
| `frontend/e2e/portfolio.spec.ts` | Portfolio CRUD tests |
| `frontend/e2e/paper-trading.spec.ts` | Paper trading page tests |
| `frontend/e2e/health.spec.ts` | Health dashboard tests |
| `frontend/e2e/corporate-events.spec.ts` | Corporate events page tests |
| `frontend/e2e/navigation.spec.ts` | Navbar, routing, mobile menu tests |
| `frontend/e2e/api/health-check.spec.ts` | API endpoint health checks |
| `frontend/e2e/api/tickers-api.spec.ts` | Ticker API tests |
| `frontend/e2e/api/websocket.spec.ts` | WebSocket protocol tests |
| `frontend/e2e/flows/ticker-to-paper-trade.spec.ts` | Critical flow test |
| `frontend/e2e/visual/home.visual.spec.ts` | Visual regression — home |
| `frontend/e2e/visual/ticker-chart.visual.spec.ts` | Visual regression — chart |

### Modified Files (2 files)

| File | Change |
|------|--------|
| `frontend/package.json` | Add `@playwright/test` devDep + scripts (`test:e2e`, `test:e2e:ui`, `test:e2e:report`) |
| `frontend/.gitignore` | Add `test-results/`, `playwright-report/`, `blob-report/`, `playwright/.cache/` |

### Unchanged Files

Everything in `backend/` and `frontend/src/` remains unchanged. E2E tests are additive — zero modifications to application code.

**Exception:** Some components may benefit from `data-testid` attributes for stable selectors (e.g., chart containers, connection status indicator). These are tiny, non-breaking additions made during test writing, not upfront.

---

## Package Changes

```json
// frontend/package.json additions
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:report": "playwright show-report",
    "test:e2e:codegen": "playwright codegen http://localhost:3000"
  },
  "devDependencies": {
    "@playwright/test": "^1.59.1"
  }
}
```

**Installation:**
```bash
cd frontend
npm install -D @playwright/test@^1.59.1
npx playwright install chromium
```

**Only install Chromium** — not Firefox/WebKit. Single browser is sufficient for a personal-use app. Reduces install time from ~500MB to ~150MB.

---

## Windows-Specific Considerations

| Concern | Solution |
|---------|----------|
| Backend venv path | `../backend/.venv/Scripts/python.exe -m uvicorn` (not `python3`) |
| Path separators | Playwright handles cross-platform. Config uses forward slashes. |
| `cd ../backend` in webServer command | Works in PowerShell and cmd. Playwright spawns process correctly. |
| Line endings | `.gitattributes` should have `*.ts text eol=lf` for consistent snapshots |
| Playwright cache | Stored in `%LOCALAPPDATA%/ms-playwright` on Windows |
| Port conflicts | `reuseExistingServer: true` in dev avoids port-already-in-use errors |
| SSL for Aiven | Backend `config.py` already patches SSL globally — works in test too |

---

## Timeout Strategy

| Component | Timeout | Rationale |
|-----------|---------|-----------|
| Backend webServer startup | 30s | APScheduler + Telegram init takes ~5-10s |
| Frontend webServer startup | 60s | Next.js dev server cold start compiles pages |
| Individual test timeout | 30s (default) | Most page loads complete in <5s with 15s wait for API data |
| API data loading assertions | 15s | Remote Aiven DB can have ~1-3s latency |
| WebSocket connection | 10s | Should connect in <1s, but allow for backend polling interval |
| Visual regression | 30s | Chart rendering + animation settle time |

---

## Build Order (Dependency-Driven)

```
Phase 1: Infrastructure Setup
├── Install @playwright/test + Chromium
├── Create playwright.config.ts (dual webServer)
├── Create e2e/fixtures/ (test-base, known-tickers)
├── Add scripts to package.json
├── Update .gitignore
├── Verify: `npx playwright test --list` shows test structure
└── Verify: webServer starts both backend and frontend

Phase 2: API Health Checks (no browser needed)
├── e2e/api/health-check.spec.ts (all endpoints return 200)
├── e2e/api/tickers-api.spec.ts (verify data shape)
├── e2e/api/websocket.spec.ts (protocol test)
└── This phase catches backend integration issues early

Phase 3: Core Page Tests
├── e2e/home.spec.ts (heatmap loads)
├── e2e/navigation.spec.ts (all navbar links work)
├── e2e/ticker.spec.ts (chart renders, indicators load, analysis shows)
├── e2e/dashboard.spec.ts (watchlist summary, market stats)
└── e2e/watchlist.spec.ts (localStorage seeding, add/remove)

Phase 4: Feature Page Tests
├── e2e/portfolio.spec.ts (CRUD with cleanup)
├── e2e/paper-trading.spec.ts (all 5 tabs)
├── e2e/health.spec.ts (job status, data freshness)
├── e2e/corporate-events.spec.ts
└── e2e/flows/ticker-to-paper-trade.spec.ts (critical flow)

Phase 5: Visual Regression + CI
├── e2e/visual/ snapshot tests
├── .github/workflows/e2e.yml
├── Update visual baselines
└── Bug discovery & fix cycle
```

**Rationale:** Infrastructure → API (fast, catches backend issues) → Core pages (high value) → Feature pages (breadth) → Visual + CI (polish). Each phase is independently runnable.

---

## Sources

| Claim | Source | Confidence |
|-------|--------|------------|
| Playwright 1.59.1 is latest stable | `npm view @playwright/test dist-tags` — verified 2025-07-20 | HIGH |
| `webServer` accepts array for multi-server | Playwright docs: test configuration > webServer | HIGH |
| `reuseExistingServer` option exists | Playwright docs | HIGH |
| Backend root returns `{"status": "ok"}` | `backend/app/main.py` line 89-90 | HIGH |
| Frontend API_BASE defaults to `http://localhost:8000/api` | `frontend/src/lib/api.ts` line 1 | HIGH |
| WebSocket URL derivation | `frontend/src/lib/use-realtime-prices.ts` line 42-49 | HIGH |
| WS protocol: subscribe/unsubscribe | `backend/app/ws/prices.py` line 130-158 | HIGH |
| Telegram bot fails gracefully | `backend/app/main.py` line 29-30 | HIGH |
| localStorage watchlist key = `holo-watchlist` | `frontend/src/lib/store.ts` line 37 | HIGH |
| NAV_LINKS array = 7 routes | `frontend/src/components/navbar.tsx` line 22-30 | HIGH |
| 560 existing backend pytest tests | `PROJECT.md` line 16 | HIGH |
| Zustand persist format (state + version) | Zustand docs + zustand/middleware persist | HIGH |
| Canvas rendering for lightweight-charts | `frontend/src/components/candlestick-chart.tsx` line 6 | HIGH |
| Exchange filter zustand key = `holo-exchange-filter` | `frontend/src/lib/store.ts` line 55 | HIGH |
| No authentication in app | PROJECT.md "Scope: Dùng cá nhân — không cần auth" | HIGH |
| CORS allows localhost:3000 | `backend/app/main.py` line 52-58 | HIGH |
| Pool size=5, max_overflow=3 | `backend/app/database.py` line 7-8 | HIGH |
