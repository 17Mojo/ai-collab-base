## Why

`spawn_agent` 目前已经有文档级治理规则，但运行时 SSOT `.vscode/ai-collab.json` 还无法表达和校验这些约束，导致“是否允许、何时阻断、如何审计”仍主要依赖人工判断。

为了让这套规则真正可检查、可留痕、可复用，需要把 `spawn_agent` 治理补成配置驱动的本地 guard，而不是继续停留在文档层。

## What Changes

- 为 `.vscode/ai-collab.json` 增加 `spawnAgentGuard` 配置块，定义启用开关、允许 actor、单父任务约束、写入委派的写集要求、只读委派开关、保护路径和报告路径
- 新增本地 `spawn-agent-guard` 校验链路，在 Codex 计划使用 `spawn_agent` 时对 actor / parent task / read-only vs write delegation / 保护路径 / 活跃任务冲突做阻断式检查
- 为每次 guard 运行写入 latest + history 审计产物，和现有 `workspaceGuard` 风格保持一致
- 暴露可复用的 guard helper，便于后续 CLI、hook 或其他自动化链路复用同一校验结果
- 将同一 guard 接入 Claude Code `PreToolUse` `Agent` hook，在实际内部委派前自动触发并阻断不合规 delegation

## Impact

- Affected specs: `task-governance`
- Affected code:
  - `ai_collab/cli.py`
  - `ai_collab/codex_integration.py`
  - `ai_collab/hooks/spawn_agent_preflight.py`
  - `ai_collab/state_manager.py`
  - `ai_collab/workspace_guard.py` 风格对齐参考
  - `tests/unit/test_cli.py`
  - `tests/unit/test_codex_integration.py`
  - 新增 `tests/unit/test_spawn_agent_guard.py`
  - 新增 `tests/unit/test_spawn_agent_preflight_hook.py`
