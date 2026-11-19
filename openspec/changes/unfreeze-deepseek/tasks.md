# Implementation Tasks

> 凡勾选者必须附**实测证据（命令 + 关键输出）**，不写「已完成」了事。
> **P1–P4 的前置条件是用户裁定原文（点名平台 + 允许范围）。未拿到就一律不勾、不执行。**
> 本 change 提案通过只表示「准备好待批」，不表示解冻生效。

## Phase 0 · 立项（本次完成，可独立验收）

- [x] 0.1 产出 proposal / spec delta / tasks，`openspec validate unfreeze-deepseek --strict` 零错误
- [x] 0.2 把 C 段「反自动化不在范围、且非 deepseek 特有」落成提案与 spec 要求（N61）
- [x] 0.3 记录未解冻基线：单测 413 / 矩阵 108/125 / 变异 178/178 / 台账 61 条

## Phase 1 · 用户裁定原文 + N60（未执行）

- [ ] 1.1 用户裁定原文落档：点名 deepseek + 允许范围 + 时间；无原文不进 P2
- [ ] 1.2 N60：经单独放行后跑只读探针，落盘发送区 `outerHTML` 与祖先 3 层，回填 N54
- [ ] 1.3 若不放行：交付说明如实写「发送区 DOM 无工件」，不假装已还原

## Phase 2 · 常量与门禁同步（未执行）

- [ ] 2.1 `ACTIVE_PLATFORM_IDS` 加 deepseek、`FROZEN_AB_PLATFORMS` 与 `AB_PLATFORMS` 同步
- [ ] 2.2 `tests/platform-freeze.test.mjs` 的 4 条断言**换样例而非删断言**
      （`:30` / `:40` / `:139` / `:155`），改后仍 0 红
- [ ] 2.3 `mutation-check.mjs` 里绑定旧常量值的 `find` 串同步，避免「变异描述与代码脱节」
- [ ] 2.4 归档写回主 spec 时，补掉 `active-platform-registry/spec.md` 的 TBD Purpose（N58）。
      本 change 的 delta 本来就要改这份 spec，顺手写掉既有占位符；
      验收：`openspec validate --specs --strict` 从 4 红降到 3 红，其余 3 条仍属 N58 待办。

## Phase 3 · 离线门禁（未执行）

- [ ] 3.1 9 条前置断言全绿，未解冻基线数字不倒退（413 / 108/125 / 178）
- [ ] 3.2 `dist` 与源码一致性核；按构建一致性口径陈述，不引用不存在的门禁编号（N38）
- [ ] 3.3 `openspec validate unfreeze-deepseek --strict` 复验

## Phase 4 · 真机验收与收口（未执行）

- [ ] 4.1 **不带** `ALLOW_FROZEN` 跑 deepseek 8/8，回执 `active:true && unfrozenBy:null`
- [ ] 4.2 5 个活跃站各一轮无回归；longcat 零触碰（回执里不出现 longcat）
- [ ] 4.3 RESULT + `known_gaps` 登记裁定时间 / 依据 / 数字 → 归档 →
      `openspec validate unfreeze-deepseek --archived --strict`
- [ ] 4.4 交付说明按 N61 写反自动化段落：不在范围、5 活跃站同样无基线

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
