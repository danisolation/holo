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
