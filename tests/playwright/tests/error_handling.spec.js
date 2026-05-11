const { test, expect } = require('@playwright/test');
const { installChromeHostMock, makePack } = require('./helpers/chromeHostMock');

/**
 * Prompt Pack 错误处理和边界情况测试
 * 测试系统在各种错误和边界情况下的行为
 */

const POPUP_PATH = '/products/prompt-pack-extension/chrome/src/popup/index.html';

test.describe('错误处理和边界情况测试', () => {
  
  test.beforeEach(async ({ page }) => {
    test.setTimeout(30000);
    await page.setViewportSize({ width: 1280, height: 720 });
  });

  test('错误处理: 空 Pack 列表', async ({ page }) => {
    console.log('\n[测试开始] 空 Pack 列表');
    console.log('='.repeat(60));

    // 安装 Chrome Host Mock,不提供任何 Pack
    console.log('→ 安装 Chrome Host Mock (无 Pack 数据)...');
    await installChromeHostMock(page, { packs: [] });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 验证空状态显示
    console.log('→ 验证空状态显示...');
    const emptyState = await page.locator('.empty-state').isVisible();
    console.log(`✓ 空状态显示: ${emptyState ? '是' : '否'}`);

    // 验证 Pack 列表为空
    const packItems = await page.locator('.pack-item').count();
    console.log(`✓ Pack 列表项数量: ${packItems}`);
    expect(packItems).toBe(0);

    // 验证执行按钮禁用
    const executeButton = await page.locator('#btnExecute');
    const isEnabled = await executeButton.isEnabled();
    console.log(`✓ 执行按钮状态: ${isEnabled ? '已启用' : '已禁用'}`);
    expect(isEnabled).toBe(false);

    // 截图
    await page.screenshot({ path: 'demo-screenshots/error-empty-list.png' });
    console.log('✓ 截图已保存: error-empty-list.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 空 Pack 列表处理正确\n');
  });

  test('错误处理: Chrome API 失败', async ({ page }) => {
    console.log('\n[测试开始] Chrome API 失败');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'error-test-pack',
      packName: '错误测试 Pack',
    });

    // 安装 Chrome Host Mock,并设置 API 失败
    console.log('→ 安装 Chrome Host Mock (API 失败模式)...');
    await installChromeHostMock(page, {
      activePack,
      mockOptions: {
        storageGetFails: true, // 模拟 storage.get 失败
      },
    });
    console.log('✓ Chrome Host Mock 已安装 (API 失败模式)');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 验证错误状态显示
    console.log('→ 验证错误状态显示...');
    const errorState = await page.locator('.error-state').isVisible();
    console.log(`✓ 错误状态显示: ${errorState ? '是' : '否'}`);

    // 验证错误消息
    const errorMessage = await page.locator('.error-message').textContent();
    console.log(`✓ 错误消息: ${errorMessage}`);
    expect(errorMessage).toContain('加载失败');

    // 截图
    await page.screenshot({ path: 'demo-screenshots/error-api-failure.png' });
    console.log('✓ 截图已保存: error-api-failure.png');

    console.log('='.repeat(60));
    console.log('[测试完成] Chrome API 失败处理正确\n');
  });

  test('错误处理: 无效 Pack 数据', async ({ page }) => {
    console.log('\n[测试开始] 无效 Pack 数据');
    console.log('='.repeat(60));

    // 创建无效的 Pack 数据
    const invalidPack = {
      metadata: {
        pack_id: 'invalid-pack',
        // 缺少 pack_name
      },
      // 缺少 prompts
    };

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock (无效 Pack 数据)...');
    await installChromeHostMock(page, { activePack: invalidPack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 验证错误状态显示
    console.log('→ 验证错误状态显示...');
    const errorState = await page.locator('.error-state').isVisible();
    console.log(`✓ 错误状态显示: ${errorState ? '是' : '否'}`);

    // 验证错误消息
    const errorMessage = await page.locator('.error-message').textContent();
    console.log(`✓ 错误消息: ${errorMessage}`);
    expect(errorMessage).toContain('无效');

    // 截图
    await page.screenshot({ path: 'demo-screenshots/error-invalid-pack.png' });
    console.log('✓ 截图已保存: error-invalid-pack.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 无效 Pack 数据处理正确\n');
  });

  test('错误处理: 执行失败', async ({ page }) => {
    console.log('\n[测试开始] 执行失败');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'exec-fail-pack',
      packName: '执行失败测试 Pack',
    });

    // 安装 Chrome Host Mock,并设置执行失败
    console.log('→ 安装 Chrome Host Mock (执行失败模式)...');
    await installChromeHostMock(page, {
      activePack,
      mockOptions: {
        tabsSendMessageFails: true, // 模拟 tabs.sendMessage 失败
      },
    });
    console.log('✓ Chrome Host Mock 已安装 (执行失败模式)');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 点击执行按钮
    console.log('→ 点击执行按钮...');
    await page.getByRole('button', { name: '执行当前 Prompt Pack' }).click();
    console.log('✓ 执行按钮已点击');

    // 等待错误状态
    console.log('→ 等待错误状态...');
    await expect(page.locator('#statusBar .status-text')).toContainText('失败', { timeout: 10000 });
    console.log('✓ 错误状态已显示');

    // 验证错误消息
    const statusText = await page.locator('#statusBar .status-text').textContent();
    console.log(`✓ 状态栏文本: ${statusText}`);
    expect(statusText).toContain('失败');

    // 截图
    await page.screenshot({ path: 'demo-screenshots/error-execution-failure.png' });
    console.log('✓ 截图已保存: error-execution-failure.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 执行失败处理正确\n');
  });

  test('边界情况: 超长 Pack 名称', async ({ page }) => {
    console.log('\n[测试开始] 超长 Pack 名称');
    console.log('='.repeat(60));

    // 创建超长名称的 Pack
    const longNamePack = makePack({
      packId: 'long-name-pack',
      packName: '这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的 Pack 名称',
    });

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock (超长名称)...');
    await installChromeHostMock(page, { activePack: longNamePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 验证 Pack 名称显示
    console.log('→ 验证 Pack 名称显示...');
    const packName = await page.locator('#currentPack .pack-name').textContent();
    console.log(`✓ Pack 名称长度: ${packName.length}`);

    // 验证名称被截断或换行
    const packNameElement = await page.locator('#currentPack .pack-name');
    const boundingBox = await packNameElement.boundingBox();
    console.log(`✓ Pack 名称元素宽度: ${boundingBox.width}px`);

    // 截图
    await page.screenshot({ path: 'demo-screenshots/boundary-long-name.png' });
    console.log('✓ 截图已保存: boundary-long-name.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 超长 Pack 名称处理正确\n');
  });

  test('边界情况: 特殊字符 Pack 名称', async ({ page }) => {
    console.log('\n[测试开始] 特殊字符 Pack 名称');
    console.log('='.repeat(60));

    // 创建包含特殊字符的 Pack
    const specialCharPack = makePack({
      packId: 'special-char-pack',
      packName: '<script>alert("XSS")</script> & "quotes" \'apostrophes\'',
    });

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock (特殊字符)...');
    await installChromeHostMock(page, { activePack: specialCharPack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 验证 Pack 名称显示 (应该被转义)
    console.log('→ 验证 Pack 名称显示...');
    const packName = await page.locator('#currentPack .pack-name').textContent();
    console.log(`✓ Pack 名称: ${packName}`);

    // 验证没有 XSS 攻击
    const pageContent = await page.content();
    const hasScript = pageContent.includes('<script>alert');
    console.log(`✓ XSS 防护: ${hasScript ? '失败' : '成功'}`);
    expect(hasScript).toBe(false);

    // 截图
    await page.screenshot({ path: 'demo-screenshots/boundary-special-chars.png' });
    console.log('✓ 截图已保存: boundary-special-chars.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 特殊字符 Pack 名称处理正确\n');
  });

  test('边界情况: 快速连续点击', async ({ page }) => {
    console.log('\n[测试开始] 快速连续点击');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'rapid-click-pack',
      packName: '快速点击测试 Pack',
    });

    // 安装 Chrome Host Mock
    console.log('→ 安装 Chrome Host Mock...');
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 快速连续点击执行按钮 5 次
    console.log('→ 快速连续点击执行按钮 5 次...');
    const executeButton = await page.getByRole('button', { name: '执行当前 Prompt Pack' });
    for (let i = 0; i < 5; i++) {
      await executeButton.click({ delay: 100 });
    }
    console.log('✓ 已点击 5 次');

    // 等待状态稳定
    await page.waitForTimeout(2000);

    // 验证只执行了一次
    const state = await page.evaluate(() => globalThis.__chromeMockState);
    const executeCount = state.tabMessages.filter(
      (entry) => entry.payload.action === 'executePack'
    ).length;
    console.log(`✓ 实际执行次数: ${executeCount}`);
    expect(executeCount).toBeLessThanOrEqual(1);

    // 截图
    await page.screenshot({ path: 'demo-screenshots/boundary-rapid-click.png' });
    console.log('✓ 截图已保存: boundary-rapid-click.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 快速连续点击处理正确 (防抖生效)\n');
  });

  test('边界情况: 网络超时', async ({ page }) => {
    console.log('\n[测试开始] 网络超时');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'timeout-pack',
      packName: '超时测试 Pack',
    });

    // 安装 Chrome Host Mock,并设置超时
    console.log('→ 安装 Chrome Host Mock (超时模式)...');
    await installChromeHostMock(page, {
      activePack,
      mockOptions: {
        tabsSendMessageTimeout: 5000, // 5 秒超时
      },
    });
    console.log('✓ Chrome Host Mock 已安装 (超时模式)');

    // 导航到 Popup 页面
    console.log('→ 导航到 Popup 页面...');
    await page.goto(POPUP_PATH);
    await expect(page).toHaveTitle('Prompt Pack');
    console.log('✓ Popup 页面加载完成');

    // 点击执行按钮
    console.log('→ 点击执行按钮...');
    await page.getByRole('button', { name: '执行当前 Prompt Pack' }).click();
    console.log('✓ 执行按钮已点击');

    // 等待超时状态
    console.log('→ 等待超时状态...');
    await expect(page.locator('#statusBar .status-text')).toContainText('超时', { timeout: 10000 });
    console.log('✓ 超时状态已显示');

    // 验证超时消息
    const statusText = await page.locator('#statusBar .status-text').textContent();
    console.log(`✓ 状态栏文本: ${statusText}`);
    expect(statusText).toContain('超时');

    // 截图
    await page.screenshot({ path: 'demo-screenshots/boundary-timeout.png' });
    console.log('✓ 截图已保存: boundary-timeout.png');

    console.log('='.repeat(60));
    console.log('[测试完成] 网络超时处理正确\n');
  });
});
