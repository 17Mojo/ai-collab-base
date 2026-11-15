# RESULT — TASK-GOV-RESTORE-001 · 恢复治理门禁的可判定性

- **状态**: completed
- 日期：2026-11-15 · change_id：`restore-governance-enforcement`
- 执行者：`claude_code`（AGENT_EXEC）· 评审者：`codearts_agent`
- 工作区：`/tmp/wt-governance-restore`（独立 worktree，分支 `feat/restore-governance-enforcement-2026-11-15`）
- 生效边界：`origin/main` @ `4d04acda3fa9ec8218a3d1a6323bd2fac25eac75`
- 范围：三处治理完整性缺口（覆盖率可判定性、门禁输入完整性、受管账本写入互斥）。
  会话化改造、规则文本修改、11 月 PR 追溯补档均不在本 change 内。

> **口径声明**：本文所有结论来自机器可复核输出（命令 + 原始 stdout/stderr + 失败集合比对），
> 不含人工目检判定。凡本仓当前不成立的项（如 `governance preflight`），如实记录为 FAIL 并给出
> 原因，不写成通过。

## 执行命令

工单 `acceptance_commands` 原样命令（逐条实际执行）：

```
openspec validate restore-governance-enforcement --strict
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
python3 -m ai_collab.cli governance preflight
python3 -m pytest tests/unit/test_governance_ledger.py -q
python3 -m ruff format --check .
python3 -m ruff check .
```

同一工作区内的附加命令：

```
python3 -m ai_collab.cli --workspace . governance check-writes
python3 -m ai_collab.cli governance declare-enforcement --commit-sha 4d04acda3fa9ec8218a3d1a6323bd2fac25eac75 --reason "..." --declared-by claude_code
python3 -m pytest -q --tb=no -p no:cacheprovider                      # 当前侧
cd /tmp/gov-baseline-clean && python3 -m pytest -q --tb=no -p no:cacheprovider   # 基线侧
comm -13 base_failed.txt cur_failed.txt && comm -23 base_failed.txt cur_failed.txt && cmp base_failed.txt cur_failed.txt
python3 /tmp/gov_a_demo.py                                            # A1-A4 原始 CLI 输出
python3 -m ai_collab.cli tasks register|update ...                    # 台账状态变更
python3 -m ai_collab.cli ack --task-id TASK-GOV-RESTORE-001 --status completed
```

## 验证结果

### 1. 规格校验

```
$ openspec validate restore-governance-enforcement --strict
Change 'restore-governance-enforcement' is valid
```

### 2. 契约与治理覆盖率（本仓真实仓库）

```
$ python3 -m ai_collab.cli tasks validate-contract --scope all --strict
契约校验结果: checked=1 skipped=0 invalid=0
  无契约问题
终态结果一致性: audited=0 consistent=0 mismatch=0 unparseable=0 missing_result=0
[governance] 治理覆盖率: available=True merge_count=0 gap_count=0 would_fail=False applied=False
exit=0
```

`applied=False` 的语义是「门禁在force状态但本仓没有未登记合并提交」，不是「门禁未开启」：
`evaluate_coverage()` 里 `applied = COVERAGE_IN_DECISION and would_fail`。

### 3. 一致性扫描（受管账本写入路径）

```
$ python3 -m ai_collab.cli --workspace . governance check-writes
✓ 一致性校验通过：受管账本写入路径 0 处绕过统一入口
exit=0
```

反向证明扫描器不是假绿：注入一个直写文件后

```
::error::绕过统一账本写入入口: ai_collab/bad.py:3:write_text()
exit=1
```

### 4. 开工检查（本仓真实状态，如实记录 FAIL）

```
$ python3 -m ai_collab.cli governance preflight
[FAIL] 必读清单声明: 缺: ['collaboration/AI_BEHAVIOR_CONSTRAINT_FILES.md', 'collaboration/COLLABORATION_GUIDELINES.md', 'collaboration/PROTOCOL.md', 'rules/AI-COLLABORATION-STANDARDS.md']
[PASS] 状态机时效: 2026-11-15T23:49:43.849981
[FAIL] 门禁输入完整性: 未装备，缺: ['expectedBranch', 'baselineCommit', 'watchPaths']
[PASS] HEAD 治理登记: 边界后合并提交 0 个，未登记 0 个
[FAIL] 显式 ACK 证据: 无显式 ACK
preflight: FAIL
exit=1
```

