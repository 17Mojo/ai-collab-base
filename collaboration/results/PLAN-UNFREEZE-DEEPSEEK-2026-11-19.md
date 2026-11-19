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
| P7 | 发送链路可用 | `getSendButton()` 命中 ≥1，或「走 Enter」被显式承认为设计**且有测试** | **N54 + N59**：真机落地页 `<button>` 数为 0；矩阵那条不是 SKIP 而是 **PASS**——mock 里摆了一个真机不存在的 `<button data-testid=send-button aria-label=发送 class=send-button>`，三条选择器同时命中（自证循环）。同站真机快照 `sendButtonFound:false` 与它矛盾，两份证据从未对账 | ❌ **未证，且被一条假 PASS 盖住** |
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

## 5 · 三件裁定的解法（我的建议）

### A · P7 发送链路：不补选择器，先修「假绿」，再把 Enter 变成有守护的主路径

分三步，全部离线可做，不需要额度：

1. **让两份证据对账**（N59 ①）：矩阵跑 send-button 断言时读同站真实快照的 `sendButtonFound`；
   「真机没有、mock 有」直接 **FAIL 并指名道姓**。这一步不动任何 fixture，就能把 9 条假绿变成红——
   先让门禁说真话，再谈解冻。
2. **重建 fixture 的发送区**：删掉 `mock-dom-deepseek.html:45` 那个真机不存在的 `<button>`，
   换成真机形态（`div.ds-icon > svg`，不标 `data-role`）；fixture 头部加
   `data-expect-send-button="none"`；矩阵支持该声明 ⇒ 断言变为「`getSendButton()` 必须返回 null」。
   站点将来真加了 button，这条会红，逼我们重新评估。
3. **adapter 收口**：清空 4 条 `button[...]` 死选择器（`sendButton: []` + 注释写清理由），
   并给 Enter 兜底补测试 + 变异锚（删掉 `dispatchEvent` ⇒ 测试必须红）。

**不选「位置锚定 / 哈希类名」**：那只是把今天的猜测写死，站点改版即漂；而且  它会让 PASS 变成
「命中了一个我们瞎猜的元素」，比没有更危险。

**A3 实测（2026-11-19，已完成）**

- `SELECTORS.sendButton: []`，原位置写了长注释。判据是**采过的**而不是推的：
  `fixtures/real/deepseek.json` 的 `sendButtonFound=false` 正是这四条选择器在登录态真机页面上
  跑出来的结果——不是猜测，是采集器留的痕。`findElement([])` 不循环，直接返回 null。
- `clickSend()` 保留「有按钮就点、没有就按 Enter」的形状，但注释写明**当前第一条是死分支**，
  以及为什么保留（N60 补采后不用再改一次）。**不许**读成「按钮路径也被测过了」。
- 新增 `tests/deepseek-clicksend.test.mjs`（7 用例）：事件形状（`type`/`key`/`code`/`bubbles`
  一个都不能少）、真的派发到输入框、真的冒泡到 document、没有输入框时不乱发键、
  按钮分支仍活着（有按钮就点 / disabled 就回落 Enter）。
- **改前状态必须记下**：这条 Enter 兜底此前**一行测试都没有**。把那三行 `dispatchEvent` 删掉，
  整套测试照样全绿，而 deepseek 会静默发不出消息、卡到 Response timeout。
  「一直能用」是运气，不是验证。
- 4 条变异锚：Enter 被掐掉 / 事件不冒泡 / 把猜的选择器塞回去 / 按钮分支被删，4/4 被杀。
- **又抓到自己一条错**：`spyKeydown` 原来写 `addEventListener(..., true)`（捕获阶段），
  捕获不看 `bubbles`，于是「测冒泡」的用例根本测不出冒泡——变异锚「不冒泡」在这条用例下**存活**，
  才发现用例写反了。改成冒泡阶段后才杀死。这是同一天里第三次「断言的对象不是被测物」。
- 矩阵无变化（108/125、`--real` 20/29），N54 关闭。**N54 关闭的含义是「现有配置与证据自洽、
  唯一的活路径有守护」，不是「发送区已按真机还原」**——那件事仍然卡在 N60。

