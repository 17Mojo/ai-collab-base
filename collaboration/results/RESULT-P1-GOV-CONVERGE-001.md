# RESULT — TASK-P1-GOV-CONVERGE-001 治理面收敛

**状态**: completed
**完成时间**: 2026-10-22T16:50:00+08:00
**报告版本**: 1.0.0
**执行者**: claude_code (AGENT_EXEC)
**审核者**: user
**change_id**: bugfix/no-spec

---

## 1. 背景

2026-10-22 对 2026-09-20 审计报告做「洞察 vs 真证」现场核验。核验本身推翻了报告的多条结论
（mypy 已是 0 错误、冷启动已 active、无未推送提交、测试 2660 而非 2062），
但在核验过程中暴露出四个**此前未被任何报告记录**的真实缺陷。

其中最关键的一条：**CI 覆盖率门禁当时是红的**，且是被遮蔽的。

---

## 2. 根因分析

### 2.1 覆盖率门禁失效（核心缺陷）

`commit 576b2a5`（*chore(ruff): 扩展检查面…*）在编辑 ruff 配置时，
**连带删除了** `pyproject.toml` 中两个与 ruff 无关的段落：

- `[tool.pytest.ini_options]`
- `[tool.coverage.run]` + `[tool.coverage.report]`

其中 `[tool.coverage.run] omit` 是 `commit 51b5b07`（*"raise TOTAL to 86 percent via omit"*）
为排除 4 个 CLI 入口模块而显式加入的。误删后覆盖率口径从 14810 条语句回到 17550 条，
TOTAL 由 87% 跌至 **83%**，跌破 `test.yml` 的 `--fail-under=85` 硬门禁。

**它为什么静默了一个版本**：同一个 commit 也把 ruff 步骤改坏了，job 在 ruff 阶段就失败退出，
**根本没跑到覆盖率那一步**。直到 `01f67c2` 修好 ruff 步骤，门禁才暴露出来——而那时它已经是红的。

这正是 CLAUDE.md「经验 3」预警的失败模式：门禁数字被真实回归掩盖。

### 2.2 双覆盖率门禁互相掩盖

修复前仓库同时存在两套覆盖率门禁，且**互不知情**：

| 工作流 | 阈值 | 测量方法 |
|---|---|---|
| `test.yml` | 85% | `coverage report --fail-under`（语句覆盖） |
| `mypy-gate.yml` | 80% | 解析 `coverage.xml` 的 `line-rate`（行覆盖） |

宽松的那一套（80%）让严格的那一套（85%）的失败完全不可见。

### 2.3 sqlite3 连接泄漏

`sqlite3` 的 `with conn:` 只管理**事务**（提交/回滚），**不关闭连接**。
`ai_collab/pack/market_store.py` 有 15 处写成 `with sqlite3.connect(...) as conn:`，
每次调用泄漏一个连接，表现为 `ResourceWarning: unclosed database`。

**关键陷阱**：直觉修法「只包 `contextlib.closing`」会**丢掉事务上下文导致写入不落盘**。
已用实验证实：

```
现状 with sqlite3.connect     : 落盘行数=1   unclosed告警=1
仅 closing（无事务上下文）    : 落盘行数=[]  ← 数据丢失
closing + conn 事务上下文     : 落盘行数=[(1,)]  unclosed告警=0
```

### 2.4 state 的 workspace 陈旧

`logs/collaboration_state.json` 的 `workspace` 停在 `/Users/raymondna/Documents/ai-collab-base`
（仓库移动前的旧路径），`tasks: {}`，导致 `ai_collab.cli status` 的所有治理计数器读 0。

**不是数据过期，是代码 bug**：`state_manager.py::_merge_states_with_latest` 的 workspace 优先级为
`local_norm → latest_norm → self.workspace_path`，**真实路径永远轮不到**，
所以任何 CLI 写操作都会把陈旧值原样保留。CLI 从不自动纠正。