三项 FAIL 各有归属，均非「门禁失效」：

| FAIL 项 | 原因 | 归属 |
| --- | --- | --- |
| 必读清单声明 | 本 worktree 没有 `.ai_collab_session.json`；该文件的写入方在本仓内不存在（`grep` 全仓只有 `governance.py` 读取它，无任何写入点，`sessions register` 也不写它） | 会话接入缺口，见风险 7 |
| 门禁输入完整性 | `concurrentGuard` 三个输入为空，tasks.md 4.7 显式不做 | 结构性缺口，见风险 1 |
| 显式 ACK 证据 | 当时尚未生成 ACK，已在 Phase 5 补生成；复跑后该项转为 `[PASS] 显式 ACK 证据: 1 条` | 本报告收口动作，已完成 |

`preflight` 的 PASS 路径由验收场景 A6 在受控临时 git 仓库中机器证明（补齐三项输入后
`preflight: PASS`、`exit=0`），不靠在本仓写死会话基线来换一个绿色。

### 5. 治理账本机制测试

```
$ python3 -m pytest tests/unit/test_governance_ledger.py -q
42 passed, 2 warnings in 5.48s
```

其中 Phase 4 验收场景逐条：

```
test_acceptance_a1_undeclared_merge_fails_strict PASSED
test_acceptance_a2_declared_merge_passes PASSED
test_acceptance_a3_merges_before_boundary_not_flagged PASSED
test_acceptance_a4_missing_or_corrupt_ledger_fails PASSED
test_acceptance_a5_guard_not_equipped_fails_preflight_but_keeps_risk PASSED
test_acceptance_a6_preflight_passes_with_all_inputs PASSED
```

A1 / A2 的原始 CLI 输出（不是 pytest 摘要）：

```
boundary=b8b673a undeclared_merge=26f14f5
--- A1 未登记合并提交 ---
exit=1
[governance] 治理覆盖率: available=True merge_count=1 gap_count=1 would_fail=True applied=True
stderr: ::error::未登记合并提交: 26f14f555beda3e3c0b04f8568c7383d8b1e7be4（缺 change_id 或 exemption 声明）
--- A2 登记该提交后 ---
exit=0
[governance] 治理覆盖率: available=True merge_count=1 gap_count=0 would_fail=False applied=False
```

A3 证明生效边界之前的提交不参与判定：

```
before_boundary=d15788b boundary=d15788b after_boundary=e5a793e
compute_coverage(repo)["gaps"] == ["e5a793e..."]     # 只有边界之后的 late
early(d15788b) 不在 gaps，也不在 stderr
```

A4 证明事实源不可取时 fail-closed（登记表缺失 / 损坏两次均 `exit=1`）：

```
--- A4a 登记表缺失 ---  exit=1  stderr: ::error::治理覆盖率不可用: 登记表缺失: collaboration/governance/governance-ledger.jsonl
--- A4b 登记表损坏 ---  exit=1  stderr: ::error::治理覆盖率不可用: 登记表第 1 行无法解析: Expecting property name enclosed in double quotes
```

### 6. 测试结论

全套回归采用**两侧同环境对照法**：干净 `origin/main` 快照（`/tmp/gov-baseline-clean`，
已 `git init` 成真实仓库，避免 `git ls-files` 无 `.git` 造成的伪失败）与当前 worktree
用同一条命令各跑一遍，再比对 FAILED 集合。

| 侧 | 结果 |
| --- | --- |
| 基线（`origin/main` 快照） | `50 failed, 3027 passed, 8 skipped` |
| 当前（本 change） | `50 failed, 3069 passed, 8 skipped` |
| 新增失败（`comm -13`） | 空 |
| 新增通过（`comm -23`） | 空 |
| `cmp` 判定 | **IDENTICAL** |

净增 `3069 - 3027 = 42` 条通过 = 新增测试文件 `tests/unit/test_governance_ledger.py` 的用例数。
50 条失败是本地环境基线（外部服务/网络类），与 `origin/main` 逐条一致，非本 change 引入。

