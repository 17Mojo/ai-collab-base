# 多智能体协作协议（治理版）

**版本**: 2.0.0  
**生效日期**: 2026-03-02  
**适用范围**: Codex + Claude Code + CodeArts Agent 协作执行

---

## 一、协议目的

本协议用于固定“谁负责决策、谁负责执行、谁负责辅助”，并把 OpenSpec 与工单体系打通，确保 Prompt Pack 与基座项目都能稳定落地。

---

## 二、单一事实源（SSOT）

角色与调度口径按以下优先级解释：

1. `.vscode/ai-collab.json`（运行时编排配置）
2. `rules/codex_agent_rules.md`（Codex 技术合伙人管理规则）
3. 本文档 `collaboration/PROTOCOL.md`

若出现冲突，以高优先级文件为准。

---

## 三、角色分工（RACI）

| 角色 | 责任定位 | 可做 | 禁止 |
|------|---------|------|------|
| **User（产品负责人）** | 最终决策者 | 定义目标、确定优先级、验收发布 | 不需要承担实现细节 |
| **Codex** | 开发管理负责人（技术合伙人） | 需求收敛、方案拆解、任务分派、质量门禁、风险回滚 | 不能绕过用户做产品决策 |
| **Claude Code** | 主执行者 | 按工单实现、联调、补测试、提交证据 | 不承担全局治理裁决 |
| **CodeArts Agent** | 执行辅助者（替代 Copilot） | 测试补齐、文档初稿、快速修复、并行验证 | 不担任全局主控/技术合伙人领导 |
| **GitHub Copilot** | 兼容占位 | 仅历史兼容映射 | 不参与当前协作编排 |

---

## 四、OpenSpec 与工单协同模型

### 4.1 OpenSpec 负责“能力生命周期”

Prompt Pack 相关能力变更必须走 OpenSpec，覆盖：
- 生成（Generation）
- 审核（Review）
- 迭代（Iteration）
- 归档（Archive）

### 4.2 工单负责“执行派发”

OpenSpec 变更获批后，按工单派发实现任务：
- 任务文件：`collaboration/tasks/TASK-*.md`
- 结果文件：`collaboration/results/RESULT_*.md`
- 状态文件：`logs/collaboration_state.json`

### 4.3 绑定规则（强制）

每个执行工单必须声明 `change_id`（对应 OpenSpec 变更）或明确标注 `bugfix/no-spec`。

---

## 五、任务流转

1. **需求澄清（Codex）**  
   输出 V1 范围、非目标、风险和验收标准。
2. **规范立项（OpenSpec）**  
   新能力/架构变更先出 proposal + tasks + spec delta。
3. **工单分派（Codex）**  
   Claude Code 作为默认实现 owner；CodeArts 作为并行支持。
4. **执行与回传（Claude/CodeArts）**  
   产出代码、测试、结果文档、风险说明。
5. **门禁验收（Codex + User）**  
   通过测试和验收后合并；未通过则回到第 3 步。

---

## 六、默认派发策略

| 任务类型 | Lead | Support |
|---------|------|---------|
| 架构/方案/跨模块设计 | Codex | Claude Code, CodeArts |
| 功能实现/重构 | Claude Code | Codex, CodeArts |
| 测试补齐/回归验证 | CodeArts | Claude Code, Codex |
| 文档与使用说明 | CodeArts | Codex, Claude Code |
| 发布/运维/回滚演练 | Codex | Claude Code, CodeArts |

## 6.1 Codex `spawn_agent` 内部委派规则

为最大化资源利用，允许 Codex 在**单个父任务内**使用 `spawn_agent` 做内部并行委派。

但该能力必须满足：

1. 仅作为 Codex 主线程的内部执行工具
2. 不新增外部协作角色，不替代 Claude / CodeArts 正式工单
3. 不直接生成正式 `ACK|task=...` 回执
4. 不得绕过 owner lock、状态同步、冲突检查
5. 必须保证子代理写集与主线程/其他代理不重叠

