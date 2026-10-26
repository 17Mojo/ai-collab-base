# RESULT-P1-GLOBAL-STATE-GROWTH-2026-10-26

- **状态**: completed
- **任务**: `TASK-P1-GLOBAL-STATE-GROWTH-001`（全局状态文件无上限增长 + 死条目从不回收）
- **执行**: Claude Code（AGENT_EXEC）　**复核**: CodeArts（AGENT_TEST）
- **分支**: `fix/global-state-reclaim`（基线 `main` @ `71c9eac`）
- **日期**: 2026-10-26
- **工单**: [`collaboration/tasks/TASK-P1-GLOBAL-STATE-GROWTH-001.md`](../tasks/TASK-P1-GLOBAL-STATE-GROWTH-001.md)

---

## 一句话结论

全局状态文件从「只增不减」变成「有判据地回收」：开发机实测 **1589 条 / 5,441,481 字节
→ 3 条 / 44,360 字节**（**-99.2% 体积**），且**路径仍存在的真实工作区条目一条没少**；
配套 14 条守护用例（含 1 条**反向可验证**用例）+ 11 条变异全部被杀死；
并从**源头**止住泄漏——整个测试套件不再往开发机真实的
`~/.vscode/ai-collab/collaboration_state.json` 里写一个字节（摘要与 mtime 均未变）。

---

## 执行命令

以下 5 条即工单契约里的 `acceptance_commands`，逐字执行，全部通过：

### 1. `python3 -m pytest tests/unit/test_state_manager_global_sync.py -q`

```
14 passed in 0.12s
```

### 2. `python3 -m pytest tests/perf/ -q`

```
7 passed in 0.36s
```

### 3. `python3 -m pytest tests/ -q`

```
3053 passed, 6 skipped in 47.15s
```

6 个 skip 全部是环境原因：5 个本地后端未启动（`127.0.0.1:8000`）、
1 个 worktree 里没有 `local-backend/data/client_tokens.db`。**都不是代码问题**。

### 4. `python3 -m ruff check .`

```
All checks passed!
```

### 5. `python3 -m ai_collab.cli tasks validate-contract --scope all --strict`

```
契约校验结果: checked=18 skipped=0 invalid=0
  无契约问题

终态结果一致性: audited=17 consistent=15 mismatch=0 unparseable=0 missing_result=2
```

> `missing_result=2` 是**本工单开工前就存在**的：`TASK-P1-EXTERNAL-USER-ONBOARDING-001`
> 与 `TASK-P1-REALMACHINE-COVERAGE-EXPAND-001` 的结果文件在**尚未合入 main 的
> PR #5 分支**上，本分支从 `main` 切出，故审计时读不到。与本工单无关。

### 6. `python3 scripts/scan_secrets_pii.py --workspace .`（附加）

```
[OK] no secrets found
```

### 7. `python3 scripts/check_global_state_reclaim_mutations.py`（附加，反向可验证）

```
✅ 被杀死：回收逻辑整体失效（死条目一条不删） → test_temp_workspace_entries_are_reclaimed_immediately
✅ 被杀死：临时目录不再被特殊对待（泄漏形态漏网） → test_temp_workspace_entries_are_reclaimed_immediately
✅ 被杀死：宽限期失效（死条目一律立即回收） → test_dead_non_temp_workspace_is_kept_during_grace_period
✅ 被杀死：存在性判断恒真（什么都判成活着） → test_temp_workspace_entries_are_reclaimed_immediately
✅ 被杀死：当前条目不再受保护（正在写的条目被自己删掉） → test_current_workspace_entry_is_never_reclaimed
✅ 被杀死：条目数上限失效 → test_entry_count_cap_evicts_oldest_and_keeps_current
✅ 被杀死：体积上限失效 → test_byte_cap_evicts_oldest
✅ 被杀死：淘汰顺序颠倒（先淘汰最新的） → test_entry_count_cap_evicts_oldest_and_keeps_current
✅ 被杀死：条目 schema 被改（读取方的数据形状变了） → test_entry_schema_is_unchanged
✅ 被杀死：判不出来的 key 也被回收 → test_unknown_key_is_not_reclaimed
✅ 被杀死：测试隔离失效（套件写进 ambient 全局文件） → test_suite_does_not_write_the_ambient_global_state_file

全部 11 条变异都被杀死。
```

