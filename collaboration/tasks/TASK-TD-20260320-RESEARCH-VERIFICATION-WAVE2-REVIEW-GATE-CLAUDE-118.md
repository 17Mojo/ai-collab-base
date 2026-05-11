# 任务: Research verification wave2 review gate

**任务ID**: TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE2-REVIEW-GATE-CLAUDE-118  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: systematic-debugging
- **support_skills**: [planning-with-files, api-test-pro]
- **scope_in**:
  - 在 `TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE2-BOOTSTRAP-CLAUDE-117` 完成后，执行 Wave 2 的代码审查门禁
  - 复用 `/private/tmp/cc-claude-codex` 与 `/private/tmp/ai-collab-system-verify-wave2-claude`，输出一份 review 报告资产
  - 明确发现项等级、建议修复范围、可直接移交给测试/E2E 工单的输入
  - 将 review 报告接入 `research/INDEX.md`
- **scope_out**:
  - 不重复做 bootstrap 与 worktree 配置
  - 不直接执行 CodeArts 的测试与 E2E 验收
  - 不在主工作区提交产品改动

## 输入

- `research/MULTI_AGENT_VERIFICATION_WAVE2_BOOTSTRAP_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_WORKTREE_ISOLATION_2026-03-20.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_REVIEW_REPORT_2026-03-20.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE2-REVIEW-GATE-CLAUDE-118.md`
- 必须包含:
  - review 范围
  - 分级发现
  - 建议修复 / 不修复项
  - 对 119/120 的输入说明
  - 风险与回滚

## acceptance_commands（必填）

```bash
git -C /private/tmp/ai-collab-system-verify-wave2-claude rev-parse --is-inside-work-tree
test -f research/MULTI_AGENT_VERIFICATION_REVIEW_REPORT_2026-03-20.md
rg -n "Critical|Warning|Info|风险|回滚|输入" research/MULTI_AGENT_VERIFICATION_REVIEW_REPORT_2026-03-20.md
rg -n "MULTI_AGENT_VERIFICATION_REVIEW_REPORT_2026-03-20.md" research/INDEX.md
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
