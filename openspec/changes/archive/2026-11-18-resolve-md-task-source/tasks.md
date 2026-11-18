# Implementation Tasks

> 凡勾选者必须附**实测证据（命令 + 关键输出）**，不写「已完成」了事。
> 证据按编号 E1–E8 引用，集中列在文末。

## Phase 0 · 立项与隔离

- [x] 0.1 从 `origin/main @ 64c85f7` 开独立分支，确认主工作区在途改动零影响（E1）
- [x] 0.2 产出 `proposal.md` / `specs/task-contract/spec.md` 增量 / `tasks.md`（E1）
- [x] 0.3 产出工单 `TASK-RESOLVE-MD-TASK-SOURCE-001.md`，带 `session_id` / `model_id`（E1）
- [x] 0.4 `openspec validate resolve-md-task-source --strict` 零错误（E1）

## Phase 1 · 代码：同步入口

- [x] 1.1 新增 `ai_collab/task_md_sync.py`：`parse_frontmatter` / `collect_task_files` / `declared_identity`（E2）
- [x] 1.2 `StateManager.sync_tasks_from_md()` 只写 md 已声明字段；缺身份的留空由 `resolve_identity` 判 legacy/partial（E3）
- [x] 1.3 同步方向单向，不回写 md；按 md 的 `created_at` 覆盖；记录 `md_sync` 元数据（E4）
- [x] 1.4 `scripts/verify_task_file_contracts.py` 两处登记调用补传 `session_id` / `model_id`，`parse_frontmatter` 改为复用新模块（E2）

## Phase 2 · 代码：CLI 与审计披露

- [x] 2.1 CLI 加 `tasks sync-from-md`，支持 `--dry-run`，输出同步/跳过/未变条数（E2）
- [x] 2.2 `audit_task_identity()` 返回追加 `input_source`：有同步记录给出时间与条数，无记录明确写「未同步过 md」（E5）
- [x] 2.3 `tasks migrate-identity` 打印来源说明，不改既有六项计数的位置与名称（E5）

## Phase 3 · 验证

- [x] 3.1 在账本为空的新 clone 上同步：`total` 从 0 变为磁盘 md 数（E4）
- [x] 3.2 不编造：只写 `session_id` 的 md 同步后 `model_id` 为空、判 `partial`；历史 md 判 `legacy`（E3）
- [x] 3.3 幂等：连续同步两次 `tasks` 内容 sha256 不变；md 文件 sha256 前后不变（E4）
- [x] 3.4 新增 10 条用例覆盖上述三点与 `input_source` 两态（E6）
- [x] 3.5 全套 pytest 与干净基线同环境对照；ruff format / check（E6）

## Phase 4 · 收口

- [x] 4.1 `PROTOCOL §7.6` 写清标准流程 sync-from-md → migrate-identity 及四条约束（E7）
- [x] 4.2 `known_gaps.json` N26 → closed，补实测证据（E7）
- [x] 4.3 结果报告四段 + 状态行 + 6 条 `acceptance_commands`（E7）
- [x] 4.4 提交带 pathspec；PR；declare-commit（**40 位完整 sha**）；归档；`validate --archived --strict`（E8）

## 实测证据

### E1 · 隔离与工件

```
$ git branch --show-current && git rev-parse --short HEAD
fix/resolve-md-task-source-2026-11-18
64c85f7                                    # == origin/main

$ git -C /Users/raymondna/Documents/AI-collab/ai-collab-base status --porcelain | wc -l
153                                        # 主工作区在途，全程未变

$ openspec validate resolve-md-task-source --strict
Change 'resolve-md-task-source' is valid
```

工单由 CLI 注册，身份如实声明、路由键由注册表反查：

```
身份: session_id=sess-resolve-md-source-20261118 model_id=deepseek/v4.1-flash
路由键来源: registry（assignee=claude_code）
```

### E2 · 代码落点

```
新增 ai_collab/state_manager.py::sync_tasks_from_md()  — 单事务提交，dry_run 不写盘
新增 ai_collab/task_md_sync.py                         — 纯函数：解析/挑文件/取已声明身份
CLI: tasks sync-from-md [--dry-run] [--tasks-dir]
CLI: tasks migrate-identity 打印 input_source

$ grep -n "session_id=fm.get" scripts/verify_task_file_contracts.py
108:                session_id=fm.get("session_id"),
109:                model_id=fm.get("model_id"),
126:                session_id=fm.get("session_id"),
127:                model_id=fm.get("model_id"),
```

`TestRegistrationPath` 用 AST 遍历两个登记调用点，断言两者的 keyword 均含
`session_id` / `model_id`——防止以后有人再次「顺手」漏掉。

### E3 · 不编造

```
$ pytest tests/unit/test_task_md_sync.py -q
..........                                             [100%]
10 passed in 0.09s
```

关键用例：

