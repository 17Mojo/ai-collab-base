# 开发记录：治理面收敛 Phase 2（sqlite 泄漏 / 双门禁统一 / react_convert 接入 / state workspace 修复 + TASK→RESULT→ACK 闭环）

## 记录信息

- **任务ID**: TASK-P1-GOV-CONVERGE-001
- **change_id**: bugfix/no-spec
- **AI类型**: Claude Code（AGENT_EXEC）
- **审核者**: user
- **时间**: 2026-10-22
- **分支**: `refactor/slimming-2026-09-20`
- **前置日志**: `2026-10-22_coverage-gate-restore.md`（Phase 1：还原被误删的 pytest/coverage 配置）
- **结果报告**: `collaboration/results/RESULT-P1-GOV-CONVERGE-001.md`

---

## Phase 1 遗留项与本次处置

Phase 1 结束时留下四项待决，全部由用户点名要求走正式闭环处理：

| 遗留项 | 用户原话 | 本次处置 |
|---|---|---|
| sqlite 泄漏 | "要不要我现在修（15 处，需逐个核对提交语义）" | 修，并逐处核对事务语义 |
| 双覆盖率门禁 | "两套覆盖率门禁要不要统一为单一口径" | 统一为单一口径（composite action 作 SSOT） |
| react_convert | "是孤儿脚本…删除还是接入主 CLI" | 接入主 CLI（先证伪「孤儿」判断） |
| state 陈旧 | "所有 CLI 治理计数器读 0 是这个原因" | 修代码而非改数据 |

---

## 1. sqlite3 泄漏：先做语义实验，再动代码

### 1.1 问题定性

`sqlite3` 的 `with conn:` 只管理**事务**（成功提交 / 异常回滚），**不关闭连接**。
`ai_collab/pack/market_store.py` 15 处写成 `with sqlite3.connect(...) as conn:`，每次调用泄漏一个连接。

### 1.2 直觉修法会丢数据（关键陷阱）

最直觉的修法是包一层 `contextlib.closing`。但在动手前先做了三路对照实验：

| 写法 | 落盘行数 | unclosed 告警 |
|---|---|---|
| 现状 `with sqlite3.connect(...) as conn:` | 1 | 1 |
| 仅 `closing(...)` | **0（数据丢失）** | 0 |
| `closing(...)` + `with conn:` 事务上下文 | 1 | 0 |

`closing` 包在外层时，`with conn:` 的事务上下文被吞掉——`conn.__exit__` 不会执行，
`COMMIT` 从未发生。**只包 closing 的写法是"把泄漏换成丢数据"，比原 bug 更危险。**

### 1.3 最终方案

新增模块级 `_connect()` 上下文管理器，事务语义与关闭语义分层：

```python
@contextmanager
def _connect(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()
```

退出顺序「先提交/回滚，后关闭」，异常路径同样关闭。15 处调用点全部替换为 `with _connect(...)`。

### 1.4 mypy 副作用

加了这个未标注类型的 helper 后，`conn` / `cursor` 退化为 `Any`，
mypy 立刻报 3 处 `Returning Any from function declared to return bool`（market_store.py:236/253/492）。
修法是补 `from __future__ import annotations` + `from collections.abc import Iterator` +
`-> Iterator[sqlite3.Connection]`，让 `conn` 保持具体类型。

### 1.5 测试侧同模式泄漏

`tests/unit/pack/test_market.py` 也有 7 处 `with sqlite3.connect(temp_db) as conn:`。
这些是**测试代码**，同样会触发 `ResourceWarning`，且会污染同文件的告警断言窗口
（首轮写 `ResourceWarning` 断言时在文件内跑失败、单跑通过——跨测试 GC 污染）。
修法同样是 `with closing(sqlite3.connect(temp_db)) as conn, conn:`（保留 `conn:` 事务上下文，
因为其中有 INSERT 用例）。

### 1.6 双向守护

新增 `tests/unit/pack/test_market_store_connection.py`（8 用例）同时防两个方向：

