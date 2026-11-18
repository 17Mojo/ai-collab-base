# RESULT — DeepSeek 723 秒假超时：归因、修复、全量复验（2026-11-18）

- **状态**: completed（N55 closed；N56 登记为 open）
- 日期：2026-11-18
- 执行者：`claude_code`（AGENT_EXEC）
- 工作区：`/Users/raymondna/Documents/AI-collab/ai-collab-base`（`main @ 505b66d`）
- 范围：用户裁定「按 A 做」（删宽通配 + 补测试与变异锚 + 复跑全量），并追加「核查冻结的 longcat 是否同病因」

> **口径声明（先读）**
>
> 1. 本轮**动过冻结闸门**：`ALLOW_FROZEN=1` 只用于 deepseek 一次全量复跑，回执
>    `platformPolicy = {allowed:true, active:false, unfrozenBy:"ALLOW_FROZEN=1"}` 可复核。
> 2. **longcat 一次真机都没跑**：连只读预检都没做（预检会开页面，按红线同样算「碰」）。
>    第 5 节的 longcat 结论**全部来自磁盘上已有的历史回执与源码静态比对**，不是本轮实测。
> 3. 「8/8 通过」证明的是**不再出现假超时、也没有因删判据变成「太早成功」**；
>    「`site_logo_loading` 会让 `isTyping()` 恒真」这个**直接证明来自单测**，不来自复跑。

## 1. 原先的病灶（硬证据）

`evidence/L2-nov18-deepseek.json`：`step_5_boundary` 卡满 **723.44s**（= 4×180s + 3.44s），
回执只写「Response timeout。如果那个网站要求先登录，请先在页面上登录再重试」。

同一时刻的截图 `evidence/L2-nov18-deepseek.png` 说明页面并非「没反应」：

- AI 回答**早已完整落在页面上**（「这段边界标注说得清楚：…」整段可见）；
- 输入框空闲，没有「停止生成」按钮；
- 页面上写着「搜索到 23 个网页」，并排着 **6 个 16×16 的来源站点图标占位**：

```html
<div class="site_logo_loading site_logo_fallback" style="width:16px;height:16px"></div>
```

因果链：

```
class 里带 loading
  ⇒ [class*="loading"] 命中
  ⇒ findVisibleElement 返回它（isElementRendered 只看 display/visibility/opacity，不看尺寸，16×16 也算「可见」）
  ⇒ isTyping() 恒为 true
  ⇒ content-script.js:510 的 `state.ready && !isTyping()` 永不成立
  ⇒ 每一步都必然耗尽 4×180s
```

**为什么只有 step_5 撞上**：前 4 步没触发联网搜索，页面上没有那排 logo。
缺陷是**条件触发**的，不是每次必现——这正是它躲过 11-12~11-14 连续 5 轮 8/8 的原因。

## 2. 修复（按用户裁定的方案 A）

`chrome-extension/src/platforms/deepseek-adapter.js:93-96`

```diff
-  typingIndicator: [
-    '[class*="loading"]',
+  typingIndicator: [
+    '[class*="generating"]',
     ".typing-indicator",
   ],
```

刻意**不**改成 `:not([class*="site_logo"])`：那只是把今天的类名钉进选择器，站点改版即复发。
宽通配 `[class*="..."]` 误命中界面外壳是这个项目反复踩的同一个坑（文心命中通知中心、
元宝命中新建按钮）。宁可少一个信号，也不要一个恒为 true 的忙闲判定。

删掉后靠什么判忙闲：`[class*="generating"]` + `.typing-indicator` + `stopButton` +
等待循环里的正文稳定窗。真机空闲态这三条实测均 0 命中，step_2/3/4 本来就是走稳定窗成功的，
所以删掉不引入「太早成功」。理由逐条写进了生产代码注释（20 行）。

配套守卫：

