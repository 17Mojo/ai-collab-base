const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DIR = '/tmp/chromium-test-' + Date.now();

async function test() {
  console.log('启动 Chromium...');
  console.log('用户目录:', USER_DIR);
  
  const browser = await chromium.launchPersistentContext(USER_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });
  
  console.log('浏览器已启动');
  
  const page = await browser.newPage();
  await page.goto('https://kimi.com');
  
  console.log('Kimi 页面已打开');
  console.log('\n请在 Console 执行测试代码，浏览器保持打开 180 秒...');
  
  await new Promise(r => setTimeout(r, 180000));
  
  await browser.close();
}

test().catch(e => console.error('错误:', e.message));
