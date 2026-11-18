# PLAN — DeepSeek 解冻：正常流程、影响面与解冻前测试论证（2026-11-19）

- **状态**: plan-only（本轮**不改**白名单、不建 openspec change、不跑真机）
- 日期：2026-11-19
- 执行者：`claude_code`（AGENT_EXEC）
- 工作区：`/Users/raymondna/Documents/AI-collab/ai-collab-base`（`main @ 4eb3d51`）
- 前置：N55 已关（723s 假超时修好，8/8、81.58s）、N57 已关（长回答不缺字）

> **口径声明**
>
> 1. 本文件是**提案**，不是已执行记录。开工前需要用户对 §5 的三项裁定点头。
> 2. §2 的影响面、§4 的 9 条红是**实测**出来的（在 `/tmp` 的两份副本上跑，
>    工作区一个字节没动），不是读代码猜的。
> 3. 「合格」比「解冻」严：解冻是许可，合格是能力。§3 的 8 条命题里目前
>    **3 条未证、1 条不可证**——这才是现在不能解冻的真实原因，不是流程没走。

## 1 · 正常解冻流程（按 stepfun 先例，五阶段）

仓里已经有过一次同类改判：`openspec/changes/archive/2026-11-18-replace-qianwen-with-stepfun/`
（qianwen → stepfun）。那次是「换站」，这次是「把冻结站转正」，骨架一样。

| 阶段 | 做什么 | 判据 / 产物 |
|---|---|---|
| **P0 立项** | 先有用户裁定原文，再建 `openspec/changes/unfreeze-deepseek/`（`proposal.md` / `tasks.md` / `specs/active-platform-registry/spec.md` 增量） | `openspec validate unfreeze-deepseek --strict` 零错误 |
| **P1 取证** | 登录事实 → 只读 DOM 探针 → 真实快照 → 发送链路 → 长回答完整性 | 每条选择器有真机命中数，不是「跑通过一次」 |
| **P2 改常量与门禁同步** | 白名单加 deepseek、冻结名单去掉 deepseek、测试期望、变异锚、spec 场景 | 离线全量门禁绿（§2 清单一条不漏） |
| **P3 离线门禁** | 单测 / 适配器矩阵 / 变异检查 / build / Python 门禁 | 4 类全绿，变异 0 存活 |
| **P4 真机验收** | **不带 `ALLOW_FROZEN`** 跑完整 L2；其余 5 站复验无回归；longcat 零触碰 | 回执 `platformPolicy = {allowed:true, active:true, unfrozenBy:null}` |
| **P5 收口** | RESULT 报告 + `known_gaps` 登记裁定 + 归档 change + `validate --archived --strict` | 磁盘可复核「谁在什么时候解冻的」 |

**P4 是关键**：今天那次 8/8 回执写的是 `active:false / unfrozenBy:"ALLOW_FROZEN=1"`。
那证明「它能跑」，**不证明「它作为活跃源能跑」**——后者才要求 `active:true` 且不许带例外开关。

## 2 · 影响面清单（实测：只改常量会让 9 条断言变红 + 1 条变异锚失效）

### 2.1 必须改的代码/常量

| 文件:行 | 现值 | 改成 |
|---|---|---|
| `tests/real-machine/platform-freeze.mjs:46-52` | `ACTIVE_PLATFORM_IDS = [stepfun, yuanbao, chatglm, yiyan, kimi]` | 加 `deepseek` |
| `tests/real-machine/platform-freeze.mjs:55` | `FROZEN_AB_PLATFORMS = ["deepseek","longcat"]` | `["longcat"]` |
| `tests/platform-freeze.test.mjs:30` | 「白名单恰好是 5 个活跃站，不含 deepseek / longcat / qianwen」 | 改 6 个、只剩 longcat / qianwen 不含 |
| `tests/platform-freeze.test.mjs:64` | 拿 deepseek 当「冻结样本」演示 `ALLOW_FROZEN=1` | 换 longcat |
| `tests/platform-freeze.test.mjs:134` | N35 回归：用 deepseek 当「真的解冻过」的样本 | 换 longcat |
| `tests/platform-freeze.test.mjs:154` | 同上 | 换 longcat |
| `tests/session-wall-ab.test.mjs:53/59/68/154/163` | 断言 A/B 计划的冻结对**恰好是 deepseek + longcat**、4 条命令里两站齐现 | 只针对 longcat，或整体退役（见 §5 裁定 B） |
| `tests/platform-freeze.test.mjs:55` | 测试名「活跃 5 站默认放行」——断言是遍历式的，不会红 | 仅需改名（**假绿**：名字说 5 站，实际跑 6 站） |
| `tests/real-machine/mutation-check.mjs:1205-1213` | 锚点「把 deepseek 悄悄加进活跃白名单」，`find` 匹配 `[\n  "stepfun",` | 换成注入 longcat / 未登记 id；`expectTest` 跟着改（见 2.3） |