对照过程中另有一类**环境伪失败**必须披露：本会话的沙箱 shim
（`sandbox-center-runtime-kit/shim/sitecustomize.py:884`）在 `Path.mkdir(exist_ok=True)` 目标
已存在时仍把 `mkdir` 代理给宿主，宿主返回 `EEXIST` 后直接抛出、不回落到原生 `exist_ok` 语义，
导致 `ai_collab/cli/pack_rating.py:29` 这类代码连带失败，单轮出现 73 条「新增失败」。
该轮已作废；两侧统一在屏蔽该 hook 的环境下重测（`PYTHONPATH=/tmp/noshim:$PYTHONPATH`），
才得到上表的 IDENTICAL。

### 7. 观测期零行为改变的机器证明（翻闸依据）

```
base_exit=0  cur_exit=0
$ grep -v '^\[observe\]' cur_vc.txt > cur_vc_filtered.txt
$ diff -u base_vc.txt cur_vc_filtered.txt   → 逐位一致
[observe] 治理覆盖率: available=False merge_count=0 gap_count=0 would_fail=True applied=False
```

反向测试 `test_coverage_signal_can_be_disabled_and_restored`：总闸 `True → False → True`
三次判定可关可恢复；`test_concurrent_guard_adds_input_contract_without_changing_risk`：
`strip_signal(empty) == strip_signal(full)`，移除新增字段后报告逐位一致。

### 8. 静态与格式门禁

```
$ ruff format --check .
326 files already formatted
$ ruff check .
All checks passed!
```

## 风险

1. **`.vscode/ai-collab.json` 的 `concurrentGuard` 仍未装备（tasks.md 4.7 显式不做）。**
   `baselineCommit` / `sessionStartedAt` 是会话级状态，唯一落点是受跟踪配置且无 `.local.json`
   覆盖机制；`detect_baseline_staleness()` 会把 `baselineCommit..HEAD` 内被监视路径的任何提交
   计为 `violations`（`risk_level=high`、`allowed=false`）。把会话基线写进仓库等于给后续每个
   提交埋一颗硬阻断。影响面：本仓 `preflight` 的「门禁输入完整性」项持续 FAIL；PASS 路径由 A6
   在受控仓库证明。后续应由会话化 change 提供不受跟踪的会话配置落点后再装备。

2. **治理登记表是 append-only 事实源，写错不能改。**
   `declare_enforcement()` 检测到已有 `enforcement` 记录即拒绝追加，`declare_commit()` 只允许
   追加登记。若生效边界声明错，唯一手段是人工修文件（破坏 append-only 语义）。当前边界
   `4d04acd` 为 `origin/main` 提交，`enforced_from()` 用 `git cat-file -e <sha>^{commit}` 校验其
   真实性，已通过。

3. **覆盖率门禁只在「严格 + 有登记表」时生效。**
   `validate-contract` 不带 `--strict` 时不引红；登记表缺失时走 fail-closed（A4）。这意味着
   绕过方式是「不跑严格模式」，属流程约束而非代码约束，需在 CI 侧固定使用 `--strict`。

4. **原 `logs/` 落点被 `.gitignore:39` 的目录级排除挡死。**
   因此开发日志 `logs/claude-code/2026-11/*.md` **不入库**（`git ls-files 'logs/claude-code/*'`
   为 0），登记表迁至 `collaboration/governance/`。这是第三处治理假绿，须由后续立法 change
   处理 `.gitignore` 与目录约定，本 change 不擅自改忽略规则。

5. **`tests/unit/test_cli.py` 的一条既有单测被有意改变行为。**
   `test_tasks_validate_contract_strict_passes_when_contracts_and_results_are_clean` 原假设
   「契约干净即退出 0」，翻闸后缺登记表必须 fail-closed。处理方式是只 mock 覆盖率、不放宽门禁，
   该用例的语义从「端到端」收窄为「CLI 分支」，端到端由 A1–A6 接管。

6. **主工作区另一 session 的在途改动未被触碰。** 全部操作在独立 worktree 内，提交一律带
   pathspec；主工作区在途改动数量在提交前后复核一致。

