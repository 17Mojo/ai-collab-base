/**
 * 通义千问详细检查 - 查找聊天入口
 */

const { chromium } = require('playwright');

async function inspectTongyiDetailed() {
  console.log('=== 通义千问详细检查 ===\n');

  const browser = await chromium.launch({
    headless: false
  });

  const page = await browser.newPage();

  console.log('打开通义千问首页...');
  await page.goto('https://tongyi.aliyun.com/', {
    waitUntil: 'networkidle',
    timeout: 30000
  });

  await page.waitForTimeout(5000);

  // 检查页面标题和URL
  const title = await page.title();
  const url = page.url();
  console.log('页面标题:', title);
  console.log('当前URL:', url);

  // 截图首页
  await page.screenshot({ path: '/tmp/tongyi-homepage.png' });
  console.log('首页截图: /tmp/tongyi-homepage.png');

  // 查找可能的聊天入口按钮
  console.log('\n--- 查找聊天入口按钮 ---');

  const buttonSelectors = [
    'button',
    'a[href*="chat"]',
    'a[href*="tongyi"]',
    '[class*="chat"]',
    '[class*="button"]',
    '[role="button"]',
    'a'
  ];

  for (const selector of buttonSelectors) {
    try {
      const buttons = await page.$$eval(selector, els =>
        els.map(e => ({
          tag: e.tagName,
          text: e.textContent?.trim().substring(0, 30),
          className: e.className?.substring(0, 40),
          href: e.getAttribute('href') || '',
          visible: e.offsetWidth > 20
        }))
      );

      const visibleButtons = buttons.filter(b => b.visible && (b.text.includes('聊') || b.text.includes('问') || b.text.includes('chat') || b.href.includes('chat')));

      if (visibleButtons.length > 0) {
        console.log(`\n可能的聊天入口 (${selector}):`);
        visibleButtons.forEach(b => {
          console.log(`  - "${b.text}" href="${b.href}" class="${b.className}"`);
        });
      }
    } catch (e) {}
  }

  // 尝试直接访问聊天页面
  console.log('\n--- 尝试直接访问聊天页面 ---');
  await page.goto('https://tongyi.aliyun.com/tongyi/tongyi-chat', {
    waitUntil: 'networkidle',
    timeout: 30000
  });

  await page.waitForTimeout(5000);

  const chatUrl = page.url();
  console.log('聊天页URL:', chatUrl);

  await page.screenshot({ path: '/tmp/tongyi-chat-page.png' });
  console.log('聊天页截图: /tmp/tongyi-chat-page.png');

  // 再次检查输入框
  console.log('\n--- 聊天页输入框检查 ---');

  const allInputs = await page.$$eval('*', els =>
    els.filter(e => {
      const tag = e.tagName.toLowerCase();
      return tag === 'textarea' ||
             tag === 'input' ||
             e.getAttribute('contenteditable') === 'true' ||
             e.getAttribute('role') === 'textbox';
    }).map(e => ({
      tag: e.tagName,
      id: e.id,
      className: e.className?.substring(0, 50),
      role: e.getAttribute('role'),
      placeholder: e.getAttribute('placeholder') || '',
      contenteditable: e.getAttribute('contenteditable'),
      type: e.getAttribute('type') || '',
      visible: e.offsetWidth > 50,
      width: e.offsetWidth,
      height: e.offsetHeight
    }))
  );

  console.log('找到的输入元素:');
  allInputs.forEach(e => {
    console.log(`  - ${e.tag}.${e.className}, role=${e.role}, type=${e.type}, placeholder="${e.placeholder.substring(0,20)}", size=${e.width}x${e.height}, visible=${e.visible}`);
  });

  console.log('\n浏览器保持打开 30 秒...');
  await new Promise(r => setTimeout(r, 30000));

  await browser.close();
}

inspectTongyiDetailed().catch(err => console.error('错误:', err));