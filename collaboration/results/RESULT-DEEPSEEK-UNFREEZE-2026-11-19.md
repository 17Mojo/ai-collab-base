# RESULT — DeepSeek 解冻执行（2026-11-19）

## 1 · 用户裁定原文（授权来源）

2026-11-19 13:41（GMT+8），WorkBuddy 交互中向用户提问：

> 解冻执行（P1–P4）需要你的裁定原文。现在按哪条走？

用户选择：

> **授权解冻 deepseek**
> 选项说明：按 tasks P1→P4 执行到真机验收。请在下方补充裁定原文：点名平台 + 允许范围 + 时间；我把它落档后才动常量。

用户未额外输入文字，但**选项本身即裁定**，三要素齐全：

| 要素 | 值 | 来源 |
|---|---|---|
| 平台 | `deepseek`（点名） | 选项标签「授权解冻 deepseek」 |
| 允许范围 | `tasks.md` 的 P1 → P4，含真机验收 | 选项说明「按 tasks P1→P4 执行到真机验收」 |
| 时间 | 2026-11-19 | 交互时间戳 |

**没有授权的事项，逐项写清**（避免范围外扩）：

- **N60 的只读探针未单独放行** ⇒ 不跑。按 tasks 1.3，交付说明如实写
  「发送区 DOM 从未落盘」，不假装已还原。
- **longcat 未授权** ⇒ 零触碰，回执里不应出现 longcat。
- **反自动化不在范围**（N61）：不是 deepseek 特有，5 个活跃站同样没有基线；
  L1 那 6 条 `bot_check` 阳性只来自 chatgpt / claude 两个非活跃站。
  `captchaBypass: false` 是「未使用绕过手段」的行为声明，不是「未遇到验证码」。
  交付说明里不许写「反自动化已验过」。
- **不绕验证码 / 风控**，不替真人登录。
- **不删任何 adapter**；生产支持与真机白名单是两件事。
- **不把 N25 写成已解决**：它的 closed 是「未获有效检验 + 目标源退出」。
- **不覆盖**两份历史计划工件 `session-wall-ab-plan-2026-11-11/11-18.json`。

## 2 · 执行命令与结果

> 本节按阶段追加。未完成前不写「通过」。

### P0 · 前置（已完成，见 change 提案）

```
openspec validate --all --strict  → Totals: 7 passed, 0 failed (7 items)
单测 413 / 矩阵 108/125 / 全量变异 178/178 被杀死、0 存活
台账 61 条（54 closed / 6 open / 1 wontfix）
```

### P2 · 常量与断言

改前先让测试自己说话，不照抄 PLAN 里可能漂移的行号：

```
$ node --test tests/platform-freeze.test.mjs        # 只改三个常量后
not ok 1  白名单恰好是 5 个活跃站，不含 deepseek / longcat / qianwen
not ok 5  只有 ALLOW_FROZEN=1 才放行冻结平台，并在回执里留痕
not ok 11 N35 回归：预检 + 真的解冻过
not ok 13 真正解冻过 ⇒ 打，且靠 unfrozenBy 而非 active 判定
# tests 15 / pass 11 / fail 4
```

4 条数量与 PLAN 预估一致，但**具体条目不同**（PLAN 写的是 `:30/:40/:139/:155`）——
以实测为准。处置：

| 红项 | 做法 | 为什么 |
|---|---|---|
| #1 白名单计数 | 5 → 6，期望数组加 deepseek；另加 `isPlatformActive("deepseek")===true` | 不删断言，正向钉住解冻生效 |
| #5 ALLOW_FROZEN 留痕 | 样例 deepseek → **longcat** | longcat 仍冻结，原门守的是「例外开关必须留痕」，与站点无关 |
| #11 N35 预检分支 | 样例 deepseek → longcat | 同上 |
| #13 解冻留痕判定 | 样例 deepseek → longcat | 同上 |

另外补一条**新**断言：`assertPlatformAllowed("deepseek")` 必须
`allowed=true / active=true / unfrozenBy=null / reason="active"`——
这是「真活跃」与「ALLOW_FROZEN 假放行」的分界线。

