# Agent Dispatch Orders（自动生成）

- 生成时间: `2026-03-03T17:18:12`
- 待派发任务数: `6`

## 发送给 `Claude` (`claude_code`)

### TASK-S9-D2-BASE-BENEFIT-RUNBOOK-CLAUDE-007

```text
【执行指令 | TASK-S9-D2-BASE-BENEFIT-RUNBOOK-CLAUDE-007】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D2-BASE-BENEFIT-RUNBOOK-CLAUDE-007 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 collaboration/scripts/run_daily_benefit_snapshot.py --workspace . --dry-run
python3 -m ai_collab.cli benefit --dry-run
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-D2-BASE-BENEFIT-RUNBOOK-CLAUDE-007.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D2-BASE-BENEFIT-RUNBOOK-CLAUDE-007 --status testing --note "result ready for codex review"
```

### TASK-S9-D2-BASE-CLI-HELP-COPY-CLAUDE-006

```text
【执行指令 | TASK-S9-D2-BASE-CLI-HELP-COPY-CLAUDE-006】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D2-BASE-CLI-HELP-COPY-CLAUDE-006 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 -m pytest -q tests/unit/test_cli.py
python3 -m ai_collab.cli --help
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-D2-BASE-CLI-HELP-COPY-CLAUDE-006.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D2-BASE-CLI-HELP-COPY-CLAUDE-006 --status testing --note "result ready for codex review"
```

### TASK-S9-D2-BASE-DAILY-SNAPSHOT-USABILITY-CLAUDE-008

```text
【执行指令 | TASK-S9-D2-BASE-DAILY-SNAPSHOT-USABILITY-CLAUDE-008】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D2-BASE-DAILY-SNAPSHOT-USABILITY-CLAUDE-008 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 -m pytest -q tests/unit/test_daily_benefit_snapshot.py
make benefit-daily
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-D2-BASE-DAILY-SNAPSHOT-USABILITY-CLAUDE-008.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D2-BASE-DAILY-SNAPSHOT-USABILITY-CLAUDE-008 --status testing --note "result ready for codex review"
```

## 发送给 `CodeArts` (`codearts_agent`)

### TASK-S9-D2-RESEARCH-BENEFIT-REGRESSION-CODEARTS-006

```text
【执行指令 | TASK-S9-D2-RESEARCH-BENEFIT-REGRESSION-CODEARTS-006】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D2-RESEARCH-BENEFIT-REGRESSION-CODEARTS-006 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 -m pytest -q tests/unit/test_automation_benefit_dashboard.py tests/unit/test_daily_benefit_snapshot.py tests/unit/test_agent_dispatch_bridge.py tests/unit/test_agent_receipt_bridge.py
python3 -m ai_collab.cli benefit --dry-run
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-D2-RESEARCH-BENEFIT-REGRESSION-CODEARTS-006.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D2-RESEARCH-BENEFIT-REGRESSION-CODEARTS-006 --status testing --note "result ready for codex review"
```

### TASK-S9-D2-RESEARCH-DAY2-BENEFIT-AUDIT-CODEARTS-008

```text
【执行指令 | TASK-S9-D2-RESEARCH-DAY2-BENEFIT-AUDIT-CODEARTS-008】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D2-RESEARCH-DAY2-BENEFIT-AUDIT-CODEARTS-008 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 -m ai_collab.cli benefit --dispatch-history logs/bench_dispatch_history.jsonl --receipt-history logs/bench_receipt_history.jsonl --report logs/bench_automation_benefit_report.json --output collaboration/monitoring/AUTOMATION_BENEFIT_DASHBOARD_bench.md
python3 -m ai_collab.cli status -v
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-D2-RESEARCH-DAY2-BENEFIT-AUDIT-CODEARTS-008.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D2-RESEARCH-DAY2-BENEFIT-AUDIT-CODEARTS-008 --status testing --note "result ready for codex review"
```

### TASK-S9-D2-RESEARCH-REAL-BATCH-VERIFY-CODEARTS-007

```text
【执行指令 | TASK-S9-D2-RESEARCH-REAL-BATCH-VERIFY-CODEARTS-007】

1) 切换状态为 implementing
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D2-RESEARCH-REAL-BATCH-VERIFY-CODEARTS-007 --status implementing --note "dispatch bridge kickoff"

2) 执行验收命令并记录关键输出
python3 -m ai_collab.cli receipt --dry-run
python3 collaboration/scripts/run_daily_benefit_snapshot.py --workspace . --dry-run
python3 -m ai_collab.cli tasks validate-contract --scope active --strict

3) 创建结果文件（至少包含：执行命令、测试结论、风险/回滚）
collaboration/results/RESULT_TASK-S9-D2-RESEARCH-REAL-BATCH-VERIFY-CODEARTS-007.md

4) 切换状态为 testing 并回报进展
python3 -m ai_collab.cli tasks update --task-id TASK-S9-D2-RESEARCH-REAL-BATCH-VERIFY-CODEARTS-007 --status testing --note "result ready for codex review"
```
