import { test, expect } from '@playwright/test';
import { navigateAndWait } from './fixtures/test-helpers';

test.describe('INTERACT-04: Paper Trading Tab Switching', () => {
  test.beforeEach(async ({ page }) => {
    await navigateAndWait(page, '/dashboard/paper-trading');
    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible();
  });

  test('all 5 tab triggers are visible', async ({ page }) => {
    await expect(page.locator('[data-testid="pt-tab-overview"]')).toBeVisible();
    await expect(page.locator('[data-testid="pt-tab-trades"]')).toBeVisible();
    await expect(page.locator('[data-testid="pt-tab-analytics"]')).toBeVisible();
    await expect(page.locator('[data-testid="pt-tab-calendar"]')).toBeVisible();
    await expect(page.locator('[data-testid="pt-tab-settings"]')).toBeVisible();
  });

  test('Overview tab is active by default', async ({ page }) => {
    // Overview tab should have the active/selected state by default
    const overviewTab = page.locator('[data-testid="pt-tab-overview"]');
    await expect(overviewTab).toHaveAttribute('data-state', 'active');
  });

  test('clicking each tab shows corresponding content', async ({ page }) => {
    // --- Trades tab ---
    await page.locator('[data-testid="pt-tab-trades"]').click();
    // Trades tab renders PTTradesTable (has data-testid="pt-trades-table") or loading skeleton
    const tradesTable = page.locator('[data-testid="pt-trades-table"]');
    // Wait for either the table or an empty-state message
    await expect(
      tradesTable.or(page.getByText('Chưa có lệnh paper trading nào.'))
    ).toBeVisible({ timeout: 10000 });
    // Verify trades tab is active
    await expect(page.locator('[data-testid="pt-tab-trades"]')).toHaveAttribute('data-state', 'active');

    // --- Analytics tab ---
    await page.locator('[data-testid="pt-tab-analytics"]').click();
    const analyticsContent = page.locator('[data-testid="pt-analytics-content"]');
    await expect(analyticsContent).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="pt-tab-analytics"]')).toHaveAttribute('data-state', 'active');
    // Trades tab should no longer be active
    await expect(page.locator('[data-testid="pt-tab-trades"]')).toHaveAttribute('data-state', 'inactive');

    // --- Calendar tab ---
    await page.locator('[data-testid="pt-tab-calendar"]').click();
    // Calendar tab renders PTCalendarTab — wait for its content area
    await expect(page.locator('[data-testid="pt-tab-calendar"]')).toHaveAttribute('data-state', 'active');
    await expect(page.locator('[data-testid="pt-tab-analytics"]')).toHaveAttribute('data-state', 'inactive');

    // --- Settings tab ---
    await page.locator('[data-testid="pt-tab-settings"]').click();
    const settingsForm = page.locator('[data-testid="pt-settings-form"]');
    await expect(settingsForm).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="pt-tab-settings"]')).toHaveAttribute('data-state', 'active');

    // --- Back to Overview tab ---
    await page.locator('[data-testid="pt-tab-overview"]').click();
    await expect(page.locator('[data-testid="pt-tab-overview"]')).toHaveAttribute('data-state', 'active');
    await expect(page.locator('[data-testid="pt-tab-settings"]')).toHaveAttribute('data-state', 'inactive');
  });

  test('tab switching hides previous content', async ({ page }) => {
    // Switch to Settings → form visible
    await page.locator('[data-testid="pt-tab-settings"]').click();
    await expect(page.locator('[data-testid="pt-settings-form"]')).toBeVisible({ timeout: 10000 });

    // Switch to Trades → settings form should be hidden
    await page.locator('[data-testid="pt-tab-trades"]').click();
    await expect(page.locator('[data-testid="pt-settings-form"]')).not.toBeVisible();

    // Trades content should be visible (table or empty state)
    await expect(
      page.locator('[data-testid="pt-trades-table"]').or(
        page.getByText('Chưa có lệnh paper trading nào.')
      )
    ).toBeVisible({ timeout: 10000 });
  });
});