危害不止于显示：`scripts/reconcile_state_drift.py:71` 与
`scripts/task_controller_daemon.py:146` 都读 `state["workspace"]` 来定位 RESULT 文件，
路径错了就会**静默找不到结果工件**，漂移永远不会触发。

补充事实：`logs/` 被 `.gitignore:39` 忽略，state 无版本历史；当前 stub 缺 CLI 必写的 5 个 key、
`last_updated` 是整点整秒 `00:00:00.000000`（CLI 写的是 `datetime.now().isoformat()`），
是手工产物而非 CLI 生成。

### 2.5 react_convert 的真实性质

初判为「孤儿脚本」，实测**判断错误**。它是 `ai_collab/pack/react_converter.py`
（93% 覆盖、有已归档 OpenSpec 规格背书）的**唯一生产调用方**，删不得。

`omit` 名单此前把它的 0% 覆盖**藏了起来**，掩盖的真实缺口是：
「同目录 8 个兄弟脚本全部有 `tests/unit/cli/test_*_cli.py` 专属测试，唯独它没有，
且没接入主 CLI」。

---

## 3. 变更内容

### 3.1 还原被误删的配置

`pyproject.toml` 还原两段配置（内容取自 `git show 51b5b07` 原始定义，未改写）：
`[tool.pytest.ini_options]`（testpaths / asyncio_mode / strict-markers / markers / filterwarnings）
+ `[tool.coverage.run]` omit + `[tool.coverage.report]`。

开启 `--strict-markers` 前已核对仓库实际用到的 marker：
`asyncio`(40，插件自带注册) / `parametrize`(12，内置) / `skipif`(6，内置)，
原声明的 `slow` / `integration` 无人使用——确认不会误伤现有测试。

### 3.2 统一覆盖率门禁

新增 `.github/actions/coverage-gate/action.yml` 作为**阈值与测量方法的唯一事实源**，
`test.yml` 与 `mypy-gate.yml` 均改为 `uses: ./.github/actions/coverage-gate`。

**保留双工作流而不是只留一个，是有意的**：2026-09-20 的 `01f67c2` 正是因为 test.yml
自身步骤故障而让门禁整体失效，单一工作流承载单一门禁仍有单点故障风险。
现在两个工作流口径完全一致（阈值 85 + `coverage report --fail-under`），互为备份且不会互相掩盖。

### 3.3 修复 sqlite3 连接泄漏

`ai_collab/pack/market_store.py` 新增 `_connect()` 辅助上下文管理器，
在事务上下文外层补上关闭语义，15 处调用点全部替换。

退出顺序为「先提交/回滚，后关闭」，异常路径同样关闭。
新增 `tests/unit/pack/test_market_store_connection.py`（8 用例）双向守护：
既防连接泄漏回归，也防「只包 closing」导致的数据丢失回归。

同时清理测试侧 7 处同模式泄漏（`tests/unit/pack/test_market.py`）。

### 3.4 处置 react_convert

- 抽出 `convert_requirement_file()`，转换逻辑从 argparse 中解耦（可测试、可被主 CLI 调用）
- 新增 `tests/unit/cli/test_react_convert_cli.py`（18 用例）
- 注册 `pack convert` 子命令；`draft_pack.json` 的 `metadata.pack_id` / `metadata.pack_name`
  与 `pack import` 读取的字段天然对齐，两步闭环成立
- 从 coverage omit 中移除该文件（0% → **83%**）

### 3.5 修复 state 的 workspace

`ai_collab/state_manager.py` 两处：
- `_normalize_state`：把 `workspace` 提升为不受磁盘旧值覆盖的字段
- `_merge_states_with_latest`：`self.workspace_path` 优先于磁盘值

**修代码而不是改数据**——不改代码的话，任何 CLI 写操作都会把陈旧值写回去。

### 3.6 重建 state 并注册任务

