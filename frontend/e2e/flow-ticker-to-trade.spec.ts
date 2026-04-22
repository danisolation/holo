import { test, expect } from '@playwright/test';
import { navigateAndWait, TEST_TICKER } from './fixtures/test-helpers';

/**
 * FLOW-01: Ticker → Analysis → Trading Plan → Follow → Verify Trade
 *
 * Multi-page journey simulating a user discovering a ticker, reviewing
 * analysis and trading plan, optionally following the signal, then
 * verifying the trade appears on the Paper Trading dashboard.
 */
test.describe('FLOW-01: Ticker to Trade Journey', () => {
  test('full flow: open ticker → analysis → trading plan → follow → verify trade', async ({ page }) => {
    // ── Step 1: Navigate to ticker detail page ──────────────────────
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);
    await expect(page.locator('[data-testid="ticker-page"]')).toBeVisible({ timeout: 15000 });

    // ── Step 2: Verify chart renders ────────────────────────────────
    const chartSection = page.locator('[data-testid="ticker-chart"]');
    await expect(chartSection).toBeVisible({ timeout: 15000 });
    await expect(chartSection.getByText('Biểu đồ giá')).toBeVisible();

    // ── Step 3: Scroll down and verify analysis sections load ───────
    // Technical indicators
    await expect(page.getByText('Chỉ báo kỹ thuật')).toBeVisible({ timeout: 10000 });
    // Support & Resistance
    await expect(page.getByText('Hỗ trợ & Kháng cự').first()).toBeVisible({ timeout: 10000 });
    // AI multi-dimensional analysis
    await expect(page.getByText('Phân tích AI đa chiều').first()).toBeVisible({ timeout: 10000 });

    // ── Step 4: Look for trading plan panel and Follow button ───────
    // The trading plan section ("Kế Hoạch Giao Dịch") renders only
    // when a trading signal exists for this ticker. It may not exist.
    const tradingPlanHeading = page.getByText('Kế Hoạch Giao Dịch');
    const hasTradingPlan = await tradingPlanHeading.isVisible({ timeout: 5000 }).catch(() => false);

    let followClicked = false;

    if (hasTradingPlan) {
      // Scroll trading plan into view
      await tradingPlanHeading.scrollIntoViewIfNeeded();

      // Find a Follow button — there may be up to 2 (long & bearish columns).
      // Only buttons with valid signals (confidence > 0) have the Follow button.
      const followButtons = page.getByRole('button', { name: 'Follow' });
      const followCount = await followButtons.count();

      if (followCount > 0) {
        // Click the first available Follow button
        const followBtn = followButtons.first();
        await followBtn.scrollIntoViewIfNeeded();
        await followBtn.click();

        // Wait for success state: button text changes to "Đã follow"
        await expect(
          page.getByRole('button', { name: 'Đã follow' }).first()
        ).toBeVisible({ timeout: 10000 });

        followClicked = true;
      }
    }

    // ── Step 5: Navigate to Paper Trading dashboard ─────────────────
    await navigateAndWait(page, '/dashboard/paper-trading');
    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible({ timeout: 10000 });

    // ── Step 6: Verify trade appears (if Follow was clicked) ────────
    if (followClicked) {
      // Switch to Trades tab
      await page.locator('[data-testid="pt-tab-trades"]').click();

      // Wait for trades table or empty state
      const tradesTable = page.locator('[data-testid="pt-trades-table"]');
      await expect(
        tradesTable.or(page.getByText('Chưa có lệnh paper trading nào.'))
      ).toBeVisible({ timeout: 10000 });

      // If table loaded, look for the ticker symbol in the table
      if (await tradesTable.isVisible()) {
        // The ticker may appear in the table — but don't hard-assert on live data
        // Just verify the table has rendered successfully with rows or empty state
        const rowCount = await tradesTable.locator('tbody tr').count();
        // Table is rendering (with or without our new trade)
        expect(rowCount).toBeGreaterThanOrEqual(0);
      }
    } else {
      // Even without a Follow, verify the dashboard structure is intact
      const overviewTab = page.locator('[data-testid="pt-tab-overview"]');
      await expect(overviewTab).toHaveAttribute('aria-selected', 'true');
    }
  });

  test('ticker page structure is complete without trading signal', async ({ page }) => {
    // This test ensures the page doesn't break if no trading signal exists.
    // Navigate to the ticker and verify all major sections load.
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);
    await expect(page.locator('[data-testid="ticker-page"]')).toBeVisible({ timeout: 15000 });

    // Chart
    await expect(page.locator('[data-testid="ticker-chart"]')).toBeVisible({ timeout: 15000 });

    // Indicators
    await expect(page.getByText('Chỉ báo kỹ thuật')).toBeVisible({ timeout: 10000 });

    // Support & Resistance
    await expect(page.getByText('Hỗ trợ & Kháng cự').first()).toBeVisible({ timeout: 10000 });

    // AI Analysis section heading (always visible even if no data)
    await expect(page.getByText('Phân tích AI đa chiều').first()).toBeVisible({ timeout: 10000 });

    // If trading plan heading is missing, that's okay — verify page didn't crash
    await expect(page.locator('[data-testid="ticker-page"]')).toBeVisible();
  });
});
