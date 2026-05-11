# 任务: Research verification wave7 index steady sync

**任务ID**: TASK-TD-20260322-RESEARCH-VERIFICATION-WAVE7-INDEX-STEADY-SYNC-CLAUDE-136  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 将 Wave 6 已完成状态同步回研究主线索引与总结入口
  - 更新 `research/INDEX.md` 与 `research/MULTI_AGENT_COLLABORATION_FINAL_SUMMARY.md` 的状态口径
  - 产出一份 steady sync 审计资产，说明哪些入口已更新、哪些历史文档保持快照
  - 只做研究/文档状态同步，不触碰产品代码
- **scope_out**:
  - 不修改控制面协议
  - 不执行新的 worktree 删除
  - 不执行 branch cleanup

## 输入

- `collaboration/results/WAVE6_CLOSEOUT_SUMMARY_2026-03-22.md`
- `collaboration/results/RESEARCH_VERIFICATION_WAVE6_CLOSEOUT_GATE_2026-03-22.md`
- `research/INDEX.md`
- `research/MULTI_AGENT_COLLABORATION_FINAL_SUMMARY.md`

## 输出要求

- 资产文件: `collaboration/results/RESEARCH_VERIFICATION_WAVE7_INDEX_STEADY_SYNC_2026-03-22.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260322-RESEARCH-VERIFICATION-WAVE7-INDEX-STEADY-SYNC-CLAUDE-136.md`
- 必须包含:
  - 已同步入口清单
  - Wave 6 / Wave 1-6 完成状态口径
  - 历史快照与当前事实源的分工
  - 风险与非破坏性回滚

## acceptance_commands（必填）

```bash
test -f collaboration/results/RESEARCH_VERIFICATION_WAVE7_INDEX_STEADY_SYNC_2026-03-22.md
rg -n "Wave 6|Wave 1-6|steady state|历史快照|最终归档" research/INDEX.md research/MULTI_AGENT_COLLABORATION_FINAL_SUMMARY.md
rg -n "INDEX|final summary|Wave 6|steady state|同步|回滚" collaboration/results/RESEARCH_VERIFICATION_WAVE7_INDEX_STEADY_SYNC_2026-03-22.md
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