### 2.2 跟着语义漂移、但不报错的地方

- `tests/real-machine/l2-platform-auto.mjs:74`：`CANDIDATES` 默认由白名单派生 ⇒ 解冻后**预检默认会打开 6 个站**。这不是 bug，但成本与「不去碰」的边界都变了，得在 change 里写明。
- `tests/real-machine/session-wall-ab.mjs:164`：用 `FROZEN_AB_PLATFORMS` 生成计划 ⇒ 解冻后计划只剩 longcat 一站，A/B 对照失去意义。
- `docs/EXAMPLE-ACCEPTANCE-MATRIX.md:64`：把 deepseek 记作「冻结 A/B 样本」，引用的 `platform-freeze.mjs:52` 行号已经漂了。
- `openspec/specs/active-platform-registry/spec.md` 的 Scenario「deepseek / longcat 退出目标源」明确写「`ACTIVE_PLATFORM_IDS` 仍是不含这两站的 5 站白名单」——**这条 Scenario 必须被新 change 的场景取代**，否则规范与代码直接打架。

### 2.3 变异锚会「失效」而不是「变红」（这条最容易漏）

实测：改完常量后在副本里跑 `MUTATION_TESTFILE=platform-freeze.test.mjs`，结果是

```
✗ 把 deepseek 悄悄加进活跃白名单：在 real-machine/platform-freeze.mjs 里找不到待替换片段
  ——变异描述与代码脱节
变异存活 1 条——守护有洞
```

原因是锚点的 `find` 串以 `[\n  "stepfun",` 开头，而加进 deepseek 之后白名单第一行变成
`"deepseek",`，锚点**压根应用不上**。它不会给出「测试没红」这种容易看懂的信息，
而是报「变异描述与代码脱节」——不处理就会让 CI 在解冻后一直红。

⇒ 解冻时必须**同时**改写这个锚点（建议改成「把 longcat 悄悄加进白名单」，并且
`expectTest` 跟着测试改名一起更新）。

## 3 · 解冻前必须证明的 8 条 + 1 条跨站（这是「论证」的主体）

每条都写成**可证伪**的形式：给判据、给当前证据、给结论。结论只有三种：已证 / 未证 / 不可证。

| # | 命题 | 证伪判据 | 当前证据 | 结论 |
|---|---|---|---|---|
| P1 | 选择器契约在真机仍然成立 | 探针逐项命中数与历史一致 | 11-18 实采 3/5/8 与 11-11 探针逐项吻合；`deepseek.json` 落地页快照 | ✅ 已证（仅落地页） |
| P2 | 忙闲判据不会恒真 | 空闲页上 `isTyping()` 必须 false | N55：单测 5 条 + 变异锚 + 8/8；诱饵元素 `site_logo_loading` | ✅ 已证 |
| P3 | 长回答不缺字 | 点击/滚动前后 `textContent.length` 不变且等于回执长度 | N57：1049/8/8 三态恒定，与回执逐字对齐 | ✅ 已证 |
| P4 | 会话重置真的发生 | `sessionResets[0].available && after < before` | fix1 回执：`strategy: adapter-text-match, 3→0, 322ms` | ✅ 已证 |
| P5 | 8 步 Pack 能跑完 | 回执 `status=completed`、8/8 | fix1：8/8、81.58s；历史 11-12~11-14 连续 5 轮 | ✅ 已证 |
| P6 | **不依赖例外开关也能跑** | 不带 `ALLOW_FROZEN` 跑 8/8，且 `unfrozenBy=null && active=true` | 无。今天那次是 `active:false` 的放行 | ❌ **未证（必须解冻后才能跑，属于 P4 阶段）** |
| P7 | 发送链路可用 | `getSendButton()` 命中 ≥1，或「走 Enter」被显式承认为设计 | **N54 open**：落地页 `<button>` 数为 0，4 条 sendButton 恒 0 命中，一直走 Enter 兜底 | ❌ **未证** |
| P8 | 反自动化可控 | 回执里出现验证码/WAF/风控信号并能归因 | 无。历史回执只有 `Response timeout`；N25 原文定性为「产品裁定，非实测」 | ⚠️ **不可证（无采集手段）** |

另有一条**非** deepseek 专属、但解冻会碰到的：

