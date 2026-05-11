/**
 * 千问 qianwen.com DOM 检查 - 这个域名测试成功
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';

async function inspectQianwen() {
  console.log('=== 千问 qianwen.com DOM 检查 ===\n');

  const browser = await chromium.launchPersistentContext('/tmp/qianwen-inspect-' + Date.now(), {
    headless: false,
    args: [`--disable-extensions-except=${EXTENSION_PATH}`, `--load-extension=${EXTENSION_PATH}`]
  });

  const page = await browser.newPage();

  page.on('console', msg => {
    if (msg.text().includes('[Prompt Pack]')) {
      console.log('[Console]', msg.text());
    }
  });

  console.log('打开千问...');
  await page.goto('https://qianwen.com', {
    waitUntil: 'domcontentloaded',
    timeout: 20000
  });

  await page.waitForTimeout(6000);

  const url = page.url();
  console.log('当前URL:', url);

  // 检查输入框详细信息
  console.log('\n--- 输入框详细信息 ---');

  const inputInfo = await page.evaluate(() => {
    // 查找所有可能的输入元素
    const allEls = document.querySelectorAll('*');
    const inputs = [];

    allEls.forEach(e => {
      const tag = e.tagName.toLowerCase();
      const role = e.getAttribute('role');
      const ce = e.getAttribute('contenteditable');
      const className = e.className;

      if (tag === 'textarea' ||
          tag === 'input' ||
          ce === 'true' ||
          role === 'textbox' ||
          (className && (className.includes('input') || className.includes('chat') || className.includes('editor')))) {

        const rect = e.getBoundingClientRect();
        if (rect.width > 50 && rect.height > 20) {
          inputs.push({
            tag: e.tagName,
            id: e.id || '',
            className: typeof className === 'string' ? className.substring(0, 60) : '',
            role: role || '',
            contenteditable: ce || '',
            type: e.getAttribute('type') || '',
            placeholder: e.getAttribute('placeholder') || '',
            ariaLabel: e.getAttribute('aria-label') || '',
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            // 获取父元素信息
            parentClass: e.parentElement?.className?.substring(0, 30) || ''
          });
        }
      }
    });

    return inputs;
  });

  console.log('找到的输入元素:');
  inputInfo.forEach(e => {
    console.log(`\n元素: ${e.tag}`);
    console.log(`  id: "${e.id}"`);
    console.log(`  class: "${e.className}"`);
    console.log(`  role: "${e.role}"`);
    console.log(`  contenteditable: "${e.contenteditable}"`);
    console.log(`  type: "${e.type}"`);
    console.log(`  placeholder: "${e.placeholder}"`);
    console.log(`  aria-label: "${e.ariaLabel}"`);
    console.log(`  size: ${e.width}x${e.height}`);
    console.log(`  parent: "${e.parentClass}"`);
  });

  // 截图
  await page.screenshot({ path: '/tmp/qianwen-dom.png' });
  console.log('\n截图: /tmp/qianwen-dom.png');

  console.log('\n浏览器保持打开 30 秒...');
  await new Promise(r => setTimeout(r, 30000));

  await browser.close();
}

inspectQianwen().catch(err => console.error('错误:', err));