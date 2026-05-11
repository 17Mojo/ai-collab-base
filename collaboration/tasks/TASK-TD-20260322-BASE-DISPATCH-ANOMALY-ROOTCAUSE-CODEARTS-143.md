# 任务: Base dispatch anomaly rootcause

**任务ID**: TASK-TD-20260322-BASE-DISPATCH-ANOMALY-ROOTCAUSE-CODEARTS-143  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 `BASE_DISPATCH_SUCCESS_BASELINE_2026-03-22.md`，深挖 18 个异常空派单样本的根因
  - 对 `candidate_count>0 且 dispatched_count=0` 的样本做分类，区分环境因素、门禁因素、逻辑因素
  - 输出下一轮 dispatch 代码修复所需的最小证据包与 backlog
  - 不修改产品代码，只产出根因分析资产
- **scope_out**:
  - 不修改 `ai_collab` 源码
  - 不调整 benefit 计算口径
  - 不重开研究验证线任务

## 输入

- `collaboration/results/BASE_DISPATCH_SUCCESS_BASELINE_2026-03-22.md`
- `collaboration/results/RESULT_TASK-TD-20260322-BASE-DISPATCH-SUCCESS-BASELINE-CODEARTS-141.md`
- `logs/task_dispatch_history.jsonl`
- `logs/task_dispatch_report.json`
- `collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md`

## 输出要求

- 资产文件: `collaboration/results/BASE_DISPATCH_ANOMALY_ROOTCAUSE_2026-03-22.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260322-BASE-DISPATCH-ANOMALY-ROOTCAUSE-CODEARTS-143.md`
- 必须包含:
  - 18 个异常样本的分类摘要
  - 根因分组
  - “正常空运行 / 异常空派单 / 可忽略噪声” 的判定口径
  - 下一轮 dispatch uplift backlog

## acceptance_commands（必填）

```bash
test -f collaboration/results/BASE_DISPATCH_ANOMALY_ROOTCAUSE_2026-03-22.md
rg -n "18|异常|candidate_count|dispatched_count|根因|backlog" collaboration/results/BASE_DISPATCH_ANOMALY_ROOTCAUSE_2026-03-22.md
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
