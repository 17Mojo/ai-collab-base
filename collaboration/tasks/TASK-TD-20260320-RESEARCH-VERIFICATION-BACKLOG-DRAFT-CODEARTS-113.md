# 任务: Research verification backlog draft

**任务ID**: TASK-TD-20260320-RESEARCH-VERIFICATION-BACKLOG-DRAFT-CODEARTS-113  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [api-test-pro, systematic-debugging]
- **scope_in**:
  - 基于 `research/MULTI_AGENT_VERIFICATION_IMPLEMENTATION_PLAN.md` 与当前基座/研究已完成结果，整理一份可直接转工单的 backlog 草案
  - 将 backlog 按波次拆分，明确每项的目标、owner、依赖、建议验收命令与风险
  - 新建一份研究资产文档，并接入 `research/INDEX.md`，让后续 Codex 可以直接据此继续派单
  - 在结果报告中说明该 backlog 草案如何服务下一轮基座与研究协同
- **scope_out**:
  - 不修改 OpenSpec spec
  - 不新增 CLI 子命令
  - 不直接创建正式 `TASK-*` 工单池

## 输入

- `research/MULTI_AGENT_VERIFICATION_IMPLEMENTATION_PLAN.md`
- `research/MULTI_AGENT_VERIFICATION_ANALYSIS.md`
- `collaboration/results/BASE_RESEARCH_7DAY_EXECUTION_PLAN_2026-03-19.md`
- `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-STATE-SYNC-AUTOMATION-CODEARTS-099.md`
- `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-ASSEMBLY-ACCEPTANCE-GATE-CODEARTS-100.md`
- `collaboration/results/RESULT_TASK-TD-20260320-RESEARCH-ASSEMBLY-RUNBOOK-ASSET-CODEARTS-111.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260320-RESEARCH-VERIFICATION-BACKLOG-DRAFT-CODEARTS-113.md`
- 必须包含:
  - Wave 拆分
  - 候选任务清单
  - owner / reviewer / dependency 建议
  - 验收命令草案
  - 风险与回滚
  - 索引接入说明

## acceptance_commands（必填）

```bash
test -f research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md
rg -n "Wave|任务|owner|reviewer|依赖|验收命令|风险|回滚" \
  research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md
rg -n "MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md" research/INDEX.md
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
