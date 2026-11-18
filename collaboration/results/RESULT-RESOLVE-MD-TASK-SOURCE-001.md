# RESULT — TASK-RESOLVE-MD-TASK-SOURCE-001 · 让 md 成为任务事实源

- **状态**: completed
- 日期：2026-11-18 · change_id：`resolve-md-task-source`
- 执行者：`sess-resolve-md-source-20261118`（`deepseek/v4.1-flash`，AGENT_EXEC）· 评审者：`codearts_agent`
- 工作区：`/private/tmp/wt-g11`（分支 `fix/resolve-md-task-source-2026-11-18`，基线 `origin/main @ 64c85f7`）
- 范围：按用户 2026-11-18 裁定的方案 A，关闭 N26

> **口径声明**：md 是工单契约的唯一事实源；账本是从 md 派生、每个工作树各一份的本机状态。
> 同步**只写 md 已声明的字段**，缺失身份留空按切点判 `legacy` / `partial`，
> **不推导、不补全、不编造**。审计保持只读，不自动触发同步。

## 执行命令

工单 `acceptance_commands` 原样命令（逐条实际执行）：

```
openspec validate resolve-md-task-source --strict
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
python3 -m ai_collab.cli tasks sync-from-md --dry-run
python3 -m ai_collab.cli governance preflight
python3 -m pytest tests/unit/test_task_md_sync.py -q
PYTHONPATH=/tmp/noshim python3 -m pytest -q
```

同一工作区内的附加命令：

```
python3 -m ai_collab.cli tasks sync-from-md
python3 - <<'PY'  # tasks 内容幂等与 md 未被回写
import json, hashlib
d = json.load(open('logs/collaboration_state.json'))
hashlib.sha256(json.dumps(d['tasks'], sort_keys=True).encode()).hexdigest()
PY
git worktree add /tmp/wt-md-base 64c85f7 --detach   # 干净基线对照
```

## 验证结果

### 1 · N26 台账原文只说对了最浅的一层

台账写的是「账本 18 条，磁盘另有 8 个文件未计入」。复核时这已经过时，真实情况三层：

**第一层 · 账本不是仓库事实。** `logs/` 被 gitignore，每个工作树各一份：
主工作区 18 条 / 34,644 B / `62d92b34…`；wt-g11 2 条 / 3,301 B / `0472a163…`；
全新 clone 0 条。磁盘 27→28 个 `TASK-*.md` 恒定，与三者交集**都是 0**。
「差 8 条」只在那台机器成立，换台机器差值是 28 或 2。所以「补录 8 个文件进账本」
作为仓库层面的解根本不成立——补完只对自己这台生效。

**第二层 · 补录链路在最后一米丢身份。** `scripts/verify_task_file_contracts.py`
扫 md、解析 frontmatter、调 `register_task(...)` / `update_task_contract(...)`，
但两处**都没传 `session_id` / `model_id`**。而这两个函数都支持、内部也真会写入
（`state_manager.py:1083-1084` / `:1427-1428`，写入在 `:1139-1140` / `:1496-1503`）。
丢在调用点。不修它，把 28 个 md 全登记进账本仍会得到全 `legacy`——
正是 N26 影响面第 ② 条预言的「补完还像没补完」的返工。

**第三层 · 双输入源不是秘密，但身份这一维没人管。** 该脚本 docstring 首段就写着
「`validate-contract` 读运行时状态库、不读 md」，解法是临时登记再校验；
但它不检查身份。所以身份只在账本侧被查，md 侧的校验器完全没覆盖。

### 2 · 实现期抓到两个真 bug（都是冒烟测试逼出来的，不是靠读代码看出来的）

**① `applied` 键名拼错。** 字典键写的是 `created` / `updated`，而 `plan["action"]`
的值是 `create` / `update`。第一次实际同步建完一条就 `KeyError` 崩溃，账本留下部分写入
（4 条中多出一条 `TASK-CLOSE-GOV-GAPS-001`）。修法是统一键名；修好后重跑走 `update`
分支把那条纠正，**没有手工删账本**。

**② `created_at` 被同步时刻覆盖。** `register_task` 不接受 `created_at` 参数，
同步时用当前时间。结果 2026-10-24 的历史工单被判成「切点后缺身份」（`missing`）。
修法是在同步元数据提交时按 md 的 `created_at` 覆盖——事实源是 md，不是同步动作。
两个 bug 都有守护用例（`TestNoFabrication` / `TestOneWayAndIdempotent`）。

### 3 · 同步实测

