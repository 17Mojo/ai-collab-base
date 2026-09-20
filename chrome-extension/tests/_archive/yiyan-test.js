const { chromium } = require('playwright');
const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';

async function testYiyan() {
  console.log('=== 文心一言测试 ===\n');

  const browser = await chromium.launchPersistentContext('/tmp/yiyan-test-' + Date.now(), {
    headless: false,
    args: [`--disable-extensions-except=${EXTENSION_PATH}`, `--load-extension=${EXTENSION_PATH}`]
  });

  const page = await browser.newPage();

  page.on('console', msg => {
    if (msg.text().includes('[Prompt Pack]')) {
      console.log('[Console]', msg.text());
    }
  });

  console.log('打开文心一言...');
  await page.goto('https://yiyan.baidu.com/', { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(6000);

  console.log('当前URL:', page.url());

  // 检测输入框
  const input = await page.$('textarea, div[contenteditable="true"], [role="textbox"]');

  if (input) {
    const visible = await input.isVisible();
    if (visible) {
      console.log('✅ 找到输入框！');

      await input.focus();
      await input.fill('文心一言测试消息 - Prompt Pack');
      await page.waitForTimeout(1000);

      const content = await input.textContent();
      if (content.includes('测试消息') || content.includes('Prompt Pack')) {
        console.log('✅ 注入成功！');
      } else {
        console.log('注入内容:', content.substring(0, 50));
      }

      await input.fill('');
      console.log('已清空');
    } else {
      console.log('输入框不可见');
    }
  } else {
    console.log('❌ 未找到输入框');
  }

  await page.screenshot({ path: '/tmp/yiyan-test.png' });
  console.log('截图: /tmp/yiyan-test.png');

  console.log('\n浏览器保持打开 30 秒...');
  await new Promise(r => setTimeout(r, 30000));

  await browser.close();
  console.log('测试完成！');
}

testYiyan().catch(err => console.error('错误:', err));
