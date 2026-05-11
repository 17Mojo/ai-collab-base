# 任务: Research verification worktree isolation

**任务ID**: TASK-TD-20260320-RESEARCH-VERIFICATION-WORKTREE-ISOLATION-CLAUDE-116  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 `research/MULTI_AGENT_VERIFICATION_PREFLIGHT_2026-03-20.md` 的已完成基线，复用 `/private/tmp/cc-claude-codex` 作为 helper repo，不重复执行 Wave 1 安装与 clone
  - 为当前仓库创建独立验证 worktree：`/private/tmp/ai-collab-system-verify-wave2-claude`
  - 沉淀一份 worktree 隔离资产文档，明确 helper repo、主仓库 worktree、建议的后续 CodeArts worktree 预留路径、owner lock、回滚与清理口径
  - 将该资产接入 `research/INDEX.md`
- **scope_out**:
  - 不重复安装 `codex` / `opencode`
  - 不重新 clone `cc-claude-codex`
  - 不直接执行 Wave 2 审查 / 测试 / E2E
  - 不删除现有 `/private/tmp` 历史 worktree

## 输入

- `research/MULTI_AGENT_VERIFICATION_PREFLIGHT_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_IMPLEMENTATION_PLAN.md`
- `research/INDEX.md`
- `collaboration/PROTOCOL.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_WORKTREE_ISOLATION_2026-03-20.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260320-RESEARCH-VERIFICATION-WORKTREE-ISOLATION-CLAUDE-116.md`
- 必须包含:
  - helper repo 复用说明（`/private/tmp/cc-claude-codex`）
  - worktree 创建路径与命令
  - owner lock / 写集隔离建议
  - 下一步如何承接 Wave 2
  - 风险与回滚

## acceptance_commands（必填）

```bash
test -d /private/tmp/cc-claude-codex/.git
test -f research/MULTI_AGENT_VERIFICATION_WORKTREE_ISOLATION_2026-03-20.md
rg -n "cc-claude-codex|worktree|/private/tmp/ai-collab-system-verify-wave2-claude|owner lock|回滚" \
  research/MULTI_AGENT_VERIFICATION_WORKTREE_ISOLATION_2026-03-20.md
git worktree list | rg "/private/tmp/ai-collab-system-verify-wave2-claude"
rg -n "MULTI_AGENT_VERIFICATION_WORKTREE_ISOLATION_2026-03-20.md" research/INDEX.md
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [ ] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [x] completed
- [ ] failed
- [ ] cancelled
