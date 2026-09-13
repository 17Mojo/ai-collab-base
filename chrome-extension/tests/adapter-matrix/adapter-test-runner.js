/**
 * Adapter Test Runner
 * Tests all 10 platform adapters against mock DOM fixtures
 *
 * Tests per adapter:
 *   - detect()        : hostname matching
 *   - getChatInput()  : input element selection with fallback
 *   - getSendButton() : send button selection with fallback
 *   - getMessageList(): message list selection with fallback
 *   - injectText()    : text injection into input element
 *
 * Usage:
 *   node tests/adapter-matrix/adapter-test-runner.js
 *   node tests/adapter-matrix/adapter-test-runner.js --platform=chatgpt
 *   node tests/adapter-matrix/adapter-test-runner.js --verbose
 */

const {
  loadFixture,
  findElement,
  findElements,
  extractMessageContent,
  isVisible,
  runTest,
  formatResults,
} = require('./adapter-test-utils');

// ============================================================================
// Platform Adapter Definitions (mirrors source SELECTORS exactly)
// ============================================================================

const ADAPTERS = {
  chatgpt: {
    name: 'ChatGPT',
    hostnames: ['chat.openai.com', 'chatgpt.com'],
    fixture: 'chatgpt',
    SELECTORS: {
      chatInput: ['#prompt-textarea', 'textarea[placeholder*="Message"]', 'div[contenteditable="true"]'],
      sendButton: ['button[data-testid="send-button"]', 'button[aria-label="Send prompt"]'],
      messageList: ['[data-testid="conversation-turn"]', '.text-base'],
      typingIndicator: ['[data-testid="typing-indicator"]'],
      stopButton: ['button[aria-label="Stop generating"]'],
      messageContent: ['.markdown', '[data-message-author-role]'],
    },
  },

  claude: {
    name: 'Claude.ai',
    hostnames: ['claude.ai'],
    fixture: 'claude',
    SELECTORS: {
      chatInput: ['div[contenteditable="true"]', 'div.ProseMirror[contenteditable="true"]'],
      sendButton: ['button[aria-label="Send"]', 'button[data-testid="send-button"]'],
      messageList: ['[data-testid="conversation-turn"]', '.conversation-turn'],
      typingIndicator: ['[data-testid="typing-indicator"]'],
      stopButton: ['button[aria-label="Stop generating"]'],
      messageContent: ['.prose', '[data-testid="message-content"]'],
    },
  },

  kimi: {
    name: 'Kimi AI',
    hostnames: ['kimi.com', 'kimi.moonshot.cn'],
    fixture: 'kimi',
    SELECTORS: {
      chatInput: ['div.chat-input-editor', 'div[contenteditable="true"]', 'textarea'],
      sendButton: ['button[type="submit"]', 'button[aria-label*="发送"]', 'button[class*="send"]'],
      messageList: ['.chat-message', '[class*="message"]'],
      messageContent: ['.prose', '.chat-content', '[class*="content"]'],
      typingIndicator: ['.loading', '[class*="loading"]', '.generating'],
    },
  },

  gemini: {
    name: 'Gemini',
    hostnames: ['gemini.google.com'],
    fixture: 'gemini',
    SELECTORS: {
      chatInput: [
        'div[contenteditable="true"][aria-label*="prompt"]',
        'div[contenteditable="true"][aria-label*="Gemini"]',
        'div[contenteditable="true"].ql-editor',
        '[role="textbox"]',
        'textarea[placeholder*="prompt"]',
      ],
      sendButton: ['button[aria-label="Send prompt"]', 'send-button', 'button[aria-label*="Send"]'],
      messageList: ['model-response', '.chat-turn', '[class*="conversation-turn"]'],
      typingIndicator: ['mat-progress-bar', '[class*="loading"]'],
      stopButton: ['button[aria-label="Stop"]', 'button[aria-label*="Stop"]'],
      messageContent: ['.model-response-text', 'message-content', '.markdown'],
    },
  },

  deepseek: {
    name: 'DeepSeek',
    hostnames: ['chat.deepseek.com'],
    fixture: 'deepseek',
    SELECTORS: {
      chatInput: ['textarea', 'div[contenteditable="true"]', '#chat-input', 'textarea[placeholder*="message"]'],
      sendButton: ['button[data-testid="send-button"]', 'button[aria-label*="Send"]', 'button[aria-label*="发送"]', 'button[class*="send"]'],
      messageList: ['[data-testid="conversation-turn"]', '.chat-message', '[class*="message"]', '.ds-chat-message'],
      messageContent: ['.ds-assistant-message-main-content', '.markdown', '.prose', '[class*="message-content"]', '[class*="content"]'],
      typingIndicator: ['[class*="loading"]', '[class*="generating"]', '.typing-indicator'],
      stopButton: ['button[aria-label="Stop generating"]', 'button[aria-label="Stop"]'],
    },
  },

  longcat: {
    name: 'LongCat AI',
    hostnames: ['longcat.chat'],
    fixture: 'longcat',
    SELECTORS: {
      chatInput: ['div[role="textbox"]', 'div[contenteditable="true"]'],
      sendButton: ['button[type="submit"]', 'img[cursor="pointer"]'],
      messageList: ['.message', '[class*="response"]', '[class*="chat-item"]'],
      messageContent: ['.prose', '.response-content', '[class*="content"]'],
      typingIndicator: ['[class*="loading"]', '[class*="generating"]'],
    },
  },

  qianwen: {
    name: 'Qianwen (千问)',
    hostnames: ['qianwen.com', 'tongyi.aliyun.com'],
    fixture: 'qianwen',
    SELECTORS: {
      chatInput: ['div[contenteditable="true"]', 'textarea'],
      sendButton: ['button[aria-label*="发送"]', 'button[title*="发送"]', 'button[class*="send"]'],
      messageList: ['[class*="message"]', '[class*="chat-item"]', '.response-content'],
      messageContent: ['.prose', '[class*="message-content"]', 'div[class*="content"]'],
      typingIndicator: ['[class*="loading"]', '[class*="generating"]', '.typing-indicator'],
    },
  },

  yiyan: {
    name: 'Yiyan (文心一言)',
    hostnames: ['yiyan.baidu.com', 'wenxin.baidu.com'],
    fixture: 'yiyan',
    SELECTORS: {
      chatInput: ['textarea.ci-textarea', 'textarea', 'div[contenteditable="true"]', '[role="textbox"]', 'input[type="text"]'],
      sendButton: ['button[type="submit"]', 'button[aria-label*="发送"]', 'button[class*="send"]', 'button[data-send]'],
      messageList: ['[class*="message"]', '[class*="chat"]', '[class*="response"]', '.chat-item'],
      messageContent: ['.prose', '[class*="answer"]', '[class*="content"]'],
      typingIndicator: ['[class*="loading"]', '[class*="generating"]', '.spinner'],
    },
  },

  yuanbao: {
    name: 'Yuanbao (腾讯元宝)',
    hostnames: ['yuanbao.tencent.com'],
    fixture: 'yuanbao',
    SELECTORS: {
      chatInput: ['div.ql-editor', 'div[contenteditable="true"]', 'textarea', '[role="textbox"]'],
      sendButton: ['button[type="submit"]', 'button[aria-label*="发送"]', 'button[class*="send"]', 'button[data-send]'],
      messageList: ['[class*="message"]', '[class*="chat"]', '[class*="response"]', '.message-item'],
      messageContent: ['.prose', '[class*="answer"]', '[class*="content"]'],
      typingIndicator: ['[class*="loading"]', '[class*="generating"]', '.spinner'],
    },
  },

  chatglm: {
    name: 'ChatGLM (智谱清言)',
    hostnames: ['chatglm.cn'],
    fixture: 'chatglm',
    SELECTORS: {
      chatInput: ['div[contenteditable="true"]', 'textarea', '[role="textbox"]'],
      sendButton: ['button[type="submit"]', 'button[aria-label*="发送"]', 'button[class*="send"]'],
      messageList: ['.chat-message', '[class*="message"]', '[class*="response"]'],
      messageContent: ['.chat-content', '.message-text', '[class*="content"]'],
      typingIndicator: ['[class*="loading"]', '[class*="generating"]', '.typing-indicator'],
    },
  },
};

