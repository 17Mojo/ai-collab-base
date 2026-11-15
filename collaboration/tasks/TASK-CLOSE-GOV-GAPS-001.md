---
task_id: TASK-CLOSE-GOV-GAPS-001
change_id: close-governance-gaps
status: planning
priority: P1
assignee: claude_code
assignee_role: AGENT_EXEC
assignee_provider: claude_code
reviewer: codearts_agent
primary_skill: governance-engineering
support_skills: [testing, documentation]
created_at: 2026-11-16T04:30:00+08:00
acceptance_commands:
  - "openspec validate close-governance-gaps --strict"
  - "python3 -m ai_collab.cli tasks validate-contract --scope all --strict"
  - "python3 -m ai_collab.cli governance preflight"
  - "python3 -m pytest tests/unit/test_governance_gaps.py -q"
  - "python3 -m ruff format --check ."
  - "python3 -m ruff check ."
result_file: collaboration/results/RESULT-CLOSE-GOV-GAPS-001.md
---

# TASK-CLOSE-GOV-GAPS-001 · 收口治理门禁剩余三处缺口

## 范围

见 `openspec/changes/close-governance-gaps/proposal.md`。一句话：上一轮结果报告诚实登记的
三处缺口——必读清单纯自证且无写入方、会话级配置没有不受跟踪的落点、开发日志被目录级排除
挡在版本库外——在本工单内一次收口。

**不在范围**：规则文本修改、会话注册表语义迁移、11 月 PR 追溯登记。

## 交付条件

1. `openspec validate close-governance-gaps --strict` 零错误。
2. 三条 Requirement 各有正反两侧的机器用例（不是只测「能过」，还要测「改了就该红」）。
3. 本仓 `governance preflight` **五项全 PASS**，且受跟踪的 `.vscode/ai-collab.json` 零改动。
4. 全套 pytest 与干净 `origin/main` 基线 FAILED 集合一致。
5. 结果报告含四段 + 可解析状态行 + 本工单全部 `acceptance_commands` 原样出现。
6. ACK 由 CLI 生成、任务状态由 CLI 更新、提交带 pathspec。

## 回滚

三条缺口彼此独立，可分别回退：必读声明退回旧格式只需删 `.ai_collab_session.json` 并把
`preflight` 的该项判回列表成员判定（会回到恒 FAIL 状态）；覆盖层退回只需删
`ai-collab.local.json` 并恢复 `guard_input_report` 只读受跟踪配置；忽略规则退回只需把
`logs/*` 改回 `logs/`（开发日志重新不可入库）。
