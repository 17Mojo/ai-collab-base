## Context

当前系统已经具备“共享状态 + 任务级闭环”的骨架，但仍缺少真正的会话控制面。

已有基础设施：

- `ai_collab/dispatch_trigger.py` 可以为 Claude / CodeArts / Codex 生成会话 payload，并提供 freshness repair 命令
- `ai_collab/missing_ack_monitor.py`、ACK watchdog、receipt bridge、result consistency audit 能发现部分异常
- `ai_collab/hooks/session_inject.py` 与 `ai_collab/hooks/pre_compact.py` 能在会话开始/压缩前注入或快照共享工作区信息

当前缺口：

- 外部会话本身没有正式 session registry，Codex 无法稳定知道“哪个外部会话是当前有效会话”
- 异常信号分散在多个模块里，没有统一的 session health 判定
- 系统能生成“该发给 Claude / CodeArts 的纠偏内容”，但没有 intervention queue 与 delivery status
- 用户仍然承担消息搬运角色

换句话说，当前更像“workspace-mediated continuity”，还不是“session-layer orchestration”。

## Goals / Non-Goals

- Goals:
  - 为跨会话协作补齐可审计的 session control plane
  - 让 Codex 能识别外部会话失联、漂移、过期和协议异常
  - 让纠偏消息成为正式工件，可被排队、投递、跟踪和关闭
  - 在有受控 transport hook 时减少人工搬运，在无 hook 时也要把人工动作缩到最小
- Non-Goals:
  - 不承诺直接控制任意第三方 GUI 窗口
  - 不改变正式工单、owner lock、显式 ACK、receipt closeout 的既有治理规则
  - 不把 Codex 内部 `spawn_agent` 升级成外部正式会话角色

## Decisions

### 1. Session state 与 task state 分层

新增 session registry，而不是把会话信息继续塞进任务状态。

最小字段建议：

- `session_id`
- `assignee`
- `transport_mode`
- `session_status`
- `last_seen_at`
- `last_handoff_artifact`
- `last_ack_at`
- `health_status`
- `open_intervention_count`

理由：任务状态描述“要做什么”，会话状态描述“谁在什么通道里接收并执行这些内容”，两者关注点不同。

### 1.5 外部 transport adapter 分产品选型，而不是一刀切

V1 不采用“所有外部 Agent 都走同一种消息投递方式”的设计，而是按产品提供的官方能力分层接入：

- `codex`: 优先使用 Codex App Server / Codex SDK 暴露的线程与事件能力；`codex mcp-server` 仅作为较窄的可调用工具面
- `claude_code`: 优先使用官方 `Hooks + Channels`
- `codearts_agent`: 优先使用 `Rule + MCP + pull-based sync`

理由：三个产品的原生能力边界并不对称，强行统一 transport 只会把系统绑到最脆弱的一层。

### 2. 健康判定复用现有监控，不重造第二套信号

V1 的 session health 聚合器直接消费既有控制面信号，而不是再发明新检查器。

优先纳入：

- payload freshness 失败
- `ACK_WATCHDOG` 超时或重复重发
- missing explicit ACK / stale fallback bridge
- receipt blocked / result consistency mismatch
- session registration 缺失或过期

理由：当前系统已经能检测很多问题，缺的是统一归因和干预动作。

### 3. Intervention 是一等工件

每次会话纠偏都要生成正式 intervention record，而不是只在聊天里临时写一句话。

建议字段：

- `intervention_id`
- `session_id`
- `assignee`
- `reason_code`
- `severity`
- `message_artifact`
- `delivery_mode`
- `delivery_status`
- `created_at`
- `resolved_at`

理由：只有这样才能知道系统“发现了什么、想发什么、发没发出去、后来是否解除”。

### 3.5 Intervention 消息采用“双层协议”

V1 将消息分成两层：

- 内层：控制面内部结构化 intervention record
- 外层：对外发送时的传输封装

推荐策略：

- 人工转发/人工审阅场景：使用 ACP 风格的人类可读消息壳
- 自动桥接场景：使用 adapter 原生协议字段，不强制把 ACP 文本塞入所有 transport

理由：ACP 适合做人类可读、可审阅的消息格式，但其设计前提本身就是“人类负责在 Agent 之间传递消息”；若把它直接当 transport，会把人环固定下来。

### 4. 传输能力显式分层

V1 按 transport capability 分两层：

- `manual`: 只能生成工件和待办，不宣称自动投递
- `bridge`: 有明确 adapter / hook 时，允许自动写入外部会话桥接通道或控制面 inbox

`bridge` 模式必须是显式配置和可审计的；默认仍为 `manual`。

理由：这样既能最大化自动化，又不会虚构“我已经控制了那个外部窗口”。

### 4.5 Codex 侧优先使用 App Server，不把 MCP 当作完整会话协议

Codex 自身的优先集成面应是 App Server，而不是 `mcp-server`。

原因：

- App Server 暴露的是完整 Codex harness，包括线程生命周期、持久化、事件流和审批往返
- `mcp-server` 更适合“把 Codex 当一个可调用工具”，不适合承载完整会话状态与富事件语义

