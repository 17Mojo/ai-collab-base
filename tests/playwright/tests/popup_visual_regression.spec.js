const { test, expect } = require('@playwright/test');
const { installChromeHostMock, makePack } = require('./helpers/chromeHostMock');

/**
 * Popup 视觉回归测试
 * 使用 Playwright 的截图功能进行视觉回归测试
 */

const POPUP_PATH = '/products/prompt-pack-extension/chrome/src/popup/index.html';

test.describe('Popup 视觉回归测试', () => {
  
  test.beforeEach(async ({ page }) => {
    test.setTimeout(30000);
    await page.setViewportSize({ width: 400, height: 600 });
  });

  test('视觉回归: 初始状态', async ({ page }) => {
    console.log('\n[测试开始] 视觉回归: 初始状态');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'visual-test-pack',
      packName: '视觉测试 Pack',
      description: '用于视觉回归测试的 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 等待页面稳定
    await page.waitForTimeout(1000);

    // 截图
    await expect(page).toHaveScreenshot('popup-initial-state.png', {
      maxDiffPixels: 100,
    });
    console.log('✓ 截图已保存: popup-initial-state.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 视觉回归: 初始状态\n');
  });

  test('视觉回归: Pack 列表', async ({ page }) => {
    console.log('\n[测试开始] 视觉回归: Pack 列表');
    console.log('='.repeat(60));

    // 创建多个测试 Pack
    const packs = [
      makePack({ packId: 'pack-1', packName: 'Alpha Pack', description: '第一个测试 Pack' }),
      makePack({ packId: 'pack-2', packName: 'Beta Pack', description: '第二个测试 Pack' }),
      makePack({ packId: 'pack-3', packName: 'Gamma Pack', description: '第三个测试 Pack' }),
    ];

    console.log('✓ 创建 3 个测试 Pack');

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { packs });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 等待页面稳定
    await page.waitForTimeout(1000);

    // 截图
    await expect(page).toHaveScreenshot('popup-pack-list.png', {
      maxDiffPixels: 100,
    });
    console.log('✓ 截图已保存: popup-pack-list.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 视觉回归: Pack 列表\n');
  });

  test('视觉回归: Pack 选中状态', async ({ page }) => {
    console.log('\n[测试开始] 视觉回归: Pack 选中状态');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'selected-pack',
      packName: '已选中 Pack',
      description: '已选中的测试 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 等待页面稳定
    await page.waitForTimeout(1000);

    // 截图
    await expect(page).toHaveScreenshot('popup-selected-state.png', {
      maxDiffPixels: 100,
    });
    console.log('✓ 截图已保存: popup-selected-state.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 视觉回归: Pack 选中状态\n');
  });

  test('视觉回归: 执行状态', async ({ page }) => {
    console.log('\n[测试开始] 视觉回归: 执行状态');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'exec-pack',
      packName: '执行测试 Pack',
      description: '用于执行测试的 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 点击执行按钮
    console.log('→ 点击执行按钮...');
    await page.getByRole('button', { name: '执行当前 Prompt Pack' }).click();
    console.log('✓ 执行按钮已点击');

    // 等待执行完成
    await expect(page.locator('#statusBar .status-text')).toContainText('完成', { timeout: 10000 });
    console.log('✓ 执行完成');

    // 等待页面稳定
    await page.waitForTimeout(1000);

    // 截图
    await expect(page).toHaveScreenshot('popup-executed-state.png', {
      maxDiffPixels: 100,
    });
    console.log('✓ 截图已保存: popup-executed-state.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 视觉回归: 执行状态\n');
  });

  test('视觉回归: 响应式布局 (小屏幕)', async ({ page }) => {
    console.log('\n[测试开始] 视觉回归: 响应式布局 (小屏幕)');
    console.log('='.repeat(60));

    // 设置小屏幕视口
    await page.setViewportSize({ width: 320, height: 480 });
    console.log('✓ 设置视口大小: 320x480');

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'responsive-pack',
      packName: '响应式测试 Pack',
      description: '用于响应式测试的 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 等待页面稳定
    await page.waitForTimeout(1000);

    // 截图
    await expect(page).toHaveScreenshot('popup-responsive-small.png', {
      maxDiffPixels: 100,
    });
    console.log('✓ 截图已保存: popup-responsive-small.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 视觉回归: 响应式布局 (小屏幕)\n');
  });

  test('视觉回归: 响应式布局 (大屏幕)', async ({ page }) => {
    console.log('\n[测试开始] 视觉回归: 响应式布局 (大屏幕)');
    console.log('='.repeat(60));

    // 设置大屏幕视口
    await page.setViewportSize({ width: 600, height: 800 });
    console.log('✓ 设置视口大小: 600x800');

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'responsive-pack',
      packName: '响应式测试 Pack',
      description: '用于响应式测试的 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 等待页面稳定
    await page.waitForTimeout(1000);

    // 截图
    await expect(page).toHaveScreenshot('popup-responsive-large.png', {
      maxDiffPixels: 100,
    });
    console.log('✓ 截图已保存: popup-responsive-large.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 视觉回归: 响应式布局 (大屏幕)\n');
  });

  test('视觉回归: Compact 视口', async ({ page }) => {
    console.log('\n[测试开始] 视觉回归: Compact 视口');
    console.log('='.repeat(60));

    // 设置 compact 视口
    await page.setViewportSize({ width: 360, height: 640 });
    console.log('✓ 设置视口大小: 360x640');

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'compact-pack',
      packName: 'Compact 测试 Pack',
      description: '用于 compact 视口测试的 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 等待页面稳定
    await page.waitForTimeout(1000);

    // 截图
    await expect(page).toHaveScreenshot('popup-compact-viewport.png', {
      maxDiffPixels: 100,
    });
    console.log('✓ 截图已保存: popup-compact-viewport.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 视觉回归: Compact 视口\n');
  });

  test('视觉回归: Mobile 视口', async ({ page }) => {
    console.log('\n[测试开始] 视觉回归: Mobile 视口');
    console.log('='.repeat(60));

    // 设置 mobile 视口
    await page.setViewportSize({ width: 375, height: 667 });
    console.log('✓ 设置视口大小: 375x667');

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'mobile-pack',
      packName: 'Mobile 测试 Pack',
      description: '用于 mobile 视口测试的 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 等待页面稳定
    await page.waitForTimeout(1000);

    // 截图
    await expect(page).toHaveScreenshot('popup-mobile-viewport.png', {
      maxDiffPixels: 100,
    });
    console.log('✓ 截图已保存: popup-mobile-viewport.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 视觉回归: Mobile 视口\n');
  });

  test('视觉回归: Empty 状态', async ({ page }) => {
    console.log('\n[测试开始] 视觉回归: Empty 状态');
    console.log('='.repeat(60));

    // 安装 Chrome Host Mock (无 Pack)
    console.log('→ 安装 Chrome Host Mock (空 Pack 列表)...');
    await installChromeHostMock(page, { packs: [] });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 等待页面稳定
    await page.waitForTimeout(1000);

    // 截图
    await expect(page).toHaveScreenshot('popup-empty-state.png', {
      maxDiffPixels: 100,
    });
    console.log('✓ 截图已保存: popup-empty-state.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 视觉回归: Empty 状态\n');
  });

  test('视觉回归: Error 状态', async ({ page }) => {
    console.log('\n[测试开始] 视觉回归: Error 状态');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'error-pack',
      packName: 'Error 测试 Pack',
      description: '用于 error 状态测试的 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock (配置执行失败)
    console.log('→ 安装 Chrome Host Mock (配置执行失败)...');
    await installChromeHostMock(page, {
      activePack,
      mockOptions: {
        tabsSendMessageFails: true,
        tabsSendMessageFailsActions: ['executePack'],
      },
    });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 点击执行按钮
    console.log('→ 点击执行按钮...');
    await page.getByRole('button', { name: '执行当前 Prompt Pack' }).click();
    console.log('✓ 执行按钮已点击');

    // 等待错误状态出现
    await expect(page.locator('#statusBar .status-text')).toContainText('失败', { timeout: 10000 });
    console.log('✓ 错误状态已显示');

    // 等待页面稳定
    await page.waitForTimeout(1000);

    // 截图
    await expect(page).toHaveScreenshot('popup-error-state.png', {
      maxDiffPixels: 100,
    });
    console.log('✓ 截图已保存: popup-error-state.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 视觉回归: Error 状态\n');
  });
});