---

## 验证结果

### 工单第四节的 6 个待定设计问题（先答，再动手）

工单明确要求「给出回收策略的**选型理由**（为什么选 A 不选 B、备选方案是什么），
不只给实现」。逐条回答：

#### ① 回收策略：选「两级判据」（路径已不存在 × 是否位于系统临时目录），不选 LRU / 纯 mtime / 纯 TTL

| 方案 | 为什么不选 |
|---|---|
| **LRU（按访问时间淘汰）** | 全局文件是**写多读少**的索引，条目基本不重复被读 ⇒ LRU 的「最近用过」信号在这里几乎无信息量。真正的问题是「这条路径还在吗」，不是「最近用过吗」。 |
| **纯 mtime / 显式 TTL** | TTL 需要一个「多久算过期」的经验阈值，而这个阈值的取值完全取决于**路径消失的原因**：pytest 临时目录是**秒级**消失，U 盘拔掉是**用户自己拔的**。同一条 TTL 规则要么太快（误删真实工作区），要么太慢（垃圾清不干净）。 |
| **纯「路径不存在即删」** | 会误删**磁盘临时未挂载**的真实工作区——`/Volumes/external-disk/projects/team-repo` 在盘没挂上时 `stat` 就是失败的。这不是理论风险，是外接盘用户的日常。 |
| **✅ 两级判据（本次采用）** | 把「消失的原因」显式编码进规则：<br>① 路径已不存在 **且** 位于系统临时目录 ⇒ **立即**回收（实测泄漏 100% 是这一类）；<br>② 路径已不存在 **但** 不在临时目录 ⇒ 需超过宽限期（默认 7 天，从 `last_sync` 起算）才回收；<br>③ 路径还在 ⇒ 不回收；<br>④ 判不出来（`unknown` 之类非路径 key、`stat` 不到、`last_sync` 缺失）⇒ 不回收。 |

**关键前提（这是整个方案成立的地基）**：全局文件是**镜像**，不是事实源。
每个工作区自己的 `logs/collaboration_state.json` 才是事实源，全局文件只承担
「跨工作区索引」职责。所以**回收条目不会丢用户可见的状态**——该工作区下次
同步时会被重新写回。回收的代价只是「索引里少一条」，不是「数据没了」。

**为什么第②档要留宽限期**：它专门保护「外接盘 / 网络盘临时未挂载」这一类
真实工作区。宁可让它在全局文件里多留 7 天，也不误删用户看得见的项目。
**宁可多留，不可误删**——这是本方案在「安全」与「整洁」之间的取舍方向。

#### ② 回收时机：选「写入时顺手回收」，不选后台定期 / 读取时惰性

- **后台定期**：需要额外的常驻进程或定时任务。本项目是**本地优先、零配置**的
  设计（见 `CLAUDE.md` 架构哲学），引入常驻清理进程违背该前提，且没人保证它跑过。
- **读取时惰性**：全局文件的读取方是**别的工具**（监控/一致性审计），把写逻辑
  摊到读路径上会让那些读取方也承担副作用——更坏的是，**读路径不写文件**是
  很多工具的隐含假设。
- **✅ 写入时顺手回收**：`_sync_to_global()` 本来就要**读整份 → 改一条 → 写回整份**，
  回收只是「读进来的那一份里，把已经没用的条目顺手摘掉」。**零额外 I/O**
  （不新增一次读、不新增一次写），且与现有的 `_file_lock` 临界区完全重合。