详细规则见：

- `collaboration/guides/CODEX_SPAWN_AGENT_USAGE_GUIDELINES.md`

运行时校验命令：

```bash
python3 -m ai_collab.cli spawn-agent-guard --actor codex --parent-task <TASK-ID> --files <path1> <path2>
python3 -m ai_collab.cli spawn-agent-guard --actor codex --parent-task <TASK-ID> --read-only
```

安装 `python3 -m ai_collab.cli codex hooks --action install` 后，Claude Code 在实际执行 `Agent` 工具委派前会自动运行同一门禁；CLI 入口继续作为手动诊断口。

---

## 6.2 派发后必做校验（新鲜度守卫）

**目的**：确保 Agent 执行的 payload 与最新派发状态一致，避免执行过期任务。

### 校验时机

每次收到 `C.RUN`、`A.RUN` 或 `X.RUN` 指令后，**必须先执行新鲜度校验**，再开始任务执行。

### 校验步骤

```bash
# 1. 检查 dispatch report 中的 generated_at
cat logs/task_dispatch_report.json | grep generated_at

# 2. 对比 payload 的 GeneratedAt 与 dispatch report
# 如果时间差 > 5 分钟，则 payload 已过期

# 3. 如果 payload 已过期，执行一键修复：
python3 -m ai_collab.cli trigger --phrase '2X DISPATCH Claude' --target claude_code
```

### 判定规则

- ✅ **新鲜**：时间差 ≤ 5 分钟 → 继续执行
- ⚠️  **过期**：时间差 > 5 分钟 → 立即停止，执行一键修复

### 过期处理流程

1. **立即停止执行**：不要继续执行过期任务
2. **执行一键修复**：重新生成 payload
3. **使用新 payload**：将新生成的 payload 发送到 Agent 会话
4. **继续执行**：使用新鲜 payload 继续任务

### 风险提示

- **执行过期任务**可能导致：
  - 任务状态不一致
  - 重复执行已完成任务
  - 遗漏新派发的任务
  - 破坏协作流程完整性

### 自动化支持

系统提供 `check_payload_freshness()` 函数用于自动化校验：

```python
from ai_collab.dispatch_trigger import check_payload_freshness

result = check_payload_freshness(
    payload_generated_at="2026-03-12T11:27:39.268613",
    dispatch_report_path="logs/task_dispatch_report.json",
    assignee="claude_code",
    threshold_minutes=5
)

if not result["is_fresh"]:
    print(result["warning"])
    print(f"修复命令: {result['fix_command']}")
```

---

## 七、工单最小字段（必须）

任务模板至少包含：

- `task_id`
- `change_id`（或 `bugfix/no-spec`）
- `assignee`
- `reviewer`（默认 Codex）
- `priority`
- `primary_skill`
- `support_skills`
- `acceptance_commands`
- `result_file`

工单创建后、进入 `implementing` 前，建议执行契约预检：

