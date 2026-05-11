const { test, expect } = require('@playwright/test');

/**
 * 简单 GUI 演示
 * 快速演示基本的浏览器自动化操作
 */

test('简单演示: 页面加载和输入', async ({ page }) => {
  console.log('\n[演示开始] 页面加载和输入操作');
  console.log('=' .repeat(60));

  // 设置视口大小
  await page.setViewportSize({ width: 1280, height: 720 });
  console.log('✓ 设置浏览器窗口大小: 1280x720');

  // 导航到测试页面
  console.log('→ 正在导航到 example.com...');
  await page.goto('https://example.com', { waitUntil: 'networkidle' });
  console.log('✓ 页面加载完成');

  // 获取页面标题
  const title = await page.title();
  console.log(`✓ 页面标题: ${title}`);

  // 查找标题元素
  const h1 = await page.locator('h1');
  const h1Text = await h1.textContent();
  console.log(`✓ H1 文本: ${h1Text}`);

  // 截图
  await page.screenshot({ path: 'demo-screenshots/simple-demo-01.png' });
  console.log('✓ 截图已保存: demo-screenshots/simple-demo-01.png');

  // 查找链接
  const link = await page.locator('a').first();
  const linkText = await link.textContent();
  console.log(`✓ 找到链接: ${linkText}`);

  // 点击链接
  console.log('→ 点击链接...');
  await link.click();
  await page.waitForLoadState('networkidle');
  console.log('✓ 链接点击完成');

  // 获取新页面标题
  const newTitle = await page.title();
  console.log(`✓ 新页面标题: ${newTitle}`);

  // 截图
  await page.screenshot({ path: 'demo-screenshots/simple-demo-02.png' });
  console.log('✓ 截图已保存: demo-screenshots/simple-demo-02.png');

  console.log('=' .repeat(60));
  console.log('[演示完成] 所有操作成功执行\n');
});
