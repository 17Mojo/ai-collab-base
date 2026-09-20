/**
 * 通义千问 DOM 结构检查
 * 找出正确的输入框选择器
 */

const { chromium } = require('playwright');

async function inspectTongyi() {
  console.log('=== 通义千问 DOM 结构检查 ===\n');

  const browser = await chromium.launch({
    headless: false
  });

  const page = await browser.newPage();

  console.log('打开通义千问...');
  await page.goto('https://tongyi.aliyun.com/tongyi/tongyi-home', {
    waitUntil: 'domcontentloaded',
    timeout: 30000
  });

  console.log('等待页面加载...');
  await page.waitForTimeout(8000);

  // 查找所有可能的输入框元素
  console.log('\n--- 检查所有可能的输入框 ---');

  const selectors = [
    'textarea',
    'div[contenteditable="true"]',
    '[role="textbox"]',
    'input[type="text"]',
    'input[placeholder]',
    '[class*="input"]',
    '[class*="chat"]',
    '[class*="editor"]',
    '[class*="textarea"]',
    '[data-testid*="input"]',
    '.input-area',
    '.chat-input',
    '#chat-input',
    '[placeholder]'
  ];

  for (const selector of selectors) {
    try {
      const elements = await page.$$eval(selector, els =>
        els.map(e => ({
          tag: e.tagName,
          id: e.id,
          className: e.className?.substring(0, 50),
          role: e.getAttribute('role'),
          placeholder: e.getAttribute('placeholder') || '',
          contenteditable: e.getAttribute('contenteditable'),
          visible: e.offsetWidth > 50,
          width: e.offsetWidth,
          height: e.offsetHeight
        }))
      );

      if (elements.length > 0) {
        const visible = elements.filter(e => e.visible);
        console.log(`\n选择器: ${selector}`);
        console.log(`  总数: ${elements.length}, 可见: ${visible.length}`);
        visible.forEach(e => {
          console.log(`  - ${e.tag}.${e.className?.substring(0,30)}, role=${e.role}, placeholder="${e.placeholder.substring(0,20)}", size=${e.width}x${e.height}`);
        });
      }
    } catch (e) {
      // selector 可能不匹配
    }
  }

  // 截图
  await page.screenshot({ path: '/tmp/tongyi-dom-screenshot.png', fullPage: false });
  console.log('\n截图保存: /tmp/tongyi-dom-screenshot.png');

  // 获取页面HTML结构片段
  console.log('\n--- 检查主要结构 ---');
  const bodyClasses = await page.$eval('body', el => el.className);
  console.log('body classes:', bodyClasses);

  // 查找主要的聊天容器
  const chatContainers = await page.$$eval('[class*="chat"], [class*="conversation"], [class*="dialog"]', els =>
    els.map(e => ({
      tag: e.tagName,
      className: e.className?.substring(0, 50),
      id: e.id
    }))
  );

  if (chatContainers.length > 0) {
    console.log('\n聊天容器:');
    chatContainers.forEach(e => {
      console.log(`  - ${e.tag}.${e.className}`);
    });
  }

  console.log('\n浏览器保持打开 30 秒...');
  await new Promise(r => setTimeout(r, 30000));

  await browser.close();
  console.log('\n检查完成！');
}

inspectTongyi().catch(err => console.error('错误:', err));