走 CLI（不直接编辑 `logs/collaboration_state.json`，遵守
`rules/archive/claude_code_memory.md` 与 `PROTOCOL.md:385` 的禁止条款）：
旧文件备份为 `logs/collaboration_state.json.stale-20260513.bak` 后移出，
由 CLI 以正确的 workspace 重建，再注册两个任务。

顺带校正了 `TASK-P0-CONSENSUS-ENGINE-001` 的契约漂移：
`result_file` 原指向不存在的 `collaboration/results/…`（实际在 `hermes_target/`），
`acceptance_commands` 原指向不存在的 `tests/unit/hermes/…`（实际在 `hermes_target/hermes_agent/…`）。
其 `status: ready_to_implement` 不在 CLI 的 `TaskStatus` 枚举中，映射为语义最接近的 `planning`。

---

## 4. 执行命令

```bash
python3 -m pytest -q
python3 -m ruff check .
python3 -m mypy ai_collab
python3 -m coverage report --fail-under=85
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
python3 -m ai_collab.cli status
```

---

## 5. 测试结论

### 5.1 质量门禁

| 门禁 | 修复前 | 修复后 |
|---|---|---|
| `pytest -q` | collection error（hermes_target 触发 ModuleNotFoundError） | **2686 passed / 6 skipped** |
| `ruff check .` | pass | **pass** |
| `mypy ai_collab` | 0 错误 / 99 文件 | **0 错误 / 99 文件** |
| `coverage report --fail-under=85` | **exit 2（83%）** | **exit 0（89%）** |
| `tasks validate-contract --scope all --strict` | 无任务可校验 | **checked=2 invalid=0** |
| `ai_collab.cli status` 任务计数 | 总数 0 / 活跃 0 | **总数 2 / 活跃 2** |

### 5.2 覆盖率明细

| 指标 | 修复前 | 修复后 |
|---|---|---|
| TOTAL | 83%（17550 语句 / 2994 未覆盖） | **89%**（14720 语句 / 1660 未覆盖） |
| `cli/react_convert.py` | omit 掩盖，实际 0% | **83%**（128 语句） |
| `pack/market_store.py` | 94%（修复前） | 94%（171 语句） |

### 5.3 sqlite 泄漏专项

| 指标 | 修复前 | 修复后 |
|---|---|---|
| `ResourceWarning: unclosed database` | **405 条** | **0 条** |
| 生产代码泄漏点 | 15 处（`market_store.py`） | 0 处 |
| 测试侧泄漏点 | 7 处（`test_market.py`） | 0 处 |

### 5.4 跳过用例说明（6 条，均为环境依赖，非失败）

- `tests/unit/test_database_indexes.py`：缺少 `local-backend/data/client_tokens.db`
- `tests/integration/test_studio_integration.py` ×5：本地后端未在 127.0.0.1:8000 运行

### 5.5 治理面自检

```
契约校验: checked=2 skipped=0 invalid=0 → 无契约问题
漂移检测: scripts/reconcile_state_drift.py --workspace $PWD → drift_count=0, applied_count=0
终态结果一致性: audited=1 consistent=1 mismatch=0 unparseable=0 missing_result=0
Controller: controller --once --dry-run → task_contract_checked=1 invalid=0 error_count=0
```

### 5.6 收口过程中发现并修掉的一个自身缺陷：RESULT 头部缺少状态行

首次跑 `tasks audit-result-consistency` 时，本任务被标为
`unparseable_result_header`（result artifact missing parseable top-level status header）。

`result_consistency_audit.parse_result_header_status`（`ai_collab/result_consistency_audit.py:94-105`）
的规则是：扫描结果文件**前 40 行**，找第一个匹配
`^(?:[-*+]\s+|\d+\.\s+)?\*{0,2}(status|状态|任务状态|执行状态|当前…状态)\*{0,2}\s*[:：]\s*(.+)$` 的行，
并要求其值能归一化成任务状态。

