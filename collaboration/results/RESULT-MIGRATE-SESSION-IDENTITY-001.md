# RESULT — TASK-MIGRATE-SESSION-IDENTITY-001 · 身份与路由分离（PROTOCOL §7.3 语义迁移）

- **状态**: completed
- 日期：2026-11-16 · change_id：`migrate-session-identity`
- 执行者：`claude_code`（AGENT_EXEC）· 评审者：`codearts_agent`
- 工作区：`/tmp/wt-gov-identity`（分支 `feat/migrate-session-identity-2026-11-16`，基线 `origin/main @ 768b7f2`）
- 范围：`PROTOCOL §7.3` 绑定规则从厂商标签改为会话+模型身份；`SUPPORTED_ASSIGNEES` 与 §12 废弃声明的矛盾裁定

> **口径声明**：本 change 交付的是「身份可声明、可核验、可反查路由」，
> **不是**「运行时路由已迁移」。五个路由模块仍按 `assignee` 过滤，淘汰条件写进 `PROTOCOL §12.1`
> 但**未执行**。历史工单一个都没补身份——补不出来，也不编造。
> 验收标准是「正反两侧都有机器用例」，不是「功能看起来装上了」。

## 执行命令

工单 `acceptance_commands` 原样命令（逐条实际执行）：

```
openspec validate migrate-session-identity --strict
python3 -m ai_collab.cli tasks migrate-identity
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
python3 -m pytest tests/unit/test_session_identity.py tests/unit/test_governance_gaps.py -q
ruff format --check .
ruff check .
```

同一工作区内的附加命令：

```
PYTHONPATH=/tmp/noshim:$PYTHONPATH python3 -m pytest -q --tb=no -p no:cacheprovider          # 当前侧
cd /tmp/gov-id-baseline && PYTHONPATH=/tmp/noshim:$PYTHONPATH python3 -m pytest -q --tb=no -p no:cacheprovider
diff /tmp/fail-base.txt /tmp/fail-work.txt && cmp /tmp/fail-base.txt /tmp/fail-work.txt
python3 -m ai_collab.cli -w <main> tasks migrate-identity      # 真实账本只读审计
shasum -a 256 <main>/logs/collaboration_state.json             # 审计前后各一次
python3 -m ai_collab.cli tasks register|update ... ; python3 -m ai_collab.cli ack ...
```

## 验证结果

### 1. 身份模块：四态判定（declared / legacy / missing / invalid）

`ai_collab/identity.py` 是唯一判定入口，理由是把「身份是否成立」的判断集中在契约层
用同一套规则，而不是让 CLI、账本、审计各写一份。

| 状态 | 触发条件 | 契约后果 |
| --- | --- | --- |
| `declared` | `session_id` + `model_id` 齐全且格式合法 | 通过 |
| `legacy` | `created_at < 2026-11-16` 且未声明 | **不判错**，计入 `legacy_identity` |
| `missing` | `created_at >= 2026-11-16` 且未声明 | 不合法，点名缺失字段 |
| `invalid` | 已声明但含空白/超长/非法字符 | 不合法，与 `missing` 分开报 |

关键设计：`created_on_or_after()` 在 `created_at` 缺失时**按必填处理**（fail-closed）——
拿不到创建时间就无法证明它是历史工单，宁可判严也不放行。

### 2. 契约层接入（时间切点而非一刀切）

```
$ python3 -m pytest tests/unit/test_session_identity.py -q
34 passed, 2 warnings in 0.42s
```

覆盖正反两侧：

| 用例族 | 断言 |
| --- | --- |
| 新工单声明完整身份 | 通过，且不被 `assignee` 的存在「顺带」判过 |
| 切点后缺失身份 | 不合法，`missing_fields` 含 `session_id` / `model_id` |
| 切点前缺失身份 | 不判错，`legacy_identity` 计数 +1 |
| 格式非法 | 与缺失分开进 `invalid_fields`，不混为「没填」 |
| 注册表反查成功 | 只给 `session_id` 也能建单，`assignee` 来自注册表且标 `sources=registry` |
| 注册表反查失败 | **拒绝创建**（`exit=1`），不写空 `assignee` 让下游更远处失败 |
| 审计只读 | 不改任何工单或账本 |
| `--apply` | 只写注册表里可查到的路由键，反查不到的保持不变 |