#### ③ 上限兜底：条目数上限（200）+ 体积上限（4MB），超限**淘汰最旧**（不拒绝写）

- **拒绝写**会把「清理」变成「故障」：一个超大工作区就能让全局文件再也写不进去，
  产品的状态同步直接静默失效。**不可接受**。
- **淘汰最旧**（按 `last_sync` 从旧到新）保留的是「最近还在用的工作区」，
  且**当前正在写的条目永不被淘汰**。淘汰掉的条目同样会在该工作区下次同步时回来。
- 阈值可用环境变量覆盖（`AI_COLLAB_GLOBAL_STATE_MAX_ENTRIES` /
  `AI_COLLAB_GLOBAL_STATE_MAX_BYTES` / `AI_COLLAB_GLOBAL_STATE_DEAD_GRACE_DAYS`），
  便于按机器调整，也便于测试钉住边界。
  **注意**：这三个阈值是**模块导入时**从环境变量读的（即进程启动时生效），
  不是每次调用时重读——改环境变量后需重启相关进程才生效。
  非法值（不是正整数）会安全地回落到默认值，不会导致除零或空列表。

#### ④ 兼容性：全局文件还有别的读取方吗？删条目会不会丢用户可见的状态？

- 读取方经全仓检索确认只有 `VSCodeStateManager.get_global_state_file()`
  这一个入口（`ai_collab/state_manager.py`），外部消费方是 VSCode 侧的输出通道。
- **条目 schema 一个字段都没改**（`last_sync` / `tasks` / `patches` /
  `active_tasks` / `conflicts`），有专门用例 `test_entry_schema_is_unchanged` 钉住。
  只在**条目集合层面**做增删，不改**条目结构**层面 ⇒ 读取方的数据形状不变。
- **真实工作区不被误删**有 3 条专门用例钉住（存活工作区、宽限期内、当前条目）。

#### ⑤ 并发：`_file_lock` 已存在，回收逻辑**不引入新竞态**

`_sync_to_global()` 已经在 `self._file_lock(global_state_file)` 临界区内完成
「读—改—写」。回收发生**在同一个临界区内**，与写入是同一次事务：
不存在「回收和写入交错」的新窗口。写回用 `_atomic_write_json`
（临时文件 + `fsync` + `os.replace`），**要么整份替换、要么不动**，不会留半份文件。

#### ⑥ 与 VSCode 扩展侧的共享语义是否冲突？

不冲突。全局文件承担的是**跨工作区索引**（每个工作区一条），
扩展侧读它是为了知道「有哪些工作区在用本系统」，**不是**用它存跨窗口共享的
业务数据——后者由各工作区自己的 `logs/collaboration_state.json` 承担。
回收一条路径已消失的工作区索引，不影响任何跨窗口共享语义。

### 变更内容

| 文件 | 性质 | 说明 |
|---|---|---|
| `ai_collab/state_manager.py` | 产品 | 新增两级回收判据 + 容量兜底 + 写回时的回收；**条目 schema 未动** |
| `tests/unit/test_state_manager_global_sync.py` | 守护 | 新增 14 条用例（含反向可验证 + 真实工作区不误删） |
| `tests/unit/test_perf_isolation_guard.py` | 守护 | **方向翻转**（见下）+ 平台无关化 |
| `tests/conftest.py` | 隔离 | 整个套件的 `HOME`/`USERPROFILE` 指向临时目录 |
| `scripts/check_global_state_reclaim_mutations.py` | 验证 | 11 条变异检查，每条指定必须抓住它的用例 |

### 回收策略的实现要点

```
判据（_global_entry_is_reclaimable）：
  ① key 为空 / 是 "unknown" 这类判不出来的值   → 不回收
  ② 路径解析失败（相对路径、异常）              → 不回收
  ③ 路径还在（stat 成功）                       → 不回收
  ④ 路径已不存在 + 在系统临时目录下             → 立即回收
  ⑤ 路径已不存在 + 不在临时目录下 + 超过宽限期  → 回收（默认 7 天）
  ⑥ 其余（last_sync 缺失/解析不出）             → 不回收
```

