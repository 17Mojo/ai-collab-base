# 工单契约化派单作业手册

## 1. 目标

确保所有新工单在进入 `implementing` 前满足契约字段，避免执行漂移和上下文错配。

## 2. 必填字段

- `change_id`
- `assignee`
- `reviewer`
- `primary_skill`
- `support_skills`
- `acceptance_commands`
- `result_file`

## 3. 标准派单命令（示例）

```bash
python3 -m ai_collab.cli tasks register \
  --task-id TASK-EXAMPLE-001 \
  --ai claude_code \
  --description "示例任务" \
  --files ai_collab/cli.py \
  --change-id bugfix/no-spec \
  --assignee claude_code \
  --reviewer codex \
  --primary-skill backend-architect \
  --support-skills planning-with-files systematic-debugging \
  --acceptance-commands "python3 -m ai_collab.cli status -v" "pytest -q tests/unit/test_cli.py" \
  --result-file collaboration/results/RESULT_TASK-EXAMPLE-001.md
```

## 4. 上线前门禁

```bash
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

通过标准：
- `invalid=0`
- `mismatch=0`
- `unparseable=0`
- `missing_result=0`

说明：`--strict` 不再只是字段契约检查，还会联动终态结果一致性审计；只要结果报告状态头和控制面终态不一致，就必须先修复后再进入 closeout / operator review。

建议：
- 新工单直接复用 [TASK_TEMPLATE_SKILL_GATED.md](/Users/raymondna/Documents/ai-collab-system/collaboration/templates/TASK_TEMPLATE_SKILL_GATED.md)
- 波次收口直接复用 [WAVE_CLOSEOUT_SUMMARY_TEMPLATE.md](/Users/raymondna/Documents/ai-collab-system/collaboration/templates/WAVE_CLOSEOUT_SUMMARY_TEMPLATE.md)

## 5. 历史任务契约迁移（S3）

先执行一次历史任务迁移，消除 legacy 分支：

```bash
python3 -m ai_collab.cli tasks migrate-contract --scope all
```

迁移完成后，再执行全量门禁：

```bash
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
```

## 6. 控制器巡检观测项

`python3 -m ai_collab.cli controller --once --dry-run` 报告新增：
- `task_contract_checked`
- `task_contract_invalid`

## 7. Operator Closeout Checklist

1. **命令顺序**：先运行 `python3 -m ai_collab.cli tasks validate-contract --scope active --strict`（结合终态一致性审计），再运行 `python3 -m ai_collab.cli controller --once --dry-run` 完成 patch/stale drift 检查；最后可使用 `python3 -m ai_collab.cli daily-report`/`python3 -m ai_collab.cli run --dry-run` 确认全链路产物（dispatch/receipt/controller/run）。
如果本轮还涉及 Claude / CodeArts 外部收口，再补跑 `python3 -m ai_collab.cli sessions closeout-queue` 生成最新的 operator closeout 面板，不要手工从 tasks / interventions / packs 之间来回拼装。
2. **ACK 缺口排查**：查看 `collaboration/monitoring/ACK_WATCHDOG_SUMMARY_latest.md`，确认 `claude_explicit_ack_count` 与 `claude_legacy_fallback_count`。若存在缺显式 ACK，运行 `python3 -m ai_collab.cli ack-remediation --dry-run` 统计残留，再按照 `python3 -m ai_collab.cli ack --task-id ...` 生成 `cli-ack` 补全。Stop Hook 会提示具体 ACK 命令，必须先补 ACK 再 closeout。
3. **结果一致性查看**：结果文件不一致会在 `logs/task_result_consistency_report.json` 与 `collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md` 体现，`issues` 列表指示 `task_id`、`state_status`、`result_header_status`。daily report 会汇总 `audited/consistent/mismatch/unparseable/missing_result/issue_count`，一致值清零才能判断 closeout 合格。
4. **判定 closeout 健康**：`tasks validate-contract --strict` 返回 `invalid=0`、`result_consistency_issue_count=0`、`missing_result=0`，同时 `controller` dry-run 无未解决 errors、`ACK_WATCHDOG` 无 `alerted_count` 且 `clode_explicit_ack_count` 覆盖所有 `claude_code` closeout；daily report显示结果一致性指标齐全且 `pending_tasks` 为空即可视为 closeout 健康。

## 8. 回滚点

若契约门禁需临时回退：
- 移除 `update_task_status()` 中 implementing 契约拦截
- 回退到 S2 版本（允许 legacy 跳过）再重跑状态校验
