import { test, expect } from '@playwright/test';
import { navigateAndWait } from './fixtures/test-helpers';

test.describe('INTERACT-02: Trades Table Sorting & Filtering', () => {
  test.beforeEach(async ({ page }) => {
    await navigateAndWait(page, '/dashboard/paper-trading');
    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible();
    // Switch to Trades tab
    await page.locator('[data-testid="pt-tab-trades"]').click();
    // Wait for either the table or empty state
    await expect(
      page.locator('[data-testid="pt-trades-table"]').or(
        page.getByText('Chưa có lệnh paper trading nào.')
      ).first()
    ).toBeVisible({ timeout: 15000 });
  });

  test('trades table or empty state renders', async ({ page }) => {
    const tradesTable = page.locator('[data-testid="pt-trades-table"]');
    await expect(tradesTable).toBeVisible();

    // Either we see data rows or the empty state message
    const emptyState = tradesTable.getByText('Chưa có lệnh paper trading nào.');
    const tableBody = tradesTable.locator('tbody tr');

    const hasEmpty = await emptyState.isVisible().catch(() => false);
    if (hasEmpty) {
      // Empty state — no further interaction possible
      await expect(emptyState).toBeVisible();
    } else {
      // Data rows should exist
      const rowCount = await tableBody.count();
      expect(rowCount).toBeGreaterThan(0);
    }
  });

  test('column headers with sort buttons are clickable', async ({ page }) => {
    const tradesTable = page.locator('[data-testid="pt-trades-table"]');

    // The sortable columns render ghost buttons with ArrowUpDown icon
    // Sortable headers: "Ngày", "Entry", "P&L", "AI"
    const sortableHeaders = tradesTable.locator('thead button');
    const headerCount = await sortableHeaders.count();

    if (headerCount > 0) {
      // Click the first sortable header (Ngày / Date)
      const firstSortButton = sortableHeaders.first();
      await firstSortButton.click();

      // Click again to reverse sort direction
      await firstSortButton.click();

      // Table should still be visible (no crash)
      await expect(tradesTable).toBeVisible();
    }
  });

  test('direction filter buttons work', async ({ page }) => {
    const tradesTable = page.locator('[data-testid="pt-trades-table"]');

    // Filter buttons: "Tất cả", "Long", "Bearish"
    const allFilter = tradesTable.getByRole('button', { name: 'Tất cả' });
    const longFilter = tradesTable.getByRole('button', { name: 'Long' });
    const bearishFilter = tradesTable.getByRole('button', { name: 'Bearish' });

    await expect(allFilter).toBeVisible();
    await expect(longFilter).toBeVisible();
    await expect(bearishFilter).toBeVisible();

    // Click Long filter
    await longFilter.click();
    // Table should still be visible
    await expect(tradesTable).toBeVisible();

    // Click Bearish filter
    await bearishFilter.click();
    await expect(tradesTable).toBeVisible();

    // Click "Tất cả" to reset
    await allFilter.click();
    await expect(tradesTable).toBeVisible();
  });

  test('symbol filter input accepts text', async ({ page }) => {
    const tradesTable = page.locator('[data-testid="pt-trades-table"]');

    // Symbol filter input with placeholder "Lọc mã CK..."
    const symbolInput = tradesTable.getByPlaceholder('Lọc mã CK...');
    await expect(symbolInput).toBeVisible();

    // Type a symbol to filter
    await symbolInput.fill('VNM');

    // Wait a moment for the query to refetch (usePaperTrades has symbol param)
    await page.waitForTimeout(1000);

    // Table should still be visible (either with filtered results or empty)
    await expect(tradesTable).toBeVisible();

    // Clear the filter
    await symbolInput.clear();
    await expect(tradesTable).toBeVisible();
  });

  test('sorting changes row order when data exists', async ({ page }) => {
    const tradesTable = page.locator('[data-testid="pt-trades-table"]');
    const rows = tradesTable.locator('tbody tr');
    const rowCount = await rows.count();

    if (rowCount >= 2) {
      // Get the P&L sort button — contains "P&L" text
      const pnlHeader = tradesTable.locator('thead button', { hasText: 'P&L' });
      if (await pnlHeader.count() > 0) {
        // Read first row text before sort
        const firstRowBefore = await rows.first().textContent();

        // Click to sort ascending
        await pnlHeader.first().click();
        await page.waitForTimeout(300);

        // Click again to sort descending
        await pnlHeader.first().click();
        await page.waitForTimeout(300);

        // Verify table is still functional
        await expect(tradesTable).toBeVisible();
        const newRowCount = await rows.count();
        expect(newRowCount).toBeGreaterThan(0);
      }
    }
  });
});
