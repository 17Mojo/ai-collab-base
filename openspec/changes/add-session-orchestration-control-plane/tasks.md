## 1. Control Plane
- [x] 1.1 增加会话注册与状态模型，至少覆盖 `session_id`、`assignee`、`transport_mode`、`last_seen_at`、`last_handoff_artifact`、`health_status`
- [x] 1.2 建立会话健康聚合器，统一消费 trigger freshness、ACK watchdog、missing-ack、receipt/result consistency 等异常信号
- [x] 1.3 建立 intervention 队列与审计模型，记录 `reason_code`、`message_artifact`、`delivery_mode`、`delivery_status`
- [x] 1.4 支持 V1 传输模式分层：`manual`（仅生成待发送工件）与 `bridge`（存在受控传输 hook 时自动投递）
- [x] 1.5 定义统一 adapter contract，至少覆盖 `register_session`、`push_intervention`、`pull_interventions`、`ack_delivery`、`heartbeat`

## 2. Governance Integration
- [x] 2.1 为 Claude Code / CodeArts / Codex 三类会话补齐统一 session registration / refresh / inspect CLI 入口或等价控制面入口
- [x] 2.2 将当前手工补发口径沉淀为标准 intervention 模板，覆盖过期 payload、缺失 ACK、模板 ACK、结果/状态分裂等场景
- [x] 2.3 输出 `latest/history` 审计产物与人类可读摘要，支持 operator 查看待处理 intervention 与已解决事件
- [x] 2.4 更新协议与运行手册，明确“有桥自动投递、无桥最小人工转运”的边界
- [x] 2.5 实现 `Claude channel adapter`，把 session incident 转成可审计的 Claude push event
- [x] 2.6 实现 `CodeArts MCP pull adapter`，通过项目 Rule + MCP 工具拉取并确认 intervention
- [x] 2.7 实现 `Codex control-plane adapter`，以 `app-server` / `mcp-server` / hooks 暴露本地编排入口

## 3. Quality Gates
- [x] 3.1 补充单元测试，覆盖会话注册、健康判定、intervention 状态迁移、delivery fallback
- [x] 3.2 补充 CLI/集成测试，验证 `manual` 与 `bridge` 两种传输模式下的输出与审计行为
- [x] 3.3 增加 adapter 级验证，至少覆盖 `Claude push` 成功路径与 `CodeArts pull` 收敛路径
- [x] 3.4 验证现有任务级强门禁未被削弱：`python3 -m ai_collab.cli tasks validate-contract --scope all --strict`
- [x] 3.5 `openspec validate add-session-orchestration-control-plane --strict`
