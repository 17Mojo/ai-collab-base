# 任务: Research verification wave2 test gate

**任务ID**: TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE2-TEST-GATE-CODEARTS-119  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [systematic-debugging, planning-with-files]
- **scope_in**:
  - 在 `TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE2-BOOTSTRAP-CLAUDE-117` 完成后，复用 `/private/tmp/cc-claude-codex` 与约定 worktree 执行 Wave 2 测试门禁
  - 产出测试执行报告，覆盖命令、结果、失败分类、是否可进入 E2E
  - 将测试报告接入 `research/INDEX.md`
- **scope_out**:
  - 不重复做 Wave 1 preflight
  - 不重写 Claude 的 review 报告
  - 不直接修改主工作区产品代码

## 输入

- `research/MULTI_AGENT_VERIFICATION_WAVE2_BOOTSTRAP_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_REVIEW_REPORT_2026-03-20.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_TEST_REPORT_2026-03-20.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE2-TEST-GATE-CODEARTS-119.md`
- 必须包含:
  - 测试命令
  - 通过 / 失败摘要
  - 是否允许进入 E2E
  - 风险与回滚

## acceptance_commands（必填）

```bash
test -f research/MULTI_AGENT_VERIFICATION_TEST_REPORT_2026-03-20.md
rg -n "pytest|test|通过|失败|E2E|风险|回滚" research/MULTI_AGENT_VERIFICATION_TEST_REPORT_2026-03-20.md
rg -n "MULTI_AGENT_VERIFICATION_TEST_REPORT_2026-03-20.md" research/INDEX.md
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [ ] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [x] blocked
- [ ] completed
- [ ] failed
- [ ] cancelled
