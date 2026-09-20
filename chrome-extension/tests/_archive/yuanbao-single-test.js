/**
 * 单平台测试 - 腾讯元宝
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/yuanbao-test-' + Date.now();

async function testYuanbao() {
  console.log('=== 腾讯元宝注入测试 ===\n');

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  const page = await browser.newPage();

  // 监听 console
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[Prompt Pack]')) {
      console.log('[Console]', text);
    }
  });

  console.log('打开腾讯元宝...');
  await page.goto('https://yuanbao.tencent.com/chat/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);

  console.log('\n--- 检测输入框 ---');

  // 查找 contenteditable
  const contentEditable = await page.$('div[contenteditable="true"]');
  if (contentEditable) {
    console.log('✅ 找到 div[contenteditable="true"]');

    // 测试注入
    console.log('\n--- 测试注入 ---');
    const testText = '这是来自 Prompt Pack 的测试消息';

    await contentEditable.focus();
    await page.waitForTimeout(500);

    // 使用 fill 方法（Playwright 支持）
    await contentEditable.fill(testText);
    await page.waitForTimeout(1000);

    // 检查内容
    const content = await contentEditable.textContent();
    console.log('输入框内容:', content.substring(0, 50));

    if (content.includes(testText) || content.includes('Prompt Pack')) {
      console.log('✅ 注入成功！');
    } else {
      console.log('❌ 注入失败');
    }

    // 截图
    await page.screenshot({ path: '/tmp/yuanbao-inject-test.png' });
    console.log('截图: /tmp/yuanbao-inject-test.png');

    // 清空
    await contentEditable.fill('');
    console.log('已清空');
  } else {
    console.log('❌ 未找到 contenteditable');
  }

  console.log('\n浏览器保持打开 60 秒...');
  await new Promise(r => setTimeout(r, 60000));

  await browser.close();
  console.log('测试完成');
}

testYuanbao().catch(err => console.error('错误:', err));