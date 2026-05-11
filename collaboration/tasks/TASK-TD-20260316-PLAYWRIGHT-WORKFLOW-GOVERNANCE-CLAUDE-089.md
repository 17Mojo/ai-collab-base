# 任务: Playwright Workflow 并发治理与队列降噪

**任务ID**: TASK-TD-20260316-PLAYWRIGHT-WORKFLOW-GOVERNANCE-CLAUDE-089  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: devops-architect
- **support_skills**: [api-test-pro, systematic-debugging]
- **scope_in**:
  - 在 `.github/workflows/ci.yml` 与 `.github/workflows/nightly.yml` 增加安全的 workflow/job 并发治理，避免同分支或同工作流重复运行长期占用队列
  - 为长耗时 Playwright / nightly 相关 job 增加明确 `timeout-minutes`，降低卡死 run 长时间占坑风险
  - 保持现有 artifact 名称、测试命令、通知链路兼容，不改变主 CI popup gate 与 nightly extended gate 的职责边界
  - 在结果报告中说明本次治理对 queue waste、回归信号稳定性、排障效率的收益
- **scope_out**:
  - 不修改 `tests/playwright/package.json`
  - 不修改 Playwright 测试 spec 或断言
  - 不新增或拆分 workflow 文件

## 输入

- `.github/workflows/ci.yml`
- `.github/workflows/nightly.yml`
- `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-CI-POPUP-GATE-CLAUDE-087.md`
- `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-EXTENDED-ARTIFACTS-CODEARTS-088.md`
- `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-NIGHTLY-EXTENDED-GATE-CODEX-086.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-WORKFLOW-GOVERNANCE-CLAUDE-089.md`
- 必须包含:
  - 新增 concurrency / timeout 策略摘要
  - 哪些重复运行会被自动收敛，哪些不会
  - 对 CI / nightly 现有 artifact 与通知的兼容性判断
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "concurrency:|cancel-in-progress|timeout-minutes" .github/workflows/ci.yml .github/workflows/nightly.yml
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
