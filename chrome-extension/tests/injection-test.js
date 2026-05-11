/**
 * 注入能力测试 - 验证Chrome能否向真实AI网站注入提示词
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/chromium-inject-test-' + Date.now();

async function testInjection() {
  console.log('=== 注入能力测试 ===');

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  // 打开Kimi
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

  // 检查页面状态
  const state = await page.evaluate(() => {
    // 尝试获取Content Script暴露的getPageState
    if (window.__promptPackState) {
      return window.__promptPackState;
    }

    // 手动检查输入框
    const textarea = document.querySelector('textarea');
    const contenteditable = document.querySelector('div[contenteditable="true"]');

    return {
      hasTextarea: !!textarea,
      hasContenteditable: !!contenteditable,
      textareaVisible: textarea ? textarea.offsetParent !== null : false,
      contenteditableVisible: contenteditable ? contenteditable.offsetParent !== null : false
    };
  });

  console.log('页面状态:', JSON.stringify(state, null, 2));

  // 尝试注入提示词（通过postMessage桥接）
  console.log('\n尝试注入提示词...');
  const injectResult = await page.evaluate(async () => {
    try {
      // 使用postMessage桥接（页面 → Content Script → Service Worker）
      return new Promise((resolve) => {
        // 监听结果
        window.addEventListener('message', (event) => {
          if (event.data.type === 'PROMPT_PACK_INJECT_RESULT') {
            resolve(event.data.result);
          }
        });

        // 发送注入请求
        window.postMessage({
          type: 'PROMPT_PACK_INJECT',  // 新消息类型
          text: '你好，请告诉我人工智能对未来工作的影响'
        }, '*');

        // 5秒超时
        setTimeout(() => resolve({ success: false, error: 'Timeout' }), 5000);
      });
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  console.log('注入结果:', JSON.stringify(injectResult, null, 2));

  // 等待观察
  console.log('\n浏览器保持打开 60 秒，请观察输入框...');
  await new Promise(r => setTimeout(r, 60000));

  await browser.close();
  console.log('测试完成');
}

testInjection().catch(err => console.error('测试失败:', err));