```bash
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

`--strict` 现在同时包含两层强门禁：
- 契约字段校验（`invalid=0`）
- 终态任务 `state/result` 一致性审计（`mismatch=0`、`unparseable=0`、`missing_result=0`）

也就是说，closeout/operator review 依赖的结果报告若与控制面终态分裂，将直接导致该命令返回非零。

### 7.1 自动派单桥接（S9+）

为减少人工复制粘贴，支持通过桥接命令生成 Agent 指令包与派单审计记录：

```bash
python3 -m ai_collab.cli dispatch --dry-run
python3 -m ai_collab.cli dispatch
```

默认输出：
- 派单报告：`logs/task_dispatch_report.json`
- 派单历史：`logs/task_dispatch_history.jsonl`
- 派单状态：`logs/agent_dispatch_state.json`
- 指令包：`collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md`

### 7.2 自动回执桥接（S9+）

为减少人工收口，支持对 `testing` 任务执行“证据门禁校验 + 自动完成态更新”：

```bash
python3 -m ai_collab.cli receipt --dry-run
python3 -m ai_collab.cli receipt
```

默认输出：
- 回执报告：`logs/task_receipt_report.json`
- 回执历史：`logs/task_receipt_history.jsonl`
- 回执状态：`logs/agent_receipt_state.json`
- 回执摘要：`collaboration/monitoring/AGENT_RECEIPT_SUMMARY_latest.md`

### 7.3 自动化收益看板（S9+）

为持续追踪收益目标（默认 `>3`），支持按日聚合派单与回执历史：

```bash
python3 -m ai_collab.cli benefit --dry-run
python3 -m ai_collab.cli benefit
```

默认输出：
- 收益报告：`logs/automation_benefit_report.json`
- 收益看板：`collaboration/monitoring/AUTOMATION_BENEFIT_DASHBOARD_latest.md`

### 7.4 最小人环固定流程（Chatbox 版本）

为降低“复制粘贴错位/漏项”风险，固定执行口径如下：

1. **用户按需发送会话执行暗语（执行面触发）**
   - 在 Claude 会话发送：`C.RUN`
   - 在 CodeArts 会话发送：`A.RUN`
   - 在 Codex 会话发送：`X.RUN`
2. **Codex 负责控制面收口**
   - 拉取 ACK 与结果文件
   - 执行门禁检查、状态核验、回执收口与收益刷新
3. **禁止回退到大段手工派单复制**
   - 除非 trigger 文件缺失或协议异常，不再手工分段粘贴任务正文

`X.RUN` 仅用于启动 Codex 当前轮次的执行任务，不替代控制面 CLI 命令 `dispatch / trigger / receipt / run`。

**标准回报格式（Agent 必须）**
- Claude: `C.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>`
- CodeArts: `A.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>`
- Codex: `X.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>`

**ACK 工具化输出（推荐）**
- 执行者完成任务后，优先运行 `python3 -m ai_collab.cli ack --task-id <id> --ai <assignee> --status ok`
- 将该命令 stdout 原样回复到会话中，禁止手写改写 ACK 协议行

**显式 ACK 门禁（强制）**
- 所有正式 assignee 任务只有在控制面记录到显式 ACK 证据后，才允许进入正式闭环；有效来源仅限 `python3 -m ai_collab.cli ack ...` 生成的 `cli-ack`，或会话中原样回放该单行协议的 `chat-ack`
- `receipt`、`reconcile_state_drift`、`missing_ack_monitor` 不得为任何正式 assignee 任务合成 fallback ACK，也不得仅因 `result_file` 已存在就自动判定完成
- 若当前会话负责的任务处于 `testing/completed` 但缺少显式 ACK，Stop Hook 必须阻止结束会话，并只提示执行对应的 `python3 -m ai_collab.cli ack --task-id <id> --ai <assignee> --status ok`
- 历史 fallback bridge 残留的审计/标记统一使用 `python3 -m ai_collab.cli ack-remediation [--dry-run]`
- 已被 `ack-remediation` 标记的历史残留，在后续收到真实 `cli-ack/chat-ack` 后必须自动解除残留标记，不再继续出现在 `explicit ACK required` 监控里
- `ai_type` 表示任务原始分配对象，`assignee` / `ownership.owner` 表示当前责任 owner；当存在合法 `tasks takeover` 且 owner lock 生效时，`ai_type != assignee` 属于正常接管状态，不应被判定为脏数据或异常 closeout

**异常处理**
- 若发送 `C.RUN/A.RUN/X.RUN` 后 2 分钟内无 ACK，执行对应的 `RUN-RESET` 一次，再重发 `RUN`。
- 若仍无 ACK，按“窗口协议失败”记录到结果文件并转人工排障。
- 控制面自动化会通过 `ACK_WATCHDOG_SUMMARY_latest.md` 输出“自动重派 / 告警”结果；receipt-bridge 自动完成态时会同步写 ACK bridge

### 7.5 会话压缩前续接交接（Session Continuation Handoff）

为避免在“压缩当前对话 -> 开新对话 -> 继续同一工作流”时丢失上下文，固定采用标准 handoff 命令，而不是手工临时总结。

标准命令：

```bash
python3 -m ai_collab.cli sessions handoff
```

固定流程：

1. 在当前对话结束前，先运行 `sessions handoff`
2. 打开新生成的 `collaboration/results/SESSION_CONTINUATION_HANDOFF_*.md`
3. 复制其中 `Paste This Into The Next Conversation` 代码块
4. 将该代码块作为新对话的第一条消息
5. 完成以上步骤后，再压缩或结束旧对话

默认输出：

- 版本化 handoff 文件：`collaboration/results/SESSION_CONTINUATION_HANDOFF_YYYY-MM-DD*.md`
- 最新摘要：`collaboration/monitoring/SESSION_CONTINUATION_HANDOFF_SUMMARY_latest.md`
- 外部收口面板：`collaboration/monitoring/EXTERNAL_CLOSEOUT_QUEUE_YYYY-MM-DD_latest.md`
- 机器报告：`logs/session_continuation_handoff_report.json`
- 历史记录：`logs/session_continuation_handoff_history.jsonl`

增强写法：

```bash
python3 -m ai_collab.cli sessions handoff \
  --completed-item "本轮完成事项" \
  --validation-command "已执行的验证命令" \
  --related-file "关键文件路径" \
  --next-slice "下一步建议"
