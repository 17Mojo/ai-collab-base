# 任务: SSOT 收敛 - 文档与运行状态快照一致化

**任务ID**: TASK-TD-20260306-SSOT-SNAPSHOT-CLAUDE-021  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [compliance-checker, devops-architect]
- **scope_in**: 统一 README、PROJECT_INTRODUCTION、项目进展快照中的任务/测试/角色口径，消除过期与冲突信息。
- **scope_out**: 不改业务逻辑，不改现有 API 行为。

## 输入

- 文件: README.md, docs/PROJECT_INTRODUCTION.md, collaboration/results/PROJECT_PROGRESS_SYNC_2026-03-01.md
- 上下文: 当前实测 `pytest -q` 为 643 passed，协作角色基线已从 copilot 迁移到 codearts_agent。

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260306-SSOT-SNAPSHOT-CLAUDE-021.md`
- 必须包含: 口径差异清单、修正点、验证命令、风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q
python3 -m ai_collab.cli status
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

