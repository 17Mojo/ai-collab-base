/**
 * 快速平台检测测试
 * 检查各平台的输入框选择器是否正确
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/quick-platform-test-' + Date.now();

const PLATFORMS = [
  { id: 'chatglm.cn', name: '智谱清言', url: 'https://chatglm.cn' },
  { id: 'yuanbao.tencent.com', name: '腾讯元宝', url: 'https://yuanbao.tencent.com/chat/' },
  { id: 'longcat.chat', name: 'LongCat', url: 'https://longcat.chat' }
];

async function quickTest() {
  console.log('=== 快速平台检测测试 ===\n');

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  for (const platform of PLATFORMS) {
    console.log(`\n--- ${platform.name} ---`);

    try {
      const page = await browser.newPage();

      console.log(`打开: ${platform.url}`);
      await page.goto(platform.url, { waitUntil: 'domcontentloaded', timeout: 20000 });

      // 等待页面加载
      console.log('等待页面加载...');
      await page.waitForTimeout(5000);

      // 检测输入框
      const selectors = [
        'textarea',
        'div[contenteditable="true"]',
        '[role="textbox"]',
        'input[type="text"]'
      ];

      for (const selector of selectors) {
        try {
          const elements = await page.$$eval(selector, els =>
            els.map(e => ({
              tag: e.tagName,
              visible: e.offsetWidth > 100 && e.offsetHeight > 20,
              role: e.getAttribute('role'),
              placeholder: e.getAttribute('placeholder') || ''
            }))
          );

          const visible = elements.filter(e => e.visible);

          if (visible.length > 0) {
            console.log(`✅ 找到输入框 (${selector}):`);
            visible.forEach(e => {
              console.log(`   - ${e.tag}, role=${e.role}, placeholder="${e.placeholder.substring(0, 20)}"`);
            });
          }
        } catch (e) {
          // selector 可能不匹配
        }
      }

      // 截图
      const screenshotPath = `/tmp/${platform.id}-screenshot.png`;
      await page.screenshot({ path: screenshotPath });
      console.log(`截图保存: ${screenshotPath}`);

      await page.close();

    } catch (error) {
      console.log(`❌ 错误: ${error.message}`);
    }
  }

  console.log('\n测试完成，浏览器保持打开 60 秒...');
  await new Promise(r => setTimeout(r, 60000));

  await browser.close();
}

quickTest().catch(err => console.error('错误:', err));