两个**容易踩空、必须专门钉住**的实现细节：

- **临时目录判定必须走 `os.path.realpath`**：macOS 上 `/var/folders/...` 与
  `/private/var/folders/...` 是**同一个目录**，pytest 写进全局文件的是后者。
  只比字符串会把临时目录误判成「不是临时目录」⇒ 泄漏漏网。
  有专门用例 `test_temp_dir_detection_uses_realpath`。
- **临时目录必须用 `tempfile.gettempdir()` 取，不能写死 `/tmp`**：
  macOS 的 `gettempdir()` 是 `/var/folders/...`（**不在** `/tmp` 下面），
  Linux 才是 `/tmp`。写死 `/tmp` 会让判定随平台漂移——原性能守护里
  `/tmp/pytest-of-user/...` 这种硬编码路径就是这么在 macOS 上「碰巧蒙对」的，
  到 Linux CI 上就会失配。已一并改掉。

### 性能守护的**方向翻转**（必须说明，否则看起来像「把断言改松了」）

`tests/unit/test_perf_isolation_guard.py` 里原有一条对照断言：
「污染态必须比隔离态慢一个量级」。**那是缺陷存在的证据**——
全局状态文件从不回收死条目，1500 条垃圾每次都要整份重新序列化。
缺陷修好后，同一条断言等于**要求缺陷永远存在**，修复就永远落不了地。
所以它必须跟着翻转。

翻转后守护的是同一件事的**修复后形态**，canary 的牙齿没变：

| 断言 | 回收逻辑坏掉时 |
|---|---|
| 污染态体积必须掉到原来的 10% 以下 | ❌ 红（体积掉不下来） |
| 稳态耗时倍率必须 ≤ 10（不得被机器历史主导） | ❌ 红（重新主导测量） |
| 首次写入（读旧文件+回收+写回）倍率必须 ≥ 5 | ✅ 绿（这条是旧对照想说的话，现在被表达成「第一次写入比稳态慢一个量级」） |
| 反证用例：存活路径的污染态倍率必须 ≥ 10 | ❌ 红 |

并且**补了一条反证用例**（`test_polluted_global_state_would_dominate_without_reclamation`）：
直接构造「产品没能回收」的状态（把死条目的 key 换成仍然存在的目录 + 关掉容量兜底，
等价于修复前行为），断言此时污染态**确实**重新主导测量（倍率 ≥ 10）。
**没有这条反证，「翻转后的断言恒真」这一怀疑就排除不掉。**

### 泄漏的**源头**也止住了（不止是止血）

工单「后果 1」写的是「每跑一次测试套件就往全局文件里塞一条临时目录条目」。
**只做回收是止血**——条目还会被写进去，只是会被摘掉。真正的治本是
**测试不该写进开发机的真实文件**。

原先只有 `tests/perf/conftest.py` 隔离了 `HOME`，其余用例全都写真实文件。
现在 `tests/conftest.py` 承担**全仓隔离**：`HOME` / `USERPROFILE` 指向
每个用例自己的临时目录（`os.path.expanduser` 在 POSIX 跟随 `HOME`、
在 Windows 跟随 `USERPROFILE`，两者都设）。

隔离的是**路径解析**，不是产品行为：产品照常往「全局文件」写，只是那个文件
落在临时目录里——**没有把「产品会写全局文件」这件事从测试里拿掉**。

**实测证据**（整套件跑完后比对开发机真实文件）：

```
ambient digest before: fb5b1c3ce6a99b8b  after: fb5b1c3ce6a99b8b  => UNCHANGED
ambient mtime changed: False
```

**摘要与 mtime 都没变**——不是「内容恰好相同」，是文件根本没被碰过。

配套两条守护用例：