- **防泄漏回归**：monkeypatch `sqlite3.connect` 捕获连接对象，退出后断言 `sqlite3.ProgrammingError`
- **防数据丢失**：`test_write_is_persisted` / `test_write_visible_from_a_fresh_connection` / `test_delete_is_persisted`

中途踩了两个坑：
1. `test_connection_closed_even_when_operation_raises` 报 `AttributeError: 'PackMarketStore' object has no attribute '_connect'`
   —— `_connect` 是**模块级函数**不是方法，改写为 `from ai_collab.pack.market_store import PackMarketStore, _connect`
2. 回滚断言写成 "DID NOT RAISE OperationalError" 是错的——SQLite 的 DDL（CREATE TABLE）
   在 legacy transaction 模式下**自动提交**，所以表还在、只有 INSERT 被回滚。
   实测后改为断言「表存在但 0 行」。

**结果**：ResourceWarning 从 405 条 → **0 条**。

---

## 2. 双覆盖率门禁统一

### 2.1 为什么不是"删掉一个"

原状：

| 工作流 | 阈值 | 测量方法 |
|---|---|---|
| `test.yml` | 85% | `coverage report --fail-under`（语句覆盖） |
| `mypy-gate.yml` | 80% | 解析 `coverage.xml` 的 `line-rate`（行覆盖） |

宽松那套（80%）让严格那套（85%）的失败完全不可见。

**但没有简单合并成一个工作流**——commit `01f67c2` 恰恰证明了单一工作流承载单一门禁有单点故障风险
（test.yml 自身步骤故障 → 门禁整体失效）。所以保留双工作流做互为备份，
把**阈值与测量方法**抽到 composite action 作唯一事实源。

### 2.2 实现

新增 `.github/actions/coverage-gate/action.yml`：

- `inputs.threshold` 默认 `"85"`
- 执行 `coverage report --fail-under="${THRESHOLD}"`，失败时 `::error::` 标注

`test.yml` 与 `mypy-gate.yml` 均改为 `uses: ./.github/actions/coverage-gate`。
两处现在口径完全一致（85 + `coverage report`），既不会互相掩盖，也各自有独立的触发路径。

### 2.3 口径说明（避免以后再混）

`coverage report --fail-under=N` 是**语句覆盖**（statement coverage），
`coverage.xml` 的 `line-rate` 是**行覆盖**（line coverage）。两者数字不同，**不能混用**。
本次统一后，门禁只看语句覆盖，与 CLAUDE.md「经验 3」中 87% 那一组数字同源。

---

## 3. react_convert：先证伪「孤儿」判断

### 3.1 初判被推翻

初判依据是「123 行、0% 覆盖、`_cli_main.py` 未 import」。派 Explore 子代理做跨文件考古后，
结论是**判断错误**：

- 它是 `ai_collab/pack/react_converter.py`（**93% 覆盖**、有已归档 OpenSpec 规格背书）的
  **唯一生产调用方**
- 规格 `2026-03-11-add-pack-runtime-style-react-conversion-layer` 仍在
  `collaboration/guides/OPENSPEC_PACK_MARKET_WORKFLOW.md:217-224` 被引用
- 同目录 8 个兄弟脚本**全部**有 `tests/unit/cli/test_*_cli.py` 专属测试，唯独它没有

所以真正被 omit 掩盖的缺口不是「文件该不该存在」，而是「**没接入主 CLI + 没有测试**」。
**选「接入」而非「删除」**。

### 3.2 实施

1. `ai_collab/cli/react_convert.py` 抽出 `convert_requirement_file(requirement_path, output_dir, verbose=False) -> int`
   ——转换逻辑从 argparse `main()` 里解耦出来，可测试、可被主 CLI 调用
2. 新增 `tests/unit/cli/test_react_convert_cli.py`（18 用例）
3. `ai_collab/cli/_cli_main.py` 注册 `pack convert` 子命令 + `_handle_convert_command`
4. 从 `[tool.coverage.run] omit` 移除该文件：**0% → 83%**（128 语句）

### 3.3 两步闭环字段对齐

