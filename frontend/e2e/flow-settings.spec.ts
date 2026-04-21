import { test, expect } from '@playwright/test';
import { navigateAndWait } from './fixtures/test-helpers';

/**
 * FLOW-04: Settings Persistence & Effect on Overview
 *
 * Multi-tab journey: Navigate to settings → modify capital → save
 * → reload → verify persistence → switch to overview → verify
 * the overview reflects updated state.
 */
test.describe('FLOW-04: Settings Change → Persist → Verify Effect', () => {
  test('full flow: change setting → save → reload → verify persistence → check overview', async ({ page }) => {
    // ── Step 1: Navigate to Paper Trading dashboard ─────────────────
    await navigateAndWait(page, '/dashboard/paper-trading');
    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible({ timeout: 10000 });

    // ── Step 2: Click Settings tab ──────────────────────────────────
    await page.locator('[data-testid="pt-tab-settings"]').click();
    await expect(page.locator('[data-testid="pt-tab-settings"]')).toHaveAttribute('data-state', 'active');

    const settingsForm = page.locator('[data-testid="pt-settings-form"]');
    await expect(settingsForm).toBeVisible({ timeout: 10000 });

    // ── Step 3: Read current capital value ──────────────────────────
    // The capital input is the first number input ("Vốn ban đầu (VND)")
    const capitalInput = settingsForm.locator('input[type="number"]').first();
    await expect(capitalInput).toBeVisible();
    const originalValue = await capitalInput.inputValue();

    // ── Step 4: Modify the capital value ────────────────────────────
    // Change by adding 1,000,000 to the current value (or set to 200M if empty)
    const numericOriginal = Number(originalValue) || 100000000;
    const newCapital = String(numericOriginal + 1000000);

    await capitalInput.clear();
    await capitalInput.fill(newCapital);

    // ── Step 5: Submit the form ─────────────────────────────────────
    const submitButton = page.locator('[data-testid="pt-settings-submit"]');
    await expect(submitButton).toBeVisible();
    await submitButton.click();

    // Wait for save to complete — button re-enables and shows "Lưu cài đặt"
    await expect(submitButton).not.toBeDisabled({ timeout: 10000 });
    await expect(submitButton).toContainText('Lưu cài đặt', { timeout: 5000 });

    // ── Step 6: Reload page and verify persistence ──────────────────
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Navigate back to settings tab
    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible({ timeout: 10000 });
    await page.locator('[data-testid="pt-tab-settings"]').click();
    await expect(settingsForm).toBeVisible({ timeout: 10000 });

    // Verify the capital input shows the new value
    const persistedValue = await capitalInput.inputValue();
    expect(persistedValue).toBe(newCapital);

    // ── Step 7: Switch to Overview tab and verify effect ────────────
    await page.locator('[data-testid="pt-tab-overview"]').click();
    await expect(page.locator('[data-testid="pt-tab-overview"]')).toHaveAttribute('data-state', 'active');

    // Overview loads summary data from the analytics API.
    // The settings change affects the simulation — verify the overview
    // renders without error (data cards or fallback message).
    // We don't assert specific values since this is live data.
    await page.waitForTimeout(1000);

    // Verify the overview area has rendered (cards or error fallback)
    const overviewArea = page.locator('[data-testid="pt-tab-overview"]').locator('..');
    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible();

    // The page should not show a crash or blank state
    // Check for either stat cards or the "Không thể tải dữ liệu" fallback
    const hasCards = await page.locator('.grid .rounded-xl, .grid [class*="Card"]').first().isVisible().catch(() => false);
    const hasFallback = await page.getByText('Không thể tải dữ liệu phân tích').isVisible().catch(() => false);
    expect(hasCards || hasFallback).toBeTruthy();

    // ── Step 8: Restore original value (cleanup) ────────────────────
    await page.locator('[data-testid="pt-tab-settings"]').click();
    await expect(settingsForm).toBeVisible({ timeout: 10000 });

    await capitalInput.clear();
    await capitalInput.fill(originalValue || String(numericOriginal));
    await submitButton.click();
    await expect(submitButton).not.toBeDisabled({ timeout: 10000 });
  });

  test('confidence threshold change persists', async ({ page }) => {
    // ── Step 1: Navigate to settings ────────────────────────────────
    await navigateAndWait(page, '/dashboard/paper-trading');
    await page.locator('[data-testid="pt-tab-settings"]').click();

    const settingsForm = page.locator('[data-testid="pt-settings-form"]');
    await expect(settingsForm).toBeVisible({ timeout: 10000 });

    // ── Step 2: Read and modify confidence threshold ────────────────
    // Confidence input is the second number input (min=1, max=10)
    const confidenceInput = settingsForm.locator('input[type="number"]').nth(1);
    await expect(confidenceInput).toBeVisible();
    const originalConfidence = await confidenceInput.inputValue();

    // Set to a different value
    const newConfidence = originalConfidence === '7' ? '6' : '7';
    await confidenceInput.clear();
    await confidenceInput.fill(newConfidence);

    // ── Step 3: Submit ──────────────────────────────────────────────
    const submitButton = page.locator('[data-testid="pt-settings-submit"]');
    await submitButton.click();
    await expect(submitButton).not.toBeDisabled({ timeout: 10000 });

    // ── Step 4: Reload and verify ───────────────────────────────────
    await page.reload();
    await page.waitForLoadState('networkidle');

    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible({ timeout: 10000 });
    await page.locator('[data-testid="pt-tab-settings"]').click();
    await expect(settingsForm).toBeVisible({ timeout: 10000 });

    const persistedConfidence = await confidenceInput.inputValue();
    expect(persistedConfidence).toBe(newConfidence);

    // ── Step 5: Restore original value ──────────────────────────────
    await confidenceInput.clear();
    await confidenceInput.fill(originalConfidence);
    await submitButton.click();
    await expect(submitButton).not.toBeDisabled({ timeout: 10000 });
  });
});
