/**
 * 最终测试 - CORS修复后
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/chromium-final-' + Date.now();

async function finalTest() {
  console.log('=== CORS修复后测试 ===');

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
    if (text.includes('[Prompt Pack]') || text.includes('error') || text.includes('Error')) {
      console.log('[Console]', text);
    }
  });

  await page.goto('https://kimi.com');
  console.log('Kimi已打开');
  await new Promise(r => setTimeout(r, 5000));

  // 执行完整测试
  const result = await page.evaluate(async () => {
    return new Promise((resolve) => {
      // 设置结果监听器
      window.addEventListener('message', (event) => {
        if (event.data.type === 'PROMPT_PACK_RESULT') {
          resolve(event.data);
        }
      });

      // 发送测试请求
      window.postMessage({
        type: 'PROMPT_PACK_TEST',
        prompt: '知识付费',
        config: { soulProfile: 'luoyonghao' }
      }, '*');

      // 30秒超时
      setTimeout(() => resolve({ error: 'Timeout waiting for result' }), 30000);
    });
  });

  console.log('\n=== 测试结果 ===');
  console.log(JSON.stringify(result, null, 2));

  if (result.result?.success) {
    console.log('\n✅ 测试成功！完整工作流已验证：');
    console.log('- Consensus生成:', result.result.consensus ? '完成' : '失败');
    console.log('- Soul注入:', result.result.soulInjection ? '完成' : '失败');
    console.log('- 最终内容:', result.result.finalContent ? '生成' : '未生成');
  } else {
    console.log('\n❌ 测试失败:', result.error || result.result?.error);
  }

  console.log('\n浏览器保持打开 120 秒...');
  await new Promise(r => setTimeout(r, 120000));
  await browser.close();
}

finalTest().catch(err => console.error('测试失败:', err));