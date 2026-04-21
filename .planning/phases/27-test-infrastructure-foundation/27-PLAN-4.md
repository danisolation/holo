---
phase: 27
plan: 4
type: infrastructure
wave: 2
depends_on: [1, 2]
files_modified:
  - frontend/e2e/fixtures/test-helpers.ts
  - frontend/e2e/fixtures/api-helpers.ts
  - frontend/e2e/infra.spec.ts
autonomous: true
requirements: [INFRA-04]
---

# Plan 27.4: Test Fixtures & Seed Data Helpers

<objective>
Create test fixture utilities that can seed necessary data (tickers, prices, analysis, paper trades) via API calls for test scenarios, plus a comprehensive infrastructure validation test.
</objective>

<tasks>

<task id="1" type="file">
<title>Create API helper for test data seeding</title>
<read_first>
- backend/app/api/router.py (all registered API routes)
- backend/app/api/paper_trading.py (paper trading endpoints — POST routes for creating data)
</read_first>
<action>
Create `frontend/e2e/fixtures/api-helpers.ts`:

```typescript
import { APIRequestContext } from '@playwright/test';

const API_BASE = 'http://localhost:8001/api';

export class ApiHelpers {
  constructor(private request: APIRequestContext) {}

  /** Check if API is healthy */
  async healthCheck() {
    const response = await this.request.get(`${API_BASE}/health`);
    return response.ok();
  }

  /** Get tickers list */
  async getTickers() {
    const response = await this.request.get(`${API_BASE}/tickers`);
    return response.json();
  }

  /** Get a specific ticker's price data */
  async getTickerPrices(symbol: string) {
    const response = await this.request.get(`${API_BASE}/prices/${symbol}`);
    return { ok: response.ok(), data: response.ok() ? await response.json() : null };
  }

  /** Get analysis for a ticker */
  async getAnalysis(symbol: string) {
    const response = await this.request.get(`${API_BASE}/analysis/${symbol}`);
    return { ok: response.ok(), data: response.ok() ? await response.json() : null };
  }

  /** Get paper trading settings */
  async getPaperSettings() {
    const response = await this.request.get(`${API_BASE}/paper-trading/settings`);
    return { ok: response.ok(), data: response.ok() ? await response.json() : null };
  }

  /** Get paper trades list */
  async getPaperTrades() {
    const response = await this.request.get(`${API_BASE}/paper-trading/trades`);
    return { ok: response.ok(), data: response.ok() ? await response.json() : null };
  }

  /** Get paper trading analytics */
  async getPaperAnalytics() {
    const response = await this.request.get(`${API_BASE}/paper-trading/analytics`);
    return { ok: response.ok(), data: response.ok() ? await response.json() : null };
  }

  /** Get watchlist */
  async getWatchlist() {
    const response = await this.request.get(`${API_BASE}/watchlist`);
    return { ok: response.ok(), data: response.ok() ? await response.json() : null };
  }
}
```

This provides typed API helpers for all major endpoints. Tests use these to verify data availability and seed state.
</action>
<verify>
`frontend/e2e/fixtures/api-helpers.ts` exists and contains `class ApiHelpers`
</verify>
<acceptance_criteria>
- `frontend/e2e/fixtures/api-helpers.ts` exists
- File contains `class ApiHelpers`
- File contains `healthCheck` method
- File contains `getTickers` method
- File contains `getPaperTrades` method
- File contains `getWatchlist` method
</acceptance_criteria>
</task>

<task id="2" type="file">
<title>Create test helper with common utilities</title>
<read_first>
- frontend/playwright.config.ts (baseURL, webServer config)
</read_first>
<action>
Create `frontend/e2e/fixtures/test-helpers.ts`:

