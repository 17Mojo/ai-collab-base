const { test, expect } = require('@playwright/test');
const { installChromeHostMock, makePack } = require('./helpers/chromeHostMock');

/**
 * Prompt Pack 项目 GUI 直播演示
 * 演示 Chrome 扩展的 Popup 界面交互
 */

const POPUP_PATH = '/products/prompt-pack-extension/chrome/src/popup/index.html';

test.describe('Prompt Pack 项目 GUI 直播演示', () => {
  
  test.beforeEach(async ({ page }) => {
    // 设置较长的超时时间,便于演示
    test.setTimeout(120000);
    
    // 设置视口大小
    await page.setViewportSize({ width: 1280, height: 720 });
  });

  test('演示: Prompt Pack Popup 加载和显示', async ({ page }) => {
    console.log('\n[演示开始] Prompt Pack Popup 加载和显示');
    console.log('='.repeat(60));

    // 创建测试 Pack 数据
    const activePack = makePack({
      packId: 'demo-pack-001',
      packName: '演示 Prompt Pack',
      description: '这是一个用于 GUI 直播演示的 Prompt Pack',
    });

    console.log('✓ 创建测试 Pack 数据');
    console.log(`  - Pack ID: ${activePack.metadata.pack_id}`);
    console.log(`  - Pack Name: ${activePack.metadata.pack_name}`);

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 截图
    await page.screenshot({ path: 'demo-screenshots/prompt-pack-01-popup-loaded.png' });
    console.log('✓ 截图已保存: prompt-pack-01-popup-loaded.png');

    // 验证 Pack 名称显示
    const packName = await page.locator('#currentPack .pack-name').textContent();
    console.log(`✓ Pack 名称显示: ${packName}`);
    expect(packName).toBe('演示 Prompt Pack');

    // 验证执行按钮状态
    const executeButton = await page.locator('#btnExecute');
    const isEnabled = await executeButton.isEnabled();
    console.log(`✓ 执行按钮状态: ${isEnabled ? '已启用' : '已禁用'}`);
    expect(isEnabled).toBe(true);

    console.log('='.repeat(60));
    console.log('[演示完成] Popup 加载和显示成功\n');
  });

  test('演示: Pack 列表渲染和选择', async ({ page }) => {
    console.log('\n[演示开始] Pack 列表渲染和选择');
    console.log('='.repeat(60));

    // 创建多个测试 Pack
    const packs = [
      makePack({ packId: 'pack-alpha', packName: 'Alpha Pack', description: '第一个测试 Pack' }),
      makePack({ packId: 'pack-beta', packName: 'Beta Pack', description: '第二个测试 Pack' }),
      makePack({ packId: 'pack-gamma', packName: 'Gamma Pack', description: '第三个测试 Pack' }),
    ];

    console.log('✓ 创建 3 个测试 Pack');
    packs.forEach((pack, index) => {
      console.log(`  ${index + 1}. ${pack.metadata.pack_name} (${pack.metadata.pack_id})`);
    });

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { packs });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 截图
    await page.screenshot({ path: 'demo-screenshots/prompt-pack-02-pack-list.png' });
    console.log('✓ 截图已保存: prompt-pack-02-pack-list.png');

    // 验证 Pack 列表项数量
    const packItems = await page.locator('.pack-item').count();
    console.log(`✓ Pack 列表项数量: ${packItems}`);
    expect(packItems).toBe(3);

    // 点击选择第一个 Pack
    console.log('→ 点击选择 Alpha Pack...');
    await page.click('.pack-item[data-pack-id="pack-alpha"] .btn-select');
    await page.waitForTimeout(1000);
    console.log('✓ Alpha Pack 已选择');

    // 截图
    await page.screenshot({ path: 'demo-screenshots/prompt-pack-03-pack-selected.png' });
    console.log('✓ 截图已保存: prompt-pack-03-pack-selected.png');

    // 验证当前 Pack 显示
    const currentPackName = await page.locator('#currentPack .pack-name').textContent();
    console.log(`✓ 当前 Pack: ${currentPackName}`);
    expect(currentPackName).toBe('Alpha Pack');

    // 验证 Chrome Mock 状态
    const state = await page.evaluate(() => globalThis.__chromeMockState);
    console.log(`✓ Mock 状态 - lastLoadedPackId: ${state.lastLoadedPackId}`);
    expect(state.lastLoadedPackId).toBe('pack-alpha');

    console.log('='.repeat(60));
    console.log('[演示完成] Pack 列表渲染和选择成功\n');
  });

  test('演示: Pack 执行流程', async ({ page }) => {
    console.log('\n[演示开始] Pack 执行流程');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'exec-demo-pack',
      packName: '执行演示 Pack',
      description: '用于演示执行流程的 Pack',
    });

    console.log('✓ 创建执行演示 Pack');

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 截图初始状态
    await page.screenshot({ path: 'demo-screenshots/prompt-pack-04-before-execute.png' });
    console.log('✓ 截图已保存: prompt-pack-04-before-execute.png');

    // 点击执行按钮
    console.log('→ 点击执行按钮...');
    await page.getByRole('button', { name: '执行当前 Prompt Pack' }).click();
    console.log('✓ 执行按钮已点击');

    // 等待状态更新
    console.log('→ 等待执行完成...');
    await expect(page.locator('#statusBar .status-text')).toContainText('完成', { timeout: 10000 });
    console.log('✓ 执行完成');

    // 截图完成状态
    await page.screenshot({ path: 'demo-screenshots/prompt-pack-05-after-execute.png' });
    console.log('✓ 截图已保存: prompt-pack-05-after-execute.png');

    // 验证状态栏
    const statusText = await page.locator('#statusBar .status-text').textContent();
    console.log(`✓ 状态栏文本: ${statusText}`);

    // 验证 Chrome Mock 状态
    const state = await page.evaluate(() => globalThis.__chromeMockState);
    console.log(`✓ Mock 状态 - tabStatus.status: ${state.tabStatus.status}`);
    expect(state.tabStatus.status).toBe('completed');

    // 验证 Tab 消息
    const tabActions = state.tabMessages.map((entry) => entry.payload.action);
    console.log(`✓ Tab 消息操作: ${tabActions.join(', ')}`);
    expect(tabActions).toContain('executePack');

    console.log('='.repeat(60));
    console.log('[演示完成] Pack 执行流程成功\n');
  });

  test('演示: 设置页面打开', async ({ page }) => {
    console.log('\n[演示开始] 设置页面打开');
    console.log('='.repeat(60));

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page);
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 截图初始状态
    await page.screenshot({ path: 'demo-screenshots/prompt-pack-06-before-settings.png' });
    console.log('✓ 截图已保存: prompt-pack-06-before-settings.png');

    // 点击设置按钮
    console.log('→ 点击设置按钮...');
    await page.getByRole('button', { name: '打开设置' }).click();
    console.log('✓ 设置按钮已点击');

    // 等待一下
    await page.waitForTimeout(1000);

    // 截图
    await page.screenshot({ path: 'demo-screenshots/prompt-pack-07-after-settings.png' });
    console.log('✓ 截图已保存: prompt-pack-07-after-settings.png');

    // 验证 Chrome Mock 状态
    const state = await page.evaluate(() => globalThis.__chromeMockState);
    console.log(`✓ Mock 状态 - optionsPageOpened: ${state.optionsPageOpened}`);
    expect(state.optionsPageOpened).toBeTruthy();

    console.log('='.repeat(60));
    console.log('[演示完成] 设置页面打开成功\n');
  });

  test('演示: 完整用户流程', async ({ page }) => {
    console.log('\n[演示开始] 完整用户流程');
    console.log('='.repeat(60));

    // 创建多个测试 Pack
    const packs = [
      makePack({ packId: 'flow-pack-1', packName: '流程 Pack 1', description: '第一个流程测试 Pack' }),
      makePack({ packId: 'flow-pack-2', packName: '流程 Pack 2', description: '第二个流程测试 Pack' }),
    ];

    console.log('✓ 创建 2 个测试 Pack');

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { packs });
    console.log('✓ Chrome Host Mock 已安装');

    // 步骤 1: 打开 Popup
    console.log('\n步骤 1: 打开 Popup');
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');
    await page.screenshot({ path: 'demo-screenshots/prompt-pack-08-step1-popup.png' });

    // 步骤 2: 查看 Pack 列表
    console.log('\n步骤 2: 查看 Pack 列表');
    const packItems = await page.locator('.pack-item').count();
    console.log(`✓ 找到 ${packItems} 个 Pack`);
    await page.screenshot({ path: 'demo-screenshots/prompt-pack-09-step2-list.png' });

    // 步骤 3: 选择 Pack
    console.log('\n步骤 3: 选择 Pack');
    console.log('→ 选择流程 Pack 1...');
    await page.click('.pack-item[data-pack-id="flow-pack-1"] .btn-select');
    await page.waitForTimeout(1000);
    const selectedPack = await page.locator('#currentPack .pack-name').textContent();
    console.log(`✓ 已选择: ${selectedPack}`);
    await page.screenshot({ path: 'demo-screenshots/prompt-pack-10-step3-select.png' });

    // 步骤 4: 执行 Pack
    console.log('\n步骤 4: 执行 Pack');
    console.log('→ 点击执行按钮...');
    await page.getByRole('button', { name: '执行当前 Prompt Pack' }).click();
    await expect(page.locator('#statusBar .status-text')).toContainText('完成', { timeout: 10000 });
    console.log('✓ 执行完成');
    await page.screenshot({ path: 'demo-screenshots/prompt-pack-11-step4-execute.png' });

    // 步骤 5: 查看状态
    console.log('\n步骤 5: 查看状态');
    const statusText = await page.locator('#statusBar .status-text').textContent();
    console.log(`✓ 当前状态: ${statusText}`);
    await page.screenshot({ path: 'demo-screenshots/prompt-pack-12-step5-status.png' });

    console.log('='.repeat(60));
    console.log('[演示完成] 完整用户流程成功\n');
  });
});
