# 开发记录：PR #2 复核整改（2026-10-24）——9 条发现全部落地 + 性能根因推翻

## 记录信息

- **任务ID**: TASK-P1-PR2-CODEARTS-REVIEW-001（复核）/ 复核后整改（Claude Code 侧）
- **AI类型**: Claude Code（AGENT_EXEC + AGENT_ARCH）
- **时间**: 2026-10-24
- **分支**: `feat/codearts-collab-wiring`
- **PR**: #2（`feat/codearts-collab-wiring` → `main`）
- **复核结果文件**: `collaboration/results/RESULT-P1-PR2-CODEARTS-REVIEW-2026-10-24.md`（CodeArts 出具，判定「**有条件通过**」，9 条发现）
- **整改结果**: 9 条发现全部落地；6 条验收命令全绿

---

## 一、复核结论与本轮处置

CodeArts（AGENT_TEST）复核判定「有条件通过」，列 9 条发现。作者侧**逐条独立复现**后
全部采纳，无一条驳回：

| # | 发现 | 本轮处置 | 落地位置 |
|---|------|----------|----------|
| 1 | CI 隔离守护只隔离 `HOME`，未清理凭据类环境变量 → 「撤掉打桩仍绿」 | 子进程 env 显式剔除 `OPENCODE_SERVER_PASSWORD` / `OPENCODE_SERVER_USERNAME` / `CODEARTS_KERNEL_PASSWORD` | `tests/unit/test_ci_isolation_guard.py` |
| 2 | 全量套件性能用例超阈值 0.001s；且 PR 门禁**不跑** `tests/perf/` | 根因修复 + 纳入 PR 门禁（见第二节） | `tests/perf/conftest.py`、`tests/unit/test_perf_isolation_guard.py`、`.github/workflows/test.yml` |
| 3 | 重命名路径归一化无守护用例 | 补 `test_dirty_paths_normalize_renamed_entry` | `tests/unit/test_concurrent_guard.py` |
| 4 | 「连续跑两次 → 历史 2 行且每行可解析」无守护断言 | 补 `test_two_runs_append_two_parseable_history_lines` | `tests/unit/test_concurrent_guard.py` |
| 5 | `enabled=false` 降级语义「有实现、有用例、**无需求**」 | spec「CLI 门禁」需求补一条场景 | `openspec/changes/add-concurrent-workspace-guard/specs/concurrent-workspace-safety/spec.md` |
| 6 | PROTOCOL 14.3 笔误 `gitF rev-parse HEAD` | 改为 `git rev-parse HEAD` | `collaboration/PROTOCOL.md` |
| 7 | PROTOCOL 14.5 分层表写 G3「不可阻断」，但实现允许 `foreignChangeSeverity: high` 时阻断 | 表格加注 + 补 G3 例外块 | `collaboration/PROTOCOL.md` |
| 8 | 派单模板/工单把四段契约标为「PROTOCOL §7.3 契约」，而 §7.3 是**绑定规则** | PROTOCOL 新增 **§7.4 结果文件四段契约**（正式定义）+ 所有错引改指 §7.4 | `collaboration/PROTOCOL.md`、`openspec/config.yaml`、`scripts/agent_dispatch_bridge.py` |
| 9 | 工单 R3.2 / R3.3 表述与工具实际用法不符 | 补「契约勘误」小节（原文保留作历史记录） | `collaboration/tasks/TASK-P1-PR2-CODEARTS-REVIEW-001.md` |

---

## 二、发现 #2 的根因被推翻：不是「阈值抖动」，是全局状态文件的无上限增长

复核方把首跑那条 `test_state_update_performance` 失败归因为「**性能阈值边界抖动**」
（0.101s vs 阈值 0.1s）。作者侧实测**证伪**了这个归因。

### 实测过程

1. `test_state_update_performance` 测的是 `StateManager.update_task_status()`。
   顺着写路径读 `ai_collab/state_manager.py`：`update_task_status` →
   `_commit_state_transaction` → `_atomic_write_json` + `_backup_state` + **`_sync_to_global()`**。
2. `_sync_to_global()`（`state_manager.py:838`）把当前 workspace 的状态写进
   **全局**文件 `~/.vscode/ai-collab/collaboration_state.json`
   （路径来自 `VSCodeStateManager.get_global_state_file()`，`state_manager.py:145-149`，
   `os.path.expanduser` 跟随 `HOME`）。写法是**读整份 → 改一条 → 写回整份**。
3. 那个文件按 `workspace_path` 逐条累加、**从不回收**。开发机实测：
   **5,424,838 字节 / 1581 条**，其中 **1578 条是测试自身泄漏的临时目录**
   （pytest 临时目录 + macOS `tempfile.mkdtemp()` 路径），真实工作区只有 **3 条**；
   泄漏条目占总字符数 **95.2%**。