因此，若后续要让其它控制面或桌面客户端更深地接入 Codex，会优先围绕 App Server 的线程/事件模型设计，而不是只做 MCP 封装。

### 4.6 Claude 侧走 push，CodeArts 侧先走 pull

基于当前官方能力证据：

- Claude Channels 支持通过 stdio 注册通知监听器，并把 webhook / alert / curl POST 等事件推入 Claude 会话，同时支持 reply tool 与权限中继
- CodeArts 官方文档明确支持 Rule、Skill、MCP 与代码库索引，但当前未看到等价于 Claude Channels 的“外部事件主动推入活跃会话”的官方通道

因此：

- `claude_code` 的 intervention adapter 采用 push-first 设计
- `codearts_agent` 的 intervention adapter 采用 pull-first 设计：会话启动、关键动作前、ACK 前主动拉取待处理 intervention

这能在尊重各产品边界的前提下，先拿到最高价值的自动化收益。

### 5. 用户从“胶水人”降为“异常兜底”

系统默认路径应是：

1. 自动发现异常
2. 自动生成 intervention
3. 有桥则自动投递
4. 无桥则给出精确的单条待转发消息和目标会话

用户只在 transport 不可达时承担最小转发动作，而不是自己判断该发什么、发给谁、何时补发。

### 5.5 参考 A2A / Agents handoff，但不直接照搬

外部参考表明两类模式值得吸收：

- A2A：agent discovery、同步/异步/流式通知、结构化任务与事件交换
- OpenAI Agents handoff：把“交接”建模成结构化工具调用，并在 handoff 时附带小型元数据与输入过滤

V1 吸收这些思想，但不会直接把内部控制面实现成完整 A2A 节点网络。更务实的做法是：

- 在 registry 中吸收 A2A 的 capability/discovery 思路
- 在 intervention record 中吸收 handoff metadata 思路，例如 `reason_code`、`priority`、`summary`
- 继续保留当前项目的任务治理与显式 ACK 门禁

理由：现阶段目标是降低人环与提升纠偏能力，不是构建通用 agent internet。

## Risks / Trade-offs

- 风险：会话健康误判过多，造成噪音干预
  - 缓解：采用 reason code、severity 分级和去重窗口
- 风险：`bridge` 模式若语义不清，容易越过真实控制边界
  - 缓解：仅允许已配置 transport adapter，所有自动投递必须落审计
- 风险：把过多职责堆进单一 CLI
  - 缓解：保持 registry / health / intervention / delivery 分层，CLI 只是控制面入口
- 风险：对外部协议理解不完整导致错误承诺
  - 缓解：所有 adapter 均以官方文档和本机真实配置为边界；未确认的能力不进入 V1 承诺

## Migration Plan

1. 先定义 OpenSpec 能力边界和状态模型
2. 实现 session registry 与 health aggregation，但默认 `delivery_mode=manual`
3. 将现有“补发/纠偏消息”统一落到 intervention artifacts
4. 在具备可靠 transport hook 的目标上增量开启 `bridge`
5. 再根据收益决定是否扩展更强的自动恢复与策略编排

## Product-Specific Adapter Strategy

### Codex

- 首选接口：App Server / SDK / thread primitives
- 次选接口：`codex exec` 用于一次性自动化，`codex mcp-server` 用于被其它 MCP client 调用
- 不建议：仅用 `exec` 或纯 shell 包装去模拟长生命周期会话同步

### Claude Code

- 首选接口：Channels
- 辅助接口：Hooks（SessionStart / PreToolUse / Stop）
- 预期收益：可直接把 intervention 从控制面推入 Claude 会话，减少用户中转

### CodeArts Agent

- 首选接口：Project Rule + MCP server + code index
- 辅助接口：Skill / context loading
- 预期收益：即使没有 push channel，也能通过 pull-based sync 在关键阶段自动收敛待处理 intervention

## Evidence Baseline

当前设计建立在以下证据之上：

- Claude Code 文档明确说明 `SessionStart` hooks 能接收 `session_id` 并向 Claude 上下文注入 `additionalContext`
- Claude Channels 文档明确说明可通过 `notifications/claude/channel` 把外部事件推入会话，并支持 reply tool
- OpenAI Codex App Server 文章明确说明 App Server 暴露完整 Codex harness 的线程、事件流与双向 JSON-RPC
- OpenAI Agents handoff 文档明确说明 handoff 可携带结构化 metadata，并在 handoff 时触发回调
- CodeArts 文档明确说明 Rule 在对话开始时加载、MCP 提供外部工具能力、代码库索引每 5 分钟增量更新

## Open Questions

- session registry 的 `session_id` 是否完全由 operator 提供，还是允许通过特定 adapter 自动发现
- intervention queue 应独立持久化，还是先落到现有 monitoring/report 体系再逐步抽象
- `bridge` 模式首批支持哪个 transport：文件型 inbox、IDE 扩展桥，还是受控桌面自动化
