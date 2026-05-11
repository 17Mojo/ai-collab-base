## 1. Implementation
- [x] 1.1 新增终态任务 `state/result` 一致性审计模块，覆盖 `completed/failed/blocked/cancelled`
- [x] 1.2 增加 CLI 入口，输出 JSON 报告路径与摘要路径，并在存在 mismatch 时返回非零状态码
- [x] 1.3 定义结果报告状态头解析规则，兼容中英文与 emoji/markdown 头部格式
- [x] 1.4 为合法 takeover 场景补充说明，避免把 `ai_type != assignee` 机械判为异常
- [x] 1.5 补充单元测试，覆盖一致/不一致/缺失状态头/合法 takeover 样例
- [x] 1.6 将终态结果一致性审计接入 `tasks validate-contract --strict`，作为 closeout/operator review 的正式强门禁