**A2 实测（2026-11-19，已完成；与上文第 2 步有一处实质偏离）**

- 落地：删掉 `mock-dom-deepseek.html` 里那个 `button[data-testid=send-button][aria-label=发送][class=send-button]`；
  `<body>` 加 `data-expect-send-button="none"`；矩阵新增纯函数 `judgeSendButtonDeclaration()`（7 态：
  `pass` / `no-declaration` / `unknown` / `self-contradictory` / `no-witness` / `contradicts-real` / `still-matches`），
  断言改为「`getSendButton()` 必须返回 null」，并要求同站真机快照当**独立见证人**（快照不可用 ⇒ 降级 SKIP，不算 PASS）。
- **实质偏离**：上面第 2 步写「换成真机形态（`div.ds-icon > svg`，不标 `data-role`）」。**没做**。原因是查证后发现
  那个形状**没有任何落盘工件**：`grep -rln ds-icon evidence/ tests/` 零命中（只有台账自己在说）；
  `fixtures/real/deepseek.html` 只有 270 字节、仅含 textarea 子树；`new-session-probe-2026-11-11.deepseek-ab-diagnostic.json`
  里的 `labeledControls: []` 只收「新建对话」类文案，**不能**当「没有发送按钮」的证据。
  凭一句话重建 fixture，只是把猜测从 adapter 挪进 fixture，PASS 会再次失去意义——那是把假绿换成假绿。
  所以 Send 区**故意留空**，缺的工件登记为 **N60**。
- 结果：矩阵 `107/125 (17 skipped)` → **`108/125 passed, 0 failed, 17 skipped`**；deepseek 由 SKIP 变 **PASS**，
  且这个 PASS 有三方见证：真机 `sendButtonFound=false` + fixture 里没有控件 + adapter 返回 null。
  严格模式仍是红，但**红的是剩下 6 站**（原 7 站减掉 deepseek），deepseek 不受影响——它的争议已经用另一种方式关掉了。
- 用例改名：`getSendButton() 命中 fixture 标注的发送按钮` → `…与 fixture 的 send-button 契约一致`。
  声明站断言的是 null，名字还写「命中」就是名字在说谎——这个项目已经因为「名字会说谎」吃过一次亏。
- 守门：`judgeSendButtonDeclaration` 8 条用例；新增 3 条变异锚（去掉 `contradicts-real` / 去掉 `still-matches` /
  runner 不读声明），6 条 send-button 锚 **6/6 被杀**。
- **又挖出一条自己的错**：事实地图测试原来用正则数 `data-role="send-button"`。fixture 的注释里引用了被删掉的那段
  标记原文（为了说清删了什么），正则把注释当成了 DOM，于是「deepseek 已经没有发送按钮」被自己的注释弄红。
  已改成 jsdom 解析，并且用**生产 adapter 自己的四条选择器**去问 DOM——问「会不会命中」，而不是「文件里有没有这几个字」。

验收：变异锚「删掉 Enter 兜底」被杀；deepseek 的 send-button 断言从**自证 PASS** 变成
**「显式断言 null」的绿**（有真机依据）。

**A1 实测（2026-11-19，已完成；A2/A3 未做）**

- 落地：`adapter-test-utils.js` 加 `readRealSnapshotMeta()` + 纯函数 `judgeSendButtonCrossCheck()`（5 态）；
  `adapter-test-runner.js` 的 send-button 断言改成「先问真机快照再断言」，`runTestAsync` 认 `{ skip: "原因" }`，
  `formatResults` 把原因打在同一行；新增 `tests/sendbutton-crosscheck.test.mjs`（12 用例）+ 3 条变异锚（3/3 被杀）。
- **偏离计划一处，且有理由**：上面第 1 步写的是「把 9 条假绿**变成红**」。实际做成 **SKIP 并写明原因**，
  红由 `STRICT_SENDBUTTON=1` 提供。理由：9 条里有 2 条（chatgpt / claude）是**快照不可用**而非矛盾，
  把它们判红等于用「环境限制」当缺陷；剩下 7 条判红则会让 main 长期带着 7 条红，红久了没人看。
  「未验证」与「坏了」必须能区分 —— 这正是 N59 想修的那个毛病（把未验证说成已验证）的镜像，
  只是方向相反：把未验证说成坏了，同样让人读不懂门禁。
