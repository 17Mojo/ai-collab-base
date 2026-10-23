---
task_id: TASK-P1-GOV-CONVERGE-001
change_id: bugfix/no-spec
status: completed
priority: P1
assignee: claude_code
assignee_role: AGENT_ARCH
reviewer: user
status_updated_at: 2026-10-22T16:45:00+08:00
primary_skill: backend-architect
support_skills:
  - testing
  - documentation
created_at: 2026-10-22T16:30:00+08:00
acceptance_commands:
  - "python3 -m pytest -q"
  - "python3 -m ruff check ."
  - "python3 -m mypy ai_collab"
  - "python3 -m coverage report --fail-under=85"
  - "python3 -m ai_collab.cli tasks validate-contract --scope all --strict"
  - "python3 -m ai_collab.cli status"
result_file: collaboration/results/RESULT-P1-GOV-CONVERGE-001.md
---

> **2026-10-22 收口记录**
>
> - 状态流转：`planning` → `implementing` → `testing` → `completed`（全部经 CLI 驱动）
> - 收口时刻提交 `status: completed` 时触发了 `state_manager._validate_result_artifact_for_completion`
>   结果工件门禁（6 条 acceptance_commands 逐条比对 + 三个必需标记），一次通过
> - 显式 ACK：`C.ACK|task=TASK-P1-GOV-CONVERGE-001|status=ok|result=collaboration/results/RESULT-P1-GOV-CONVERGE-001.md`
> - `receipt --dry-run` 候选数 0：自动回执桥接只接管 `testing` 状态的任务
>   （`scripts/agent_receipt_bridge.py:212`），本任务已显式收口，属预期终态
> - 结果报告：`collaboration/results/RESULT-P1-GOV-CONVERGE-001.md`

# 任务：治理面收敛（覆盖率门禁统一 + state 陈旧修复 + react_convert 接入 + sqlite 泄漏修复）

## 背景

2026-10-22 对 2026-09-20 审计报告做「洞察 vs 真证」现场核验，发现报告本身也带代际漂移，
核验过程中又暴露出四个此前未被任何报告记录的真实缺陷。

其中最关键的一条是：**CI 覆盖率门禁当时是红的**。根因不是业务代码退化，而是一次
ruff 配置清理误删了 `pyproject.toml` 里的 `[tool.coverage.*]` 段。该缺陷被**同一 commit
自身造成的 ruff 步骤故障**遮蔽了一个版本——严格的那套门禁从未被执行到。

## 目标

1. 修复 CI 覆盖率门禁（恢复被误删的配置），并让两套门禁收敛到**同一阈值、同一测量方法**
2. 修复 `logs/collaboration_state.json` 的 `workspace` 陈旧问题（根因是 merge 优先级 bug，
   不是单纯的数据过期）
3. 处置 `ai_collab/cli/react_convert.py`：补测试 + 接入主 CLI `pack convert` 子命令
4. 修复 `ai_collab/pack/market_store.py` 的 sqlite3 连接泄漏（15 处）

## 非目标

- 不重构 `_cli_main.py`（2606 行巨型 CLI 的拆分是独立任务）
- 不删除 `hermes_target/`（TASK-P0-CONSENSUS-ENGINE-001 的工作产物）
  —— **该非目标已于 2026-10-23 失效**：那次噪声清理已删除该目录，
  本工单的范围限制只对本工单当时的执行期有效
- 不改变 `pack/react_converter.py` 的转换逻辑

## 步骤

### Step 1: 还原 pytest / coverage 配置

- [x] 还原 `[tool.pytest.ini_options]`（testpaths / asyncio_mode / strict-markers / markers / filterwarnings）
- [x] 还原 `[tool.coverage.run]` omit + `[tool.coverage.report]`
- [x] 验证：`coverage report --fail-under=85` 从 exit 2（83%）恢复 exit 0（88%）

### Step 2: 统一覆盖率门禁

- [x] 新建 `.github/actions/coverage-gate/action.yml` 作为阈值与测量方法的唯一事实源
- [x] `test.yml` 与 `mypy-gate.yml` 改为调用同一个 composite action
- [x] 消除原先「test.yml 用 coverage report + 阈值 85」与「mypy-gate.yml 用 XML line-rate + 阈值 80」
      的双口径（宽松的一套会掩盖严格的一套）

### Step 3: 修复 sqlite3 连接泄漏

- [x] `ai_collab/pack/market_store.py` 新增 `_connect()` 辅助上下文管理器
- [x] 15 处 `with sqlite3.connect(...)` 全部改为 `with _connect(...)`
- [x] 新增 `tests/unit/pack/test_market_store_connection.py`（8 用例）
- [x] 验证：ResourceWarning 从 405 条降到 9 条

### Step 4: 处置 react_convert

- [x] 抽出 `convert_requirement_file()`，转换逻辑从 argparse 中解耦
- [x] 新增 `tests/unit/cli/test_react_convert_cli.py`（18 用例）
- [x] 注册 `pack convert` 子命令（`_cli_main.py`）
- [x] 从 coverage omit 中移除 `ai_collab/cli/react_convert.py`（0% → 83%）

### Step 5: 修复 state 陈旧

- [x] 修 `state_manager.py::_merge_states_with_latest` 的 workspace 优先级 bug
- [x] 修 `state_manager.py::_normalize_state` 不让磁盘旧值覆盖 workspace
- [x] 重建 state 文件（走 CLI，不直接编辑）
- [x] 注册 TASK-P0-CONSENSUS-ENGINE-001 进 state

## 风险与回滚

| 风险 | 说明 | 回滚点 |
|---|---|---|
| 覆盖率口径变化 | omit 名单变更会改变 TOTAL 数字 | `git checkout pyproject.toml` |
| sqlite 事务语义 | 若只包 `closing` 会丢数据 | 已有 `test_write_is_persisted` 守护 |
| CI 门禁口径变更 | 两处门禁阈值从 80/85 统一到 85 | `git checkout .github/` |
| state 重建 | 旧 state 文件被移走（备份保留） | `logs/collaboration_state.json.stale-20260513` |

## 验收标准

- `pytest -q` 全绿
- `ruff check .` 通过
- `mypy ai_collab` 0 错误
- `coverage report --fail-under=85` 通过
- `tasks validate-contract --scope all --strict` 通过
- `ai_collab.cli status` 的治理计数器反映真实任务数
