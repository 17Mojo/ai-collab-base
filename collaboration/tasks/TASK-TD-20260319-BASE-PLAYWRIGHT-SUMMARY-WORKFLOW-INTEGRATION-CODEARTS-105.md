# 任务: Playwright failure summary 接入 CI / nightly workflow

**任务ID**: TASK-TD-20260319-BASE-PLAYWRIGHT-SUMMARY-WORKFLOW-INTEGRATION-CODEARTS-105  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [systematic-debugging, planning-with-files]
- **scope_in**:
  - 基于 `103` 的分析结果，在 `.github/workflows/ci.yml` 与 `.github/workflows/nightly.yml` 中接入 `report:summary` 的最小 workflow 集成
  - 明确 `logs/playwright-failure-summary.md` 的 artifact 上传路径与触发条件
  - 保持现有 popup gate / extended gate / nightly gate 的职责边界，不重写现有 Playwright 套件结构
  - 在结果报告中说明本次接入如何减少人工翻 artifact 排障
- **scope_out**:
  - 不改 popup 产品代码
  - 不新增 Playwright spec
  - 不重写 `playwright-summary.js`

## 输入

- `.github/workflows/ci.yml`
- `.github/workflows/nightly.yml`
- `tests/playwright/package.json`
- `tests/playwright/README.md`
- `tests/playwright/scripts/playwright-summary.js`
- `collaboration/results/RESULT_TASK-TD-20260319-BASE-PLAYWRIGHT-CI-TRIAGE-GATE-CODEARTS-103.md`
- `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-FAILURE-SUMMARY-CODEARTS-090.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260319-BASE-PLAYWRIGHT-SUMMARY-WORKFLOW-INTEGRATION-CODEARTS-105.md`
- 必须包含:
  - workflow 变更摘要
  - summary artifact 上传口径
  - 与现有 gate/nightly 职责边界的兼容性说明
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "report:summary|playwright-failure-summary|upload-artifact|playwright-report.json" \
  .github/workflows/ci.yml \
  .github/workflows/nightly.yml \
  tests/playwright/package.json \
  tests/playwright/README.md
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
