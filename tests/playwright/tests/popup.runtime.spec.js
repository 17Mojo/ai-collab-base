const { test, expect } = require('@playwright/test');
const { installChromeHostMock, makePack } = require('./helpers/chromeHostMock');

const POPUP_PATH = '/products/prompt-pack-extension/chrome/src/popup/index.html';

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

    logTestStep('Verifying pack name display');
    await expect(page.locator('#currentPack .pack-name')).toHaveText('Active Pack');

    logTestStep('Verifying execute button is enabled');
    await expect(page.locator('#btnExecute')).toBeEnabled();

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

    logTestStep('Clicking pack-1 select button');
    await page.click('.pack-item[data-pack-id="pack-1"] .btn-select');

    logTestStep('Verifying selected pack name');
    await expect(page.locator('#currentPack .pack-name')).toHaveText('Alpha Pack');
    await expect(page.locator('#btnExecute')).toBeEnabled();

    logTestStep('Retrieving chrome mock state');
    const state = await page.evaluate(() => globalThis.__chromeMockState);
    logTestStep('Mock state retrieved', { lastLoadedPackId: state.lastLoadedPackId });
    expect(state.lastLoadedPackId).toBe('pack-1');

    const tabActions = state.tabMessages.map((entry) => entry.payload.action);
    logTestStep('Verifying tab actions', { tabActions });
    expect(tabActions).toContain('loadPack');

    logTestStep('Test completed successfully');
  });

  test('executes pack end-to-end via mocked tabs API and updates status', async ({ page }) => {
    logTestStep('Test started: executes pack end-to-end');

    const activePack = makePack({
      packId: 'pack-exec',
      packName: 'Execution Pack',
    });

    logTestStep('Created execution pack', { packId: activePack.metadata.pack_id });

    await openPopup(page, { activePack });

    logTestStep('Clicking execute button');
    await page.getByRole('button', { name: '执行当前 Prompt Pack' }).click();

    logTestStep('Waiting for completion status');
    await expect(page.locator('#statusBar .status-text')).toContainText('完成');

    logTestStep('Waiting for status stabilization');
    await page.waitForTimeout(2200);

    logTestStep('Verifying final status');
    await expect(page.locator('#statusBar .status-text')).toContainText('完成');

    logTestStep('Retrieving chrome mock state');
    const state = await page.evaluate(() => globalThis.__chromeMockState);

    const tabActions = state.tabMessages.map((entry) => entry.payload.action);
    logTestStep('Verifying tab actions', { tabActions, tabStatus: state.tabStatus.status });
    expect(tabActions).toContain('executePack');
    expect(state.tabStatus.status).toBe('completed');

    logTestStep('Test completed successfully');
  });

  test('opens settings through mocked runtime host', async ({ page }) => {
    logTestStep('Test started: opens settings');

    await openPopup(page);

    logTestStep('Clicking settings button');
    await page.getByRole('button', { name: '打开设置' }).click();

    logTestStep('Retrieving chrome mock state');
    const state = await page.evaluate(() => globalThis.__chromeMockState);
    logTestStep('Verifying options page opened', { optionsPageOpened: state.optionsPageOpened });
    expect(state.optionsPageOpened).toBeTruthy();

    logTestStep('Test completed successfully');
  });
});
