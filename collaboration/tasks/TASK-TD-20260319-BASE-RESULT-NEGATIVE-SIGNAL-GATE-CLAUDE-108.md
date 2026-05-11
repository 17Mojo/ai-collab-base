# 任务: 结果门禁负向信号拦截补强

**任务ID**: TASK-TD-20260319-BASE-RESULT-NEGATIVE-SIGNAL-GATE-CLAUDE-108  
**change_id**: bugfix/no-spec  
**分配给**: claude_code  
**reviewer**: codex  
**优先级**: P1

## Skill 分配（必填）

- **primary_skill**: systematic-debugging
- **support_skills**: [planning-with-files, api-test-pro]
- **scope_in**:
  - 基于 `106/107` 的收口问题，补强 `receipt` / `result artifact` 门禁，避免“结果文件写着 blocked / 未集成 / not found / 待添加”却仍可进入 completed
  - 在 `ai_collab/state_manager.py` 与相关单测中增加负向信号识别
  - 覆盖至少以下场景: `blocked`, `not found`, `FILE NOT FOUND`, `未集成`, `待集成`, `待添加`
  - 保持现有 acceptance command 检查逻辑，不重写整个 receipt 流程
  - 在结果报告中说明本次补强如何防止研究型报告误过 gate
- **scope_out**:
  - 不改 dispatch / trigger 主流程
  - 不修改研究文档本身
  - 不引入 OpenSpec 变更

## 输入

- `ai_collab/state_manager.py`
- `tests/unit/test_state_manager.py`
- `tests/unit/test_agent_receipt_bridge.py`
- `collaboration/results/RESULT_TASK-TD-20260319-RESEARCH-CROSS-INDUSTRY-TEMPLATE-KIT-CLAUDE-106.md`
- `collaboration/results/RESULT_TASK-TD-20260319-BASE-PLAYWRIGHT-FAILURE-SUMMARY-WORKFLOW-CODEARTS-107.md`

## 输出要求

- result_file: `collaboration/results/RESULT_TASK-TD-20260319-BASE-RESULT-NEGATIVE-SIGNAL-GATE-CLAUDE-108.md`
- 必须包含:
  - 负向信号规则摘要
  - 新增/更新测试列表
  - 对 `106/107` 类问题的拦截说明
  - 风险与回滚

## acceptance_commands（必填）

```bash
python3 -m pytest -q \
  tests/unit/test_state_manager.py \
  tests/unit/test_agent_receipt_bridge.py
rg -n "blocked|not found|未集成|待集成|待添加" \
  ai_collab/state_manager.py \
  tests/unit/test_state_manager.py \
  tests/unit/test_agent_receipt_bridge.py
python3 -m ai_collab.cli tasks validate-contract --scope active --strict
```

## 状态

- [x] pending
- [ ] planning
- [ ] implementing
- [ ] testing
- [ ] blocked
- [ ] completed
- [ ] failed
- [ ] cancelled
