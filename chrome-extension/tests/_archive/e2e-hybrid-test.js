/**
 * 端到端混合模式测试
 *
 * 完整流程：
 * 1. 打开AI平台（Kimi）
 * 2. 注入提示词 + 发送
 * 3. 等待真实AI响应
 * 4. Backend共识提取 + 灵魂注入
 * 5. 返回个性化内容
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/chromium-e2e-' + Date.now();

async function testEndToEnd() {
  console.log('=== 端到端混合模式测试 ===');
  console.log('目标：验证真实AI响应 + Backend处理完整流程\n');

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  const page = await browser.newPage();

  // 监听所有Console日志
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[Prompt Pack]') || text.includes('[Service Worker]') || text.includes('Error')) {
      console.log('[Console]', text);
    }
  });

  console.log('打开 Kimi...');
  await page.goto('https://kimi.com');
  await new Promise(r => setTimeout(r, 5000));

  // 检查是否需要登录
  const loginCheck = await page.evaluate(() => {
    const loginButton = document.querySelector('button[class*="login"]') ||
                        document.querySelector('a[href*="login"]');
    const chatInput = document.querySelector('div[contenteditable="true"]');
    return {
      needsLogin: !!loginButton && !chatInput,
      hasChatInput: !!chatInput
    };
  });

  console.log('页面状态:', JSON.stringify(loginCheck, null, 2));

  if (!loginCheck.hasChatInput) {
    console.log('\n⚠️  请手动登录 Kimi（等待60秒）...');
    await new Promise(r => setTimeout(r, 60000));
  }

  // 执行完整工作流
  console.log('\n执行 SEND_TO_AI 工作流...');
  const testPrompt = '人工智能对未来工作的影响有哪些？请简要回答。';

  const result = await page.evaluate(async (prompt) => {
    return new Promise((resolve) => {
      // 监听结果
      window.addEventListener('message', (event) => {
        if (event.data.type === 'PROMPT_PACK_RESULT') {
          resolve(event.data);
        }
      });

      // 发送测试请求
      console.log('[Test] 发送请求，提示词:', prompt);
      window.postMessage({
        type: 'PROMPT_PACK_TEST',
        prompt: prompt,
        config: {
          soulProfile: 'luoyonghao',
          timeout: 120000  // 真实AI响应需要更长超时
        }
      }, '*');

      // 180秒超时（包含真实AI响应时间）
      setTimeout(() => resolve({
        type: 'PROMPT_PACK_RESULT',
        result: { success: false, error: 'Timeout (180s) - AI may not have responded' }
      }), 180000);
    });
  }, testPrompt);

  // 输出结果
  console.log('\n========== 测试结果 ==========');

  if (result.result?.success) {
    console.log('\n✅ 工作流执行成功！');

    const stats = result.result.stats;
    console.log('\n执行统计:');
    console.log(`  - 使用平台数: ${stats?.platformsUsed || 0}`);
    console.log(`  - 共识模式: ${stats?.consensusMode || 'unknown'}`);
    console.log(`  - 工作流类型: ${stats?.workflow || 'unknown'}`);
    console.log(`  - 灵魂风格: ${stats?.soulProfile || 'unknown'}`);
    console.log(`  - 执行时长: ${result.result.duration || 0}ms`);

    if (result.result.consensus?.sources) {
      console.log('\n共识来源:');
      result.result.consensus.sources.forEach(src => {
        console.log(`  - ${src.ai}: ${src.response?.substring(0, 50)}...`);
      });
    }

    if (result.result.finalContent) {
      console.log('\n📄 最终个性化内容:');
      console.log('─'.repeat(50));
      console.log(result.result.finalContent);
      console.log('─'.repeat(50));
    }

    // 判断是否为真实响应
    const isRealMode = stats?.consensusMode === 'real_chrome' || stats?.workflow === 'real';
    console.log('\n🏆 业务价值评估:');
    console.log(`  - 真实AI响应: ${isRealMode ? '✅ 是' : '❌ 否 (Mock)'}`);
    console.log(`  - 多平台并发: ${stats?.platformsUsed > 1 ? '✅ 是' : '⚠️  单平台'}`);
    console.log(`  - 灵魂注入: ${result.result.soulInjection?.success ? '✅ 是' : '❌ 否'}`);

  } else {
    console.log('\n❌ 测试失败:', result.result?.error || result.error);
  }

  console.log('\n浏览器保持打开 60 秒...');
  await new Promise(r => setTimeout(r, 60000));

  await browser.close();
  console.log('\n测试完成');
}

testEndToEnd().catch(err => {
  console.error('测试失败:', err.message);
  console.error(err.stack);
});