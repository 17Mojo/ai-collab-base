---
name: RESULT 结果文件的契约校验与终态一致性要求
description: 结果文件除 PROTOCOL §7.4 四段标题外还需可解析的状态行与测试结论小节，否则 tasks validate-contract 与一致性审计判不合格；任务终态须收口为 completed
type: feedback
from: Agent
---

派单任务的结果文件（`collaboration/results/RESULT-*.md`）要通过两道机器校验，二者都会因"形式齐备但内容不合规"而失败：

1. **契约校验**（`python3 -m ai_collab.cli tasks validate-contract`）：正文需含 PROTOCOL §7.4 四段标题 `## 执行命令` / `## 验证结果` / `## 风险` / `## 回滚`；仅标题齐备**仍可能不合格**——需在「验证结果」段内补出**每条验收命令的真实输出与测试结论小节**（校验按章节结构统计 checked 项）。
2. **一致性审计**：会**解析结果文件中的状态行**，并据此核对任务终态；工单状态必须收口到 `completed` 且结果文件在位，否则审计不通过。

**Why:** 2026-10-23 执行 `TASK-P1-CLI-EXITCODE-001` 时，结果文件起初只写了四段标题，契约校验的 checked 统计不达标，补齐「测试结论」小节并复跑 `validate-contract` + 一致性审计后才转绿。说明校验器看的是"段落 + 结论"的结构，不是"有没有这四个字"。

**How to apply**:
- 写结果文件时按「四段标题 → 每条验收命令的真实输出 → 测试结论小节 → 状态行」的顺序一次写全，写完立刻跑 `tasks validate-contract` 与一致性审计复验，不要等 ACK 前才发现缺项。
- 状态行格式要与既有 RESULT 文件保持一致（可先读一份同日期的既有结果文件对齐）。
- 收尾顺序：任务状态 `implementing` → 实现 → 跑验收命令 → 写结果文件 → 复验契约与审计 → 状态收口 `completed` → 用 `python3 -m ai_collab.cli ack ...` 生成一行 ACK 原样回复。
- 与 `feedback_dispatch_payload_freshness.md`、`feedback_ack_cli_generated.md` 并行遵守。
