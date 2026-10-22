# RESULT — TASK-P0-CONSENSUS-ENGINE-001 Hermes 迁移基线

**状态**: 计划中
**完成时间**: 2026-10-22T17:49:34+08:00
**报告版本**: 2.0.0
**本地基线执行者**: claude_code (AGENT_ARCH)
**承接执行者**: codearts_agent (AGENT_EXEC)
**审核者**: user
**change_id**: migrate-parallel-architecture-to-hermes
**交接说明**: 本文件为 CodeArts 承接前的基线快照。本地移植层已实测通过；覆盖率补强与远程部署由 CodeArts 承接，收口时需同步更新本文件的状态头与验证结果章节。

---

## 任务概述

将 ai-collab-base 的 `ai_collab/engines/consensus_engine.py` 移植到 Hermes 移植目标目录 `hermes_target/`，实现多模型并发查询能力（asyncio.gather）、分级超时控制、重试机制与结果归一化。

## 交付物清单

| 文件 | 说明 |
|---|---|
| `hermes_target/hermes_agent/engines/consensus_engine.py` | 移植后的引擎实现（425 行） |
| `hermes_target/hermes_agent/engines/__init__.py` | 包导出 |
| `hermes_target/hermes_agent/tests/unit/test_consensus_engine.py` | 单元测试（3 用例） |
| `hermes_target/config.yaml` | `engines.consensus` 配置段 |

## 适配变更

1. `providers` → `models`：新增 `models` 别名，保留 `providers` 兼容性
2. Hermes 日志集成：`from hermes.logger import log`
3. 移除 ai-collab 特有依赖：`IntegrationMode` 以本地 mock 替代

## 配置段

```yaml
engines:
  consensus:
    enabled: true
    max_concurrent: 5
    global_timeout: 60
    retry:
      max_retries: 3
      backoff: exponential
    fallback_mode: partial
```

## 执行命令

以下三条为工单契约的验收命令，均在仓库根目录执行：

```bash
PYTHONPATH=hermes_target python3 -m pytest hermes_target/hermes_agent/tests/unit/test_consensus_engine.py -v
python3 -c "import sys; sys.path.insert(0, 'hermes_target'); from hermes_agent.engines import ConsensusEngine; print('OK')"
PYTHONPATH=hermes_target python3 -m pytest hermes_target/hermes_agent/tests/unit/test_consensus_engine.py -q --cov=hermes_agent.engines.consensus_engine --cov-fail-under=80
```

> **契约修正说明**：原第一条命令缺少 `PYTHONPATH=hermes_target`，直接执行会在收集阶段抛 `ModuleNotFoundError: No module named 'hermes_agent'`。现按「hermes_target 是外部移植目标、其模块不进入主仓依赖」这一前提，在单条命令内显式补齐路径前缀；未改动 `[tool.pytest.ini_options] testpaths = ["tests"]`，hermes_target 仍不进入主仓覆盖率分母。

## 验证结果

### 命令 1 — 单元测试

```text
collected 3 items

hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_consensus_engine_imports PASSED
hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_consensus_engine_has_models PASSED
hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_ai_provider_dataclass PASSED

3 passed in 0.02s
```

### 命令 2 — 导入冒烟

```text
OK
```

### 命令 3 — 覆盖率门禁（当前未达标）

```text
Name                                                     Stmts   Miss  Cover   Missing
--------------------------------------------------------------------------------------
hermes_target/hermes_agent/engines/consensus_engine.py     157    110    30%   88-89, 94-99, 105-137, 141, 145-146, 177-217, 233-255, 274-302, 316-318, 336-352, 369, 379, 383-387, 391-408, 413-414, 419-421
--------------------------------------------------------------------------------------
TOTAL                                                      157    110    30%
3 passed in 0.05s
FAIL Required test coverage of 80% not reached. Total coverage: 29.94%
```

| 验收标准 | 实测 | 结论 |
|---|---|---|
| 单元测试全部通过 | 3/3 passed | 达标 |
| 导入冒烟 | OK | 达标 |
| 覆盖率 ≥ 80% | 30% | 未达标 |

**覆盖率缺口成因**：现有 3 个用例只覆盖模块导入、实例化与 dataclass 默认值。`asyncio.gather` 并发查询、分级超时、指数退避重试、结果归一化等核心路径（对应 Missing 列出的 88-89 / 94-137 / 177-217 / 233-302 / 336-352 等区间）尚未被触达。

## 风险

1. **覆盖率不达标（高）**：实测 30%，距 80% 门禁缺口约 50 个百分点。补齐并发查询、超时隔离、重试退避、结果归一化四条主路径的用例，是收口前的硬性前置。
2. **pytest 收集面串扰（中）**：本仓 `[tool.pytest.ini_options] testpaths = ["tests"]` 刻意排除 `hermes_target/`。若在全局 pytest 配置追加 `pythonpath` 或放宽 `testpaths`，hermes_target 的 425 行会进入主仓覆盖率分母，直接影响 CI 覆盖率门禁。路径注入必须限定在单条命令内。
3. **远程环境不可达（中）**：工单原始步骤中的 `ssh openclaw` / `scp` 指向一个本会话无法访问的主机。远程部署链路（`~/.hermes/hermes-agent/engines/`、`~/.hermes/config.yaml`、`~/.openclaw-mac/workspace/ai-media-analysis-report.py`）尚无可执行凭证，需先确认接入方式。
4. **日志集成依赖（中）**：`from hermes.logger import log` 依赖 Hermes 侧的 `hermes.logger` 模块。本仓副本以 mock 绕开，真实 Hermes 环境中该模块路径需在部署时核对。
5. **性能收益未实测（低）**：工单声称延迟降低 60%，但仓库内无基准脚本与基准数据，该收益为设计预期值而非实测值。

## 回滚

| 场景 | 回滚动作 |
|---|---|
| 覆盖率补强引入回归 | 将 `hermes_target/hermes_agent/tests/unit/test_consensus_engine.py` 还原至本文件记录的 3 用例基线（git 历史 `3ae6cca`），命令 1 与命令 2 仍应通过 |
| 远程部署后 Hermes 启动失败 | 删除 `~/.hermes/hermes-agent/engines/consensus_engine.py`，并移除 `~/.hermes/config.yaml` 的 `engines.consensus` 段；`fallback_mode: partial` 保证单 provider 失败不阻断主流程 |
| 配置项与既有部署冲突 | 将 `engines.consensus.enabled` 置为 `false` 即可关闭引擎，不影响既有串行调用路径 |
| 本仓侧全量回退 | `git revert` 本次改动涉及的 `hermes_target/` 与工单文件；因 `hermes_target/` 是独立目录，不触及 `ai_collab/` 主链路 |

## 承接指引（CodeArts）

1. 补齐 `hermes_target/hermes_agent/tests/unit/test_consensus_engine.py` 的并发查询、超时隔离、重试退避、结果归一化用例，使命令 3 的覆盖率门禁通过。
2. 确认远程 Hermes 环境接入方式后执行部署，并完成 `ai-media-analysis-report.py` 的调用改造。
3. 收口时更新本文件的任务状态头与验证结果章节，按工单契约回执。
