/**
 * 混合模式测试 - Chrome并发 + Backend共识
 *
 * 测试流程：
 * 1. 打开多个AI平台标签页（Kimi + ChatGLM）
 * 2. Content Script注入提示词
 * 3. 收集真实AI响应
 * 4. Backend共识提取 + 灵魂注入
 * 5. 返回个性化内容
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/chromium-hybrid-' + Date.now();

// 测试平台列表
const TEST_PLATFORMS = [
  'https://kimi.com',
  'https://chatglm.cn'
];

async function testHybridMode() {
  console.log('=== 混合模式完整测试 ===');
  console.log('扩展路径:', EXTENSION_PATH);
  console.log('测试平台:', TEST_PLATFORMS.join(', '));

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  console.log('\n浏览器已启动');

  // 打开多个AI平台标签页
  const pages = [];
  for (const url of TEST_PLATFORMS) {
    console.log(`打开平台: ${url}`);
    const page = await browser.newPage();

    // 监听console日志
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('[Prompt Pack]') || text.includes('Error')) {
        console.log(`[${url}] ${text}`);
      }
    });

    await page.goto(url);
    pages.push({ url, page });
    await new Promise(r => setTimeout(r, 3000)); // 等待Content Script注入
  }

  console.log('\n已打开平台数量:', pages.length);

  // 等待用户登录/准备好AI界面
  console.log('\n等待10秒确保AI界面可用...');
  console.log('（如果需要登录，请手动登录）');
  await new Promise(r => setTimeout(r, 10000));

  // 选择一个页面执行测试
  const testPage = pages[0].page;

  // 执行完整工作流测试
  console.log('\n执行完整工作流测试...');
  const result = await testPage.evaluate(async () => {
    return new Promise((resolve) => {
      // 设置结果监听器
      window.addEventListener('message', (event) => {
        if (event.data.type === 'PROMPT_PACK_RESULT') {
          resolve(event.data);
        }
      });

      // 发送测试请求
      console.log('[Test] 发送SEND_TO_AI请求');
      window.postMessage({
        type: 'PROMPT_PACK_TEST',
        prompt: '人工智能对未来工作的影响',
        config: {
          soulProfile: 'luoyonghao',
          timeout: 90000  // 真实AI响应需要更长超时
        }
      }, '*');

      // 120秒超时（真实AI响应）
      setTimeout(() => resolve({
        type: 'PROMPT_PACK_RESULT',
        result: { success: false, error: 'Timeout waiting for real AI responses' }
      }), 120000);
    });
  });

  // 输出结果
  console.log('\n=== 测试结果 ===');
  console.log(JSON.stringify(result, null, 2));

  if (result.result?.success) {
    const stats = result.result.stats;
    console.log('\n✅ 工作流执行成功！');
    console.log(`- 使用平台数: ${stats?.platformsUsed || 0}`);
    console.log(`- 共识模式: ${stats?.consensusMode || 'unknown'}`);
    console.log(`- 灵魂风格: ${stats?.soulProfile || 'unknown'}`);
    console.log(`- 工作流类型: ${stats?.workflow || 'unknown'}`);
    console.log(`- 执行时长: ${result.result.duration || 0}ms`);

    if (result.result.finalContent) {
      console.log('\n📄 最终内容预览:');
      const preview = result.result.finalContent.substring(0, 200);
      console.log(preview + '...');
    }
  } else {
    console.log('\n❌ 测试失败:', result.result?.error || result.error);
  }

  console.log('\n浏览器保持打开 180 秒...');
  await new Promise(r => setTimeout(r, 180000));

  await browser.close();
  console.log('测试完成');
}

testHybridMode().catch(err => {
  console.error('测试失败:', err.message);
  console.error(err.stack);
});