本 RESULT 最初的元数据块只有 `完成时间` / `报告版本` / `执行者` / `审核者` / `change_id`，
**没有任何一行含 status/状态 键**，所以解析器扫完 40 行仍返回空串。
这是**结果工件格式要求**，与 `state_manager` 的收口门禁是**两套独立校验**——
后者只查「三个必需标记 + 6 条 acceptance_commands 逐条比对」，不查状态头。

补一行 `**状态**: completed` 后归一化结果为 `completed`，与 state 的终态一致，审计转绿。
（顺带确认：状态值必须**恰好**归一化成 `completed`；写 `✅` 或 `正常` 也会归一化成 `completed`，
但写 `testing` 会触发 `terminal_status_mismatch`。）

### 5.7 P0 任务的漂移信号：由本次契约校正「暴露」，非本次引入

`controller --once --dry-run` 报出 1 条 result-consistency issue：

```
TASK-P0-CONSENSUS-ENGINE-001: result_file exists but status not closed
```

**成因**：§3.6 校正了 P0 的 `result_file`（原指向不存在的 `collaboration/results/…`，
实际在 `hermes_target/`）。校正前该路径不存在，控制器不会把它当结果工件；校正后它成了真实工件，
于是「有结果文件但状态未闭合」这个**原本被掩盖的**不一致被暴露出来。

**未处理，理由如实说明**：

1. P0 的 assignee 是 `codearts_agent`、reviewer 是 `user`，且其交付本质是
   「本地准备 100% 完成 / 远程 Hermes 执行 0%」——`planning`（已排期、未开工）虽是
   CLI 枚举中唯一可表达「未闭合」的合法值，但如实反映的是「本地已备妥、远端待执行」；
   转 `completed` 会**失真**（远程执行确实没做）。
2. 其结果文件仍缺 `验证结果` / `风险` / `回滚` 三章节，
   转 `completed` 也会被 `state_manager` 的结果工件门禁拦下。
3. 本次沙箱策略**禁止执行 `hermes_target/` 外部副本的代码**，
   P0 的两条 acceptance_commands（跑 `hermes_target/hermes_agent/tests/unit/test_consensus_engine.py`
   与导入 `hermes_agent.engines`）无法在本环境复核。
   路径存在性已用只读方式确认：新路径两个文件均存在，旧路径两个均不存在。

结论：这是**遗留项**，不是本任务的收口缺口。已在校正说明、P0 工单与本报告中留痕，
待其 assignee 在 Hermes 环境执行远程步骤后收口。

---

## 6. 风险与回滚

| 风险 | 说明 | 回滚点 |
|---|---|---|
| 覆盖率口径变化 | omit 名单变更会改变 TOTAL 数字 | `git checkout pyproject.toml` |
| sqlite 事务语义 | 若只包 `closing` 会丢数据 | `test_write_is_persisted` 用例守护 |
| CI 门禁口径变更 | 两处门禁统一到阈值 85 + `coverage report` | `git checkout .github/` |
| state 重建 | 旧 state 文件被移出 | `logs/collaboration_state.json.stale-20260513.bak` |
| 新增 `pack convert` 子命令 | 草稿为**待审状态**，非可直接激活的正式 Pack | 移除 `_cli_main.py` 中的注册分支 |
| `react_convert` 移出 omit | 该文件现在计入覆盖率统计 | `git checkout pyproject.toml` |

### 已知限制

1. `pack convert` 产出的草稿只覆盖 `PromptPackV2` 的部分段（`metadata` / `domain` /
   `example_library` / `workflow` / `quality_metrics` / `runtime_config`），
   缺 `generation_params` / `optimization` / `performance_tracking` / `collaboration` / `system_prompt`。
   `PromptPackV2.from_dict` 对缺失段用默认值兜底因此能过闸，但草稿仍是**半成品**；
   要成为可激活的正式 Pack 还需一次目录式物化。
