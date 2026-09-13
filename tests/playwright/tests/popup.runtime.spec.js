const { test, expect } = require('@playwright/test');
const { installChromeHostMock, makePack } = require('./helpers/chromeHostMock');

const POPUP_PATH = '/chrome-extension/public/popup.html';

// Enhanced logging helper
function logTestStep(stepName, details = {}) {
  console.log(`[TEST STEP] ${stepName}`, details);
}

async function openPopup(page, options = {}) {
  const consoleErrors = [];
  const consoleWarnings = [];
  const consoleLogs = [];

  page.on('console', (msg) => {
    const text = msg.text();
    if (msg.type() === 'error') {
      consoleErrors.push(text);
      console.error(`[BROWSER ERROR] ${text}`);
    } else if (msg.type() === 'warning') {
      consoleWarnings.push(text);
      console.warn(`[BROWSER WARNING] ${text}`);
    } else {
      consoleLogs.push(text);
    }
  });

  logTestStep('Installing Chrome host mock', { options });
  await installChromeHostMock(page, options);

  logTestStep('Navigating to popup', { path: POPUP_PATH });
  await page.goto(POPUP_PATH);

  logTestStep('Waiting for popup title');
  await expect(page).toHaveTitle('Prompt Pack');

  logTestStep('Popup loaded successfully', {
    errorCount: consoleErrors.length,
    warningCount: consoleWarnings.length
  });

  return { consoleErrors, consoleWarnings, consoleLogs };
}

test.describe('Prompt Pack popup runtime (Playwright)', () => {
  test('loads active pack from chrome.storage without popup runtime error', async ({ page }) => {
    logTestStep('Test started: loads active pack from chrome.storage');

    const activePack = makePack({
      packId: 'pack-active',
      packName: 'Active Pack',
      description: 'Loaded from chrome.storage.local',
    });

    logTestStep('Created test pack', { packId: activePack.metadata.pack_id });

    const { consoleErrors } = await openPopup(page, { activePack });

    logTestStep('Verifying pack list is visible');
    await expect(page.locator('[data-testid="pack-list"]')).toBeVisible();

    logTestStep('Verifying refresh button is enabled');
    await expect(page.locator('[data-testid="refresh-btn"]')).toBeEnabled();

    const popupErrors = consoleErrors.filter((msg) => msg.includes('[Popup]'));
    logTestStep('Checking for popup errors', { popupErrorCount: popupErrors.length });
    expect(popupErrors).toEqual([]);

    const hasStorageError = consoleErrors.some((msg) =>
      msg.includes("Cannot read properties of undefined (reading 'local')")
    );
    logTestStep('Checking for storage errors', { hasStorageError });
    expect(hasStorageError).toBeFalsy();

    logTestStep('Test completed successfully');
  });

  test('renders pack list and selects pack via mocked runtime/tabs host', async ({ page }) => {
    logTestStep('Test started: renders pack list and selects pack');

    const packs = [
      makePack({ packId: 'pack-1', packName: 'Alpha Pack' }),
      makePack({ packId: 'pack-2', packName: 'Beta Pack' }),
    ];

    logTestStep('Created test packs', { packCount: packs.length });

    await openPopup(page, { packs });

    logTestStep('Verifying pack list items');
    await expect(page.locator('.pack-item')).toHaveCount(2);

    logTestStep('Clicking pack-1 item');
    await page.click('.pack-item[data-id="pack-1"]');

    logTestStep('Verifying status bar updated');
    await expect(page.locator('[data-testid="status-bar"]')).toContainText('执行');

    logTestStep('Retrieving chrome mock state');
    const state = await page.evaluate(() => globalThis.__chromeMockState);
    logTestStep('Mock state retrieved', { runtimeMessageCount: state.runtimeMessages.length });

    // popup.js 通过 chrome.runtime.sendMessage 发送 EXECUTE_PACK（非 tabs.sendMessage）
    const runtimeTypes = state.runtimeMessages.map((msg) => msg.type);
    logTestStep('Verifying runtime message types', { runtimeTypes });
    expect(runtimeTypes).toContain('EXECUTE_PACK');

    logTestStep('Test completed successfully');
  });

  test('executes pack end-to-end via mocked runtime API and updates status', async ({ page }) => {
    logTestStep('Test started: executes pack end-to-end');

    const packs = [
      makePack({ packId: 'pack-exec', packName: 'Execution Pack' }),
    ];

    logTestStep('Created execution pack', { packId: packs[0].metadata.pack_id });

    await openPopup(page, { packs });

    logTestStep('Clicking pack item to execute');
    await page.click('.pack-item[data-id="pack-exec"]');

    logTestStep('Waiting for status update');
    await expect(page.locator('[data-testid="status-bar"]')).toContainText('执行');

    logTestStep('Retrieving chrome mock state');
    const state = await page.evaluate(() => globalThis.__chromeMockState);

    // popup.js 通过 chrome.runtime.sendMessage 发送 EXECUTE_PACK
    const runtimeTypes = state.runtimeMessages.map((msg) => msg.type);
    logTestStep('Verifying runtime message types', { runtimeTypes });
    expect(runtimeTypes).toContain('EXECUTE_PACK');

    logTestStep('Test completed successfully');
  });

  test('opens settings through mocked runtime host', async ({ page }) => {
    logTestStep('Test started: opens settings');

    await openPopup(page);

    logTestStep('Clicking settings button');
    await page.getByRole('button', { name: '刷新 Pack 列表' }).click();

    logTestStep('Retrieving chrome mock state');
    const state = await page.evaluate(() => globalThis.__chromeMockState);
    logTestStep('Verifying refresh completed', { runtimeMessages: state.runtimeMessages.length });
    expect(state).toBeTruthy();

    logTestStep('Test completed successfully');
  });
});
