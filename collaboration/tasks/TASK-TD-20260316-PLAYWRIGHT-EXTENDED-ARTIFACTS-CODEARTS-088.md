# 任务: Playwright 扩展套件脚本与产物口径稳定化

**任务ID**: TASK-TD-20260316-PLAYWRIGHT-EXTENDED-ARTIFACTS-CODEARTS-088  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [frontend-architect, systematic-debugging]
- **scope_in**:
  - 在 `tests/playwright/package.json` 增加显式 `test:popup:extended` / `test:popup:extended:ci` 套件别名，覆盖 axe + visual + perf
  - 在 `tests/playwright/playwright.config.js` 明确并稳定 junit / html / json / results 输出路径，保证 CI/nightly artifact 一致
  - 在 `tests/playwright/README.md` 补充 gate / extended / nightly 的执行矩阵
  - 在结果报告中解释本地、CI、nightly 三层运行入口如何对齐
- **scope_out**:
  - 不修改 `.github/workflows/ci.yml`
  - 不修改 `.github/workflows/nightly.yml`
  - 不扩充测试断言内容

## 输入

- `tests/playwright/package.json`
- `tests/playwright/playwright.config.js`
- `tests/playwright/README.md`
- `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-SCRIPT-BUNDLES-CODEARTS-085.md`
- `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-NIGHTLY-EXTENDED-GATE-CODEX-086.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-EXTENDED-ARTIFACTS-CODEARTS-088.md`
- 必须包含:
  - 新增 script 清单与命令说明
  - reporter / artifact 输出路径说明
  - gate / extended / nightly 执行矩阵
  - 风险与回滚

## acceptance_commands（必填）

```bash
(cd tests/playwright && npm run test:popup:extended -- --list && npm run test:popup:extended:ci -- --list)
rg -n "test:popup:extended|playwright-junit.xml|playwright-report|playwright-report.json" tests/playwright/package.json tests/playwright/playwright.config.js tests/playwright/README.md
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
