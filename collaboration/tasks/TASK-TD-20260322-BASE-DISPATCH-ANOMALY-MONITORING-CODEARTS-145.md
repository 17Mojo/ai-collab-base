# 任务: Base dispatch anomaly monitoring

**任务ID**: TASK-TD-20260322-BASE-DISPATCH-ANOMALY-MONITORING-CODEARTS-145  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 `143` 的根因结果，沉淀一份可持续复用的 dispatch anomaly 监控摘要/巡检资产
  - 聚焦异常空派单趋势、日期聚集、dry-run 与 apply 差异
  - 输出 operator 可直接复用的监控口径与后续告警建议
  - 不修改产品代码，只产出监控资产
- **scope_out**:
  - 不修改 `ai_collab` 源码
  - 不调整 benefit 计算口径
  - 不重开研究验证线任务

## 输入

- `collaboration/results/BASE_DISPATCH_ANOMALY_ROOTCAUSE_2026-03-22.md`
- `collaboration/results/BASE_DISPATCH_SUCCESS_BASELINE_2026-03-22.md`
- `logs/task_dispatch_history.jsonl`
- `logs/task_dispatch_report.json`
- `collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md`

## 输出要求

- 资产文件: `collaboration/results/BASE_DISPATCH_ANOMALY_MONITORING_2026-03-22.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260322-BASE-DISPATCH-ANOMALY-MONITORING-CODEARTS-145.md`
- 必须包含:
  - 异常趋势摘要
  - dry-run / apply 差异口径
  - 日期聚集与风险等级
  - 后续告警与巡检建议

## acceptance_commands（必填）

```bash
test -f collaboration/results/BASE_DISPATCH_ANOMALY_MONITORING_2026-03-22.md
rg -n "dry-run|apply|异常|趋势|告警|巡检" collaboration/results/BASE_DISPATCH_ANOMALY_MONITORING_2026-03-22.md
python3 -m ai_collab.cli dispatch --dry-run --force-workspace
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [x] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [ ] completed
- [ ] failed
- [ ] cancelled
