# 任务: Playwright failure summary 真接入 CI / nightly

**任务ID**: TASK-TD-20260319-BASE-PLAYWRIGHT-FAILURE-SUMMARY-WORKFLOW-CODEARTS-107  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**:
  - 基于 `105` 的研究结论，在 `.github/workflows/ci.yml` 与 `.github/workflows/nightly.yml` 中接入 `report:summary` 的真实 workflow 步骤
  - 让 `logs/playwright-failure-summary.md` 成为稳定 artifact，减少人工翻 `playwright-report` / `trace` 的成本
  - 保持现有 popup gate / extended gate / nightly gate 的职责边界，不重写现有 Playwright 套件结构
  - 更新 `tests/playwright/README.md`，说明 CI/nightly 中 summary 的生成与查看路径
  - 在结果报告中说明本次接入如何缩短失败排障链路
- **scope_out**:
  - 不改 popup 产品代码
  - 不新增 Playwright spec
  - 不大改 `tests/playwright/scripts/playwright-summary.js` 逻辑，除非为 workflow 接线必须的小修

## 输入

- `.github/workflows/ci.yml`
- `.github/workflows/nightly.yml`
- `tests/playwright/package.json`
- `tests/playwright/README.md`
- `tests/playwright/scripts/playwright-summary.js`
- `collaboration/results/RESULT_TASK-TD-20260319-BASE-PLAYWRIGHT-CI-TRIAGE-GATE-CODEARTS-103.md`
- `collaboration/results/RESULT_TASK-TD-20260319-BASE-PLAYWRIGHT-SUMMARY-WORKFLOW-INTEGRATION-CODEARTS-105.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260319-BASE-PLAYWRIGHT-FAILURE-SUMMARY-WORKFLOW-CODEARTS-107.md`
- 必须包含:
  - workflow 真实变更摘要
  - summary 生成步骤与 artifact 上传口径
  - 与现有 gate/nightly 职责边界的兼容性说明
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "Generate Playwright failure summary|Upload Playwright failure summary|playwright-failure-summary|report:summary" \
  .github/workflows/ci.yml \
  .github/workflows/nightly.yml \
  tests/playwright/README.md \
  tests/playwright/package.json
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
