# 任务: Playwright 演示与 CI 可观测性增强

**任务ID**: TASK-TD-20260311-PLAYWRIGHT-OBSERVABILITY-CODEARTS-056  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [frontend-architect, planning-with-files]
- **scope_in**:
  - 增强 Playwright 产物可观测性（失败时更快定位：日志、trace、关键步骤记录）
  - 统一 popup runtime 用例输出格式（含关键 action 序列）
  - 补充 README 中“本地直播演示”和“CI 复现”操作节
- **scope_out**:
  - 不改业务逻辑
  - 不改 OpenSpec 已归档能力边界

## 输入

- `tests/playwright/playwright.config.js`
- `tests/playwright/tests/popup.runtime.spec.js`
- `tests/playwright/README.md`
- `logs/playwright-report/`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260311-PLAYWRIGHT-OBSERVABILITY-CODEARTS-056.md`
- 必须包含:
  - 新增/优化的可观测性点清单
  - CI 与本地运行命令
  - 风险与回滚

## acceptance_commands（必填）

```bash
cd tests/playwright && npm run test:ci
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