4. 于是「单次状态更新」每次都要把这份 5.4MB 重新序列化一遍。拿真实全局文件的
   **逐字节副本**做隔离复现：单次 update 稳定落在 **0.098~0.103 秒**（死死贴着
   0.1s 阈值横跳）；把 HOME 隔离到空目录后，同一用例只要 **0.0011 秒**——**约 90 倍**。
5. 第一次合成污染（1500 条 × 3000 字符 = 4.76MB）只得到 0.026s，**并不越阈值**；
   换成真实文件的形状才复现——说明「大小」不是关键，**形状**才是。

**结论**：这条基线过去测的是**开发机的历史垃圾清理成本**，不是产品自身开销。
复核方的「阈值抖动」归因只描述了症状，没触及成因。

### 处置：改测量环境，不改阈值

- **阈值不动**（`state_update_single: 0.1` 保持原值）。`openspec/config.yaml` 明写
  「不得为了让门禁变绿而修改测试断言或反向改造产品」——加宽阈值正是反向操作。
- **改测量环境**：`tests/perf/conftest.py` 加 autouse fixture，把 `HOME` / `USERPROFILE`
  指向临时目录（POSIX 跟随 `HOME`、Windows 跟随 `USERPROFILE`，两端都要设）。
  子进程（`python3 -m ai_collab.cli`）继承同一环境，隔离对它们同样成立。
- **把前提钉成机器可检的守护**：`tests/unit/test_perf_isolation_guard.py`
  - 正向：把 ambient HOME 污染成 5MB 全局状态文件后跑性能套件 → 仍必须全绿，
    且 ambient 文件**一个字节都不能被改**（证明隔离生效）；
  - 对照：污染态 / 隔离态的耗时要拉开 **≥ 10 倍**（实测约 90 倍），且隔离态 < 0.1s。
  - **对照用倍率而不是「是否越过 0.1s 阈值」**：污染态实测 0.098~0.103 秒，
    本身就在阈值上下横跳，拿阈值当断言线会写出**必然偶发**的用例。
- **反向验证（mutation）**：把 `tests/perf/conftest.py` 移走 → 守护变红
  （`1 failed, 1 passed`，报「ambient 全局状态文件被改写（原 9627960 字节）」）；
  放回 → `2 passed`。

### 顺带把 `tests/perf/` 纳入 PR 门禁

复核方给的二选一里选 ①（纳入门禁），前提是测量口径已确定且余量够大。实测余量：

- 隔离态单次 update **0.0011s** vs 阈值 0.1s → **约 90 倍**
- `cli_help` 冷启动 0.289~0.322s vs 阈值 1.0s → 约 3 倍（最紧的一项）
- 性能套件整体 0.24~0.27s（连续 10 次），单条 0.02~0.08s

`.github/workflows/test.yml` 新增 `performance-tests` job（独立于 3.10/3.11/3.12 矩阵）。
共享 runner 有机器速度噪声，故给 **2 次重试**——重试不是掩盖回归：测量口径的确定性
由上面的守护用例钉住。

---

## 三、发现 #8：PROTOCOL §7.4 四段契约

PROTOCOL **从未定义**过结果文件的四段格式（所以很多地方才会顺手当成 §7.3 引用，
而 §7.3 实际是绑定规则）。处置：

- 在 `collaboration/PROTOCOL.md` 新增 **§7.4 结果文件四段契约（强制）**，把四段表格、
  状态行要求、`acceptance_commands` 原样出现的要求正式写下来，并指明机器校验实现
  （`TASK_RESULT_REQUIRED_SECTION_GROUPS` / `TASK_RESULT_NEGATIVE_SIGNAL_MARKERS`）；
- 所有错指 §7.3 的地方改指 §7.4（`openspec/config.yaml` 的 `operations.apply.guidance`、
  `scripts/agent_dispatch_bridge.py` 的派单模板）；
- §7.3 本身的 **约 15 处正确引用**（`ai_collab/` 下绑定规则相关）**保持不动**。

---

## 四、发现 #9：工单勘误（原文保留 + 补订正小节）

沿用仓库既有先例（commit `cf7907a`）：**保留原文作为历史记录**，追加
「契约勘误」小节指向真实行为与实测证据。五条订正：

1. **R3.2**：`openspec status` 裸调用直接报错
   `✖ Error: Missing required option --change (or --all ...)`；
   正确写法 `openspec status --change add-concurrent-workspace-guard`
   → `Progress: 4/4 artifacts complete`。