- `test_partial_never_infers_model_id`：md 只有 `session_id` → 账本 `model_id == ""`，判 `partial`，
  `invalid == 0`，不得从任何字段推导。
- `test_declared_and_legacy`：切点后完整身份判 `declared`；切点前无身份判 `legacy`；
  `missing` / `invalid` 均为 0。
- `test_created_at_comes_from_md_not_sync_time`：回归用例。`register_task` 不接受 `created_at`，
  同步时若用当前时间会把 2026-10-24 的历史工单误判 `missing`；本例断言账本保留 md 的日期。

### E4 · 同步结果、幂等与单向

```
$ python3 -m ai_collab.cli -w . tasks sync-from-md --dry-run
md 工单同步: 预演 source=28 created=26 updated=0 unchanged=2

$ python3 -m ai_collab.cli -w . tasks sync-from-md
md 工单同步: 已写入 source=28 created=26 updated=0 unchanged=2

$ python3 -m ai_collab.cli -w . tasks migrate-identity
身份迁移审计: scope=all apply=False cutoff=2026-11-16 total=29
  declared=3 partial=0 legacy=25 missing=1 invalid=0
  输入来源: 账本源自 md 同步（2026-11-18T07:58:01.989565，28 条）
```

`total=29 > synced_count=28` 的差值来自 1 条无对应 md 的本机条目，同步不删除它。

幂等与不回写（任务内容哈希，非文件字节哈希）：

```
tasks 内容 sha256 before: 095bbb5478ffac2a
tasks 内容 sha256 after : 095bbb5478ffac2a       → 幂等 PASS
md 集合 sha256  before : 16040211017f448c
md 集合 sha256  after  : 16040211017f448c       → 未回写 PASS
重复同步: created=0 updated=0 unchanged=28
```

账本文件整体 sha256 会变（`md_sync.synced_at` 每次刷新），这是审计信息，
不牺牲它换字节幂等——proposal 验收标准第 4 条已同步更正。

### E5 · 来源披露两态

```
未同步过:
  输入来源: 未同步过 md；审计仅覆盖当前账本，不能解释为全量
同步后:
  输入来源: 账本源自 md 同步（2026-11-18T07:58:01.989565，28 条）
```

用例 `test_unsynced_state_is_explicit` / `test_synced_state_reports_count_and_time`
分别守护两态；`test_ledger_entry_without_md_is_not_deleted` 守护「只补不删」。

### E6 · 全套对照与静态检查

| 侧 | 全套 pytest（同环境同命令） |
|---|---|
| 干净基线 `64c85f7`（临时 worktree） | 3189 passed, 8 skipped |
| 改动分支 | **3199 passed, 8 skipped** |

```
$ /Users/raymondna/miniforge3/bin/python3 -m ruff format --check .
333 files already formatted
$ /Users/raymondna/miniforge3/bin/python3 -m ruff check .
All checks passed!
```

环境说明：全套须带 `PYTHONPATH=/tmp/noshim`（前置空 `sitecustomize.py`），
否则沙箱 `mkdir` 代理会让全部 fixture 崩成 error。

### E7 · 收口工件

- `PROTOCOL §7.6` 新增「任务事实源与身份审计流程」，含标准流程与四条约束。
- 中途改 PROTOCOL 触发 preflight「必读清单内容已变更（需重读）」→ FAIL。
  读回确认 §7.6 落盘正确后，用 `sessions ack-reads` 唯一入口重新声明：
  `declared: 4 verified: 4`；复跑六项全 PASS。
- `known_gaps.json` N26 → `closed` / `closed_at: 2026-11-18`，证据 11 条；
  台账 28 条：closed 26 / wontfix 1 / **open 1（N25）**。
- 结果报告 `RESULT-RESOLVE-MD-TASK-SOURCE-001.md` 四段 + 状态行 + 6 条命令。

### E8 · PR 与归档

```
PR #76: https://github.com/17Mojo/ai-collab-base/pull/76
合入提交（40 位完整 sha）: face8ddaba0e95ad6b125a788e6fbcf5a439f98f
登记表: chore(governance): 登记本 change 的合入提交 face8dd
preflight 复跑: 边界后合并提交 7 个，未登记 0 个；六项全 PASS
归档: 2026-11-18-resolve-md-task-source（specs/task-contract/spec.md +4 requirements）
openspec validate --archived --strict: 8 passed, 0 failed
```

CI：Bandit / python-tests ×3 / mypy 均为既有红灯（PR #72–#75 同集合）。
本 change 曾**新引入**一条 mypy error（`task_md_sync.py:16` import yaml 缺 stub），
CI 从 3 errors/1 file 变为 4 errors/2 files；补 `# type: ignore[import-untyped]`
后恢复为既有 3 errors/1 file，未带着新增错误合入。
PR body 曾因 shell 反引号解析吞掉 `logs/`，已用 `--body-file` 重写并复核。
