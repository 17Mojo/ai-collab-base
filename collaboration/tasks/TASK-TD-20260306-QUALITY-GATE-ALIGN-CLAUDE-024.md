# 任务: 质量门禁对齐 - Lint 策略与 CI 显式化

**任务ID**: TASK-TD-20260306-QUALITY-GATE-ALIGN-CLAUDE-024  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: devops-architect
- **support_skills**: [compliance-checker, api-test-pro]
- **scope_in**: 明确并落地 lint 策略（tests 是否纳入及如何分阶段治理），使 pre-release/CI/文档三者一致。
- **scope_out**: 不大规模重写测试代码，不调整业务功能。

## 输入

- 文件: scripts/pre_release_check.sh, .github/workflows/ci.yml, docs/RELEASE_CHECKLIST.md, docs/README_TESTING.md
- 上下文: 当前 `ruff check ai_collab src/ai_collab` 通过，但 `ruff check ... tests` 存在历史债务，口径需统一。

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260306-QUALITY-GATE-ALIGN-CLAUDE-024.md`
- 必须包含: 门禁策略决策、CI 变更摘要、测试结论、风险与回滚

## acceptance_commands（必填）

```bash
bash scripts/pre_release_check.sh --workspace . --quick --with-locks
python3 -m ruff check ai_collab src/ai_collab
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

