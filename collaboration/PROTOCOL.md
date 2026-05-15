# 多智能体协作协议（治理版 v3.0）

**版本**: 3.0.0  
**生效日期**: 2026-05-14  
**适用范围**: 动态角色编排的多 Agent 协作系统

---

## 一、协议目的

本协议定义**角色别名驱动的动态协作架构**，支持：
- 单 Agent 起步 → 多 Agent 渐进扩展
- SubAgent 内部分工模式
- 运行时动态调整角色绑定
- 命令前缀重定义与历史兼容

**核心转变**:
- **v2.0**: 硬编码特定 Agent 提供商（Claude Code、Codex、CodeArts）
- **v3.0**: 使用角色别名（AGENT_EXEC、AGENT_ARCH、AGENT_TEST），通过 `agent-orchestration.json` 动态映射

---

## 二、单一事实源（SSOT）

角色与调度口径按以下优先级解释：

1. `config/agent-orchestration.json`（运行时编排配置）
2. `.vscode/ai-collab.json`（VSCode 扩展配置）
3. 本文档 `collaboration/PROTOCOL.md`（协议规范）

若出现冲突，以高优先级文件为准。

---

## 三、角色分工（RACI）

### 3.1 角色别名定义

系统使用**语义化角色代号**，不绑定具体 Agent 提供商：

| 角色代号 | 显示名称 | RACI 定位 | 职责描述 |
|---------|---------|----------|---------|
| `AGENT_EXEC` | 主执行者 | R (Responsible) | 代码实现、重构、Bug修复 |
| `AGENT_ARCH` | 架构师 | A (Accountable) | 架构设计、技术选型、代码审查 |
| `AGENT_TEST` | 测试验证 | C (Consulted) | 单元测试、集成测试、质量保证 |
| `AGENT_DOC` | 文档编写 | C (Consulted) | 文档撰写、使用说明、API 文档 |
| `AGENT_PERF` | 性能优化 | C (Consulted) | 性能测试、负载分析、优化建议 |
| `AGENT_OPS` | 运维部署 | I (Informed) | 发布管理、环境配置、回滚演练 |

**扩展性**: 用户可通过 `/menu` 动态新增角色，上限为 `runtime_policy.max_roles`（默认 10）。

### 3.2 运行时角色解析

命令执行时，系统从 `agent-orchestration.json` 解析当前绑定：

```python
# 示例: X.RUN 命令解析流程
用户输入: X.RUN

解析流程:
1. 查询 command_prefixes: X.RUN → AGENT_EXEC
2. 查询 roles.AGENT_EXEC.binding:
   - provider: "claude_code"  (冷启动时确定)
   - model_variant: "sonnet"  (SubAgent 模式下)
   - status: "active"
3. 实际执行: Claude Code (Sonnet) 执行任务
```

### 3.3 User 角色（不变）

| 角色 | 责任定位 | 可做 | 禁止 |
|------|---------|------|------|
| **User（产品负责人）** | 最终决策者 | 定义目标、确定优先级、验收发布 | 不承担实现细节 |

---

## 四、冷启动机制

### 4.1 冷启动触发条件

项目首次使用时，检测 `agent-orchestration.json` 状态：

```python
if not exists("agent-orchestration.json"):
    # 从模板复制
    copy("agent-orchestration.template.json", "agent-orchestration.json")

orchestration = load("agent-orchestration.json")

if orchestration.binding_status == "uninitialized":
    trigger_cold_start_wizard()
```

### 4.2 冷启动流程

```
┌──────────────────────────────────────────────┐
│ 1. 检测可用 Agent 服务商                      │
│    - Claude Code (连接检测)                   │
│    - Codex CLI (进程检测)                     │
│    - Gemini CLI (进程检测)                    │
│    - CodeArts Agent (进程检测)                │
└──────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────┐
│ 2. 选择启动模式                               │
│    - [1] 单 Agent 模式                        │
│    - [2] SubAgent 模式 (内部分工)              │
│    - [3] 多 Agent 模式 (渐进扩展)              │
└──────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────┐
│ 3. 配置命令前缀                               │
│    - 确认 A.RUN, X.RUN, C.RUN 映射             │
│    - 可自定义前缀                              │
└──────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────┐
│ 4. 生成最终配置                               │
│    - binding_status = minimal/active          │
│    - roles.*.binding.provider = 选中值        │
│    - cold_start_config.wizard_completed = true│
└──────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────┐
│ 5. 协作系统激活                               │
│    - 所有命令即时可用                          │
│    - 可通过 /menu 随时调整                     │
└──────────────────────────────────────────────┘
```

### 4.3 冷启动配置示例

**单 Agent 模式配置**:

```json
{
  "binding_status": "minimal",
  "startup_mode": "single_agent",
  "roles": {
    "AGENT_EXEC": {
      "binding": {
        "provider": "claude_code",
        "status": "active"
      }
    },
    "AGENT_ARCH": {
      "binding": {
        "provider": null,
        "status": "dormant"
      }
    },
    "AGENT_TEST": {
      "binding": {
        "provider": null,
        "status": "dormant"
      }
    }
  }
}
```

**SubAgent 模式配置**:

```json
{
  "binding_status": "active",
  "startup_mode": "sub_agent",
  "roles": {
    "AGENT_EXEC": {
      "binding": {
        "provider": "claude_code",
        "model_variant": "sonnet",
        "status": "active"
      }
    },
    "AGENT_ARCH": {
      "binding": {
        "provider": "claude_code",
        "model_variant": "opus",
        "status": "active"
      }
    },
    "AGENT_TEST": {
      "binding": {
        "provider": "claude_code",
        "model_variant": "haiku",
        "status": "active"
      }
    }
  }
}
```

**多 Agent 模式配置**:

```json
{
  "binding_status": "active",
  "startup_mode": "multi_agent",
  "roles": {
    "AGENT_EXEC": {
      "binding": {
        "provider": "claude_code",
        "status": "active"
      }
    },
    "AGENT_ARCH": {
      "binding": {
        "provider": "codex_cli",
        "status": "active"
      }
    },
    "AGENT_TEST": {
      "binding": {
        "provider": "codearts_agent",
        "status": "active"
      }
    }
  }
}
```

---

## 五、运行时动态调整

### 5.1 /menu 控制面板

通过 `/menu` 命令随时调整配置：

| 功能模块 | 支持操作 |
|---------|---------|
| 角色管理 | 新增/编辑/删除/激活角色 |
| Agent 绑定 | 重新分配/启用 SubAgent/接入新服务商 |
| 命令配置 | 重定义前缀/新增自定义命令 |
| 工作模式切换 | 单 Agent ↔ SubAgent ↔ 多 Agent |
| 快照与回滚 | 创建快照/回滚历史配置 |
| 导出/导入 | 配置备份/团队共享 |

详细交互规范见: `collaboration/guides/MENU_INTERACTION_SPEC.md`

### 5.2 配置热更新

所有 `/menu` 变立即生效（`runtime_policy.allow_hot_reload = true`）：

```python
# 示例: 激活新角色
用户执行: /menu bind → 激活 AGENT_PERF → Gemini CLI

系统响应:
→ roles.AGENT_PERF.binding.status = active
→ roles.AGENT_PERF.binding.provider = gemini_cli
→ binding_status: partial → active
→ history 记录: role_activated
→ 即时可使用 PERF.RUN 命令
```

### 5.3 命令重定义流程

```python
# 示例: 重定义 C.RUN 命令
当前映射: C.RUN → AGENT_TEST
用户重定义: C.RUN → AGENT_PERF

系统响应:
→ command_prefixes["C.RUN"] = "AGENT_PERF"
→ history 记录: command_redefined
→ 历史兼容模式启用:
  - 旧格式 C.ACK|task=... 自动解析为原角色
  - 新格式 C.RUN 映射到新角色
```

---

## 六、命令协议

### 6.1 RUN 命令格式

```text
<PREFIX>.RUN

示例:
X.RUN  → 触发 AGENT_EXEC 执行任务
A.RUN  → 触发 AGENT_ARCH 架构任务
C.RUN  → 触发当前映射角色（可能是 AGENT_TEST 或自定义）
```

### 6.2 ACK 命令格式

```text
<PREFIX>.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>

示例:
X.ACK|task=TASK-001|status=ok|result=collaboration/results/RESULT_001.md
A.ACK|task=TASK-002,TASK-003|status=blocked|result=
```

**ACK 工具化输出（推荐）**:

```bash
python3 -m ai_collab.cli ack --task-id <id> --ai <role_id> --status ok
# 注意: --ai 参数现在使用角色代号（如 AGENT_EXEC），而非具体提供商名称
```

### 6.3 历史兼容保证

`command_prefixes.history_compatible = true` 时：

```python
# 历史格式自动转换
历史文件内容: C.ACK|task=TASK-001
→ 解析为: AGENT_TEST.ACK|task=TASK-001
→ 即使当前 C.RUN 已映射到 AGENT_PERF
→ 历史任务仍正确识别为测试角色完成

新文件内容: PERF.ACK|task=TASK-002
→ 解析为: AGENT_PERF.ACK|task=TASK-002
→ 使用自定义命令前缀
```

---

## 七、OpenSpec 与工单协同模型

### 7.1 OpenSpec 负责"能力生命周期"

Prompt Pack 相关能力变更必须走 OpenSpec，覆盖：
- 生成（Generation）
- 审核（Review）
- 迭代（Iteration）
- 归档（Archive）

