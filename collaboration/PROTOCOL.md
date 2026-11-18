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
# 示例: A.RUN 命令解析流程
用户输入: A.RUN

解析流程:
1. 查询 command_prefixes: A.RUN → AGENT_EXEC
2. 查询 roles.AGENT_EXEC.binding:
   - provider: "codearts_agent"  (冷启动时确定)
   - model_variant: "sonnet"  (SubAgent 模式下)
   - status: "active"
3. 实际执行: 当前绑定的提供商执行任务
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
A.RUN  → 触发 AGENT_EXEC 执行任务
X.RUN  → 触发 AGENT_ARCH 架构任务
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
- `session_id`（执行该工单的会话标识）
- `model_id`（执行该工单的模型标识）

`session_id` 与 `model_id` 合起来才算「身份」。**`assignee_provider`（厂商标签）不再是身份字段**，
按 §12 降级为过渡期路由键：它回答「消息发给谁」，不回答「谁做的」。

时间切点：`2026-11-16`（含）之后创建的工单缺失身份即契约不合法。切点之前创建的历史工单
按 legacy 处理——不判错，但会在契约校验输出中以 `legacy_identity=N` 显式计数，
且**不得为其编造身份值**（当时会话已不存在，编造比缺失更坏）。

身份来源只能有两个：人显式声明，或从会话注册表事实反查。除此之外不接受任何推断。

### 7.5 身份与路由分离

身份（`session_id` + `model_id`）与路由（`assignee`）是两件事，不得互相冒充：

| 维度 | 回答的问题 | 事实源 | 可变性 |
|------|-----------|--------|--------|
| 身份 | 谁在哪个模型上完成了这个工单 | 工单契约 | 一次性事实，写完不改 |
| 路由 | 消息/回执该发给谁 | 会话注册表 | 可随会话重启而变 |

推论三条：

1. **同一身份可以换路由。** 会话重连后 transport 变了，身份不该变，工单不该改。
2. **同一路由可以承载多个身份。** 同一个厂商可以有多个并行会话，因此厂商名永远无法唯一定位责任主体。
3. **只声明身份的工单必须能跑。** 系统按会话注册表反查路由键；反查不到时**拒绝创建工单**，
   而不是写一个空路由键让消息在更远的地方丢失。

> **过渡期说明**：运行时路由仍按 `assignee` 过滤（ack / 干预队列 / 缺失 ACK / 看门狗 / 会话健康）。
> 这属于 §12 的兼容白名单范围，淘汰条件见 §12。

### 7.6 任务事实源与身份审计流程

`collaboration/tasks/TASK-*.md` 是工单契约的**唯一事实源**；
`logs/collaboration_state.json` 是由 md 派生、每个工作树各一份的本机账本（gitignored）。
因此账本条数**不等于**全量工单数：全新检出的账本为空，此时 `tasks migrate-identity`
报 `total=0` 只说明「这台机器没同步过」，不说明「没有历史欠账」。

标准流程（两步，第一步不可省略）：

```
python3 -m ai_collab.cli tasks sync-from-md       # md → 账本，只写已声明事实
python3 -m ai_collab.cli tasks migrate-identity   # 只读审计
```

约束四条：

1. `sync-from-md` **单向**：从 md 写账本，不回写 md；只写 md 已声明的字段，
   缺失身份留空，由切点规则判 `legacy` / `partial`。**禁止推导或编造身份。**
2. 审计**不自动同步**，只读账本；输出必须给出 `input_source`——同步时间与条数，
   或明确写「未同步过 md」。不得让一个工作树的条数看起来像全量。
3. 账本中若有**没有对应 md** 的本机条目，同步不删除它。审计的 `total` 会大于
   `synced_count`；两者同时出现在输出中，须据差值解释覆盖范围。
4. 切点按**日期**判定。落在切点当天、但早于身份机制落地时刻的历史工单会判 `missing`，
   这是切点粒度的边界案例，**不得为此编造身份补齐**，须先裁定切点规则（独立 change）。

### 7.4 结果文件四段契约（强制）

