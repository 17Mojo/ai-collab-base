/**
 * Kimi UI检测脚本 - 分析Kimi页面DOM结构
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/chromium-kimi-ui-' + Date.now();

async function analyzeKimiUI() {
  console.log('=== Kimi UI检测 ===\n');

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  const page = await browser.newPage();
  await page.goto('https://kimi.com');
  await new Promise(r => setTimeout(r, 5000));

  // 分析UI结构
  console.log('分析Kimi页面UI结构...\n');

  const uiInfo = await page.evaluate(() => {
    // 查找输入框
    const inputSelectors = [
      'textarea',
      'div[contenteditable="true"]',
      'input[type="text"]',
      '[class*="input"]',
      '[class*="chat-input"]'
    ];

    const inputResults = inputSelectors.map(sel => {
      const el = document.querySelector(sel);
      return {
        selector: sel,
        found: !!el,
        visible: el ? el.offsetParent !== null : false,
        tagName: el?.tagName,
        className: el?.className?.substring(0, 50),
        ariaLabel: el?.getAttribute('aria-label'),
        placeholder: el?.getAttribute('placeholder')
      };
    });

    // 查找发送按钮
    const buttonSelectors = [
      'button[type="submit"]',
      'button[aria-label*="发送"]',
      'button[aria-label*="send"]',
      'button[class*="send"]',
      'button svg',  // 可能是图标按钮
      '[class*="submit"]'
    ];

    const buttonResults = buttonSelectors.map(sel => {
      const el = document.querySelector(sel);
      return {
        selector: sel,
        found: !!el,
        tagName: el?.tagName,
        className: el?.className?.substring(0, 50),
        ariaLabel: el?.getAttribute('aria-label'),
        type: el?.getAttribute('type'),
        innerText: el?.innerText?.substring(0, 20)
      };
    });

    // 检查所有button元素
    const allButtons = Array.from(document.querySelectorAll('button')).slice(0, 10).map(btn => ({
      className: btn.className.substring(0, 30),
      ariaLabel: btn.getAttribute('aria-label'),
      type: btn.getAttribute('type'),
      innerText: btn.innerText.substring(0, 20),
      hasSvg: !!btn.querySelector('svg')
    }));

    return {
      inputs: inputResults,
      buttons: buttonResults,
      allButtons
    };
  });

  console.log('输入框检测结果:');
  console.log(JSON.stringify(uiInfo.inputs.filter(i => i.found), null, 2));

  console.log('\n按钮检测结果:');
  console.log(JSON.stringify(uiInfo.buttons.filter(b => b.found), null, 2));

  console.log('\n所有button元素（前10个）:');
  console.log(JSON.stringify(uiInfo.allButtons, null, 2));

  // 尝试手动注入并观察
  console.log('\n尝试手动注入文本...');
  await page.evaluate(() => {
    const input = document.querySelector('div[contenteditable="true"]');
    if (input) {
      input.focus();
      document.execCommand('insertText', false, '你好Kimi');
      console.log('文本已注入');
    }
  });

  console.log('\n浏览器保持打开 60 秒，请手动测试发送...');
  await new Promise(r => setTimeout(r, 60000));

  await browser.close();
}

analyzeKimiUI().catch(err => console.error('错误:', err));