# 4周开发计划执行看板（2026-02-28）

> 2026-02-28 更新：`copilot` 暂时不可用，相关工单已取消并生成替代工单（`-R1`）。

| Task ID | 周次 | 优先级 | 负责人 | 截止时间 | 目标 |
|---|---|---|---|---|---|
| TASK-W1-CHROME-INJECTION-001 | W1 | P1 | claude_code | 2026-03-06 | Chrome 注入稳健性加固 |
| TASK-W1-CHROME-MESSAGE-002 | W1 | P1 | codex | 2026-03-06 | 扩展消息通道可靠性提升 |
| TASK-W1-CHROME-STORAGE-003 | W1 | P1 | copilot | 2026-03-06 | 本地存储版本迁移与清理 |
| TASK-W2-VSCODE-NATIVE-001 | W2 | P0 | claude_code | 2026-03-13 | VSCode Native Messaging 通道落地 |
| TASK-W2-VSCODE-COMMANDS-002 | W2 | P1 | codex | 2026-03-13 | VSCode 命令面板扩展化 |
| TASK-W2-VSCODE-STATUSBAR-003 | W2 | P2 | copilot | 2026-03-13 | VSCode 状态栏指示器 |
| TASK-W3-REDIS-CACHE-001 | W3 | P0 | claude_code | 2026-03-20 | Redis 缓存可开关接入 |
| TASK-W3-DB-OPTIMIZE-002 | W3 | P1 | codex | 2026-03-20 | 数据库查询与索引优化 |
| TASK-W3-BULK-API-003 | W3 | P1 | copilot | 2026-03-20 | 批量操作 API |
| TASK-W4-PROM-METRICS-001 | W4 | P0 | claude_code | 2026-03-27 | Prometheus 指标导出 |
| TASK-W4-ALERT-RULES-002 | W4 | P1 | codex | 2026-03-27 | 告警规则与SLO基线 |
| TASK-W4-ERROR-TRACKING-003 | W4 | P1 | copilot | 2026-03-27 | 错误追踪与故障归档 |
| TASK-W1-CHROME-STORAGE-003-R1 | W1 | P1 | codex | 2026-03-06 | 本地存储版本迁移与清理（替代） |
| TASK-W2-VSCODE-STATUSBAR-003-R1 | W2 | P1 | claude_code | 2026-03-13 | VSCode 状态栏指示器（替代） |
| TASK-W3-BULK-API-003-R1 | W3 | P1 | codex | 2026-03-20 | 批量操作 API（替代） |
| TASK-W4-ERROR-TRACKING-003-R1 | W4 | P1 | claude_code | 2026-03-27 | 错误追踪与故障归档（替代） |

## 执行指令

1. 先领取 P0/P1 工单，确保本周阻塞项优先清理。
2. 每个工单结束必须提交 `RESULT_<TASK_ID>.md`，包含测试结果与风险。
3. 禁止跨周大范围改动，超出范围需新建工单。

## 本周可执行批次（延期单重排，2026-02-28）

> 目标：将 `deferred` 的 9 个工单恢复为可执行队列；按依赖关系拆成 4 个批次，批次内并行、批次间串行。

### Batch 1（D1，基础通道与观测入口）

> 2026-02-28 更新：Batch 1 已完成（`TASK-W2-VSCODE-NATIVE-001`、`TASK-W4-PROM-METRICS-001`）。

| 顺序 | Task ID | 优先级 | 负责人 | 依赖 | 说明 |
|---|---|---|---|---|---|
| 1 | TASK-W2-VSCODE-NATIVE-001 | P0 | claude_code | 无 | 先落 VSCode 通道骨架（当前 `products/vscode-extension/` 缺失） |
| 2 | TASK-W4-PROM-METRICS-001 | P0 | claude_code | 无 | 先提供 `/metrics`，为后续告警规则提供数据源 |

### Batch 2（D2-D3，数据层性能能力）

> 2026-02-28 更新：Batch 2 已解锁，3 个工单状态已切换为 `pending`。
> 2026-02-28 更新：`TASK-W3-REDIS-CACHE-001` 已完成，Batch 2 剩余 2 单（DB 优化、批量 API）。
> 2026-02-28 更新：`TASK-W3-DB-OPTIMIZE-002` 已完成，Batch 2 剩余 1 单（批量 API）。
> 2026-02-28 更新：`TASK-W3-BULK-API-003-R1` 已完成，Batch 2 全部完成。

| 顺序 | Task ID | 优先级 | 负责人 | 依赖 | 说明 |
|---|---|---|---|---|---|
| 3 | TASK-W3-REDIS-CACHE-001 | P0 | claude_code | 无 | 缓存开关+降级能力 |
| 4 | TASK-W3-DB-OPTIMIZE-002 | P1 | codex | 无 | 先做索引/查询路径优化基线 |
| 5 | TASK-W3-BULK-API-003-R1 | P1 | codex | 4 | 批量 API 依赖优化后查询路径，避免返工 |

### Batch 3（D3-D4，VSCode 体验层）

> 2026-02-28 更新：Batch 2 已全部完成，Batch 3 两单状态已切换为 `pending`。

| 顺序 | Task ID | 优先级 | 负责人 | 依赖 | 说明 |
|---|---|---|---|---|---|
| 6 | TASK-W2-VSCODE-COMMANDS-002 | P1 | codex | 1 | 在通道骨架上补命令面板能力 |
| 7 | TASK-W2-VSCODE-STATUSBAR-003-R1 | P1 | claude_code | 1,6 | 状态栏消费任务状态与命令入口 |

### Batch 4（D4-D5，稳定性与告警闭环）

| 顺序 | Task ID | 优先级 | 负责人 | 依赖 | 说明 |
|---|---|---|---|---|---|
| 8 | TASK-W4-ERROR-TRACKING-003-R1 | P1 | claude_code | 2 | 先统一错误结构化日志 |
| 9 | TASK-W4-ALERT-RULES-002 | P1 | codex | 2,8 | 基于指标+错误字段产出可执行告警规则 |

### 执行约束

1. 每完成一个批次，先补 `RESULT_*` 再启动下一批次。
2. VSCode 相关批次必须先补 `products/vscode-extension/` 最小骨架（由 Batch 1 产出）。
3. 监控相关批次统一复用 `local-backend/app/core/monitoring.py`，避免重复实现。
