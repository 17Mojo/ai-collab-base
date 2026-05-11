# AI 协同工作准则 (Collaboration Guidelines)

**版本**: 1.0
**创建时间**: 2026-02-28T23:45:00+08:00
**创建者**: CodeArts Agent (技术合伙人)
**适用范围**: 所有参与项目的 AI Agent

---

## 一、核心原则

### 1.1 价值最大化原则

**每个 AI 必须最大化利用可用资源**:

| 资源类型 | 使用场景 | 强制要求 |
|---------|---------|---------|
| **Skills** | 代码生成、前端设计、i18n | 相关任务必须调用 |
| **MCP 工具** | NotebookLM、Context7 | 复杂问题必须查询 |
| **知识图谱** | 项目知识管理 | 重要决策必须记录 |
| **现有文档** | 报告、任务、公告 | 开始前必须阅读 |

**违规后果**: 任务质量不达标,需要返工

### 1.2 协同优先原则

**所有共享文档必须遵守协同规则**:

1. **认领机制**: 开始前必须打标记
2. **锁定机制**: 被锁定的文档只读
3. **审计机制**: 所有变更必须带时间戳
4. **超时机制**: 60 分钟无进展可被接管

**违规后果**: 修改被回滚,任务重新分配

### 1.3 质量优先原则

**交付物必须达到质量标准**:

- 测试覆盖率: ≥ 80%
- 测试通过率: 100%
- 代码质量: 通过 Lint 检查
- 文档质量: 符合模板规范

**违规后果**: 任务标记为 `blocked`,需要改进

---

## 二、任务执行流程 (强制遵守)

### 2.1 任务启动前 (Pre-Task Checklist)

**必须完成以下检查**:

- [ ] **阅读相关文档**:
  - [ ] 阅读任务文件 (`collaboration/tasks/TASK-*.md`)
  - [ ] 阅读相关报告 (`collaboration/results/*.md`)
  - [ ] 阅读公告 (`notifications/*.md`)

- [ ] **检查协同状态**:
  - [ ] 检查看板 (`Current Locks`)
  - [ ] 确认任务未被锁定
  - [ ] 打标记认领任务

- [ ] **评估资源需求**:
  - [ ] 是否需要查询最佳实践? → 使用 NotebookLM
  - [ ] 是否需要查询框架文档? → 使用 Context7
  - [ ] 是否涉及前端? → 调用 `frontend-design` 技能
  - [ ] 是否涉及 i18n? → 调用 `i18n-integration` 技能

- [ ] **制定执行计划**:
  - [ ] 分解任务步骤
  - [ ] 估算所需时间
  - [ ] 识别风险点

**标记模板**:
```text
[IN_PROGRESS][owner=<ai_name>][task=<task_id>][start=<ISO8601>]
```

### 2.2 任务执行中 (During Task)

**必须遵守以下规则**:

1. **资源使用**:
   - 遇到复杂问题 → 先查询 NotebookLM
   - 需要框架文档 → 先查询 Context7
   - 代码质量提升 → 调用相关技能

2. **进度更新**:
   - 每完成一个子任务 → 更新任务文件
   - 遇到阻塞 → 立即标记 `blocked` 并说明原因
   - 超过 30 分钟无进展 → 考虑请求协助

3. **知识记录**:
   - 重要决策 → 记录到知识图谱
   - 关键发现 → 更新相关报告
   - 最佳实践 → 分享给其他 AI

### 2.3 任务完成后 (Post-Task Checklist)

**必须完成以下检查**:

- [ ] **质量验证**:
  - [ ] 测试通过率 100%
  - [ ] 覆盖率达标 (≥ 80%)
  - [ ] 代码通过 Lint
  - [ ] 文档符合规范

- [ ] **生成结果报告**:
  - [ ] 创建 `RESULT_<task_id>.md`
  - [ ] 包含改进前后对比
  - [ ] 包含验证结果
  - [ ] 包含后续建议

- [ ] **更新任务状态**:
  - [ ] 标记任务为 `completed`
  - [ ] 更新执行记录
  - [ ] 打完成标记

- [ ] **更新共享文档**:
  - [ ] 更新覆盖率报告 (如适用)
  - [ ] 更新改进总结报告 (如适用)
  - [ ] 更新看板状态

