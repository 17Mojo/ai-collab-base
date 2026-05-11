const { test, expect } = require('@playwright/test');
const { installChromeHostMock, makePack } = require('./helpers/chromeHostMock');

const POPUP_PATH = '/products/prompt-pack-extension/chrome/src/popup/index.html';

async function openPopup(page, options = {}) {
  await installChromeHostMock(page, options);
  await page.goto(POPUP_PATH);
  await expect(page).toHaveTitle('Prompt Pack');
}

function normalizeOutlineWidth(width) {
  const value = Number.parseFloat(width || '0');
  return Number.isFinite(value) ? value : 0;
}

test.describe('Prompt Pack popup accessibility smoke', () => {
  test('supports keyboard focus and exposes accessible labels', async ({ page }) => {
    const packs = [
      makePack({ packId: 'pack-1', packName: 'Alpha Pack' }),
      makePack({ packId: 'pack-2', packName: 'Beta Pack' }),
    ];

    await openPopup(page, { packs, activePack: packs[0] });

    await expect(page.getByRole('button', { name: '执行当前 Prompt Pack' })).toBeVisible();
    await expect(page.getByRole('button', { name: '暂停当前执行' })).toBeVisible();
    await expect(page.getByRole('button', { name: '停止当前执行' })).toBeVisible();
    await expect(page.getByRole('button', { name: '刷新 Pack 列表' })).toBeVisible();
    await expect(page.getByRole('button', { name: '打开设置' })).toBeVisible();
    await expect(
      page.locator('.pack-item[data-pack-id="pack-1"] .btn-select')
    ).toHaveAttribute('aria-label', '选择 Pack Alpha Pack');
    await expect(
      page.locator('.pack-item[data-pack-id="pack-1"] .btn-delete')
    ).toHaveAttribute('aria-label', '删除 Pack Alpha Pack');

    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: '执行当前 Prompt Pack' })).toBeFocused();

    const outlineWidth = await page
      .getByRole('button', { name: '执行当前 Prompt Pack' })
      .evaluate((element) => getComputedStyle(element).outlineWidth);
    expect(normalizeOutlineWidth(outlineWidth)).toBeGreaterThan(0);
  });

  test('announces execution state through role=status', async ({ page }) => {
    const activePack = makePack({
      packId: 'pack-a11y',
      packName: 'A11y Pack',
      description: 'Smoke accessibility pack',
    });

    await openPopup(page, { activePack });

    const status = page.getByRole('status');
    await expect(status).toContainText('就绪');

    await page.getByRole('button', { name: '执行当前 Prompt Pack' }).click();
    await expect(status).toContainText('完成');
  });

  test('surfaces runtime errors through alert semantics and retry action', async ({ page }) => {
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

    const alert = page.getByRole('alert');
    await expect(alert).toBeVisible();
    await expect(alert).toContainText('执行失败');
    await expect(page.getByRole('button', { name: '重试当前运行时状态' })).toBeVisible();
    await expect(page.getByRole('status')).toContainText('失败');
  });

  test('keeps empty state actions reachable', async ({ page }) => {
    await openPopup(page, { packs: [], activePack: null });

    await expect(page.locator('#packList')).toContainText('暂无 Pack');
    await expect(page.getByRole('button', { name: '导入 Prompt Pack' })).toBeVisible();
    await expect(page.getByRole('status')).toContainText('就绪');
  });
});
