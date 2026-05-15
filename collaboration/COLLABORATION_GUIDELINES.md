# AI 协同工作准则 (Collaboration Guidelines v3.0)

**版本**: 3.0  
**更新时间**: 2026-05-15  
**适用范围**: 所有参与项目的 Agent（通过 `config/agent-orchestration.json` 绑定的角色）

---

## 一、核心原则

### 1.1 价值最大化原则

**每个 Agent 必须最大化利用可用资源**:

| 资源类型 | 使用场景 | 强制要求 |
|---------|---------|---------|
| **Skills** | 代码生成、前端设计、i18n | 相关任务必须调用 |
| **MCP 工具** | NotebookLM、Context7 | 复杂问题必须查询 |
| **知识图谱** | 项目知识管理 | 重要决策必须记录 |
| **现有文档** | 报告、任务、公告 | 开始前必须阅读 |

**违规后果**: 任务质量不达标，需要返工

### 1.2 协同优先原则

**所有共享文档必须遵守协同规则**:

1. **认领机制**: 开始前必须打标记
2. **锁定机制**: 被锁定的文档只读
3. **审计机制**: 所有变更必须带时间戳
4. **超时机制**: 60 分钟无进展可被接管

**违规后果**: 修改被回滚，任务重新分配

### 1.3 质量优先原则

**交付物必须达到质量标准**:

- 测试覆盖率: ≥ 80%
- 测试通过率: 100%
- 代码质量: 通过 Lint 检查
- 文档质量: 符合模板规范

**违规后果**: 任务标记为 `blocked`，需要改进

---

## 二、角色系统说明

### 2.1 动态角色编排

本项目采用**角色别名驱动**的动态协作架构，具体 Agent 提供商通过 `config/agent-orchestration.json` 绑定。

**角色代号**:

| 角色代号 | 显示名称 | RACI 定位 | 职责描述 |
|---------|---------|----------|---------|
| `AGENT_EXEC` | 主执行者 | R (Responsible) | 代码实现、重构、Bug修复 |
| `AGENT_ARCH` | 架构师 | A (Accountable) | 架构设计、技术选型、代码审查 |
| `AGENT_TEST` | 测试验证 | C (Consulted) | 单元测试、集成测试、质量保证 |
| `AGENT_DOC` | 文档编写 | C (Consulted) | 文档撰写、使用说明 |
| `AGENT_PERF` | 性能优化 | C (Consulted) | 性能测试、负载分析 |
| `AGENT_OPS` | 运维部署 | I (Informed) | 发布管理、环境配置 |

**角色扩展**: 用户可通过 `/menu` 动态新增角色，上限为 10 个。

### 2.2 运行时角色解析

命令执行时，系统从 `agent-orchestration.json` 解析当前绑定：

```
用户输入: X.RUN
→ 查询 command_prefixes: X.RUN → AGENT_EXEC
→ 查询 roles.AGENT_EXEC.binding.provider
→ 实际执行: [当前绑定的 Agent 提供商]
```

### 2.3 冷启动机制

项目首次使用需执行冷启动配置：

```bash
python3 -m src.cli orchestration cold-start
```

或通过 `/menu` 触发。

---

## 三、任务执行流程 (强制遵守)

### 3.1 任务启动前 (Pre-Task Checklist)

**必须完成以下检查**:

- [ ] **阅读相关文档**:
  - [ ] 阅读任务文件 (`collaboration/tasks/TASK-*.md`)
  - [ ] 阅读相关报告 (`collaboration/results/*.md`)
  - [ ] 阅读公告 (`notifications/*.md`)
  - [ ] 阅读角色编排配置 (`config/agent-orchestration.json`)

- [ ] **检查协同状态**:
  - [ ] 检查看板 (`Current Locks`)
  - [ ] 确认任务未被锁定
  - [ ] 确认当前角色绑定状态（通过 `/menu status`）

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
[IN_PROGRESS][owner=<role_id>][task=<task_id>][start=<ISO8601>]
```

**注意**: 使用角色代号（如 `AGENT_EXEC`），而非具体提供商名称。

### 3.2 任务执行中 (During Task)

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
   - 最佳实践 → 分享给其他角色

4. **角色协作**:
   - 需要架构决策 → 请求 `AGENT_ARCH` 支持
   - 需要测试验证 → 请求 `AGENT_TEST` 支持
   - 跨角色协作 → 通过 `/menu` 调整绑定

### 3.3 任务完成后 (Post-Task Checklist)

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
[DONE][owner=<role_id>][task=<task_id>][done=<ISO8601>]
```

---

## 四、命令协议

### 4.1 RUN 命令格式

```text
<PREFIX>.RUN

示例:
X.RUN  → 触发 AGENT_EXEC 执行任务
A.RUN  → 触发 AGENT_ARCH 架构任务
C.RUN  → 触发当前映射角色（可能是 AGENT_TEST 或自定义）
```

