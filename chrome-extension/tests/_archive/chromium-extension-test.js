const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';

async function test() {
  console.log('启动 Chromium 并加载扩展...');
  
  const browser = await chromium.launchPersistentContext('/tmp/chromium-ext-test', {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });
  
  console.log('浏览器已启动');
  
  // 等待扩展加载
  await new Promise(r => setTimeout(r, 3000));
  
  // 检查 Background Pages
  const bgPages = browser.backgroundPages();
  console.log('Background Pages:', bgPages.length);
  
  // 打开扩展管理页面
  const page = await browser.newPage();
  await page.goto('chrome://extensions/');
  await page.waitForTimeout(2000);
  
  // 检查已加载的扩展
  const exts = await page.evaluate(() => {
    const items = document.querySelectorAll('extensions-item');
    const result = [];
    items.forEach(item => {
      result.push({
        name: item.querySelector('#name')?.textContent,
        enabled: item.getAttribute('data-enabled') === 'true'
      });
    });
    return result;
  });
  
  console.log('已加载扩展:', JSON.stringify(exts, null, 2));
  
  // 如果扩展加载成功，打开 Kimi 测试
  if (exts.length > 0) {
    console.log('\n扩展加载成功！打开 Kimi 测试...');
    const kimiPage = await browser.newPage();
    await kimiPage.goto('https://kimi.com');
    await kimiPage.waitForTimeout(5000);
    
    // 测试 SEND_TO_AI
    const result = await kimiPage.evaluate(() => {
      return new Promise((resolve) => {
        chrome.runtime.sendMessage({
          type: 'SEND_TO_AI',
          prompt: '知识付费的商业价值',
          config: { soulProfile: 'luoyonghao' }
        }, (response) => {
          resolve(response);
        });
      });
    });
    
    console.log('SEND_TO_AI 结果:', JSON.stringify(result, null, 2));
  }
  
  console.log('\n保持浏览器打开 30 秒...');
  await new Promise(r => setTimeout(r, 30000));
  
  await browser.close();
  console.log('测试完成');
}

test().catch(e => console.error('错误:', e.message));
