/**
 * 全平台测试 - 包括需登录平台
 * 测试登录弹窗关闭 + Pack 注入
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/full-platform-test-' + Date.now();

const ALL_PLATFORMS = [
  { id: 'chatglm.cn', name: '智谱清言', url: 'https://chatglm.cn', loginFree: true },
  { id: 'yuanbao.tencent.com', name: '腾讯元宝', url: 'https://yuanbao.tencent.com/chat/', loginFree: true },
  { id: 'longcat.chat', name: 'LongCat', url: 'https://longcat.chat', loginFree: true },
  { id: 'kimi.com', name: 'Kimi', url: 'https://kimi.com', loginFree: false },
  { id: 'qianwen.com', name: '千问', url: 'https://qianwen.com', loginFree: false },
  { id: 'tongyi.aliyun.com', name: '通义千问', url: 'https://tongyi.aliyun.com/tongyi/tongyi-home', loginFree: false },
  { id: 'gemini.google.com', name: 'Gemini', url: 'https://gemini.google.com', loginFree: false },
  { id: 'claude.ai', name: 'Claude', url: 'https://claude.ai', loginFree: false },
  { id: 'chatgpt.com', name: 'ChatGPT', url: 'https://chatgpt.com', loginFree: false }
];

async function fullTest() {
  console.log('=== 全平台测试 ===\n');
  console.log('平台总数:', ALL_PLATFORMS.length);
  console.log('免登录:', ALL_PLATFORMS.filter(p => p.loginFree).map(p => p.name).join(', '));
  console.log('需登录:', ALL_PLATFORMS.filter(p => !p.loginFree).map(p => p.name).join(', '));

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  const results = [];

  // 测试所有平台
  for (const platform of ALL_PLATFORMS) {
    console.log(`\n========================================`);
    console.log(`  测试: ${platform.name}`);
    console.log(`========================================`);

    const result = await testPlatform(browser, platform);
    results.push(result);

    // 等待一下再测试下一个
    await new Promise(r => setTimeout(r, 2000));
  }

  // 输出汇总
  console.log('\n========================================');
  console.log('  测试结果汇总');
  console.log('========================================\n');

  results.forEach(r => {
    const status = r.success ? '✅' : (r.partial ? '⚠️' : '❌');
    console.log(`${status} ${r.platform.name}: ${r.message}`);
    if (r.details) {
      console.log(`   - Content Script: ${r.details.contentScript ? '✅' : '❌'}`);
      console.log(`   - 输入框检测: ${r.details.inputFound ? '✅' : '❌'}`);
      console.log(`   - 弹窗关闭: ${r.details.modalClosed ? '✅' : '无弹窗'}`);
      console.log(`   - 注入测试: ${r.details.injectionSuccess ? '✅' : '❌'}`);
    }
  });

  console.log('\n浏览器保持打开 120 秒...');
  await new Promise(r => setTimeout(r, 120000));

  await browser.close();
  console.log('\n测试完成！');
}

async function testPlatform(browser, platform) {
  const result = {
    platform: platform,
    success: false,
    partial: false,
    message: '',
    details: {}
  };

  try {
    const page = await browser.newPage();

    // 监听 console
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('[Prompt Pack]')) {
        console.log(`  [Console] ${text}`);
      }
    });

    console.log(`  打开: ${platform.url}`);
    await page.goto(platform.url, { waitUntil: 'domcontentloaded', timeout: 30000 });

    // 等待页面加载
    console.log(`  等待页面加载...`);
    await page.waitForTimeout(5000);

    // 检查 Content Script 是否初始化
    const csLogs = [];
    page.on('console', msg => {
      const text = msg.text();
      if (text.includes('Content Script initialized') || text.includes('Platform detected')) {
        csLogs.push(text);
      }
    });

    // 检测是否有登录弹窗
    console.log(`  检测登录弹窗...`);
    const modalSelectors = [
      '[class*="login-modal"]',
      '[class*="login-dialog"]',
      '[class*="auth-modal"]',
      '[role="dialog"]',
      '.modal',
      '.ant-modal'
    ];

    let hasModal = false;
    for (const selector of modalSelectors) {
      const modal = await page.$(selector);
      if (modal) {
        const visible = await modal.isVisible();
        if (visible) {
          hasModal = true;
          console.log(`  ⚠️ 发现登录弹窗: ${selector}`);
          break;
        }
      }
    }

    result.details.hasModal = hasModal;

    // 检查 Content Script 是否自动关闭弹窗
    if (hasModal) {
      console.log(`  等待自动关闭弹窗...`);
      await page.waitForTimeout(3000);

      // 再次检查弹窗是否还存在
      let modalStillExists = false;
      for (const selector of modalSelectors) {
        const modal = await page.$(selector);
        if (modal && await modal.isVisible()) {
          modalStillExists = true;
          break;
        }
      }

      if (!modalStillExists) {
        console.log(`  ✅ 弹窗已自动关闭`);
        result.details.modalClosed = true;
      } else {
        console.log(`  ❌ 弹窗仍存在，需手动关闭`);
        result.details.modalClosed = false;
      }
    }

    // 检测输入框
    console.log(`  检测输入框...`);
    const inputSelectors = [
      'textarea',
      'div[contenteditable="true"]',
      '[role="textbox"]',
      '#prompt-textarea',
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

    result.details.contentScript = csLogs.length > 0 || inputFound;
    result.details.inputFound = inputFound;
    result.details.inputSelector = inputSelector;

    if (!inputFound) {
      if (hasModal && !result.details.modalClosed) {
        result.message = '有登录弹窗阻挡，需手动关闭';
        result.partial = true;
      } else {
        result.message = '未找到输入框';
      }
      await page.close();
      return result;
    }

    // 测试注入
    console.log(`  测试注入...`);
    const testText = 'Prompt Pack 测试消息';

    const input = await page.$(inputSelector);
    await input.focus();
    await page.waitForTimeout(500);

    if (inputSelector.includes('textarea')) {
      await input.fill(testText);
    } else {
      // contenteditable
      await input.fill(testText);
    }

    await page.waitForTimeout(1000);

    // 检查注入结果
    let content = '';
    if (inputSelector.includes('textarea')) {
      content = await input.inputValue();
    } else {
      content = await input.textContent();
    }

    if (content.includes(testText) || content.includes('Prompt Pack')) {
      console.log(`  ✅ 注入成功`);
      result.details.injectionSuccess = true;
      result.success = true;
      result.message = '注入成功';
    } else {
      console.log(`  ❌ 注入失败，内容: "${content.substring(0, 30)}"`);
      result.details.injectionSuccess = false;
      result.message = '注入失败';
      result.partial = true;
    }

    // 清空
    await input.fill('');
    console.log(`  已清空输入框`);

    await page.close();

  } catch (error) {
    console.log(`  ❌ 错误: ${error.message}`);
    result.message = `错误: ${error.message}`;
    result.details.error = error.message;
  }

  return result;
}

fullTest().catch(err => console.error('测试错误:', err));