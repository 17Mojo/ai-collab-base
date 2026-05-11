---
task_id: TASK-W8-D1-BRANCH-LOGIC-TEST-001
change_id: branch-logic-integration-test
status: completed
assignee: claude_code
reviewer: user
primary_skill: testing
support_skills: ["javascript", "python", "chrome_extension"]
acceptance_commands: "pytest tests/integration/test_branch_logic.py -v && node chrome-extension/tests/test-branch-executor.js"
created_at: 2026-04-26T09:00:00
estimated_hours: 0.5
priority: P0
depends_on: ["TASK-W7-D1-BRANCH-REGEX-IMPL-001"]
---

# TASK-W8-D1-BRANCH-LOGIC-TEST-001

## 任务描述

测试 Week 7 实现的分支逻辑实际运行，验证 regex 分支路由、错误处理跳转、重试机制。

## 背景

Week 7 完成了 Schema 和 PackExecutor 的分支逻辑实现，需要在真实场景中验证功能正确性。

## 详细任务

### Task 1: 创建集成测试文件 (15min)

**位置**: `tests/integration/test_branch_logic.py`

**测试用例**:

```python
def test_branch_regex_match_success():
    """测试 regex_match 条件匹配 SUCCESS 跳转"""
    # 加载 error-handling-workflow.json
    # 模拟 SUCCESS 响应
    # 验证跳转到 step_success

def test_branch_regex_match_error():
    """测试 regex_match 条件匹配 ERROR 跳转"""
    # 模拟 ERROR: NETWORK_FAILED 响应
    # 验证跳转到 step_error_handler
    # 验证 error_code 提取

def test_branch_contains_retry():
    """测试 contains 条件匹配 retry 跳转"""
    # 模拟 "retry" 响应
    # 集验证跳回 step_1_request

def test_branch_negate_condition():
    """测试 negate 条件"""
    # 测试否定条件跳转

def test_max_iterations_guard():
    """测试 maxIterations 防止无限循环"""
    # 模拟循环场景
    # 验证执行次数上限
```

---

### Task 2: JavaScript Executor 测试 (10min)

**位置**: `chrome-extension/tests/test-branch-executor.js`

```javascript
// 测试 RegexMatcher
const result = RegexMatcher.match('^SUCCESS:', 'SUCCESS: Task completed', 'i');
assert(result.matched);

// 测试 BranchEvaluator
const execution = { output: 'ERROR: TIMEOUT', steps: [] };
const branch = { condition_type: 'regex_match', regex_config: { pattern: 'ERROR:', flags: 'i' }, target_step: 'error' };
const evalResult = BranchEvaluator.evaluate(branch, execution);
assert(evalResult.matched);
```

---

### Task 3: 实际 Pack 执行验证 (10min)

**命令**:

```bash
# 使用 Backend API 执行 Pack
curl -X POST http://127.0.0.1:8000/api/packs/execute \
  -H "Content-Type: application/json" \
  -d '{"pack_id": "error-handling-workflow", "input": {"request": "test request"}}'
```

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| pytest 测试全部通过 | 5 tests passed |
| JavaScript 测试通过 | node test 断言成功 |
| SUCCESS 分支跳转正确 | 日志显示 step_success |
| ERROR 分支跳转正确 | 日志显示 step_error_handler |
| 重试循环正确终止 | maxIterations 上限生效 |
| 提取字段存储正确 | execution.extractedData 有值 |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| tests/integration/test_branch_logic.py | 新建 |
| chrome-extension/tests/test-branch-executor.js | 新建 |

---

## 风险/回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| 分支跳转失败 | 功能不可用 | 检查 BranchCondition 字段顺序 |
| 无限循环 | 执行卡住 | maxIterations 保障 |

---

**创建时间**: 2026-04-26T09:00:00+08:00