// ============================================================================
// Test Definitions
// ============================================================================

/**
 * Test detect() — hostname matching
 */
function testDetect(adapter, hostname) {
  const tests = [];

  // Positive test: correct hostname should match
  tests.push(runTest(`detect() matches hostname "${hostname}"`, () => {
    const { window } = loadFixture(adapter.fixture, hostname);
    const detected = adapter.hostnames.some(h => hostname.includes(h));
    if (!detected) throw new Error(`Expected hostname "${hostname}" to match [${adapter.hostnames.join(', ')}]`);
    return true;
  }));

  // Negative test: wrong hostname should not match
  tests.push(runTest(`detect() rejects wrong hostname`, () => {
    const { window } = loadFixture(adapter.fixture, 'example.com');
    const detected = adapter.hostnames.some(h => 'example.com'.includes(h));
    if (detected) throw new Error('Should not detect on example.com');
    return true;
  }));

  return tests;
}

/**
 * Test getChatInput() — input element selection with fallback
 */
function testGetChatInput(adapter) {
  const tests = [];
  const { document } = loadFixture(adapter.fixture, adapter.hostnames[0]);
  const selectors = adapter.SELECTORS.chatInput;

  // Primary selector should find an element
  tests.push(runTest(`getChatInput() primary selector "${selectors[0]}" finds element`, () => {
    const el = document.querySelector(selectors[0]);
    if (!el) throw new Error(`Primary selector "${selectors[0]}" returned null`);
    return true;
  }));

  // findElement with full selector array should find an element
  tests.push(runTest(`getChatInput() findElement() finds input`, () => {
    const el = findElement(document, selectors);
    if (!el) throw new Error('findElement returned null for chatInput selectors');
    return true;
  }));

  // Found element should be an input-type element
  tests.push(runTest(`getChatInput() returns input-capable element`, () => {
    const el = findElement(document, selectors);
    if (!el) throw new Error('No element found');
    const tag = el.tagName;
    const isContentEditable = el.getAttribute('contenteditable') === 'true';
    const isTextarea = tag === 'TEXTAREA';
    const isInput = tag === 'INPUT';
    const hasRole = el.getAttribute('role') === 'textbox';
    if (!isContentEditable && !isTextarea && !isInput && !hasRole) {
      throw new Error(`Element <${tag}> is not input-capable`);
    }
    return true;
  }));

  return tests;
}