`draft_pack.json` 的 `metadata.pack_id` / `metadata.pack_name` 与 `pack import` 读取的字段一致，
所以 `pack convert` → `pack import` 可串成两步闭环。测试里专门断言了这一点。

### 3.4 遗留的产品问题（代码给不出答案）

已归档规格的触发面是「Owner 需求表单」，但当前仓库 `products/` 下只有 `vscode-extension`，
**该触发面已不存在**。若「Owner 需求」这条业务线已废弃，
正确处置是连同 `pack/react_converter.py` 一起删除，而不是维护现状。
这需要产品侧决策，已列入 RESULT 的后续建议 P0。

---

## 4. state workspace 陈旧：根因是代码 bug，不是数据过期

### 4.1 根因

`state_manager.py::_merge_states_with_latest` 的 workspace 优先级是
`local_norm → latest_norm → self.workspace_path`——**真实路径永远轮不到**。
所以任何 CLI 写操作都会把磁盘上的陈旧值原样保留，**CLI 从不自动纠正**。

危害不止于显示：`scripts/reconcile_state_drift.py:71` 与
`scripts/task_controller_daemon.py:146` 都读 `state["workspace"]` 来定位 RESULT 文件，
路径错了就**静默找不到结果工件**，漂移永远不会触发。

### 4.2 修法

两处：
- `_normalize_state`：把 `workspace` 提升为不受磁盘旧值覆盖的字段
- `_merge_states_with_latest`：`self.workspace_path` 优先于磁盘值

**修代码而不是改数据**——不改代码的话，任何 CLI 写操作都会把陈旧值写回去。

### 4.3 重建方式

遵守「禁止直接编辑 `logs/collaboration_state.json`」（`rules/archive/claude_code_memory.md:49,60`、
`PROTOCOL.md:385`）：旧文件备份为 `logs/collaboration_state.json.stale-20260513.bak` 后移出，
由 CLI 以正确的 workspace 重建，再注册两个任务。

旁证旧文件是手工产物：它缺 CLI 必写的 5 个 key，且 `last_updated` 是整点整秒
`2026-05-13T00:00:00.000000`（CLI 写的是 `datetime.now().isoformat()`，带微秒）。

### 4.4 顺带校正 P0 任务的契约漂移

`TASK-P0-CONSENSUS-ENGINE-001.md` 有三处漂移：

| 字段 | 原值 | 实际 |
|---|---|---|
| `result_file` | `collaboration/results/RESULT-P0-CONSENSUS-ENGINE-001.md`（不存在） | `hermes_target/RESULT-P0-CONSENSUS-ENGINE-001.md` |
| `acceptance_commands[0]` | `tests/unit/hermes/test_consensus_engine.py`（不存在） | `hermes_target/hermes_agent/tests/unit/test_consensus_engine.py` |
| `status` | `ready_to_implement`（**不在 CLI 枚举内**） | `planning`（语义最接近：已排期、未开工） |

`ready_to_implement` 不是合法值这点，`ai_collab/state_manager.py` 的 `TaskStatus` / `status_map` /
argparse choices 三处都没有——CLI 设不进去。**这说明本任务自己也不能用这个值**，
已一并改成合法值。

---

## 5. 正式闭环：TASK → RESULT → ACK

### 5.1 流程

| 步骤 | 命令 | 结果 |
|---|---|---|
| 1 | `tasks update --task-id TASK-P1-GOV-CONVERGE-001 --status testing` | 成功 |
| 2 | `tasks update --task-id TASK-P1-GOV-CONVERGE-001 --status completed` | 成功，**结果工件门禁通过** |
| 3 | `ack --task-id ... --ai claude_code --status ok --result-file ...` | `C.ACK\|task=...\|status=ok\|result=...` |
| 4 | `receipt --dry-run` | candidate=0（预期，见下） |

第 2 步触发 `state_manager._validate_result_artifact_for_completion`：
逐条比对 6 个 acceptance_commands（空白归一化后）+ 检查三个必需标记
（`执行命令` / `测试结论` / `风险`）+ 拒绝负向标记。一次通过。

### 5.2 receipt 候选数为 0 是预期终态