没红但**说谎**的两处也一并改：#2 测试名里的「deepseek / longcat 都拦」、#4 的「活跃 5 站」。

常量最终值：

```
ACTIVE_PLATFORM_IDS  = [stepfun, yuanbao, chatglm, yiyan, kimi, deepseek]   // 6
FROZEN_AB_PLATFORMS  = [longcat]
AB_PLATFORMS         = [longcat]   // 不变：解冻 ≠ 重开 N25 的 A/B 命题
```

变异锚同步：原锚「把 deepseek 悄悄加进活跃白名单」在 deepseek 已获授权后失去原义，
改成「把 **longcat** 悄悄加进活跃白名单（未授权放宽）」；闸门锚的 why 同步。
局部变异 `MUTATION_TESTFILE=platform-freeze.test.mjs` → **7/7 被杀**。

复验：`platform-freeze.test.mjs` **16/16**；扩展全套 **414/414**；矩阵 **108/125**。

### P3 · 离线门禁

```
node tests/run-tests.mjs                 → 415/415 passed，33/33 受跟踪
node tests/adapter-matrix/adapter-test-runner.js → 108/125 passed / 0 failed / 17 skipped
node build.js + git status dist/         → 零 diff，源码与产物一致
openspec validate --all --strict         → 7 passed / 0 failed
pytest 台账与门禁编号                      → 9 passed
全量变异                                  → 178/178 被杀、0 存活
```

**全量变异抓到 1 条存活，值得单独记**：锚「session-wall-ab 改回读冻结名单当实验对象」
没被杀死。根因是解冻后 `AB_PLATFORMS` 与 `FROZEN_AB_PLATFORMS` **都是 `["longcat"]`**，
把 `platforms = [...AB_PLATFORMS]` 改回 `[...FROZEN_AB_PLATFORMS]` 在值层面是等价变换——
B1 那些值级断言数学上不可能红。**这是解耦设计在当前常量取值下的真实退化，不是环境噪声。**

修法不是删锚，也不是等两值再次不同：补一条**结构性断言**，直接验 `platforms` 的来源
表达式只能出现 `AB_PLATFORMS`、不许出现 `FROZEN_AB_PLATFORMS`，并把锚的 `expectTest`
指向它。理由写进测试注释：解耦是**结构性约束**，不是值约束。局部 14/14 被杀后，
最终全量 178/178 被杀、0 存活。单测 414 → **415**。

### P4 · 真机验收

**4.1 deepseek 8/8 — 通过**

```
$ PRECHECK=1 CANDIDATES=deepseek OUT=.../L2-precheck-2026-11-19.deepseek.json \
    node tests/real-machine/l2-platform-auto.mjs
deepseek composerVisible=true / looksLikeLogin=false
platformPolicy = {"allowed":true,"active":true,"unfrozenBy":null,"reason":"active"}

$ PLATFORM=deepseek OUT=.../L2-deepseek-auto-2026-11-19.unfreeze.json \
    SHOT=.../L2-deepseek-auto-2026-11-19.unfreeze.png \
    node tests/real-machine/l2-platform-auto.mjs     # 没有 ALLOW_FROZEN
success=true | status=completed | steps=8/8 success | errors=[]
sessionResets[0] = {stepId:"step_8_output", available:true,
                    strategy:"adapter-text-match", before:3, after:0, durationMs:405}
duration=86,620 ms
```

回执：`evidence/L2-deepseek-auto-2026-11-19.unfreeze.json` + 同名 PNG。
`platformPolicy.unfrozenBy === null` —— **不是** `ALLOW_FROZEN=1` 假放行。

**这里必须写清边界**：`sessionResets[0].available=true / 3→0` 说明 step_8 的会话边界
这次**真的生效了**，而 N25 当年两轮就是没跑到这个生效点。但本次是**解冻后的单站回归**，
没有对照组 ⇒ **不能**据此宣称「fresh_session 解掉了长会话撞墙」。N25 的 closed 口径
（未获有效检验 + 目标源退出）不变，A/B 命题仍未获有效检验。

