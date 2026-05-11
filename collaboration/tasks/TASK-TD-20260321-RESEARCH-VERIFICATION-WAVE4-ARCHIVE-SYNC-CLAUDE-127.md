# 任务: Research verification wave4 archive sync

**任务ID**: TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE4-ARCHIVE-SYNC-CLAUDE-127  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 Wave 3 closeout 结论，整理 verification 资产的 archive / closeout / index / backlog 同步方案
  - 将 `research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md` 收正为历史快照口径，不再作为下一波直接派单源
  - 让 `research/INDEX.md` 能准确指向 Wave 3 closeout 与 Wave 4 archive sync 资产
  - 输出下一步归档建议与依赖边界
- **scope_out**:
  - 不执行 worktree 清理动作
  - 不重跑 Wave 1~3 历史验证
  - 不修改主工作区产品代码

## 输入

- `collaboration/results/WAVE3_CLOSEOUT_SUMMARY_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_WAVE3_FINAL_VALIDATION_REPORT_2026-03-21.md`
- `research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_WAVE4_ARCHIVE_SYNC_2026-03-21.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260321-RESEARCH-VERIFICATION-WAVE4-ARCHIVE-SYNC-CLAUDE-127.md`
- 必须包含:
  - archive / closeout / index / backlog 同步清单
  - backlog 历史快照化建议
  - Wave 4 后续依赖说明
  - 风险与非破坏性回滚

## acceptance_commands（必填）

```bash
test -f research/MULTI_AGENT_VERIFICATION_WAVE4_ARCHIVE_SYNC_2026-03-21.md
rg -n "archive|closeout|historical snapshot|Wave 4|风险|回滚" research/MULTI_AGENT_VERIFICATION_WAVE4_ARCHIVE_SYNC_2026-03-21.md
rg -n "MULTI_AGENT_VERIFICATION_WAVE4_ARCHIVE_SYNC_2026-03-21.md" research/INDEX.md
rg -n "historical snapshot|不再作为派单源|历史快照" research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md
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
