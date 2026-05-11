# 任务: Research verification wave1 preflight

**任务ID**: TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE1-PREFLIGHT-CODEARTS-115  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**:
  - 按 `research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md` 的 Wave 1 预检要求，完成 OpenCode CLI / Codex CLI 可用性检查
  - 若 `opencode` 缺失，则完成安装并记录版本与路径
  - 在 `/private/tmp/cc-claude-codex` 克隆 `cc-claude-codex` 仓库，避免污染主工作区
  - 新建一份预检资产文档，沉淀版本、路径、clone 位置、下一步依赖
  - 将该预检资产接入 `research/INDEX.md`
- **scope_out**:
  - 不修改本仓库产品代码
  - 不直接执行 Wave 2 验证流程
  - 不创建正式外部 worktree

## 输入

- `research/MULTI_AGENT_VERIFICATION_IMPLEMENTATION_PLAN.md`
- `research/MULTI_AGENT_VERIFICATION_BACKLOG_2026-03-20.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_PREFLIGHT_2026-03-20.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE1-PREFLIGHT-CODEARTS-115.md`
- 必须包含:
  - `opencode` / `codex` 版本与路径
  - clone 路径与仓库状态
  - Wave 1 完成度
  - 下一步依赖
  - 风险与回滚

## acceptance_commands（必填）

```bash
command -v codex
command -v opencode
test -d /private/tmp/cc-claude-codex/.git
test -f research/MULTI_AGENT_VERIFICATION_PREFLIGHT_2026-03-20.md
rg -n "MULTI_AGENT_VERIFICATION_PREFLIGHT_2026-03-20.md" research/INDEX.md
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
