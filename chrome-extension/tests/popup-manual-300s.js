/**
 * Popup手动测试 - 300秒
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/popup-manual-' + Date.now();

async function manualTest() {
  console.log('=== Popup手动测试 (300秒) ===\n');

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  const chatPage = await browser.newPage();
  chatPage.on('console', msg => {
    const text = msg.text();
    if (text.includes('[Prompt Pack]')) {
      console.log('[ChatGLM]', text);
    }
  });

  console.log('打开 ChatGLM...');
  await chatPage.goto('https://chatglm.cn');
  await new Promise(r => setTimeout(r, 5000));

  console.log('\n==========================================');
  console.log('  Popup测试步骤：');
  console.log('==========================================\n');
  console.log('1. 点击右上角扩展图标，打开Popup');
  console.log('2. 选择Pack: "知识问答"');
  console.log('3. 选择风格: "罗永浩风格"');
  console.log('4. 输入: "AI是什么？"');
  console.log('5. 点击 "执行 Pack"');
  console.log('6. 观察结果区域\n');

  console.log('浏览器保持打开 300 秒 (5分钟)...\n');

  await new Promise(r => setTimeout(r, 300000));

  await browser.close();
  console.log('测试完成');
}

manualTest().catch(err => console.error('错误:', err));