- `test_suite_does_not_write_the_ambient_global_state_file`：
  跑一次真实的状态同步，真实全局文件必须一个字节都没变。
- `test_global_state_file_is_redirected_into_the_test_sandbox`：
  **反向**——全局文件确实被写了，只是写在隔离目录里。
  没有这条，上面那条可能因为「产品压根不写全局文件」而恒真。

隔离装置本身也进了**变异检查**（第 11 条变异：摘掉 `HOME` 隔离 ⇒
`test_suite_does_not_write_the_ambient_global_state_file` 必须变红 ⇒ 已被杀死）。
变异检查脚本本身也改成用**独立的临时 HOME** 跑守护子进程，
避免「变异破坏隔离 ⇒ 守护往开发机真实文件里写」这种守护反成污染源的情况。

### 真实机器上的效果（实测，非推断）

开发机 `~/.vscode/ai-collab/collaboration_state.json`：

| 指标 | 修复前 | 修复后（产品自动回收后） | 变化 |
|---|---|---|---|
| 条目数 | 1589 | **3** | **-99.8%** |
| 体积 | 5,441,481 字节（5.4 MB） | **44,360 字节** | **-99.2%** |
| 真实工作区条目 | 3 | 2 | 只少了 1 条**已消失**的 `.` 之外的历史项 |

修复后剩余 3 条的构成（逐条核对过）：2 条路径仍在（`.` 与本仓），
1 条非临时目录死条目仍在**宽限期内**（`/tmp/gtest`，2026-10-22 同步，
按设计保留到宽限期结束）。

> 回收分两步完成，中间态曾短暂停在「9 条 / 78,764 字节」：
> 那 6 条多出来的条目是**变异检查脚本的历史残留**——脚本故意改坏回收逻辑时
> 把死条目原样写回了真实文件。用真实文件的一份**副本**跑一次真实同步验证：
> 9 条 → 4 条，6 条临时目录死条目全部被回收，存活工作区与宽限期内条目原样保留。
> 随后产品自己在一次真实同步（`tasks update`）中把真实文件也收敛到了 3 条。
> **变异检查脚本已改成使用独立临时 HOME，此后不会再污染真实文件。**

### 守护用例覆盖的行为契约

`tests/unit/test_state_manager_global_sync.py`（14 条）：

| # | 契约 | 用例 |
|---|---|---|
| ① | 临时目录下的死条目立即回收 | `test_temp_workspace_entries_are_reclaimed_immediately` |
| ①' | 条目数/体积不随泄漏次数无上限增长 | `test_entry_count_does_not_grow_with_repeated_leaked_workspaces`（含**反证**：回收坏掉时条目数线性增长） |
| ② | 非临时目录的死条目在**宽限期内**保留 | `test_dead_non_temp_workspace_is_kept_during_grace_period` |
| ②' | 超过宽限期后回收 | `test_dead_non_temp_workspace_is_reclaimed_after_grace_period` |
| ③ | 存活工作区条目不被误删 | `test_live_workspace_entries_are_never_deleted` |
| ④ | 当前正在写的条目永不被回收 | `test_current_workspace_entry_is_never_reclaimed` |
| ⑤ | 判不出来的 key（`unknown`）不被误删 | `test_unknown_key_is_not_reclaimed` |
| ⑥ | 条目 schema 未变 | `test_entry_schema_is_unchanged` |
| ⑦ | 条目数上限淘汰最旧、保留当前 | `test_entry_count_cap_evicts_oldest_and_keeps_current` |
| ⑦' | 体积上限淘汰最旧 | `test_byte_cap_evicts_oldest` |
| ⑧ | 临时目录判定走 realpath | `test_temp_dir_detection_uses_realpath` |
| ⑨ | 套件不写 ambient 全局文件 | `test_suite_does_not_write_the_ambient_global_state_file` |
| ⑨' | 全局文件确实被写、只是写在隔离目录 | `test_global_state_file_is_redirected_into_the_test_sandbox` |
| ⑧' | **反向可验证**（回收改坏 ⇒ 用例变红） | `test_reclamation_guard_is_reverse_verifiable` |

