# AI 协作开发标准规范 (v3.0)

## 版本信息

- **版本**: v3.0.0
- **生效日期**: 2026-05-15
- **适用范围**: 动态角色编排的多 Agent 协作系统

---

## 1. 协作原则

### 1.1 单一职责

- 每个 Agent 在同一时间只处理一个任务
- 任务完成后才能接受新任务
- 禁止多任务并行处理

**例外说明**:

- `AGENT_ARCH` 可在**单一父任务内部**使用 `spawn_agent` 进行受控委派
- 该能力不视为新增独立外部任务
- 前提是不得绕过状态、锁、写集隔离与正式 ACK/工单流程
- 对所有正式 assignee 而言，正式闭环都要求显式 ACK 证据
- 详细规则见 `collaboration/guides/CODEX_SPAWN_AGENT_USAGE_GUIDELINES.md`

### 1.2 状态透明

- 所有任务状态必须实时同步到 `collaboration_state.json`
- 文件修改前必须检查冲突状态
- 状态变更必须记录时间戳
- `ai_type` 代表原始派单对象，`assignee`/`ownership.owner` 代表当前责任 owner
- 合法 takeover 后两者不一致是允许的

### 1.3 日志完整

- 每次开发必须生成结构化日志
- 日志必须包含：任务ID、时间、变更、结果
- 日志格式统一使用 `dev-record-template.md`

---

## 2. 开发前检查清单

### 2.1 通用检查项（所有角色）

```markdown
- [ ] 检测到激活词 `2X`
- [ ] 读取角色编排配置 `config/agent-orchestration.json`
- [ ] 读取 `AI-COLLABORATION-STANDARDS.md`
- [ ] 检查 `collaboration_state.json` 冲突状态
- [ ] 确认目标文件未被标记为 `implementing` 或 `testing`
- [ ] 确认当前角色绑定状态（通过 `/menu status`）
- [ ] 创建开发日志文件
```

### 2.2 角色特定检查项

**AGENT_EXEC（主执行者）**:
```markdown
- [ ] 确认绑定到有效 Agent 提供商
- [ ] 确认任务属于实现类工作
- [ ] 准备代码实现计划
```

**AGENT_ARCH（架构师）**:
```markdown
- [ ] 确认绑定到有效 Agent 提供商
- [ ] 确认任务属于架构/设计类工作
- [ ] 准备技术决策方案
```

**AGENT_TEST（测试验证）**:
```markdown
- [ ] 确认绑定到有效 Agent 提供商
- [ ] 确认任务属于测试/验证类工作
- [ ] 准备测试计划
```

---

## 3. 冲突解决机制

### 3.1 冲突检测

当 Agent 尝试修改文件时，系统检查：

1. 目标文件是否存在于其他任务的 `files` 列表中
2. 对应任务状态是否为 `implementing` 或 `testing`
3. 如果是，标记为冲突并阻止操作

### 3.2 冲突解决流程

```text
检测到冲突
    ↓
暂停当前操作
    ↓
通知用户冲突详情
    ↓
等待用户决策
    ↓
执行用户选择方案
```

### 3.3 用户决策选项

- **选项A**: 等待其他任务完成后再执行
- **选项B**: 取消其他任务，优先执行当前任务
- **选项C**: 合并修改（仅适用于非冲突行）
- **选项D**: 手动指定文件分区，各自修改不同部分

---

## 4. 禁止行为列表

### 4.1 通用禁止

- ❌ 不读取规则直接开始开发
- ❌ 不检查冲突状态直接修改文件
- ❌ 不记录开发日志
- ❌ 同时处理多个未关联的任务
- ❌ 修改标记为 `conflict` 的文件
- ❌ 删除或修改其他 Agent 的日志文件
- ❌ 绕过状态检查机制
- ❌ 使用硬编码 Agent 名称而非角色代号

### 4.2 角色特定禁止

**AGENT_EXEC**:
- ❌ 跳过 `Test` 阶段直接标记完成
- ❌ 不生成测试覆盖报告

**AGENT_ARCH**:
- ❌ 跳过 `Review` 阶段直接标记完成
- ❌ 不生成架构决策文档

**AGENT_TEST**:
- ❌ 跳过 `Validate` 阶段直接标记完成
- ❌ 不生成验证报告

---

## 5. 质量门控标准

### 5.1 代码质量

- 所有代码必须通过类型检查
- 所有函数必须有类型注解
- 所有复杂逻辑必须有注释

### 5.2 测试覆盖

- 新功能必须有对应的测试用例
- 测试覆盖率不得低于 80%
- 所有测试必须通过才能标记完成

### 5.3 文档要求

- 所有公共 API 必须有文档字符串
- 所有配置文件必须有注释说明
- 所有变更必须在日志中记录

---

## 6. 状态定义

### 6.1 任务状态

