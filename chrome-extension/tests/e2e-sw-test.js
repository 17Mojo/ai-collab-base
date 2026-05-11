/**
 * 增强版端到端测试 - 捕获Service Worker日志
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/chromium-e2e-sw-' + Date.now();

async function testWithSWLogs() {
  console.log('=== 增强版端到端测试（含Service Worker日志） ===\n');

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  // 打开页面触发Content Script
  const page = await browser.newPage();
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[Prompt Pack]')) {
      console.log('[Page]', text);
    }
  });

  console.log('打开 Kimi...');
  await page.goto('https://kimi.com');
  await new Promise(r => setTimeout(r, 5000));

  // 检查Service Worker
  let bgPages = browser.backgroundPages();
  console.log('Background Pages (初始):', bgPages.length);

  // 发送消息激活Service Worker
  console.log('\n发送激活消息...');
  const activateResult = await page.evaluate(() => {
    return new Promise(resolve => {
      window.addEventListener('message', (e) => {
        if (e.data.type === 'PROMPT_PACK_RESULT') {
          resolve(e.data);
        }
      });
      window.postMessage({
        type: 'PROMPT_PACK_TEST',
        prompt: '测试激活',
        config: { soulProfile: 'luoyonghao', timeout: 30000 }
      }, '*');
      setTimeout(() => resolve({ error: 'Timeout' }), 35000);
    });
  });

  console.log('激活结果:', JSON.stringify(activateResult, null, 2));

  // 再次检查Service Worker
  bgPages = browser.backgroundPages();
  console.log('\nBackground Pages (激活后):', bgPages.length);

  if (bgPages.length > 0) {
    const swPage = bgPages[0];

    // 监听Service Worker日志
    swPage.on('console', msg => {
      console.log('[Service Worker]', msg.text());
    });

    // 获取Service Worker状态
    try {
      const swState = await swPage.evaluate(() => {
        return {
          hasBackendClient: typeof backendClient !== 'undefined',
          backendClientUrl: backendClient?.baseUrl,
          hasMultiPlatformExecutor: typeof multiPlatformExecutor !== 'undefined',
          adapterCount: Object.keys(adapters || {}).length
        };
      });
      console.log('Service Worker状态:', JSON.stringify(swState, null, 2));
    } catch (e) {
      console.log('无法获取SW状态:', e.message);
    }
  }

  // 执行完整测试
  console.log('\n执行完整工作流测试...');
  const testPrompt = 'AI对教育的影响';

  const result = await page.evaluate(async (prompt) => {
    return new Promise(resolve => {
      window.addEventListener('message', (e) => {
        if (e.data.type === 'PROMPT_PACK_RESULT') {
          resolve(e.data);
        }
      });
      window.postMessage({
        type: 'PROMPT_PACK_TEST',
        prompt: prompt,
        config: { soulProfile: 'luoyonghao', timeout: 60000 }
      }, '*');
      setTimeout(() => resolve({ result: { success: false, error: 'Timeout 60s' }}), 65000);
    });
  }, testPrompt);

  console.log('\n========== 最终结果 ==========');
  console.log(JSON.stringify(result, null, 2));

  // 分析结果
  if (result.result?.success) {
    const stats = result.result.stats || {};
    const isReal = stats.consensusMode === 'real_chrome';

    console.log('\n📊 业务价值判定:');
    console.log(`  真实AI响应: ${isReal ? '✅' : '❌ Mock'}`);
    console.log(`  多平台并发: ${stats.platformsUsed > 1 ? '✅' : '⚠️ 单平台'}`);
    console.log(`  灵魂注入: ${result.result.soulInjection?.success ? '✅' : '❌'}`);

    if (result.result.finalContent) {
      console.log('\n📝 最终内容:');
      console.log(result.result.finalContent.substring(0, 300) + '...');
    }
  }

  console.log('\n浏览器保持打开 30 秒...');
  await new Promise(r => setTimeout(r, 30000));
  await browser.close();
  console.log('测试完成');
}

testWithSWLogs().catch(err => console.error('错误:', err));