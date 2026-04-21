import { test, expect } from '@playwright/test';
import { navigateAndWait, TEST_TICKER } from './fixtures/test-helpers';

/**
 * VIS-01 + VIS-03: Screenshot baselines for 5 key pages with dynamic data masking.
 *
 * Masks cover dynamic content that changes between runs:
 * - Price values (font-mono numeric spans with color classes)
 * - Percentage badges and change indicators
 * - Timestamps and dates
 * - Canvas-based charts (lightweight-charts renders differently each time)
 * - Skeleton loaders (transient loading states)
 */

/** Shared screenshot options: disable animations, set tolerance */
function screenshotOpts(page: import('@playwright/test').Page, name: string) {
  return {
    animations: 'disabled' as const,
    mask: [
      // Price/PnL values with gain/loss colors (VN stock market palette)
      page.locator('[class*="text-\\[#26a69a\\]"]'),
      page.locator('[class*="text-\\[#ef5350\\]"]'),
      page.locator('.text-emerald-500, .text-red-500'),
      // Percentage and numeric badges
      page.locator('.font-mono'),
      // Timestamps
      page.locator('time, [data-timestamp]'),
      // Canvas charts — rendered by lightweight-charts, pixel-unstable
      page.locator('canvas'),
      // Skeleton loaders — transient
      page.locator('[class*="skeleton"], [class*="Skeleton"]'),
      // Real-time price flash cells
      page.locator('[data-testid="price-flash"]'),
    ],
    maxDiffPixelRatio: 0.05,
    fullPage: true,
  };
}

test.describe('Visual regression — Page screenshots', () => {
  test('VIS-01: Homepage / Market Overview baseline', async ({ page }) => {
    await navigateAndWait(page, '/');
    // Wait for heatmap tiles to render (they contain dynamic prices)
    await page.waitForTimeout(1000);

    await expect(page).toHaveScreenshot('homepage.png', screenshotOpts(page, 'homepage'));
  });

  test('VIS-01: Ticker detail page baseline', async ({ page }) => {
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);
    // Extra wait for chart canvas to paint
    await page.waitForTimeout(2000);

    await expect(page).toHaveScreenshot(
      'ticker-detail.png',
      screenshotOpts(page, 'ticker-detail'),
    );
  });

  test('VIS-01: Paper Trading page baseline', async ({ page }) => {
    await navigateAndWait(page, '/dashboard/paper-trading');
    // Overview tab loads by default — wait for stat cards
    await page.waitForTimeout(1000);

    await expect(page).toHaveScreenshot(
      'paper-trading.png',
      screenshotOpts(page, 'paper-trading'),
    );
  });

  test('VIS-01: Portfolio page baseline', async ({ page }) => {
    await navigateAndWait(page, '/dashboard/portfolio');
    await page.waitForTimeout(1000);

    await expect(page).toHaveScreenshot(
      'portfolio.png',
      screenshotOpts(page, 'portfolio'),
    );
  });

  test('VIS-01: Watchlist page baseline', async ({ page }) => {
    await navigateAndWait(page, '/watchlist');
    await page.waitForTimeout(500);

    await expect(page).toHaveScreenshot(
      'watchlist.png',
      screenshotOpts(page, 'watchlist'),
    );
  });
});
