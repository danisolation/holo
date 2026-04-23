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
  { path: '/dashboard/health', name: 'System Health' },
  { path: '/dashboard/corporate-events', name: 'Corporate Events' },
] as const;

/** A known ticker symbol that should have data (use for ticker detail tests) */
export const TEST_TICKER = 'VNM';
