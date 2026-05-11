# 任务: CLI 补齐 Codex 角色支持

**任务ID**: TASK-FIX-CLI-CODEX-SUPPORT-001
**分配给**: codex
**优先级**: P1
**创建时间**: 2026-02-28T15:24:47+08:00
**截止时间**: 2026-03-02T18:00:00+08:00

## 任务描述
修复 CLI 的 AI 参数枚举，允许 `codex` 作为合法角色参与 `activate/check/tasks` 流程，并保持现有 `claude/claude_code/copilot` 兼容。

## 输入
- 文件:
  - ai_collab/cli.py
  - src/cli.py
- 上下文: 当前协作模式中 Codex 已参与实际执行，但 CLI 参数校验仍拒绝 `codex`

## 输出要求
- 输出: CLI 参数兼容补丁
- 格式: 代码变更 + 验证结果 + 风险说明
- 结果文件: collaboration/results/RESULT_TASK-FIX-CLI-CODEX-SUPPORT-001.md

## 验证标准
- [x] `--ai codex` 可用于 `activate`
- [x] `--ai codex` 可用于 `check`
- [x] `--ai codex` 可用于 `tasks register`
- [x] 不影响现有 `claude/claude_code/copilot` 参数

## 状态
- [ ] 待开始 (pending)
- [ ] 进行中 (in_progress)
- [x] 已完成 (completed)
- [ ] 已阻塞 (blocked)

## 备注
- 该工单属于协作基座可用性修复，优先级高于新特性开发。
