/**
 * 多平台 Pack 执行测试
 * 测试所有支持的 AI 平台
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/multi-platform-test-' + Date.now();

// 支持的平台列表
const PLATFORMS = [
  { id: 'chatglm.cn', name: '智谱清言', url: 'https://chatglm.cn', loginFree: true },
  { id: 'yuanbao.tencent.com', name: '腾讯元宝', url: 'https://yuanbao.tencent.com/chat/', loginFree: true },
  { id: 'longcat.chat', name: 'LongCat', url: 'https://longcat.chat', loginFree: true },
  { id: 'kimi.com', name: 'Kimi', url: 'https://kimi.com', loginFree: false },  // 需登录
  { id: 'qianwen.com', name: '千问', url: 'https://qianwen.com', loginFree: false },  // 需登录
  { id: 'gemini.google.com', name: 'Gemini', url: 'https://gemini.google.com', loginFree: false },
  { id: 'claude.ai', name: 'Claude', url: 'https://claude.ai', loginFree: false },
  { id: 'chatgpt.com', name: 'ChatGPT', url: 'https://chatgpt.com', loginFree: false }
];

async function testAllPlatforms() {
  console.log('=== 多平台 Pack 执行测试 ===\n');
  console.log('支持的平台:', PLATFORMS.map(p => p.name).join(', '));
  console.log('\n免登录平台:', PLATFORMS.filter(p => p.loginFree).map(p => p.name).join(', '));

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  // 测试结果收集
  const results = [];

  // 测试免登录平台
  console.log('\n========================================');
  console.log('  测试免登录平台');
  console.log('========================================\n');

  for (const platform of PLATFORMS.filter(p => p.loginFree)) {
    const result = await testPlatform(browser, platform);
    results.push(result);
  }

  // 打开需要登录的平台（供手动测试）
  console.log('\n========================================');
  console.log('  需登录平台（手动测试）');
  console.log('========================================\n');

  for (const platform of PLATFORMS.filter(p => !p.loginFree)) {
    console.log(`- ${platform.name}: ${platform.url}`);
    // 可以选择打开但跳过自动测试
    // const page = await browser.newPage();
    // await page.goto(platform.url);
  }

  // 输出测试结果
  console.log('\n========================================');
  console.log('  测试结果汇总');
  console.log('========================================\n');

  results.forEach(r => {
    const status = r.success ? '✅' : '❌';
    console.log(`${status} ${r.platform.name}: ${r.message}`);
  });

  console.log('\n浏览器保持打开 300 秒，可手动测试需登录平台...\n');

  await new Promise(r => setTimeout(r, 300000));

  await browser.close();
  console.log('测试完成');
}

async function testPlatform(browser, platform) {
  console.log(`\n--- 测试 ${platform.name} ---`);

  const result = {
    platform: platform,
    success: false,
    message: '',
    details: {}
  };

  try {
    const page = await browser.newPage();

    // 监听 console
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('[Prompt Pack]') || text.includes('[MultiPlatform]')) {
        console.log(`  [${platform.name}] ${text}`);
      }
    });

    // 打开平台
    console.log(`  打开 ${platform.url}...`);
    await page.goto(platform.url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);

    // 检测输入框
    console.log(`  检测输入框...`);
    const inputSelectors = [
      'textarea',
      'div[contenteditable="true"]',
      '[role="textbox"]',
      'input[type="text"]'
    ];

    let inputFound = false;
    let inputSelector = null;

    for (const selector of inputSelectors) {
      const input = await page.$(selector);
      if (input) {
        const visible = await input.isVisible();
        if (visible) {
          inputFound = true;
          inputSelector = selector;
          console.log(`  ✅ 找到输入框: ${selector}`);
          break;
        }
      }
    }

    if (!inputFound) {
      result.message = '未找到输入框';
      result.details.inputFound = false;
      await page.close();
      return result;
    }

    result.details.inputFound = true;
    result.details.inputSelector = inputSelector;

    // 测试注入
    console.log(`  测试文本注入...`);
    const testText = '这是来自 Prompt Pack 的测试消息';

    // 尝试填充输入框
    const input = await page.$(inputSelector);
    await input.focus();

    if (inputSelector.includes('textarea') || inputSelector.includes('input')) {
      await input.fill(testText);
    } else {
      // contenteditable
      await page.evaluate((sel, text) => {
        const el = document.querySelector(sel);
        if (el) {
          el.focus();
          document.execCommand('selectAll', false, null);
          document.execCommand('delete', false, null);
          document.execCommand('insertText', false, text);
        }
      }, inputSelector, testText);
    }

    await page.waitForTimeout(1000);

    // 检查是否成功注入
    let injectedContent = '';
    if (inputSelector.includes('textarea') || inputSelector.includes('input')) {
      injectedContent = await input.inputValue();
    } else {
      injectedContent = await input.textContent();
    }

    if (injectedContent.includes(testText) || injectedContent.includes('Prompt Pack')) {
      console.log(`  ✅ 文本注入成功`);
      result.details.injectionSuccess = true;
      result.success = true;
      result.message = '注入成功';
    } else {
      console.log(`  ❌ 文本注入失败，内容: "${injectedContent.substring(0, 30)}"`);
      result.details.injectionSuccess = false;
      result.message = '注入失败';
    }

    // 不发送，只是测试注入
    console.log(`  清空输入框（不发送）...`);
    await input.fill('');
    await page.waitForTimeout(500);

    await page.close();

  } catch (error) {
    console.log(`  ❌ 错误: ${error.message}`);
    result.message = `错误: ${error.message}`;
    result.details.error = error.message;
  }

  return result;
}

testAllPlatforms().catch(err => console.error('测试错误:', err));