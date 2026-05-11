# 任务: Base dispatch success baseline

**任务ID**: TASK-TD-20260322-BASE-DISPATCH-SUCCESS-BASELINE-CODEARTS-141  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 `138` 的 triage 结果，沉淀 dispatch 成功率基线与失败样本清单
  - 区分正常 `candidate_count=0` 空运行与异常 `candidate_count > 0 但 dispatched_count=0`
  - 形成下一步 dispatch uplift 所需的 operator / reviewer 证据，不修改产品代码
  - 输出最小可执行的 dispatch 改进 backlog
- **scope_out**:
  - 不修改 `ai_collab` 源码
  - 不调整 benefit 计算口径
  - 不重开研究验证线任务

## 输入

- `collaboration/results/BASE_AUTOMATION_BENEFIT_TRIAGE_2026-03-22.md`
- `collaboration/results/BASE_HEALTHCHECK_OPERATOR_SUMMARY_2026-03-22.md`
- `logs/task_dispatch_history.jsonl`
- `logs/task_dispatch_report.json`
- `collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md`

## 输出要求

- 资产文件: `collaboration/results/BASE_DISPATCH_SUCCESS_BASELINE_2026-03-22.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260322-BASE-DISPATCH-SUCCESS-BASELINE-CODEARTS-141.md`
- 必须包含:
  - dispatch 成功率基线
  - 失败样本分类
  - 正常空运行与异常空派单的区分口径
  - 下一轮 dispatch uplift backlog

## acceptance_commands（必填）

```bash
test -f collaboration/results/BASE_DISPATCH_SUCCESS_BASELINE_2026-03-22.md
rg -n "dispatch|candidate_count|dispatched_count|空运行|失败样本|backlog" collaboration/results/BASE_DISPATCH_SUCCESS_BASELINE_2026-03-22.md
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
