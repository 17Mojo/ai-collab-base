# 任务: Playwright Popup 脚本分层与套件别名补齐

**任务ID**: TASK-TD-20260316-PLAYWRIGHT-SCRIPT-BUNDLES-CODEARTS-085  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [systematic-debugging, planning-with-files, frontend-architect]
- **scope_in**:
  - 为 `tests/playwright/package.json` 增加 popup 分层脚本：`test:popup:gate` / `test:popup:gate:ci` / `test:visual` / `test:visual:ci` / `test:perf` / `test:perf:ci`
  - 必要时对 `tests/playwright/playwright.config.js` 做最小调整，确保 CI/local artifact 行为不被破坏
  - 让脚本边界和现有 suite 对齐：runtime+error+a11y+axe 属于 gate，visual/perf 属于扩展层
  - 不改 README 文档口径
- **scope_out**:
  - 不做 workflow YAML 修改
  - 不改 popup 产品代码
  - 不引入新测试框架

## 输入

- `tests/playwright/package.json`
- `tests/playwright/playwright.config.js`
- `tests/playwright/tests/popup.runtime.spec.js`
- `tests/playwright/tests/error_handling.spec.js`
- `tests/playwright/tests/popup.a11y.spec.js`
- `tests/playwright/tests/popup.a11y.axe.spec.js`
- `tests/playwright/tests/popup_visual_regression.spec.js`
- `tests/playwright/tests/popup.performance.spec.js`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-SCRIPT-BUNDLES-CODEARTS-085.md`
- 必须包含:
  - 新增 scripts 清单
  - gate / extended 分层说明
  - 执行验证结果
  - 风险与回滚

## acceptance_commands（必填）

```bash
(cd tests/playwright && npm run test:popup:gate -- --list && npm run test:visual -- --list && npm run test:perf -- --list)
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
