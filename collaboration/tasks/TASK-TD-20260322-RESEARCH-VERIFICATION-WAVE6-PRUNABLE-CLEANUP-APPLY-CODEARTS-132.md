# 任务: Research verification wave6 prunable cleanup apply

**任务ID**: TASK-TD-20260322-RESEARCH-VERIFICATION-WAVE6-PRUNABLE-CLEANUP-APPLY-CODEARTS-132  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: systematic-debugging
- **support_skills**: [planning-with-files, api-test-pro]
- **scope_in**:
  - 只对 `git worktree list` 当前已标记为 `prunable` 的 `/private/tmp/*` worktree 执行 cleanup apply
  - 逐个执行 `git worktree remove <path>`，记录 before / after 清单
  - 明确保留主仓库与 helper repo，不触碰 `/private/tmp/cc-claude-codex`
  - 产出 cleanup apply 报告与回滚清单
- **scope_out**:
  - 不删除主仓库 worktree
  - 不删除 helper repo
  - 不做 branch cleanup
  - 不修改产品代码

## 输入

- `collaboration/results/WAVE5_CLOSEOUT_SUMMARY_2026-03-22.md`
- `collaboration/results/RESEARCH_VERIFICATION_WAVE5_WORKTREE_CLEANUP_PREFLIGHT_2026-03-21.md`
- `collaboration/results/RESEARCH_VERIFICATION_WAVE5_EXECUTION_GATE_2026-03-21.md`

## 输出要求

- 资产文件: `collaboration/results/RESEARCH_VERIFICATION_WAVE6_PRUNABLE_CLEANUP_APPLY_2026-03-22.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260322-RESEARCH-VERIFICATION-WAVE6-PRUNABLE-CLEANUP-APPLY-CODEARTS-132.md`
- 必须包含:
  - cleanup 前后 worktree 清单
  - 已删除路径列表
  - 未删除保留项说明
  - 风险与非破坏性回滚

## acceptance_commands（必填）

```bash
test -f collaboration/results/RESEARCH_VERIFICATION_WAVE6_PRUNABLE_CLEANUP_APPLY_2026-03-22.md
rg -n "before|after|prunable|removed|保留|风险|回滚" collaboration/results/RESEARCH_VERIFICATION_WAVE6_PRUNABLE_CLEANUP_APPLY_2026-03-22.md
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