2. **R3.3**：`rules` 顶层是**分组 dict**（proposal/specs/design/tasks），
   **是这些分组「值」**才是 `list[str]`；`operations.*.guidance` 才是直接的 `list[str]`。
   工单原文「rules 与 operations.*.guidance 的值必须是字符串数组」在 `rules` 一项上不准确。
3. **R5.5.3**：grep 的**失败形态**记错了。提交版原形是
   `cat logs/task_dispatch_report.json | grep generated_at`（无 `-E`、无括号）；
   真实失败形态是 **grep 无命中 → rc=1、输出为空**（报告当时只有 `timestamp` 键），
   **不是** shell 语法错误。实测三种写法：
   - `grep -E '"(generated_at|timestamp)"'` → **rc=0 跑通**（工单原文所称不成立）
   - `grep -E 'generated_at|timestamp'` → rc=0（本次修复后的写法）
   - `grep -E (generated_at|timestamp)`（**不加引号**）→ rc=2，
     `syntax error near unexpected token '('`——报的是 `(`，**不是** `)`
   **修复本身正确**，错的只是对失败形态的记录。
4. **第六章**：`§7.3 收口要求` → 四段契约在 **§7.4**（§7.3 是绑定规则）。
5. **frontmatter**：`status: planning` → `completed`（与 DB 实际终态一致）。

> 复核方在结果文件里已自行标注「未能复现该报错」——本轮把成因查清并写进了勘误。

---

## 五、遗留缺陷登记：全局状态文件无上限增长

复核发现 #2 的**根因本身**是一个独立的产品缺陷，本次**只修了测量口径，没有修缺陷**
（那是产品行为变更，需要单独选型）。已登记为独立工单：

- `collaboration/tasks/TASK-P1-GLOBAL-STATE-GROWTH-001.md`（已在
  `logs/collaboration_state.json` 注册，状态 `pending`）
- 记录了实测数据（5.4MB / 1581 条 / 1578 条泄漏 / 95.2% 字符占比）、两条后果
  （无上限增长 + 写放大）、6 条待定设计问题（回收策略 / 回收时机 / 上限兜底 /
  兼容性 / 并发 / 与 VSCode 扩展侧的共享语义）、验收标准与验收命令。
- **明确边界**：`tests/perf/conftest.py` 的 docstring 里写清了「本装置只隔离**测量环境**」，
  全局文件的无上限增长**不在性能基线的修复范围内**——避免后人误以为已经修好。

---

## 六、验收（6 条 acceptance_commands 全部实跑）

| # | 命令 | 结果 |
|---|------|------|
| 1 | `pytest tests/unit/test_concurrent_guard*.py test_project_boundary_guard.py test_consensus_engine_concurrency.py -q` | 52 passed |
| 2 | `pytest tests/unit/test_ci_isolation_guard.py -q` | 3 passed |
| 3 | `pytest tests/ -q` | **3020 passed / 6 skipped** |
| 4 | `python3 -m ruff check .` | All checks passed |
| 5 | `cli tasks validate-contract --scope all --strict` | checked=14 invalid=0；一致性审计 audited=13 consistent=13 |
| 6 | `python3 scripts/scan_secrets_pii.py --workspace .` | no secrets found |

另：`openspec validate add-concurrent-workspace-guard --strict` → valid。

> 第 3 条的 6 条 skipped 均为**环境性跳过**（本地无 `client_tokens.db`、本地后端未起），
> 与本轮改动无关。

---

## 七、下一步

1. 推送本轮提交 → PR #2 重新跑门禁（含新增的 `performance-tests` job）；
2. 门禁全绿后 `gh pr merge 2 --rebase`（main 用 rebase merge 保持线性）；
3. `openspec archive add-concurrent-workspace-guard -y` 归档，生成
   `openspec/specs/concurrent-workspace-safety/spec.md`；
4. 真机 3 平台回归 + 第一个外部用户的执行清单（仓库目前无脚手架，需新建）。

## 八、尚未处理（阻塞中）

**记忆源的两处 §7.3 → §7.4 订正**（`~/.codeartsdoer/memory/<slug>/` 下的
`feedback_dispatch_payload_freshness.md` 与 `project_healthcheck_tooling_debt.md`）
被权限分类器拦下，需要用户**显式点名授权这两个文件**。授权后的动作：
改源 → 跑 `python3 scripts/sync_agent_memory.py` 重生成只读镜像
（当前 `--check` 报 3 个待同步：MEMORY.md / feedback_dispatch_execution_protocol.md /
feedback_result_file_contract.md）→ 复验 `scripts/verify_agent_config_sync.sh` V2/V3 仍 PASS。

**F（覆盖率批次 3）**：用户已明确跳过。
