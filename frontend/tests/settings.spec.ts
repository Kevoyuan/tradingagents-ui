import { test, expect } from '@playwright/test';

test.describe('Settings Screen', () => {
  test('(a) mounts and loads existing settings without showing blanks', async ({ page }) => {
    await page.goto('/settings');

    // Header title
    await expect(page.locator('h1')).toContainText(/SETTINGS/i);

    // Ticker field is loaded from preferences (not blank)
    const tickerInput = page.locator('[data-testid="settings-ticker"]');
    await expect(tickerInput).toBeVisible();
    const tickerVal = await tickerInput.inputValue();
    expect(tickerVal.length).toBeGreaterThan(0);

    // Provider select has options loaded from catalog
    const providerSelect = page.locator('[data-testid="settings-provider"]');
    await expect(providerSelect).toBeVisible();
    await expect(providerSelect.locator('option')).not.toHaveCount(0);

    // Language select
    const languageSelect = page.locator('[data-testid="settings-language"]');
    await expect(languageSelect).toBeVisible();

    // Research depth select
    const depthSelect = page.locator('[data-testid="settings-depth"]');
    await expect(depthSelect).toBeVisible();

    // Quick and deep model selects
    await expect(page.locator('[data-testid="settings-quick-model"]')).toBeVisible();
    await expect(page.locator('[data-testid="settings-deep-model"]')).toBeVisible();
  });

  test('(b) settings opens as a left modal drawer over the monitor and fits one screen', async ({
    page,
  }) => {
    // The "whole configuration on one screen" requirement is tied to the design
    // target viewport. Playwright's default is 1280x720, which is not it.
    await page.setViewportSize({ width: 1680, height: 1050 });
    await page.goto('/');
    await expect(page.locator('[data-testid="stage-rail"]')).toBeVisible();

    // The trigger is the gear in the left icon rail.
    await page.locator('[data-testid="nav-settings"]').click();

    const drawer = page.locator('[data-testid="settings-drawer"]');
    await expect(drawer).toBeVisible();
    await expect(page.locator('[data-testid="settings-scrim"]')).toBeVisible();

    // It is a left drawer, not a centred dialog.
    const box = await drawer.boundingBox();
    expect(box).not.toBeNull();
    expect(Math.round(box!.x)).toBe(0);
    expect(Math.round(box!.width)).toBeGreaterThan(700);

    // The run stays mounted behind the scrim.
    await expect(page.locator('[data-testid="stage-rail"]')).toBeAttached();

    // The whole configuration is visible at 1050px: every section, and the
    // save button, without scrolling the drawer body.
    const fits = await page.evaluate(() => {
      const body = document.querySelector('[data-testid="settings-body"]') as HTMLElement;
      const save = document.querySelector('[data-testid="settings-save-button"]') as HTMLElement;
      const sections = [...document.querySelectorAll('[data-testid="settings-drawer"] section')];
      const last = sections[sections.length - 1].getBoundingClientRect();
      const bb = body.getBoundingClientRect();
      const sb = save.getBoundingClientRect();
      return {
        // The scroll area must fit every section on its own, and the pinned
        // footer must sit inside the viewport.
        overflow: body.scrollHeight - body.clientHeight,
        lastSectionVisible: last.bottom <= bb.bottom + 2,
        saveInViewport: sb.bottom <= window.innerHeight + 2 && sb.top >= 0,
        sections: sections.length,
      };
    });
    expect(fits.sections).toBeGreaterThanOrEqual(4);
    expect(fits.lastSectionVisible).toBe(true);
    expect(fits.saveInViewport).toBe(true);
    expect(fits.overflow).toBeLessThanOrEqual(4);

    // Closing dismisses the drawer without navigating away.
    await page.locator('[data-testid="settings-close"]').click();
    await expect(page.locator('[data-testid="settings-drawer"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="stage-rail"]')).toBeVisible();
  });

  test('(c) saving settings displays confirmation banner', async ({ page }) => {
    await page.goto('/settings');

    // Ensure ticker input is ready
    const tickerInput = page.locator('[data-testid="settings-ticker"]');
    await expect(tickerInput).toBeVisible();

    // Click Save Preferences button
    const saveBtn = page.locator('[data-testid="settings-save-button"]');
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();

    // Success banner is displayed
    const successBanner = page.locator('[data-testid="save-success-banner"]');
    await expect(successBanner).toBeVisible({ timeout: 10000 });
    await expect(successBanner).toContainText(/saved/i);
  });

  test('(d) Run Launcher modal displays provider and models', async ({ page }) => {
    await page.goto('/');

    // Open launcher modal
    const newRunBtn = page.locator('[data-testid="new-run-button"]');
    if (await newRunBtn.isVisible()) {
      await newRunBtn.click();

      // Assert provider and model selectors are present
      await expect(page.locator('[data-testid="launcher-provider"]')).toBeVisible();
      await expect(page.locator('[data-testid="launcher-quick-model"]')).toBeVisible();
      await expect(page.locator('[data-testid="launcher-deep-model"]')).toBeVisible();
      await expect(page.locator('[data-testid="launcher-ticker"]')).toBeVisible();
      await expect(page.locator('[data-testid="launcher-date"]')).toBeVisible();
    }
  });
});
