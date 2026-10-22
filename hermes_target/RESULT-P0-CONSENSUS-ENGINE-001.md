# RESULT — TASK-P0-CONSENSUS-ENGINE-001 Hermes 移植收口

**状态**: 本地移植层已完成（覆盖率门禁已转绿）
**完成时间**: 2026-10-23T00:52:00+08:00
**报告版本**: 3.0.0
**执行者**: codearts_agent (AGENT_EXEC)
**审核者**: user
**change_id**: migrate-parallel-architecture-to-hermes
**执行口径**: 分支 `feat/codearts-collab-wiring` / HEAD `ce8a3b9` / Python 3.14.6 / macOS darwin / 分母=单文件 `hermes_target/hermes_agent/engines/consensus_engine.py`
**承接说明**: 本文件由 Claude Code 的 2.0.0 基线快照升级而来，覆盖其「覆盖率不达标」章节；本地移植层四条主路径已全部落地并通过工单契约的三条验收命令。

---

## 任务概述

将 ai-collab-base 的 `ai_collab/engines/consensus_engine.py` 移植到 Hermes 移植目标目录 `hermes_target/`，实现多模型并发查询能力（asyncio.gather）、分级超时控制、重试机制与结果归一化。

## 交付物清单

| 文件 | 说明 | 规模 |
|---|---|---|
| `hermes_target/hermes_agent/engines/consensus_engine.py` | 移植后的引擎实现（v1.3，含四条主路径公开 API） | 748 行 |
| `hermes_target/hermes_agent/engines/__init__.py` | 包导出（`ConsensusEngine` / `AIProvider`） | 4 行 |
| `hermes_target/hermes_agent/tests/unit/test_consensus_engine.py` | 单元测试（54 用例，覆盖四条主路径 + 兼容层） | 660 行 |
| `hermes_target/config.yaml` | `engines.consensus` 配置段 | 10 行 |

## 本次实现变更（v1.2 → v1.3）

四条主路径从「仅内部实现」升级为「公开 API + 可测试」：

| 主路径 | 公开入口 | 实现要点 |
|---|---|---|
| 多模型并发查询 | `query_models(topic)` / `query_multiple_models(topics)` / `query_consensus(topic)` | `asyncio.gather` 并发 + `asyncio.Semaphore(max_concurrent)` 限流 |
| 超时控制 | `global_timeout`（全局）+ `AIProvider.timeout`（单 provider） | 双层 `asyncio.wait_for`；单 provider 超时不拖垮整体（超时隔离） |
| 重试机制 | `AIProvider.max_retries`（默认 3） | 指数退避 `backoff_base * 2 ** attempt` |
| 结果归一化 | `normalize_result(raw, provider, status=, error=)` | 统一 `ai/response/confidence/timestamp/provider/status`；失败以 `status` 表达而非抛异常 |

配套增强：

1. **配置加载**：新增 `config_path` 参数，读取 Hermes `config.yaml` 的 `engines.consensus` 段（`max_concurrent` / `global_timeout` / `retry.max_retries` / `fallback_mode`）；文件缺失、YAML 损坏、根节点非 mapping 三种异常均降级为默认配置，不阻断引擎启动。
2. **参数化构造**：`ConsensusEngine(config_path=None, *, global_timeout=None, max_concurrent=None, max_retries=None, models=None, mode=None)`，向后兼容原有无参构造。
3. **状态机**：单次查询结果携带 `status`（`success` / `partial` / `failed` / `timeout`），对应工单 `fallback_mode: partial` 的「部分失败仍返回结果」语义。
4. **日志出口**：优先 `from hermes.logger import log`，缺失时回退标准 `logging`，日志后端异常不影响主流程。
5. **兼容层保留**：原有 `generate_consensus` / `_query_multiple_ais` / `_query_multiple_ais_mock` / `_query_multiple_ais_real` / `get_consensus_summary` 语义不变。

## 执行命令

以下三条为工单契约的验收命令，均在仓库根目录执行：

```bash
PYTHONPATH=hermes_target python3 -m pytest hermes_target/hermes_agent/tests/unit/test_consensus_engine.py -v
python3 -c "import sys; sys.path.insert(0, 'hermes_target'); from hermes_agent.engines import ConsensusEngine; print('OK')"
PYTHONPATH=hermes_target python3 -m pytest hermes_target/hermes_agent/tests/unit/test_consensus_engine.py -q --cov=hermes_agent.engines.consensus_engine --cov-fail-under=80
```

本次实施过程中的过程命令（供复现）：

```bash
python3 -m ai_collab.cli run --redispatch
python3 -m ai_collab.cli run
python3 -m ai_collab.cli tasks update --task-id TASK-P0-CONSENSUS-ENGINE-001 --ai codearts_agent --status implementing
python3 -m ruff check hermes_target/hermes_agent/engines/consensus_engine.py hermes_target/hermes_agent/tests/unit/test_consensus_engine.py
```

