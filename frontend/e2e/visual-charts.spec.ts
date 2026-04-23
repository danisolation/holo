import { test, expect } from '@playwright/test';
import { navigateAndWait, TEST_TICKER } from './fixtures/test-helpers';

/**
 * VIS-02: Chart rendering verification.
 *
 * Candlestick chart (lightweight-charts) renders to `<canvas>` inside
 * `[data-testid="ticker-chart"]`. We verify the element exists and has
 * non-zero dimensions — pixel-perfect screenshot comparison is unreliable
 * for canvas-based charts.
 *
 * Recharts (SVG-based) in Paper Trading analytics tab renders `<svg>`
 * elements inside `[data-testid="pt-analytics-content"]`.
 */

test.describe('Visual regression — Chart rendering', () => {
  test('VIS-02: Candlestick chart canvas exists with non-zero dimensions', async ({ page }) => {
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);

    // Wait for chart container to be visible
    const chartContainer = page.locator('[data-testid="ticker-chart"]');
    await expect(chartContainer).toBeVisible();

    // Allow time for lightweight-charts to paint the canvas
    await page.waitForTimeout(2000);

    // Verify <canvas> element exists inside chart container
    const canvas = chartContainer.locator('canvas').first();
    await expect(canvas).toBeVisible();

    // Verify canvas has non-zero width
    const width = await canvas.getAttribute('width');
    expect(width).toBeTruthy();
    expect(Number(width)).toBeGreaterThan(0);

    // Verify canvas has non-zero height
    const height = await canvas.getAttribute('height');
    expect(height).toBeTruthy();
    expect(Number(height)).toBeGreaterThan(0);
  });

  test('VIS-02: Candlestick chart container screenshot baseline', async ({ page }) => {
    await navigateAndWait(page, `/ticker/${TEST_TICKER}`);
    await page.waitForTimeout(2000);

    const chartContainer = page.locator('[data-testid="ticker-chart"]');
    await expect(chartContainer).toBeVisible();

    // Element-level screenshot of just the chart section
    await expect(chartContainer).toHaveScreenshot('ticker-chart-container.png', {
      animations: 'disabled',
      // Mask the canvas itself — pixel content is unstable
      mask: [chartContainer.locator('canvas')],
      maxDiffPixelRatio: 0.05,
    });
  });
});