- 数字：矩阵 `116/125 passed, 0 failed, 9 skipped` → `107/125 passed, 0 failed, 18 skipped`；
  严格模式单跑 deepseek `9/11, 1 failed, 1 skipped`、退出码 1。
- **顺带挖出的测试洞**：真机 11 站里 `outcome` 与 `composerFound` 恰好同真同假，所以删掉
  `composerFound === true` 这半句，「登录墙」那条用例照样全绿 —— 首轮变异锚实测**存活**。
  补了「采集成功但没找着输入框（composer 选择器漂移）」用例后才杀死。记在 N59 fix 里。
  这类洞只有变异检查能发现：用例在跑、结果也对，只是它守的不是那一行。

### B · session-wall-ab：拆掉「一个常量当两个用」

这套工件本身没错，错在**耦合**：`FROZEN_AB_PLATFORMS` 同时承担「不许碰」与「A/B 实验对象」，
所以解冻 deepseek 会连带改掉 A/B 的实验语义——§2.1 里那 5 条红就是这么来的，改动半径被无意放大。

1. 新增独立常量 `AB_PLATFORMS`（当前 `["longcat"]`），`session-wall-ab.mjs` 只读它，不再读冻结名单。
2. 断言 `session-wall-ab.test.mjs:59` 改成「A/B 对象必须是冻结站的子集」——解冻 deepseek 不再变红，
   但仍守住「不许拿活跃站当 A/B 实验对象」这条红线。
3. 4 条命令的计划工件（deepseek × 2 + longcat × 2）退役为 evidence 留档，删掉对其内容的断言
   （`:53 / :68 / :154 / :163`），或改成按新的一站计划重新生成。
4. 加变异锚：「A/B 对象越过冻结名单」⇒ 测试必须红。

N25 的历史证据一分不丢（回执与计划都还在 `evidence/`），只是脚本不再把「冻结」当成「实验对象」的同义词。

**B1/B2 实测（2026-11-19，已完成；第 3 步按「改写成推导」处理，第 4 步已做）**

- `AB_PLATFORMS = ["longcat"]`，`session-wall-ab.mjs` 改读它；`plan` 里新增 `abPlatforms`，
  `frozenPlatforms` 保持「治理事实」语义（= `FROZEN_AB_PLATFORMS`）。两个字段分开之后，
  「实验设计变了」与「治理状态变了」不再共用一个值。
- **取值不是我拍的**：写注释前逐条查了证据。deepseek 的 A/B 两轮齐全、已被 N25 裁定收口；
  longcat 的 2026-11-12 两轮是**无效**数据——`ab2-no-boundary` 第 3 步就失败（3 步成 2），
  `ab2-with-boundary` 虽跑完 8 步但 `sessionResets[0] = {available:false, strategy:"none"}`
  （adapter 没声明 newChat，重置根本没发生）⇒ 两组不可比。所以 longcat 仍待跑。
- **第 3 步换了做法**：原文写「删掉对计划内容的断言（`:53 / :68 / :154 / :163`）」。
  实际是**把写死的数字换成推导**：`runMatrix.length === AB_PLATFORMS.length × variants.length`、
  `commands.length === 2 + AB_PLATFORMS.length × 2`、额度 `${n} 站 × 2 × 8`、
  `CANDIDATES=${AB_PLATFORMS.join(",")}`。理由：删掉断言是把门拆了，改成推导是让门跟着设计走——
  下次加站不会因为我漏改一个「4」而红。只有一条真的该改判：`frozenPlatforms` 从「相等 deepseek+longcat」
  改成「⊆ 当初撞墙的两站」，因为解冻后它必然只剩 longcat，写相等就是把治理状态抄成常量。
