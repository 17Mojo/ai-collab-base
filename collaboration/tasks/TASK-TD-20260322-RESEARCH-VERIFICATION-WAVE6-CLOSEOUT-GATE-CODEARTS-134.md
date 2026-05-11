# 任务: Research verification wave6 closeout gate

**任务ID**: TASK-TD-20260322-RESEARCH-VERIFICATION-WAVE6-CLOSEOUT-GATE-CODEARTS-134  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 在 `132/133` 完成后，汇总 cleanup apply 与 cleanup verify 结果
  - 输出 Wave 6 closeout gate，明确是否需要进入 branch cleanup 波次
  - 形成最终门禁、风险与下一轮建议
- **scope_out**:
  - 在 `132/133` 未完成前不执行
  - 不直接执行 branch cleanup
  - 不修改产品代码

## 输入

- `collaboration/results/RESEARCH_VERIFICATION_WAVE6_PRUNABLE_CLEANUP_APPLY_2026-03-22.md`
- `collaboration/results/RESEARCH_VERIFICATION_WAVE6_CLEANUP_VERIFY_2026-03-22.md`
- `collaboration/results/WAVE5_CLOSEOUT_SUMMARY_2026-03-22.md`

## 输出要求

- 资产文件: `collaboration/results/RESEARCH_VERIFICATION_WAVE6_CLOSEOUT_GATE_2026-03-22.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260322-RESEARCH-VERIFICATION-WAVE6-CLOSEOUT-GATE-CODEARTS-134.md`
- 必须包含:
  - `132/133` 收口摘要
  - branch cleanup 是否进入下一波
  - 风险与非破坏性回滚

## acceptance_commands（必填）

```bash
test -f collaboration/results/RESEARCH_VERIFICATION_WAVE6_CLOSEOUT_GATE_2026-03-22.md
rg -n "132|133|branch cleanup|closeout gate|风险|回滚" collaboration/results/RESEARCH_VERIFICATION_WAVE6_CLOSEOUT_GATE_2026-03-22.md
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
