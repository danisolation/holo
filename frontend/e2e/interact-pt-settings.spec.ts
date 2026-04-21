import { test, expect } from '@playwright/test';
import { navigateAndWait } from './fixtures/test-helpers';

test.describe('INTERACT-01: Paper Trading Settings Form', () => {
  test('settings form submits and values persist through reload', async ({ page }) => {
    // 1. Navigate to Paper Trading page
    await navigateAndWait(page, '/dashboard/paper-trading');
    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible();

    // 2. Click Settings tab
    await page.locator('[data-testid="pt-tab-settings"]').click();

    // 3. Wait for settings form to be visible
    const settingsForm = page.locator('[data-testid="pt-settings-form"]');
    await expect(settingsForm).toBeVisible({ timeout: 10000 });

    // 4. Read the initial capital value from the input
    const capitalInput = settingsForm.locator('input[type="number"]').first();
    await expect(capitalInput).toBeVisible();
    const initialValue = await capitalInput.inputValue();

    // 5. Modify the capital value — append "0" to make it different
    await capitalInput.clear();
    const newValue = initialValue ? String(Number(initialValue) + 1000000) : '100000000';
    await capitalInput.fill(newValue);

    // 6. Click submit button
    const submitButton = page.locator('[data-testid="pt-settings-submit"]');
    await expect(submitButton).toBeVisible();
    await submitButton.click();

    // 7. Wait for success indication — button should re-enable (no longer show "Đang lưu...")
    // After mutation completes, button text returns to "Lưu cài đặt"
    await expect(submitButton).not.toBeDisabled({ timeout: 10000 });
    await expect(submitButton).toContainText('Lưu cài đặt', { timeout: 5000 });

    // 8. Reload the page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // 9. Navigate back to Settings tab
    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible();
    await page.locator('[data-testid="pt-tab-settings"]').click();
    await expect(settingsForm).toBeVisible({ timeout: 10000 });

    // 10. Verify the form shows the submitted value persisted
    const persistedValue = await capitalInput.inputValue();
    expect(persistedValue).toBe(newValue);
  });

  test('settings form renders all expected fields', async ({ page }) => {
    await navigateAndWait(page, '/dashboard/paper-trading');
    await page.locator('[data-testid="pt-tab-settings"]').click();

    const settingsForm = page.locator('[data-testid="pt-settings-form"]');
    await expect(settingsForm).toBeVisible({ timeout: 10000 });

    // Verify labels exist (Vietnamese text from component)
    await expect(settingsForm.getByText('Vốn ban đầu (VND)')).toBeVisible();
    await expect(settingsForm.getByText('Tự động theo dõi tín hiệu')).toBeVisible();
    await expect(settingsForm.getByText('Ngưỡng confidence tối thiểu')).toBeVisible();

    // Verify auto-track toggle buttons exist (Bật/Tắt)
    await expect(settingsForm.getByRole('button', { name: 'Bật' })).toBeVisible();
    await expect(settingsForm.getByRole('button', { name: 'Tắt' })).toBeVisible();

    // Verify submit button exists
    await expect(page.locator('[data-testid="pt-settings-submit"]')).toBeVisible();
  });

  test('auto-track toggle can be switched', async ({ page }) => {
    await navigateAndWait(page, '/dashboard/paper-trading');
    await page.locator('[data-testid="pt-tab-settings"]').click();

    const settingsForm = page.locator('[data-testid="pt-settings-form"]');
    await expect(settingsForm).toBeVisible({ timeout: 10000 });

    const enableBtn = settingsForm.getByRole('button', { name: 'Bật' });
    const disableBtn = settingsForm.getByRole('button', { name: 'Tắt' });

    // Click "Tắt" (disable) — it should become the active/default variant
    await disableBtn.click();

    // Click "Bật" (enable) — it should switch back
    await enableBtn.click();

    // Both buttons should remain visible and clickable
    await expect(enableBtn).toBeVisible();
    await expect(disableBtn).toBeVisible();
  });
});
