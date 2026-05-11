# 任务: Popup 性能与负载 smoke 补齐

**任务ID**: TASK-TD-20260316-POPUP-PERF-SMOKE-CODEARTS-081  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [systematic-debugging, planning-with-files, frontend-architect]
- **scope_in**:
  - 为 Prompt Pack popup 增加 Playwright 性能/负载 smoke spec
  - 覆盖 100+ Pack 列表渲染、快速连续 execute、refresh 循环等高风险交互
  - 给出可执行、不过度脆弱的阈值与断言策略
  - 更新 README，说明本地与 CI 中如何解释性能失败
- **scope_out**:
  - 不做浏览器级 benchmark
  - 不引入真实外部网络依赖
  - 不改 popup 产品信息架构

## 输入

- `products/prompt-pack-extension/chrome/src/popup/popup.js`
- `products/prompt-pack-extension/chrome/src/popup/styles.css`
- `tests/playwright/README.md`
- `tests/playwright/tests/helpers/chromeHostMock.js`
- `tests/playwright/tests/popup.runtime.spec.js`
- `tests/playwright/tests/popup.a11y.spec.js`
- `tests/playwright/TEST_IMPROVEMENT_PLAN.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260316-POPUP-PERF-SMOKE-CODEARTS-081.md`
- 必须包含:
  - 新增性能/负载场景清单
  - 阈值与断言策略说明
  - 失败排查口径
  - 风险与回滚

## acceptance_commands（必填）

```bash
(cd tests/playwright && npm ci && npx playwright test tests/popup.performance.spec.js --reporter=list)
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
