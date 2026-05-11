/**
 * Popup Pack执行测试
 * 自动打开Chrome扩展Popup并执行Pack
 */

const { chromium } = require('playwright');

const EXTENSION_PATH = '/Users/raymondna/Documents/ai-collab-system/chrome-extension';
const USER_DATA_DIR = '/tmp/popup-test-' + Date.now();

async function testPopupExecution() {
  console.log('=== Popup Pack执行测试 ===\n');
  console.log('测试流程:');
  console.log('  1. 打开ChatGLM页面');
  console.log('  2. 打开扩展Popup');
  console.log('  3. 选择Pack和风格');
  console.log('  4. 输入提示词');
  console.log('  5. 执行Pack');
  console.log('  6. 验证结果显示\n');

  // 启动带扩展的浏览器
  const browser = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`
    ]
  });

  // 打开ChatGLM页面（需要AI平台才能执行）
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

  // 手动测试说明
  console.log('\n==========================================');
  console.log('  请手动执行以下步骤：');
  console.log('==========================================\n');
  console.log('步骤1: 点击浏览器右上角的扩展图标');
  console.log('       打开 Prompt Pack Popup\n');
  console.log('步骤2: 在Popup中选择:');
  console.log('       - Pack: "知识问答"');
  console.log('       - 风格: "罗永浩风格"\n');
  console.log('步骤3: 输入提示词:');
  console.log('       "AI是什么？请简短回答"\n');
  console.log('步骤4: 点击 "执行 Pack" 按钮\n');
  console.log('步骤5: 观察:');
  console.log('       - 结果区域是否显示');
  console.log('       - 统计信息是否正确');
  console.log('       - 内容是否个性化\n');

  console.log('浏览器保持打开 120 秒...');
  console.log('等待你手动测试 Popup\n');

  await new Promise(r => setTimeout(r, 120000));

  await browser.close();
  console.log('\n测试完成');
}

testPopupExecution().catch(err => console.error('错误:', err));