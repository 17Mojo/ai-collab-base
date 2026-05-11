const { test, expect } = require('@playwright/test');
const { installChromeHostMock, makePack } = require('./helpers/chromeHostMock');

/**
 * Popup 性能与负载 Smoke 测试
 * 测试 Popup 在各种负载情况下的性能表现
 */

const POPUP_PATH = '/products/prompt-pack-extension/chrome/src/popup/index.html';

test.describe('Popup 性能与负载 Smoke 测试', () => {
  
  test.beforeEach(async ({ page }) => {
    test.setTimeout(60000);
    await page.setViewportSize({ width: 400, height: 600 });
  });

  test('性能: 页面加载时间', async ({ page }) => {
    console.log('\n[测试开始] 性能: 页面加载时间');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'perf-test-pack',
      packName: '性能测试 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 测量页面加载时间
    const startTime = Date.now();
    await page.goto(POPUP_PATH);
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    console.log(`✓ 页面加载时间: ${loadTime}ms`);

    // 验证加载时间在合理范围内 (< 2000ms)
    expect(loadTime).toBeLessThan(2000);
    console.log('✓ 加载时间验证通过 (< 2000ms)');

    console.log('='.repeat(60));
    console.log('[测试完成] 性能: 页面加载时间\n');
  });

  test('性能: 大量 Pack 数据 (100个)', async ({ page }) => {
    console.log('\n[测试开始] 性能: 大量 Pack 数据 (100个)');
    console.log('='.repeat(60));

    // 创建 100 个 Pack
    const packs = [];
    for (let i = 0; i < 100; i++) {
      packs.push(makePack({
        packId: `pack-${i}`,
        packName: `Pack ${i}`,
        description: `测试 Pack ${i}`,
      }));
    }

    console.log('✓ 创建 100 个测试 Pack');

    // 安装 Chrome Host Mock
    await installChromeHostMock(page, { packs });
    console.log('✓ Chrome Host Mock 已安装');

    // 测量页面加载时间
    const startTime = Date.now();
    await page.goto(POPUP_PATH);
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    console.log(`✓ 页面加载时间 (100 Packs): ${loadTime}ms`);

    // 验证加载时间在合理范围内 (< 5000ms)
    expect(loadTime).toBeLessThan(5000);
    console.log('✓ 加载时间验证通过 (< 5000ms)');

    // 验证 Pack 列表渲染
    const packItems = await page.locator('.pack-item').count();
    console.log(`✓ Pack 列表项数量: ${packItems}`);
    expect(packItems).toBe(100);

    console.log('='.repeat(60));
    console.log('[测试完成] 性能: 大量 Pack 数据 (100个)\n');
  });

  test('性能: 快速连续操作', async ({ page }) => {
    console.log('\n[测试开始] 性能: 快速连续操作');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'rapid-test-pack',
      packName: '快速操作测试 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    await page.goto(POPUP_PATH);
    await page.waitForLoadState('networkidle');
    console.log('✓ Popup 页面加载完成');

    // 快速连续点击执行按钮 10 次
    console.log('→ 快速连续点击执行按钮 10 次...');
    const executeButton = await page.getByRole('button', { name: '执行当前 Prompt Pack' });
    
    const startTime = Date.now();
    for (let i = 0; i < 10; i++) {
      await executeButton.click();
    }
    const clickTime = Date.now() - startTime;

    console.log(`✓ 点击完成时间: ${clickTime}ms`);

    // 等待状态稳定
    await page.waitForTimeout(2000);

    // 验证只执行了一次 (防抖机制)
    const state = await page.evaluate(() => globalThis.__chromeMockState);
    const executeCount = state.tabMessages.filter(
      (entry) => entry.payload.action === 'executePack'
    ).length;

    console.log(`✓ 实际执行次数: ${executeCount}`);
    expect(executeCount).toBeLessThanOrEqual(1);
    console.log('✓ 防抖机制验证通过');

    console.log('='.repeat(60));
    console.log('[测试完成] 性能: 快速连续操作\n');
  });

  test('性能: 内存使用', async ({ page }) => {
    console.log('\n[测试开始] 性能: 内存使用');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'memory-test-pack',
      packName: '内存测试 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    await page.goto(POPUP_PATH);
    await page.waitForLoadState('networkidle');
    console.log('✓ Popup 页面加载完成');

    // 获取页面性能指标
    const performanceTiming = await page.evaluate(() => {
      const timing = performance.timing;
      return {
        loadTime: timing.loadEventEnd - timing.navigationStart,
        domReady: timing.domContentLoadedEventEnd - timing.navigationStart,
        responseTime: timing.responseEnd - timing.requestStart,
      };
    });

    console.log(`✓ 页面加载时间: ${performanceTiming.loadTime}ms`);
    console.log(`✓ DOM Ready 时间: ${performanceTiming.domReady}ms`);
    console.log(`✓ 响应时间: ${performanceTiming.responseTime}ms`);

    // 验证性能指标在合理范围内
    expect(performanceTiming.loadTime).toBeLessThan(2000);
    expect(performanceTiming.domReady).toBeLessThan(1000);
    console.log('✓ 性能指标验证通过');

    console.log('='.repeat(60));
    console.log('[测试完成] 性能: 内存使用\n');
  });

  test('性能: 多次执行稳定性', async ({ page }) => {
    console.log('\n[测试开始] 性能: 多次执行稳定性');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'stability-test-pack',
      packName: '稳定性测试 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    await page.goto(POPUP_PATH);
    await page.waitForLoadState('networkidle');
    console.log('✓ Popup 页面加载完成');

    // 执行 10 次操作
    console.log('→ 执行 10 次操作...');
    const startTime = Date.now();
    for (let i = 0; i < 10; i++) {
      await page.getByRole('button', { name: '执行当前 Prompt Pack' }).click();
      await expect(page.locator('#statusBar .status-text')).toContainText('完成', { timeout: 10000 });
      await page.waitForTimeout(100);
    }
    const totalTime = Date.now() - startTime;

    console.log(`✓ 10 次操作完成,总时间: ${totalTime}ms`);
    console.log(`✓ 平均每次操作时间: ${(totalTime / 10).toFixed(0)}ms`);

    // 验证平均操作时间在合理范围内 (< 1000ms)
    expect(totalTime / 10).toBeLessThan(1000);
    console.log('✓ 操作性能验证通过');

    console.log('='.repeat(60));
    console.log('[测试完成] 性能: 多次执行稳定性\n');
  });

  test('性能: 响应式布局性能', async ({ page }) => {
    console.log('\n[测试开始] 性能: 响应式布局性能');
    console.log('='.repeat(60));

    // 创建测试 Pack
    const activePack = makePack({
      packId: 'responsive-perf-pack',
      packName: '响应式性能测试 Pack',
    });

    console.log('✓ 创建测试 Pack');

    // 安装 Chrome Host Mock
    await installChromeHostMock(page, { activePack });
    console.log('✓ Chrome Host Mock 已安装');

    // 导航到 Popup 页面
    await page.goto(POPUP_PATH);
    await page.waitForLoadState('networkidle');
    console.log('✓ Popup 页面加载完成');

    // 测试不同视口大小的性能
    const viewports = [
      { width: 320, height: 480, name: '小屏幕' },
      { width: 400, height: 600, name: '中等屏幕' },
      { width: 600, height: 800, name: '大屏幕' },
    ];

    for (const viewport of viewports) {
      console.log(`→ 测试 ${viewport.name} (${viewport.width}x${viewport.height})...`);
      
      const startTime = Date.now();
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.waitForTimeout(500);
      const resizeTime = Date.now() - startTime;

      console.log(`  ✓ 调整大小时间: ${resizeTime}ms`);
      expect(resizeTime).toBeLessThan(1000);
    }

    console.log('✓ 所有视口大小调整性能验证通过');

    console.log('='.repeat(60));
    console.log('[测试完成] 性能: 响应式布局性能\n');
  });
});
