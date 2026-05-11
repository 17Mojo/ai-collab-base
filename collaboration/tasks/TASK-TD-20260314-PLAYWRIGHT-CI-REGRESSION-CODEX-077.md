# 任务: Playwright CI 回归面收敛与执行口径固化

**任务ID**: TASK-TD-20260314-PLAYWRIGHT-CI-REGRESSION-CODEX-077  
**change_id**: bugfix/no-spec  
**分配给**: codex  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**:
  - 收敛 Playwright runtime suite 的 CI 入口
  - 明确错误处理用例的报告、trace、重跑与 README 口径
  - 统一 `popup.runtime` 与 `error_handling` 的执行方式，避免“本地能跑、CI 不稳定”
  - 形成后续可持续加例的基线
- **scope_out**:
  - 不做跨浏览器矩阵
  - 不做视觉快照基线治理
  - 不引入新测试框架

## 输入

- `tests/playwright/playwright.config.js`
- `tests/playwright/README.md`
- `tests/playwright/tests/error_handling.spec.js`
- `tests/playwright/tests/popup.runtime.spec.js`
- `tests/playwright/TEST_IMPROVEMENT_PLAN.md`
- `tests/playwright/TEST_IMPROVEMENT_SUMMARY.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260314-PLAYWRIGHT-CI-REGRESSION-CODEX-077.md`
- 必须包含:
  - CI 入口与报告产物口径
  - 失败复现命令
  - 当前覆盖边界与后续扩展建议
  - 风险与回滚

## acceptance_commands（必填）

```bash
(cd tests/playwright && npm ci && npx playwright install chromium && npx playwright test tests/popup.runtime.spec.js tests/error_handling.spec.js)
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