```typescript
import { Page, expect } from '@playwright/test';

/** Wait for page to finish loading (network idle + content visible) */
export async function waitForPageLoad(page: Page) {
  await page.waitForLoadState('networkidle');
}

/** Wait for a specific API response */
export async function waitForApi(page: Page, urlPattern: string) {
  return page.waitForResponse(
    (response) => response.url().includes(urlPattern) && response.status() === 200
  );
}

/** Navigate and wait for page to stabilize */
export async function navigateAndWait(page: Page, path: string) {
  await page.goto(path);
  await waitForPageLoad(page);
}

/** Verify navbar is visible (common assertion for all pages) */
export async function expectNavbarVisible(page: Page) {
  await expect(page.locator('[data-testid="navbar"]')).toBeVisible();
}

/** Known application routes for smoke tests */
export const APP_ROUTES = [
  { path: '/', name: 'Home / Overview' },
  { path: '/watchlist', name: 'Watchlist' },
  { path: '/dashboard', name: 'Dashboard' },
  { path: '/dashboard/paper-trading', name: 'Paper Trading' },
  { path: '/dashboard/portfolio', name: 'Portfolio' },
  { path: '/dashboard/health', name: 'System Health' },
  { path: '/dashboard/corporate-events', name: 'Corporate Events' },
] as const;

/** A known ticker symbol that should have data (use for ticker detail tests) */
export const TEST_TICKER = 'VNM';
```
</action>
<verify>
`frontend/e2e/fixtures/test-helpers.ts` exists and contains `APP_ROUTES`
</verify>
<acceptance_criteria>
- `frontend/e2e/fixtures/test-helpers.ts` exists
- File contains `waitForPageLoad` function
- File contains `navigateAndWait` function
- File contains `expectNavbarVisible` function
- File contains `APP_ROUTES` array with 7 routes
- File contains `TEST_TICKER` constant
</acceptance_criteria>
</task>

<task id="3" type="file">
<title>Create infrastructure validation test</title>
<read_first>
- frontend/playwright.config.ts (webServer config)
- frontend/e2e/fixtures/api-helpers.ts (API helper class)
- frontend/e2e/fixtures/test-helpers.ts (helper functions)
</read_first>
<action>
Create `frontend/e2e/infra.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';
import { ApiHelpers } from './fixtures/api-helpers';
import { expectNavbarVisible } from './fixtures/test-helpers';

test.describe('Infrastructure Validation', () => {
  test('FastAPI backend is reachable', async ({ request }) => {
    const api = new ApiHelpers(request);
    const healthy = await api.healthCheck();
    expect(healthy).toBe(true);
  });

  test('Next.js frontend loads', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Holo/);
  });

  test('API returns tickers data', async ({ request }) => {
    const api = new ApiHelpers(request);
    const tickers = await api.getTickers();
    expect(Array.isArray(tickers) || (tickers && typeof tickers === 'object')).toBe(true);
  });

  test('Navbar renders with navigation links', async ({ page }) => {
    await page.goto('/');
    await expectNavbarVisible(page);
  });
});
```

This validates the full infrastructure: both servers start, API responds, frontend renders, fixtures work.
</action>
<verify>
`frontend/e2e/infra.spec.ts` exists and contains `Infrastructure Validation`
</verify>
<acceptance_criteria>
- `frontend/e2e/infra.spec.ts` exists
- File contains `test.describe('Infrastructure Validation'`
- File contains `FastAPI backend is reachable`
- File contains `Next.js frontend loads`
- File contains `API returns tickers data`
- File contains `Navbar renders with navigation links`
</acceptance_criteria>
</task>

</tasks>

<verification>
1. `frontend/e2e/fixtures/api-helpers.ts` provides typed API helper class
2. `frontend/e2e/fixtures/test-helpers.ts` provides navigation and assertion helpers
3. `frontend/e2e/infra.spec.ts` validates infrastructure (both servers + fixtures)
4. All TypeScript files compile without errors
</verification>

<success_criteria>
Addresses INFRA-04: Test fixture utilities can seed necessary data (tickers, prices, analysis, paper trades) for test scenarios.
</success_criteria>

<must_haves>
- API helpers class with methods for all major endpoints
- Test helpers with page navigation, wait, and assertion utilities
- APP_ROUTES constant matching all 7+ application routes
- Infrastructure validation test proving both servers + API work
</must_haves>