受影响夹具回归：`tests/unit/test_state_manager.py` → `40 passed`；
`tests/perf/test_performance_baseline.py` + `tests/unit/test_perf_isolation_guard.py` → `10 passed`。

### 3. 规则文本与代码同 commit

`PROTOCOL §7.3` 改绑 `session_id` + `model_id`；新增 §7.5「身份与路由分离」；§12 增加 §12.1
把 `SUPPORTED_ASSIGNEES` 明确为**过渡兼容白名单**并写出三条**可判定**淘汰条件
（五模块路由入参改为 `session_id` / 注册表提供完整 `transport` 映射且投递侧改造 / `legacy_identity` 归零）。
`AI-COLLABORATION-STANDARDS §2.1` 加入身份字段检查项。

这是本 change 最容易出现「第四类假绿」的地方：规则说要校验、代码不校验，或者反过来。
所以文本与代码在**同一个提交**里落地，没有拆成两次。

### 4. 真实账本上的只读审计（含「不写入」的实证）

```
$ shasum -a 256 <main>/logs/collaboration_state.json
62d92b3408f39d92b97170edf87440098086ba90925583583e8e78a009f1b5d4

$ python3 -m ai_collab.cli -w <main> tasks migrate-identity
身份迁移审计: scope=all apply=False cutoff=2026-11-16 total=18 declared=0 partial=0
              legacy=18 missing=0 invalid=0
  路由键可补全项: 0（注册表未提供可反查的会话）
  只读审计，未写入任何文件（加 --apply 才写，且只写注册表事实）
  提示: legacy 是历史欠账，本命令不为其编造身份值

$ shasum -a 256 <main>/logs/collaboration_state.json    # 复算
62d92b3408f39d92b97170edf87440098086ba90925583583e8e78a009f1b5d4
```

哈希前后一字不差 —— 「默认只读」不是注释里的承诺，是实测。这轮结束后主工作区
`git status --porcelain | wc -l` 仍是 `153`，在途改动零触碰。

### 5. 测试结论（全套回归，两侧同环境对照）

基线 = `git archive 768b7f2` 展开后 `git init` 的干净快照；当前 = 本分支工作树。
两侧都加 `PYTHONPATH=/tmp/noshim:$PYTHONPATH` 遮蔽沙箱 shim（原因见风险 1）。

| 侧 | 结果 |
| --- | --- |
| 基线 | `50 failed, 3084 passed, 8 skipped, 3 warnings in 42.89s` |
| 当前 | `50 failed, 3118 passed, 8 skipped, 3 warnings in 43.42s` |
| 净增通过 | `3118 - 3084 = 34`（= 新增用例数） |
| `diff` / `cmp` FAILED 集合 | **无输出 / byte-identical** |

50 条既有失败全部落在 `test_consensus_engine*` / `test_soul_injection*` /
`test_ai_integration_mock_flags`，都是依赖外部 LLM 服务的环境型失败
（provider_client 13、real_adapter 12、consensus_engine 10、concurrency 5、
soul_injection_engine 4、consensus_engine_extra 3、mock_flags 3）。与本次改动无关，
且两侧数量与集合完全一致。

静态门禁：`ruff format --check .` → `329 files already formatted`；`ruff check .` → `All checks passed!`。

### 6. OpenSpec

```
$ openspec validate migrate-session-identity --strict
Change 'migrate-session-identity' is valid
```

## 风险

1. **沙箱 shim 会让「全绿」变成假绿，本报告的对照结论依赖遮蔽它。**
   本会话 `PYTHONPATH` 前植的 `sandbox-center-runtime-kit/shim` 中
   `sitecustomize.py:884` 的 `_brokered_path_mkdir` 在 `exist_ok=True` 且目录已存在时
   仍把 `mkdir` 代理给宿主，宿主返回 `EEXIST` 后直接抛出、**不回落原生语义**。
   后果是任何 `Path(...).mkdir(exist_ok=True)` 打在已存在目录上都会炸。
   本轮首次运行因此跑出大量伪失败，已作废那一轮并在 E6 里只采用遮蔽后两侧同环境的数据。
   `CODEBUDDY_BROKERED_FS_HOOK_ENABLED=0` 无效，只能前置空 `sitecustomize.py` 遮蔽。
   **这意味着「一次跑绿」在本环境不构成证据，必须两侧对照。**

