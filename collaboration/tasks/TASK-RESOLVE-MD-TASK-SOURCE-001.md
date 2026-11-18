---
task_id: TASK-RESOLVE-MD-TASK-SOURCE-001
change_id: resolve-md-task-source
status: pending
priority: P2
session_id: sess-resolve-md-source-20261118
model_id: deepseek/v4.1-flash
assignee: claude_code
assignee_role: AGENT_EXEC
assignee_provider: claude_code
reviewer: codearts_agent
primary_skill: governance-engineering
support_skills: [testing, documentation]
created_at: 2026-11-18T07:55:00+08:00
acceptance_commands:
  - "openspec validate resolve-md-task-source --strict"
  - "python3 -m ai_collab.cli tasks validate-contract --scope all --strict"
  - "python3 -m ai_collab.cli tasks sync-from-md --dry-run"
  - "python3 -m ai_collab.cli governance preflight"
  - "python3 -m pytest tests/unit/test_task_md_sync.py -q"
  - "PYTHONPATH=/tmp/noshim python3 -m pytest -q"
result_file: collaboration/results/RESULT-RESOLVE-MD-TASK-SOURCE-001.md
---

# TASK-RESOLVE-MD-TASK-SOURCE-001 · 让 md 成为任务事实源

## 状态说明

- 权威状态落在协作台账（`logs/collaboration_state.json`，gitignored），由
  `python3 -m ai_collab.cli tasks update --status ...` 变更，**不手改台账**。
- 本文件 frontmatter 的 `status` 只是镜像；两者不一致时以台账为准。
- 账本是 **per-worktree** 的本机状态；本工单只在本工作树注册。路由键 `assignee=claude_code`
  由注册表反查得到，未手工指定。

## 背景

`known_gaps.json` N26 记录了身份审计的输入口径问题。复核后发现三层根因：

1. `logs/` 被 gitignore，账本每个工作树各一份（主工作区 18 条 / wt-g11 2 条 / 新 clone 0 条），
   而磁盘 `TASK-*.md` 恒为 27 个，与三者交集均为 0。
2. `scripts/verify_task_file_contracts.py` 把 md 登记进账本时，两处调用**漏传**
   `session_id` / `model_id`，而登记函数本身支持这两个字段。
3. 两套校验器输入源不同，脚本 docstring 已记载，但身份这一维没有 md 侧覆盖。

用户 2026-11-18 裁定选 **A：md 是事实源**。

## 范围

- 新增 `ai_collab/task_md_sync.py`，从 md 同步进当前工作树账本，**只写已声明字段**。
- 修 `verify_task_file_contracts.py` 两处漏传，`parse_frontmatter` 复用新模块。
- CLI 加 `tasks sync-from-md`（显式、可 `--dry-run`）。
- 身份审计输出追加 `input_source`，披露覆盖范围。
- PROTOCOL 写明标准流程：sync-from-md → migrate-identity。

## 明确不做

- 不推导、不补全、不编造身份；历史 md 缺身份判 `legacy` 是正确结果。
- 不改 `audit_task_identity` 的只读语义，不自动触发同步。
- 不把账本变成共享文件，不回写 md，不接 preflight。
