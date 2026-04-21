import { test, expect } from '@playwright/test';
import { navigateAndWait, TEST_TICKER } from './fixtures/test-helpers';

/**
 * FLOW-03: Watchlist Management Journey
 *
 * Multi-page flow: Add ticker to watchlist (via ticker page star button)
 * → verify on /watchlist page → reload to verify persistence
 * → remove ticker → verify removal.
 *
 * Watchlist uses zustand persist with localStorage key "holo-watchlist".
 */
test.describe('FLOW-03: Watchlist Add → Persist → Remove → Verify', () => {
  test.beforeEach(async ({ page }) => {
    // Clean slate: remove the test ticker from watchlist via localStorage
    // to ensure a predictable starting state.
    await page.goto('/watchlist');
    await page.evaluate((ticker) => {
      const raw = localStorage.getItem('holo-watchlist');
      if (raw) {
        const store = JSON.parse(raw);
        store.state.watchlist = store.state.watchlist.filter(
          (s: string) => s !== ticker
        );
        localStorage.setItem('holo-watchlist', JSON.stringify(store));
      }
    }, TEST_TICKER);
  });

  test('full flow: add → verify on watchlist → persist → remove → verify removal', async ({ page }) => {
    // ── Step 1: Navigate to ticker detail page ──────────────────────
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);
    await expect(page.locator('[data-testid="ticker-page"]')).toBeVisible({ timeout: 15000 });

    // ── Step 2: Find the watchlist toggle and ensure ticker is NOT in watchlist ──
    const watchButton = page.getByRole('button', { name: /Theo dõi|Đang theo dõi/ });
    await expect(watchButton).toBeVisible();

    // If already in watchlist ("Đang theo dõi"), remove first
    const initialText = await watchButton.textContent();
    if (initialText?.includes('Đang theo dõi')) {
      await watchButton.click();
      await expect(page.getByRole('button', { name: /^Theo dõi/ })).toBeVisible();
    }

    // ── Step 3: Add ticker to watchlist ─────────────────────────────
    const addButton = page.getByRole('button', { name: /^Theo dõi/ });
    await addButton.click();

    // Button should now show "Đang theo dõi" (currently watching)
    await expect(page.getByRole('button', { name: 'Đang theo dõi' })).toBeVisible({ timeout: 5000 });

    // ── Step 4: Navigate to watchlist page and verify ticker appears ─
    await navigateAndWait(page, '/watchlist');
    await expect(page.locator('[data-testid="watchlist-page"]')).toBeVisible();

    const watchlistTable = page.locator('[data-testid="watchlist-table"]');
    await expect(watchlistTable).toBeVisible();
    await expect(watchlistTable.getByText(TEST_TICKER)).toBeVisible({ timeout: 10000 });

    // ── Step 5: Reload page to verify persistence ───────────────────
    await page.reload();
    await page.waitForLoadState('networkidle');

    await expect(page.locator('[data-testid="watchlist-page"]')).toBeVisible();
    await expect(watchlistTable.getByText(TEST_TICKER)).toBeVisible({ timeout: 10000 });

    // ── Step 6: Remove the ticker ───────────────────────────────────
    // Navigate back to the ticker detail page to use the star button
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);
    await expect(page.locator('[data-testid="ticker-page"]')).toBeVisible({ timeout: 15000 });

    // Should show "Đang theo dõi" since we just added it
    const removeButton = page.getByRole('button', { name: 'Đang theo dõi' });
    await expect(removeButton).toBeVisible({ timeout: 5000 });
    await removeButton.click();

    // Should revert to "Theo dõi"
    await expect(page.getByRole('button', { name: /^Theo dõi/ })).toBeVisible();

    // ── Step 7: Navigate back to watchlist and verify removal ───────
    await navigateAndWait(page, '/watchlist');
    await expect(page.locator('[data-testid="watchlist-page"]')).toBeVisible();

    // The ticker should no longer appear, or the table shows empty state
    const tickerInTable = watchlistTable.getByText(TEST_TICKER, { exact: true });
    const emptyState = page.getByText('Chưa có mã nào trong danh mục.');

    // Either the ticker is gone or the entire list is empty
    const tickerVisible = await tickerInTable.isVisible().catch(() => false);
    const emptyVisible = await emptyState.isVisible().catch(() => false);

    // At least one must be true: ticker is gone (not visible) or empty state shows
    expect(tickerVisible === false || emptyVisible === true).toBeTruthy();
  });

  test('watchlist add persists across full page navigation cycle', async ({ page }) => {
    // Add via localStorage injection for deterministic setup
    await page.goto('/watchlist');
    await page.evaluate((ticker) => {
      const existing = JSON.parse(
        localStorage.getItem('holo-watchlist') ||
        '{"state":{"watchlist":[]},"version":0}'
      );
      if (!existing.state.watchlist.includes(ticker)) {
        existing.state.watchlist.push(ticker);
        localStorage.setItem('holo-watchlist', JSON.stringify(existing));
      }
    }, TEST_TICKER);

    // Navigate away to homepage
    await navigateAndWait(page, '/');

    // Navigate back to watchlist
    await navigateAndWait(page, '/watchlist');
    await expect(page.locator('[data-testid="watchlist-page"]')).toBeVisible();

    const watchlistTable = page.locator('[data-testid="watchlist-table"]');
    await expect(watchlistTable).toBeVisible();

    // Ticker should still be in the list after navigation cycle
    await expect(watchlistTable.getByText(TEST_TICKER)).toBeVisible({ timeout: 10000 });
  });
});
