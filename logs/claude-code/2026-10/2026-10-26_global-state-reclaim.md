# 2026-10-26 · 全局状态文件死条目回收（TASK-P1-GLOBAL-STATE-GROWTH-001）

**工单**: `TASK-P1-GLOBAL-STATE-GROWTH-001`
**结果文件**: `collaboration/results/RESULT-P1-GLOBAL-STATE-GROWTH-2026-10-26.md`
**分支**: `fix/global-state-reclaim`（基线 `main` @ `71c9eac`）

---

## 做了什么

全局状态文件 `~/.vscode/ai-collab/collaboration_state.json` 之前只增不减：
开发机上 1589 条里 1587 条是 pytest 临时目录（测试自身泄漏的产物），
体积 5.4MB，真实工作区只有 2 条。

本次做了三件事：

1. **产品侧回收**（`ai_collab/state_manager.py`）——两级判据：
   路径已不存在 **且** 在系统临时目录 ⇒ 立即回收；
   路径已不存在但不在临时目录 ⇒ 超过 7 天宽限期才回收；
   路径还在 / 判不出来 ⇒ 不回收。
   外加条目数（200）与体积（4MB）容量兜底，按 `last_sync` 淘汰最旧，
   当前条目永不动。**条目 schema 一个字段没改。**
2. **性能守护方向翻转**（`tests/unit/test_perf_isolation_guard.py`）——
   原来的对照断言「污染态必须比隔离态慢一个量级」等于**要求缺陷永远存在**，
   修复就永远落不了地。翻转后守护「机器历史不得再主导测量」，
   并补了一条反证用例证明翻转后的断言不是恒真。
3. **从源头止住泄漏**（`tests/conftest.py`）——原先只有 `tests/perf/` 隔离
   `HOME`，其余用例全都写开发机真实文件。现在全仓隔离。

## 关键判断

- **全局文件是镜像，不是事实源**——这是整个方案的地基。每个工作区自己的
  `logs/collaboration_state.json` 才是事实源。所以回收条目**不丢用户可见状态**，
  该工作区下次同步会被重新写回。这也让「容量兜底淘汰最旧」变得安全。
- **回收策略不选 LRU、不选纯 TTL**——全局文件写多读少，LRU 的「最近用过」
  信号在这里几乎无信息量；纯 TTL 的阈值取决于**路径消失的原因**
  （pytest 临时目录秒级消失 vs U 盘被拔掉），同一条规则要么太快误删真实工作区、
  要么太慢清不掉垃圾。**把「消失的原因」显式编码进两级判据**。
- **宽限期专门保护「外接盘临时未挂载」**——`stat` 失败可能是盘没挂上。
  宁可让它在索引里多留 7 天，也不误删用户看得见的项目。**宁可多留，不可误删。**
- **回收放在写入时顺手做**——`_sync_to_global()` 本来就要「读整份→改一条→写回整份」，
  回收只是把读进来的那份里没用的摘掉，**零额外 I/O**，且与既有 `_file_lock`
  临界区完全重合，**不引入新竞态**。不引入后台常驻清理进程（违背本地优先/零配置前提）。
- **回收是止血，不是治本**——工单「后果 1」说的是「每跑一次测试就塞一条」。
  只做回收，条目还会被写进去。所以 `tests/conftest.py` 必须做全仓 HOME 隔离。
  隔离的是**路径解析**，不是产品行为：产品照常写全局文件，只是落在临时目录里。

## 踩到的坑

- **「当前条目受保护」那条用例最初证明不了任何事**：幽灵路径用了
  `/Volumes/gone/workspace`，它被**宽限期**保护着，不是被「当前条目保护」保护着
  ——变异「当前条目不再受保护」因此存活。改用「临时目录下、确实不存在的兄弟路径」后，
  变异被杀死。**断言必须只被它声称的那条规则兜住**，否则是假绿。
