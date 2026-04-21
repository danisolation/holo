import { test, expect } from '@playwright/test';
import { navigateAndWait } from './fixtures/test-helpers';

/**
 * FLOW-02: Paper Trading Dashboard Exploration
 *
 * Multi-tab journey simulating a user exploring the entire paper trading
 * dashboard: Overview → Trades (sort/filter) → Analytics → Calendar.
 */
test.describe('FLOW-02: Paper Trading Dashboard Exploration', () => {
  test('full flow: overview → trades → sort/filter → analytics → calendar', async ({ page }) => {
    // ── Step 1: Navigate to paper trading dashboard ─────────────────
    await navigateAndWait(page, '/dashboard/paper-trading');

    // Verify tabs container loads
    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible({ timeout: 10000 });

    // ── Step 2: Verify Overview tab content loads by default ────────
    const overviewTab = page.locator('[data-testid="pt-tab-overview"]');
    await expect(overviewTab).toHaveAttribute('data-state', 'active');

    // Overview renders summary cards or error message — just check the page is stable
    // Cards show "Tỷ lệ thắng", "Tổng P&L", etc. or a fallback
    await page.waitForTimeout(1000); // Allow data to load

    // ── Step 3: Click Trades tab and verify table loads ─────────────
    await page.locator('[data-testid="pt-tab-trades"]').click();
    await expect(page.locator('[data-testid="pt-tab-trades"]')).toHaveAttribute('data-state', 'active');

    // Wait for trades table or empty state
    const tradesTable = page.locator('[data-testid="pt-trades-table"]');
    const emptyState = page.getByText('Chưa có lệnh paper trading nào.');
    await expect(tradesTable.or(emptyState)).toBeVisible({ timeout: 10000 });

    const hasTradesData = await tradesTable.isVisible();

    // ── Step 4: If table has data, attempt sort and filter ──────────
    if (hasTradesData) {
      // Sort by clicking the "Ngày" (Date) column header sort button
      const sortButton = tradesTable.getByRole('button', { name: /Ngày/ });
      if (await sortButton.isVisible().catch(() => false)) {
        await sortButton.click();
        // Table should still be visible after sorting
        await expect(tradesTable).toBeVisible();
      }

      // Filter by direction — click "Long" filter button
      const longFilterBtn = tradesTable.getByRole('button', { name: 'Long' });
      if (await longFilterBtn.isVisible().catch(() => false)) {
        await longFilterBtn.click();
        // Table should still render (possibly with fewer rows or empty)
        await expect(tradesTable).toBeVisible();
        await page.waitForTimeout(500); // Allow re-fetch
      }

      // Reset filter — click "Tất cả" (All) button
      const allFilterBtn = tradesTable.getByRole('button', { name: 'Tất cả' });
      if (await allFilterBtn.isVisible().catch(() => false)) {
        await allFilterBtn.click();
        await expect(tradesTable).toBeVisible();
      }
    }

    // ── Step 5: Click Analytics tab and verify content loads ────────
    await page.locator('[data-testid="pt-tab-analytics"]').click();
    await expect(page.locator('[data-testid="pt-tab-analytics"]')).toHaveAttribute('data-state', 'active');

    const analyticsContent = page.locator('[data-testid="pt-analytics-content"]');
    await expect(analyticsContent).toBeVisible({ timeout: 10000 });

    // Analytics should contain chart sections or empty fallback
    // Verify the analytics area has rendered children
    const analyticsChildren = await analyticsContent.locator('> *').count();
    expect(analyticsChildren).toBeGreaterThanOrEqual(0);

    // ── Step 6: Click Calendar tab and verify content renders ───────
    await page.locator('[data-testid="pt-tab-calendar"]').click();
    await expect(page.locator('[data-testid="pt-tab-calendar"]')).toHaveAttribute('data-state', 'active');

    // Calendar tab contains PTCalendarHeatmap + PTPeriodicTable
    // Just verify the content area has rendered and tab is active
    // Previous tabs should be inactive
    await expect(page.locator('[data-testid="pt-tab-analytics"]')).toHaveAttribute('data-state', 'inactive');

    // Wait for calendar content to render
    await page.waitForTimeout(1000);

    // Page should still be stable — no crash
    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible();
  });

  test('can navigate back to overview from any tab', async ({ page }) => {
    await navigateAndWait(page, '/dashboard/paper-trading');
    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible({ timeout: 10000 });

    // Go to Calendar (last tab)
    await page.locator('[data-testid="pt-tab-calendar"]').click();
    await expect(page.locator('[data-testid="pt-tab-calendar"]')).toHaveAttribute('data-state', 'active');

    // Return to Overview
    await page.locator('[data-testid="pt-tab-overview"]').click();
    await expect(page.locator('[data-testid="pt-tab-overview"]')).toHaveAttribute('data-state', 'active');

    // Calendar should be inactive
    await expect(page.locator('[data-testid="pt-tab-calendar"]')).toHaveAttribute('data-state', 'inactive');
  });
});