2. **`migrate_task_contracts` 刻意保持不填身份 —— 这是裁定，不是遗漏。**
   实施中曾让它顺带补 `session_id` / `model_id`，撞红 6 条既有用例。复核后判为设计错误：
   契约字段迁移与身份声明正交，前者可从工单自身推导，后者**推导不出来**（会话已消失）。
   回退迁移逻辑，改为给 5 处测试夹具补身份——那些用例测的是「完整契约能过」与性能基线，
   不是「缺身份如何报错」。用修夹具换取迁移函数「顺手造数据」，是把没做的补齐，不能接受。

3. **审计只覆盖账本（18 条），磁盘上还有 8 个任务文件没被计入。**
   `audit_task_identity` 读 `state["tasks"]`（18 条），而 `collaboration/tasks/TASK-*.md` 有 26 个。
   逐个 grep 身份字段得到 26/26 两者皆无。因此 `legacy=18` **不等于**「全部任务已盘点」。
   已登记 `known_gaps.json` N26（P2/open）并在此声明，不给单一数字背书。差值 8 的归属未逐条追查。
   **2026-11-16 复核追加**：在真实 clone 上 `checked=0` / `total=0` / 磁盘 26 个文件——
   `18` 是某台机器账本的属性，**不可从仓库复现**。见 §记录更正 2。

4. **运行时路由仍是 `assignee`，本 change 没有迁移它。**
   ack / 干预队列 / 缺失 ACK / 看门狗 / 会话健康五个模块仍按厂商标签过滤。
   改成按 `session_id` 路由需要 `assignee → session_id → transport` 完整映射与投递侧改造，
   牵动桥接脚本，属独立风险面。`PROTOCOL §12.1` 的三条淘汰条件就是给下一个 change 的入口判据。
   在此之前，「工单能声明身份」与「消息按身份投递」之间仍有断层。

5. **历史工单没有任何身份事实可依，只能按 legacy 计数。**
   磁盘 26 个 `TASK-*.md` 逐个 grep：26/26 既无 `session_id` 也无 `model_id`；
   本机账本里那 18 条同样没有。注册表里没有这些会话的记录，`created_at` 也在切点之前。
   给它们编 `session_id` 会让统计看起来漂亮，但那是假的——比留空更坏。
   `legacy_identity` 会一直是这个数，直到这些工单到达可核验终态。
   注意这个数**只在本机账本上有意义**（干净检出上是 0），见 §记录更正 2。

6. **`git add -A` 会把本机单会话快照覆盖到共享监控文件上（已登记 N27，本轮已规避）。**
   `collaboration/monitoring/*_latest.md` 被跟踪，但数据源 `logs/session_registry_state.json` 是
   gitignored 的本机状态。本 worktree 跑过一次 `sessions register` 后，`SESSION_REGISTRY_SUMMARY_latest.md`
   就从「2026-10-24 / 会话数 8 / healthy 7」变成「2026-11-16 / 会话数 1 / healthy 1」，
   8 个真实会话 ID 整段被替换成本机的 `sess-migrate-identity-20261116`。
   本轮已把这两个文件排除出提交 pathspec 并 `git checkout --` 还原。
   这条**不是**本 change 引入的缺陷，但收口时差点被 `add -A` 顺手带进 main。

7. **干净 main 检出上 `preflight` 会 FAIL，缺的是本机活动不是代码。**
   `.ai_collab_session.json`、`logs/collaboration_state.json`、
   `.vscode/ai-collab.local.json` 三个输入都是 gitignored 的本机状态，干净检出上没有它们，
   「必读清单声明」「状态机时效」「门禁输入完整性」「显式 ACK」**四项**必然红；
   只有「HEAD 治理登记」是仓库事实因而 PASS。
   这不是回归，是这四项的设计前提就是「有本机会话在活动」。CI 上若要绿，需要各自的装备，
   或改用 CI 自己的基线。原报告写的是「三项」，漏了门禁输入完整性——见 §记录更正 1。

