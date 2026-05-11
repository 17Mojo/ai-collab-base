# 任务: Research verification wave6 cleanup verify

**任务ID**: TASK-TD-20260322-RESEARCH-VERIFICATION-WAVE6-CLEANUP-VERIFY-CLAUDE-133  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 `132` 的 cleanup apply 结果做 cleanup 后核验
  - 验证 surviving worktree、helper repo 与主仓库均保持预期
  - 形成 rollback manifest 与残余风险说明
  - 产出下一步是否需要 branch cleanup 的判断
- **scope_out**:
  - 不执行新的 worktree 删除
  - 不执行 branch cleanup
  - 不修改产品代码

## 输入

- `collaboration/results/WAVE5_CLOSEOUT_SUMMARY_2026-03-22.md`
- `collaboration/results/RESEARCH_VERIFICATION_WAVE6_PRUNABLE_CLEANUP_APPLY_2026-03-22.md`
- `collaboration/results/RESEARCH_VERIFICATION_WAVE5_EXECUTION_GATE_2026-03-21.md`

## 输出要求

- 资产文件: `collaboration/results/RESEARCH_VERIFICATION_WAVE6_CLEANUP_VERIFY_2026-03-22.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260322-RESEARCH-VERIFICATION-WAVE6-CLEANUP-VERIFY-CLAUDE-133.md`
- 必须包含:
  - cleanup 后核验结论
  - surviving worktree / helper repo 状态
  - rollback manifest
  - branch cleanup 建议

## acceptance_commands（必填）

```bash
test -f collaboration/results/RESEARCH_VERIFICATION_WAVE6_CLEANUP_VERIFY_2026-03-22.md
rg -n "surviving|helper repo|rollback|branch cleanup|风险|回滚" collaboration/results/RESEARCH_VERIFICATION_WAVE6_CLEANUP_VERIFY_2026-03-22.md
git worktree list
test -d /private/tmp/cc-claude-codex
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
