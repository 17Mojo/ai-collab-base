# Agent Dispatch Orders - Week 8

**生成时间**: 2026-04-26T09:00:00
**派发者**: Claude Code (主执行者)
**待派发任务数**: `2`

---

## 发送给 `CodeArts Agent` (`codearts_agent`)

### TASK-W8-D4-PACK-SAMPLE-VALIDATION-004

**优先级**: P1
**预估工时**: 2.0h
**依赖**: TASK-W7-D1-BRANCH-REGEX-IMPL-001 (已完成)

```text
【执行指令 | TASK-W8-D4-PACK-SAMPLE-VALIDATION-004】

1) 切换状态为 implementing
更新 collaboration/tasks/TASK-W8-D4-PACK-SAMPLE-VALIDATION-004.md
status: implementing

2) 执行任务内容
- Task 1: 创建 Pack 验证测试 (30min)
  文件: tests/integration/test_pack_validation.py
  测试: 加载成功 + Schema 兼容 + 向后兼容 + 分支结构

- Task 2: 逐个 Pack 验证 (45min)
  验证 17 个 Pack 示例兼容性

- Task 3: 修复不兼容 Pack (30min)
  添加缺失字段 / 调整顺序

- Task 4: 生成验证报告 (15min)
  文件: collaboration/results/PACK_VALIDATION_REPORT_2026-04-26.md

3) 执行验收命令
pytest tests/integration/test_pack_validation.py -v

4) 创建结果文件
collaboration/results/RESULT_TASK-W8-D4-PACK-SAMPLE-VALIDATION-004.md

5) 更新任务状态为 testing
status: testing

6) 生成 ACK
回复本文件确认任务已接收
```

---

### TASK-W8-D6-DOCUMENTATION-006 (依赖 D2 完成)

**优先级**: P2
**预估工时**: 1.5h
**状态**: 等待 TASK-W8-D2-CAPABILITY-UPDATE-002 完成

---

## Claude Code 直接执行的任务

| 任务 | 状态 | 说明 |
|------|------|------|
| TASK-W8-D1-BRANCH-LOGIC-TEST-001 | 待执行 | 分支逻辑测试 |
| TASK-W8-D2-CAPABILITY-UPDATE-002 | 待执行 | 能力清单更新 |
| TASK-W8-D3-KNOWLEDGE-SOURCE-EXPANSION-003 | 待执行 | 知识源扩展 |
| TASK-W8-D5-CHROME-EXTENSION-TEST-005 | 待执行 | Extension 测试 |

---

## 执行约束

1. **禁止绕过验收命令**: 必须执行 pytest 验证
2. **禁止跳过结果文件**: 必须创建 RESULT_*.md
3. **禁止直接修改 main 分支**: 使用 feature 分支开发
4. **遇阻塞立即回报**: 在任务文件中记录 blocker

---

## ACK 协议

CodeArts Agent 接收任务后，请回复：

```
【ACK | TASK-W8-D4-PACK-SAMPLE-VALIDATION-004】
status: received
timestamp: {ISO时间}
note: {简短备注}
```

---

**派发完成**