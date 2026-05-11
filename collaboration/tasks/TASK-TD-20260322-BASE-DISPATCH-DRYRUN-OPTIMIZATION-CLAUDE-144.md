# 任务: Base dispatch dry-run optimization

**任务ID**: TASK-TD-20260322-BASE-DISPATCH-DRYRUN-OPTIMIZATION-CLAUDE-144  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P0

## Skill 分配（必填）

- **primary_skill**: planning-with-files
- **support_skills**: [systematic-debugging, api-test-pro]
- **scope_in**:
  - 基于 `BASE_DISPATCH_ANOMALY_ROOTCAUSE_2026-03-22.md`，降低 dispatch dry-run 模式下的误报和异常空派单
  - 优先处理 `candidate_count>0 且 dispatched_count=0` 但后续 apply 正常的情况
  - 允许修改 dispatch 相关实现与测试，但不改变 apply 模式的既有稳定行为
  - 输出实际代码修改与验证证据
- **scope_out**:
  - 不调整 benefit 计算口径
  - 不修改研究验证线资产
  - 不进行破坏性工作区清理

## 输入

- `collaboration/results/BASE_DISPATCH_ANOMALY_ROOTCAUSE_2026-03-22.md`
- `collaboration/results/RESULT_TASK-TD-20260322-BASE-DISPATCH-ANOMALY-ROOTCAUSE-CODEARTS-143.md`
- `scripts/agent_dispatch_bridge.py`
- `ai_collab/dispatch_trigger.py`
- `ai_collab/cli.py`
- `tests/unit/test_agent_dispatch_bridge.py`
- `tests/unit/test_dispatch_trigger.py`
- `tests/unit/test_cli.py`

## 输出要求

- 资产文件: `collaboration/results/BASE_DISPATCH_DRYRUN_OPTIMIZATION_2026-03-22.md`
- result_file: `collaboration/results/RESULT_TASK-TD-20260322-BASE-DISPATCH-DRYRUN-OPTIMIZATION-CLAUDE-144.md`
- 必须包含:
  - 实际修改文件清单
  - dry-run 误报修复点
  - 测试/验证结果
  - 风险与非破坏性回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_agent_dispatch_bridge.py \
  tests/unit/test_dispatch_trigger.py \
  tests/unit/test_cli.py
python3 -m ai_collab.cli dispatch --dry-run --force-workspace
test -f collaboration/results/BASE_DISPATCH_DRYRUN_OPTIMIZATION_2026-03-22.md
rg -n "dry-run|误报|candidate_count|dispatched_count|回滚|测试" collaboration/results/BASE_DISPATCH_DRYRUN_OPTIMIZATION_2026-03-22.md
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [x] pending
- [x] planning
- [x] implementing
- [x] testing
- [ ] blocked
- [x] completed
- [ ] failed
- [ ] cancelled
