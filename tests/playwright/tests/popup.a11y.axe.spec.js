const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;
const { installChromeHostMock, makePack } = require('./helpers/chromeHostMock');

const POPUP_PATH = '/products/prompt-pack-extension/chrome/src/popup/index.html';

async function openPopup(page, options = {}) {
  await installChromeHostMock(page, options);
  await page.goto(POPUP_PATH);
  await expect(page).toHaveTitle('Prompt Pack');
}

function formatViolations(violations) {
  if (!violations.length) {
    return 'No axe violations';
  }

  return violations
    .map((violation) => {
      const targets = violation.nodes
        .flatMap((node) => node.target)
        .slice(0, 5)
        .join(', ');
      return `${violation.id} [${violation.impact || 'unknown'}] ${violation.help} :: ${targets}`;
    })
    .join('\n');
}

async function expectNoAxeViolations(page, contextName) {
  const results = await new AxeBuilder({ page })
    .include('.popup-container')
    .analyze();

  expect(results.violations, `${contextName}\n${formatViolations(results.violations)}`).toEqual([]);
}

test.describe('Prompt Pack popup axe accessibility audit', () => {
  test('passes axe audit for selected idle state', async ({ page }) => {
    const packs = [
      makePack({ packId: 'pack-alpha', packName: 'Alpha Pack' }),
      makePack({ packId: 'pack-beta', packName: 'Beta Pack' }),
    ];

    await openPopup(page, { packs, activePack: packs[0] });
    await page.locator('.pack-item[data-pack-id="pack-beta"] .btn-select').click();
    await expect(page.locator('#currentPack .pack-name')).toHaveText('Beta Pack');

    await expectNoAxeViolations(page, 'selected idle state');
  });

  test('passes axe audit for empty state', async ({ page }) => {
    await openPopup(page, { packs: [], activePack: null });
    await expect(page.locator('#packList')).toContainText('暂无 Pack');

    await expectNoAxeViolations(page, 'empty state');
  });

  test('passes axe audit for runtime error state', async ({ page }) => {
    const activePack = makePack({
      packId: 'pack-error',
      packName: 'Broken Pack',
    });

    await openPopup(page, {
      activePack,
      mockOptions: {
        tabsSendMessageFails: true,
        tabsSendMessageFailsActions: ['executePack'],
      },
    });

    await page.getByRole('button', { name: '执行当前 Prompt Pack' }).click();
    await expect(page.getByRole('alert')).toBeVisible();

    await expectNoAxeViolations(page, 'runtime error state');
  });

  test('passes axe audit for completed state', async ({ page }) => {
    const activePack = makePack({
      packId: 'pack-complete',
      packName: 'Completed Pack',
    });

    await openPopup(page, { activePack });
    await page.getByRole('button', { name: '执行当前 Prompt Pack' }).click();
    await expect(page.getByRole('status')).toContainText('完成');

    await expectNoAxeViolations(page, 'completed state');
  });
});