> **契约修正说明**：原第一条命令缺少 `PYTHONPATH=hermes_target`，直接执行会在收集阶段抛 `ModuleNotFoundError: No module named 'hermes_agent'`。路径前缀在单条命令内显式补齐；未改动 `[tool.pytest.ini_options] testpaths = ["tests"]`，hermes_target 仍不进入主仓覆盖率分母。

## 验证结果

### 命令 1 — 单元测试

```text
collected 54 items

hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_consensus_engine_imports PASSED
hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_query_models_concurrent_returns_all_results PASSED
hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_query_models_respects_max_concurrent PASSED
hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_query_model_timeout_is_isolated PASSED
hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_query_model_retries_then_succeeds PASSED
hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_query_model_retry_uses_exponential_backoff PASSED
hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_query_consensus_global_timeout PASSED
hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_query_consensus_partial_when_some_provider_fails PASSED
hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_parallel_query_is_faster_than_serial PASSED
hermes_target/hermes_agent/tests/unit/test_consensus_engine.py::test_normalize_result_with_dict_payload PASSED
...

54 passed in 1.93s
```

### 命令 2 — 导入冒烟

```text
OK
```

### 命令 3 — 覆盖率门禁

```text
Name                                                     Stmts   Miss  Cover
----------------------------------------------------------------------------
hermes_target/hermes_agent/engines/consensus_engine.py     309     14    95%
----------------------------------------------------------------------------
TOTAL                                                      309     14    95%
Required test coverage of 80% reached. Total coverage: 95.47%
54 passed in 1.93s
```

未覆盖的 14 行集中在防御性分支：`hermes.logger` 导入兜底（6 行，仅 Hermes 运行时存在）、`_resolve_model` 的空 provider 兜底、`query_models` 内层 gather 的异常归一化、`_normalize_client_response` 的非 dict/非 str 分支、模块级 `__main__` 入口。

### 验收标准对照

| 验收标准 | 实测 | 结论 |
|---|---|---|
| `consensus_engine.py` 成功移植到 Hermes | `hermes_target/hermes_agent/engines/consensus_engine.py`，748 行，公开 API 四条主路径齐备 | 达标 |
| 单元测试全部通过 | 54 passed / 0 failed（基线 3 passed） | 达标 |
| 覆盖率 ≥ 80% | 95.47%（309 stmts / 14 miss） | 达标 |
| `config.yaml` 包含 engines 配置段 | `engines.consensus`：enabled / max_concurrent=5 / global_timeout=60 / retry.max_retries=3 / fallback_mode=partial | 达标 |
| 性能基准：延迟降低 ≥ 50% | 实测 5 topic × 0.2s 延迟：并行 0.202s vs 串行 1.012s，加速 5.00x，延迟降低 80.0% | 达标 |

### 四条主路径的用例覆盖映射

| 主路径 | 对应用例 |
|---|---|
| 多模型并发查询 | `test_query_models_concurrent_returns_all_results` / `test_query_multiple_models_returns_one_result_per_topic` / `test_query_models_respects_max_concurrent` / `test_query_multiple_models_respects_max_concurrent` / `test_parallel_query_is_faster_than_serial` |
| 超时控制（全局 + 单 provider） | `test_query_model_timeout_is_isolated` / `test_query_consensus_global_timeout` / `test_query_multiple_ais_real_global_timeout` |
| 重试（max_retries=3 + 指数退避） | `test_query_model_retries_then_succeeds` / `test_query_model_retry_uses_exponential_backoff` / `test_register_provider_honours_max_retries` |
| 结果归一化 | `test_normalize_result_with_dict_payload` / `test_normalize_result_with_string_payload` / `test_normalize_result_with_other_payload` / `test_normalize_result_with_none_payload_keeps_error` / `test_query_model_with_sync_client` / `test_query_model_with_async_client` |

### 静态检查

```text
$ python3 -m ruff check hermes_target/hermes_agent/engines/consensus_engine.py hermes_target/hermes_agent/tests/unit/test_consensus_engine.py
All checks passed!
```

## 测试结论

| 结论项 | 判定 |
|---|---|
| 三条工单验收命令 | 全部通过（54 passed / 0 failed；导入冒烟输出 OK；覆盖率门禁 95.47% ≥ 80%） |
| 单元测试规模 | 54 用例（基线 3 用例），四条主路径各有专属用例 |
| 覆盖率分母 | 单一文件 `hermes_target/hermes_agent/engines/consensus_engine.py`（309 stmts / 14 miss） |
| 静态检查 | ruff 全绿 |
| 四条主路径 | 多模型并发查询 / 超时控制 / 重试退避 / 结果归一化 均已落地为公开 API 并被用例触达 |
| 性能 | 并发 5.00x 加速，延迟降低 80.0%（本地合成基准） |
| 主仓全量回归 | 2786 passed / 1 failed / 6 skipped；唯一失败项 `tests/unit/test_codearts_bridge_deliver.py::test_resolve_credentials_reads_credential_file` 的根因是本机环境变量 `OPENCODE_SERVER_USERNAME=codearts` 污染（该用例只清除 PASSWORD 类变量），与本次改动无调用关系 |
| 远程 Hermes 部署 | 属工单的后续项，需先确认接入方式 |