> 第④条的关键设计：测试用的「幽灵路径」必须**本来就可回收**（在临时目录下
> 且确实不存在）。否则测到的「没被删」其实是**宽限期**在兜底，而不是
> 「当前条目保护」在兜底——那样这条用例就**证明不了任何事**。
> 这条在实现过程中真的踩过一次坑（最初用 `/Volumes/gone/workspace`，
> 被宽限期保护，变异存活），已修正为「临时目录下的不存在的兄弟路径」。

### 工单点名要求保持绿的 4 处

```
tests/unit/test_state_manager.py
tests/unit/test_state_manager_extra.py
tests/unit/test_state_manager_v2_coverage.py
tests/perf/
```

```
94 passed in 1.54s
```

---

## 测试结论

**结论：通过。**

- 5 条验收命令**全部**逐字执行并通过（见「执行命令」，每条附真实输出）；
- 新增守护用例 **14/14** 通过；变异检查 **11/11** 变异全部被杀死；
- Python 全量 **3053 通过 / 6 跳过 / 0 失败**（跳过均为环境原因）；
- ruff **All checks passed**；mypy（`ai_collab/state_manager.py`）**Success**；
  密钥扫描 **0 命中**；
- 开发机真实全局文件：修复后 **1589 条 / 5.4MB → 3 条 / 44KB**，
  路径仍存在的真实工作区条目一条没少（少的 1 条是**已消失**的历史项，
  按设计在宽限期内才回收）；
- 测试套件对开发机真实全局文件的写入：**0 字节**（摘要与 mtime 均未变）。

**不是「写完没验证过」**：每一条守护都配了变异或反证，
证明它们对被守护的逻辑**确实敏感**，而不是恒真。

---

## 风险

### 宽限期内的非临时目录死条目会**多留 7 天**（如实的取舍）

设计如此：宁可让 `/Volumes/...` 这类路径在索引里多留 7 天，
也不误删一个「外接盘刚好没挂上」的真实工作区。
这期间它占着几百字节——**这是可接受的代价**，不是缺陷。
宽限期可用 `AI_COLLAB_GLOBAL_STATE_DEAD_GRACE_DAYS` 调整。

### 「路径不存在」在某些环境里可能是**假阴性**

网络盘断连、或权限不足导致 `stat` 失败时，产品会把路径判成「不存在」。
但产品用的是 `os.stat` 并且**只把 `FileNotFoundError` 当成不存在**，
其余 `OSError`（权限、网络错误）**一律按「还在」处理**（`_global_path_exists`
里 `except OSError: return True`）。这意味着**权限/网络异常不会导致误删**，
只可能导致条目暂时不被回收。**安全侧优先。**

### 首次写入仍要读一遍**旧文件**（老用户的一次性成本）

一个还没被回收过的历史大文件，第一次写入时仍要完整读入 + 序列化 + 写回
（实测 9.7MB 污染文件的首写约 0.05s 级）。**这一次**之后文件就小了，
后续写入回到毫秒级。**这不是回归**——它比修复前每次写入都读 5.4MB 要好得多；
修复前是**永久**的每次 5.4MB，现在是**一次性**的历史成本。

### 容量兜底可能淘汰掉「真实但很久没同步」的工作区条目

条目数超 200 或体积超 4MB 时按 `last_sync` 淘汰最旧的。
被淘汰的条目**不是数据丢失**（工作区自己的状态文件是事实源），
下次同步会回来。**当前正在写的条目永不被淘汰。**
极端情况下：一个用户有 201 个活跃工作区且都很久没动，最旧的那条会被淘汰——
下次同步它就回来了。**影响面：索引的完备性，不影响任何状态。**

### `tests/conftest.py` 的隔离是**全局**的，影响面覆盖全套件

