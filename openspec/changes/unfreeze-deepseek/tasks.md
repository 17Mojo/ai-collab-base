# Implementation Tasks

> 凡勾选者必须附**实测证据（命令 + 关键输出）**，不写「已完成」了事。
> **P1–P4 的前置条件是用户裁定原文（点名平台 + 允许范围）。未拿到就一律不勾、不执行。**
> 本 change 提案通过只表示「准备好待批」，不表示解冻生效。

## Phase 0 · 立项（本次完成，可独立验收）

- [x] 0.1 产出 proposal / spec delta / tasks，`openspec validate unfreeze-deepseek --strict` 零错误
- [x] 0.2 把 C 段「反自动化不在范围、且非 deepseek 特有」落成提案与 spec 要求（N61）
- [x] 0.3 记录未解冻基线：单测 413 / 矩阵 108/125 / 变异 178/178 / 台账 61 条
- [x] 0.4 补齐 4 份 spec 的 TBD Purpose（关闭 N58），`openspec validate --specs --strict` 6/6
      见「P0 · N58」段；这一步不需要解冻授权，故提前做掉，没挂在 P2 后面

## Phase 1 · 用户裁定原文 + N60（未执行）

- [x] 1.1 用户裁定原文落档：点名 deepseek + 允许范围 + 时间（2026-11-19 选项授权）
      → `collaboration/results/RESULT-DEEPSEEK-UNFREEZE-2026-11-19.md` §1
- [ ] 1.2 N60：经单独放行后跑只读探针，落盘发送区 `outerHTML` 与祖先 3 层，回填 N54
      **本次未放行，不执行**
- [x] 1.3 不放行 ⇒ RESULT §1 已写「发送区 DOM 从未落盘」，不假装已还原

## Phase 2 · 常量与门禁同步（未执行）

- [x] 2.1 `ACTIVE_PLATFORM_IDS` 加 deepseek → 6 站；`FROZEN_AB_PLATFORMS` → `["longcat"]`；
      `AB_PLATFORMS` 仍 `["longcat"]`（deepseek 解冻不等于重开 N25 的 A/B 命题）
- [x] 2.2 `tests/platform-freeze.test.mjs` **4 条红实测定位**（#1 / #5 / #11 / #13，
      与 PLAN 预估行号不同，按磁盘事实改）：白名单计数 5→6、冻结样例 deepseek→longcat、
      N35 两条样例 deepseek→longcat；**没有删任何断言**，另补 1 条正向断言钉住
      「deepseek 真活跃且 `unfrozenBy=null`」。改后 16/16 绿
- [x] 2.3 `mutation-check.mjs` 锚「把 deepseek 悄悄加进白名单」改为 **longcat**（deepseek 已授权，
      原锚失去原义）；闸门锚的 why 同步；局部变异 7/7 被杀
- [x] 2.4 主 spec 过期的「5 站白名单」Scenario 用 change delta 的 `## MODIFIED Requirements`
      覆盖；open-spec 校验要求保留原 Scenario 名，第一次加后缀被拒后改正。docs 验收矩阵同步，
      历史 RESULT 数字不改

## Phase 3 · 离线门禁（未执行）

- [x] 3.1 前置断言全绿，基线数字不倒退：**415 单测 / 108/125 矩阵 / 178 变异全杀**
- [x] 3.2 `node build.js` 后 `git status chrome-extension/dist/` 零 diff ⇒ 源码与产物一致；
      按构建一致性口径陈述，不引用不存在的门禁编号（N38）
- [x] 3.3 `openspec validate --all --strict` → 7 passed / 0 failed

## Phase 4 · 真机验收与收口（未执行）

- [x] 4.1 **不带** `ALLOW_FROZEN` 跑 deepseek **8/8**，`errors=[]`，
      回执 `active:true && unfrozenBy:null`；`sessionResets[0].available=true / 3→0`
- [ ] 4.2 5 个活跃站各一轮无回归 — **本轮 5/5 失败，未达成**（N62 open）。
      longcat 零触碰已核（今日工件 `grep -l longcat` 零命中）