结论：本地移植层收口完成，工单契约的三条验收命令与覆盖率门禁全部满足。

> 主仓全量回归的唯一失败项不属于本任务范围：本次改动仅涉及 `hermes_target/` 下的三个文件，`git status` 显示 `ai_collab/`、`tests/`、`scripts/` 均无未提交改动；该失败由本机 shell 环境变量 `OPENCODE_SERVER_USERNAME=codearts` 触发——`resolve_credentials` 优先取环境变量，而该用例只删除了 `OPENCODE_SERVER_PASSWORD` / `CODEARTS_KERNEL_PASSWORD`，未删除 `OPENCODE_SERVER_USERNAME`，导致断言期望的 `who` 被环境值 `codearts` 覆盖。清除该环境变量后该用例可通过。

## 风险

1. **远程环境不可达（中）**：工单原始步骤中的 `ssh openclaw` / `scp` 指向一个本会话无法访问的主机。远程部署链路（`~/.hermes/hermes-agent/engines/`、`~/.hermes/config.yaml`、`~/.openclaw-mac/workspace/ai-media-analysis-report.py`）尚无可执行凭证，接入方式需单独确认。本地移植层的正确性不依赖该环境。
2. **pytest 收集面串扰（中）**：本仓 `[tool.pytest.ini_options] testpaths = ["tests"]` 刻意排除 `hermes_target/`。若在全局 pytest 配置追加 `pythonpath` 或放宽 `testpaths`，hermes_target 的 748 行会进入主仓覆盖率分母，直接影响 CI 覆盖率门禁。路径注入必须限定在单条命令内。
3. **日志集成依赖（中）**：`from hermes.logger import log` 依赖 Hermes 侧的 `hermes.logger` 模块，真实 Hermes 环境中该模块路径需在部署时核对。当前实现已做 ImportError 兜底，缺失时自动回退标准 `logging`，因此该风险只影响日志落点、不影响功能。
4. **配置键与 Hermes 真实 schema 可能漂移（中）**：本次按工单给定的 `hermes_target/config.yaml` 结构读取 `engines.consensus`。若 Hermes 上游的 config schema 与该结构不同，`max_concurrent` / `global_timeout` / `retry.max_retries` 将静默取默认值。引擎对配置解析失败一律降级而非抛错，需在远程部署后回读实际生效值。
5. **性能收益为本地合成基准（低）**：80% 的延迟降幅来自本仓构造的固定 0.2s 延迟 provider，不是真实模型端到端时延。真实收益取决于 provider 实际耗时分布与并发上限，需要在 Hermes 侧用真实链路复测。
6. **本仓主链路未受影响（低）**：`hermes_target/` 是独立目录，本次改动不触及 `ai_collab/` 主链路，主仓 2660+ 用例的回归面为零。

## 回滚

| 场景 | 回滚动作 |
|---|---|
| 本仓侧全量回退 | `git checkout -- hermes_target/` 还原引擎与测试两处改动；因 `hermes_target/` 是独立目录，不触及 `ai_collab/` 主链路，主仓测试基线不受影响 |
| 仅回退实现、保留测试 | `git checkout -- hermes_target/hermes_agent/engines/consensus_engine.py` 还原至 425 行基线；命令 1 与命令 2 仍通过，命令 3 的覆盖率回落至 30% 基线值（工单契约门禁随之失败，需同步回退任务状态） |
| 远程部署后 Hermes 启动失败 | 删除 `~/.hermes/hermes-agent/engines/consensus_engine.py`，并移除 `~/.hermes/config.yaml` 的 `engines.consensus` 段；`fallback_mode: partial` 保证单 provider 失败不阻断主流程 |
| 配置项与既有部署冲突 | 将 `engines.consensus.enabled` 置为 `false` 即可关闭引擎，不影响既有串行调用路径 |
| 并发行为异常（限流失效） | 将 `engines.consensus.max_concurrent` 下调至 1 即可退化为串行执行，无需回滚代码 |

## 后续项

1. 远程 Hermes 环境接入方式确认后执行部署，并完成 `ai-media-analysis-report.py` 的调用改造（`_llm_investor_insight()` 串行调用替换为 `query_multiple_models` 并行调用）。
2. 远程部署后回读 `engines.consensus` 配置的实际生效值，并补一次真实模型链路的端到端延迟复测。
