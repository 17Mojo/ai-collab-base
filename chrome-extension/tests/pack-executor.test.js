/**
 * Pack Executor Tests
 * Pack 执行引擎单元测试
 */

// 模拟 Chrome API
global.chrome = {
  runtime: {
    sendMessage: (message) => Promise.resolve({ success: true }),
    onMessage: {
      addListener: () => {}
    }
  }
};

// 测试 PackExecutor 类
class TestPackExecutor {
  constructor() {
    this.results = [];
  }

  test(name, fn) {
    try {
      fn();
      this.results.push({ name, status: 'PASSED' });
    } catch (e) {
      this.results.push({ name, status: 'FAILED', error: e.message });
    }
  }

  report() {
    console.log('\n=== Pack Executor Test Results ===');
    const passed = this.results.filter(r => r.status === 'PASSED').length;
    const failed = this.results.filter(r => r.status === 'FAILED').length;
    console.log(`Passed: ${passed}, Failed: ${failed}`);

    if (failed > 0) {
      console.log('\nFailed tests:');
      this.results.filter(r => r.status === 'FAILED').forEach(r => {
        console.log(`  - ${r.name}: ${r.error}`);
      });
    }

    return failed === 0;
  }
}

// 导入 PackExecutor (ES Module 模拟)
const ExecutionStatus = {
  IDLE: 'idle',
  RUNNING: 'running',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  FAILED: 'failed'
};

class PackExecutor {
  constructor(options = {}) {
    this.packs = new Map();
    this.currentExecution = null;
    this.executionHistory = [];
    this.status = ExecutionStatus.IDLE;
    this.options = {
      maxRetries: 3,
      retryDelay: 1000,
      timeout: 60000,
      ...options
    };
  }

  loadPack(pack) {
    if (!pack.metadata || !pack.metadata.pack_id) {
      throw new Error('Invalid pack: missing metadata or pack_id');
    }
    this.packs.set(pack.metadata.pack_id, pack);
  }

  getPack(packId) {
    return this.packs.get(packId) || null;
  }

  getStatus() {
    return {
      status: this.status,
      currentExecution: this.currentExecution ? {
        packId: this.currentExecution.packId,
        startTime: this.currentExecution.startTime
      } : null,
      loadedPacks: Array.from(this.packs.keys())
    };
  }
}

// 运行测试
const tester = new TestPackExecutor();

// Test 1: 初始化
tester.test('PackExecutor initialization', () => {
  const executor = new PackExecutor();
  if (executor.status !== 'idle') throw new Error('Status should be idle');
  if (executor.packs.size !== 0) throw new Error('Packs should be empty');
});

// Test 2: 加载 Pack
tester.test('Load pack', () => {
  const executor = new PackExecutor();
  const pack = {
    metadata: { pack_id: 'test-pack-001' },
    workflow: { steps: [] }
  };
  executor.loadPack(pack);
  if (executor.packs.size !== 1) throw new Error('Should have 1 pack');
  if (!executor.getPack('test-pack-001')) throw new Error('Pack not found');
});

// Test 3: 无效 Pack
tester.test('Load invalid pack throws error', () => {
  const executor = new PackExecutor();
  try {
    executor.loadPack({ metadata: {} });
    throw new Error('Should have thrown');
  } catch (e) {
    if (!e.message.includes('Invalid pack')) throw new Error('Wrong error message');
  }
});

// Test 4: 获取状态
tester.test('Get status', () => {
  const executor = new PackExecutor();
  const status = executor.getStatus();
  if (status.status !== 'idle') throw new Error('Status should be idle');
  if (status.currentExecution !== null) throw new Error('Should have no execution');
  if (status.loadedPacks.length !== 0) throw new Error('Should have no packs');
});

// Test 5: Pack 不存在
tester.test('Get nonexistent pack returns null', () => {
  const executor = new PackExecutor();
  if (executor.getPack('nonexistent') !== null) throw new Error('Should return null');
});

// 输出报告
const success = tester.report();
process.exit(success ? 0 : 1);