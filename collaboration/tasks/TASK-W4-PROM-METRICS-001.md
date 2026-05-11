# 任务: Prometheus 指标导出

**任务ID**: TASK-W4-PROM-METRICS-001
**分配给**: claude_code
**优先级**: P0
**创建时间**: 2026-02-28T14:52:12+08:00
**截止时间**: 2026-03-27T18:00:00+08:00

## 任务描述
在 FastAPI 暴露 /metrics，输出请求、延迟、错误率等关键指标。

## 输入
- 文件:
  - local-backend/app/main.py
  - local-backend/app/core/monitoring.py
  - local-backend/requirements.txt
  - docs/DEPLOYMENT_AND_DEVELOPMENT_PLAN.md
- 上下文: 按 4 周开发计划推进，避免跨周范围扩散
- 依赖: 无硬依赖，支持并行推进

## 输出要求
- 输出: /metrics 可观测端点
- 格式: 提交代码 + 测试结果 + 变更说明
- 结果文件: collaboration/results/RESULT_TASK-W4-PROM-METRICS-001.md

## 验证标准
- [x] Prometheus 可抓取到关键业务指标
- [x] 指标命名与标签规范化
- [x] 不影响现有 API 延迟表现

## 状态
- [ ] 待开始 (pending)
- [ ] 进行中 (in_progress)
- [x] 已完成 (completed)
- [ ] 已阻塞 (blocked)

## 备注
- 工单已自动发布，可立即领取执行。
- 2026-02-28: 已完成 `/metrics` 端点、中间件采样、路径标签归一化和集成测试覆盖。