- **实测（同一台机器、同一方法，未解冻基线 410 全绿）**：在 HEAD（531d777）上模拟解冻
  （deepseek 进 ACTIVE、`FROZEN_AB` 去掉 deepseek）⇒ `session-wall-ab` **5 红** + `platform-freeze` **4 红** = 9；
  在 B1/B2 之后同样模拟 ⇒ `session-wall-ab` **0 红**（17/17）+ `platform-freeze` **4 红** = 4。
  **§2.1 里那 5 条红确实被消掉了，改动半径回到「只碰该碰的地方」。**
- **剩下的 4 条红是 P2 的活**（不是 B 没做完）：`platform-freeze.test.mjs` 的 ①白名单恰好 5 站
  ②`ALLOW_FROZEN` 留痕用例拿 deepseek 当「冻结站样例」③④N35 预检/解冻两条同样绑定 deepseek。
  解冻时把它们换成别的冻结站（qianwen / chatgpt / claude）作为样例即可。
- 变异锚 2 条（实验对象越出冻结集 / 脚本改回读冻结名单），2/2 被杀。
- **顺带修了 2 条既有锚**：我改文案时把它们要匹配的 `find` 串改了（`"4 条命令…"` 与
  `CANDIDATES=deepseek,longcat`），两条锚立刻报「变异描述与代码脱节」。这正是 §2.3 预警过的情况，
  已同步更新 find/replace 与 expectTest。
- **改文案时揪出一条写反的事实**：`unfreezeConditions` 里「两站登录态…deepseek 此前从未被预检过，
  longcat 只有 2026-11-10 的旧快照，都不是当前态」是**过期断言**。磁盘上 `L2-precheck-2026-11-11/12/14/
  11-18*.deepseek-longcat.json` 四次预检全在，且每一份都是两站 `composerVisible=true`、
  `looksLikeLogin=false`——连 `session-wall-ab-plan-2026-11-18.json` 自己生成时（02:49:02）都已经站不住了
  （它 30 秒后跑的预检就是这两站）。改成引用 11-18 那份的真实结论：「当时满足，但快照已 1 天，正式跑前必须重跑」。
  结论没变（登录态**仍然**不构成放行理由），但理由从「没验过」变成「验过、但是旧快照」——
  两者对下一步的指令完全不同：前者要「去验」，后者要「再验一次」。
- **顺手校准 `docs/EXAMPLE-ACCEPTANCE-MATRIX.md:64-65`**：`platform-freeze.mjs:52` 漂到 `:55`；
  更重要的是「deepseek / longcat 都是冻结 A/B 样本」在拆分后语义变了——deepseek 仍是冻结样本、
  **但已不是实验对象**（`AB_PLATFORMS` 里没有它）。表格已按两件事分别写，并加了一条注说明
  「冻结样本 ≠ 实验对象」，以及「行号只作定位提示，引用以符号名 grep 为准」。

**B3 实测（2026-11-19，已完成）**

第 3 步原来写「4 条命令的计划工件退役为 evidence 留档，删掉对其内容的断言，或改成按新的
一站计划重新生成」。「重新生成」那半在 B1/B2 已做成推导；这一轮做「退役」那半。

- **先对账：这两份 JSON 不能动**。它们已在 `evidence/` 里、`status` 已是
  `plan-only / NOT-EXECUTED`、被 `.vscode/ai-collab.local.json` 的 `watchPaths` 监视着
  （N38 的修复对象）、被 `RESULT-N25-AB` 与 `RESULT-L2-MULTIPLATFORM` 引用。
  改内容 = 篡改证据 + 触发 G2 基线过期。所以「退役」不可能是「改字段」。
- **那退役只剩一件事：保证它们不会再被重写**。而 `main()` 原来是无条件
  `writeFileSync(out, ...)`，计划文件名只带**日期** ⇒ 同一天重跑一次就覆盖同名工件。
- **这不是假想**：本轮为验证脚本能跑直接执行了 `--plan`，把
  `session-wall-ab-plan-2026-11-18.json` 覆盖成了「1 站 2 命令」的版本，靠 `git checkout`
  才还原。能还原是运气——没提交过的工件盖掉就没了。**能覆盖历史证据的脚本，不该把「覆盖」
  设成默认动作。**
