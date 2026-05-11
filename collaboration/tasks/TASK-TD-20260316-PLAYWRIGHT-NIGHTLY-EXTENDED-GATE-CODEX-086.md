# 任务: Playwright Popup Nightly 扩展门禁接入

**任务ID**: TASK-TD-20260316-PLAYWRIGHT-NIGHTLY-EXTENDED-GATE-CODEX-086  
**change_id**: bugfix/no-spec  
**分配给**: codex  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [planning-with-files, systematic-debugging]
- **scope_in**:
  - 扩展 `.github/workflows/nightly.yml`，增加 popup extended gate，覆盖 visual / perf / axe 等高信号但不必进主 CI 的套件
  - 保持 nightly artifact 可上传、失败可回溯
  - 明确 nightly job 与主 CI popup gate 的职责边界
  - 尽量使用显式命令，不依赖主 CI job 的上下文
- **scope_out**:
  - 不改 README 文档
  - 不改 `.github/workflows/ci.yml`
  - 不改 popup 产品代码

## 输入

- `.github/workflows/nightly.yml`
- `tests/playwright/package.json`
- `tests/playwright/playwright.config.js`
- `tests/playwright/tests/popup.a11y.axe.spec.js`
- `tests/playwright/tests/popup_visual_regression.spec.js`
- `tests/playwright/tests/popup.performance.spec.js`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-NIGHTLY-EXTENDED-GATE-CODEX-086.md`
- 必须包含:
  - nightly popup gate 覆盖范围
  - artifact 产物说明
  - 失败 triage 入口
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "popup.a11y.axe.spec.js|popup_visual_regression.spec.js|popup.performance.spec.js|playwright" .github/workflows/nightly.yml
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
