---
phase: 27
plan: 1
type: infrastructure
wave: 1
depends_on: []
files_modified:
  - frontend/package.json
  - frontend/playwright.config.ts
  - frontend/e2e/smoke.spec.ts
  - frontend/.gitignore
  - backend/.gitignore
autonomous: true
requirements: [INFRA-01, INFRA-05]
---

# Plan 27.1: Playwright Installation & Configuration

<objective>
Install Playwright and configure dual webServer (FastAPI :8001 + Next.js :3000) so `npx playwright test` auto-starts both servers and runs a basic smoke test.
</objective>

<tasks>

<task id="1" type="command">
<title>Install Playwright as devDependency</title>
<read_first>
- frontend/package.json
</read_first>
<action>
Run from `frontend/` directory:
```bash
npm install --save-dev @playwright/test
npx playwright install chromium
```
This adds `@playwright/test` to devDependencies and downloads the Chromium browser binary.
</action>
<verify>
`frontend/package.json` devDependencies contains `@playwright/test`
</verify>
<acceptance_criteria>
- `frontend/package.json` contains `"@playwright/test"` in devDependencies
- `npx playwright --version` outputs a version number (1.x)
</acceptance_criteria>
</task>

<task id="2" type="file">
<title>Create playwright.config.ts with dual webServer</title>
<read_first>
- frontend/package.json (scripts section for dev command)
- backend/app/main.py (app entry point for uvicorn)
</read_first>
<action>
Create `frontend/playwright.config.ts` with this content:

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html', { open: 'never' }]],

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
  ],

  webServer: [
    {
      command: '../backend/.venv/Scripts/python -m uvicorn app.main:app --port 8001',
      cwd: '../backend',
      url: 'http://localhost:8001/api/health',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        HOLO_TEST_MODE: 'true',
      },
    },
    {
      command: 'npm run dev -- --port 3000',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
```

Key decisions:
- FastAPI on port 8001 (not 8000) to avoid conflict with dev server
- `HOLO_TEST_MODE=true` passed to FastAPI via webServer env
- Chromium only (no WebKit on Windows)
- `reuseExistingServer: !process.env.CI` for fast local dev
- Health check on `/api/health` for FastAPI
- HTML reporter with `open: 'never'` (no auto-browser popup)
- `cwd: '../backend'` so uvicorn finds `app.main:app` correctly
</action>
<verify>
File `frontend/playwright.config.ts` exists and contains `webServer` array with 2 entries
</verify>
<acceptance_criteria>
- `frontend/playwright.config.ts` exists
- File contains `webServer: [` (array of servers)
- File contains `port 8001` (FastAPI test port)
- File contains `HOLO_TEST_MODE: 'true'`
- File contains `reuseExistingServer: !process.env.CI`
- File contains `testDir: './e2e'`
</acceptance_criteria>
</task>

<task id="3" type="file">
<title>Create initial smoke test</title>
<read_first>
- frontend/playwright.config.ts (verify testDir is ./e2e)
</read_first>
<action>
Create `frontend/e2e/smoke.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test('homepage loads successfully', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Holo/);
  await expect(page.locator('body')).toBeVisible();
});
```

This minimal test validates the entire infrastructure: both servers start, Next.js serves the page, and it loads.
</action>
<verify>
File `frontend/e2e/smoke.spec.ts` exists and contains `test(`
</verify>
<acceptance_criteria>
- `frontend/e2e/smoke.spec.ts` exists
- File contains `import { test, expect } from '@playwright/test'`
- File contains `page.goto('/')`
</acceptance_criteria>
</task>

<task id="4" type="file">
<title>Update .gitignore files for test artifacts</title>
<read_first>
- frontend/.gitignore
- backend/.gitignore
</read_first>
<action>
Append to `frontend/.gitignore`:

```
# playwright
/test-results/
/playwright-report/
/blob-report/
/playwright/.cache/
/e2e/**/*.png
```

No changes needed to `backend/.gitignore` — test artifacts are frontend-only.
</action>
<verify>
`frontend/.gitignore` contains `test-results` and `playwright-report`
</verify>
<acceptance_criteria>
- `frontend/.gitignore` contains `/test-results/`
- `frontend/.gitignore` contains `/playwright-report/`
- `frontend/.gitignore` contains `/playwright/.cache/`
</acceptance_criteria>
</task>

</tasks>

<verification>
1. `frontend/package.json` devDependencies includes `@playwright/test`
2. `frontend/playwright.config.ts` configures dual webServer array
3. `frontend/e2e/smoke.spec.ts` exists as initial test
4. `frontend/.gitignore` includes test artifact paths
</verification>

<success_criteria>
Addresses INFRA-01 (Playwright installed + dual webServer config) and INFRA-05 (.gitignore updated for test artifacts).
</success_criteria>

<must_haves>
- Playwright installed as devDependency with Chromium browser
- playwright.config.ts with dual webServer (FastAPI :8001 + Next.js :3000)
- HOLO_TEST_MODE env var passed to FastAPI webServer
- .gitignore updated for test-results/, playwright-report/
</must_haves>
