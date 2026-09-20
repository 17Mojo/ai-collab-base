/**
 * 调试版测试 - 显示Service Worker详细日志
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/chromium-debug-' + Date.now();

async function debugTest() {
  console.log('=== 调试版测试 ===\n');

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  const page = await browser.newPage();
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[Prompt Pack]')) {
      console.log('[Console]', text);
    }
  });

  console.log('打开 Kimi...');
  await page.goto('https://kimi.com');
  await new Promise(r => setTimeout(r, 5000));

  // 执行测试
  console.log('\n执行测试...');
  const result = await page.evaluate(() => {
    return new Promise(resolve => {
      window.addEventListener('message', (e) => {
        if (e.data.type === 'PROMPT_PACK_RESULT') {
          resolve(e.data);
        }
      });
      window.postMessage({
        type: 'PROMPT_PACK_TEST',
        prompt: 'AI测试',
        config: { soulProfile: 'luoyonghao', timeout: 30000 }
      }, '*');
      setTimeout(() => resolve({ error: 'Timeout' }), 35000);
    });
  });

  console.log('\n=== 结果分析 ===');
  console.log(JSON.stringify(result, null, 2));

  // 提取调试信息
  if (result.result?.result?.debug) {
    const debug = result.result.result.debug;
    console.log('\n=== 调试信息 ===');
    console.log('找到的标签页数量:', debug.foundTabsCount);
    console.log('标签页详情:', JSON.stringify(debug.foundTabs));
    console.log('真实响应数量:', debug.realResponsesCount);
    console.log('Backend状态:', debug.backendClientStatus);
  }

  await new Promise(r => setTimeout(r, 20000));
  await browser.close();
}

debugTest().catch(err => console.error('错误:', err));