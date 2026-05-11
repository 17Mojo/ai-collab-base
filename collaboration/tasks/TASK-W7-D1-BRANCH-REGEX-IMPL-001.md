---
task_id: TASK-W7-D1-BRANCH-REGEX-IMPL-001
change_id: pack-workflow-branch-regex
status: completed
assignee: claude_code
reviewer: user
primary_skill: javascript
support_skills: ["python", "testing", "schema_design"]
acceptance_commands: "pytest tests/unit/pack/test_schema_v2.py -v && node chrome-extension/tests/test-pack-executor.js"
created_at: 2026-04-25T10:00:00
estimated_hours: 2.25
priority: P1
depends_on: []
---

# TASK-W7-D1-BRANCH-REGEX-IMPL-001

## 任务描述

实现 Pack Workflow 分支逻辑与正则表达式支持，使 PackExecutor 能够根据 AI 响应内容决定下一步执行路径。

## 背景

当前 PackExecutor 仅支持线性顺序执行，无法根据 AI 响应动态路由。Plan 已完成，详见 `~/.claude/plans/toasty-crunching-liskov.md`。

## 详细任务

### Phase 1: Schema 更新 (Python) - 0.5天

**位置**: `src/ai_collab/pack/schema_v2.py`

**新增数据类**:

```python
@dataclass
class RegexPattern:
    """正则表达式配置"""
    pattern: str                            # 正则模式
    flags: str = ""                         # 标志: 'i'=忽略大小写, 'm'=多行
    extract_fields: Optional[Dict[str, str]] = None  # 提取字段映射

@dataclass
class BranchCondition:
    """分支条件定义"""
    condition_type: str                     # 'regex_match', 'contains', 'equals', 'threshold', 'exists'
    target_field: str = "output"            # 检查字段
    condition_value: str = ""               # 匹配值/模式
    target_step: str                        # 目标步骤 ID
    regex_config: Optional[RegexPattern] = None
    negate: bool = False                    # 否定条件
```

**WorkflowStep 新增字段**:

```python
next_step: Optional[str] = None            # 显式下一步
branches: Optional[List[BranchCondition]] = None  # 条件分支列表
on_error: Optional[str] = None             # 错误处理步骤
on_timeout: Optional[str] = None           # 超时处理步骤
```

---

### Phase 2: PackExecutor 更新 (JavaScript) - 1天

**位置**: `chrome-extension/src/background/pack-executor.js`

**新增类**:

1. **RegexMatcher**
   - `match(pattern, text, flags)` - 单次匹配
   - `matchAll(pattern, text, flags)` - 全部匹配
   - 返回 `{ matched, extracts, fullMatch }`

2. **BranchEvaluator**
   - `evaluate(branch, execution)` - 评估条件
   - 支持 5 种条件类型: regex_match/contains/equals/threshold/exists

**修改 execute() 方法**:

替换顺序 for 循环为分支执行逻辑:

```javascript
async _executeWorkflowWithBranching(steps, execution) {
  let currentStepIndex = 0;
  const executedSteps = new Set();
  const maxIterations = steps.length * 3;  // 防止无限循环

  while (currentStepIndex < steps.length && executedSteps.size < maxIterations) {
    const step = steps[currentStepIndex];
    const stepResult = await this._executeStep(step, execution);

    // 评估分支
    const nextStepId = this._determineNextStep(step, execution);

    if (nextStepId === 'end') break;
    if (nextStepId) currentStepIndex = execution.stepIndex.get(nextStepId);
    else currentStepIndex++;
  }
}
```

---

### Phase 3: 示例 Pack JSON - 0.25天

**位置**: `packs/examples/error-handling-workflow.json`

**内容**:
- step_1_request: 带分支的请求步骤
- step_success: 成功处理
- step_error_handler: 错误处理（含 retry 分支）
- regex_match 条件提取 error_code

---

### Phase 4: 验证测试 - 0.5天

**验收命令**:

```bash
# Python Schema 测试
pytest tests/unit/pack/test_schema_v2.py -v

# JavaScript Executor 测试
node chrome-extension/tests/test-pack-executor.js

# 集成测试
pytest tests/integration/test_week2_integration.py -v
```

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| RegexPattern 数据类定义正确 | pytest schema 测试通过 |
| BranchCondition 数据类定义正确 | pytest schema 测试通过 |
| RegexMatcher.match() 正常工作 | 单元测试验证 |
| BranchEvaluator.evaluate() 支持 5 种条件 | 单元测试验证 |
| 分支执行逻辑防止无限循环 | maxIterations 验证 |
| 向后兼容（无分支 Pack 顺序执行） | 加载 demo-pack.json 验证 |
| error-handling-workflow Pack 执行正常 | 集成测试验证 |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| `src/ai_collab/pack/schema_v2.py` | 新增 BranchCondition, RegexPattern |
| `chrome-extension/src/background/pack-executor.js` | 新增 RegexMatcher, BranchEvaluator |
| `packs/examples/error-handling-workflow.json` | 新建示例 Pack |

---

## 风险/回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| 正则表达式性能问题 | 长文本匹配慢 | 限制匹配文本长度 |
| 分支死循环 | 执行卡住 | maxIterations 上限 |
| 向后兼容破坏 | 旧 Pack 失效 | Optional 字段 + 默认顺序执行 |

**回滚方案**: 删除新增代码，恢复原始顺序执行逻辑

---

## 参考文档

- Plan 文件: `~/.claude/plans/toasty-crunching-liskov.md`
- Schema 文件: `src/ai_collab/pack/schema_v2.py`
- Executor 文件: `chrome-extension/src/background/pack-executor.js`

---

**创建时间**: 2026-04-25T10:00:00+08:00