```
$ tasks sync-from-md --dry-run
md 工单同步: 预演 source=28 created=26 updated=0 unchanged=2

$ tasks sync-from-md
md 工单同步: 已写入 source=28 created=26 updated=0 unchanged=2

$ tasks migrate-identity
身份迁移审计: scope=all apply=False cutoff=2026-11-16 total=29
  declared=3 partial=0 legacy=25 missing=1 invalid=0
  输入来源: 账本源自 md 同步（2026-11-18T07:58:01.989565，28 条）
```

`total=29 > synced_count=28` 的差值来自 1 条**没有对应 md** 的本机条目
（`TASK-PREFLIGHT-WORKTREE-GATE-001`）。同步不删除它——删除账本事实不在授权范围内——
两者同时出现在输出中，覆盖范围可被解释。

`missing=1` 已逐条定位：`TASK-CLOSE-GOV-GAPS-001`，`created_at=2026-11-16T04:30:00`，
正好等于切点日期。按现有「按日期比较」规则判 `missing` **是正确的**；但它早于身份机制
当天稍晚落地的时刻，属于切点粒度边界。**没有改切点规则**（那会影响已归档 spec 与既有用例，
是独立 change），也**没有为它编造身份**，已在 PROTOCOL §7.6 第 4 条明文披露。

### 4 · 幂等、单向、零回归

```
连续同步两次：tasks 内容 sha256 095bbb5478ffac2a → 095bbb5478ffac2a
md 集合 sha256：16040211017f448c → 16040211017f448c
重复同步：created=0 updated=0 unchanged=28
```

账本**文件整体** sha256 会变，因为 `md_sync.synced_at` 每次刷新。这是「最近一次同步」
的审计信息；为追求字节幂等而丢掉它是错误取舍。因此幂等指标定义为**任务内容哈希**，
不是文件字节哈希——proposal 验收标准已同步更正。

| 侧 | 全套 pytest（同环境同命令） |
|---|---|
| 干净基线 `64c85f7` | 3189 passed, 8 skipped |
| 改动分支 | **3199 passed, 8 skipped** |

净增 10（新增守护用例），零失败。`ruff check` / `ruff format --check .` 全过
（333 files）。preflight 六项全 PASS——中途因改了 `PROTOCOL.md` 触发「必读清单内容已变更」
而 FAIL，重新读确认后按唯一入口重新声明，复跑恢复 PASS；这个过程本身证明门禁有效。

## 偏离与残留

**1 · 切点粒度边界未修。** 见 §3 末段。`missing=1` 按现行规则正确，语义上是历史工单。
要修得改 `IDENTITY_REQUIRED_SINCE` 的比较粒度（按日期 → 按时刻，或加机制落地时刻），
影响已归档 spec 与既有用例，未在本 change 范围。**不得为此编造身份。**

**2 · 账本里无 md 的本机条目保留。** 同步只补 md，不删除没有 md 的条目。
这使 `total` 可能大于 `synced_count`；已通过 `input_source` 让差值可见，不靠「删掉差值」制造一致。

**3 · 审计不自动同步。** `audit_task_identity` 保持只读，是否先同步由 PROTOCOL §7.6 的流程纪律承担。
理由与 G11 不读并发门禁降级开关相同：让一个入口的旋钮悄悄改变另一个的判定，
会让「审计过了」的含义不可预期。

**4 · 切点边界的 CLI 提示仍偏泛。** `tasks migrate-identity` 对 `missing` 打印
「需用 tasks update 补齐」。对本次这类历史边界工单，该建议会误导人编造身份。
PROTOCOL §7.6 第 4 条已明确禁止；改 CLI 文案属输出契约变更，未并入本 change。

**5 · CI 不是全绿，但不带新增错误合入。** PR #76 的 Bandit / python-tests ×3 / mypy
是既有红灯，PR #72–#75 失败集合一致。过程中本 change **新引入**过一条 mypy error
（`task_md_sync.py:16` 的 `import yaml` 缺 stub，CI 从 3 errors/1 file 变成 4 errors/2 files）。
补 `# type: ignore[import-untyped]` 后本地与 CI 均恢复为既有 3 errors/1 file，
确认无新增后才合并。其余检查项通过。

## 交付编号

- PR：https://github.com/17Mojo/ai-collab-base/pull/76
- 合入提交（40 位完整 sha）：`face8ddaba0e95ad6b125a788e6fbcf5a439f98f`
- 登记：`chore(governance): 登记本 change 的合入提交 face8dd`
- 归档：`2026-11-18-resolve-md-task-source`，`openspec validate --archived --strict` 8 passed
- 台账：N26 closed；28 条中 closed 26 / wontfix 1 / **open 1（仅 N25）**
