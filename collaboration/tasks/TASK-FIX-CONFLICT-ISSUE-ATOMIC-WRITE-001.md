# 任务: 冲突记录原子写与唯一 ID 修复

**任务ID**: TASK-FIX-CONFLICT-ISSUE-ATOMIC-WRITE-001
**分配给**: codex
**优先级**: P1
**创建时间**: 2026-02-28T15:24:47+08:00
**截止时间**: 2026-03-02T18:00:00+08:00

## 任务描述
修复冲突记录写入过程的并发安全问题：`conflict_id` 改为 UUID，`issues` 文件写入改为加锁 + 原子写，避免高并发下冲突记录覆盖或丢失。

## 输入
- 文件:
  - ai_collab/state_manager.py
  - src/state_manager.py
  - tests/unit/test_state_manager.py
- 上下文: 现有冲突记录使用秒级时间戳 ID 且无锁写文件，存在并发冲突风险

## 输出要求
- 输出: 并发安全补丁 + 单测补充
- 格式: 代码变更 + 验证结果 + 风险说明
- 结果文件: collaboration/results/RESULT_TASK-FIX-CONFLICT-ISSUE-ATOMIC-WRITE-001.md

## 验证标准
- [x] `conflict_id` 唯一性改为 UUID 机制
- [x] 冲突写入流程使用锁与原子写
- [x] 并发场景下无 JSON 损坏与记录丢失
- [x] `tests/unit/test_state_manager.py` 通过

## 状态
- [ ] 待开始 (pending)
- [ ] 进行中 (in_progress)
- [x] 已完成 (completed)
- [ ] 已阻塞 (blocked)

## 备注
- 该工单属于数据一致性修复，建议优先执行。
