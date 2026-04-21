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