**标记模板**:
```text
[DONE][owner=<ai_name>][task=<task_id>][done=<ISO8601>]
```

---

## 三、资源使用指南

### 3.1 NotebookLM 使用指南

**何时使用**:
- 需要查询 AI 协作最佳实践
- 需要查询 Prompt Pack 设计参考
- 需要了解 OpenSpec 使用方法
- 遇到复杂问题需要专家建议

**如何使用**:
```python
# 1. 开始会话
ask_question({
  question: "Give me an overview of [topic]",
  session_id: null  # 创建新会话
})

# 2. 深入查询 (使用相同 session_id)
ask_question({
  question: "Key APIs/methods?",
  session_id: <上一步返回的 session_id>
})

# 3. 获取生产示例
ask_question({
  question: "Show a production-ready example",
  session_id: <相同的 session_id>
})
```

### 3.2 Context7 使用指南

**何时使用**:
- 需要查询框架/库的最新文档
- 需要查看代码示例
- 需要了解 API 用法

**如何使用**:
```python
# 1. 解析库 ID
resolve_library_id({
  libraryName: "pytest",
  query: "How to use pytest fixtures?"
})

# 2. 查询文档
query_docs({
  libraryId: "/org/pytest",
  query: "How to use pytest fixtures?"
})
```

### 3.3 Skills 使用指南

**frontend-design 技能**:
- 何时: 创建或修改前端组件/页面
- 调用: `SkillTool(skill_name="frontend-design")`

**i18n-integration 技能**:
- 何时: 添加国际化支持
- 调用: `SkillTool(skill_name="i18n-integration")`

**ide-tool 技能**:
- 何时: 需要调用 IDE 功能
- 调用: `SkillTool(skill_name="ide-tool")`

### 3.4 知识图谱使用指南

**何时使用**:
- 记录重要决策
- 记录项目结构
- 记录 AI 角色和职责
- 记录任务依赖关系

**如何使用**:
```python
# 创建实体
create_entities({
  entities: [{
    name: "TASK-W1-CHROME-INJECTION-001",
    entityType: "Task",
    observations: [
      "任务: 加固 Chrome 注入稳健性",
      "执行者: codearts_agent",
      "状态: completed",
      "覆盖率提升: 0% → 85%"
    ]
  }]
})

# 创建关系
create_relations({
  relations: [{
    from: "TASK-W1-CHROME-INJECTION-001",
    to: "codearts_agent",
    relationType: "executed_by"
  }]
})
```

### 3.5 AI Integration 模式治理指南

**何时使用**:
- 新增或修改 `src/ai_collab/integrations/*`、`src/ai_collab/engines/*` 代码
- 需要在 `mock/fallback/real` 间切换运行模式
- 排查“线上走 mock”或“真实调用失败回退”问题

**模式定义**:
- `mock`: 仅模拟响应，必须输出 `_mock` 与 `_mock_reason`
- `fallback`: 先真实调用，失败回退模拟，并记录回退原因
- `real`: 仅真实调用，失败直接暴露错误，不允许 mock 回退

**配置优先级**:
1. `AI_INTEGRATION_MODE_<MODULE>`
2. `AI_INTEGRATION_MODE`
3. `DEFAULT_INTEGRATION_MODES`（`IntegrationMode` 默认配置）

**推荐实践**:
- 本地开发: `mock` 或 `fallback`
- CI 回归: `fallback`
- 发布联调: 关键模块切 `real`
- 生产环境: 默认 `fallback`，关键路径可按模块设为 `real`

**常用检查命令**:
```bash
python3 -m pytest -q tests/unit/test_integration_flags.py tests/unit/test_ai_integration_mock_flags.py
python3 -m ruff check src/ai_collab/config src/ai_collab/integrations src/ai_collab/engines
openspec validate add-ai-integration-mode-governance --strict
```

---

## 四、协同文档更新规则

### 4.1 共享报告更新规则

**适用文档**:
- `TEST_COVERAGE_REPORT_2026-02-28.md`
- `IMPROVEMENT_SUMMARY_REPORT_2026-02-28.md`

**更新流程**:

1. **检查锁定状态**:
   - 查看 `Current Locks` 看板
   - 如果有 `IN_PROGRESS` 标记,检查 owner
   - 如果 owner 不是自己,只能读取

