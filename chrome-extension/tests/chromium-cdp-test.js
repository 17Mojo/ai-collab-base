const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';

async function test() {
  console.log('启动 Chromium (CDP 端口 9223) 并加载扩展...');
  
  const browser = await chromium.launchPersistentContext('/tmp/chromium-cdp-test', {
    headless: false,
    args: [
      '--remote-debugging-port=9223',
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });
  
  console.log('浏览器已启动，CDP 端口: 9223');
  
  // 等待扩展加载
  await new Promise(r => setTimeout(r, 5000));
  
  // 检查 Background Pages
  const bgPages = browser.backgroundPages();
  console.log('Background Pages:', bgPages.length);
  
  // 打开 Kimi
  const page = await browser.newPage();
  await page.goto('https://kimi.com');
  await page.waitForTimeout(3000);
  
  console.log('Kimi 页面已打开');
  console.log('\n请在浏览器窗口中测试，浏览器将保持打开 120 秒...');
  
  await new Promise(r => setTimeout(r, 120000));
  
  await browser.close();
  console.log('测试完成');
}

test().catch(e => console.error('错误:', e.message));