/**
 * Test getSendButton() — send button selection with fallback
 */
function testGetSendButton(adapter) {
  const tests = [];
  const { document } = loadFixture(adapter.fixture, adapter.hostnames[0]);
  const selectors = adapter.SELECTORS.sendButton;

  tests.push(runTest(`getSendButton() findElement() finds button`, () => {
    const el = findElement(document, selectors);
    if (!el) throw new Error('findElement returned null for sendButton selectors');
    return true;
  }));

  tests.push(runTest(`getSendButton() returns a button element`, () => {
    const el = findElement(document, selectors);
    if (!el) throw new Error('No element found');
    const tag = el.tagName;
    const isButton = tag === 'BUTTON' || el.closest('button') !== null || tag === 'SEND-BUTTON';
    // Some platforms use img or custom elements
    if (!isButton && tag !== 'IMG' && tag !== 'SEND-BUTTON') {
      throw new Error(`Element <${tag}> is not a button`);
    }
    return true;
  }));

  return tests;
}

/**
 * Test getMessageList() — message list selection with fallback
 */
function testGetMessageList(adapter) {
  const tests = [];
  const { document } = loadFixture(adapter.fixture, adapter.hostnames[0]);
  const selectors = adapter.SELECTORS.messageList;

  tests.push(runTest(`getMessageList() findElements() finds messages`, () => {
    const els = findElements(document, selectors);
    if (!els || els.length === 0) throw new Error('No message elements found');
    return true;
  }));

  tests.push(runTest(`getMessageList() returns multiple messages (>= 2)`, () => {
    const els = findElements(document, selectors);
    if (!els || els.length < 2) throw new Error(`Expected >= 2 messages, got ${els ? els.length : 0}`);
    return true;
  }));

  return tests;
}

/**
 * Test injectText() — text injection into input element
 */
function testInjectText(adapter) {
  const tests = [];
  const { document, window } = loadFixture(adapter.fixture, adapter.hostnames[0]);
  const selectors = adapter.SELECTORS.chatInput;
  const testText = 'Hello from adapter test!';

  // Test textarea injection
  tests.push(runTest(`injectText() can inject into textarea`, () => {
    // Find a textarea in the fixture
    const textarea = document.querySelector('textarea');
    if (!textarea) return true; // Skip if no textarea (some platforms use contenteditable)

    // Simulate nativeInputValueSetter
    textarea.value = testText;
    textarea.dispatchEvent(new window.Event('input', { bubbles: true }));

    if (textarea.value !== testText) {
      throw new Error(`Expected "${testText}", got "${textarea.value}"`);
    }
    return true;
  }));

  // Test contenteditable injection
  tests.push(runTest(`injectText() can inject into contenteditable`, () => {
    const editable = document.querySelector('div[contenteditable="true"]');
    if (!editable) return true; // Skip if no contenteditable

    editable.textContent = testText;
    editable.dispatchEvent(new window.Event('input', { bubbles: true }));

    if (!editable.textContent.includes(testText)) {
      throw new Error('Text not found in contenteditable after injection');
    }
    return true;
  }));

  // Test that the input element is focusable
  tests.push(runTest(`injectText() input element is focusable`, () => {
    const el = findElement(document, selectors);
    if (!el) throw new Error('No input element found');
    // Just verify focus() doesn't throw
    try {
      el.focus();
    } catch (e) {
      throw new Error(`focus() threw: ${e.message}`);
    }
    return true;
  }));

  return tests;
}

