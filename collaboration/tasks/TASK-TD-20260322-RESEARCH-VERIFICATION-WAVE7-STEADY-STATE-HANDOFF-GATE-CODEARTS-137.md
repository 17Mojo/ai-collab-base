# 任务: Research verification wave7 steady state handoff gate

**任务ID**: TASK-TD-20260322-RESEARCH-VERIFICATION-WAVE7-STEADY-STATE-HANDOFF-GATE-CODEARTS-137  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 在 `135/136` 完成后，形成 Wave 7 steady-state handoff gate
  - 定义后续维护节奏、复用 helper repo/worktree 的入口与重启条件
  - 输出 Research Verification 从“战役模式”切换到“稳态模式”的最终门禁
  - 只处理研究/结果资产，不触碰产品代码
- **scope_out**:
  - 在 `135/136` 未完成前不执行
  - 不执行 branch cleanup
  - 不修改产品代码

## 输入

- `research/MULTI_AGENT_VERIFICATION_FINAL_ARCHIVE_SUMMARY_2026-03-22.md`
- `collaboration/results/RESEARCH_VERIFICATION_WAVE7_INDEX_STEADY_SYNC_2026-03-22.md`
- `collaboration/results/WAVE6_CLOSEOUT_SUMMARY_2026-03-22.md`

## 输出要求

- 资产文件: `collaboration/results/RESEARCH_VERIFICATION_WAVE7_STEADY_STATE_HANDOFF_GATE_2026-03-22.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260322-RESEARCH-VERIFICATION-WAVE7-STEADY-STATE-HANDOFF-GATE-CODEARTS-137.md`
- 必须包含:
  - `135/136` 收口摘要
  - steady-state 维护节奏
  - 何时重开正式验证波次
  - 风险与非破坏性回滚

## acceptance_commands（必填）

```bash
test -f collaboration/results/RESEARCH_VERIFICATION_WAVE7_STEADY_STATE_HANDOFF_GATE_2026-03-22.md
rg -n "135|136|steady state|handoff gate|重开|风险|回滚" collaboration/results/RESEARCH_VERIFICATION_WAVE7_STEADY_STATE_HANDOFF_GATE_2026-03-22.md
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
