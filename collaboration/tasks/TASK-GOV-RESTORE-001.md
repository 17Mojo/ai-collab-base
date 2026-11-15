---
task_id: TASK-GOV-RESTORE-001
change_id: restore-governance-enforcement
status: testing
priority: P0
assignee: claude_code
assignee_role: AGENT_EXEC
assignee_provider: claude_code
reviewer: codearts_agent
primary_skill: governance-engineering
support_skills: [testing, documentation]
created_at: 2026-11-15T22:47:00+08:00
acceptance_commands:
  - "openspec validate restore-governance-enforcement --strict"
  - "python3 -m ai_collab.cli tasks validate-contract --scope all --strict"
  - "python3 -m ai_collab.cli governance preflight"
  - "python3 -m pytest tests/unit/test_governance_ledger.py -q"
  - "python3 -m ruff format --check ."
  - "python3 -m ruff check ."
result_file: collaboration/results/RESULT-GOV-RESTORE-001.md
---

# TASK-GOV-RESTORE-001 · 恢复治理门禁的可判定性

## 状态说明

**本工单已从 `planning` 进入 `testing`。** Phase 1–4 已实施完成并通过机器验收，
Phase 5（协同收口）进行中。

- 权威状态落在协作台账（`logs/collaboration_state.json`，gitignored），由
  `python3 -m ai_collab.cli tasks update --status ...` 变更，不手改台账。
- 本文件 frontmatter 的 `status` 只是镜像，用于人读一致性；两者不一致时以台账为准。
- `acceptance_commands` 的实测输出见
  `collaboration/results/RESULT-GOV-RESTORE-001.md`，不在此重复。

### 规划工件回溯更正

原 `acceptance_commands` 第 4 条指向 `tests/unit/test_governance_coverage.py`，
该文件从未存在；实际落地的是 `tests/unit/test_governance_ledger.py`（42 条用例，
覆盖 A1–A6 验收场景）。规划阶段预设的拆分粒度（按「覆盖率」单独建测试文件）
在实施时改为「单文件承载全部治理账本机制」，因此路径随之更正——这是工件向实现
对齐，不是实现向工件迁就。

## 字段口径注记（重要，避免后续误读）

- `assignee` / `assignee_provider` 按**现行** `PROTOCOL §7.3` 口径填写（从
  `config/agent-orchestration.json` 反查厂商名）。
- 本次立项已探讨「多会话 + 多模型代替 Agent 框架平台」，结论是
  `assignee_provider` 的语义应迁移为 `session_id + model_id`，且
  `PROTOCOL §12` 已把硬编码厂商名列为废弃。但**规则文本尚未修改**，所以本工单
  仍按现行口径填写，不提前套用未生效的新语义。
- 语义迁移与 `2X` 立法由后续 change 处理，详见
  `openspec/changes/restore-governance-enforcement/design.md` D6 / D7。

## 范围

见 `openspec/changes/restore-governance-enforcement/proposal.md` 的
What Changes / Non-goals，以及 `tasks.md` 的 Phase 1–5。

一句话：修三处治理完整性缺口（覆盖率、输入完整性、账本写入互斥），
**不实施会话化改造、不改规则文本、不追溯惩罚 11 月 PR**。

## 交付条件

1. `openspec validate restore-governance-enforcement --strict` 零错误。
2. 观测期有机器证据证明零行为改变（跑前 / 跑后输出哈希一致 + 反向测试）。
3. 翻闸后五个验收场景全部通过（见 `tasks.md` Phase 4）。
4. 结果报告含 `PROTOCOL §7.4` 四段 + 可解析状态行 + 本工单全部
   `acceptance_commands` 原样出现。
5. 开发日志落到 `logs/claude-code/2026-11/`（该目录当前不存在）。
6. ACK 由 CLI 生成、任务状态由 CLI 更新、会话结束前有 handoff。
7. 主工作区另一 session 的 153 项在途改动数量不变；所有提交带 pathspec。

## 回滚

观测期把模块级总闸翻回关闭即完全恢复旧行为；每个 PR 独立可 `git revert`；
登记表只追加、生效边界声明落盘后不改。详见 `design.md` D9。