### 7.2 工单负责"执行派发"

OpenSpec 变更获批后，按工单派发实现任务：
- 任务文件：`collaboration/tasks/TASK-*.md`
- 结果文件：`collaboration/results/RESULT_*.md`
- 状态文件：`logs/collaboration_state.json`

### 7.3 绑定规则（强制）

每个执行工单必须声明：
- `change_id`（对应 OpenSpec 变更）或明确标注 `bugfix/no-spec`
- `assignee_role`（角色代号，如 AGENT_EXEC）
- `assignee_provider`（实际提供商，从 orchestration 解析）

---

## 八、任务流转

### 8.1 标准流程

1. **需求澄清（AGENT_ARCH）**
   输出 V1 范围、非目标、风险和验收标准。

2. **规范立项（OpenSpec）**
   新能力/架构变更先出 proposal + tasks + spec delta。

3. **工单分派（AGENT_ARCH）**
   AGENT_EXEC 作为默认实现 owner；AGENT_TEST 作为并行支持。

4. **执行与回传（AGENT_EXEC/AGENT_TEST）**
   产出代码、测试、结果文档、风险说明。

5. **门禁验收（AGENT_ARCH + User）**
   通过测试和验收后合并；未通过则回到第 3 步。

### 8.2 默认派发策略（角色视角）

| 任务类型 | Lead Role | Support Role |
|---------|----------|--------------|
| 架构/方案/跨模块设计 | AGENT_ARCH | AGENT_EXEC, AGENT_TEST |
| 功能实现/重构 | AGENT_EXEC | AGENT_ARCH, AGENT_TEST |
| 测试补齐/回归验证 | AGENT_TEST | AGENT_EXEC, AGENT_ARCH |
| 文档与使用说明 | AGENT_DOC | AGENT_ARCH, AGENT_EXEC |
| 发布/运维/回滚演练 | AGENT_OPS | AGENT_EXEC, AGENT_ARCH |

---

## 九、执行心跳与反空转门禁

### 9.1 状态更新渠道

- 禁止直接编辑 `logs/collaboration_state.json` 改任务状态。
- 任务状态变更只能通过 CLI：
  ```bash
  python3 -m ai_collab.cli tasks update --task-id <id> --status <status> --note "<note>"
  ```

### 9.2 implementing/testing 心跳 SLA

- `implementing/testing` 达到预警阈值时：
  - controller 自动写入 prewarning 提示
  - 执行者需在超时前回写心跳并更新证据路径

- `implementing/testing` 状态超过 `activeTimeoutSec` 无更新：
  - controller 自动降级为 `blocked`
  - 必须补充心跳说明

### 9.3 blocked 升级规则

- `blocked` 状态超过 `blockedTimeoutSec` 无更新：
  - controller 自动升级为 `failed`
  - 需由 AGENT_ARCH 重新派单或明确回滚/重启方案

---

## 十、会话交接

### 10.1 会话压缩前续接交接

为避免上下文丢失，使用标准 handoff 命令：

```bash
python3 -m ai_collab.cli sessions handoff
```

流程：
1. 在当前对话结束前，先运行 `sessions handoff`
2. 打开新生成的 `collaboration/results/SESSION_CONTINUATION_HANDOFF_*.md`
3. 复制其中 `Paste This Into The Next Conversation` 代码块
4. 将该代码块作为新对话的第一条消息
5. 完成后，再压缩或结束旧对话

---

## 十一、生效与回滚

### 11.1 生效条件

本协议自 2026-05-14 赵生效，适用于：
- 新建工单与新一轮任务派发
- 冷启动配置后的所有协作

### 11.2 回滚触发

若出现以下任一情况，通过 `/menu rollback` 回滚至上个快照：
- 命令映射混乱导致任务无法正确解析
- 角色绑定状态不一致超过 24h
- 发布门禁无法形成闭环

---

## 十二、废弃声明

以下旧口径在当前治理阶段视为废弃：
- 硬编码特定 Agent 提供商名称的协议条款
- 固定的"Claude Code + Codex + CodeArts"架构描述
- 不可动态调整的角色分工规则

---

## 十三、配置文件位置

| 配置项 | 文件路径 |
|-------|---------|
| 角色编排主配置 | `config/agent-orchestration.json` |
| 配置模板 | `config/agent-orchestration.template.json` |
| Schema 定义 | `config/agent-orchestration.schema.json` |
| /menu 交互规范 | `collaboration/guides/MENU_INTERACTION_SPEC.md` |
| VSCode 扩展配置 | `.vscode/ai-collab.json` |
| 协作状态 | `logs/collaboration_state.json` |

---

**更新时间**: 2026-05-14  
**更新内容**: 协议 v3.0 - 动态角色编排架构