2. **认领任务**:
   - 在看板中添加:
     ```text
     [IN_PROGRESS][owner=<ai_name>][task=<task_id>][start=<ISO8601>]
     ```

3. **更新内容**:
   - 只更新自己认领的任务相关内容
   - 不要修改其他任务的内容
   - 所有变更必须带时间戳

4. **完成标记**:
   - 更新看板:
     ```text
     [DONE][owner=<ai_name>][task=<task_id>][done=<ISO8601>]
     ```

### 4.2 任务文件更新规则

**适用文档**:
- `collaboration/tasks/TASK-*.md`

**更新流程**:

1. **开始前**:
   - 更新 `分配给` 字段
   - 更新状态为 `in_progress`
   - 添加执行记录

2. **执行中**:
   - 定期更新执行记录
   - 遇到问题立即标记

3. **完成后**:
   - 更新状态为 `completed`
   - 添加完成时间
   - 总结执行成果

---

## 五、质量标准

### 5.1 测试质量标准

**强制要求**:
- 测试通过率: 100%
- 新增代码覆盖率: ≥ 80%
- 边界条件测试: 必须包含
- 异常情况测试: 必须包含

**推荐要求**:
- 使用参数化测试
- 使用 fixture 管理测试数据
- 添加清晰的测试文档

### 5.2 代码质量标准

**强制要求**:
- 通过 Lint 检查 (flake8/pylint)
- 通过类型检查 (mypy)
- 无安全漏洞 (bandit)

**推荐要求**:
- 遵循 PEP 8 规范
- 添加类型注解
- 添加文档字符串

### 5.3 文档质量标准

**强制要求**:
- 符合模板规范
- 包含时间戳
- 包含执行者信息

**推荐要求**:
- 结构清晰
- 数据准确
- 建议具体

---

## 六、违规处理

### 6.1 轻微违规

**定义**:
- 未使用推荐资源
- 文档格式不规范
- 进度更新不及时

**处理**:
- 提醒改进
- 记录到知识图谱
- 累计 3 次升级为中度违规

### 6.2 中度违规

**定义**:
- 未遵守协同规则
- 质量标准不达标
- 未完成必需检查

**处理**:
- 任务标记为 `blocked`
- 要求返工改进
- 记录到改进报告

### 6.3 严重违规

**定义**:
- 破坏共享文档
- 并行冲突导致数据丢失
- 故意违反规则

**处理**:
- 回滚所有修改
- 重新分配任务
- 记录到知识图谱

---

## 七、持续改进

### 7.1 规则更新机制

**触发条件**:
- 发现规则漏洞
- 新增资源类型
- 优化工作流程

**更新流程**:
1. 提出改进建议
2. 讨论并达成共识
3. 更新本文档
4. 通知所有 AI

### 7.2 反馈机制

**如何反馈**:
- 在 `collaboration/feedback/` 目录创建反馈文件
- 格式: `FEEDBACK_<topic>_<date>.md`
- 包含问题描述和改进建议

**处理流程**:
1. 技术合伙人审核反馈
2. 评估改进价值
3. 制定实施计划
4. 更新相关规则

---

## 八、附录

### 8.1 标记模板汇总

```text
# 认领任务
[IN_PROGRESS][owner=<ai_name>][task=<task_id>][start=<ISO8601>]

# 完成任务
[DONE][owner=<ai_name>][task=<task_id>][done=<ISO8601>]

# 接管任务
[TAKEOVER][by=<ai_name>][from=<owner>][time=<ISO8601>]

# 阻塞任务
[BLOCKED][owner=<ai_name>][task=<task_id>][reason=<reason>][time=<ISO8601>]
```

### 8.2 检查清单模板

**任务启动前**:
```markdown
- [ ] 阅读任务文件
- [ ] 阅读相关报告
- [ ] 检查看板状态
- [ ] 打标记认领
- [ ] 评估资源需求
- [ ] 制定执行计划
```

**任务完成后**:
```markdown
- [ ] 测试通过率 100%
- [ ] 覆盖率达标
- [ ] 代码通过 Lint
- [ ] 生成结果报告
- [ ] 更新任务状态
- [ ] 更新共享文档
- [ ] 打完成标记
```

---

**本准则对所有 AI 强制生效,违反将按违规处理流程执行**
