## 1. Spec & Governance Alignment

- [x] 1.1 为 `task-governance` 增加 `claude_code` 显式 ACK 闭环门禁 requirement / scenario
- [x] 1.2 对齐治理文档与 OpenSpec 术语，统一 `cli-ack` / `chat-ack` / fallback bridge 口径

## 2. Monitoring & Remediation

- [x] 2.1 增加对历史 `claude_code` fallback bridge 记录的审计口径，明确“残留/跳过/不可闭环”的展示方式
- [x] 2.2 设计并实现一个最小 remediation 路径，用于审查或清理历史非显式 ACK bridge 记录
- [x] 2.3 在监控摘要中单独显示 `explicit ACK required` 类跳过项，避免与通用 missing-ack 混淆
- [x] 2.4 在后续收到真实 `cli-ack/chat-ack` 时，自动解除 legacy remediation 残留标记并恢复显式证据

## 3. Verification

- [x] 3.1 补充/更新单元测试，覆盖 OpenSpec 中定义的显式 ACK 闭环场景
- [x] 3.2 执行 targeted CLI smoke，确认 receipt / state-drift / monitoring 产物与新规范一致
- [x] 3.3 运行 `openspec validate add-explicit-ack-closeout-gate --strict`
- [x] 3.4 覆盖“历史残留 -> 显式 ACK -> 残留清除”的回归测试
