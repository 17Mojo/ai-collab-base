# 任务: Base governance healthcheck runbook

**任务ID**: TASK-TD-20260320-BASE-GOVERNANCE-HEALTHCHECK-RUNBOOK-CLAUDE-114  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于现有治理命令与历史 runbook，沉淀一份统一的基座健康检查执行手册
  - 明确 `workspace-guard / dispatch / trigger / receipt / ack-remediation / benefit / tasks validate-contract` 的标准执行顺序
  - 为日常巡检、派单前、收口后、异常排查四类场景给出最小命令链
  - 在结果报告中说明该 runbook 如何帮助把自动化收益比从当前 `2.09` 往目标 `3.0` 推进
- **scope_out**:
  - 不新增 CLI 子命令
  - 不修改 Prompt Pack 产品代码
  - 不重写现有派单协议

## 输入

- `collaboration/PROTOCOL.md`
- `collaboration/results/BASE_RESEARCH_7DAY_EXECUTION_PLAN_2026-03-19.md`
- `collaboration/results/POST_MERGE_DISPATCH_ACK_RUNBOOK_PLAYWRIGHT_2026-03-14.md`
- `collaboration/results/FINAL_DELIVERY_WAVE_CLOSE_2026-03-13.md`
- `ai_collab/cli.py`
- `collaboration/monitoring/AUTOMATION_BENEFIT_DASHBOARD_latest.md`

## 输出要求

- 资产文件: `collaboration/results/BASE_GOVERNANCE_HEALTHCHECK_RUNBOOK_2026-03-20.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260320-BASE-GOVERNANCE-HEALTHCHECK-RUNBOOK-CLAUDE-114.md`
- 必须包含:
  - 标准执行顺序
  - 场景化命令链
  - 异常排查入口
  - 风险与回滚

## acceptance_commands（必填）

```bash
test -f collaboration/results/BASE_GOVERNANCE_HEALTHCHECK_RUNBOOK_2026-03-20.md
rg -n "workspace-guard|dispatch|trigger|receipt|ack-remediation|benefit|validate-contract" \
  collaboration/results/BASE_GOVERNANCE_HEALTHCHECK_RUNBOOK_2026-03-20.md
python3 -m ai_collab.cli benefit --dry-run
python3 -m ai_collab.cli receipt --dry-run --force-workspace
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
