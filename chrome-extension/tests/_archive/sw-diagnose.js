/**
 * Service Worker Fetch诊断脚本
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/chromium-diag-' + Date.now();

async function diagnose() {
  console.log('=== Service Worker Fetch诊断 ===');

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  // 先打开页面触发Content Script
  const page = await browser.newPage();
  page.on('console', msg => console.log('[Page]', msg.text()));

  await page.goto('https://kimi.com');
  console.log('Kimi已打开，等待Content Script...');
  await new Promise(r => setTimeout(r, 3000));

  // 通过Content Script触发Service Worker启动
  // 发送一个简单消息来激活Service Worker
  const result = await page.evaluate(async () => {
    try {
      // 先测试直接fetch（页面context）
      const pageFetchTest = await fetch('http://127.0.0.1:8000/health');
      const pageFetchData = await pageFetchTest.json();

      // 然后测试通过Extension的消息
      const extResult = await chrome.runtime.sendMessage({
        type: 'SEND_TO_AI',
        prompt: '知识付费',
        config: { soulProfile: 'luoyonghao' }
      });

      return {
        pageFetch: { success: true, data: pageFetchData },
        extResult: extResult
      };
    } catch (error) {
      return { error: error.message, stack: error.stack };
    }
  });

  console.log('\n=== 诊断结果 ===');
  console.log(JSON.stringify(result, null, 2));

  // 等待Service Worker日志
  console.log('\n等待Service Worker日志...');
  await new Promise(r => setTimeout(r, 5000));

  // 检查Service Worker
  const bgPages = browser.backgroundPages();
  console.log('Background Pages:', bgPages.length);

  if (bgPages.length > 0) {
    const bgPage = bgPages[0];
    bgPage.on('console', msg => console.log('[Service Worker]', msg.text()));

    // 在Service Worker中直接测试
    const swTest = await bgPage.evaluate(async () => {
      try {
        console.log('[SW] Testing fetch to localhost:8000');
        const response = await fetch('http://127.0.0.1:8000/health');
        console.log('[SW] Fetch response status:', response.status);
        const data = await response.json();
        console.log('[SW] Fetch data:', JSON.stringify(data));
        return { success: true, data };
      } catch (error) {
        console.error('[SW] Fetch error:', error.message);
        return { success: false, error: error.message };
      }
    });
    console.log('Service Worker Fetch:', JSON.stringify(swTest, null, 2));
  }

  console.log('\n浏览器保持打开 60 秒...');
  await new Promise(r => setTimeout(r, 60000));
  await browser.close();
}

diagnose().catch(err => console.error('诊断失败:', err));