| # | 命题 | 判据 | 现状 |
|---|---|---|---|
| P9 | 其余 5 站无回归 | 5/5 各自 8/8 + 会话重置 | 最近一次全量是 11-18 早前（`RESULT-ACTIVE5-VERIFICATION`），**不是本轮**。解冻改动只动测试与常量，理论上不影响生产逻辑，但仍应按 P4 复验 |

**结论**：P1–P5 已证，所以「它能跑」成立；P6 是解冻流程本身的产物（不可提前证）；
**P7 是唯一可以在解冻前就能补、但还没补的**；P8 需要单独裁定「接受为已知空白」。

## 4 · 已经做过的演练（数字都是跑出来的）

在 `/tmp/unfreeze-baseline` 与 `/tmp/unfreeze-dryrun` 两份副本上（`rsync` 排除
`node_modules`/`dist`，`node_modules` 用软链），只改 §2.1 的两行常量，然后全量对跑：

```
基线（未改）       241 passed / 5 failed
改常量后           232 passed / 14 failed
```

5 条基线失败是**环境**造成的（`/tmp` 下没有 git 仓库、缺 N36 的文档路径），不是代码问题；
把两边相减，得到**净增 9 条红**：

```
platform-freeze.test.mjs
  125 白名单恰好是 5 个活跃站，不含 deepseek / longcat / qianwen
  129 只有 ALLOW_FROZEN=1 才放行冻结平台，并在回执里留痕
  135 N35 回归：预检 + 真的解冻过，仍不许打
  137 真正解冻过 ⇒ 打，且靠 unfrozenBy 而非 active 判定
session-wall-ab.test.mjs
  178 方案默认标注「未执行」，不冒充真机回执
  179 冻结的两个站恰好是当初真正撞墙的 deepseek / longcat
  180 变体是 A/B 两组，且只差 fresh_session 一个变量
  187 计划命令里不许再出现 <...> 占位符
  188 4 条 L2 命令的 PACK_PATH 指向真实绝对路径，且 A/B 各用各的文件
```

外加 §2.3 那条「变异锚失效」。⇒ §2 的清单是**穷举**的（至少在当前 HEAD 上）。

### 4.1 顺带发现的规范卫生问题

`openspec validate --specs --strict` 现在就是 4 红：

```
✓ concurrent-workspace-safety    ✓ governance-coverage
✗ active-platform-registry       ✗ new-session-boundary
✗ task-contract                  ✗ tracked-artifact-hygiene
Totals: 2 passed, 4 failed (6 items)
```

四份都是同一个原因：`## Purpose` 还是 `openspec archive` 写的占位符
（`TBD - created by archiving change ...`）。要改的正是 `active-platform-registry`，
所以**改 spec 时顺手把这个 Purpose 补上**，否则「新 change 严格通过、被改的 spec 自己不过」
这种话没法对外说。已登记 N58。

## 5 · 需要你裁定的三件事

**A. P7（发送链路）怎么处理？**
　① 补 sendButton 选择器（难：落地页无 `<button>`，发送箭头是 `div.ds-icon > svg`，祖先六层全哈希类名）；
　② 承认「走 Enter」是设计，把 `sendButton` 留空并在矩阵里显式记 SKIP 原因（N54 的建议）；
　③ 解冻前不动，作为已知空白写进 change。

**B. `session-wall-ab` 这套 A/B 工件留不留？**
　它服务的是 N25（会话边界解命题），该命题已按「目标源退出」关闭。解冻 deepseek 后，
　它要么退役（删计划与断言），要么改成只对 longcat。两者的测试改动量不同（§2.1 最后一行）。

**C. P8（反自动化）接受为已知空白，还是要先做信号采集？**
　现有回执只有 `Response timeout`，没有任何风控信号。若要做采集，得先设计指标
　（验证码出现率、429/风控页、响应时长分布漂移），这是一件独立的事，不该塞进解冻 change。

## 6 · 若决定解冻，最小执行顺序

1. 你给裁定原文 → 建 `openspec/changes/unfreeze-deepseek/`（P0）
2. 按 §2 清单改（含 §2.3 的锚点改写、spec 的 Purpose 与 Scenario 更新）
3. `openspec validate unfreeze-deepseek --strict` + 离线四类门禁全绿
4. **不带** `ALLOW_FROZEN` 跑 deepseek 8/8，回执须 `active:true && unfrozenBy:null`
5. 5 个活跃站各跑一轮无回归；longcat 零触碰（回执里不应出现 longcat）
6. RESULT + `known_gaps` 登记裁定时间/依据 + 归档 + `validate --archived --strict`

## 7 · 回滚

一条 `git revert` 就能回到 5 站白名单：常量、测试期望、变异锚、spec Scenario 在同一个
change 里，原子回滚。真机回执与证据是只读留档，不随回滚删除。