| 工件 | 内容 |
|---|---|
| `chrome-extension/tests/typing-indicator.test.mjs`（新建） | 5 条：诱饵在 ⇒ false；空页 ⇒ false；generating 在 ⇒ true；停止按钮在 ⇒ true；`display:none` ⇒ false |
| `chrome-extension/tests/adapter-matrix/fixtures/mock-dom-deepseek.html` | 追加真机诱饵 `site_logo_loading site_logo_fallback` |
| `chrome-extension/tests/real-machine/mutation-check.mjs` | 变异锚：把 `[class*=loading]` 加回去，必须让上面第一条测试变红 |

## 3. 验证

| 项 | 结果 |
|---|---|
| 新单测独跑 | 5 passed / 0 fail |
| 扩展单测全量 | **374 passed / 0 fail**（受跟踪 30 个 / 未跟踪 0） |
| 适配器矩阵 | **116/125 passed / 0 failed / 9 skipped** |
| 全量变异检查 | **160/160 杀死**，`EXIT=0`（§3.1） |
| **DeepSeek 全量 L2 复跑** | **8/8 completed**，整轮 **81.58s** |

复跑回执 `evidence/L2-nov18-deepseek.fix1.json` 逐步耗时：

```
step_1_topic      0ms      step_5_boundary  11671ms   ← 修复前这一步 723440ms
step_2_hook   10741ms      step_6_takeaway  10163ms
step_3_explain 11167ms     step_7_visual    12665ms
step_4_scene  11171ms      step_8_output    14002ms
sessionResets: [{stepId: step_8_output, mode: prefer, available: true,
                 strategy: adapter-text-match, 3 → 0, 322ms}]
```

同一站点、同一 Pack、同一 profile：**723.44s（单步） → 11.67s（同一步），整轮 8/8**。

### 3.1 变异检查

`CODEBUDDY_SAFE_DELETE_ENABLED=0 node tests/real-machine/mutation-check.mjs`
（前者绕过 safe-delete 的「一次删 >50 个文件」阈值）。**全部 160 条变异都被杀死**，`EXIT=0`
（上一轮是 159 条，新增 1 条即本轮锚点）。

单独确认新锚点确实由**新测试**杀掉（`MUTATION_TESTFILE=typing-indicator.test.mjs`）：

```
=== 变异检查（1 条 / 仅 typing-indicator.test.mjs）===

✓ DeepSeek typingIndicator 加回 [class*=loading] 宽通配
    被 DeepSeek：空闲页上的搜索来源图标（class 带 loading）不得被判成「正在生成」 杀死
```

即：把这个缺陷加回去，测试会红——判据是**可证伪**的，不是「写了就算守住」。

## 4. DeepSeek 到底坏没坏（分层回答）

| 层 | 结论 | 依据 |
|---|---|---|
| 选择器 / DOM 契约 | **没问题** | 11-18 实采 3/5/8 与 11-11 探针逐项一致 |
| 忙闲判据 | **曾经坏，已修** | `[class*="loading"]` 命中搜索来源图标（§1、§2） |
| 8 步全链路 | **能跑通** | 本轮 8/8 completed；11-12~11-14 也曾连续 5 轮 8/8 |
| 反自动化 | **仍未测** | 历史回执里没有验证码 / WAF / 风控提示；RESULT-N25 明确写「产品裁定非实测」 |

**关于解冻**：技术上不再有阻塞（8/8 已复现）。但解冻是**治理决定**，不是技术决定——
N25 的裁定是「按用户现场判断把两站降级为目标源外平台」，本轮没有推翻该裁定的任何新证据。
⇒ 建议维持冻结；若要解冻，应作为一次显式裁定并改 `ACTIVE_PLATFORM_IDS` + 同步
`platform-freeze.test.mjs` 与变异锚点（本轮**未**动这些常量）。

## 5. longcat 是否同病因（用户追加项）——**不是**

逐条读磁盘上 6 份 longcat 真机回执（不是凭印象）：