## 记录更正（2026-11-16 复核）

本报告首版有两处口径不准，复核后按实测改，保留更正痕迹而不是直接改数：

### 更正 1 · 干净检出 `preflight` 是四项 FAIL，不是三项

首版列的是「必读清单声明 / 状态机时效 / 显式 ACK」三项，漏了**门禁输入完整性**。
漏的原因是那次在 `/tmp/wt-gov-identity` 里跑的，而我在那儿亲手建了
`.vscode/ai-collab.local.json` 覆盖层，所以它 PASS——**在干净检出上它必然 FAIL**。

真实 clone 实测（不是 `git archive` 快照，避免 `4d04acd` 不存在造成的假象）：

```
$ git clone git@github.com:17Mojo/ai-collab-base.git /tmp/realclone   # HEAD 2a968a2
$ python3 -m ai_collab.cli governance preflight
[FAIL] 必读清单声明: .ai_collab_session.json 缺失或为空，无法核验必读清单
[FAIL] 状态机时效: 状态文件缺失或无 last_updated
[FAIL] 门禁输入完整性: 未装备，缺: ['expectedBranch', 'baselineCommit', 'watchPaths']
[PASS] HEAD 治理登记: 边界后合并提交 3 个，未登记 0 个
[FAIL] 显式 ACK 证据: 无显式 ACK
preflight: FAIL
```

### 更正 2 · `legacy_identity=18` 不可从仓库复现

同一个真实 clone 上：

```
$ python3 -m ai_collab.cli tasks validate-contract --scope all
契约校验结果: checked=0 skipped=0 invalid=0 legacy_identity=0

$ python3 -m ai_collab.cli tasks migrate-identity
身份迁移审计: scope=all apply=False cutoff=2026-11-16 total=0 ... legacy=0

$ ls collaboration/tasks/TASK-*.md | wc -l
26
```

三处数字互不相等：**账本 0 条 / 磁盘 26 个文件 / 本机 18 条**。

所以 `legacy_identity=18` 是「某台机器的 `logs/collaboration_state.json` 里恰好有 18 条任务」
这个事实，**不是仓库事实**。首版把它写成「26 个工单全部 legacy」会让人以为任何检出都能看到
这批历史欠账——实际看不到。这条已追加进 `known_gaps.json` N26 的证据链。

含义：任何以账本为输入的身份类审计，在新鲜检出上都是空跑（`checked=0`），
**看不出**历史工单缺身份这件事。要真做「历史欠账盘点」，得先有余量把
`collaboration/tasks/TASK-*.md` 与账本对齐（N26 的待做项 ①）。

## 回滚

本 change 的改动彼此独立，可分块回退：

- **身份层**：删除 `ai_collab/identity.py`，`state_manager` 里 `TASK_CONTRACT_IDENTITY_FIELDS`
  的注入与 `resolve_identity` 调用一并移除，契约回到「只有 `assignee`」的旧口径。
  回退后新工单不再要求身份，`legacy_identity` 计数消失。
- **CLI**：`tasks register/update` 的 `--session-id` / `--model-id` 与 `migrate-identity` 子命令
  是纯新增参数，移除后旧调用方式不受影响（不带这些参数即旧行为）。
- **规则文本**：`PROTOCOL §7.3` / §7.5 / §12.1 与 `STANDARDS §2.1` 的新增行是可独立回退的文本块；
  但**必须与代码同时回退**，否则会造出「规则要求、代码不校验」的第四类假绿，比原状更坏。
- **known_gaps N26**：条目按约定只改 `status` 不删，回退时置 `wontfix` 并保留结论。
- **整体**：`git revert <本 change 的提交>`。新增文件（`identity.py`、change 工件、
  `test_session_identity.py`、本报告）随之删除，5 处夹具改动一并恢复。