> **历史勘误（2026-10-24 复核）**：本契约此前被多处标注为「PROTOCOL §7.3 契约」，
> 但 §7.3 是**绑定规则**（当时为 change_id / assignee_role / assignee_provider），
> 从未定义结果文件格式——引用与实际内容对不上号。现于本节正式定义，
> 此前所有「§7.3 四段」表述一律改指本节。
>
> **二次勘误（2026-11-16）**：§7.3 的第三个字段已由 `assignee_provider` 改为
> `session_id` + `model_id`（见上），本条勘误保留历史表述以便追溯，不再代表现行口径。

每个执行工单的**结果文件**（`collaboration/results/RESULT_*.md`）必须含四段：

| 段落 | 标题 | 内容要求 |
|------|------|---------|
| 执行命令 | `## 执行命令` | 逐条列出实际执行的命令 |
| 验证结果 | `## 验证结果` | 每条验收命令的**真实输出**；须含「测试结论」小节 |
| 风险 | `## 风险` | 遗留风险与影响面 |
| 回滚 | `## 回滚` | 出问题时的回滚方式 |

另需：
- 一行**可解析的状态行**（如 `- **状态**: completed`）；
- 工单 `acceptance_commands` 里的每条命令字符串**原样**出现在结果报告中。

#### 7.4.1 匹配规则（2026-11-18 补，台账 N41）

上表列的是「概念」，不是「字面字符串」。四段各自必须有**标题**表达该概念，
判据如下（权威实现在 `ai_collab/result_file_contract.py`）：

| 规则 | 说明 | 例 |
|---|---|---|
| 必须是标题 | H2–H4 标题，正文里提到不算 | 正文写「风险：无」**不**满足风险段 |
| 允许前导编号 | `1.` `2.3` `六、` `(1)` 等前缀会被剥掉再匹配 | `## 4. 执行命令` ✅ |
| 允许合并标题 | 复合标题按分隔符拆段，任一段命中即算 | `## 风险与回滚` 同时满足风险+回滚 |
| 必须以概念**开头** | 只认「某一段以同义词开头」，不认「标题里出现」 | `## 回滚方案` ✅ / `### 关于回滚的说明` ❌ |

「验证结果」组接受 `## 验证结果`、`## 测试结论`、`## 验证结果 / ### 测试结论` 等形态——
即「测试结论」既可作为 `验证结果` 的**小节**，也可独立成段，两种都算。

> **为什么把规则写死到这种程度**：此前这条契约有两份互相矛盾的实现对
> ——`state_manager` 用三组替代词且把「回滚」当成「风险」的替代词（回滚零强制），
> 回执桥 `scripts/agent_receipt_bridge.py` 要求字面 `## 测试结论`（无替代词）。
> 结果是按本节写出的**合规**结果文件被回执桥判 invalid，卡在链路最后一步；
> 而缺强制段 `## 回滚` 的文件两处门禁都放行——方向正好相反。
> 现已收敛为一份判据：`ai_collab/result_file_contract.py` 是唯一实现，
> 回执桥出于「可单独拷走执行」保留本地副本，由
> `tests/unit/test_result_file_contract.py` 强制两侧逐字一致 + 行为等价。

**机器校验实现**：`ai_collab/result_file_contract.py` 的 `SECTION_GROUPS` 与
`missing_sections()`；`ai_collab/state_manager.py` 的
`TASK_RESULT_NEGATIVE_SIGNAL_MARKERS` 是另一组判据（否定信号，不属于章节契约）。
`ai_collab/state_manager.py` 的 `TASK_RESULT_REQUIRED_SECTION_GROUPS` 只是
`SECTION_GROUPS` 的兼容视图，不再是独立判据。

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

### 12.1 过渡兼容白名单（`SUPPORTED_ASSIGNEES`）

`ai_collab/ack_protocol.py` 的 `SUPPORTED_ASSIGNEES = {"claude_code", "codearts_agent", "codex"}`
与本节「硬编码提供商名称」表面矛盾，特此定性：

- 它是**过渡期兼容白名单**，不是身份定义。身份见 §7.3（`session_id` + `model_id`）。
- 它的作用范围仅限运行时路由与回执投递（ack / 干预队列 / 缺失 ACK / 看门狗 / 会话健康）。
- 它**不得**被用作工单契约的必填项，也不得作为「谁做的」的证据。