- **性能守护翻转后倍率只有 1.0**：探针量的是 `update_task_status`，
  但同一次探针里更早的 `register_task` 已经把文件回收完了。补了
  `_FIRST_WRITE_LATENCY_PROBE`（量首次写入=读旧文件+回收+写回）才量到差异。
- **反证用例倍率 8.7 < 10**：新的条目数上限把 1500 条存活条目淘汰掉了。
  关掉两个容量兜底（`AI_COLLAB_GLOBAL_STATE_MAX_ENTRIES` /
  `..._MAX_BYTES`）才等价于「修复前」的行为。
- **平台依赖的定时炸弹**：原性能守护的污染源写死 `/tmp/pytest-of-user/...`，
  而 macOS 的 `tempfile.gettempdir()` 是 `/var/folders/...`（**不在** `/tmp` 下面），
  Linux 才是 `/tmp`。原用例在 macOS 上是**碰巧蒙对**的，到 Linux CI 上就会失配。
  已改用 `tempfile.gettempdir()`。
- **测试隔离目录名撞车**：根 conftest 的隔离目录一开始也叫 `fake-home`，
  撞上 `test_perf_isolation_guard.py` / `test_ci_isolation_guard.py` 自己造的
  `fake-home`/`isolated-home` ⇒ `FileExistsError`。改成 `conftest-isolated-home`。
- **变异检查脚本自己成了污染源**：它故意改坏回收逻辑再跑守护，
  于是把死条目**原样写回了开发机真实文件**（实测残留 6 条）。改成用独立临时
  HOME 跑守护子进程，并加第 11 条变异（摘掉隔离 ⇒ 守护必须变红）。
- **PR #6 的 CI 在 3.11 上红（倍率 6.2 < 10），3.10/3.12 绿**——这次栽的不是
  产品行为，是**测量口径**。对照断言比的是整条 `update_task_status` 的倍率，
  而隔离态那 0.0196s 里绝大部分是**与全局文件无关**的固定开销（契约校验、通知、
  工作区状态落盘），共享 runner 上这些就要 ~20ms。污染的**边际成本**（~0.1s）
  明明远大于隔离态的**总**耗时，倍率却被无关开销稀释 ⇒ **这条断言在测机器，
  不在测产品**（同一份代码本地倍率 90、3.11 runner 上 6.2）。
  改成只量 `_sync_to_global()` 这一步（机器历史真正进入的地方）+ 4 采样取 min
  （抗 fsync 抖动）+ 污染源提到 3000 条（为余量）后，实测倍率 266 / 382。
  **教训：跨进程的墙钟倍率当门禁，分子分母都得先确认「只含被守护的那个变量」。**

## 验证

```
python3 -m pytest tests/unit/test_state_manager_global_sync.py -q  → 14 passed
python3 -m pytest tests/unit/test_perf_isolation_guard.py -q        → 3 passed
python3 -m pytest tests/perf/ -q                                    → 7 passed
python3 -m pytest tests/ -q                                          → 3053 passed, 6 skipped
python3 -m ruff check .                                              → All checks passed
python3 -m mypy ai_collab/state_manager.py                          → Success
python3 -m ai_collab.cli tasks validate-contract --scope all --strict → invalid=0
scripts/scan_secrets_pii.py --workspace .                           → [OK] no secrets found
scripts/check_global_state_reclaim_mutations.py                     → 11/11 变异全被杀死
```

真实机器效果：开发机全局文件 **1589 条 / 5,441,481 字节 → 3 条 / 44,360 字节**，
路径仍存在的真实工作区条目一条没少（少的 1 条是已消失的历史项，按设计在宽限期内才回收）。
测试套件对真实文件的写入：**0 字节**（摘要与 mtime 均未变）。

## 还没做的

- **开发机真实文件里剩 1 条死条目**（`/tmp/gtest`，非临时目录、同步于 2026-10-22）
  仍在**宽限期内** ⇒ 按设计不回收，宽限期过后产品会自己清掉。不主动改用户文件。
- 宽限期内的非临时目录死条目会**多留 7 天**：设计如此，是取舍不是缺陷。
