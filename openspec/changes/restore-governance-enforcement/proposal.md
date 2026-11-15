# Change Proposal: Restore Governance Enforcement

## Why

2026-11-15 对项目开发合规性做了两轮磁盘真值审计（`openspec-compliance-audit.html`、
`dev-governance-compliance-audit.html`），确认治理链路自 2026-10-26 起停摆：11 月 51 个合并
PR 全部未进工单 / 结果 / 日志体系。更关键的是，**治理门禁本身存在两处假绿**，
即使有人开始按规矩填表，门禁也不会因为「没登记」而报警：

1. **契约门禁只检查它能看见的任务**。实跑
   `python3 -m ai_collab.cli tasks validate-contract --scope all --strict` 得
   `checked=18 skipped=0 invalid=0`、`audited=18 consistent=18 mismatch=0`，
   但这条校验只遍历 `logs/collaboration_state.json` 里已登记的 18 个任务
   （全部创建于 2026-10-22～10-25，状态全 `completed`，`last_updated=2026-10-26T16:21:15`）。
   11 月 51 个合并提交从未登记，对该门禁完全不可见。`invalid=0` 是
   「没登记就不用检查」，不是合规结论。

2. **并发守护的两个硬门禁没有输入**。`logs/workspace_forensics/concurrent_guard_latest.json`
   报 `allowed=true, risk_level=low`，但 `.vscode/ai-collab.json` 的 `concurrentGuard` 是
   `expectedBranch=null`、`requireBaselineCommit=false`、`baselineCommit=null`、
   `watchPaths=[]`、`sessionStartedAt=null`。按 `PROTOCOL §14.5`，G1 分支漂移 / G2 基线过期
   是仅有的两个硬门禁信号，输入为空时结构上永远评不出 `high`。同一份报告的
   `git_context` 却记着 `behind=39, dirty_total=153`。

这与 2026-11-15 之前修掉的 CI 假绿（`|| true` / `continue-on-error` / 空扫描返回 0）是同一
类病根：**门禁只覆盖它能看见的对象，而最省事的绕过方式就是让它看不见**。

本轮按用户要求在立项前深入调研了工单系统实现，又发现第三处前置风险（见 What Changes
的「范围修正」）：部分账本写入路径绕过了既有的跨进程锁。这一项不修，后续改成多会话
并行执行会直接写坏状态文件，因此必须与前两项一起纳入本 change。

## What Changes

### 新增

| 产物 | 内容 | 层 |
|------|------|---|
| `logs/governance-ledger.jsonl` | append-only 治理登记表：合并提交 → `change_id` / 豁免标签 / 理由 / 声明时间 / 声明主体 | 事实源 |
| `tasks declare-commit` CLI | 登记入口，写入上表并校验声明内容 | CLI |
| `governance preflight` CLI | 开工前一次机器检查：必读清单、状态机时效、门禁输入完整性、HEAD 是否被登记、上一条 ACK | CLI |
| `logs/governance_coverage_observe.jsonl` | 观测期差异留痕（假想判定 vs 实际判定） | 证据 |
| `tests/unit/test_governance_coverage.py` 等 | 覆盖率 / 输入契约 / 并发写入守护测试 | 测试层 |

### 修改

| 文件 | 内容 | 层 |
|------|------|---|
| `ai_collab/state_manager.py` | 批量契约校验增加覆盖率判定；账本写入统一到既有跨进程锁 + 原子替换 | 服务层 |
| `ai_collab/cli/_cli_main.py` | `validate-contract` 接入覆盖率结果；新增 `declare-commit` / `governance preflight` 分发 | CLI |
| `ai_collab/concurrent_guard.py` | 报告新增 `input_contract_complete` 字段（观测期只记录，不改放行结论） | 服务层 |
| `ai_collab/ack_protocol.py`、`scripts/agent_receipt_bridge.py` | 收口账本写入到统一入口，移除对状态文件的直写 | 服务层 |
| `.vscode/ai-collab.json` | `concurrentGuard` 补真实输入：`expectedBranch`、`requireBaselineCommit`、`baselineCommit`、`watchPaths` | 配置 |
| `logs/task_result_consistency_report.json` 之外的自动报告 | 去掉纯时间戳差异判定，保证脚本幂等 | 工具 |

