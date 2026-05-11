# 任务: Playwright failure summary workflow 真落地

**任务ID**: TASK-TD-20260319-BASE-PLAYWRIGHT-FAILURE-SUMMARY-WORKFLOW-REAL-CODEARTS-109  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**:
  - 在 `.github/workflows/ci.yml` 与 `.github/workflows/nightly.yml` 中真正接入 `Generate Playwright failure summary` 与 `Upload Playwright failure summary`
  - 让 `tests/playwright/package.json` 的 `report:summary` 在 workflow 中有真实调用路径
  - 更新 `tests/playwright/README.md`，说明 CI/nightly 中的 failure summary 产出与查看方式
  - 保持现有 popup gate / nightly gate 的结构，不重写 Playwright 套件
  - 在结果报告中说明本次变更如何缩短失败排障链路
- **scope_out**:
  - 不改 popup 产品代码
  - 不新增 Playwright spec
  - 不把 task 退回成纯研究报告

## 输入

- `.github/workflows/ci.yml`
- `.github/workflows/nightly.yml`
- `tests/playwright/package.json`
- `tests/playwright/README.md`
- `tests/playwright/scripts/playwright-summary.js`
- `collaboration/results/RESULT_TASK-TD-20260319-BASE-PLAYWRIGHT-FAILURE-SUMMARY-WORKFLOW-CODEARTS-107.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260319-BASE-PLAYWRIGHT-FAILURE-SUMMARY-WORKFLOW-REAL-CODEARTS-109.md`
- 必须包含:
  - 实际 workflow 变更摘要
  - summary 生成与 artifact 上传路径
  - CI/nightly 触发条件说明
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "Generate Playwright failure summary|Upload Playwright failure summary" \
  .github/workflows/ci.yml \
  .github/workflows/nightly.yml
rg -n "playwright-failure-summary|report:summary" \
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
