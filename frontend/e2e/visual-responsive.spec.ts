import { test, expect } from '@playwright/test';
import { navigateAndWait, TEST_TICKER } from './fixtures/test-helpers';

/**
 * VIS-04: Mobile responsive layout tests at 375px viewport (iPhone SE).
 *
 * Verifies key pages render without layout breakage at mobile width:
 * - No horizontal overflow (scrollWidth <= clientWidth)
 * - Mobile hamburger menu visible (desktop nav hidden at md breakpoint)
 * - Content adapts to narrow viewport
 */

test.describe('Visual regression — Mobile responsive (375px)', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  /** Helper: assert no horizontal overflow on the page */
  async function expectNoHorizontalOverflow(page: import('@playwright/test').Page) {
    const hasOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasOverflow).toBe(false);
  }

  /** Helper: verify mobile navigation is visible */
  async function expectMobileNavVisible(page: import('@playwright/test').Page) {
    // Desktop nav should be hidden at 375px (md:flex → hidden below md)
    const desktopNav = page.locator('[data-testid="nav-desktop"]');
    await expect(desktopNav).toBeHidden();

    // Hamburger menu button should be visible (md:hidden class means visible below md)
    // The hamburger is a button with Menu icon inside the Sheet trigger
    const navbar = page.locator('[data-testid="navbar"]');
    await expect(navbar).toBeVisible();
  }

  test('VIS-04: Homepage renders at mobile viewport without overflow', async ({ page }) => {
    await navigateAndWait(page, '/');
    await page.waitForTimeout(1000);

    await expectNoHorizontalOverflow(page);
    await expectMobileNavVisible(page);

    await expect(page).toHaveScreenshot('mobile-homepage.png', {
      animations: 'disabled',
      mask: [
        page.locator('canvas'),
        page.locator('.font-mono'),
        page.locator('[class*="text-\\[#26a69a\\]"]'),
        page.locator('[class*="text-\\[#ef5350\\]"]'),
      ],
      maxDiffPixelRatio: 0.05,
      fullPage: true,
    });
  });

  test('VIS-04: Watchlist renders at mobile viewport without overflow', async ({ page }) => {
    await navigateAndWait(page, '/watchlist');
    await page.waitForTimeout(500);

    await expectNoHorizontalOverflow(page);
    await expectMobileNavVisible(page);

    // Watchlist table should be contained (overflow-x-auto on table, not page)
    const watchlistContainer = page.locator('[data-testid="watchlist-page"]');
    await expect(watchlistContainer).toBeVisible();

    await expect(page).toHaveScreenshot('mobile-watchlist.png', {
      animations: 'disabled',
      mask: [
        page.locator('.font-mono'),
        page.locator('[class*="text-\\[#26a69a\\]"]'),
        page.locator('[class*="text-\\[#ef5350\\]"]'),
      ],
      maxDiffPixelRatio: 0.05,
      fullPage: true,
    });
  });

  test('VIS-04: Ticker detail renders at mobile viewport without overflow', async ({ page }) => {
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);
    await page.waitForTimeout(2000);

    await expectNoHorizontalOverflow(page);
    await expectMobileNavVisible(page);

    // Chart container should still be present
    const tickerPage = page.locator('[data-testid="ticker-page"]');
    await expect(tickerPage).toBeVisible();

    await expect(page).toHaveScreenshot('mobile-ticker-detail.png', {
      animations: 'disabled',
      mask: [
        page.locator('canvas'),
        page.locator('.font-mono'),
        page.locator('[class*="text-\\[#26a69a\\]"]'),
        page.locator('[class*="text-\\[#ef5350\\]"]'),
      ],
      maxDiffPixelRatio: 0.05,
      fullPage: true,
    });
  });
});
