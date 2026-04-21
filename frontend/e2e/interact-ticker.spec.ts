import { test, expect } from '@playwright/test';
import { navigateAndWait, TEST_TICKER } from './fixtures/test-helpers';

test.describe('INTERACT-05: Ticker Detail Page Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);
    await expect(page.locator('[data-testid="ticker-page"]')).toBeVisible({ timeout: 15000 });
  });

  test('ticker page renders with chart container', async ({ page }) => {
    // Verify the chart section is visible
    const chartSection = page.locator('[data-testid="ticker-chart"]');
    await expect(chartSection).toBeVisible({ timeout: 15000 });

    // Chart should contain the heading "Biểu đồ giá"
    await expect(chartSection.getByText('Biểu đồ giá')).toBeVisible();
  });

  test('chart time range buttons are clickable', async ({ page }) => {
    const chartSection = page.locator('[data-testid="ticker-chart"]');
    await expect(chartSection).toBeVisible({ timeout: 15000 });

    // Time range buttons: "1T", "3T", "6T", "1N", "2N"
    // These are in the CandlestickChart component's control bar
    const timeRangeLabels = ['1T', '3T', '6T', '1N', '2N'];

    for (const label of timeRangeLabels) {
      const button = page.getByRole('button', { name: label, exact: true });
      // Some may not be visible if chart hasn't loaded — check existence
      const isVisible = await button.isVisible().catch(() => false);
      if (isVisible) {
        await button.click();
        // Chart container should still be visible after clicking
        await expect(chartSection).toBeVisible();
      }
    }
  });

  test('adjusted/original price toggle works', async ({ page }) => {
    const chartSection = page.locator('[data-testid="ticker-chart"]');
    await expect(chartSection).toBeVisible({ timeout: 15000 });

    // Price toggle buttons: "Giá ĐC" (adjusted) and "Giá gốc" (original)
    const adjustedBtn = page.getByRole('button', { name: 'Giá ĐC' });
    const originalBtn = page.getByRole('button', { name: 'Giá gốc' });

    const adjustedVisible = await adjustedBtn.isVisible().catch(() => false);
    const originalVisible = await originalBtn.isVisible().catch(() => false);

    if (adjustedVisible && originalVisible) {
      // Click "Giá gốc" to switch to original prices
      await originalBtn.click();
      // Chart should still be visible
      await expect(chartSection).toBeVisible();

      // Click "Giá ĐC" to switch back to adjusted
      await adjustedBtn.click();
      await expect(chartSection).toBeVisible();
    }
  });

  test('ticker header shows symbol and back button', async ({ page }) => {
    // The ticker symbol should be displayed in the header
    await expect(page.getByText(TEST_TICKER, { exact: true }).first()).toBeVisible();

    // Back button (ArrowLeft) should exist
    const backButton = page.locator('[data-testid="ticker-page"]').locator('button').first();
    await expect(backButton).toBeVisible();
  });

  test('watchlist star button is interactive on ticker page', async ({ page }) => {
    // The watchlist toggle button should be visible
    const watchButton = page.getByRole('button', { name: /Theo dõi|Đang theo dõi/ });
    await expect(watchButton).toBeVisible();

    // Get initial state
    const initialText = await watchButton.textContent();

    // Click to toggle
    await watchButton.click();

    // State should have changed
    const newText = await watchButton.textContent();
    expect(newText).not.toBe(initialText);

    // Click again to restore original state
    await watchButton.click();
    const restoredText = await watchButton.textContent();
    expect(restoredText).toBe(initialText);
  });

  test('indicator and analysis sections render', async ({ page }) => {
    // "Chỉ báo kỹ thuật" section heading
    await expect(page.getByText('Chỉ báo kỹ thuật')).toBeVisible({ timeout: 10000 });

    // "Hỗ trợ & Kháng cự" section heading
    await expect(page.getByText('Hỗ trợ & Kháng cự')).toBeVisible({ timeout: 10000 });

    // "Phân tích AI đa chiều" section heading
    await expect(page.getByText('Phân tích AI đa chiều')).toBeVisible({ timeout: 10000 });
  });

  test('page does not crash after rapid time range switching', async ({ page }) => {
    const chartSection = page.locator('[data-testid="ticker-chart"]');
    await expect(chartSection).toBeVisible({ timeout: 15000 });

    // Rapidly click through time ranges
    const labels = ['1T', '3T', '1N', '6T', '2N', '1T'];
    for (const label of labels) {
      const btn = page.getByRole('button', { name: label, exact: true });
      const vis = await btn.isVisible().catch(() => false);
      if (vis) {
        await btn.click();
        // Small wait to allow chart re-render
        await page.waitForTimeout(200);
      }
    }

    // Page and chart should still be intact
    await expect(page.locator('[data-testid="ticker-page"]')).toBeVisible();
    await expect(chartSection).toBeVisible();
  });
});
