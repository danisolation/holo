# Domain Pitfalls — E2E Testing & Quality Assurance

**Domain:** E2E Testing for Stock Intelligence Platform (live financial data, charts, real-time WebSocket)
**Researched:** 2025-07-21

## Critical Pitfalls

Mistakes that cause the test suite to be abandoned or rewritten.

### Pitfall 1: Flaky Tests from Live Financial Data

**What goes wrong:** Stock prices, volumes, and indicator values change daily. Tests that assert on specific numbers (`expect(price).toBe(82500)`) fail the next trading day.
**Why it happens:** Natural instinct to assert exact values. Financial data is inherently volatile.
**Consequences:** Tests fail every Monday morning. Developers learn to ignore failures. Test suite becomes noise, not signal.
**Prevention:**
- Assert on **structure**, not **values**: `expect(price).toBeGreaterThan(0)`, `expect(tickers.length).toBeGreaterThan(0)`
- Assert on **presence**: `expect(page.getByTestId('price-display')).toBeVisible()`
- Visual regression: **mask dynamic data** areas: `{ mask: [page.locator('.price-cell')] }`
- API tests: validate response **shape** (has fields `symbol`, `close`, `volume`) not specific values
**Detection:** Tests that pass during market hours but fail after market close (or vice versa).

### Pitfall 2: Canvas-Based Charts Are Invisible to DOM Assertions

**What goes wrong:** lightweight-charts and Recharts render to `<canvas>` elements. `page.getByText('82,500')` won't find text rendered inside canvas. Tests that try to assert on chart content via DOM locators always fail.
**Why it happens:** Developer forgets that charting libraries bypass DOM rendering.
**Consequences:** Wasted time trying to locate chart elements. Tests give up on chart validation entirely, leaving the most complex UI component untested.
**Prevention:**
- Use `toHaveScreenshot()` for chart validation — visual comparison is the **only** reliable approach for canvas content
- Assert on chart **container** presence: `expect(page.getByTestId('candlestick-chart')).toBeVisible()`
- Assert on chart **controls/legends** (which ARE in DOM): indicator toggles, timeframe buttons
- For Recharts (SVG-based): some text IS in DOM as `<text>` elements — but don't rely on specific values
**Detection:** Test selectors that never match anything inside a chart component.

### Pitfall 3: WebSocket Connection Timing in Tests

**What goes wrong:** Tests navigate to pages with WebSocket connections (real-time prices). The WS connection may not establish before the test asserts on connection status or live prices.
**Why it happens:** WebSocket connections are async and may take a few hundred ms to establish. Playwright's auto-wait doesn't cover WebSocket state.
**Consequences:** Flaky tests — pass when WS is fast, fail when slow.
**Prevention:**
- Don't test WebSocket protocol directly in E2E — test the **UI indicator** instead
- Wait for the connection-status component to show "connected": `await page.waitForSelector('[data-testid="connection-status"][data-connected="true"]')`
- If connection-status component doesn't have `data-testid`, add it (minimal code change to support testing)
- Accept that WS tests may need a small explicit wait (300-500ms) after page load
**Detection:** Tests that pass 90% of the time but fail intermittently on CI.

### Pitfall 4: Visual Regression Chaos from Missing Stability Measures

**What goes wrong:** Screenshots differ on every run due to: loading spinners captured mid-animation, CSS transitions not complete, React Query data loading at different speeds, font rendering differences across OS.
**Why it happens:** Taking screenshot immediately after navigation without ensuring page stability.
**Consequences:** Every test run produces diffs. Developer raises `maxDiffPixelRatio` to absurd values (0.3+), making visual regression useless.
**Prevention:**
- **Wait for data load**: `await page.waitForSelector('[data-testid="content-loaded"]')` or wait for specific API responses: `await page.waitForResponse('**/api/tickers**')`
- **Disable animations**: `await page.emulateMedia({ reducedMotion: 'reduce' })` OR set in config globally
- **Use `animations: 'disabled'`** in `toHaveScreenshot()` config — Playwright can disable CSS animations automatically
- **Mask dynamic content**: stock prices, timestamps, "last updated" fields
- **Pin browser version**: don't auto-update Playwright in CI without updating golden screenshots
- **OS-consistent goldens**: generate on same OS as CI (Linux). Playwright auto-suffixes screenshots with platform.
**Detection:** More than 3 false-positive visual regression failures per week.

### Pitfall 5: Starting Both Servers Reliably

**What goes wrong:** Playwright's `webServer` config fails to start FastAPI or Next.js. Tests time out waiting for servers. Common causes: port already in use, Python venv not activated, wrong working directory, missing env vars.
**Why it happens:** Two separate tech stacks (Python + Node.js) with different startup requirements. FastAPI needs venv, Next.js needs `node_modules`.
**Consequences:** Tests can't run at all. Developer gives up on `webServer` and starts servers manually, losing CI automation.
**Prevention:**
- **FastAPI command**: use absolute path to venv Python: `../backend/.venv/Scripts/python -m uvicorn app.main:app --port 8001` (Windows) or `../backend/.venv/bin/python ...` (Linux)
- **Use a dedicated test port** (8001) different from dev port (8000) to avoid port conflicts
- **Health check URL**: `webServer.url` should be a fast endpoint: `http://localhost:8001/` (root returns `{"status": "ok"}`)
- **Generous timeout**: `timeout: 60_000` for first startup (cold start can be slow)
- **`reuseExistingServer: !process.env.CI`**: reuse in dev (fast iteration), fresh start in CI (clean state)
- **Environment variables**: Pass `DATABASE_URL` explicitly in `webServer.env` — don't rely on shell environment
**Detection:** `webServer` timeout errors in test output.

