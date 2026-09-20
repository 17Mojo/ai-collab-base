const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DIR = '/tmp/chromium-final-' + Date.now();

async function test() {
  console.log('=== 最终测试 ===');
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
  console.log('\n请在 Console 执行:');
  console.log('window.postMessage({ type: "PROMPT_PACK_TEST", prompt: "知识付费", config: { soulProfile: "luoyonghao" } }, "*");');
  console.log('\n浏览器保持打开 300 秒...');
  
  // 保持打开 300 秒
  await new Promise(r => setTimeout(r, 300000));
  
  await browser.close();
  console.log('测试完成');
}

test().catch(e => console.error('错误:', e.message));
