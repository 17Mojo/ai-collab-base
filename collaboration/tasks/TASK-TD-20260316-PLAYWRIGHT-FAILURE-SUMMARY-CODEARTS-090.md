# 任务: Playwright 失败摘要与制品分诊摘要脚本

**任务ID**: TASK-TD-20260316-PLAYWRIGHT-FAILURE-SUMMARY-CODEARTS-090  
**change_id**: bugfix/no-spec  
**分配给**: codearts_agent  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: api-test-pro
- **support_skills**: [devops-architect, systematic-debugging]
- **scope_in**:
  - 在 `tests/playwright/` 下新增可复用的失败摘要脚本，优先消费 `logs/playwright-report.json`，必要时兼容 `logs/playwright-junit.xml`
  - 输出稳定的 markdown 摘要文件，聚合 suite 通过/失败数、失败用例名、trace/screenshot/report triage 路径
  - 在 `tests/playwright/package.json` 提供统一入口脚本，在 `tests/playwright/README.md` 补充使用方式
  - 结果报告中说明该摘要如何帮助 CI/nightly 更快定位失败，而不依赖人工逐个翻 artifact
- **scope_out**:
  - 不修改 `.github/workflows/ci.yml`
  - 不修改 `.github/workflows/nightly.yml`
  - 不改现有 Playwright spec 断言

## 输入

- `tests/playwright/package.json`
- `tests/playwright/README.md`
- `tests/playwright/playwright.config.js`
- `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-EXTENDED-ARTIFACTS-CODEARTS-088.md`
- `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-CI-POPUP-GATE-CLAUDE-087.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260316-PLAYWRIGHT-FAILURE-SUMMARY-CODEARTS-090.md`
- 必须包含:
  - 新增脚本入口与参数摘要
  - 生成的 markdown 摘要文件路径
  - 失败 triage 信息有哪些字段
  - 风险与回滚

## acceptance_commands（必填）

```bash
rg -n "report:summary|playwright summary|playwright-report.json|playwright-junit.xml" tests/playwright/package.json tests/playwright/README.md tests/playwright
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
