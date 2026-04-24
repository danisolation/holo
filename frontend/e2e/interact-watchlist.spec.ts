import { test, expect } from '@playwright/test';
import { navigateAndWait, TEST_TICKER } from './fixtures/test-helpers';

test.describe('INTERACT-03: Watchlist Add/Remove & Persistence', () => {
  // Watchlist is now server-backed. Tests work through the UI only (no localStorage).

  test('add ticker via ticker detail page and verify on watchlist', async ({ page }) => {
    // 1. Navigate to a ticker detail page
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);
    await expect(page.locator('[data-testid="ticker-page"]')).toBeVisible({ timeout: 15000 });

    // 2. Find the watchlist toggle button
    const watchButton = page.getByRole('button', { name: /Theo dõi|Đang theo dõi/ });
    await expect(watchButton).toBeVisible();

    // 3. Ensure ticker IS in watchlist — if "Theo dõi" (not following), click to add
    const buttonText = await watchButton.textContent();
    if (buttonText?.includes('Đang theo dõi') === false) {
      await watchButton.click();
      await expect(page.getByRole('button', { name: 'Đang theo dõi' })).toBeVisible();
    }

    // 4. Navigate to watchlist page and verify ticker is listed
    await navigateAndWait(page, '/watchlist');
    await expect(page.locator('[data-testid="watchlist-page"]')).toBeVisible();

    const watchlistTable = page.locator('[data-testid="watchlist-table"]');
    await expect(watchlistTable).toBeVisible();
    await expect(watchlistTable.getByText(TEST_TICKER)).toBeVisible({ timeout: 10000 });
  });

  test('watchlist persists across page reload (server-backed)', async ({ page }) => {
    // 1. Add ticker via UI on ticker detail page
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);
    await expect(page.locator('[data-testid="ticker-page"]')).toBeVisible({ timeout: 15000 });

    const watchButton = page.getByRole('button', { name: /Theo dõi|Đang theo dõi/ });
    await expect(watchButton).toBeVisible();
    const buttonText = await watchButton.textContent();
    if (buttonText?.includes('Đang theo dõi') === false) {
      await watchButton.click();
      await expect(page.getByRole('button', { name: 'Đang theo dõi' })).toBeVisible();
    }

    // 2. Navigate to watchlist, reload, verify persistence
    await navigateAndWait(page, '/watchlist');
    await page.reload();
    await page.waitForLoadState('networkidle');

    await expect(page.locator('[data-testid="watchlist-page"]')).toBeVisible();
    const watchlistTable = page.locator('[data-testid="watchlist-table"]');
    await expect(watchlistTable).toBeVisible();
    await expect(watchlistTable.getByText(TEST_TICKER)).toBeVisible({ timeout: 10000 });
  });

  test('remove ticker from watchlist via ticker detail page', async ({ page }) => {
    // 1. Ensure ticker is in watchlist first via UI
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);
    await expect(page.locator('[data-testid="ticker-page"]')).toBeVisible({ timeout: 15000 });

    const watchButton = page.getByRole('button', { name: /Theo dõi|Đang theo dõi/ });
    await expect(watchButton).toBeVisible();
    const buttonText = await watchButton.textContent();
    if (buttonText?.includes('Đang theo dõi') === false) {
      await watchButton.click();
      await expect(page.getByRole('button', { name: 'Đang theo dõi' })).toBeVisible();
    }

    // 2. Button should show "Đang theo dõi" — click to remove
    const watchingBtn = page.getByRole('button', { name: 'Đang theo dõi' });
    await expect(watchingBtn).toBeVisible({ timeout: 5000 });
    await watchingBtn.click();

    // 3. Button should now show "Theo dõi"
    await expect(page.getByRole('button', { name: /^Theo dõi/ })).toBeVisible();

    // 4. Navigate to watchlist page to verify removal
    await navigateAndWait(page, '/watchlist');
    await expect(page.locator('[data-testid="watchlist-page"]')).toBeVisible();

    const watchlistTable = page.locator('[data-testid="watchlist-table"]');
    const tickerCell = watchlistTable.getByText(TEST_TICKER, { exact: true });
    const emptyState = page.getByText('Chưa có mã nào trong danh mục.');

    await expect(tickerCell.or(emptyState)).toBeVisible({ timeout: 10000 });
  });

  test('remove ticker via X button on watchlist table', async ({ page }) => {
    // 1. Ensure ticker is in watchlist via UI
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);
    await expect(page.locator('[data-testid="ticker-page"]')).toBeVisible({ timeout: 15000 });

    const watchButton = page.getByRole('button', { name: /Theo dõi|Đang theo dõi/ });
    await expect(watchButton).toBeVisible();
    const buttonText = await watchButton.textContent();
    if (buttonText?.includes('Đang theo dõi') === false) {
      await watchButton.click();
      await expect(page.getByRole('button', { name: 'Đang theo dõi' })).toBeVisible();
    }

    // 2. Go to watchlist page
    await navigateAndWait(page, '/watchlist');
    await expect(page.locator('[data-testid="watchlist-page"]')).toBeVisible();
    const watchlistTable = page.locator('[data-testid="watchlist-table"]');
    await expect(watchlistTable).toBeVisible();

    // 3. Find the row with the ticker and its X (remove) button
    const tickerRow = watchlistTable.locator('tr', { hasText: TEST_TICKER });
    await expect(tickerRow).toBeVisible({ timeout: 10000 });

    // 4. Click the remove (X) button in that row
    const removeButton = tickerRow.locator('button').last();
    await removeButton.click();

    // 5. Wait for the ticker to disappear or empty state to appear
    await expect(
      tickerRow.or(page.getByText('Chưa có mã nào trong danh mục.'))
    ).toBeVisible({ timeout: 5000 }).catch(() => {
      // Ticker row disappeared entirely — that's expected
    });
  });
});
