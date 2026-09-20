/**
 * ChatGLM完整工作流测试
 * 测试Chrome Extension → Backend → 真实AI响应
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/chatglm-test-' + Date.now();

async function testChatGLMWorkflow() {
  console.log('=== ChatGLM完整工作流测试 ===\n');

  // 启动带扩展的浏览器
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
    if (text.includes('[Prompt Pack]') || text.includes('[Service Worker]') || text.includes('Error')) {
      console.log('[Console]', text);
    }
  });

  console.log('打开 ChatGLM...');
  await page.goto('https://chatglm.cn');
  await new Promise(r => setTimeout(r, 5000));

  // 检查页面状态
  const state = await page.evaluate(() => {
    const textbox = document.querySelector('textbox, textarea, div[contenteditable="true"]');
    return {
      hasInput: !!textbox,
      url: window.location.href
    };
  });
  console.log('页面状态:', JSON.stringify(state));

  // 执行完整工作流测试
  console.log('\n执行 SEND_TO_AI 工作流...');
  const testPrompt = '你好，请简短回答：AI是什么？';

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
        config: { soulProfile: 'luoyonghao', timeout: 30000 }
      }, '*');

      setTimeout(() => resolve({ error: 'Timeout 35s' }), 35000);
    });
  }, testPrompt);

  console.log('\n========== 测试结果 ==========');
  console.log(JSON.stringify(result, null, 2));

  // 分析结果
  if (result.result?.success) {
    const stats = result.result.stats || {};
    const debug = result.result._debug || {};

    console.log('\n📊 业务价值判定:');
    console.log(`  真实AI响应: ${debug.realResponsesCount > 0 ? '✅' : '❌ Mock'}`);
    console.log(`  多平台并发: ${debug.foundTabsCount > 1 ? '✅' : '⚠️ 单平台'}`);
    console.log(`  灵魂注入: ${result.result.soulInjection?.success ? '✅' : '❌'}`);

    if (debug.foundTabs) {
      console.log('\n找到的标签页:');
      debug.foundTabs.forEach(t => {
        console.log(`  - ${t.platformId} (tabId: ${t.tabId})`);
      });
    }

    if (result.result.finalContent) {
      console.log('\n📝 最终个性化内容:');
      console.log('─'.repeat(50));
      console.log(result.result.finalContent.substring(0, 300));
      console.log('─'.repeat(50));
    }
  } else {
    console.log('\n❌ 测试失败:', result.error || result.result?.error);
  }

  console.log('\n浏览器保持打开 30 秒...');
  await new Promise(r => setTimeout(r, 30000));
  await browser.close();
  console.log('\n测试完成');
}

testChatGLMWorkflow().catch(err => console.error('错误:', err));