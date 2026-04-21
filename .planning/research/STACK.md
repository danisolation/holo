# Technology Stack — E2E Testing & Quality Assurance

**Project:** Holo v5.0 — E2E Testing & Quality Assurance
**Researched:** 2025-07-21
**Confidence:** HIGH (versions verified via npm registry)

## Recommended Stack

### Core Testing Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `@playwright/test` | ^1.59.1 | E2E test runner + assertions + visual comparison | Only serious contender for modern E2E. Built-in `toHaveScreenshot()` eliminates need for separate visual regression tool. Auto-wait, parallel execution, multi-browser, native `webServer` config for Next.js startup. `APIRequestContext` built-in for API testing — no extra HTTP library needed. |
| `playwright` | ^1.59.1 | Browser automation core (auto-installed as dep of @playwright/test) | Pulled automatically. Provides browser binaries via `npx playwright install`. |

### Visual Regression (Built into Playwright — NO extra library needed)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Playwright `toHaveScreenshot()` | Built-in | Pixel-level visual regression | Ships with `@playwright/test`. Uses `pixelmatch` internally. Supports `maxDiffPixels`, `maxDiffPixelRatio`, `threshold` tuning. Generates golden screenshots on first run, compares on subsequent runs. Produces diff images in test-results/. No SaaS dependency, no extra cost, no setup. |
| Playwright `toMatchSnapshot()` | Built-in | Non-image snapshot comparison (HTML, text, JSON) | Useful for API response shape validation. Same update workflow (`--update-snapshots`). |

**Decision: Do NOT add Argos CI, Percy, Chromatic, or any SaaS visual regression tool.** This is a single-user personal project. Playwright's built-in `toHaveScreenshot()` is fully sufficient. SaaS tools add cost, complexity, and external dependency for zero benefit here.

### API Testing (Built into Playwright — NO extra library needed)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Playwright `APIRequestContext` | Built-in | Direct HTTP API testing without browser | `request` fixture in Playwright allows `request.get()`, `request.post()`, etc. Returns parsed JSON. Shares auth/cookies with browser context. Perfect for testing FastAPI endpoints directly. No need for supertest, axios, or got in test code. |

### Dev Utilities

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dotenv` | ^17.4.2 | Load `.env.test` for test-specific config | Load `NEXT_PUBLIC_API_URL`, `DATABASE_URL` for test env. Playwright config can use `dotenv/config` in `playwright.config.ts`. |
| `@faker-js/faker` | ^10.4.0 | Generate realistic test data | Portfolio entries, watchlist symbols, paper trade amounts. Avoids hardcoded test data. Use sparingly — most Holo data is real stock data (VN30 symbols). |

### Accessibility Testing (Optional but recommended)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@axe-core/playwright` | ^4.11.2 | Automated accessibility auditing in E2E tests | Run on each page during E2E. Catches WCAG violations. Lightweight integration: `const results = await new AxeBuilder({ page }).analyze()`. Not required for MVP but trivial to add. |

### Test Reporting

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Playwright HTML Reporter | Built-in | Rich HTML test report with screenshots, traces, videos | Default reporter. Opens in browser with `npx playwright show-report`. Includes trace viewer for debugging failures. Zero config. |
| Playwright JSON Reporter | Built-in | Machine-readable results | For CI integration if needed later. |
| `allure-playwright` | ^3.7.1 | **SKIP — do not add** | Overkill for personal project. Built-in HTML reporter is superior for single-developer use. |

## What NOT to Add

| Library | Why NOT |
|---------|---------|
| Cypress | Chose Playwright. Cypress has worse multi-tab support, no native API testing context, slower parallel execution. Decision already made. |
| Jest + Testing Library (for E2E) | Wrong tool. Jest is for unit/integration. Playwright handles E2E. |
| WebdriverIO | Legacy Selenium-based. Playwright is faster, better DX, better TypeScript support. |
| Puppeteer | Lower-level, Chromium-only, no built-in test runner or assertions. |
| `@argos-ci/playwright` | SaaS visual regression. Overkill for personal project. Playwright built-in `toHaveScreenshot()` covers this. |
| Percy / Chromatic | Same — SaaS visual regression. Not needed. |
| `pixelmatch` (standalone) | Already used internally by Playwright's `toHaveScreenshot()`. Don't install separately. |
| `msw` (Mock Service Worker) | **Not for E2E.** Holo E2E tests should hit real FastAPI backend. MSW is for unit/integration testing of frontend in isolation — which is NOT the v5.0 scope. |
| `start-server-and-test` | Playwright has built-in `webServer` config in `playwright.config.ts`. Don't add npm packages for what Playwright does natively. |
| `wait-on` | Same — `webServer.url` + `webServer.reuseExistingServer` handles this. |
| `concurrently` | Same — `webServer` array in Playwright config can start multiple servers. |
| Supertest / got / axios (in tests) | Playwright's `APIRequestContext` handles all HTTP testing natively. |