隔离 `HOME` 意味着**所有**用例都跑在假 HOME 下。已实测：全量 3053 条通过，
无一条因隔离而失败。**风险点**在于：将来若有新用例**依赖真实 HOME**
（例如读开发机上的某个真实文件），它会**静默地**在空目录上失败——
而不是明确报错。为此 `tests/unit/test_ci_isolation_guard.py` 已经在做
「空 HOME 下必须仍然全绿」的守护；本工单把隔离从 `tests/perf/` 扩到全仓，
**方向与该守护一致**（把 CI 的运行条件搬到本地）。

### 开发机真实文件里剩下的 1 条死条目（**宽限期内，按设计保留**）

最终状态 3 条里，有 1 条 `/tmp/gtest` 的路径已不存在、但它**不在**系统临时目录
（`/tmp` 不在 macOS 的 `gettempdir()` 之下），且同步时间 2026-10-22 尚在
7 天宽限期内 ⇒ **按设计不回收**。

这是有意的：非临时目录下的路径消失，可能是「外接盘没挂上」而不是「工作区没了」。
等宽限期过后，产品会自己把它清掉，**不需要人工干预**。

> 另：此前开发机文件里短暂出现过 6 条临时目录残留，那是**变异检查脚本**
> 故意改坏回收逻辑时写回的（见「验证结果」小节）。脚本已改用独立临时 HOME，
> 后续跑测试**不再新增**残留；那 6 条也已由产品自己在真实同步中回收。

### 平台差异

回收规则里 `tempfile.gettempdir()` 的取值随平台不同
（macOS `/var/folders/...`、Linux `/tmp`、Windows `%TEMP%`）。
判定走 `realpath`，且**不写死任何平台路径**，因此同一份代码在
CI runner（Ubuntu）上行为一致。已用 `tempfile.gettempdir()` 重构掉
原先硬编码 `/tmp/...` 的污染源构造——**那处在 Linux CI 上本会失配**。

---

## 回滚

本工单不涉及数据迁移、不改条目 schema（读取方的数据形状不变）、
不改运行时配置，回滚成本低。

| 场景 | 回滚方式 |
|---|---|
| 整体回滚 | `git revert` 本工单提交（PR 未合入前直接删分支 `fix/global-state-reclaim` 即可） |
| 只回滚回收逻辑 | 撤掉 `ai_collab/state_manager.py` 里新增的回收/兜底方法与 `_sync_to_global()` 中的对应调用；**已写入的回收结果不可逆**——但被回收的条目在对应工作区下次同步时会自动回来（全局文件是镜像） |
| 只回滚测试隔离 | 撤掉 `tests/conftest.py` 里的 `isolated_home` 装置；套件会重新写进开发机真实文件（**不推荐**） |
| 只回滚性能守护的方向翻转 | 撤掉 `tests/unit/test_perf_isolation_guard.py` 的改动；注意此时旧断言**要求缺陷永远存在**，产品修复落地后它会红 |
| 恢复被回收的条目 | **无需人工操作**：对应工作区下次 `register_task` / `update_task_status` 时会自动重新写回 |

**回滚后 CI 仍会绿**——新增的守护与门禁随文件一起撤掉，回到 `71c9eac` 的状态。

---

## 参考

- `ai_collab/state_manager.py` —— 回收判据与 `_sync_to_global()`
- `tests/unit/test_state_manager_global_sync.py` —— 14 条守护用例
- `tests/unit/test_perf_isolation_guard.py` —— 方向翻转后的性能隔离守护
- `tests/conftest.py` —— 全仓 HOME 隔离装置
- `scripts/check_global_state_reclaim_mutations.py` —— 11 条变异检查
- `collaboration/tasks/TASK-P1-GLOBAL-STATE-GROWTH-001.md` —— 本工单
- `collaboration/results/RESULT-P1-PR2-CODEARTS-REVIEW-2026-10-24.md` —— 复核发现 #2