```

解释边界：

- 这不是“跨会话隐藏记忆同步”
- 真正发生的是：控制面先生成可审计 handoff 包，再让下一会话优先读取该包
- handoff 会顺带刷新 external closeout queue，因此外部 Claude / CodeArts 收口待办会自动进入续接上下文
- 连续性来自文件与协议，而不是不可验证的隐式会话记忆

详细操作手册见：

- `collaboration/results/SESSION_CONTINUATION_HANDOFF_RUNBOOK_2026-03-29.md`

---

## 八、执行心跳与反空转门禁（强制）

### 8.1 状态更新渠道

- 禁止直接编辑 `logs/collaboration_state.json` 改任务状态。
- 任务状态变更只能通过 CLI：
  - `python3 -m ai_collab.cli tasks update --task-id <id> --status <status> --note "<note>"`

### 8.2 implementing/testing 心跳 SLA

- `implementing/testing` 达到预警阈值（默认 `prewarnRatio=0.8`）时：
  - controller 自动写入 prewarning 提示
  - 执行者需在超时前回写心跳并更新证据路径
- `implementing/testing` 状态超过 `activeTimeoutSec`（默认 1800 秒）无更新：
  - controller 自动降级为 `blocked`
  - 必须补充心跳说明（当前进展、阻塞点、下一步动作、证据路径）

### 8.3 blocked 升级规则

- `blocked` 状态超过 `blockedTimeoutSec`（默认 3600 秒）无更新：
  - controller 自动升级为 `failed`
  - 需由 Codex 重新派单或明确回滚/重启方案

### 8.4 完成态证据门禁

- 任务进入 `completed` 前，`result_file` 必须满足：
  - 文件存在且可读
  - 包含最小章节证据：执行命令、测试结论、风险/回滚
- 任一条件不满足，状态更新被拒绝。

---

## 九、生效与回滚

### 9.1 生效条件

本协议自 2026-03-02 起生效，适用于新建工单与新一轮任务派发。

### 9.2 回滚触发

若出现以下任一情况，回滚至上个稳定协议版本：
- 关键任务出现重复执行或无人认领
- 任务状态与责任人长期不一致（>24h）
- 发布门禁无法形成闭环

---

## 十、废弃声明

以下旧口径在当前治理阶段视为废弃：
- “Claude Code + GitHub Copilot”作为主协作模式
- “CodeArts Agent 作为技术合伙人主导项目”
- “Copilot 为默认 testing/documentation lead”