## Moderate Pitfalls

### Pitfall 6: Over-testing API in E2E When pytest Already Covers It

**What goes wrong:** Writing extensive API tests in Playwright that duplicate the 560 existing pytest tests. Testing query parameters, edge cases, error codes — all already covered by backend unit tests.
**Prevention:**
- Playwright API tests should be **integration smoke tests**: does the endpoint respond? Is the response shape correct? Is the data non-empty?
- Leave edge cases, error handling, boundary testing to pytest
- Rule of thumb: ~2-3 Playwright API tests per endpoint group, not per endpoint variant

### Pitfall 7: Brittle Locators That Break on UI Changes

**What goes wrong:** Tests use CSS class selectors (`.bg-green-500`, `.p-4.rounded-lg`) or complex DOM paths that break on any Tailwind class change or component restructuring.
**Prevention:**
- Priority order: role > text > `data-testid` > CSS selector
- Add `data-testid` attributes to key components during v5.0 (this is expected — it's part of making the app testable)
- Key components needing `data-testid`: chart containers, heatmap, connection status, loading states, empty states

### Pitfall 8: Ignoring Test Data Cleanup for Write Operations

**What goes wrong:** Portfolio entries and paper trades created during tests accumulate in the real database. Eventually, the portfolio page shows 50 test entries mixed with real data.
**Prevention:**
- Every `test.beforeAll` that creates data MUST have a matching `test.afterAll` that deletes it
- Use unique identifiers in test data: symbol `ZZZ_TEST` or notes containing `[E2E-TEST]`
- Consider: a cleanup script that deletes all `[E2E-TEST]` tagged data (safety net)
- Alternative: run write tests against a separate test database (but adds complexity)

### Pitfall 9: Screenshot Golden Overload

**What goes wrong:** Taking full-page screenshots of every page, every viewport, every state. Golden directory balloons to 200+ images. Any frontend change requires updating dozens of screenshots. Developers stop maintaining goldens.
**Prevention:**
- Limit visual regression to **5-8 key views**: dashboard overview, ticker detail, portfolio, paper trading analytics, health page
- Use component-level screenshots for critical components (heatmap, chart) not full-page
- Group visual tests in `e2e/visual/` — easy to skip during rapid development: `--grep-invert @visual`
- Document the golden update process clearly: `npx playwright test --update-snapshots --grep @visual`

## Minor Pitfalls

### Pitfall 10: Forgetting to Install Playwright Browsers

**What goes wrong:** `npx playwright install` not run after version update. Tests fail with "browser not found".
**Prevention:** Add `npx playwright install chromium` to CI setup step. Add a `postinstall` script or document in README.

### Pitfall 11: .env.test Not Created

**What goes wrong:** Tests run against production Aiven database with wrong API URL. Or `NEXT_PUBLIC_API_URL` points to port 8000 (dev) instead of 8001 (test).
**Prevention:** Template `.env.test.example` committed to repo. Documentation says "copy and fill". CI has env vars injected.

### Pitfall 12: Trace/Video Files Bloating Git

**What goes wrong:** `test-results/`, `playwright-report/` accidentally committed. Gigabytes of videos and trace files.
**Prevention:** Add to `.gitignore` from day one:
```
test-results/
playwright-report/
blob-report/
```

### Pitfall 13: Vietnamese Text Encoding in Assertions

**What goes wrong:** Tests assert on Vietnamese text (`expect(page.getByText('Danh mục')).toBeVisible()`) and fail due to encoding issues or text not matching.
**Prevention:** Use `page.getByText()` with regex for partial matching. Test a few Vietnamese strings early to verify encoding works. If the app is English-only in UI, this isn't an issue — but Holo's AI analysis outputs are in Vietnamese.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Playwright setup | Server startup failures (Pitfall 5) | Test webServer config manually before writing any tests. Get both servers starting reliably first. |
| Page smoke tests | Canvas chart assertions (Pitfall 2) | Don't try to assert chart content via DOM. Use screenshot or container presence only. |
| API health checks | Over-testing (Pitfall 6) | Smoke-level only. Shape validation, not edge cases. |
| Visual regression | Instability chaos (Pitfall 4) | Start with 2-3 stable pages. Add more only after proving stability. Mask all dynamic data. |
| Critical flow tests | Live data flakiness (Pitfall 1) | Assert on structure/presence, never on specific financial values. |
| Bug discovery | Writing tests for current bugs, not regression | Bug fix first, then write test that would have caught it. Not the reverse. |
| CI integration | Missing browser binaries (Pitfall 10), missing env vars (Pitfall 11) | CI setup script installs browsers + validates env vars before test run. |

## Sources

- Playwright docs: visual comparison best practices, webServer configuration
- Common E2E testing failure modes in financial applications
- Project analysis: canvas-based charts (lightweight-charts), WebSocket real-time prices, Vietnamese text content
- Existing stack: FastAPI on different port than Next.js, venv-based Python environment
