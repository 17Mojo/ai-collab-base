# 任务: 通知系统补齐 Codex 目标路由

**任务ID**: TASK-FIX-NOTIFICATION-CODEX-TARGET-001
**分配给**: codex
**优先级**: P1
**创建时间**: 2026-02-28T15:24:47+08:00
**截止时间**: 2026-03-02T18:00:00+08:00

## 任务描述
修复通知系统中广播/广播+@ 的目标集合未覆盖 Codex 的问题，保证 Codex 在统一协作消息通道中可接收消息并统计未读。

## 输入
- 文件:
  - src/ai_collab/notification.py
- 上下文: 当前广播目标列表硬编码为 `claude_code/copilot/user`，导致 Codex 收不到广播类通知

## 输出要求
- 输出: 通知目标集合修复补丁
- 格式: 代码变更 + 验证结果 + 风险说明
- 结果文件: collaboration/results/RESULT_TASK-FIX-NOTIFICATION-CODEX-TARGET-001.md

## 验证标准
- [x] `broadcast` 会为 Codex 写入通知
- [x] `broadcast+@` 的待处理列表包含 Codex
- [x] `get_unread_count(\"codex\")` 行为正确
- [x] `direct` 模式既有行为不回归

## 状态
- [ ] 待开始 (pending)
- [ ] 进行中 (in_progress)
- [x] 已完成 (completed)
- [ ] 已阻塞 (blocked)

## 备注
- 该工单直接影响广播协作链路可用性。
