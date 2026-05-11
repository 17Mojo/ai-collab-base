# Findings — 调整多Agent治理与职责分配（Codex接管）

## Confirmed
- `.vscode/ai-collab.json` 当前启用 AI 为 `claude_code` 与 `codex`，`copilot` 在 `disabledAgents` 中。
- `logs/collaboration_state.json` 当前任务总量 60，状态分布为 52 completed / 8 cancelled。
- 用户已明确授予 Codex 开发管理权，并声明 CodeArts 暂停“技术合伙人”身份。
- 当前协作协议文档仍含 Claude↔Copilot 主协作叙事，需要治理口径收敛。

## Open Questions
- 无（用户已确认：CodeArts 替代 Copilot 执行位，组织框架按 Codex 方案推进）

## Decisions
- 将“治理调整”作为独立 OpenSpec change 管理，避免隐式变更。
- 生效口径：Codex 全局统筹、Claude 主执行、CodeArts 替代 Copilot 作为执行辅助。
- OpenSpec 负责 Prompt Pack 生命周期变更管理，工单负责执行派发。

## Risks & Mitigations
- 风险：历史文档冲突导致执行混乱。  
  缓解：引入“单一事实源（SSOT）”并标记弃用文档。
- 风险：角色切换期间任务归属错误。  
  缓解：在任务模板中新增“owner + approver + effective_date”字段。
