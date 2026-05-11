# 任务: Research verification wave5 execution gate

**任务ID**: TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE5-EXECUTION-GATE-CODEARTS-131  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 在 `129/130` 完成后，整合 worktree cleanup preflight 与 backlog historical freeze
  - 输出下一轮是否可以进入真实 cleanup apply 的 execution gate
  - 明确哪些动作仍需人工确认，哪些动作可自动化
- **scope_out**:
  - 在 `129/130` 未完成前不执行
  - 不直接执行 worktree 删除
  - 不修改产品代码

## 输入

- `collaboration/results/RESEARCH_VERIFICATION_WAVE5_WORKTREE_CLEANUP_PREFLIGHT_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE5_HISTORICAL_FREEZE_2026-03-21.md`
- `collaboration/results/WAVE4_CLOSEOUT_SUMMARY_2026-03-21.md`

## 输出要求

- 资产文件: `collaboration/results/RESEARCH_VERIFICATION_WAVE5_EXECUTION_GATE_2026-03-21.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE5-EXECUTION-GATE-CODEARTS-131.md`
- 必须包含:
  - `129/130` 收口摘要
  - 自动化与人工确认边界
  - 下一轮执行门禁
  - 风险与非破坏性回滚

## acceptance_commands（必填）

```bash
test -f collaboration/results/RESEARCH_VERIFICATION_WAVE5_EXECUTION_GATE_2026-03-21.md
rg -n "129|130|execution gate|人工确认|风险|回滚" collaboration/results/RESEARCH_VERIFICATION_WAVE5_EXECUTION_GATE_2026-03-21.md
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [ ] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [x] blocked
- [ ] completed
- [ ] failed
- [ ] cancelled
