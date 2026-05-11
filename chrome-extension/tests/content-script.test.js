/**
 * Content Script Tests
 * 验证跨平台消息注入选择器
 */

// 测试选择器配置
const selectors = {
  'claude.ai': {
    input: 'div[contenteditable="true"]',
    message: '[data-testid="conversation-turn"]',
    sendButton: 'button[aria-label="Send Message"]',
    typingIndicator: '.animate-spin'
  },
  'chat.openai.com': {
    input: '#prompt-textarea, textarea[placeholder*="Message"], div[contenteditable="true"]',
    message: '[data-testid="conversation-turn"]',
    sendButton: 'button[data-testid="send-button"]',
    typingIndicator: 'button[aria-label="Stop generating"]'
  },
  'gemini.google.com': {
    input: 'div[contenteditable="true"][aria-label*="prompt"]',
    message: 'model-response',
    sendButton: 'button[aria-label="Send prompt"]',
    typingIndicator: 'mat-progress-bar'
  }
};

// 平台检测函数
function detectPlatform(hostname) {
  if (hostname.includes('claude.ai')) return 'claude.ai';
  if (hostname.includes('chat.openai.com') || hostname.includes('chatgpt.com')) return 'chat.openai.com';
  if (hostname.includes('gemini.google.com')) return 'gemini.google.com';
  return null;
}

// 运行测试
const tests = [];

// Test 1: 平台检测
tests.push({
  name: 'Platform detection - Claude.ai',
  fn: () => {
    const result = detectPlatform('claude.ai');
    if (result !== 'claude.ai') throw new Error(`Expected claude.ai, got ${result}`);
  }
});

tests.push({
  name: 'Platform detection - ChatGPT',
  fn: () => {
    const result = detectPlatform('chat.openai.com');
    if (result !== 'chat.openai.com') throw new Error(`Expected chat.openai.com, got ${result}`);
  }
});

tests.push({
  name: 'Platform detection - ChatGPT alias',
  fn: () => {
    const result = detectPlatform('chatgpt.com');
    if (result !== 'chat.openai.com') throw new Error(`Expected chat.openai.com, got ${result}`);
  }
});

tests.push({
  name: 'Platform detection - Gemini',
  fn: () => {
    const result = detectPlatform('gemini.google.com');
    if (result !== 'gemini.google.com') throw new Error(`Expected gemini.google.com, got ${result}`);
  }
});

tests.push({
  name: 'Platform detection - Unknown',
  fn: () => {
    const result = detectPlatform('example.com');
    if (result !== null) throw new Error(`Expected null, got ${result}`);
  }
});

// Test 2: 选择器存在性
for (const [platform, config] of Object.entries(selectors)) {
  tests.push({
    name: `Selector exists for ${platform} - input`,
    fn: () => {
      if (!config.input) throw new Error('Missing input selector');
    }
  });

  tests.push({
    name: `Selector exists for ${platform} - message`,
    fn: () => {
      if (!config.message) throw new Error('Missing message selector');
    }
  });

  tests.push({
    name: `Selector exists for ${platform} - sendButton`,
    fn: () => {
      if (!config.sendButton) throw new Error('Missing sendButton selector');
    }
  });
}

// 运行所有测试
console.log('\n=== Content Script Test Results ===');
let passed = 0;
let failed = 0;

for (const test of tests) {
  try {
    test.fn();
    passed++;
  } catch (e) {
    failed++;
    console.log(`FAILED: ${test.name} - ${e.message}`);
  }
}

console.log(`\nPassed: ${passed}, Failed: ${failed}`);
process.exit(failed === 0 ? 0 : 1);