**淘汰条件（可判定，不是"以后再说"）**：同时满足以下三条即可删除该常量。

1. ack / 干预队列 / 缺失 ACK / 看门狗 / 会话健康五个模块的路由入参改为 `session_id`；
2. 会话注册表提供 `session_id → transport` 的完整映射，且投递侧（桥接脚本）改为按会话投递；
3. 现存历史工单的 `legacy_identity` 计数归零（或全部到达可核验的终态）。

在此之前，新增执行主体需要改这个常量——这是已知的技术债，登记在案，不算合规缺口。

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

## 十四、并发工作区安全

> **新增日期**: 2026-09-26  
> **触发样本**: 2026-09-26 并行冲突事件（分支漂移 + 基线过期 + 归属不清 + 测试污染）  
> **技术设计**: `docs/CONCURRENT_GUARD_DESIGN.md`  
> **服务层实现**: `ai_collab/concurrent_guard.py`

### 14.1 工作区独占原则

- 同一 git working tree 同一时刻**至多一个 Agent 处于写模式**
- 多 Agent 并行时，各自使用**独立 worktree**（`git worktree add`）或**独立 clone**
- 共享工作区仅允许**只读**操作（inspect / 分析）
- **禁止**在未确认归属的情况下执行 `git add -A` / `git checkout -- .` / `git reset --hard`

### 14.2 分支约定

- 每个任务在**声明的分支**上进行，写入任务文件 `branch` 字段
- 提交前必须校验 `git rev-parse --abbrev-ref HEAD` == 声明分支
- 禁止在未声明的分支上提交
- **检测信号**: `concurrent_guard.detect_branch_drift(workspace, expected_branch)`

### 14.3 基线声明

- 任务开始时记录 `baseline_commit`（`git rev-parse HEAD`）
- 提交前校验 `watch_paths` 未被他人推进（`baseline_commit..HEAD` 区间无变更）
- 基线过期时先 rebase / 重新核实，禁止直接提交
- **检测信号**: `concurrent_guard.detect_baseline_staleness(workspace, baseline_commit, watch_paths)`

### 14.4 归属标记

- 未提交改动通过**会话标记**（`.ai_collab_session.json`）关联 owner
- 提交前区分「本会话改动」vs「他人改动」
- **初始实现**: mtime 启发式（文件 mtime 早于会话开始时间 → 判定为 foreign）— 定位为**软警告**，不阻断
- **后续增强**: `.ai_collab_session.json` 记录会话上下文与预期工作区状态，提供真证归属判断
- **检测信号**: `concurrent_guard.detect_foreign_changes(workspace, session_started_at)`

### 14.5 门禁分层

按既有门禁分层原则（硬门禁对齐真证，软警告承载启发式）：

| 信号 | 性质 | 门禁等级 | 可阻断 |
|------|------|---------|--------|
| 分支漂移（G1） | git 真证 | **硬门禁** | ✅ |
| 基线过期（G2） | git 真证 | **硬门禁** | ✅ |
| 归属不清（G3） | mtime 启发式 | **软警告** | ❌（见下） |
| 测试污染（G4） | pytest 配置 | 测试层修复 | ❌ |
| 工作树分支冲突（G11） | git 真证 | **硬门禁** | ✅ |

> **G3 的例外**：G3 默认只告警不阻断；但配置
> `concurrentGuard.foreignChangeSeverity: "high"` 时，它会进入
> **违规列表**并按违规阻断（此时风险级别为 `high`、放行结论为假）。
> 也就是说「G3 不可阻断」说的是**默认配置**下的行为。