| 回执 | 失败步 | 耗时 | 判读 |
|---|---|---|---|
| `-11-11.fix1` | step_2 | 243.8s = 4×60+3.8 | 当时还走默认 60s；选择器问题 |
| `-11-11.fix2` | step_2 | 723.9s = 4×180+3.9 | 加 180s 例外后仍失败；选择器问题 |
| `-11-11.fix3` | step_8 | 724.0s | step_2 起 2~7 步 17–27s 正常；靠后步骤挂 |
| `-11-12.ab2-with-boundary` | step_8 | 723.2s | 同上 |
| `-11-12.ab4-no-boundary` | step_4 | 723.3s | 失败位漂移 |
| `-11-12.ab4-with-boundary` | step_8 | 724.3s | 同上 |

四条判据：

1. **选择器层面已排除**：longcat 的 typingIndicator 从来没有裸 `[class*="loading"]`。
   它的 5 条全是 11-04 零发送静态普查从站点 bundle 里拿到的**字面量**：
   `.assistant-main .v-loading-dot` / `.v-loading-dot` / `[class*="stop-generate"]` /
   `[class*="loading-dot-box"]` / `[class*="loading-text"]`，并且
   `tests/typing-indicator-contract.test.mjs` 的 LongCat 段 7 条用例（含「思考完成后仍保留的
   reason-title 不许算生成中」反例）已经钉住。deepseek 那条宽通配是本站独有。
2. **11-11 的 step_2 失败已被归因为纯选择器问题并修好**：RESULT-L2-MULTIPLATFORM §9.3
   「longcat：账号态解除后是纯选择器问题」（messageList 0 命中）；fix3 起 step_2 203s 就过。
3. **残留失败的指纹不同**：失败位在 step_4 / step_8 之间漂移，早步骤稳定 17–27s。
   N55 那种「恒为 true」会让**第一个**用到的步骤就死，不会挑步骤。
4. **旁证**：11-11 §9 记录 longcat 在长会话里对同一条 2437 字 fusion 提示词**由平台自己回
   「服务出错啦」**；同一条提示词发进**全新会话**则 21s 答完 1481 字
   （`evidence/L2-longcat-fusion-isolated-2026-11-11.json`）。

⇒ 现有两份「看起来一样」的假超时：deepseek 是**忙闲判据恒真**（已修），longcat 是
**长会话响应迟到 / 平台报错**（未修、未归因，登记 **N56**）。把 N55 的修法照搬到 longcat
会改到一个本来就没问题的选择器上。

**本轮没做的**：longcat 归因需要一次带 `PROBE_DURING=1` 发送期 DOM 采样的真机复跑，
在失败那一步同时记 `isTyping()` / `getMessageList().length` / `messageContent` 命中数。
longcat 属冻结站，连只读预检都算「碰」，故未做——需用户明确授权。

## 6. 风险

- **「8/8」被过度解读**：复跑截图里没有「搜索到 N 个网页」，那一轮未必再次触发搜索。
  若下游把本轮写成「联网搜索场景也复验过了」，就是超范围宣称。
- **条件触发的缺陷会复发**：真正守住它的不是这一轮 8/8，而是单测 + 变异锚。
  任何「为了让测试变绿而放宽判据」的改动都会把这个洞重新打开。
- **longcat 结论缺位仍在**：N56 保持 open；「解冻 longcat 就多一个目标源」这个推论没有数据支撑。
- **N52 / N53 / N54 未修**：零静态检查、真实快照只采落地页、deepseek 无 button 形态发送控件。

## 7. 回滚

`git revert <本提交>` 即可回到带宽通配的版本；同时删掉 `tests/typing-indicator.test.mjs`
与 `mutation-check.mjs` 里那条锚点（否则变异检查会红）。回执与截图是只读证据，不随回滚删除。

## 8. 留档文件

- `evidence/L2-nov18-deepseek.json` / `.png`（失败现场：723.44s + 「搜索到 23 个网页」）
- `evidence/L2-nov18-deepseek.fix1.json` / `.png`（修复后：8/8，81.58s）
- `evidence/deepseek-dom-shape-2026-11-18.json`（会话页 DOM 形状，`site_logo_loading` 取证）
- `known_gaps.json` N55（closed）/ N56（open）/ N53（追加页态盲区）
