# Agent Dispatch Orders（自动生成）

- 生成时间: `2026-03-03T21:43:22`
- 待派发任务数: `7`

## 发送给 `Claude` (`claude_code`)

### TASK-S9-D3-BASE-CLI-HELP-ALIGN-CLAUDE-009

```text
【执行指令 | TASK-S9-D3-BASE-CLI-HELP-ALIGN-CLAUDE-009】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D3-BASE-CLI-HELP-ALIGN-CLAUDE-009 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 -m pytest -q tests/unit/test_cli.py
python3 -m ai_collab.cli --help
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-D3-BASE-CLI-HELP-ALIGN-CLAUDE-009.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D3-BASE-CLI-HELP-ALIGN-CLAUDE-009 --status testing --note "result ready for codex review"
```

### TASK-S9-D3-BASE-DAILY-SNAPSHOT-HARDEN-CLAUDE-010

```text
【执行指令 | TASK-S9-D3-BASE-DAILY-SNAPSHOT-HARDEN-CLAUDE-010】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D3-BASE-DAILY-SNAPSHOT-HARDEN-CLAUDE-010 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 -m pytest -q tests/unit/test_daily_benefit_snapshot.py
python3 collaboration/scripts/run_daily_benefit_snapshot.py --workspace . --dry-run
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-D3-BASE-DAILY-SNAPSHOT-HARDEN-CLAUDE-010.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D3-BASE-DAILY-SNAPSHOT-HARDEN-CLAUDE-010 --status testing --note "result ready for codex review"
```

### TASK-S9-D3-BASE-DOC-SYNC-CLAUDE-011

```text
【执行指令 | TASK-S9-D3-BASE-DOC-SYNC-CLAUDE-011】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D3-BASE-DOC-SYNC-CLAUDE-011 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 -m ai_collab.cli benefit --dry-run
make benefit-daily
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-D3-BASE-DOC-SYNC-CLAUDE-011.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D3-BASE-DOC-SYNC-CLAUDE-011 --status testing --note "result ready for codex review"
```

## 发送给 `CodeArts` (`codearts_agent`)

### TASK-S9-D3-RESEARCH-REGRESSION-CODEARTS-009

```text
【执行指令 | TASK-S9-D3-RESEARCH-REGRESSION-CODEARTS-009】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D3-RESEARCH-REGRESSION-CODEARTS-009 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 -m pytest -q tests/unit/test_agent_dispatch_bridge.py tests/unit/test_agent_receipt_bridge.py tests/unit/test_automation_benefit_dashboard.py tests/unit/test_daily_benefit_snapshot.py
python3 -m ai_collab.cli benefit --dry-run
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-D3-RESEARCH-REGRESSION-CODEARTS-009.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D3-RESEARCH-REGRESSION-CODEARTS-009 --status testing --note "result ready for codex review"
```

### TASK-S9-D3-RESEARCH-RESULT-QUALITY-CODEARTS-010

```text
【执行指令 | TASK-S9-D3-RESEARCH-RESULT-QUALITY-CODEARTS-010】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D3-RESEARCH-RESULT-QUALITY-CODEARTS-010 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 -m ai_collab.cli receipt --dry-run
python3 collaboration/scripts/run_daily_benefit_snapshot.py --workspace . --dry-run
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-D3-RESEARCH-RESULT-QUALITY-CODEARTS-010.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D3-RESEARCH-RESULT-QUALITY-CODEARTS-010 --status testing --note "result ready for codex review"
```

### TASK-S9-D3-RESEARCH-STABILITY-AUDIT-CODEARTS-011

```text
【执行指令 | TASK-S9-D3-RESEARCH-STABILITY-AUDIT-CODEARTS-011】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D3-RESEARCH-STABILITY-AUDIT-CODEARTS-011 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 -m ai_collab.cli benefit --dispatch-history logs/day2_accel_dispatch_history.jsonl --receipt-history logs/day2_accel_receipt_history.jsonl --report logs/day3_preview_automation_benefit_report.json --output collaboration/monitoring/AUTOMATION_BENEFIT_DASHBOARD_day3_preview.md
python3 -m ai_collab.cli status -v
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-D3-RESEARCH-STABILITY-AUDIT-CODEARTS-011.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D3-RESEARCH-STABILITY-AUDIT-CODEARTS-011 --status testing --note "result ready for codex review"
```

## 发送给 `Codex` (`codex`)

### TASK-S9-GOV-STABILITY-CLOSURE-CODEX-006

```text
【执行指令 | TASK-S9-GOV-STABILITY-CLOSURE-CODEX-006】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-GOV-STABILITY-CLOSURE-CODEX-006 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 -m ai_collab.cli benefit --dry-run
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
python3 -m ai_collab.cli status -v

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-GOV-STABILITY-CLOSURE-CODEX-006.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-GOV-STABILITY-CLOSURE-CODEX-006 --status testing --note "result ready for codex review"
```