- **落地**：新增纯函数 `decidePlanWrite({existing, next, force})` → `create` / `identical` /
  `refuse`；`deriveVariantFiles` 把「算」与「写」拆开；`main()` 先对**全部**目标（2 个变体包 +
  1 份计划）统一判定，**任一要被覆盖就一个文件都不写**，退出码 2。放行只能靠
  `FORCE_OVERWRITE=1`；只想验证脚本能跑用 `OUT` / `PLAN_OUT_DIR` 指到别处。
- **一个必须写下来的事实**：计划 JSON 带 `generatedAt`，所以**同一天重跑内容也必然不同**
  ⇒ `identical` 对计划永远不成立，只对确定性的变体包成立。也就是说留档语义是
  「重跑一律要显式放行」，不是「内容一样就悄悄幂等」。测试按这个真实形态写，没有为了
  让门好过而把 `generatedAt` 从比对里剔掉。
- **实测（真工件）**：`OUT` 指向 `evidence/session-wall-ab-plan-2026-11-18.json`、
  `PLAN_OUT_DIR` 指临时目录 ⇒ `exit=2`，stderr 点名「A/B 计划」并给出出口，临时目录
  **0 个文件**（原子性成立），`git status` 干净（证据一字未动）。同一命令在干净目录 ⇒
  `exit=0`，3 个文件，`abPlatforms=["longcat"]`、`frozenPlatforms=["deepseek","longcat"]`、
  4 条命令。
- **数字**：单测 410 → **413**（+3 用例：判据三态 / 拒绝时整体放弃 / 重跑拒绝+放行后仍跳同内容）；
  该测试文件的变异锚 10 → **14**，14/14 被杀；矩阵 **108/125** 不变。
- **取舍（明示）**：没有为「两份旧工件里仍写着 `CANDIDATES=deepseek,longcat ALLOW_FROZEN=1`、
  照抄即碰冻结站」新开台账条目。理由：风险已被两道东西夹住——① 脚本再跑也覆盖不了它们；
  ② 本节与 `platform-freeze.mjs` 的注释都写明它们已退役、不可作为待执行计划。台账 60 条
  （53 closed / 6 open / 1 wontfix）保持不变。若将来真有人据旧工件去跑，那是**新的现场事实**，
  再登记不迟；现在记一条「可能会有人照抄」属于推测，不是缺口。

### C · P8 反自动化：接受为已知空白，但升级成跨站缺口

**不做采集器**。理由很硬：活跃站侧**没有阳性对照**——写出来的采集器只能输出「0 命中」，
那是最危险的一种安心——它会让「未采集」看起来像「没发生」。

**但原稿这里写反了一句，先更正**：原写「目前所有回执里**一个阳性样本都没有**（没有验证码、
没有 WAF、没有 429）」。逐份复核后发现——`L1-2026-10-25-zh-CN.json` /
`L1-2026-10-26-zh-CN.json` / `L1-2026-11-04-en-US.json` 里，`platforms[0]=chatgpt` 与
`platforms[1]=claude` 各有一次 `outcome=bot_check`，**合计 6 条阳性**；两份 zh-CN 还留着
Cloudflare「本网站使用安全服务防护恶意自动程序」正文与 Ray ID。是真实的平台侧信号，
不是推断。

更正后的精确口径（已登记 **N61**）：

- **阳性存在，但只在非活跃站**：6 条全属 chatgpt / claude，不在活跃 5 站白名单
  （stepfun / yuanbao / chatglm / yiyan / kimi）。所以「5 个活跃站同样没有基线」仍成立。
- **探针字段别读反**：`captchaBypass: false` 是「未使用绕过手段」的行为声明，
  不是「未遇到验证码」；`captchaOrSliderPresent: false` 只在
  `ab5-final-verdict-2026-11-14.json` 出现一次，是单次观测，不是群体基线。
- **L2 生成器 `l2-platform-auto.mjs` 全文无** captcha / waf / 429 / 风控 字段
  ⇒ **没有采集 ≠ 没有发生**。

