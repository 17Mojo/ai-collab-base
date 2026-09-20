/**
 * P2 Pack Storage 测试
 * 验证 PackStorageManager + Backend API + Popup 集成
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/p2-test-' + Date.now();

async function testP2PackStorage() {
  console.log('=== P2 Pack Storage 测试 ===\n');

  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  // 监听 Console
  const page = await browser.newPage();
  page.on('console', msg => {
    const text = msg.text();
    if (text.includes('[Prompt Pack]') || text.includes('[PackStorage]') || text.includes('[Backend Client]')) {
      console.log('[Extension]', text);
    }
  });

  console.log('测试步骤:');
  console.log('1. 打开 Popup → 检查 Pack 列表加载');
  console.log('2. 打开 Settings → 点击 "打开 Pack 编辑器"');
  console.log('3. 在 Pack Editor → 创建新 Pack');
  console.log('4. 返回 Popup → 检查新 Pack 是否显示\n');

  console.log('浏览器保持打开 180 秒...\n');

  await new Promise(r => setTimeout(r, 180000));

  await browser.close();
  console.log('测试完成');
}

testP2PackStorage().catch(err => console.error('错误:', err));