> **范围修正（2026-11-15 立项前深调新增，含证据）**：上一版恢复方案只列两项 P0。
> 深调发现 `state_manager.py:772` 的 `_file_lock` 确实是跨进程锁且
> `:847` 在锁内重读最新状态、`:649` 用临时文件 + `os.replace` 原子落盘；
> 但 `ack_protocol.py:46` 与 `scripts/agent_receipt_bridge.py:129` 的写入是裸
> `path.write_text`，后者 `:326` 更直接覆写 `logs/collaboration_state.json`，
> **绕过状态机的锁与状态合并**。多会话并发 ACK 会 lost update、甚至把状态回退到旧
> 快照；`write_text` 非原子，中断会留下半截 JSON。因此新增第三项 P0「账本写入互斥与
> 原子性」，作为会话化的硬前置。详见 `design.md` 决策 D5。

### 不改

- `openspec/specs/concurrent-workspace-safety/spec.md` 的既有 requirement 一律不改：
  本 change 新增的是「门禁是否已装备」的判定，不把「未配置」混写成「检测到违规」。
  详见 `design.md` 决策 D4。
- 既有 CI workflow（`lint.yml` / `security.yml` / `healthcheck.yml` 等）不改。
- 21 个 `ai_collab/**.py` 业务文件不改。

### 接口（可观测，不含实现步骤）

- 登记一条合并提交：`change_id` 或豁免标签 + 理由 → 账本追加一行，可复核。
- 严格契约校验：返回「已检查任务数」与「生效边界之后未登记提交清单」。
- 开工检查：返回五项可读结论与一个 PASS / FAIL。
- 并发守护报告：返回 `input_contract_complete` 布尔值，不改变既有风险评级字段语义。

## Capabilities

### New Capabilities

- `governance-coverage`：让治理门禁覆盖「未登记的工作」，并对门禁自身是否装备给出
  可判定结论；同时保证多执行主体并发写账本时状态不丢失、不回退、不损坏。

### Modified Capabilities

- 无。既有 `concurrent-workspace-safety` 保持原样，理由见 D4。

## Impact

### Affected specs

- 新增 `governance-coverage`（本 change 的 `specs/governance-coverage/spec.md`，
  4 条 requirement、每条带 `#### Scenario`）。
- `concurrent-workspace-safety` **不受影响**：不改其 requirement、不写 MODIFIED delta。

### Affected code

- `ai_collab/state_manager.py`、`ai_collab/cli/_cli_main.py`、
  `ai_collab/concurrent_guard.py`、`ai_collab/ack_protocol.py`、
  `scripts/agent_receipt_bridge.py`、`.vscode/ai-collab.json`、`tests/unit/*`。
- 守护范围已 grep 确认：`test_state_manager.py`（1202 行）、`test_cli.py`（3495 行）、
  `test_concurrent_guard.py`（451 行）、`test_concurrent_guard_reuse.py`、
  `test_concurrent_guard_cli.py`（294 行），合计约 5442 行，改前须先跑相关测试。

### Non-goals

- **不追溯惩罚 11 月 51 个 PR**：覆盖率判定只作用于 `enforced_from_commit` 之后；
  历史欠账由后续 retro 补档 change 消化，不用门禁倒逼追溯性引红。
- **不实施「会话代替 Agent 框架平台」的改造**：立项前已按用户要求完成可行性探讨，
  结论写入 `design.md` D6；那是一次独立的规则文本 + 传输层变更，需另开 change。
  本 change 只交付它依赖的机制（开工检查、登记表、账本并发安全）。
- **不改 `PROTOCOL §7.3` / §8.1 / `AI-COLLABORATION-STANDARDS §2.1` 的规则文本**：
  `2X` 与轻量通道的法律地位由后续立法 change 裁定。
- **不重构角色编排、不移除 `config/agent-orchestration.json`**。
- **不启用人工目检作为翻闸依据**：用户已明确无目检样板能力，翻闸依据为机器可判定的
  差异清单 + 反向测试。
