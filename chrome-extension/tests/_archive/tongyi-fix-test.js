/**
 * 通义千问修复验证测试
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';

async function testTongyiFix() {
  console.log('=== 通义千问修复验证 ===\n');

  const browser = await chromium.launchPersistentContext('/tmp/tongyi-fix-test-' + Date.now(), {
    headless: false,
    args: [`--disable-extensions-except=${EXTENSION_PATH}`, `--load-extension=${EXTENSION_PATH}`]
  });

  const page = await browser.newPage();

  page.on('console', msg => {
    if (msg.text().includes('[Prompt Pack]')) {
      console.log('[Console]', msg.text());
    }
  });

  // 测试多个可能的聊天URL
  const urls = [
    'https://qianwen.com',
    'https://www.qianwen.com',
    'https://tongyi.aliyun.com/tongyi/tongyi-chat'
  ];

  for (const url of urls) {
    console.log(`\n--- 测试 URL: ${url} ---`);

    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(5000);

      console.log('页面URL:', page.url());

      // 检测输入框
      const input = await page.$('div[contenteditable="true"], textarea, [role="textbox"]');

      if (input) {
        const visible = await input.isVisible();
        if (visible) {
          console.log('✅ 找到输入框！');

          // 测试注入
          await input.focus();
          await input.fill('通义千问测试消息');
          await page.waitForTimeout(1000);

          const content = await input.textContent();
          if (content.includes('测试消息')) {
            console.log('✅ 注入成功！');
          } else {
            console.log('注入内容:', content.substring(0, 30));
          }

          await input.fill('');
          console.log('已清空');

          break;  // 成功就退出循环
        } else {
          console.log('输入框不可见');
        }
      } else {
        console.log('❌ 未找到输入框');
      }

    } catch (error) {
      console.log('错误:', error.message.substring(0, 50));
    }
  }

  await page.screenshot({ path: '/tmp/tongyi-fix-test.png' });
  console.log('\n截图: /tmp/tongyi-fix-test.png');

  console.log('\n浏览器保持打开 30 秒...');
  await new Promise(r => setTimeout(r, 30000));

  await browser.close();
  console.log('测试完成！');
}

testTongyiFix().catch(err => console.error('错误:', err));