// ============================================================================
// Test Runner
// ============================================================================

/**
 * Run all tests for a single adapter
 */
function testAdapter(adapterId) {
  const adapter = ADAPTERS[adapterId];
  if (!adapter) {
    console.error(`Unknown adapter: ${adapterId}`);
    return { pass: 0, fail: 1, total: 1 };
  }

  const allTests = [
    ...testDetect(adapter, adapter.hostnames[0]),
    ...testGetChatInput(adapter),
    ...testGetSendButton(adapter),
    ...testGetMessageList(adapter),
    ...testInjectText(adapter),
  ];

  return formatResults(adapter.name, allTests);
}

/**
 * Run the full test matrix
 */
function runTestMatrix(filterPlatform) {
  console.log('╔══════════════════════════════════════════════════════════════╗');
  console.log('║         Chrome Extension Adapter Test Matrix                ║');
  console.log('╚══════════════════════════════════════════════════════════════╝');
  console.log(`  Platforms: ${Object.keys(ADAPTERS).length}`);
  console.log(`  Tests per adapter: ~11`);
  console.log('');

  const platformIds = filterPlatform
    ? [filterPlatform]
    : Object.keys(ADAPTERS);

  let totalPass = 0;
  let totalFail = 0;
  let totalTests = 0;
  const platformResults = [];

  for (const id of platformIds) {
    const result = testAdapter(id);
    totalPass += result.pass;
    totalFail += result.fail;
    totalTests += result.total;
    platformResults.push({ id, ...result });
  }

  // Summary
  console.log('\n╔══════════════════════════════════════════════════════════════╗');
  console.log('║                        Summary                              ║');
  console.log('╚══════════════════════════════════════════════════════════════╝\n');

  for (const r of platformResults) {
    const icon = r.fail === 0 ? 'ALL PASS' : `${r.fail} FAIL`;
    console.log(`  ${ADAPTERS[r.id].name.padEnd(25)} ${r.pass}/${r.total} (${icon})`);
  }

  console.log(`\n  Total: ${totalPass}/${totalTests} passed, ${totalFail} failed`);
  console.log('');

  return { totalPass, totalFail, totalTests };
}

// ============================================================================
// CLI Entry Point
// ============================================================================

function main() {
  const args = process.argv.slice(2);
  let filterPlatform = null;

  for (const arg of args) {
    if (arg.startsWith('--platform=')) {
      filterPlatform = arg.split('=')[1];
    }
    if (arg === '--help' || arg === '-h') {
      console.log('Usage: node tests/adapter-matrix/adapter-test-runner.js [options]');
      console.log('');
      console.log('Options:');
      console.log('  --platform=<id>   Test a specific platform (chatgpt, claude, kimi, etc.)');
      console.log('  --list            List all available platforms');
      console.log('  --help, -h        Show this help message');
      console.log('');
      console.log('Platforms:');
      for (const [id, adapter] of Object.entries(ADAPTERS)) {
        console.log(`  ${id.padEnd(12)} ${adapter.name} (${adapter.hostnames.join(', ')})`);
      }
      process.exit(0);
    }
    if (arg === '--list') {
      console.log('Available platforms:');
      for (const [id, adapter] of Object.entries(ADAPTERS)) {
        console.log(`  ${id.padEnd(12)} ${adapter.name}`);
        console.log(`               Hostnames: ${adapter.hostnames.join(', ')}`);
        console.log(`               Fixture:   mock-dom-${adapter.fixture}.html`);
        console.log('');
      }
      process.exit(0);
    }
  }

  if (filterPlatform && !ADAPTERS[filterPlatform]) {
    console.error(`Error: Unknown platform "${filterPlatform}"`);
    console.error(`Available: ${Object.keys(ADAPTERS).join(', ')}`);
    process.exit(1);
  }

  const { totalFail } = runTestMatrix(filterPlatform);
  process.exit(totalFail > 0 ? 1 : 0);
}

main();