`scripts/agent_receipt_bridge.py:212` 的候选筛选条件是 `task.get("status") != "testing"` 即跳过。
自动回执桥接是给「停在 testing 的任务」兜底的；本任务已显式收口，**没有残留**。
不需 `--reclose`（那会对已完成任务重复处理）。

### 5.3 收口后状态

```
[任务统计]  总任务数: 2 / 活跃任务: 1 (CodeArts Agent) / 已完成任务: 1
[治理健康]  ACK bridge 记录: 1 / 显式 ACK 证据: 1 / 可闭环 ACK: 1 / Claude fallback 残留: 0
```

对比修复前：总数 0 / 活跃 0 / ACK 记录 0。**治理计数器现在反映真实任务数**，
这正是用户指出的「读 0 不是真的没有任务」的诉求闭环。

---

## 6. 收口后漂移检测：查出并修掉一个**自身**缺陷 + 暴露一条 P0 遗留漂移

按项目规则（`state-drift-detector` 技能：「每次 closeout 前必须检测状态漂移」）跑了三轮检测。

### 6.1 查出自身缺陷：RESULT 头部缺状态行 → `unparseable_result_header`

首次跑 `tasks audit-result-consistency`，本任务被判为：

```
issue: TASK-P1-GOV-CONVERGE-001 type=unparseable_result_header state=completed result=<unparseable>
```

`result_consistency_audit.parse_result_header_status`（`ai_collab/result_consistency_audit.py:94-105`）的规则：
扫描结果文件**前 40 行**，找第一个匹配

```
^(?:[-*+]\s+|\d+\.\s+)?\*{0,2}(status|状态|任务状态|执行状态|当前…状态)\*{0,2}\s*[:：]\s*(.+)$
```

的行，并要求其值能归一化成任务状态。

我最初的 RESULT 元数据块只有 `完成时间` / `报告版本` / `执行者` / `审核者` / `change_id`，
**没有任何一行含 status/状态 键** → 扫完 40 行返回空串 → unparseable。

**关键认识：这是两套独立校验。**
`state_manager._validate_result_artifact_for_completion`（收口门禁）只查
「三个必需标记 + acceptance_commands 逐条比对 + 负向标记」，**不查状态头**；
`result_consistency_audit` 查状态头，**不查 acceptance_commands**。
所以「门禁通过」不等于「一致性审计通过」——两道闸各管一半。

修法：加一行 `**状态**: completed`。归一化后与 state 终态一致，审计转绿。
顺带验证了归一化规则：写 `✅` / `正常` / `complete` 都会归一化成 `completed`，
但写 `testing` 会触发 `terminal_status_mismatch`。

**这条已列入 RESULT 的后续建议**：结果文件模板应固定带状态行，
或让收口门禁一并校验，避免「门禁绿但审计红」。

### 6.2 暴露一条 P0 遗留漂移（非本次引入）

```
controller --once --dry-run →
  TASK-P0-CONSENSUS-ENGINE-001: result_file exists but status not closed
```

**成因是我 §4.4 的契约校正把它「暴露」了**，不是本次引入的新问题：
校正前 `result_file` 指向不存在的 `collaboration/results/RESULT-P0-CONSENSUS-ENGINE-001.md`，
控制器不会把它当结果工件；校正后指向真实的 `hermes_target/RESULT-P0-CONSENSUS-ENGINE-001.md`，
于是「有结果工件但状态未闭合」这个**原本被掩盖的**不一致浮出来了。

**未处理，理由如实说明**：
1. P0 的 assignee 是 `codearts_agent`、reviewer 是 `user`，交付本质是
   「本地准备 100% / 远程 Hermes 执行 0%」。转 `completed` 会**失真**。
2. 其结果文件仍缺 `验证结果` / `风险` / `回滚` 三章节，转 `completed` 也会被收口门禁拦下。
3. **本次沙箱策略禁止执行 `hermes_target/` 外部副本的代码**——
   尝试跑 P0 的两条 acceptance_commands 时被 auto-mode classifier 拒绝
   （理由：需用户显式授权该外部来源）。因此**未能复核**这两条命令。
   改用只读方式确认路径事实：新路径两个文件均存在（`ls` 通过），
   旧路径两个均不存在（`ls` 报 No such file or directory）——校正本身是**对的**。

