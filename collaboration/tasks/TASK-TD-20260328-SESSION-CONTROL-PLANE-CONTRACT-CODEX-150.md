# 任务: Session control plane contract + slice1 integration baseline

**任务ID**: TASK-TD-20260328-SESSION-CONTROL-PLANE-CONTRACT-CODEX-150  
**change_id**: add-session-orchestration-control-plane  
**分配给**: codex  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: duoai-coordinator
- **support_skills**: [backend-architect, api-test-pro]
- **scope_in**:
  - 为 Slice 1 固化 shared contract，统一 session registry 与 intervention queue 的路径、命名、transport mode 与审计约定
  - 明确 `manual / bridge` 两种 delivery mode 的最小语义，避免 Claude / CodeArts 后续 adapter 各自发散
  - 负责整合 `claude_code` 148 与 `codearts_agent` 149 的输出，收敛到统一 CLI / monitoring 口径
  - 确保 session control plane 基线不削弱现有 ACK / receipt / result consistency / validate-contract 强门禁
  - 产出 Slice 1 集成验证与后续 Slice 2/3 接口边界
- **scope_out**:
  - 不直接实现 Claude push adapter
  - 不直接实现 CodeArts pull adapter
  - 不实现桌面自动化
  - 不把 `codex mcp-server` 误用成完整会话协议

## 输入

- `openspec/changes/add-session-orchestration-control-plane/proposal.md`
- `openspec/changes/add-session-orchestration-control-plane/design.md`
- `openspec/changes/add-session-orchestration-control-plane/tasks.md`
- `collaboration/results/SESSION_ORCHESTRATION_EXTERNAL_RESEARCH_AND_ADAPTER_STRATEGY_2026-03-28.md`
- `collaboration/results/SESSION_ORCHESTRATION_V1_IMPLEMENTATION_SLICES_2026-03-28.md`
- `collaboration/tasks/TASK-TD-20260328-SESSION-REGISTRY-CLI-BASELINE-CLAUDE-148.md`
- `collaboration/tasks/TASK-TD-20260328-SESSION-INTERVENTION-QUEUE-AUDIT-CODEARTS-149.md`
- `.vscode/ai-collab.json`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260328-SESSION-CONTROL-PLANE-CONTRACT-CODEX-150.md`
- 必须包含:
  - 实际修改文件清单
  - shared contract / file path / delivery mode 约定
  - Slice 1 集成验证结果
  - 对 Slice 2 / Slice 3 的接口边界说明
  - 风险与回滚点

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_session_registry.py \
  tests/unit/test_cli_session_registry.py \
  tests/unit/test_intervention_queue.py \
  tests/unit/test_session_intervention_summary.py
python3 -m ai_collab.cli sessions inspect
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
openspec validate add-session-orchestration-control-plane --strict
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