- [ ] 4.3 归档 — **未做**：4.2 未达成，不执行 `openspec archive`（它会把 delta 写回主 spec）。
      澄清：`validate unfreeze-deepseek --archived --strict` 返回 11 passed，但其中**不含**
      本 change——`--archived` 只校验已归档项，这个绿不是归档证据。RESULT 与台账已写
- [x] 4.4 交付说明按 N61 写反自动化段落：不在范围、5 活跃站同样无基线，
      L1 那 6 条 `bot_check` 阳性只在 chatgpt / claude 两个非活跃站

## 实测证据

### P0 · 工件与校验

```
$ ls openspec/changes/unfreeze-deepseek/
proposal.md  tasks.md  specs/
$ openspec validate unfreeze-deepseek --strict
Change 'unfreeze-deepseek' is valid
（exit 0）
```

### P0 · 未解冻基线（来自 2026-11-19 实测，非推测）

```
扩展单测：  # tests 413 / pass 413 / fail 0
适配器矩阵：Total: 108/125 passed, 0 failed, 17 skipped
全量变异：  === 变异检查（178 条 / 全量）=== ; 178 个 ✓ / 0 个 ✗
台账：      61 gaps — 53 closed / 7 open / 1 wontfix
守护测试：  test_declared_env_and_gaps.py 6 passed;
            test_protocol_gate_ids.py 3 passed
```

### P0 · N58（4 份 spec 的 Purpose）

```
$ openspec validate --specs --strict     # 改前
Totals: 2 passed, 4 failed (6 items)
$ openspec validate --specs --strict     # 改后
✓ spec/active-platform-registry
✓ spec/concurrent-workspace-safety
✓ spec/governance-coverage
✓ spec/new-session-boundary
✓ spec/task-contract
✓ spec/tracked-artifact-hygiene
Totals: 6 passed, 0 failed (6 items)
$ openspec validate unfreeze-deepseek --strict    # 交叉复验
Change 'unfreeze-deepseek' is valid
台账：61 条，54 closed / 6 open / 1 wontfix（N58 closed）
```

### P2 · 常量与断言（实测）

```
$ node --test chrome-extension/tests/platform-freeze.test.mjs   # 改常量后
not ok 1  白名单恰好是 5 个活跃站
not ok 5  只有 ALLOW_FROZEN=1 才放行冻结平台
not ok 11 N35 回归：预检 + 真的解冻过
not ok 13 真正解冻过 ⇒ 打
# tests 15 / pass 11 / fail 4     ← 与 PLAN 预估的 4 条数量一致，具体条目不同

$ node --test ...   # 换样例 + 补 1 条正向断言后
# tests 16 / pass 16 / fail 0

$ MUTATION_TESTFILE=platform-freeze.test.mjs node tests/real-machine/mutation-check.mjs
=== 变异检查（7 条 / 仅 platform-freeze.test.mjs）===
7 个 ✓ / 0 个 ✗
```

### P3 · 离线门禁（实测）

```
$ node tests/run-tests.mjs
# tests 415 / pass 415 / fail 0；[test-inventory] 33/33 跟踪、0 未跟踪
$ node tests/adapter-matrix/adapter-test-runner.js
Total: 108/125 passed, 0 failed, 17 skipped
$ node build.js && git status chrome-extension/dist/     # 无输出 ⇒ 产物一致
$ openspec validate --all --strict
Totals: 7 passed, 0 failed (7 items)
$ python3 -m pytest tests/unit/test_declared_env_and_gaps.py tests/unit/test_protocol_gate_ids.py
9 passed

全量变异第一次跑出 **1 条存活**：「session-wall-ab 改回读冻结名单当实验对象」。
根因不是锚写错，而是解冻后 `AB_PLATFORMS` 与 `FROZEN_AB_PLATFORMS` 都等于
`["longcat"]` —— 改回去在值层面是**等价变换**，任何值级断言数学上都不可能红。
修法：补一条**结构性断言**（验 `platforms` 的来源表达式只能出现 `AB_PLATFORMS`），
锚的 expectTest 指向它。局部 14/14 被杀后重跑全量：

=== 变异检查（178 条 / 全量）===
178 个 ✓ / 0 个 ✗
（exit=1 是宿主沙箱拒绝删除 214 文件的 `.mutation-tmp`，不是锚存活）
```
