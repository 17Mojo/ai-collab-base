# 任务: Research verification wave2 bootstrap

**任务ID**: TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE2-BOOTSTRAP-CLAUDE-117  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: systematic-debugging
- **support_skills**: [planning-with-files, api-test-pro]
- **scope_in**:
  - 在 `TASK-TD-20260320-RESEARCH-VERIFICATION-WORKTREE-ISOLATION-CLAUDE-116` 完成后，复用 `/private/tmp/cc-claude-codex` 与 `/private/tmp/ai-collab-system-verify-wave2-claude`
  - 为 Wave 2 启动多智能体验证流程，固化入口命令、日志目录、输出目录、失败回退口径
  - 产出一份 bootstrap 资产，供后续 review / test / E2E 工单直接复用
  - 将 bootstrap 资产接入 `research/INDEX.md`
- **scope_out**:
  - 不重复执行 Wave 1 preflight
  - 不直接关闭 review / test / E2E 三个后续任务
  - 不修改主工作区产品代码

## 输入

- `research/MULTI_AGENT_VERIFICATION_PREFLIGHT_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_WORKTREE_ISOLATION_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_WAVE2_BOOTSTRAP_2026-03-20.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE2-BOOTSTRAP-CLAUDE-117.md`
- 必须包含:
  - 启动命令链
  - helper repo / worktree 复用说明
  - 日志与产物目录约定
  - 失败回滚
  - 对 118/119/120 的输入边界

## acceptance_commands（必填）

```bash
test -d /private/tmp/cc-claude-codex/.git
git -C /private/tmp/ai-collab-system-verify-wave2-claude rev-parse --is-inside-work-tree
test -f research/MULTI_AGENT_VERIFICATION_WAVE2_BOOTSTRAP_2026-03-20.md
rg -n "cc-claude-codex|ai-collab-system-verify-wave2-claude|日志|产物|回滚" \
  research/MULTI_AGENT_VERIFICATION_WAVE2_BOOTSTRAP_2026-03-20.md
rg -n "MULTI_AGENT_VERIFICATION_WAVE2_BOOTSTRAP_2026-03-20.md" research/INDEX.md
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
