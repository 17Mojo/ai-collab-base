# 任务: Playwright failure summary 接入 CI / nightly triage gate

**任务ID**: TASK-TD-20260319-BASE-PLAYWRIGHT-CI-TRIAGE-GATE-CODEARTS-103  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [systematic-debugging, planning-with-files]
- **scope_in**:
  - 基于 `090` 的 failure summary 脚本与当前 Playwright workflow，沉淀一份稳定的 CI / nightly triage gate 接入方案
  - 明确 summary、report、trace、screenshot 的默认诊断入口与 artifact 口径
  - 补充 README / workflow 侧最小对齐建议，减少人工翻 artifact 排障
  - 在结果报告中说明该 gate 如何承接现有 popup gate / extended gate / nightly extended gate
- **scope_out**:
  - 不改 popup 产品代码
  - 不扩展新的 Playwright spec
  - 不重写现有 failure summary 脚本

## 输入

- `tests/playwright/scripts/playwright-summary.js`
- `tests/playwright/README.md`
- `tests/playwright/package.json`
- `.github/workflows/ci.yml`
- `.github/workflows/nightly.yml`
- `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-FAILURE-SUMMARY-CODEARTS-090.md`
- `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-EXTENDED-ARTIFACTS-CODEARTS-088.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260319-BASE-PLAYWRIGHT-CI-TRIAGE-GATE-CODEARTS-103.md`
- 必须包含:
  - triage gate 接入建议
  - artifact / summary / trace 默认路径口径
  - CI / nightly 对齐关系
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "report:summary|playwright-failure-summary|playwright-report.json|trace.zip|screenshot" \
  tests/playwright \
  .github/workflows/ci.yml \
  .github/workflows/nightly.yml
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