| 状态 | 描述 |
|------|------|
| `pending` | 任务已创建，等待执行 |
| `planning` | 正在制定执行计划 |
| `implementing` | 正在实现代码 |
| `testing` | 正在测试/验证 |
| `completed` | 任务已完成 |
| `failed` | 任务执行失败 |
| `cancelled` | 任务已取消 |

### 6.2 文件状态

| 状态 | 描述 |
|------|------|
| `clean` | 文件未被修改 |
| `modified` | 文件已被修改但未提交 |
| `conflict` | 文件存在冲突 |
| `locked` | 文件被锁定，禁止修改 |

### 6.3 角色绑定状态

| 状态 | 描述 |
|------|------|
| `uninitialized` | 冷启动未完成 |
| `minimal` | 仅单个角色激活 |
| `partial` | 部分角色激活 |
| `active` | 所有角色激活 |

---

## 7. 日志规范

### 7.1 日志位置

```text
logs/<role_id>/YYYY-MM/YYYY-MM-DD_<task>.md

示例:
logs/AGENT_EXEC/2026-05/2026-05-15_TASK-001.md
logs/AGENT_ARCH/2026-05/2026-05-15_TASK-002.md
logs/AGENT_TEST/2026-05/2026-05-15_TASK-003.md
```

### 7.2 日志内容

必须包含以下章节：

1. 任务信息（ID、描述、时间）
2. 执行计划
3. 执行过程记录
4. 变更文件列表
5. 测试/验证结果
6. 问题与解决方案
7. 总结与下一步

### 7.3 时间戳格式

- 日期: `YYYY-MM-DD`
- 时间: `HH:MM:SS`
- 完整格式: `YYYY-MM-DD HH:MM:SS`

---

## 8. 命令协议规范

### 8.1 RUN 命令

```text
<PREFIX>.RUN

标准前缀:
X.RUN → AGENT_EXEC（主执行者）
A.RUN → AGENT_ARCH（架构师）
C.RUN → AGENT_TEST（测试验证）

自定义前缀:
PERF.RUN → AGENT_PERF（性能优化）
DOC.RUN → AGENT_DOC（文档编写）
```

### 8.2 ACK 命令

```text
<PREFIX>.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>

示例:
X.ACK|task=TASK-001|status=ok|result=collaboration/results/RESULT_001.md
A.ACK|task=TASK-002|status=blocked|result=
```

### 8.3 命令重定义

通过 `/menu commands` 可重定义命令前缀映射：

```text
原映射: C.RUN → AGENT_TEST
新映射: C.RUN → AGENT_PERF

历史兼容模式自动启用，旧格式仍可正确解析
```

---

## 9. 应急处理

### 9.1 系统故障

如果状态文件损坏或丢失：

1. 立即停止所有开发活动
2. 从备份恢复状态文件
3. 如果无备份，重新初始化状态
4. 通知用户故障情况

### 9.2 冲突升级

如果冲突无法自动解决：

1. 标记冲突为 `unresolved`
2. 记录冲突详情到 `collaboration_issues.json`
3. 通知用户手动介入
4. 等待用户决策

### 9.3 角色绑定异常

如果角色绑定状态不一致：

1. 通过 `/menu status` 检查当前绑定
2. 通过 `/menu rollback` 回滚到稳定快照
3. 通过 `/menu cold-start` 重新配置

---

## 10. 附录

### 10.1 文件清单

| 文件 | 作用 |
|------|------|
| `config/agent-orchestration.json` | 角色编排配置 |
| `config/agent-orchestration.template.json` | 配置模板 |
| `collaboration/PROTOCOL.md` | 协议规范 |
| `collaboration/COLLABORATION_GUIDELINES.md` | 协作准则 |
| `collaboration/guides/MENU_INTERACTION_SPEC.md` | /menu 交互规范 |
| `AI-COLLABORATION-STANDARDS.md` | 协作标准 |
| `collaboration_state.json` | 协作状态 |
| `collaboration_issues.json` | 问题记录 |

### 10.2 CLI 命令参考

```bash
# 查看角色状态
python3 -m src.cli orchestration status

# 冷启动配置
python3 -m src.cli orchestration cold-start

# 检测 Agent 服务商
python3 -m src.cli orchestration detect

# 角色管理
python3 -m src.cli orchestration roles list
python3 -m src.cli orchestration roles activate --role-id AGENT_EXEC --provider claude_code

# 快照管理
python3 -m src.cli orchestration snapshot create --note "备份"
python3 -m src.cli orchestration snapshot rollback --snapshot-id snap_001

# 查看历史
python3 -m src.cli orchestration history --limit 20
```

### 10.3 更新记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v3.0.0 | 2026-05-15 | 升级为动态角色编排架构 |
| v1.0.0 | 2026-02-25 | 初始版本 |

---

**本标准对所有角色强制生效，违反将按违规处理流程执行**