## Playwright Configuration Strategy

### webServer Config (Critical for Next.js + FastAPI)

Playwright's `webServer` config can start **both** the FastAPI backend and Next.js frontend before tests run:

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';
import path from 'path';

dotenv.config({ path: path.resolve(__dirname, '.env.test') });

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  // Start both servers before tests
  webServer: [
    {
      command: 'cd ../backend && python -m uvicorn app.main:app --port 8001',
      url: 'http://localhost:8001/api/health/status',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      env: {
        DATABASE_URL: process.env.TEST_DATABASE_URL || '',
      },
    },
    {
      command: 'npm run dev -- --port 3000',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      env: {
        NEXT_PUBLIC_API_URL: 'http://localhost:8001/api',
      },
    },
  ],

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 7'] },
    },
  ],
});
```

### Key Config Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Test location | `frontend/e2e/` | Co-located with frontend since tests drive a browser. Playwright config lives in `frontend/`. |
| Browsers | Chromium + Mobile Chrome | Single-user app — don't waste time on Firefox/WebKit. Chromium covers 95%+ of personal use. Mobile Chrome catches responsive issues. |
| `reuseExistingServer` | `true` in dev, `false` in CI | Dev: start servers manually for faster iteration. CI: Playwright manages server lifecycle. |
| `fullyParallel` | `true` | Tests should be independent. Parallel = faster feedback. |
| Retries | 0 local, 2 CI | Don't mask flaky tests locally. CI retries handle infrastructure flakiness. |
| Trace | `on-first-retry` | Full trace on failure for debugging without bloating passing test artifacts. |
| Video | `retain-on-failure` | Videos only kept for failed tests. Invaluable for debugging. |
| Screenshots | `only-on-failure` + explicit `toHaveScreenshot()` for visual regression | Auto-screenshot on failure for debugging. Intentional screenshots for visual regression testing. |

## Visual Regression Configuration

```typescript
// In playwright.config.ts `use` block
use: {
  // ...other options
},

// In expect configuration
expect: {
  toHaveScreenshot: {
    maxDiffPixelRatio: 0.01,  // Allow 1% pixel difference (animations, anti-aliasing)
    threshold: 0.2,           // Per-pixel color threshold (0-1)
    animations: 'disabled',   // Disable CSS animations for stable screenshots
  },
},
```

### Screenshot Management

- Golden screenshots stored in `e2e/__screenshots__/` (committed to git)
- Diff images generated in `test-results/` (gitignored)
- Update goldens: `npx playwright test --update-snapshots`
- Platform-specific: Playwright auto-suffixes with OS/browser for cross-platform golden management

## API Testing Pattern

```typescript
// e2e/api/health.spec.ts
import { test, expect } from '@playwright/test';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api';

test.describe('API Health Checks', () => {
  test('GET /api/health/status returns healthy', async ({ request }) => {
    const response = await request.get(`${API}/health/status`);
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body).toHaveProperty('status');
  });

  test('GET /api/tickers returns ticker list', async ({ request }) => {
    const response = await request.get(`${API}/tickers`);
    expect(response.ok()).toBeTruthy();
    const tickers = await response.json();
    expect(tickers.length).toBeGreaterThan(0);
  });
});
```

## Project File Structure

```
frontend/
├── e2e/
│   ├── api/                      # API-only tests (no browser)
│   │   ├── health.spec.ts
│   │   ├── tickers.spec.ts
│   │   ├── portfolio.spec.ts
│   │   └── paper-trading.spec.ts
│   ├── pages/                    # Page-level E2E tests
│   │   ├── dashboard.spec.ts
│   │   ├── ticker-detail.spec.ts
│   │   ├── watchlist.spec.ts
│   │   ├── portfolio.spec.ts
│   │   ├── paper-trading.spec.ts
│   │   ├── health.spec.ts
│   │   └── corporate-events.spec.ts
│   ├── flows/                    # Multi-page user flow tests
│   │   └── signal-to-trade.spec.ts
│   ├── visual/                   # Dedicated visual regression tests
│   │   ├── dashboard.visual.spec.ts
│   │   └── charts.visual.spec.ts
│   ├── __screenshots__/          # Golden screenshots (committed)
│   └── fixtures/                 # Shared test helpers
│       ├── base.ts               # Extended test with common setup
│       └── api-helpers.ts        # Reusable API call wrappers
├── playwright.config.ts
├── .env.test                     # Test environment variables
└── package.json
```

## Installation

```bash
# From frontend/ directory
cd frontend

