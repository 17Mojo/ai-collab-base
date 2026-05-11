# 任务: Playwright Popup CI 门禁拆分与收敛

**任务ID**: TASK-TD-20260316-PLAYWRIGHT-CI-GATE-SPLIT-CLAUDE-084  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: frontend-architect
- **support_skills**: [planning-with-files, systematic-debugging, api-test-pro]
- **scope_in**:
  - 调整 `.github/workflows/ci.yml` 中的 Playwright job，只跑 popup 的稳定门禁集合，不再默认把 demo/spec 杂项全部混进 CI
  - 明确 CI 门禁应覆盖 runtime / error / a11y smoke / axe audit 这 4 类关键套件
  - 保持现有 artifact 上传链路可用，必要时补充更清晰的 step 命名
  - 不依赖新 workflow action，不改 Python gate/test job
- **scope_out**:
  - 不做 README 文档整理
  - 不做 nightly 扩展矩阵
  - 不改 popup 产品代码

## 输入

- `.github/workflows/ci.yml`
- `tests/playwright/package.json`
- `tests/playwright/playwright.config.js`
- `tests/playwright/tests/popup.runtime.spec.js`
- `tests/playwright/tests/error_handling.spec.js`
- `tests/playwright/tests/popup.a11y.spec.js`
- `tests/playwright/tests/popup.a11y.axe.spec.js`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-CI-GATE-SPLIT-CLAUDE-084.md`
- 必须包含:
  - 新 CI popup gate 的 suite 边界
  - workflow 变更点
  - artifact / triage 口径
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "Run Playwright popup gate|popup.runtime.spec.js|error_handling.spec.js|popup.a11y.spec.js|popup.a11y.axe.spec.js" .github/workflows/ci.yml
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
