# 任务: Research verification wave2 e2e gate

**任务ID**: TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE2-E2E-GATE-CODEARTS-120  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [systematic-debugging, planning-with-files]
- **scope_in**:
  - 在 `TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE2-TEST-GATE-CODEARTS-119` 完成后，复用现有 helper repo 与隔离 worktree 执行 Wave 2 E2E 门禁
  - 产出 E2E 执行报告，覆盖命令、结果、失败样本、回滚路径
  - 将 E2E 报告接入 `research/INDEX.md`
- **scope_out**:
  - 不重复做 Wave 1 / bootstrap / review / test gate
  - 不修改主工作区产品代码
  - 不做 Wave 3 综合修复

## 输入

- `research/MULTI_AGENT_VERIFICATION_WAVE2_BOOTSTRAP_2026-03-20.md`
- `research/MULTI_AGENT_VERIFICATION_TEST_REPORT_2026-03-20.md`
- `research/INDEX.md`

## 输出要求

- 资产文件: `research/MULTI_AGENT_VERIFICATION_E2E_REPORT_2026-03-20.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260320-RESEARCH-VERIFICATION-WAVE2-E2E-GATE-CODEARTS-120.md`
- 必须包含:
  - E2E 命令链
  - 通过 / 失败摘要
  - 失败样本位置
  - 是否可进入 Wave 3
  - 风险与回滚

## acceptance_commands（必填）

```bash
test -f research/MULTI_AGENT_VERIFICATION_E2E_REPORT_2026-03-20.md
rg -n "E2E|通过|失败|样本|Wave 3|风险|回滚" research/MULTI_AGENT_VERIFICATION_E2E_REPORT_2026-03-20.md
rg -n "MULTI_AGENT_VERIFICATION_E2E_REPORT_2026-03-20.md" research/INDEX.md
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
