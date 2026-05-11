# 任务: 告警规则与SLO基线

**任务ID**: TASK-W4-ALERT-RULES-002
**分配给**: codex
**优先级**: P1
**创建时间**: 2026-02-28T14:52:12+08:00
**截止时间**: 2026-03-27T18:00:00+08:00

## 任务描述
定义错误率、P95 延迟、失败任务比例等告警规则。

## 输入
- 文件:
  - local-backend/
  - docs/DEPLOYMENT_AND_DEVELOPMENT_PLAN.md
  - docs/RELEASE_CHECKLIST.md
- 上下文: 按 4 周开发计划推进，避免跨周范围扩散
- 依赖: 无硬依赖，支持并行推进

## 输出要求
- 输出: 告警规则配置与运行手册
- 格式: 提交代码 + 测试结果 + 变更说明
- 结果文件: collaboration/results/RESULT_TASK-W4-ALERT-RULES-002.md

## 验证标准
- [x] 至少覆盖 3 类关键告警
- [x] 告警阈值有依据且可调整
- [x] 提供告警演练步骤

## 状态
- [ ] 待开始 (pending)
- [ ] 进行中 (in_progress)
- [x] 已完成 (completed)
- [ ] 已阻塞 (blocked)

## 备注
- 工单已自动发布，可立即领取执行。
- 2026-02-28: 已完成规则落地、运行手册、最小测试与结果回填。