### 6.3 漂移检测最终结果

```
reconcile_state_drift.py --workspace $PWD --fail-on-drift → exit 0
  drift_count=0  applied_count=0  error_count=0
tasks audit-result-consistency → audited=1 consistent=1 mismatch=0 unparseable=0 missing_result=0
controller --once --dry-run → task_contract_checked=1 invalid=0 error_count=0
  （唯一 issue 是 §6.2 的 P0 遗留项）
```

---

## 7. 验收（6 条命令全部重跑）

| 命令 | 结果 |
|---|---|
| `python3 -m pytest -q` | **2686 passed / 6 skipped**（40.6s） |
| `python3 -m ruff check .` | **All checks passed!** |
| `python3 -m mypy ai_collab` | **Success: no issues found in 99 source files** |
| `python3 -m coverage report --fail-under=85` | **exit 0**（TOTAL 14720 / 1660 miss / **89%**） |
| `python3 -m ai_collab.cli tasks validate-contract --scope all --strict` | **checked=2 skipped=0 invalid=0** |
| `python3 -m ai_collab.cli status` | 总数 2 / 活跃 1 / 已完成 1 |

6 条 skip 均为环境依赖，非失败：
`tests/unit/test_database_indexes.py`（缺 `local-backend/data/client_tokens.db`）+
`tests/integration/test_studio_integration.py` ×5（本地后端未在 127.0.0.1:8000 运行）。

### 6.1 一次中途失败及处置

首次合并跑验收命令时进程被 kill（exit 137），`.coverage` 数据被清空，
随后 `coverage report` 报 "No data to report"。处置：**分步重跑**——
先单独生成覆盖率数据，再单独跑门禁。以后不要把「生成数据」和「读数据」塞进同一条长命令。

---

## 8. 未处理项（诚实标注）

1. `_cli_main.py` 已达 2606 行（本次 +30 行），拆分是独立任务
2. `TASK-P0-CONSENSUS-ENGINE-001` 仍在 `planning`，被 controller 报
   `result_file exists but status not closed`（见 §6.2）。需补 `验证结果` / `风险` / `回滚`
   三章节 + 在 Hermes 环境跑通其两条 acceptance_commands 才能收口。
   **本次未能复核那两条命令**——沙箱策略禁止执行 `hermes_target/` 外部副本代码
3. `ai_collab/context/store.py` 有 `close()` 与 `__enter__`/`__exit__`，但**只有测试消费**，
   不是生产泄漏点，未改动
4. `ai_collab/cli/` 下另有 8 个未注册进主 CLI 的独立脚本，同样没有统一入口
5. `logs/` 整体被 gitignore（`.gitignore:39`），state 无版本历史
6. **结果工件头部格式没有统一约束**：收口门禁（`state_manager`）不查状态行，
   一致性审计（`result_consistency_audit`）查状态行不查 acceptance_commands。
   建议把状态行写进结果文件模板，或让收口门禁一并校验

## 9. 经验沉淀（对应 CLAUDE.md 三条经验）

- **经验 1**（先看测试在守护什么）：`market_store.py` 的连接改动先查 `tests/unit/pack/test_market.py`
  的守护范围，发现其中 7 处同模式泄漏才一并修掉；新增用例同时防泄漏与防数据丢失两个方向
- **经验 2**（字段错配要系统性排查）：本轮发现 `ready_to_implement` 不在 `TaskStatus` 枚举，
  立即查 `state_manager.py` 的 `TaskStatus` / `status_map` / argparse choices 三处，
  确认是同一个枚举问题而非单点笔误，同步修掉自己任务的 frontmatter
- **经验 3**（commit 不撒谎）：覆盖率从 83% → 89% 是**还原误删配置**的结果，
  不是新增测试刷出来的数字——本轮真实新增测试 26 个（+2686 vs 2660），
  其余来自 omit 口径恢复。若后续提交，分开说明这两部分
