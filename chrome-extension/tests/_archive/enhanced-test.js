/**
 * 增强版测试脚本 - 重新加载扩展并测试
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/chromium-test-' + Date.now();

async function test() {
  console.log('=== 增强版扩展测试 ===');
  console.log('扩展路径:', EXTENSION_PATH);
  console.log('用户目录:', USER_DATA_DIR);

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  console.log('浏览器已启动');

  // 先打开页面触发Service Worker
  const page = await browser.newPage();
  page.on('console', msg => {
    console.log('[Page]', msg.text());
  });

  await page.goto('https://kimi.com');
  console.log('Kimi页面已打开');

  // 等待Content Script注入和Service Worker启动
  await new Promise(r => setTimeout(r, 5000));

  // 获取Service Worker页面
  let backgroundPages = browser.backgroundPages();
  console.log('Background Pages:', backgroundPages.length);

  // 如果没有，再等待一下
  if (backgroundPages.length === 0) {
    console.log('等待Service Worker启动...');
    await new Promise(r => setTimeout(r, 3000));
    backgroundPages = browser.backgroundPages();
    console.log('Background Pages (retry):', backgroundPages.length);
  }

  if (backgroundPages.length > 0) {
    const bgPage = backgroundPages[0];

    // 监听Service Worker console日志
    bgPage.on('console', msg => {
      console.log('[Service Worker]', msg.text());
    });

    // 检查backendClient状态
    const status = await bgPage.evaluate(() => {
      return {
        hasBackendClient: typeof globalThis.backendClient !== 'undefined',
        backendClientUrl: globalThis.backendClient?.baseUrl,
        hasServiceWorkerBackend: typeof backendClient !== 'undefined' && backendClient !== null
      };
    });
    console.log('Backend Client状态:', JSON.stringify(status, null, 2));

    // 直接在Service Worker中测试fetch
    const fetchTest = await bgPage.evaluate(async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/health');
        const data = await response.json();
        return { success: true, data };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    console.log('Service Worker Fetch测试:', JSON.stringify(fetchTest, null, 2));
  }

  console.log('\n请在Kimi页面Console执行测试代码:');
  console.log('window.postMessage({ type: "PROMPT_PACK_TEST", prompt: "知识付费", config: { soulProfile: "luoyonghao" } }, "*");');
  console.log('\n浏览器保持打开 300 秒...');

  await new Promise(r => setTimeout(r, 300000));

  await browser.close();
  console.log('测试完成');
}

test().catch(err => {
  console.error('测试失败:', err.message);
  console.error(err.stack);
});