1. 解冻 change 的「不在范围」写清：反自动化维度不在本次验证内，且**不是 deepseek 特有**——
   5 个活跃站同样没有基线；L1 那 6 条只说明两个非活跃站被平台侧拦过。
2. `known_gaps` 记一条**跨站**空白（不是 deepseek 专属），防止将来有人把「6 个源都验过了」写进交付。
   ✅ 已登记 **N61（open / P2）**，reader 写明是解冻 change 的作者与交付审阅者；
   台账 **60 → 61 条**（53 closed / **7 open** / 1 wontfix），守护测试 6 passed。
3. 真要做，等第一次真实风控信号出现后再定义指标（验证码选择器 / 429 / 单步耗时 p95 漂移），
   拿那次样本当阳性对照。**顺序不能反**：没有阳性样本先写采集器，它只会恒输出 0 命中。
4. N61 open **不阻断解冻**——它的作用是让交付说明里不许出现「反自动化已验过」这句话。
   第 1 项要等 P0 立项 `openspec/changes/unfreeze-deepseek/` 时才能落盘。

### 执行顺序（依赖关系）

```
A1 证据对账 ✅ →  B1/B2 解耦 ✅  →  A2 fixture ✅ / A3 adapter 收口 ✅  →  B3 计划退役 ✅
            →  C 跨站空白 N61 ✅  →  P0 立项 ✅  →  （用户裁定原文）
            →  P2 常量改动  →  P3 离线门禁  →  P4 真机验收
```

**A1 排最前**：它不改任何 fixture 就能把假绿变红。门禁先说实话，解冻才有意义。

## 6 · 若决定解冻，最小执行顺序

**P0 已落地（2026-11-19）**：`openspec/changes/unfreeze-deepseek/`
（`proposal.md` / `tasks.md` / `specs/active-platform-registry/spec.md`），
`openspec validate unfreeze-deepseek --strict` → `Change 'unfreeze-deepseek' is valid`（exit 0），
`openspec validate --changes --strict` → `1 passed, 0 failed`。

**立项不是授权**：提案里写明 P1–P4 一律未勾选、未执行。实测复核未授权状态仍成立——
`ACTIVE_PLATFORM_IDS = ["stepfun","yuanbao","chatglm","yiyan","kimi"]`、
`isPlatformActive("deepseek") === false`、
`evaluatePlatformPolicy("deepseek", {allowFrozen:false}) = {allowed:false, active:false,
unfrozenBy:null, reason:"frozen-by-user-redline"}`；`platform-freeze.test.mjs` 15/15 绿。
C 段的「不在范围」已落成提案与 spec 条款（N61）。

`openspec validate --specs --strict` 原有 **4 红**，是 N58 登记的 TBD Purpose（其中
`active-platform-registry` 那份会被本 change 的 delta 归档写回）。**已于 P0 之后单开一轮修完并关闭
N58**：4 份 Purpose 按各自 Requirement 归纳补齐，`--specs --strict` → **6 passed / 0 failed**，
`unfreeze-deepseek --strict` 仍 valid。提前做的理由：这一步不需要解冻授权，而 P1–P4 卡在裁定原文；
继续挂在解冻后面只会让一个已登记的独立缺陷长期开放。偏离原案「顺手做、别单开一轮」已写进 N58 的 fix。

1. 你给裁定原文 → 建 `openspec/changes/unfreeze-deepseek/`（P0）
2. 按 §2 清单改（含 §2.3 的锚点改写、spec 的 Purpose 与 Scenario 更新）
3. `openspec validate unfreeze-deepseek --strict` + 离线四类门禁全绿
4. **不带** `ALLOW_FROZEN` 跑 deepseek 8/8，回执须 `active:true && unfrozenBy:null`
5. 5 个活跃站各跑一轮无回归；longcat 零触碰（回执里不应出现 longcat）
6. RESULT + `known_gaps` 登记裁定时间/依据 + 归档 + `validate --archived --strict`

## 7 · 回滚

一条 `git revert` 就能回到 5 站白名单：常量、测试期望、变异锚、spec Scenario 在同一个
change 里，原子回滚。真机回执与证据是只读留档，不随回滚删除。
