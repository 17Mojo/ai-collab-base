# Agent Governance Quickstart

**版本**: 1.0.0  
**生效日期**: 2026-03-03  
**目标**: 让 Claude Code 与 CodeArts Agent 在上岗前快速完成治理对齐、自改造和协同测试。

## 1. 治理口径（必须一致）

- **User**: 产品负责人，最终决策
- **Codex**: 开发管理负责人（计划/分派/门禁/回滚）
- **Claude Code**: 主执行者（实现与交付）
- **CodeArts Agent**: 执行辅助者（测试/文档/并行验证）
- **Copilot**: 停用，仅保留兼容映射

## 2. 必读资料（启动前）

1. `collaboration/PROTOCOL.md`
2. `rules/codex_agent_rules.md`
3. `rules/claude_code_memory.md`（Claude）
4. `rules/codearts_agent_rules.md`（CodeArts）
5. `collaboration/results/GOVERNANCE_SWITCHOVER_2026-03-02.md`

## 3. 上岗前对齐动作（DoD）

- 完成一次本地激活并回传 `rules_loaded`
- 认领治理对齐工单并更新状态为 `implementing`
- 完成各自自改造任务（配置/规则/hook）
- 通过协同 smoke 测试并输出结果文件

## 4. 协同测试最小集合

```bash
python3 -m ai_collab.cli status -v
python3 -m ai_collab.cli tasks list --status active
python3 -m pytest -q tests/unit/test_agent_orchestrator.py tests/unit/test_session_inject.py tests/unit/test_cli.py
```

## 5. 偏差处理规则

- 发现口径漂移：立即阻断继续开发，先修规则和配置
- 发现职责冲突：提交给 Codex 做裁决，不自行跳过
- 发现门禁失败：进入 `systematic-debugging` 流程，禁止拍脑袋修复