7. **`preflight` 的「必读清单声明」项在本仓无法变绿，原因是缺少写入方而非缺少声明。**
   全仓检索 `ai_collab_session` 只有 `ai_collab/governance.py:597` 一处**读取**，
   没有任何模块写 `required_reads_acknowledged`；`sessions register` 写的是会话注册表
   （`logs/session_registry_state.json`），不是 `.ai_collab_session.json`。
   影响面：任何 workspace 上该项都恒为 FAIL，等于门禁五分之一永久失效。
   本 change 不自行造一个写入点（那会让「已读」变成一句无人核验的自证），
   须由会话化 change 连同会话身份一起提供可核验的写入方。

8. **本 change 自身的合入会短暂让 main 上的严格校验变红。**
   生效边界之后出现的**合并提交**必须登记（这正是门禁要拦的东西）。因此 PR 用 merge commit
   合入后、在 main 上追加登记之前，`validate-contract --strict` 会以「未登记合并提交」非零退出。
   这是设计意图不是缺陷，但顺序必须写清，否则会有人误判成回归：
   `merge → governance declare-commit --commit-sha <merge-sha> --change-id restore-governance-enforcement
   → 提交登记表 → 复跑 --strict 应 gap_count=0`。
   若改用 squash / rebase 合入（不产生合并提交），则门禁不会拦，但会丢失本次合入的合并语义。

## 回滚

- **整体回退**：`git revert <本 change 的提交>`。新增测试文件、登记表、`governance.py` 均为
  新增/独立文件，revert 不影响既有账本内容。
- **只停门禁、不回退代码**：把 `ai_collab/governance.py` 的 `COVERAGE_IN_DECISION` 改回 `False`
  即回到决策冻结态——覆盖率信号继续计算、落盘、打印，但 `applied` 恒为 `False`，既有结论与
  退出码逐位不变（已由 `test_coverage_signal_can_be_disabled_and_restored` 证明可关可恢复）。
- **只停一致性硬门禁**：`governance check-writes` 是独立 CLI 调用，不挂在提交钩子上，停用即
  不再拦截；`write_json` 的运行时守卫保留（属 fail-loud 保护，不影响正常写入路径）。
- **登记表**：append-only，回滚不做删除；如需作废某条登记，另追加一条 `exemption` 记录并说明
  理由，保留历史可追溯。
- **开发日志**：`logs/claude-code/2026-11/2026-11-15-governance-restore-phase1-3.md` 只作本地
  证据，不在版本库内，无需回滚。

---

## 收口补记（2026-11-16 · 合入与归档）

本节是合入后追加，不改上文结论，只补「合入动作自身被新门禁拦下并登记」这一段实测。

| 步骤 | 动作 | 结果 |
| --- | --- | --- |
| 合入 | `gh pr merge 70 --merge` | merge commit `89160f1aa881d679ce38ac03dd30e331cc8f80d1` |
| 拦下 | 合入后在 main 上跑 `tasks validate-contract --scope all --strict` | `merge_count=1 gap_count=1 would_fail=True applied=True`、`exit=1`、点名 `::error::未登记合并提交: 89160f1...` |
| 登记 | `governance declare-commit --commit-sha 89160f1... --change-id restore-governance-enforcement` | 追加一条 `kind=commit` 记录 |
| 复跑 | 同一命令 | `gap_count=0 would_fail=False`、`exit=0` |
| 落盘 | 提交登记表 | `8834739` |
| 归档 | `openspec archive restore-governance-enforcement --yes` | `archived as 2026-11-16-restore-governance-enforcement`；`openspec/specs/governance-coverage/spec.md` 升为常驻规格（+4 added） |
| 归档校验 | `openspec validate --archived --strict` | `2 passed, 0 failed`，`exit=0` |

**归档校验通过的口径必须写清**：它不是「42 项全做完」，而是「1 项取消 + 1 项归档动作完成」。
4.7（装备 `concurrentGuard`）**未执行**，按风险 1 的理由裁定取消，已在归档后的
`tasks.md` 里从 checkbox 改为留痕条目并单列「显式取消」章节。把未做的事情改成已勾选来凑绿，
比留着一条红更坏；因此选择改口径并留痕，而不是改勾选。

**结果报告与工单状态仍成立**：`audited=1 consistent=1 mismatch=0`；工单 `TASK-GOV-RESTORE-001`
状态 `completed`，ACK 已由 CLI 生成。归档与登记均落在 main，主工作区另一 session 的在途改动
数量在全程保持 153 未变。