### 4.2 ACK 命令格式

```text
<PREFIX>.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>

示例:
X.ACK|task=TASK-001|status=ok|result=collaboration/results/RESULT_001.md
A.ACK|task=TASK-002|status=blocked|result=
```

**ACK 工具化输出（推荐）**:
```bash
python3 -m ai_collab.cli ack --task-id <id> --ai <role_id> --status ok
# 注意: --ai 参数使用角色代号（如 AGENT_EXEC）
```

---

## 五、资源使用指南

### 5.1 NotebookLM 使用指南

**何时使用**:
- 需要查询 AI 协作最佳实践
- 需要查询 Prompt Pack 设计参考
- 需要了解 OpenSpec 使用方法
- 需要了解角色编排机制

### 5.2 Context7 使用指南

**何时使用**:
- 需要查询框架/库的最新文档
- 需要查看代码示例
- 需要了解 API 用法

### 5.3 /menu 使用指南

**何时使用**:
- 需要查看角色绑定状态
- 需要激活/休眠角色
- 需要重新绑定 Agent 提供商
- 需要重定义命令前缀
- 需要切换工作模式（单 Agent / SubAgent / 多 Agent）

**调用方式**:
```text
/menu           # 打开主菜单
/menu status    # 显示当前状态
/menu roles     # 进入角色管理
/menu bind      # 进入绑定管理
/menu detect    # 检测 Agent 服务商
```

---

## 六、协同文档更新规则

### 6.1 共享报告更新规则

**适用文档**:
- `TEST_COVERAGE_REPORT_*.md`
- `IMPROVEMENT_SUMMARY_REPORT_*.md`

**更新流程**:

1. **检查锁定状态**:
   - 查看 `Current Locks` 看板
   - 如果有 `IN_PROGRESS` 标记，检查 owner

2. **认领任务**:
   ```text
   [IN_PROGRESS][owner=<role_id>][task=<task_id>][start=<ISO8601>]
   ```

3. **更新内容**:
   - 只更新自己认领的任务相关内容
   - 所有变更必须带时间戳

4. **完成标记**:
   ```text
   [DONE][owner=<role_id>][task=<task_id>][done=<ISO8601>]
   ```

### 6.2 任务文件更新规则

**适用文档**:
- `collaboration/tasks/TASK-*.md`

**更新流程**:

1. **开始前**:
   - 更新 `assignee_role` 字段（角色代号）
   - 更新状态为 `in_progress`

2. **执行中**:
   - 定期更新执行记录
   - 遇到问题立即标记

3. **完成后**:
   - 更新状态为 `completed`
   - 添加完成时间

---

## 七、质量标准

### 7.1 测试质量标准

**强制要求**:
- 测试通过率: 100%
- 新增代码覆盖率: ≥ 80%
- 边界条件测试: 必须包含
- 异常情况测试: 必须包含

### 7.2 代码质量标准

**强制要求**:
- 通过 Lint 检查 (flake8/pylint)
- 通过类型检查 (mypy)
- 无安全漏洞 (bandit)

### 7.3 文档质量标准

**强制要求**:
- 符合模板规范
- 包含时间戳
- 包含角色代号信息

---

## 八、违规处理

### 8.1 轻微违规

**定义**:
- 未使用推荐资源
- 文档格式不规范
- 进度更新不及时

**处理**: 提醒改进，累计 3 次升级为中度违规

### 8.2 中度违规

**定义**:
- 未遵守协同规则
- 质量标准不达标
- 未完成必需检查

**处理**: 任务标记为 `blocked`，要求返工改进

### 8.3 严重违规

**定义**:
- 破坏共享文档
- 并行冲突导致数据丢失
- 故意违反规则

**处理**: 回滚所有修改，重新分配任务

---

## 九、附录

### 9.1 标记模板汇总

```text
# 认领任务
[IN_PROGRESS][owner=<role_id>][task=<task_id>][start=<ISO8601>]

# 完成任务
[DONE][owner=<role_id>][task=<task_id>][done=<ISO8601>]

# 接管任务
[TAKEOVER][by=<role_id>][from=<owner>][time=<ISO8601>]

# 阻塞任务
[BLOCKED][owner=<role_id>][task=<task_id>][reason=<reason>][time=<ISO8601>]
```

### 9.2 相关文档

| 文档 | 路径 |
|-----|------|
| 协议规范 | `collaboration/PROTOCOL.md` |
| /menu 交互规范 | `collaboration/guides/MENU_INTERACTION_SPEC.md` |
| /menu 技能定义 | `collaboration/skills/menu_skill.md` |
| 角色编排配置 | `config/agent-orchestration.json` |
| 配置模板 | `config/agent-orchestration.template.json` |

---

**本准则对所有角色强制生效，违反将按违规处理流程执行**

**更新时间**: 2026-05-15