**4.2 其余 5 活跃站无回归 — 未达成（5/5 失败，如实记）**

| 站 | 结果 | 失败点 | 错误 |
|---|---|---|---|
| stepfun | 1/8 | `step_2_hook` | `Receiving end does not exist`（content-script 连接断开） |
| yuanbao | 1/8 | `step_2_hook` | `Response timeout` |
| chatglm | 1/8 | `step_2_hook` | `Response timeout` |
| yiyan | 7/8 | `step_8_output` | `Receiving end does not exist` |
| kimi | 1/8 | `step_2_hook` | `Response timeout` |

五份回执的 `platformPolicy` **全部**是 `allowed:true / active:true /
unfrozenBy:null / reason:"active"` —— 白名单闸门没有拦它们。

**归因（不是猜测，有三条独立证据）**：

1. `node build.js` 后 `git status chrome-extension/dist/` **零 diff** ——
   本轮改动只在 `tests/` 下的冻结守卫，生产扩展发给站点的内容一个字节都没变。
2. 失败全部集中在**发送 / 等待层**（`Response timeout`、content-script 连接断开），
   没有一条出现在平台策略或 Pack 导入阶段。
3. 同一时段、同一 profile、同一 dist 上，**deepseek 8/8 成功** ——
   扩展加载与发送机制本身可用。

所以这 5 条失败**不是解冻改动造成的回归**，而是站点侧 / 环境侧的瞬时状态。
但「无回归」这条验收**确实没有拿到证据**，不能写成通过。已登记 N62（open / P2），
换时间重跑或真人确认登录态后再判。

**longcat 零触碰**：今日全部新工件 `grep -l longcat` **零命中**，没有启动、预检或发包。

**4.3 归档 — 未做**：`tasks.md` 的 4.2 未达成，所以不执行 `openspec archive`——
它会把 delta 写回主 spec，等于把未完成的验收固化成规范。

**这里我又写错了一句，当场更正**：原稿写「`validate --archived --strict` 按设计会拒绝归档」。
实测它返回 `11 passed, 0 failed`，但输出里**没有** `unfreeze-deepseek`——
`--archived` 只校验**已归档**的 change，那 11 项全是历史归档工件。
所以这个绿**不构成归档证据**，归档仍须另跑 `openspec archive unfreeze-deepseek`。
结论不变（不归档），但理由从「会被工具拒绝」改成「我不会把未完成的验收写进主 spec」——
前者是把决定推给工具，后者是我该自己做的判断。

## 3 · 风险与回滚

- 白名单变动是**唯一**影响面：`ACTIVE_PLATFORM_IDS`、`FROZEN_AB_PLATFORMS`、
  `AB_PLATFORMS` 三个常量与 4 条测试样例。一条 `git revert` 即可回到 5 站白名单。
- 真机发包会向 deepseek 发送消息，属于用户已授权范围；longcat 不在其中。
- 若浏览器 / 登录态不可用，**如实记录阻塞，不伪造回执**——这是本项目的基本口径。

## 4 · 后续步骤

1. **N62 是唯一未收口项**：换时间重跑 stepfun / yuanbao / chatglm / yiyan / kimi 各自完整
   L2（8/8 + `active:true && unfrozenBy:null`）。失败不归因于白名单，所以**不要动常量**。
2. 4.2 拿到有效结论 → 回填本 RESULT §4.2、勾选 tasks 4.2 → 才能归档 change
   （`openspec validate unfreeze-deepseek --archived --strict`）。
3. N60 仍需用户单独放行才补采发送区 DOM；在那之前「发送区按真机还原」不成立。
4. N25 的 A/B 命题**未因本次解冻而重开**：本次没有对照组，不得宣称边界解掉了撞墙。
5. 回滚：一条 `git revert` 回到 5 站白名单；真机回执与证据是只读留档，不随回滚删除。
