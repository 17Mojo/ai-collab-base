# 任务: Research verification wave5 worktree cleanup preflight

**任务ID**: TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE5-WORKTREE-CLEANUP-PREFLIGHT-CODEARTS-129  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 Wave 4 retention plan，对当前 worktree 现状做安全执行前核对
  - 为每个 `prunable` worktree 生成 keep / remove-candidate / manual-check 三段式 manifest
  - 对 `ack-governance-clean-20260317` 形成明确 keep/drop 建议
  - 仅输出 preflight manifest 与执行前检查，不直接删除任何 worktree
- **scope_out**:
  - 不执行 `git worktree remove`
  - 不执行分支删除
  - 不修改产品代码

## 输入

- `collaboration/results/WAVE4_CLOSEOUT_SUMMARY_2026-03-21.md`
- `collaboration/results/RESEARCH_VERIFICATION_WAVE4_WORKTREE_RETENTION_PLAN_2026-03-21.md`
- `collaboration/results/RESEARCH_VERIFICATION_WAVE4_HANDOFF_GATE_2026-03-21.md`

## 输出要求

- 资产文件: `collaboration/results/RESEARCH_VERIFICATION_WAVE5_WORKTREE_CLEANUP_PREFLIGHT_2026-03-21.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE5-WORKTREE-CLEANUP-PREFLIGHT-CODEARTS-129.md`
- 必须包含:
  - 当前 worktree 实测清单
  - 每个候选项的 preflight 判定
  - `ack-governance-clean-20260317` 决策建议
  - 执行前核对命令
  - 风险与非破坏性回滚

## acceptance_commands（必填）

```bash
test -f collaboration/results/RESEARCH_VERIFICATION_WAVE5_WORKTREE_CLEANUP_PREFLIGHT_2026-03-21.md
rg -n "prunable|manual-check|remove-candidate|ack-governance-clean|风险|回滚" collaboration/results/RESEARCH_VERIFICATION_WAVE5_WORKTREE_CLEANUP_PREFLIGHT_2026-03-21.md
git worktree list
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
