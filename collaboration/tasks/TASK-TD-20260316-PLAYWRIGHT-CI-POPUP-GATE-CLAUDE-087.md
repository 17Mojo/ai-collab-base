# 任务: Playwright 主 CI Popup Gate 落地

**任务ID**: TASK-TD-20260316-PLAYWRIGHT-CI-POPUP-GATE-CLAUDE-087  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: devops-architect
- **support_skills**: [api-test-pro, systematic-debugging]
- **scope_in**:
  - 将 `.github/workflows/ci.yml` 的 Playwright job 从宽泛 `npm run test:ci` 收敛到显式 `npm run test:popup:gate:ci`
  - 更新 step 命名，使其明确表达 popup gate 边界
  - 保持 `ci-playwright-reports` artifact 上传口径连续，避免 triage 入口回退
  - 在结果报告中说明主 CI gate 与 nightly extended gate 的职责分层
- **scope_out**:
  - 不修改 nightly workflow
  - 不新增 package script
  - 不改 popup 测试内容本身

## 输入

- `.github/workflows/ci.yml`
- `tests/playwright/package.json`
- `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-CI-GATE-SPLIT-CLAUDE-084.md`
- `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-SCRIPT-BUNDLES-CODEARTS-085.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-CI-POPUP-GATE-CLAUDE-087.md`
- 必须包含:
  - 修改后的 CI step / command 摘要
  - 主 CI gate 覆盖的 suite 边界
  - artifact / triage 口径是否保持兼容
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "test:popup:gate:ci|ci-playwright-reports|Run Playwright popup gate" .github/workflows/ci.yml
(cd tests/playwright && npm run test:popup:gate -- --list)
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
