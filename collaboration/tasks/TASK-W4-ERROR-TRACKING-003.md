# 任务: 错误追踪与故障归档

**任务ID**: TASK-W4-ERROR-TRACKING-003
**分配给**: copilot
**优先级**: P1
**创建时间**: 2026-02-28T14:52:12+08:00
**截止时间**: 2026-03-27T18:00:00+08:00

## 任务描述
统一错误结构化日志，接入错误聚合与故障归档流程。

## 输入
- 文件:
  - local-backend/app/core/monitoring.py
  - local-backend/app/main.py
  - docs/CODE_AUDIT_IMPROVEMENTS_REPORT.md
  - docs/RELEASE_CHECKLIST.md
- 上下文: 按 4 周开发计划推进，避免跨周范围扩散
- 依赖: 无硬依赖，支持并行推进

## 输出要求
- 输出: 错误追踪标准与实现补丁
- 格式: 提交代码 + 测试结果 + 变更说明
- 结果文件: collaboration/results/RESULT_TASK-W4-ERROR-TRACKING-003.md

## 验证标准
- [ ] 错误日志含 trace_id 和上下文
- [ ] 支持按错误类型快速聚合
- [ ] 故障回溯流程文档化

## 状态
- [ ] 待开始 (pending)
- [ ] 进行中 (in_progress)
- [ ] 已完成 (completed)
- [x] 已阻塞 (blocked)

## 备注
- 工单已自动发布，可立即领取执行。
- 2026-02-28: Copilot 暂时不可用，已转派到 `TASK-W4-ERROR-TRACKING-003-R1` (claude_code)。
