## Context

当前 `spawn_agent` 治理已经在文档中明确为“Codex 单一父任务内的内部委派”，但实际运行时只有文档，没有本地可检查 guard。

仓库已经有两类可复用模式：

- `.vscode/ai-collab.json` 作为运行时 SSOT
- `workspaceGuard` 作为“配置驱动 + latest/history 审计 + CLI 命令”的本地门禁模式

此外，`StateManager` 已经具备基于任务 `files` 字段的活跃任务冲突检测能力，可作为 `spawn_agent` guard 的一部分基础设施。

## Goals / Non-Goals

- Goals:
  - 让 `spawn_agent` 约束可通过配置表达并由本地命令校验
  - 让 Codex 在委派前可以得到明确的 allow/block 结论和违规原因
  - 让每次 guard 检查留下 latest/history 审计记录
  - 复用现有冲突检测与 guard 报告模式，避免重复造轮子
  - 让相同校验可以在 `PreToolUse Agent` 阶段自动执行，而不是依赖人工先跑 CLI

- Non-Goals:
  - 不把内部子代理升级为正式外部工单角色
  - 不改变现有 Claude / CodeArts / ACK 正式派单协议

## Proposed Design

### 1. Config Shape

在 `.vscode/ai-collab.json` 顶层新增 `spawnAgentGuard`：

```json
{
  "spawnAgentGuard": {
    "enabled": true,
    "allowedLeadAgents": ["codex"],
    "requireParentTask": true,
    "requireWriteSet": true,
    "allowReadOnly": true,
    "protectedPaths": [
      "logs/collaboration_state.json",
      "logs/agent_dispatch_state.json",
      "logs/agent_receipt_state.json"
    ],
    "protectedPrefixes": [
      "collaboration/tasks/",
      "collaboration/monitoring/AGENT_TRIGGER_"
    ],
    "report": "logs/workspace_forensics/spawn_agent_guard_latest.json",
    "history": "logs/workspace_forensics/spawn_agent_guard_history.jsonl"
  }
}
```

默认值应偏保守，并与当前文档治理边界一致。

### 2. Validation Model

新增 `spawn_agent` guard helper，输入至少包括：

- `actor`
- `parent_task_id`
- `files`
- `read_only`
- `workspace`
- `guard_config`

校验步骤：

1. 配置是否启用
2. actor 是否在 `allowedLeadAgents`
3. 是否声明且仅声明一个 `parent_task_id`
4. 若为写入委派，`files` 是否存在、是否去重、是否为空
5. 若为只读委派，是否被配置允许
6. 写入委派的 `files` 是否命中受保护路径/前缀
7. 写入委派的 `files` 是否与活跃任务写集冲突
   - 需要忽略当前 `parent_task_id`
   - 不应简单按 `ai_type` 跳过所有 Codex 任务

### 3. CLI Entry

新增 CLI 入口，建议命名为：

```bash
python3 -m ai_collab.cli spawn-agent-guard \
  --actor codex \
  --parent-task TASK-XXX \
  --read-only
```

或：

```bash
python3 -m ai_collab.cli spawn-agent-guard \
  --actor codex \
  --parent-task TASK-XXX \
  --files path/a.py path/b.md
```

行为：

- 输出 allowed / violations / report / history
- 允许作为 Codex 使用 `spawn_agent` 前的显式 preflight
- 校验失败时返回非零退出码

### 4. Automatic Hook Entry

在现有 `CodexIntegration._build_hook_config()` 中增加 `PreToolUse` `Agent` hook，调用新的
`ai_collab/hooks/spawn_agent_preflight.py`。

行为：

- 在 Claude Code 即将执行 `Agent` 工具时自动触发
- 优先从 `tool_input` 读取显式 `parent_task_id` / `files` / `read_only` 元数据
- 若 `parent_task_id` 缺失，回退到 `.cc-claude-codex/runtime.json` 中的 `task_id`
- 若写集未显式声明，尝试从 `tool_input` 文本提取路径；仍缺失时回退到 `codex-progress.md` 的 `Scope`
- 自动推导出的上下文继续走同一个 `run_spawn_agent_guard(...)`
- guard 阻断时，hook 直接 deny 这次 `Agent` 调用，并把违规原因返回给 Claude Code

说明：

- 手动 `spawn-agent-guard` CLI 继续保留，主要用于诊断、预演和本地排障
- 自动 hook 不新增第二套规则，仍以 `.vscode/ai-collab.json` 中的 `spawnAgentGuard` 为唯一 SSOT

### 5. Audit Output

每次 guard 运行都写：

- latest JSON：当前检查结果
- history JSONL：追加式审计轨迹

报告至少包含：

- actor
- parent_task_id
- files
- allowed
- violations
- active_conflicts
- timestamp
- 自动 preflight 的上下文来源（例如 runtime / prompt / progress scope）

## Open Questions

- 保护路径是否要把 `.vscode/ai-collab.json` 和 `openspec/changes/` 也纳入默认阻断列表
- `Agent` tool 的委派文本如果未显式声明写集，是否应长期强制采用推荐元数据格式
