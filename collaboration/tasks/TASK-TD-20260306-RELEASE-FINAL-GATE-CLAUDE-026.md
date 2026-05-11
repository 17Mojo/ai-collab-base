# 任务: 发布冲刺 - 最终门禁与 Go/No-Go 结论

**任务ID**: TASK-TD-20260306-RELEASE-FINAL-GATE-CLAUDE-026  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: devops-architect
- **support_skills**: [compliance-checker, api-test-pro]
- **scope_in**: 执行最终发布门禁，给出 Go/No-Go 结论与阻塞项清单（如有）。
- **scope_out**: 不新增功能，不改产品行为，仅允许修复阻塞发布的问题。

## 输入

- 文件: scripts/pre_release_check.sh, .github/workflows/ci.yml, docs/RELEASE_CHECKLIST.md, docs/RELEASE_NOTES.md

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260306-RELEASE-FINAL-GATE-CLAUDE-026.md`
- 必须包含: 执行命令、门禁结果、Go/No-Go 结论、风险与回滚点

## acceptance_commands（必填）

```bash
bash scripts/pre_release_check.sh --workspace . --with-locks
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

