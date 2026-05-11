# 任务: Session registry + CLI baseline

**任务ID**: TASK-TD-20260328-SESSION-REGISTRY-CLI-BASELINE-CLAUDE-148  
**change_id**: add-session-orchestration-control-plane  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: backend-architect
- **support_skills**: [planning-with-files, api-test-pro]
- **scope_in**:
  - 为 `session-orchestration` 建立 V1 的 `session registry` 持久化能力
  - 新增统一 CLI 入口，至少覆盖 session register / refresh / inspect 的基础能力
  - 注册对象至少覆盖 `claude_code`、`codearts_agent`、`codex`
  - 持久化字段至少覆盖 `session_id`、`assignee`、`transport_mode`、`session_status`、`last_seen_at`、`last_handoff_artifact`、`health_status`
  - 复用当前项目的 latest/history/summary 输出习惯，不另造不可审计的隐式状态
  - 补齐单测，确保 registry 与 CLI 基线可回归
- **scope_out**:
  - 不实现 session health aggregation
  - 不实现 Claude push / CodeArts pull adapter
  - 不做桌面自动化或 UI 粘贴方案
  - 不修改现有 ACK / receipt / result consistency 强门禁语义

## 输入

- `openspec/changes/add-session-orchestration-control-plane/proposal.md`
- `openspec/changes/add-session-orchestration-control-plane/design.md`
- `openspec/changes/add-session-orchestration-control-plane/tasks.md`
- `collaboration/results/SESSION_ORCHESTRATION_EXTERNAL_RESEARCH_AND_ADAPTER_STRATEGY_2026-03-28.md`
- `collaboration/results/SESSION_ORCHESTRATION_V1_IMPLEMENTATION_SLICES_2026-03-28.md`
- `ai_collab/state_manager.py`
- `ai_collab/cli.py`
- `ai_collab/codex_integration.py`
- `ai_collab/hooks/session_inject.py`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260328-SESSION-REGISTRY-CLI-BASELINE-CLAUDE-148.md`
- 必须包含:
  - 实际修改文件清单
  - session registry 数据模型与 CLI 子命令说明
  - latest/history/summary 路径说明
  - 测试/验证结果
  - 风险与回滚点

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_session_registry.py \
  tests/unit/test_cli_session_registry.py
python3 -m ruff check \
  ai_collab/session_registry.py \
  ai_collab/cli.py \
  tests/unit/test_session_registry.py \
  tests/unit/test_cli_session_registry.py
python3 -m ai_collab.cli sessions register --assignee claude_code --session-id demo-claude --transport-mode manual
python3 -m ai_collab.cli sessions inspect
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [ ] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [x] completed
- [ ] failed
- [ ] cancelled
