/**
 * PackExecutor集成验证测试
 * 验证Pack作为核心执行引擎的完整工作流
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/pack-test-' + Date.now();

async function testPackExecutorIntegration() {
  console.log('=== PackExecutor集成验证测试 ===\n');
  console.log('目标：验证Pack作为核心执行引擎\n');

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

  // 测试1: 列出可用Pack
  console.log('\n=== 测试1: 列出可用Pack ===');
  const packListResult = await page.evaluate(() => {
    return new Promise(resolve => {
      window.addEventListener('message', (e) => {
        if (e.data.type === 'PROMPT_PACK_LIST_RESULT') {
          resolve(e.data);
        }
      });
      window.postMessage({ type: 'PROMPT_PACK_LIST' }, '*');
      setTimeout(() => resolve({ error: 'Timeout' }), 5000);
    });
  });
  console.log('可用Pack:', JSON.stringify(packListResult.packs));

  // 测试2: 使用默认Pack执行
  console.log('\n=== 测试2: 使用默认Pack(knowledge-query)执行 ===');
  const testPrompt = 'AI是什么？请简短回答';

  const packResult = await page.evaluate(async (prompt) => {
    return new Promise(resolve => {
      window.addEventListener('message', (e) => {
        if (e.data.type === 'PROMPT_PACK_RESULT') {
          resolve(e.data);
        }
      });

      // 使用PROMPT_PACK_TEST（现在通过PackExecutor执行）
      window.postMessage({
        type: 'PROMPT_PACK_TEST',
        prompt: prompt,
        config: { soulProfile: 'luoyonghao' }
      }, '*');

      setTimeout(() => resolve({ error: 'Timeout 35s' }), 35000);
    });
  }, testPrompt);

  console.log('\n========== Pack执行结果 ==========');
  console.log(JSON.stringify(packResult, null, 2));

  // 分析结果
  if (packResult.result?.success) {
    const result = packResult.result.result;

    console.log('\n📊 Pack执行分析:');
    console.log(`  Pack ID: ${result.packId}`);
    console.log(`  Pack名称: ${result.packName}`);
    console.log(`  执行成功: ${result.success ? '✅' : '❌'}`);
    console.log(`  步骤数量: ${result.steps?.length || 0}`);
    console.log(`  总耗时: ${result.totalDuration}ms`);

    if (result.steps) {
      console.log('\n📝 执行步骤详情:');
      result.steps.forEach((step, i) => {
        console.log(`  步骤${i + 1}: ${step.stepName}`);
        console.log(`    - 类型: ${step.type}`);
        console.log(`    - 成功: ${step.success ? '✅' : '❌'}`);
        console.log(`    - 耗时: ${step.duration}ms`);
        if (step.mode) {
          console.log(`    - 模式: ${step.mode}`);
        }
      });
    }

    if (result.finalContent) {
      console.log('\n📄 最终个性化内容:');
      console.log('─'.repeat(50));
      console.log(result.finalContent.substring(0, 200));
      console.log('─'.repeat(50));
    }

    // 关键验证
    const usesPackExecutor = result.packId !== undefined;
    const usesRealAI = result.mode === 'real_chrome';
    const hasSoulInjection = result.soulInjection?.success;

    console.log('\n🎯 PackExecutor集成验证:');
    console.log(`  通过Pack执行: ${usesPackExecutor ? '✅ 是' : '❌ 否（直接调用）'}`);
    console.log(`  真实AI响应: ${usesRealAI ? '✅ 是' : '❌ Mock'}`);
    console.log(`  Soul注入: ${hasSoulInjection ? '✅ 是' : '❌'}`);

    if (usesPackExecutor && usesRealAI) {
      console.log('\n🎉🎉🎉 PackExecutor集成成功！Pack已成为核心执行引擎！');
    }
  } else {
    console.log('\n❌ 测试失败:', packResult.error || packResult.result?.error);
  }

  console.log('\n浏览器保持打开 30 秒...');
  await new Promise(r => setTimeout(r, 30000));
  await browser.close();
  console.log('\n测试完成');
}

testPackExecutorIntegration().catch(err => console.error('错误:', err));