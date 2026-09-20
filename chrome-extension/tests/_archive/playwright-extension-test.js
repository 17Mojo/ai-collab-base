/**
 * Playwright 测试脚本 - 测试 Prompt Pack 扩展
 * 使用 launchPersistentContext 加载扩展
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/prompt-pack-test-' + Date.now();

async function testExtension() {
  console.log('=== Playwright 扩展测试 ===');
  console.log('扩展路径:', EXTENSION_PATH);
  console.log('用户数据目录:', USER_DATA_DIR);

  // 清理旧目录
  const fs = require('fs');
  if (fs.existsSync(USER_DATA_DIR)) {
    fs.rmSync(USER_DATA_DIR, { recursive: true });
  }

  console.log('\n启动带扩展的 Chrome...');

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    channel: 'chrome',  // 使用系统 Chrome
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`,
      '--enable-extensions'
    ]
  });

  console.log('浏览器已启动');

  // 等待扩展加载
  await new Promise(r => setTimeout(r, 3000));

  // 检查 Background Pages
  let backgroundPages = browser.backgroundPages();
  console.log('Background Pages 数量:', backgroundPages.length);

  // 打开扩展管理页面检查
  const extPage = await browser.newPage();
  await extPage.goto('chrome://extensions/');
  await extPage.waitForTimeout(2000);

  const extStatus = await extPage.evaluate(() => {
    const items = document.querySelectorAll('extensions-item');
    const exts = [];
    items.forEach(item => {
      exts.push({
        name: item.querySelector('#name')?.textContent,
        enabled: item.getAttribute('data-enabled') === 'true'
      });
    });
    return exts;
  });

  console.log('已加载扩展:', JSON.stringify(extStatus, null, 2));

  // 关闭扩展页面
  await extPage.close();

  // 打开 Kimi 测试
  console.log('\n打开 Kimi 页面...');
  const page = await browser.newPage();
  await page.goto('https://kimi.com');

  console.log('等待 Content Script 注入...');
  await page.waitForTimeout(5000);

  // 检查页面日志
  const pageContent = await page.content();
  console.log('页面加载状态:', pageContent.includes('Kimi') ? '正常' : '异常');

  // 在扩展上下文中执行测试
  backgroundPages = browser.backgroundPages();
  if (backgroundPages.length > 0) {
    const bgPage = backgroundPages[0];
    console.log('\n在 Background Page 中测试...');

    const bgTest = await bgPage.evaluate(() => {
      return {
        hasBackendClient: typeof globalThis.backendClient !== 'undefined',
        hasMultiPlatformExecutor: typeof globalThis.multiPlatformExecutor !== 'undefined'
      };
    });
    console.log('Background Page 状态:', JSON.stringify(bgTest, null, 2));
  }

  // 保持浏览器打开
  console.log('\n浏览器将保持打开 60 秒，请手动检查...');
  await page.waitForTimeout(60000);

  await browser.close();
  console.log('测试完成');
}

testExtension().catch(err => {
  console.error('测试失败:', err.message);
  console.error(err.stack);
});