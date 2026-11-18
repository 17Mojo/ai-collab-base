# 开发记录：CI 覆盖率门禁修复（误删的 coverage 配置还原）

## 记录信息

- **任务ID**: quickfix/no-spec（承接 2026-10-22_pytest-collection-fix.md 的后续建议 #1）
- **AI类型**: Claude Code
- **时间**: 2026-10-22
- **分支**: `refactor/slimming-2026-09-20`
- **任务描述**: 承接上一条日志「全量跑 pytest 拿覆盖率真证，验证 CI 85% 阈值本地达成」，
  结论为**不达成（83% < 85%）**。定位根因并还原被误删的 `[tool.coverage.*]` 配置段。

---

## 背景

上一条日志修复了 pytest collection error（`testpaths = ["tests"]`），并在「后续建议」中要求
验证 CI 覆盖率阈值本地是否达成。实测结果：

| 口径 | 命令 | 结果 |
|---|---|---|
| test.yml 门禁 | `coverage report --fail-under=85` | **exit 2**，83% < 85% → CI 会红 |
| mypy-gate.yml 门禁 | XML `line-rate` | 82% ≥ 80% → 通过 |

两个工作流使用**两套不同阈值**（85% vs 80%），且互不知情，因此只有 test.yml 暴露问题。

## 根因

commit `576b2a5`（chore(ruff): 扩展检查面…）在编辑 ruff 配置时**连带删除了** `pyproject.toml` 中
两个与 ruff 无关的段落：

- `[tool.pytest.ini_options]`（testpaths / asyncio_mode / strict-markers / markers / filterwarnings）
- `[tool.coverage.run]` + `[tool.coverage.report]`（omit / skip_empty / exclude_lines）

`[tool.coverage.run] omit` 是 commit `51b5b07`（"raise TOTAL to 86 percent via omit"）为
排除 CLI 入口模块而显式加入的。误删后：

- 覆盖率口径从 14810 条语句回到 17550 条（4 个入口模块重新计入）
- TOTAL 从 87% 跌至 83%，跌破 test.yml 的 85% 硬门禁

这正是 CLAUDE.md「经验 3」预警的失败模式：**门禁数字被真实回归掩盖**——因为同一 commit
把 ruff 步骤也改坏了，ruff 先行失败使覆盖率步骤从未被执行，问题被遮蔽了一个版本。

## 修复

`pyproject.toml` 还原两段配置（内容取自 `git show 51b5b07` 原始定义，未改写）：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
addopts = "-ra --strict-markers"
markers = ["asyncio: ...", "slow: ...", "integration: ..."]
filterwarnings = ["ignore::DeprecationWarning"]

[tool.coverage.run]
omit = [
    "ai_collab/__main__.py",
    "ai_collab/cli/__main__.py",
    "ai_collab/cli/_cli_main.py",
    "ai_collab/cli/react_convert.py",
]
```

### 方案选择

对比三个候选后选定「还原 omit」：

1. **还原 omit（采纳）** — 87%（实测 88%），门禁恢复绿色。
   依据：CLAUDE.md「经验 3」明确写明「CLI 入口/编排层/集成层不适合单测覆盖，
   应该用 E2E 测试或显式 omit，不该靠凑覆盖率数字掩盖结构性限制」。
   omit 名单正是这 4 个入口模块，与项目既定原则一致。
2. **下调门禁到 83%** — 治标，且会让 576b2a5 的误删永远不被发现。
3. **补测试拉到 85%** — 需新增覆盖约 362 条语句（react_convert.py 123 条全 0%、
   codex_integration.py 235 条未覆盖）。最扎实但成本高，且入口层单测性价比低。

### 安全性验证

还原 `--strict-markers` 前先核对了仓库实际用到的 marker：

| marker | 使用次数 | 是否需注册 |
|---|---|---|
| `asyncio` | 40 | pytest-asyncio 插件自带注册 |
| `parametrize` | 12 | pytest 内置 |
| `skipif` | 6 | pytest 内置 |

原声明的 `slow` / `integration` 无人使用。结论：开启 strict-markers 不会误伤现有测试。

## 验证

| 门禁 | 命令 | 修复前 | 修复后 |
|---|---|---|---|
| test.yml 覆盖率 | `coverage report --fail-under=85` | exit 2（83%） | **exit 0（88%）** |
| mypy-gate 覆盖率 | XML `line-rate` | 82% | **88%** |
| test.yml ruff | `ruff check ai_collab/ scripts/` | pass | pass |
| mypy | `mypy ai_collab` | 0 errors / 99 files | 0 errors / 99 files |
| 单测 | `pytest tests/unit/ -q` | 2344 passed / 1 skipped | 2344 passed / 1 skipped |
| 集成 | `pytest tests/integration/ -q` | 219 passed / 5 skipped | 219 passed / 5 skipped |
| 全量 | `pytest -q` | collection error | **2660 passed / 6 skipped** |

覆盖率口径明细：TOTAL 语句数 17550 → 14581，未覆盖 2994 → 1698。

## 变更文件

- `pyproject.toml`（+41 行：`[tool.pytest.ini_options]` 补全 + `[tool.coverage.*]` 还原）

## 风险与回滚

- 风险：`omit` 名单把 `_cli_main.py`（2606 条语句）排除在覆盖率统计外，CLI 入口层回归不被门禁感知。
  这与项目既定原则一致，但需知悉。
- 风险：`asyncio_mode = "auto"` 改变了异步测试的收集语义（此前 40 处显式 `@pytest.mark.asyncio`
  仍全部生效，实测通过数不变）。
- 回滚点：删除 `[tool.coverage.*]` 段即可恢复修复前状态（覆盖率口径回到 83%）。

## 遗留发现（未修，需独立任务）

1. **sqlite3 连接泄漏（真实 Bug）** — `ai_collab/pack/market_store.py` 15 处
   `with sqlite3.connect(...) as conn:`。sqlite3 的 `with` 只管理**事务**（提交/回滚），
   **不关闭连接**。测试跑出 76 条 `ResourceWarning: unclosed database`。
   安全修法需同时保住提交语义：
   `with contextlib.closing(sqlite3.connect(p)) as conn, conn:`
   （若只包 closing 而丢掉 `conn:` 事务上下文，会引入数据不落盘的新 Bug——不可只改前半段）
2. **两套覆盖率门禁并存** — test.yml ≥85% 与 mypy-gate.yml ≥80%，口径不同且互相不知情。
   建议统一为单一门禁。
3. **`ai_collab/cli/react_convert.py` 为孤儿脚本** — 123 条语句、0% 覆盖，
   `_cli_main.py` 未 import 它，`sys.path.insert` + `argparse` 自成 CLI。
   应删除或接入主 CLI。
4. **`_cli_main.py` 2606 行** — 与 CLAUDE.md「经验 3」记录的巨型 CLI 一致，仍是 P1。