2. `_cli_main.py` 已达 2606 行，本次新增约 30 行。巨型 CLI 的拆分仍是独立任务。
3. `TASK-P0-CONSENSUS-ENGINE-001` 仍处于 `planning`，被 controller 报出一条
   `result_file exists but status not closed`（详见 §5.7）。其结果文件还缺
   `验证结果` / `风险` / `回滚` 三个收口必需章节；其两条 acceptance_commands 需在
   Hermes 环境由 assignee（`codearts_agent`）执行——本环境沙箱策略禁止运行
   `hermes_target/` 外部副本代码，故本次**未能复核**这两条命令。该任务是向
   **外部 Hermes 机器**的移植，不在本任务范围内。
4. `logs/` 整体被 gitignore，state 无版本历史，误操作只能靠 `logs/collaboration_state.json.stale-*` 备份恢复。

---

## 7. 变更文件清单

| 文件 | 变更 |
|---|---|
| `pyproject.toml` | 还原 `[tool.pytest.ini_options]` + `[tool.coverage.*]`；omit 移除 react_convert |
| `.github/actions/coverage-gate/action.yml` | **新增**——覆盖率门禁唯一事实源 |
| `.github/workflows/test.yml` | 覆盖率门禁改用 composite action |
| `.github/workflows/mypy-gate.yml` | 覆盖率门禁改用 composite action（阈值 80 → 85，方法统一） |
| `ai_collab/pack/market_store.py` | 新增 `_connect()`；15 处连接点替换 |
| `ai_collab/cli/react_convert.py` | 抽出 `convert_requirement_file()`；`main()` 返回退出码 |
| `ai_collab/cli/_cli_main.py` | 注册 `pack convert` 子命令 + `_handle_convert_command` |
| `ai_collab/state_manager.py` | 修 workspace 优先级 bug（2 处） |
| `tests/unit/pack/test_market_store_connection.py` | **新增**（8 用例） |
| `tests/unit/cli/test_react_convert_cli.py` | **新增**（18 用例） |
| `tests/unit/pack/test_market.py` | 7 处测试侧连接泄漏修复 |
| `collaboration/tasks/TASK-P1-GOV-CONVERGE-001.md` | **新增**——本任务工单 |
| `collaboration/tasks/TASK-P0-CONSENSUS-ENGINE-001.md` | 契约漂移校正 |
| `logs/claude-code/2026-10/2026-10-22_coverage-gate-restore.md` | 开发日志 |

---

## 8. 后续建议

1. **P0 — 产品侧确认「Owner 需求」业务线是否还在**。`react_convert` 的触发面
   （Owner requirement form）在当前仓库已不存在；若该业务线已废弃，
   正确的处置是连同 `pack/react_converter.py` 一起删除，而非维护现状。代码本身给不出答案。
2. **P1 — 拆分 `_cli_main.py`**（2606 行），优先按领域提取子命令模块。
3. **P1 — `logs/` 的版本化**。state 与 session registry 是运行时权威却完全无版本历史，
   建议对 `logs/collaboration_state.json` 做例外追踪，或迁到 `data/` 下。
4. **P2 — 补 `TASK-P0-CONSENSUS-ENGINE-001` 的结果章节**（`验证结果` / `风险` / `回滚`）
   并在 Hermes 环境跑通其两条 acceptance_commands，使其满足收口门禁、消除
   `result_file exists but status not closed` 漂移信号。
5. **P2 — 结果工件头部格式**：`result_consistency_audit` 要求结果文件前 40 行内存在
   可解析的状态行（如 `**状态**: completed`），而 `state_manager` 的收口门禁**不查这一项**。
   两套校验各管一半，建议在结果文件模板里固定加上状态行，
   或让收口门禁一并校验，避免「门禁通过但一致性审计报 unparseable」。
6. **P2 — 统一 `ai_collab/cli/` 下 9 个独立脚本的入口形态**：
   8 个未注册进主 CLI 的兄弟脚本同样没有统一入口。