> **本表编号非连续（中间有空号）**：门禁编号只有 **G1 / G2 / G3 / G4 / G11** 这五条是
> **定义过**的，5 到 10 这一段从未定义。引用门禁前请先回本表核对，**不要按编号连惯性去推**：
> 2026-11-18 就有人据一份旧 plan 里「门禁从 1 到 10 都齐」的说法，凭空凑出「第 7 条写入门」
> 「第 10 条 worktree-vs-commit」，并以「这两条要求用户确认」为由挡住了一次合法提交（台账 N38）。
> 需要新门禁时，**新编一个未占用的号并在本表登记**，不要为了迁就旧文档去补齐空号。
> 另：`npm run build` 后比对 dist 与源码 hash / 关键字属**构建一致性检查**，不是本表门禁，
> 不要借门禁编号描述它。
>
> 核对命令（本注不写空号的字面编号，就是为了让这条命令继续可判）：
> `grep -o 'G[0-9]\+' collaboration/PROTOCOL.md | sort -u` 应输出
> `G1 G11 G2 G3 G4`。多出任何编号，说明本表以外又出现了未登记的门禁引用。

### 14.6 工作树分支冲突（G11）

**现象**：`git worktree list` 里两个及以上工作树签出同一个分支。

**为什么它是硬门禁而不是软警告**：正常 git 造不出这个状态。`git worktree add`
会拒绝重复分支，`git checkout <branch>` / `git switch <branch>` 也会以
`fatal: '<branch>' is already checked out at '<path>'` 拦住。能造出它的只有
**大写 `-B` / `-C`**（语义是「强制重置该分支」）或手工 `update-ref`——
两者都绕过「该分支已被别处签出」的检查。

**危害**：`HEAD` 是 `ref: refs/heads/<branch>`，而 `refs/` 由所有工作树共享。
移动引用 = **同时移动所有指向它的 HEAD**，但各工作树的索引不跟着走。于是
`git status` 会把「索引 vs 新 HEAD」的基线漂移全部报成改动，包括 `D` 型
「删除」假象（文件根本没被删）。2026-11-16 实测：主工作区在一个 worktree 里
执行 `checkout -B main origin/main` 后，HEAD 被动前移，`status` 从 153 条
在途改动暴涨到 424 条（漂移 273 条路径）。

**检测**：`concurrent_guard.detect_worktree_branch_collisions(workspace)`，
解析 `git worktree list --porcelain`，只读。detached HEAD 的工作树没有
`branch` 行，不参与计数（也不会掩盖真冲突）。

**两个接入点**（缺一不可）：

| 接入点 | 何时拦 | 取值 |
|--------|--------|------|
| `concurrent guard` | 显式跑并发门禁时 | 默认硬门禁，退出码 `2` |
| `governance preflight` 第六项 | 每次开工检查时 | 冲突即该项 FAIL、总 `FAIL`、退出码 `1` |

`preflight` 那一项是**开工即拦**的关键：只挂 `concurrent guard` 时，从不跑该命令的人
完全绕得过去。接进 `preflight` 后它与其他五项同在一条命令里，无法被单独跳过。

**「查不到」的口径**：`git worktree list` 失败（非 git 目录、git 不在 PATH）时，
该项判 **PASS 但 detail 明写「无法判定…未据此判违规」**——查不到不等于有冲突，
可也不能据此判违规；detail 披露保证这个绿不是静默的。

**修法**：冲突不能靠 `--force-workspace` 覆盖解决——覆盖只是让门禁闭嘴，
失真仍在那里。先让多余的工作树脱离该分支：

```
git -C <多余工作树> checkout --detach
```

若只想移动引用、不碰任何工作树，用 `git update-ref refs/heads/<branch> <commit>`，
不要用 `-B` / `-C`。

**降级开关**：`concurrentGuard.worktreeCollisionSeverity: "warning"` 可把
`concurrent guard` 侧的判定降为软警告（仍进 `warnings`，不静默）。默认 `high`。
`preflight` 侧不读这个开关——开工检查只回答「有没有冲突」，不做分级。

### 14.7 综合风险评级

`concurrent_guard.assess_concurrent_risk()` 综合四信号输出风险等级：

| 条件 | risk_level | allowed |
|------|-----------|---------|
| 任一硬门禁信号触发 | high | False |
| 仅软警告信号 | medium | True |
| 无信号 | low | True |

---

**更新时间**: 2026-09-26  
**更新内容**: 协议 v3.0 - 动态角色编排架构；新增第十四章「并发工作区安全」