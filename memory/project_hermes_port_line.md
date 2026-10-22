---
name: Hermes 移植线（外部 openclaw 移植 Consensus Engine）
description: TASK-P0-CONSENSUS-ENGINE-001 实为从外部 Hermes(openclaw) 移植 Consensus Engine；hermes_target/ 目录是全量 pytest 的唯一阻断项
type: project
from: Agent
---

`TASK-P0-CONSENSUS-ENGINE-001` 的真实性质是**向外部项目 Hermes（openclaw）移植 Consensus Engine**，而不是在本项目内"激活/实现"一套 Consensus Engine。2026-10-22 现场核验时该任务状态为 `ready_to_implement`，此前 2026-09-20 审计报告把它记为"本项目 Consensus Engine 任务 pending"属于**性质误读**。

**Why:** 本项目没有自带 Consensus Engine 的产品实现，计划来源是外部 openclaw 仓库；移植目标代码被放在 `hermes_target/` 目录下，连同它自己的测试（`hermes_target/hermes_agent/tests/unit/test_consensus_engine.py`）。`hermes_agent` 不是本项目可导入的包，于是 pytest 在收集该目录时报 `ModuleNotFoundError: No module named 'hermes_agent'` —— 这是**全量 pytest 当前唯一的阻断项**，2026-10-22 核验时 collect 2665 项伴随 1 个 collection error。

**How to apply:**
- 跑全量测试 / 本地覆盖率前，先处理 `hermes_target/` 的 pytest 收集问题（排除路径或 `pytest` 忽略配置），不要先怀疑本项目测试代码
- CI 已有覆盖率硬门禁 `--fail-under=85`（`.github/workflows/test.yml`），全量收集跑不起来时该门禁无法执行，"覆盖率待验"就永远无法收口
- 讨论 Consensus Engine 需求时，先分清是"移植外部实现"还是"在本项目新建功能"，两者的任务编号、验收口径、评审对象都不同
