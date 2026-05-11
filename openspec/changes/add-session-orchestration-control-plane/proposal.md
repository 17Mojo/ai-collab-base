## Why

当前基座已经具备较强的任务级治理能力：`dispatch / trigger / ack / receipt / result consistency` 都能形成可审计闭环。但外部会话层仍存在一个关键缺口：

- Codex 能生成给 Claude Code / CodeArts 的 payload，却不能持续观察这些外部会话是否已经偏离预期
- 当外部会话出现无 ACK、模板 ACK、过期 payload、结果与状态不一致等异常时，系统只能把“补发/纠偏消息”交给用户手工转运
- `session_inject`、`pre_compact` 与各类监控模块更多是在共享工作区状态，而不是提供真正的会话控制面

这使用户仍然承担“胶水人”职责。需要把“会话监控 + 正向干预纠偏 + 人环最小化边界”提升为正式能力，而不是继续停留在零散脚本和口头流程层面。

## What Changes

- 新增 `session-orchestration` 能力规格，定义 Codex 对 Claude Code / CodeArts / Codex 会话的统一会话控制面
- 为会话层引入正式的注册与状态模型，包括：
  - session identity / assignee / transport mode
  - last seen / last handoff / health status
  - intervention queue / delivery status
- 定义会话健康监控要求，统一聚合现有 trigger freshness、ACK watchdog、missing-ack、result consistency 等信号
- 定义正向干预能力：
  - 发现异常后生成标准化 intervention payload
  - 若存在可用传输桥，则允许自动投递
  - 若不存在可用传输桥，则生成待发送工件并明确标记 `pending_operator_delivery`
- 明确自动化边界：系统不得虚构“已同步/已控制外部窗口”；只有在 transport hook 存在且已配置时，才允许宣称自动投递成功
- 为后续 CLI、监控摘要、runbook 与 dashboard 接入预留统一审计口径

## Impact

- Affected specs:
  - `session-orchestration` (new)
- Affected code:
  - `ai_collab/codex_integration.py`
  - `ai_collab/hooks/session_inject.py`
  - `ai_collab/dispatch_trigger.py`
  - `ai_collab/missing_ack_monitor.py`
  - `ai_collab/cli.py`
  - `collaboration/PROTOCOL.md`
  - `collaboration/monitoring/*SESSION*`
  - potential new modules such as `ai_collab/session_orchestrator.py` and transport adapters
- Risks / constraints:
  - V1 不承诺原生控制任意外部 GUI 聊天窗口；无 transport hook 时必须显式退化为“生成干预工件 + 请求最小人工协助”
  - 不改变现有正式 ACK / receipt / state drift 判定口径，只是在其上方新增会话层观察与纠偏
  - 需要避免把 Codex 内部 `spawn_agent` 与跨外部会话控制面混为一谈