# Core — this is ALL you need
npm install -D @playwright/test

# Install browser binaries (Chromium only — skip Firefox/WebKit)
npx playwright install chromium

# Optional: accessibility testing
npm install -D @axe-core/playwright

# Optional: test data generation
npm install -D @faker-js/faker

# Already in project, no install needed:
# dotenv — use inline in playwright.config.ts via dotenv/config
```

### package.json Scripts

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:headed": "playwright test --headed",
    "test:e2e:api": "playwright test --grep @api",
    "test:e2e:visual": "playwright test --grep @visual",
    "test:e2e:update-snapshots": "playwright test --update-snapshots",
    "test:e2e:report": "playwright show-report"
  }
}
```

## Integration Points with Existing Stack

### Next.js 16 Integration

| Concern | Approach |
|---------|----------|
| App Router pages | Playwright navigates to routes (`/`, `/dashboard`, `/ticker/VNM`, `/watchlist`). No special config needed. |
| Client components (React Query) | Tests wait for data to load via `page.waitForSelector()` or Playwright auto-wait. No mock needed — real API. |
| WebSocket (real-time prices) | Playwright supports WebSocket interception if needed, but for E2E we let it connect to real backend WS. |
| Dynamic routes (`/ticker/[symbol]`) | Test with real symbols: `page.goto('/ticker/VNM')`. |
| `NEXT_PUBLIC_API_URL` env var | Set in `webServer.env` to point to test backend port. |

### FastAPI Integration

| Concern | Approach |
|---------|----------|
| Server startup | `webServer` config starts uvicorn. Health check URL ensures it's ready before tests. |
| Database state | Tests run against real database (Aiven PostgreSQL). Data is read-heavy — stock data already exists. Write tests (portfolio, paper trading) should clean up after themselves. |
| API endpoints | Tested both via browser E2E (frontend → API) and directly via `APIRequestContext`. |
| WebSocket `/ws/prices` | E2E tests verify the connection-status indicator renders. Direct WS testing is out of scope for v5.0 (would require `ws` library). |
| CORS | Backend already allows `localhost:3000`. Test server uses same port. |

### Existing Backend pytest Integration

| Concern | Approach |
|---------|----------|
| 560 existing unit tests | **Untouched.** Playwright E2E tests are additive, not replacement. |
| Backend test runner | pytest stays for unit tests. Playwright for E2E. Separate commands, separate concerns. |
| CI pipeline | Run `pytest` first (fast, no browser), then `playwright test` (slower, needs browser). |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| E2E Framework | Playwright | Cypress | Cypress: no multi-tab, no native API context, slower parallelism, paid dashboard for CI features. Playwright is free, faster, better TS, better multi-browser. |
| E2E Framework | Playwright | WebdriverIO | Selenium-based legacy. Slower, worse DX, no built-in visual regression. |
| Visual Regression | Playwright built-in | Argos CI | SaaS cost, external dependency, overkill for personal project. |
| Visual Regression | Playwright built-in | Percy | Same — SaaS, paid, unnecessary. |
| Visual Regression | Playwright built-in | BackstopJS | Separate tool with its own config. Playwright `toHaveScreenshot()` is tightly integrated, zero-config. |
| API Testing | Playwright APIRequestContext | Supertest + Jest | Extra dependencies. Playwright already has HTTP client built in. |
| Server Management | Playwright webServer | start-server-and-test | Extra dependency for what Playwright does natively. |
| Test Data | @faker-js/faker | chance.js | Faker has better TypeScript support, larger community, more locale options. |

## Version Compatibility Matrix

| Package | Version | Node.js | Notes |
|---------|---------|---------|-------|
| `@playwright/test` | 1.59.1 | ≥18 | Current stable. Ships with Chromium 136, Firefox 137, WebKit 18.4. |
| `@axe-core/playwright` | 4.11.2 | ≥18 | Compatible with Playwright 1.x. |
| `@faker-js/faker` | 10.4.0 | ≥18 | ESM-first since v9. Works with TypeScript out of the box. |
| `dotenv` | 17.4.2 | ≥12 | No compatibility concerns. |

## Sources

- npm registry: `npm view @playwright/test version` → 1.59.1 (verified 2025-07-21)
- npm registry: `npm view @axe-core/playwright version` → 4.11.2 (verified 2025-07-21)
- npm registry: `npm view @faker-js/faker version` → 10.4.0 (verified 2025-07-21)
- Playwright docs: `webServer` configuration, `toHaveScreenshot()`, `APIRequestContext`
- Existing project: `frontend/package.json`, `backend/requirements.txt`, `backend/app/main.py`
