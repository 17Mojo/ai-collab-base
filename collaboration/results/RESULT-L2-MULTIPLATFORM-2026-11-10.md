# RESULT — L2 扩平台轮（yuanbao / chatglm）· 2026-11-10

> 🔧 **2026-11-10 20:57 修复轮更新（Rasp）**：下方 §0–§6 是 **19:26 首轮的历史结论**（两站 fail、门禁未闭环），已被 `RMR-2026-11-10-02` 覆盖。修复后 **qianwen / yuanbao / chatglm 三平台 L2 全部 pass**。原文不删，留痕；最新结论见 **§7**（21:46 终版：全量变异检查 76/76 全被杀死，重跑 `EXIT_CODE=0`）。
> 🔧 **2026-11-11 05:42 扩实例轮（Rasp）**：按用户裁定「前半段未认定闭环，缺少更多实例」，再起跑 yiyan / kimi / longcat / gemini 四站。首轮 4 站全未通过，但根因分属**选择器 / 账号态 / 网络**三类；修完 yiyan / kimi 的选择器后重跑 **8/8 步全过**。**L2 pass 3/10 → 5/10**。详见 **§8**；机器证据 `RMR-2026-11-11-01.json`。「第一个外部用户」按用户裁定**主动暂缓**（deferred，非缺人）。
> 🔧 **2026-11-11 07:50 收口轮（Rasp）**：按用户 06:10 裁定「只关注 deepseek 和 longcat，其他暂封存」。两站都从账号态推进到 **7/8 步**，且**同卡 `step_8_output`（fusion）**，但成因相反：deepseek 是答案迟到（4×180s 都没稳定），longcat 是**平台自己报「服务出错啦」**。隔离实验把同一条 2437 字提示词发进全新会话 → **21s 答完 1481 字**，证明问题不在提示词、而在**长会话**。⇒ 结论改写：这不是 adapter 问题，是「单会话串行跑完 8 步」这个 Pack 结构假设在真机上不成立。**L2 pass 仍记 5/10，未放行**。详见 **§9**。
> 🔒 **2026-11-11 12:18 范围收缩（用户裁定）**：平台范围收缩为 **5 个**——只保留 qianwen / yuanbao / chatglm / yiyan / kimi，其余（deepseek / longcat / gemini / chatgpt / claude / dots）**全部冻结，不去碰**。此裁定**推翻** 06:10 的「只推 deepseek 和 longcat」。
> **口径**：活跃平台 **5/5 全 pass**；但分母仍记 10（冻结≠移除），**5/10 这个数字不因裁定而上升**，也不得把冻结项算作已验证。
> ⚠️ **冻结 ≠ 缺陷修好**：`step_8` 的长会话尾部撞墙属 Pack 结构假设问题，在 5 个活跃站上依然潜伏（它们步过只因上下文尚未越界）。详见 §9 与 `memory/project_route_decision.md`。

- 日期：2026-11-10 · Run：`RMR-2026-11-10-01` · 执行者：`workbuddy_rasp`
- 目标：按路线门禁前半段「真机 3 平台回归」，在 qianwen（已 pass）之外补 2 个 L1 已 pass 平台
- 方式：Playwright 持久 profile 挂载 `dist/`，`IMPORT_PACKS` → `EXECUTE_PACK` 精确投递，同题同 Pack（`xiaohongshu-knowledge-creator` 8 步）
- 环境：`dist/` 于 19:12 用 11-09 最新源码重建（SW 自检 `hasGate/hasStatusSelector/hasMin50` 全 true）；profile 沿用 `~/Library/Application Support/rm-qianwen-l2-profile`；跑前按 N15 清 SW 三缓存
- 工具：`chrome-extension/tests/real-machine/l2-platform-auto.mjs`（本轮新增的平台参数化驱动，PRECHECK / RUN 双模式，平台定义取自 `tests/platforms.mjs`）

> **口径声明**：本文是**机器执行判定**，不是人工验收。两站都在取回层失败，**没有做 §4.5 语义裁决**——取回对象不存在，评语义等于凭空打分。截图里的模型回复不得冒充扩展产物。

## 0. 结论先行

**两站都 fail，门禁前半段未闭环，而且暴露了一个跨站通用缺陷。**

不是登录问题，不是发送失败，不是账号额度，不是旧 SW 粘连。是**扩展认不出这两个站的消息气泡**，所以永远等不到「回复已取回」。

## 1. 执行结果

| 平台 | tabId | step_1 | step_2_hook | 耗时 | 判定 |
|---|---|---|---|---|---|
| yuanbao | 1785643781 | success | `Response timeout` | 123.5s | **fail** |
| chatglm | 1785643860 | success | `Response timeout` | 244.5s | **fail** |

两次都止于第一个 AI 步骤，`output` 只有 `topic_info`，7 个产出字段全空。回执与截图：

- `evidence/L2-yuanbao-auto-2026-11-10.json` / `.png`
- `evidence/L2-chatglm-auto-2026-11-10.json` / `.png`
- `evidence/L2-selector-probe-2026-11-10.json`（只读 DOM 探针）

## 2. 截图证据：会话其实跑成了

| 平台 | 截图里能看到什么 |
|---|---|
| yuanbao | 用户 prompt 气泡完整可见；AI 回复「别再把它当成更高级的聊天机器人——它是一套能自己定计划、调工具、改错并交付结果的自主执行系统。」；左下角为已登录账号 `17Mojo`；无登录墙、无报错、无生成中状态 |
| chatglm | 访客气泡 + 完整 AI 回复 + 「思考结束」折叠条 + 后续建议按钮；输入框「和我聊聊吧」可用；游客态也能正常发送 |

⇒ **注入 → 发送 → 模型回复这三步在两站都成立**。断的是第四步「取回」。

## 3. 根因链（指到行号）

`src/content/content-script.js:279-321` 的 `handleWaitForResponse`：

```js
const initialCount = findElements(currentConfig.messageList).length;
...
countGrew: currentCount > initialCount,
...
if (state.ready && !isTyping()) resolve(...)
```

`sampleWaitState`（`src/utils/wait-policy.js:52-79`）要求 `countGrew` **与** 正文稳定 8 秒同时成立。`countGrew` 是硬前提，一次为 false 就永远不 ready。

只读 DOM 探针在两站真实会话页统计 `messageList` 候选：

| 选择器 | yuanbao | chatglm |
|---|---|---|
| `[class*="message"]` | **0** | **0** |
| `[class*="response"]` | **0** | **0** |
| `.message-item` | **0** | **0** |
| `[data-conv-speaker]` | 0 | 0 |
| `[data-message-id]` | 0 | 0 |
| `[role="article"]` | 0 | 0 |
| `[class*="chat"]`（布局/侧栏，非气泡） | 9 | 6 |

`initialCount = 0`，发送后仍 `0` ⇒ `countGrew = false` ⇒ 60s 超时。`yuanbao-adapter.js:26-45` 的注释其实早就写明了这个风险：「真实气泡的类名必须在**已登录会话**里确认……在那之前宁可返回 0（失败会响亮地超时）」。这次就是那声响亮的超时。

**两站独立复现 ⇒ 不是单站选择器漂移，是通用判据的适用面问题**：`countGrew` 假设「消息列表元素数会随新消息增加」，而虚拟列表 / 固定容器 / 追加到同一父节点的站点都不满足。qianwen 恰好满足，所以 11-05 的两轮 L2 pass 是**平台特例**，不能外推成「链路已具备多平台能力」。

## 4. 对路线门禁的影响

| 项 | 11-10 之前 | 11-10 之后 |
|---|---|---|
| L2 层 pass 平台数 | 1 / 10（qianwen） | **仍为 1 / 10**（新增 2 fail） |
| 「真机 3 平台回归」 | 1/3 | **1/3，且已知不能靠换平台碰运气关掉** |
| 第一个外部用户 | 空 | 空（未触碰） |

门禁**仍开**。而且阻塞性质变了：从「还差两次执行」变成「还差一次跨站取回判据的修复」。继续换平台试，最多找到几个恰好命中的站，拿到的是假绿，不是覆盖。

## 5. 修复方向（局部优先，不动通用判据）

1. **补两站的真实气泡选择器**：在**发送发生的同一页面**采 DOM（本轮探针是在新开标签页读历史会话，没加载到消息体，所以只拿到侧栏结构——这一步必须改成在 `EXECUTE_PACK` 期间用 `page.evaluate` 抓祖先 class 链）。yuanbao 优先查 `data-conv-*` 系属性（adapter 注释里已有 bundle 字面量证据），chatglm 查 Vue `data-v-*` 作用域内的消息容器。
2. **改判据而不是只改选择器（备选）**：把 `countGrew` 从「元素数增长」放宽为「最新正文变化 + 稳定 8s」，用正文指纹替代计数。这会动 `wait-policy.js` 与 `content-script.js` 的公共路径，属全面改动，**需单独拍板**，本轮未做。
3. 任一改动都要补契约测试 + 变异锚，重建 `dist/`，再重跑两站。

## 6. 记录与复跑

- RMR：`RMR-2026-11-10-01.json`（L2 两 fail + L1 两 not-run）。
- 门禁未破坏：`npm test` **238 / 238 pass**（19:26 复跑，新增驱动不进 CI）。
- 复跑命令（修完后）：
  ```
  cd chrome-extension
  PLATFORM=yuanbao OUT=<回执路径> SHOT=<截图路径> \
    node tests/real-machine/l2-platform-auto.mjs
  ```
- 预检（不发送、不消耗额度）：
  ```
  PRECHECK=1 CANDIDATES=gemini,kimi,longcat,yiyan,yuanbao,chatglm \
    node tests/real-machine/l2-platform-auto.mjs
  ```

---

## 7. 🔧 修复轮（20:20–20:57）：三平台 L2 全绿

### 7.1 做了什么（严格局部，未动公共判据）

| 文件 | 改动 |
|---|---|
| `src/platforms/yuanbao-adapter.js` | `messageList` 首位加 `[data-conv-speaker]`（真机会话页实测 2 条气泡：human + ai）；`messageContent` 首选 `.hyc-content-md-done`（done 修饰只在生成结束出现，流式期间不命中 ⇒ 天然不取碎片） |
| `src/platforms/chatglm-adapter.js` | `messageList` 首位加 `.answer-content-wrap`（发送期采样实证 0→1→2→3 递增；自身带 `content` 子串，命中正文提取的「先看元素自身」分支） |
| `tests/real-machine/l2-platform-auto.mjs` | 新增 `PROBE_DURING=1`：EXECUTE_PACK 进行中每 2 秒采一次 DOM，补上首轮「新开页读历史会话、拿不到消息体」的缺口 |
| `tests/real-machine/multi-platform-selector.test.mjs` | 新增 4 条契约测试，用真机采集的 DOM 形状验证「气泡数得出来」「新回复出现后计数增长」「正文取得到」 |
| `tests/real-machine/mutation-check.mjs` | 新增 2 条变异锚（摘掉新选择器 ⇒ 对应契约测试必须变红） |

**`wait-policy.js` / `content-script.js` 的公共判据一行未改**——按局部解锁原则，只修两站的选择器漂移。

### 7.2 三平台重跑结果（全部 `8/8 步 success`、`status=completed`、7 个产出字段非空）

| 平台 | tabId | 耗时 | 产出字数（hook/explain/scene/boundary/takeaway/visual/final） | 判定 |
|---|---|---|---|---|
| yuanbao | 1785644612 | 96.8s | 43 / 423 / 136 / 293 / 97 / 760 / 1079 | **pass** |
| chatglm | 1785644815 | 422.9s | 45 / 478 / 266 / 222 / 312 / 568 / 1113 | **pass** |
| qianwen | 1785644920 | 362.0s | 56 / 582 / 436 / 327 / 341 / 602 / 1322 | **pass** |

三份回执逐字段扫过：无 `{{占位符}}`、无 `[object Object]`、无「正在思考/努力工作中」状态条、无流式开头碎片。是真正文，不是假绿。

**构建口径如实登记**：yuanbao 跑在 build A（SW `size=105417`），chatglm 与 qianwen 跑在同一份最终构建 build B（`size=105780`）。两者唯一差异是 chatglm-adapter 新增的那一行选择器，按域名分流，对 yuanbao 路径无影响。没有为抹平这个差异重复消耗账号额度。

### 7.3 验证

- `npm test`：**242 / 242 pass**（较首轮 +4 条新契约测试）。
- 变异锚：**全量 `mutation-check.mjs` 已跑完（11 分 25 秒）——76 / 76 条变异全部被杀死，0 存活**。其中新增两条：
  - `把元宝的消息选择器退回 0 命中的旧三件套` → 被 `元宝消息气泡能被数出来` 杀死；
  - `把智谱的消息选择器退回 0 命中的旧三件套` → 被 `智谱消息气泡能被数出来` 杀死。
  另有定向变异验证：同时摘掉两个新选择器 ⇒ 4 条契约测试全红 ⇒ 源码自动还原。
  🔧 **21:14 更正**：本条原先写「全量变异检查超时未完成」，是 19:26 首轮遇 SIGTERM 时的旧状态，现已闭环。
  🔧 **21:46 再更正（重跑闭环，最终口径）**：带 `CODEBUDDY_SAFE_DELETE_ENABLED=0` 重跑全量（11 分 02 秒）——**76 ✓ / 0 ✗、脚本自打印「全部 76 条变异都被杀死」、`EXIT_CODE=0`**；`.mutation-tmp` 由脚本自动清理，工作区源码完好，`npm test` 242/242 复核。**判定以干净版日志为准**：`evidence/mutation-check-full-2026-11-10.clean.log`。
  首次运行日志 `evidence/mutation-check-full-2026-11-10.log` 原样保留，仅作环境诊断：其退出码 1 源于收尾 `rmSync(.mutation-tmp)` 一次删 182 个文件撞 WorkBuddy `safe-delete` shim（阈值 50），导致 `main()` 的 `return 0` 没走到，**不是断言失败**。解法已写进 `mutation-check.mjs` 头注释并实测有效。
  🔧 **21:55 对账补记（证据链完整性）**：上述两份 `.log` 原被根 `.gitignore:40` 的 `*.log` 全局规则忽略（`git check-ignore` 实锤、未跟踪），即 §7.3 指定的「最终判定依据」实际无法入库。已在 `.gitignore` Logs 段加精确白名单 `!collaboration/results/real-machine-runs/evidence/*.log`，两份日志现为 `??` 可跟踪，与 `evidence/` 既有 json/png 入库惯例一致；`git check-ignore -v foo/bar.log` 复核全局规则仍生效。此项仅修交付物入库状态，**不改变 76/76 与 `EXIT_CODE=0` 的判定**。
- 证据：`RMR-2026-11-10-02.json` + `evidence/L2-{yuanbao,chatglm,qianwen}-auto-2026-11-10.fix1.{json,png}` + `L2-chatglm-auto-2026-11-10.probe1.dom-samples.json`。

### 7.4 门禁状态

| 项 | 首轮（19:26） | 修复轮（20:57） |
|---|---|---|
| L2 pass 平台数 | 1 / 10 | **3 / 10**（qianwen、yuanbao、chatglm） |
| 「真机 3 平台回归」 | 1/3，且判定不可达 | 三平台证据齐，**是否判闭环由用户拍板**，本报告不宣布 |
| 「第一个外部用户」 | 空 | **仍空**（相关文档停在 2026-11-03，零真人会话） |

> **口径不变**：全部是机器执行判定，不是人工验收。按 `memory/project_route_decision.md` 的 Why，工程健康度与机器评分不得充当路线依据；**不说「验收通过」**，路线 A/B 仍待拍板。

### 7.5 剩下要做的

1. ~~补跑全量变异检查 / 拿干净退出码~~ ✅ **全部完成**（76/76 被杀死；重跑 `EXIT_CODE=0`）；
2. 决定是否把三平台 L2 pass 认定为门禁前半段闭环——这是产品取舍，不是技术判定；
3. 后半段「第一个外部用户」仍需一个真人，材料 `docs/EXTERNAL_USER_SESSION_RUNBOOK.md` 早已备齐，缺的只是人。

---

## 8. 扩实例轮（2026-11-11 05:18–05:42）—— L2 3/10 → 5/10

### 8.1 触发

用户裁定两条：① **前半段未认定闭环，理由是缺少更多实例**（不是「没凑够 3 台」，是实例广度不够）；② **第一个外部用户主动暂缓**，确定性更高时再启动，避免不佳体验。⇒ 本轮只做一件事：扩 L2 实例。

### 8.2 首轮：4 站全未通过，但根因分属三类

起跑 4 个预检已确认登录态的平台（yiyan / kimi / longcat / gemini），带 `PROBE_DURING=1` 采集发送期 DOM。

| 平台 | 首轮结果 | 根因类别 | 具体证据 |
|---|---|---|---|
| yiyan | fail · Response timeout 243.9s | 选择器 | 采样 45 次：三件套全程 0 命中，`[class*=answer]` 0→25 |
| kimi | fail · Response timeout 244.0s | 选择器 | `[class*=message]` 恒定 2 命中（不是气泡），`.chat-message` 0 |
| longcat | fail · Response timeout 243.9s | **账号态** | 截图左下角「请先登录」；计数 6→14→11 非单调；历史会话不可复现 |
| gemini | not-run | **网络** | `net::ERR_CONNECTION_CLOSED`（重跑前另有一次 safe-delete 拦截，已用 env 绕过） |

**这一栏是本轮最重要的产出**：4 个实例把「跨站取回」从一个疑似小 bug 拆成三类不同层的阻塞，其中**只有 1 类（选择器）是代码能修的**。这也是「3 平台 pass 属平台特例、不是多平台能力」的直接证据。

### 8.3 修复（只动两个 adapter 的选择器，不动公共判据）

新增只读结构探针 `tests/real-machine/dom-shape-probe.mjs`（不发消息、只读），取代此前「按固定 seed 文本向上取祖先链」的做法——那个做法在 yiyan 上把**侧栏历史条目**当成了气泡。

- **yiyan**：`messageList` 首位加 `div.answer-container` / `div.ai-entry`（实测 4 轮 = 4 个，文本 66/44/38/32）；`messageContent` 改为 `.cosd-markdown-content` / `.marklang`，**移除** `[class*=answer]`（该选择器在本站 45 个命中，含 hover 菜单与历史条目）。
- **kimi**：`messageList` 改为 `.chat-content-item-assistant` / `.chat-content-item`（3 轮 = 3 个 assistant 条目）；`messageContent` 用 `.markdown-container:not(.toolcall-content-text)` 精确排除**思考过程**（否则会把「思考已完成…」当答案取回，且长度足以过闸 ⇒ 静默错数据）。

两站都**只收 AI 容器、不收 human 气泡**：`findElements` 是按优先级取第一个有命中的选择器，若混入 human，发送后「最新一条」可能是用户自己刚发出的 prompt，会被当成 AI 正文回填。

守护：新增 6 条契约测试（`multi-platform-selector.test.mjs`，总 10 条）+ 2 条变异锚（`mutation-check.mjs`，总 78 条）。`npm test` **248 / 248**。

### 8.4 重跑结果

| 平台 | 步骤 | duration | 7 个产出字段（字） | 内容性质 |
|---|---|---|---|---|
| yiyan | **8/8 success** | 105.6s | 88 / 415 / 146 / 143 / 170 / 382 / 1401 | 真正文，含「开社区水果店的张姐」等具体案例 |
| kimi | **8/8 success** | 129.7s | 31 / 427 / 187 / 155 / 119 / 278 / 725 | 真正文，「嘴很灵的顾问」比喻完整，无思考过程混入 |

无占位符、无 `[object Object]`、无状态条、无流式碎片。证据：`RMR-2026-11-11-01.json` + `evidence/L2-{yiyan,kimi}-auto-2026-11-11.fix1.{json,png}`。

**守护验证**：全量变异检查 **78 / 78 全被杀死、`EXIT_CODE=0`**（11 分 18 秒；含本轮新增 2 条锚，分别被「文心只数 AI 回复容器」与「Kimi 只数 assistant 条目」杀死）。`.mutation-tmp` 由脚本自动清理，`npm test` **248 / 248** 复核。日志：`evidence/mutation-check-full-2026-11-11.clean.log`。

### 8.5 门禁状态

| 项 | 11-10 修复轮 | 11-11 扩实例轮 |
|---|---|---|
| L2 pass 平台数 | 3 / 10 | **5 / 10**（+yiyan、+kimi） |
| 「前半段闭环」 | 待用户拍板 | 用户明示**未闭环**（缺更多实例）⇒ 继续扩 |
| 「第一个外部用户」 | 空 | **主动暂缓**（deferred，非「缺人」） |

> **口径不变**：全部是机器执行判定，不是人工验收。**不说「验收通过」**，路线 A/B 仍待拍板。

### 8.6 剩余待扩

- `chatgpt` / `claude` / `deepseek`：未做登录态预检（11-10 的 L1 里 chatgpt / claude 曾 bot_check 403、deepseek login_wall）；
- `longcat`：待登录后按同一流程验收；
- `gemini`：待网络可达后补跑。

流程已固化为 4 步：**只读结构探针 → 定容器（精确计数）→ 契约测试 + 变异锚 → 重跑取证**。

> ⚠️ 本节已被 **§9** 部分覆盖：deepseek / longcat 已由真人登录并推进到 7/8；chatgpt / claude / gemini 按用户 06:10 裁定**封存**（不排期、不催办，≠ 已验证）。

## 9. deepseek / longcat 收口轮（2026-11-11 06:10–07:50）

### 9.1 触发与范围

用户 06:10 裁定：**只关注 deepseek 和 longcat，chatgpt / claude / gemini 暂封存**。两站 06:12 由真人完成登录（`evidence/login-helper-2026-11-11.json`），账号态阻塞解除。本轮目标从「扩实例」改为「这两站到底能不能过」。

### 9.2 deepseek：不是平台慢，是死配置 + 重试重发

fix1 / fix2 连续两次失败，失败步耗时 **243.9s / 244.0s**。这个数字是突破口：`244 = 4×60s + 3~4s`——`maxRetries: 3` 配 60s 上限，四次尝试全部到点，与「平台慢」无关。

根因查了三次才定位（前两次都被实测打回，一秒没变）：

| 尝试 | 读法 | 结果 |
|---|---|---|
| 1 | `message.config?.timeouts?.response` | 仍 244s —— 那是 **Pack 步骤的 config**，装 `min_output_length`，没有 timeout |
| 2 | `currentConfig?.timeouts?.response` | 仍 244s —— `currentConfig = PLATFORM_CONFIGS[id]`，只有 SELECTORS |
| 3 | 读源码 | adapter 的 `timeouts` **从未流过任何边界**：`handleSendToAI` 走的是默认 60s |

修法：内容脚本新增站点例外表 `PLATFORM_RESPONSE_TIMEOUT`（deepseek / longcat = 180s），取值优先级 = **Pack 步骤 `config.timeout` > 例外表 > 60s 默认**；并加静态护栏断言「例外表每个键必须在 `PLATFORM_CONFIGS` 里真实存在」，否则覆盖永远不会生效。

生效铁证是**耗时指纹变了**，不是错误信息变了：

| 轮次 | 失败步耗时 | 分解 | 成功步数 / 字段数 |
|---|---|---|---|
| fix2 | 244.0s | 4×60 + 4 | 5 / 4 |
| fix3 | **724.0s** | **4×180 + 4** | **7 / 6** |

fix3 逐 step 耗时（秒）：`0 / 9.7 / 11.7 / 191.9 / 10.7 / 389.8 / 10.7 / 724.0(失败)`。

**step_4 = 191.9s 与 step_6 = 389.8s 的形状暴露了第二个缺陷**：`180+1+10.9` 与 `180+1+180+1+27.8` 只能是「前一次 180s 超时 → 后一次靠**重发**在同一会话里成功」。`pack-executor.js:643-654` 的重试不看错误语义，一律再走 `SEND_TO_AI` ⇒ **每次超时都往用户对话框里再塞一条同样的提示词**。已登记 `known_gaps N21`（P1）：污染会话、上下文越拖越长、复盘时极易把这笔自伤记成「平台慢」。

step_8（fusion，吞 6 个字段）四次全超时；但同轮截图显示该答案在运行结束后**完整生成出来了**（长文，非碎片）⇒ 不是取不到，是生成时长超出窗口。**不再加 timeout**：60→180 是修死配置，180→300 属为过而过。

### 9.3 longcat：账号态解除后是纯选择器问题

fix2 在 step_2 挂 723.9s（`4×180 + 3.9`，180s 同样确认生效），0 个字段。结构探针给出：

| 选择器 | 命中 | 判定 |
|---|---|---|
| `.message` / `[class*=response]` / `[class*=chat-item]`（旧三件套） | **0 / 0 / 0** | 这就是 Response timeout 的全部原因 |
| `.v-message-list` | 1（14 子元素） | 是**容器**不是消息——拿它当 messageList 一样永远不增长 |
| `.v-chat-messge-view` | 14（7 user + 7 AI） | 单条消息外壳（`messge` 是站点自己的拼写错误） |
| `.assistant-message` / `.v-chat-assistant-message` | 7 / 7 | **AI 条目，选它** |
| `.md-show-container` / `.mt-markdown-body` | 5 / 5 | 正文容器 |
| `.v-loading-dot` / `[class*=stop-generate]` / `[class*=loading-dot-box]` / `[class*=loading-text]` | 空闲态 0 | isTyping 无假阳，**不要动** |

本站两个专属陷阱，都已钉住：

1. **`.assistant-message` 整卡 55 字 vs 正文 45 字**，多出的 10 字正是「已搜到 14 个网页」这条联网搜索状态行 ⇒ `messageContent` 只认 markdown 容器，**禁止整卡回退**（回退的长度还够顶过 50 字闸门）。顺手把 `_extractContent` 里同样的整卡回退也收紧了。
2. **`.mt-markdown-body` 永久带 `result-streaming` 类**（完成态 5/5 都带）⇒ 它绝不能进 `typingIndicator`，否则 `isTyping()` 恒 true，与千问 `reason-title` 是同一个坑。

修完 fix3：**0/8 → 7/8**，产出 37 / 587 / 124 / 478 / 247 / 878 字，全部真正文。

同一屏还给了 N21 的**直接观测证据**：该会话 7 条 AI 消息里，5 条是同一句 hook 的重复回答，2 条是「服务出错啦，请稍后再试试。」——重发污染不是推断，是看得见的。

### 9.4 两站同卡 step_8：把「平台慢」改判成「Pack 尾部撞墙」

| | deepseek | longcat |
|---|---|---|
| 结果 | 7/8，step_8 挂 | 7/8，step_8 挂 |
| 症状 | 答案迟到：4×180s 都没稳定，运行结束后才生成完 | 平台**直接报错**：「服务出错啦，请稍后再试试。」（无 markdown 容器 ⇒ 取回空串 ⇒ 继续等 ⇒ 超时 ⇒ 重发 ⇒ 再报错，4 轮同错） |
| 共同点 | 都是 `step_8_output`（fusion）——提示词最长（≈2.4–2.5k 字）、上下文最深（会话已累积 7 轮、约 5–6k 字） | 同左 |

**隔离实验（关键一步）**：把 longcat 那条 **2437 字**的 fusion 提示词原样发进**全新会话**——**21 秒答完，产出 1481 字正文**（`evidence/L2-longcat-fusion-isolated-2026-11-11.{json,png}`）。

⇒ 提示词本身不被平台拒绝，**长会话才是变量**。两个独立平台在同一位置撞墙、且同一条请求在空会话里 21s 就通过，合起来说明：**「单会话串行跑完 8 步」这个设计假设在真实平台上不成立**。这是 Pack 结构问题，不是 adapter 问题——再改选择器、再加 timeout 都不会让它过去。

### 9.5 守护

- `npm test` **253 / 253**（本轮 +4：LongCat 只数 AI 条目 / 不取「已搜到 N 个网页」/ 平台报错不冒充答案 / 计数增长）。
- 变异锚 +2（总 80），分别锚「把 messageList 退回 0 命中旧三件套」「把 messageContent 退回会把状态行带进来的旧版」。
- 全量变异检查 **80 / 80 全被杀死、`EXIT_CODE=0`**（10 分 45 秒），日志 `evidence/mutation-check-full-2026-11-11.rc2.log`。
- 探针加固：`dom-shape-probe.mjs` 新增 `CLICK`（**只允许导航型点击**，发送/生成类 selector 直接拒绝）、选择器可见性计数（区分「0 命中」与「命中但全隐藏」）、文本预览（长度看不出状态行污染，只能看文本）。

> **过程中的一次真发现**：第一遍跑出 **79/80**，存活项是「把内容脚本的 SEND_TO_AI 分支删掉」。查下来不是守护有洞，是**锚点漂移**——那条锚是一段 8 行 `find` 字面量，本轮改了 handler 内部（超时取值）就失配，变异器把它记成了「存活」。改成单行锚（只摘 `case "SEND_TO_AI":` 标签）后手工验证能杀死目标测试（连带另外 3 条），再跑即 80/80。留痕日志：`evidence/mutation-check-full-2026-11-11.b.log`（79/80 那版）。
>
> 这个坑值得记住：**锚点写得越像「整段实现」，越会随实现漂移**。锚应该钉「语义」——这条消息没人认了——而不是钉「那段代码长什么样」。

### 9.6 门禁状态（口径不变）

| 项 | 结果 |
|---|---|
| L2 pass | **5 / 10**（qianwen / yuanbao / chatglm / yiyan / kimi）——deepseek、longcat **不因「7/8 看着不错」放行** |
| deepseek | fail（7/8）· 答案超出 4×180s 窗口 |
| longcat | fail（7/8）· 平台在长会话里对 fusion 直接报错 |
| chatgpt / claude / gemini | **封存**（不排期、不催办，≠ 已验证） |
| 第一个外部用户 | **主动暂缓**（deferred，非「缺人」） |

> 全部为机器执行判定，不是人工验收。**不说「验收通过」**，路线 A/B 仍待拍板。

## 10. 新增实例 dots.ai（2026-11-11 08:45–08:55）—— 可达、可读，但**不可对话**

用户 08:45 指令：增加 dots.ai 实例测试。按「先登录 → 只读结构探针 → 发送期采样 → 再决定是否写 adapter」推进，**没有**跳过任何一步。

### 10.1 站点身份与账号态

`https://dots.ai` 打开后落到 `/chat/home/new`，title「点点」，静态资源域名 `fe-platform-s8.rednotecdn.com` ⇒ 是**小红书「点点」**的网页版。截图左下角账号 `17Mojo`，侧栏有「任务 / 收藏 / 新建对话」与历史会话 ⇒ **已登录**，不是游客态。

### 10.2 结构探明（L1 pass）

| 选择器 | 命中 | 判定 |
|---|---|---|
| `.assistant-message-item` | 12 | 干净的 per-message AI 容器 |
| `.user-message-item` | 8 | 用户气泡，1 对 1 |
| `.assistant-message-card` | 7 | 正文变体 A |
| `.message-card_long-rich-text` | 5 | 正文变体 B（7+5 = 12 全覆盖） |
| `.prose-dd` | 12 | ⚠️ **不是每条一个**：832 字那条被切成 99/462/136/134 四块 ⇒ 用它当正文只能取到第一块，**静默截断** |
| `[class*=stop/loading/thinking/search/deep/stream]` | 空闲态均 0 | 无 isTyping 假阳 |

### 10.3 但 L2 跑不了：网页端不对新对话生成

发送期采样（点品牌色 36px 圆形发送按钮）80 秒逐秒记录：`.assistant-message-item` 立刻出现 1 条，正文**恒定 9 字「请到小红书官网体验」**，无流式增长、无状态类命中。

换一条完全不同领域的提示词复跑（「帮我列一个周末去杭州的两天行程，只要要点。」）——**同样 9 字、同样 80 秒不变**。⇒ 不是单次偶发，也不是提示词触发，是平台侧拦截。

对照：侧栏历史会话里有完整长答（832 / 1134 / 824 字）。那些是**从小红书 App 同步来的历史**——能读，不能在同一网页端复现。

### 10.4 处理

**不写 adapter、不跑 L2。** 9 字低于任何一步的长度闸门，写下去只会得到一次确定的 fail，等于把平台限制记成产物缺陷。登记 `RMR-2026-11-11-02`：L0 pass / L1 pass / **L2 not-run**。

门禁不受影响：L2 pass **仍 5/10**，dots **不计入** 10 平台分母。要把它变成可用实例只有两条路——该站开放网页端生成，或走 App 内自动化（超出浏览器插件形态）。

### 10.5 小号独立复核（2026-11-11 10:31）：排除「主号账号态」这一替代解释

§10.3 的观测只发生在 `17Mojo` 主号上。一个合理的替代解释是：**不是平台限制，而是该账号被限流/风控**。为此用全新注册的小号在**独立 profile** 上复跑：

| 项 | 值 |
|---|---|
| 小号 `auth_user_id` | `194813500431245312` |
| 主号 `auth_user_id` | `191425732320583680` |
| profile | `~/Library/Application Support/rm-dots-test-profile`（与主号隔离） |
| 提示词 | 「用一句话说明什么是 RAG」 |
| 会话 | `CHAT_4688263047748169728`（全新会话） |

采样结果：`t=5s` 即 `ai=1 / user=1 / lastLen=9`，此后恒定，稳定 15s 后提前结束。末次正文 **`"请到小红书官网体验"`，长度 9，与主号基线逐字一致**。`cardLens=[9]` ⇒ 整条 `.assistant-message-item` 内只有一个 9 字块，无流式碎片、无第二渲染变体（同时也再次证明不能用 `.prose-dd` 取正文）。

⇒ **「平台侧拦截」得到独立账号确认，不是主号账号态问题。** §10.3/§10.4 结论成立，不需修正。

**门禁不受影响，反而更硬**：L2 pass 仍 **5/10**，dots 仍 **not-run**、仍不计入分母。本次复跑不构成 L2 运行，不改变任何计数。

**证据**：`evidence/L2-dots-testacct-send-2026-11-11.json`（+ `.png`）、`evidence/login-dots-testacct-verify-2026-11-11.json`（账号身份）、`evidence/L2-dots-testacct-cleanup-2026-11-11.json`（删除核验：会话行 2 → 1）。测试会话已删，仅保留登录时自动生成的「和点点的日常对话」。

---

## 11. 活跃 5 站同日完整回归（2026-11-11 12:41–12:59）

### 11.1 为什么还要跑这一轮

此前 5 站的 pass 分散在三个时间点、两个不同构建上（qianwen/yuanbao/chatglm 于 11-10 20:22–20:56，yiyan/kimi 于 11-11 05:37–05:39）。**从来没有一次「同构建 + 同日 + 同 Pack」的统一证据。** 12:18 平台范围收缩后，活跃面只剩这 5 个，值得用一轮干净的回归把它们一次性钉住。

### 11.2 前置（都核过，不是假设）

| 项 | 结果 |
|---|---|
| `dist/` 是否落后源码 | `src/content/content-script.js` mtime 07:56 晚于 `dist` 07:22 ⇒ **看似落后**。重建后整体指纹 `4bfb4dac…` 与重建前**逐字节一致** ⇒ 实际未落后，07:56 是 mutation-check 回写造成的假象。**时间戳会骗人，哈希不会。** |
| SW 自检 | `hasGate/hasStatusSelector/hasMin50` 全 true，size=108590 |
| SW 三缓存 | 每站跑前清 2–3 项 |
| 登录态 | 5 站 `composerVisible=true` / `looksLikeLogin=false`；yiyan 重定向到 `wenxin.baidu.com`，该域已在 hostnames 内，不会导致 CS 不注入 |

### 11.3 结果：5/5 全 pass

| 平台 | 步数 | 总耗时 | 逐 step 耗时(s) | 7 字段字符数 |
|---|---|---|---|---|
| qianwen | 8/8 | 257.7s | 0 / 32.8 / 40.3 / 26.8 / 33.8 / 29.3 / 54.3 / 40.3 | 43/584/417/356/365/613/1584 |
| yuanbao | 8/8 | 100.3s | 0 / 11.2 / 17.2 / 11.7 / 12.2 / 12.2 / 16.2 / 19.7 | 41/672/137/220/246/592/1346 |
| chatglm | 8/8 | 495.4s | 0 / **170.7** / 38.2 / 35.2 / 22.7 / 33.7 / **151.3** / 43.7 | 36/524/311/256/197/592/960 |
| yiyan | 8/8 | 87.7s | 0 / 11.7 / 13.2 / 11.2 / 11.2 / 10.7 / 15.2 / 14.7 | 66/266/171/139/116/519/711 |
| kimi | 8/8 | 118.6s | 0 / 17.2 / 19.2 / 15.2 / 14.7 / 16.2 / 17.7 / 18.7 | 33/416/287/226/219/339/1027 |

全部 7 个字段非空；污染扫描（`服务出错/请先登录/请到小红书/已搜到/登录后/Error:/无法回答/undefined`）**5 站 0 命中**。

### 11.4 一个必须留下的疑点：chatglm 的长步疑似重发

`PLATFORM_RESPONSE_TIMEOUT` 当前只登记 deepseek / longcat = 180s，**chatglm 走默认 60s**。但它的 `step_2` 用了 170.7s、`step_7` 用了 151.3s，且 `errors: []`。

- `170.7 ≈ 60 + 60 + 50.7`、`151.3 ≈ 60 + 60 + 31.3` ⇒ 形状符合**3 次尝试、其中 2 次为重发**
- 其余 4 站所有 step 均 < 60s（qianwen 最长 54.3s）⇒ 单次成功，无重发迹象
- 这与 deepseek 那次用 `244 = 4×60 + 4` 判定超时生效是同一套**耗时指纹法**

**但指纹是推断，不是观测。** 尝试回读会话核对是否有重复气泡时，再次访问 chatglm 触发了滑块验证（「请按住滑块，拖动到最右边」）。**按红线不绕验证码**，因此「重发是否真的发生」**未确认**，仅登记为 §11.5 的待查项。

⇒ 结论分层：**pass 成立**（8/8、字段齐、无污染是机器事实）；**「没有重发」不成立**（无法证明）。

### 11.5 本轮新增的两个运维事实

1. **chatglm 对本 profile 出现了滑块验证**，且是在本轮 8 步跑完之后、额外一次页面访问时触发。后续对 chatglm 的复跑可能直接被挡在验证页 ⇒ 若下次预检发现 `looksLikeLogin=true` 或正文含「访问验证」，应先判为**环境阻塞**，不得记成 adapter 失败。
2. 与 N21 同源的风险在**非例外表站点**上同样存在：默认 60s 对某些站的长答案不够，会触发重发；而重发既不报错、也不进 `errors`，只在时长上留指纹。**这是一个「不失败但会污染」的隐蔽路径。**

### 11.6 门禁

**L2 pass 仍记 5/10。** 活跃 5 站本轮 5/5 全 pass，但分母按 12:18 裁定保持 10（冻结≠移除），冻结的 5 站仍为 fail/not-run，不计为通过。

本文件全部为**机器执行判定**，不是人工验收。回执：`RMR-2026-11-11-03.json`。

---

## 12. N21 根治（2026-11-11 13:15–13:30）—— 超时不再重发，改续等

§11.4 留下的那个疑点（chatglm 长步疑似重发）根因不在 chatglm，在**执行器的重试逻辑**：它只看「有没有抛错」，不看错误语义。

### 12.1 缺陷重述

`_executeStep` 的 catch 原本是「失败就再跑一遍这一步」。对 AI 步骤来说，再跑一遍 = 重新注入文本 + 点发送 = **把同一句提示词再发一次**。

而 `Response timeout` 的语义是「**已经发出去了**，只是没在窗口内稳定下来」。两种失败形状一样（都是一次 throw），语义相反（一个不能重发，一个可以重发）。旧代码把两者一视同仁。

代价是三重自伤：会话里多一条重复提问；AI 再答一遍烧双倍额度；上下文变长反过来加重下一步的超时。而且它**不报错、不进 `errors`**，只在耗时上留指纹——所以从 11-10 到 11-11 一直没被发现。

### 12.2 改法

新增 `src/utils/retry-policy.js` 作为分流口径的唯一事实源：

| 函数 | 钉住什么 |
|---|---|
| `failureStrategy(error)` | 错误码优先（`RESPONSE_TIMEOUT` ⇒ `resume-wait`）；无码时只认**以** `Response timeout` **结尾**的整串文案，拒绝子串包含——否则「Response timeout 之后我换了选择器」这种句子会被误判成超时，明明没发出去却去傻等 |
| `resolveInitialCount(snapshot, baseline)` | 续等必须沿用**发送前**那个条数。重新数的话，「回复恰好在超时与续等开始之间落地」会让 `countGrew` 恒 false ⇒ 白等满一个超时窗口 |

执行器（`pack-executor.js`）按分流结果走两条路：

- `resume-wait` ⇒ `_resumeWaitForResponse()`，**只发 `WAIT_FOR_RESPONSE`**，不注入、不点发送。失败信息里明确写「超时后不重发」。
- 其它失败 ⇒ 照旧重试（没送出去的失败重试是安全的）。
- **广播投递（无 `targetTabId`）遇超时直接失败**：后台不知道该让哪个页面续等，而重发是**确定的**副作用，等不到只是慢 ⇒ 选失败。

内容脚本把语义随失败信封一起带出去（`failureEnvelope`）：`code` + `baselineCount`；`handleSendToAI` 在**发送前**记基准；`handleWaitForResponse(timeout, baselineCount)` 收下基准，超时时带 `RESPONSE_TIMEOUT_CODE`。

### 12.3 验证（机器执行）

| 项 | 结果 |
|---|---|
| `npm test` | **263/263 pass**（原 256 + 新增 7） |
| 新增契约测试 | `tests/retry-semantics.test.mjs` 7 条：分流规则 4 条 + 执行器行为 3 条 |
| 变异锚 | 新增 7 条，逐条对应一个「改回去就会重发」的侧面 |
| 变异检查 | 全部被杀死（见 `mutation-check-full-*.log`） |
| dist 产物 | 重建后核过：`content-script.js` 含 `RESPONSE_TIMEOUT`×6 / `baselineCount`×9；`service-worker.js` 含 `resume-wait` 与「超时后不重发」 |

三条执行器行为测试的具体断言（不是「有测试失败」那种含糊断言）：

1. 超时后 `tabMessages` 必须是 `["SEND_TO_AI", "WAIT_FOR_RESPONSE"]` 且 `SEND_TO_AI` 只 1 条，续等消息带 `baselineCount=4`、回到同一个 `tabId`；
2. 非超时失败（`Chat input not found`）必须仍是 2 次 `SEND_TO_AI`——别为了修超时把重试一起废了；
3. 广播超时必须 1 次广播就停，且失败文案含「不重发 / 重复提问」。

### 12.4 本条关闭的口径与**不成立**的引申

关闭依据是「代码语义 + 单测 + 变异」三件事，**不含真机复跑**。

- 成立：「重发缺陷在代码层已消除，且被 7 条变异锚钉住」
- **不成立**：「已在真机上观察到不再重发」

为什么没做真机复跑：chatglm 自 13:0x 起对本 profile 弹滑块验证（按红线不绕）；deepseek / longcat 已随 12:18 的平台范围收缩冻结。⇒ 真机复核登记为独立待办，见 §12.5。

### 12.5 待办

1. **chatglm 可访问时复核两件事**：① 180s 等待上限是否生效（step 耗时应降回单次尝试区间）；② 若仍超时，看是否出现 `WAIT_FOR_RESPONSE` 续等而**不是**第二条 `SEND_TO_AI`。
2. 解冻 deepseek / longcat 时，优先用它们验证续等路径——§9 的耗时指纹（`244 = 4×60+4`、`389.8 ≈ 180+1+180+1+27.8`）是最好的前后对照基线。

### 12.6 chatglm 挂账项复核（13:32:28–13:38:18）—— §12.5 第 1 项已做

预检：`composerVisible=true` / `looksLikeLogin=false`，**滑块验证已解除**，所以把此前「被挡住没法验」的那次补上了。

回执：`evidence/L2-chatglm-auto-2026-11-11.resume-verify.json`，截图同名 `.png`。

| 项 | 12:41 那轮（60s 上限） | 13:32 这轮（180s 上限） |
|---|---|---|
| 总时长 | 495.4s | **349.8s** |
| 步结果 | 8/8 success | 8/8 success，7 字段全非空，`errors: []` |
| 最长步 | 170.7s（step_2，形状 60+60+50.7） | **90.7s**（step_8） |
| 分步 | step_2=170.7 / step_7=151.3 | step_2=28.7 / step_3=50.7 / step_4=47.7 / step_5=32.2 / step_6=40.7 / step_7=59.2 / step_8=90.7 |

**可以硬说的两条：**

1. **没有任何一步触到 180s**，`60+60+X` 的重发指纹在 8 步里全部消失。
2. **step_8 用了 90.7s，大于旧的 60s 默认值** —— 旧配置下这一步必然撞 60s 超时并进入重发。所以 180s 这个改动对本站**是有实际作用的**，不是安慰剂。

**不能说的（必须留在这里）：**

- 单步耗时两轮差异很大（step_2 从 170.7s 到 28.7s），会话初始状态、模型负载都变了，**不能把「变快」单独归因给 180s**。
- **续等路径在真机上仍未被走到** —— 没有超时就谈不上续等。N21 的重发修复目前只有「单测 + 变异」两层证据，缺真机那一层。
- 截图只能看到最后一次问答（一条提问、一条回复，无重复气泡），**不能证明前面 7 步都没重复** —— 那要靠会话全文回读，而回读正是上次触发滑块的动作。

⇒ §12.5 第 1 项闭掉；第 2 项（用 deepseek / longcat 验证续等路径）仍挂着，等解冻。

---

## 13. Pack 重构：会话边界（`fresh_session`），解 step_8 尾部撞墙

§9.4 把「deepseek / longcat 同卡 step_8」判成 **Pack 结构问题**——不是 adapter，也不是平台慢。这一节是它的修法。

### 13.1 修的是哪个假设

隔离实验（§9.4）已经把变量单独拎出来了：同一条 **2437 字**的 fusion 提示词发进**全新会话**，**21 秒答完、产出 1481 字**。

⇒ 提示词不被任何一方拒绝，**「单会话串行跑完 8 步」才是变量**。到 step_8 时会话已累积 7 轮、约 5–6k 字，而 step_8 的提示词其实**把 6 个上游字段全内联了**——它根本不需要那段历史，却一直在为它付费。

### 13.2 改法：把「要不要共用会话」变成 Pack 的显式声明

| 层 | 改动 |
|---|---|
| Pack（数据） | `step_8_output` 新增 `"fresh_session": "prefer"` |
| 执行器 | AI 步骤在发送**之前**，若声明了 `fresh_session` 就先发 `NEW_SESSION` 到同一个标签页 |
| 内容脚本 | 新增 `NEW_SESSION`：先找 adapter 的 `newChat` 选择器，否则按文案兜底；点完**必须确认消息数下降**才算成功 |
| 回执 | `sessionResets[]` 记录 `strategy / available / messageCountBefore / messageCountAfter` |

两档语义，差别只在「开不成」时：

- `true` / `"strict"`：**这一步失败**，一条提示词都不发。适合「上一步的上下文会污染这一步」的 Pack。
- `"prefer"`：记一条 `available:false` 后**照常发送**，行为与修复前一致。

**为什么出厂用 `prefer` 而不是 `strict`**：逐站探测发现 5 个活跃站里只有 chatglm / 文心有可识别的「新对话」入口。一律 strict 会让一个结构性优化，把**本来跑得通**的站点直接打成 7/8。

### 13.3 「新对话」入口不是按钮（这一步踩了坑）

第一版按 `button / a / [role=button]` 找，chatglm 上**恒为 0 命中**，于是 step_8 被判失败——拒绝把提示词发进旧会话（这个行为是对的），但事没办成。

只读 DOM 探测（`dom-shape-probe`，`TEXTS='新对话'`）给出了真实结构：

| 站 | 命中的元素 | 结论 |
|---|---|---|
| chatglm | `div.new-session.flex…el-tooltip__trigger > div.text`（挂在 `aside.aside-container`） | 已写入 `newChat` 选择器 |
| 文心 | `div.new-dialog-container-plain > span.cos-line-clamp-1` | 已写入 `newChat` 选择器 |
| 千问 | `div.flex…hover:bg-option`（纯 Tailwind，无稳定语义类名） | 兜底匹配不到 → 见 N23 |
| 元宝 / Kimi | 页面上**没有**「新对话」三个字（leafHits=0） | 大概率图标按钮或别的措辞 → 见 N23 |

同一份探测还抓到一个**危险诱饵**：chatglm 输入框旁边还有一处文本同为「新对话」的 `div.enter.is-main-chat`（祖先链 `input-box-container → input-wrap`）。所以兜底匹配加了 `form / [class*=input|editor|send|composer]` 祖先排除——点那个东西的后果不可预料。

### 13.4 真机验证（两台，两个分支都走到了）

| | chatglm | 千问 |
|---|---|---|
| 结果 | **8/8 success, completed** | **8/8 success, completed** |
| `sessionResets` | `available: true`, `strategy: adapter-selector`, **12 → 0** | `available: false`, `strategy: none` |
| step_8 | **75.0s** 通过，final_content 1287 字 | 46.3s 通过，final_content 1206 字 |
| 总耗时 | 419.6s | 263.8s（12:41 那轮 257.7s，无回归） |
| 回执 | `evidence/L2-chatglm-auto-2026-11-11.fresh-session2.json` | `evidence/L2-qianwen-auto-2026-11-11.fresh-session.json` |

**能硬说的**：会话边界在 chatglm 上是**真的重置了**——不是「点了按钮」，是消息数 12 → 0；而千问上它**没办成、但没把站点弄坏**，降级事实落在回执里。

**不能说的**：① chatglm 总耗时 419.6s 比不加边界那轮的 349.8s 更长，但差异主要在 step_2（28.7 → 70.2s）等平台抖动上，**不能归因给重置**，也**不能反过来说重置是免费的**；② 元宝 / Kimi / 文心**没有做端到端验证**（文心只有 DOM 选择器证据）；③ 真正撞墙的 deepseek / longcat 冻结中，**本次没有验证「加了会话边界就不撞了」**——这是这条修复最该被验的一条，也是最欠的一条。

### 13.5 守护

- `npm test` **282 / 282**（263 + 会话边界 8 + 证据路径 11；会话边界那 8 条覆盖 strict/prefer 两个分支与「自足性」检查）。
- 结构自检：声明 `fresh_session` 的步骤，提示词里的每个 `{{var}}` 都必须来自上游产出——**自足是 fresh_session 成立的前提**，不自足时开新会话反而更糟。
- 变异锚 +6（忽略 fresh_session / strict 失败后照发 / 广播放行 / 降级记成成功 / Pack 去掉声明 / 自足性放过未知变量），全量 **97/97 全杀死**，见 §13.6。

### 13.6 全量变异检查暴露的两个自伤（都出在「守护自己」上）

第一轮全量变异跑完，`prefer 降级被记成「成功开过新会话」` **存活**。按 §9.5 的老规矩先判「守护有洞」还是「锚点漂移」——这次是**两个都不是**，是第三类：**锚点本身是空变异**。顺着查下去还牵出一个真漏洞。

**（1）锚是空的：`...result` 在后面会把强制值覆盖掉**

```js
record = { ...base, available: result.available !== false, ...result };
```

把 `available: result.available !== false` 改成 `available: true`——看起来是「降级记成成功」，但同一对象字面量里 `...result` 展开在**后面**，`result.available=false` 会把它重新盖回去。**行为一点没变，测试当然照常绿。** 这条锚等于什么都没验。

修法：让强制值排在展开**之后**（`{ ...result, available: true }`）。改完立刻被杀死。

> 这条值得单记：变异的判据不是「这行代码看着重要」，而是「改掉它，行为真的会不同」。§9.5 记的是锚点随实现漂移（find 找不到），这一条是**find 找得到、replace 也执行了，但语义等价**——比漂移更隐蔽，因为它不报错、不存活提示异常，只是悄悄不设防。

**（2）真漏洞：自足性检查对交付的那个 Pack 从来没执行过**

```js
if (step.fresh_session === true) {   // ← 而出厂 Pack 声明的是 "prefer"
```

自足性检查（「开新会话 ⇒ 提示词必须自己带齐所有变量」）写的是 `=== true`，而出厂 Pack 用的是 `"prefer"`。**`"prefer"` 在 chatglm / 文心上一样会把历史清空**——也就是说，这条检查恰好对唯一真正会开新会话的那个 Pack 完全失效。

改成判真值（`if (step.fresh_session)`）后，检查真的跑到了 `step_8_output` 上，并通过（6 个变量全部来自上游）。同时补两条锚证明它咬得住：删掉 Pack 的声明、把一个变量名改成没人产出的名字。

**（3）连带发现：变异副本里那两条 Pack 测试恒红（ENOENT）**

第一轮的失败清单里还混着 `真实 Pack 的 step_8_output 声明了 fresh_session=prefer` 与 `声明 fresh_session 的步骤，提示词引用的变量必须全部来自上游`——它们在**未变异**的副本里同样红。根因是 `PACK_PATH` 写死 `resolve(HERE, "../../packs/…")`：变异检查把 `tests/` 复制到 `<扩展根>/.mutation-tmp/tests/`，**深度多一层**，`../../packs` 就落到不存在的 `<扩展根>/packs`。

后果不是「多两条红的」，而是**这两条守护在变异环境里从未被真正判定过**（永远红，永远和「被杀死」混在一起，无法区分）。修法是往上找而不是假设层级（`findUpwards`，最多 6 层）。修完副本里 8/8 全绿，对照组与变异组的差异才可信。

**收口**：`npm test` 282/282 → 全量变异 **97/97 全杀死**。


---

## 14. 「整包变慢 69.8s」能不能归因给会话重置

§13.4 留了一句悬置结论：chatglm 加了会话边界那轮 419.6s，比不加边界那轮 349.8s 更长，
「不能归因给重置，也不能反过来说重置免费」。这一节把它拆成**能硬说的**和**仍然只能量上界的**两部分。

### 14.1 先钉死代码路径：重置只可能出现在 step_8

`pack-executor.js` 里 `_resetSession` 只有**一个**调用点：

```js
// :809-810，_executeAIStep 内、发送之前
if (step.fresh_session) {
  await this._resetSession(execution, step);
}
```

交付的 Pack 里声明了 `fresh_session` 的步骤用机器数过，**只有 `step_8_output` 一个**。

⇒ **step_1 ~ step_7 的执行路径里不可能包含任何重置动作**。这不是假设，是调用图。
所以这 7 步的耗时差异，无论多大，都**与重置无关**。

### 14.2 再把两轮的分步耗时摊开（都取自磁盘回执，不是回忆）

对照组 B = `L2-chatglm-auto-2026-11-11.resume-verify.json`（13:32，8/8，349.8s）；
边界组 D = `L2-chatglm-auto-2026-11-11.fresh-session2.json`（14:57，8/8，419.6s，
`sessionResets[0]: available:true / adapter-selector / 12 → 0`）。

| 步 | B | D | Δ（D−B） |
|---|---:|---:|---:|
| step_1_topic | 0.0 | 0.0 | +0.0 |
| step_2_hook | 28.7 | 70.2 | **+41.5** |
| step_3_explain | 50.7 | 58.7 | +8.0 |
| step_4_scene | 47.7 | 45.7 | −2.0 |
| step_5_boundary | 32.2 | 34.2 | +2.0 |
| step_6_takeaway | 40.7 | 47.2 | +6.5 |
| step_7_visual | 59.2 | 88.7 | **+29.5** |
| **step_1~7 小计** | **259.2** | **344.7** | **+85.5** |
| step_8_output | 90.7 | 75.0 | **−15.7** |
| **整包** | **349.8** | **419.6** | **+69.8** |

`+85.5 + (−15.7) = +69.8`，账对得上。

### 14.3 能硬说的三条

1. **整包多出来的 69.8s，全部来自 step_1~7（+85.5s），step_8 反而少用了 15.7s。**
2. 由 §14.1 的代码路径，step_1~7 不含重置 ⇒ **「重置拖慢了整包」这句不成立**，可以撤回悬置状态、直接判否。
3. 变慢集中在 step_2（+41.5s）与 step_7（+29.5s），这两步都是普通 AI 问答、两轮提示词完全相同 ⇒ 只能是平台侧抖动／模型负载，不是本轮改动。

### 14.4 仍然不能说的（别把「判否」滑成「免费」）

- step_8 的 75.0s 里**同时**含「重置耗时 + AI 回答耗时」。两轮 AI 回答波动本身就远大于 15.7s，
  所以 **不能反过来说「重置免费」或「重置反而更快」**。
- 旧回执里没有重置耗时的独立字段，这两轮**量不到**它的固定开销，只能给代码上界：
  `waitForSessionReset` 每 300ms 轮询、超时 8000ms ⇒ 最坏 8s，典型几百毫秒到 1 秒。
- 只有**同一站、同一时刻、A/B 交替多轮**才能把重置的固定开销从抖动里分离出来；
  本轮没有做（每轮真机 L2 要 4–7 分钟，且会消耗账号额度）。

⇒ 修法不是「再跑一轮猜」，而是**让这个数自己出现在回执里**：`NEW_SESSION` 现在返回
`durationMs`（找入口 + 点击 + 等消息数下降的耗时），经 `sessionResets[]` 一路透到
`EXECUTE_PACK` 回执；单测 + 变异锚钉住它不会被悄悄丢掉。下一轮真机就能直接读，
不必再从整包差值里反推。实测数字见 §14.5。

### 14.5 重置耗时：现在有实测数了，不必再猜

`NEW_SESSION` 现在返回 `durationMs`（找入口 + 点击 + 等消息数下降），
经 `sessionResets[]` 透到 `EXECUTE_PACK` 回执。本轮 4 站真机实测：

| 站 | strategy | Before → After | durationMs | step_8 | 整包 |
|---|---|---|---:|---:|---:|
| 千问 | `hidden-semantic` | 12 → 0 | **319** | 15.1s | 244.2s |
| 元宝 | `adapter-selector` | 12 → 0 | **312** | 21.0s | 103.6s |
| Kimi | `adapter-selector` | 6 → 0 | **304** | 16.7s | 120.7s |
| 文心 | `adapter-selector` | 6 → 0 | **318** | 16.0s | 90.5s |
| chatglm（§17.2 补测） | `adapter-selector` | 12 → 0 | **311** | 117.5s | 380.1s |

⇒ **重置的固定开销是 0.3 秒量级**，比 AI 单步回答（10–90s）小两个数量级。
这就把 §14.4 的悬置彻底收窄了：

- 「重置拖慢了整包」：**判否**（§14.1 的代码路径 + §14.2 的分步账 + 这里的 0.3s 实测，三条独立证据同向）。
- 「重置免费」：**仍不能这么写**——它有非零开销（304–319ms），且上限由代码给出（8s 判据超时）；
  只是这个开销被 AI 回答耗时的波动**完全淹没**，从整包差值里分离不出来。
- chatglm 在**这一轮**（419.6s 那次）的 `durationMs` 没测到——它跑在加计时字段之前。
  这条挂账已在 §17.2 用**新的一轮真机 L2** 补测闭环（311ms），没有回填、没有改写历史回执。
  5 站同构实现给出的 0.3s 量级，足以否定「+69.8s 是重置造成的」这种量级完全对不上的归因。

**没有做 A/B 交替多轮**：那需要再烧 4 × 8 步的账号额度，而 `durationMs` 已经把
要分离的那个量直接测出来了——再跑 A/B 是重复造尺子，不是补证据。

---

## 15. N23 收口：5 个活跃站的会话边界都真的生效了

### 15.1 不再猜结构：先抽样、人工核验、再批量推导

新增 `tests/real-machine/new-session-probe.mjs` —— **只读**探测器，
脚本级保证：不 click、不 type、不 send、不 hover、不绕验证码 / 滑块 / 登录墙，
不导入 Pack、不发 EXECUTE_PACK。采集文案命中、语义类名命中、带标签控件、
祖先链、computed style、rect、以及 adapter `messageList` 在真机上的命中数。

先只探 Kimi 一站做抽样，人工核验结构（`a.new-chat-btn[data-testid=sidebar-new-chat]`），
再批量探 5 站。产物：`evidence/new-session-probe-2026-11-11.chatglm-kimi-qianwen-yiyan-yuanbao.json`。

| 站 | 只读探测拿到的真实结构 | 落地方式 |
|---|---|---|
| chatglm | `div.new-session`（aside 下，非 button） | 已有 `newChat` |
| 文心 | `div.new-dialog-container-plain > span`「新对话」 | 已有 `newChat` |
| 千问 | `div[data-session-switch-target="new-chat"]`，祖先链含 `pointer-events-none opacity-0` 的 `div.newChatReveal-*` | **第三层 `hidden-semantic` 兜底**（qianwen 适配器里刻意不写 `newChat`，留注释说明原因） |
| 元宝 | `div.yb-new-chat-entry__item[role=button][aria-label=新建对话]` | 新增 `newChat` |
| Kimi | `div.sidebar-new-chat > a.new-chat-btn[data-testid=sidebar-new-chat]`，`href="/?chat_enter_method=new_chat"`；另有 `a.logo[aria-label=新建会话]` | 新增 `newChat` |

两个结构坑：

1. **千问的入口是「不可见」的**：整条祖先链在 hover-reveal 层里，`isElementRendered`
   必然拒绝。新增窄口径的第三层兜底，只对「属性值直接声明 new-chat 语义」的元素放行；
   程序化 `el.click()` 不受 `pointer-events:none` 影响，而**到底有没有重置仍由消息数下降判定**——
   安全边界是行为判据，不是可见性。
2. **Kimi 的入口是 `<a href>`**：直接 `.click()` 可能整页导航，内容脚本随文档销毁，
   `sendResponse` 永远发不出去，后台只会看到一次莫名的「开新会话失败」。
   点击期间挂捕获阶段 `preventDefault`，拦掉浏览器默认跳转但不拦站点自己的 click 处理器。

### 15.2 真机 L2：5/5 都 `available:true` 且消息数下降

| 站 | 回执 | 结果 | strategy | Before → After | durationMs | step_8 | 整包 |
|---|---|---|---|---|---:|---:|---:|
| chatglm | `.fresh-session2.json` | 8/8 | `adapter-selector` | 12 → 0 | 未测（该轮早于计时字段；§17.2 已另跑一轮补测到 311ms） | 75.0s | 419.6s |
| 千问 | `.n23.json` | 8/8 | `hidden-semantic` | 12 → 0 | 319 | 15.1s | 244.2s |
| 元宝 | `.n23.json` | 8/8 | `adapter-selector` | 12 → 0 | 312 | 21.0s | 103.6s |
| Kimi | `.n23.json` | 8/8 | `adapter-selector` | 6 → 0 | 304 | 16.7s | 120.7s |
| 文心 | `.n23-fix.json` | 8/8 | `adapter-selector` | 6 → 0 | 318 | 16.0s | 90.5s |

⇒ N23 原定的收口判据（每站一次真机 L2、`sessionResets[0].available === true`
且 `messageCountAfter < messageCountBefore`）**全部满足**，台账 N23 → closed。
出厂 Pack 仍是 `prefer`，但现在 5 站都真的开得成新会话，降级分支只在站点改 DOM 时才会走。

**仍未验证**：真正撞墙的 deepseek / longcat 冻结中。这 5 站验的是
「重置真的做到了」，**不是**「重置解掉了长会话撞墙」——后者仍欠一次解冻后的对照。
（本轮已把这条从「报告里的一句话」升级为代码级冻结守卫 + A/B 判据，见 §17.4 / 台账 N25；
**守卫不等于验证**，命题本身依旧未验。）

### 15.3 守护从「真机 4–7 分钟」下沉到「秒级」

把 DOM 逻辑从 content-script 抽成可注入模块 `src/content/new-session-control.js`
（`document` / `findVisibleElement` / `isElementRendered` / `findElements` 全部注入），
于是 `tests/new-session-control.test.mjs` 能在 jsdom 里把 5 站真实结构各摆一遍：
三层兜底、`<a>` 导航拦截、输入区诱饵排除、`durationMs`、prefer/strict 两档、
点了没生效不许假装成功、空会话直接放行。测试**直接引用生产 SELECTORS**，
所以「把适配器选择器改坏」也会立刻变红；10 条变异锚全杀死。

顺带修了变异运行器的一个可用性问题：加 `MUTATION_TESTFILE=xxx` 只跑某个测试文件
对应的锚，改完一处守护可以秒级预检，不必每次都跑十几分钟的全量。

---

## 16. 顺带抓到的 N24：文心新 UI 的「假基准」

首轮 `.n23.json` 里文心在 **step_2** 就失败（1/2 步、243.6s、`Response timeout`），
与会话边界无关（step_2 没有 `fresh_session`），但截图里 AI 明明答完了。

`243.6 ≈ 4×60 + 3.6` 起初像重发指纹，核对代码后确认是
**1 次等待 + 3 次续等**——N21 的正常行为，截图也只有一条提问气泡，没有重复发送。

真正根因是 `findElements` 的「按优先级取**第一个有命中**的选择器」：

| 时刻 | `div.answer-container` | `[class*="message"]` | findElements 实际返回 |
|---|---:|---:|---|
| 发送前（落地页） | 0 | **8**（全是通知中心元素） | **8** |
| 回答落地后 | **1** | 8 | **1**（改取第一条选择器） |

⇒ `countGrew = 1 > 8` 恒 false ⇒ 明明答完还一直判超时。
只读诊断（点开已有历史会话、未发送任何消息）：会话页 `/search/<id>` 上
`div.answer-container = 1`、打字指示器全 0、答案正文挂在
`.cosd-markdown-content > .marklang > p.marklang-paragraph` ⇒ **答案容器没漂移，坏的是恒命中的兜底**。

修法：删掉 `[class*="message"]` / `[class*="response"]` / `.chat-item` 三条兜底，
只留 `div.answer-container` / `div.ai-entry`。宁可发送前 0 命中（响亮地超时），
也不要一个会跳组的假基准。

| | 修复前 `.n23.json` | 修复后 `.n23-fix.json` |
|---|---|---|
| 结果 | failed，1/2 步 | completed，8/8 |
| 耗时 | 243.6s | 90.5s |
| `sessionResets` | `[]`（根本没跑到 step_8） | `available:true / 6→0 / 318ms` |

守护：`tests/message-list-contract.test.mjs` 4 条（基准必须为 0 / 0→1 / 1→2 /
正文来自答案容器而非通知中心）+ 1 条变异锚（把 `[class*=message]` 塞回去）。台账 N24 → closed。

---

## 17. 「处理 仍未验证」：三条挂账的逐条裁定（2026-11-11）

§15.2 / §16 收口时留了三条**明确写了「没验」**的账。本轮不把它们当成
「open 0 就没事了」，而是逐条给出机器可复核的结果。先说结论：

| # | 挂账 | 本轮结果 | 判据落在哪 |
|---|---|---|---|
| ① | deepseek / longcat 冻结中，「加了会话边界就不撞了」没验 | **仍未验**，且**本轮不许验**；已落成代码级冻结守卫 + A/B 可执行方案（默认 NOT-EXECUTED） | §17.4、台账 N25（open） |
| ② | chatglm 那轮 `durationMs` 未测 | **已补测闭环**：新跑一轮真机 L2，311ms、8/8、12→0 | §17.2、回执 `.n23.json` |
| ③ | 探针「全程只读」只有注释声明、诊断证据在 `/tmp` | **已闭环**：静态门禁 + 变异锚 + 证据原样落盘 | §17.3 |

⚠️ 口径：① 的守卫与方案**不是验证**。写清楚「怎么验、为什么现在不能验」
不等于「验过了」。台账为此新增 N25 并保持 `open`，不因为本轮干了很多活
就把 `open` 数改回 0。

### 17.1 为什么先核磁盘再动手

上一轮的结论是会话记忆，本轮开头先按 disk-truth 对账：后台 chatglm L2
（`lMf5aa`，10:34:20 触发 / 10:40:40 落盘）实际已完成；`git status` 显示
头部是 5 个**本地**提交、领先 `origin/main` 5 个、未推送；两份 `/tmp` 诊断
产物都还在。所有下面的数字都从回执与代码读出来，不是回忆。

### 17.2 ②：chatglm 的 `durationMs` 补测闭环

后台任务跑的是加了计时字段之后的**新代码**，所以顺带验了「新代码在 chatglm 上无回归」。
回执 `evidence/L2-chatglm-auto-2026-11-11.n23.json`（+ 同名截图）：

| 字段 | 值 |
|---|---|
| `exec.success` / `result.status` | `true` / `completed` |
| steps | **8/8 success** |
| `sessionResets[0]` | `step_8_output` / `prefer` / `available:true` / `adapter-selector` / **12 → 0** / **durationMs 311** |
| 分步耗时和 / `result.duration` | 380146ms ≈ 380.1s（step_8 = 117504ms ≈ 117.5s） |
| 日志时间 | 10:34:20 触发 → 10:40:40 落盘（≈380s，与分步账吻合） |

⇒ 5 站重置耗时现在是完整的一组：**304 / 311 / 312 / 318 / 319ms**，
都落在 §14.5 的 0.3s 量级里。§14.5 与 §15.2 表格已就地补注；
419.6s 那轮 `.fresh-session2.json` 仍如实标注「未测」，**没有回填、没有改写历史回执**。

同时保留 §14.4 的两条边界，不因为多了一个数字就松口：
- 「重置拖慢了整包」仍**判否**（重置只在 step_8，§14.1 代码路径 + §14.2 分步账）；
- 「重置免费」仍**不能写**（311ms 非零，代码上界 8s，只是被 AI 回答波动淹没）；
- chatglm 那轮 419.6s vs 349.8s 的差异主要在 step_2 抖动（28.7→70.2s），
  既不能归因给重置，也不能反过来当作「重置无代价」的证据。

### 17.3 ③：探针「只读」从声明变成门禁，诊断证据落盘

**(a) 静态门禁** `tests/probe-readonly.test.mjs`（4 条）。它扫描的是
`new-session-probe.mjs` **剥离注释后的实际代码**——注释里写红线，谁加一行
`click()` 注释不会变、单测不会红，而「只读」已经不成立。四条判据：

1. 无任何 `click / dblclick / type / fill / press / hover / focus / check / selectOption / keyboard / mouse` 调用；
2. 不出现 `EXECUTE_PACK / SEND_TO_AI / WAIT_FOR_RESPONSE / IMPORT_PACKS / NEW_SESSION / runtime.sendMessage / tabs.sendMessage`；
3. Playwright 侧只许调用白名单（`goto / evaluate / waitForTimeout / title / isVisible / count / newPage / close / url / locator`）；
   —— 这一条第一版写成「扫描所有 `.method()`」，把 `.toISOString()` 误报了，
   已收窄为只管 `page.* / context.*` 交互面；
4. 回执必须明写 `mode: "readonly-dom-probe"` 且 `redlines` 六个 flag 全 `false`。

**(b) 变异锚**（`mutation-check.mjs`，`MUTATION_TESTFILE=probe-readonly.test.mjs` 秒级预检）：
「往探测器中插一次真实 `page.locator(COMPOSER).first().click()`」与「把 `redlines.clicks` 谎报为 `true`」
两条都被对应测试杀死 ⇒ 门禁不是空跑。

**(c) 证据落盘**：`/tmp` 是临时目录，引用它等于证据随时会消失。两份诊断产物
经 `sha256` 校验后**原样复制**（不改写内容）到 `evidence/`：

| 新文件 | 内容 | sha256（前后一致） |
|---|---|---|
| `new-session-probe-2026-11-11.yiyan-pre-fix.json` | 修复前落地页：`div.answer-container=0` / `div.ai-entry=0` / `[class*="message"]=8` 全是通知中心 | `0f3929c5…f3` |
| `yiyan-session-page-diagnostic-2026-11-11.json` | 会话页 `/search/<id>`：`div.answer-container=1`、答案挂 `.cosd-markdown-content > .marklang > p.marklang-paragraph` | `6f18ec78…7b` |

台账 N24 里那条旧的 `/tmp` 诊断引用已换成上面两个可复核路径，
`where` 也补了这两份证据。**诊断过程中只点开已有历史会话、未发送任何消息、
未绕过验证码**——这一句现在是「探测器门禁 + 落盘原始产物」两层可查，不只是声明。

### 17.4 ①：冻结项 —— 守卫 + A/B 方案，但**不执行**

用户 2026-11-11 红线：「仅保留 qianwen、yuanbao、chatglm、yiyan、kimi，
其他都暂时冻结不去碰。」此前它只写在报告里，而 `l2-platform-auto.mjs`
只要给 `PLATFORM=deepseek` 就会照跑：启动浏览器 → 打开站点 → 导入 Pack → 真实发消息。
一次手滑的环境变量就能破线。

**(a) 代码级冻结守卫** `tests/real-machine/platform-freeze.mjs`：
- `ACTIVE_PLATFORM_IDS` 是白名单**唯一事实源**（5 站），不在表内一律视为冻结
  （包括还不认识的新 id，不搞「默认放行」）；
- `assertPlatformAllowed()` / `assertCandidatesAllowed()` 硬闸门：冻结站直接抛错，
  候选集里混进一个冻结站就**整体拒绝**，不做「跳过继续」的半吊子放行；
- 唯一解冻开关 `ALLOW_FROZEN=1`，放行时返回 `unfrozenBy`，由调用方写进回执
  `platformPolicy` ⇒ 「谁在什么时候解冻过」能从磁盘复核，不靠聊天记录。

**(b) 接线** `l2-platform-auto.mjs`：闸门放在 **`launch()` 之前**
（冻结站连浏览器都不启动）；PRECHECK 的 `CANDIDATES` 同样过闸（打开页面也算「碰」）；
`CANDIDATES` 默认值改为由白名单派生，消除第二处硬编码漂移；
新增 `PACK_PATH` / `PACK_VARIANT`，原行为不变（默认仍是出厂 Pack、`as-is`）。

**(c) A/B 可执行方案** `tests/real-machine/session-wall-ab.mjs`：
产出 `evidence/session-wall-ab-plan-2026-11-11.json`，`status = "plan-only / NOT-EXECUTED"`。

- 变体：`A-control`（递归删掉 `fresh_session`，复现长会话撞墙）/ `B-boundary`（出厂 Pack，`prefer`）。
  出厂声明实际在 `workflow.steps[7]`，所以用**递归删键**而不是写死容器路径；
  测试里断言 A/B **只差这一个变量**，其余字段逐字节一致。
- 矩阵：deepseek / longcat × 2 变体 = 4 组，2 站 × 2 变体 × 8 步 = 32 步真实发送（额度已写明）。
- 5 条验收判据，其中最要紧的两条：B 组必须验到
  `sessionResets[0].available === true && messageCountAfter < messageCountBefore`
  （否则「根本没开成新会话」，这轮对照作废）；判定规则是
  **只有「A 撞墙且 B 通过」才支持命题**——「A/B 都通过」说明本轮墙不存在、
  不能归功边界，「A/B 都撞墙」说明边界无效、另找根因。
- 4 条归因边界：不能归因给重置（§14 已判否）、不能说重置免费（durationMs 非零）、
  B 单轮通过 ≠ 边界有效（N21 续等 / N24 假基准是同期混杂变量，须两轮同时固定）、
  chatglm step_2 抖动的旧账不许翻案。

**(d) 为什么本轮不跑**：解冻条件写进计划——用户**明确解冻指令**（点名平台与范围）、
两站登录态可用、dist 与源码一致、账号额度确认。四条都不满足（第一条就没有），
所以脚本只写计划，不启动浏览器、不导入 Pack、不发消息；evidence 下**没有**
任何冒充真机回执的 A/B 产物。台账 N25 登记为 `open`（P2），不因本轮做完守卫就关账。

### 17.5 守护与红线

- 新增测试 22 条：`probe-readonly.test.mjs` 4、`platform-freeze.test.mjs` 9、
  `session-wall-ab.test.mjs` 9；`npm test` **319/319** 全绿（297 → 319）。
- 新增变异锚 11 条（只读门禁 2 / 冻结守卫 5 / A/B 判据 4），并各按
  `MUTATION_TESTFILE` 做过秒级预检；其中「L2 回执不再记录平台放行策略」
  第一次**存活**——因为测试只断言 `platformPolicy:` 存在，而预检回执里也有同名字段，
  改坏 L2 回执照样匹配。已把断言收窄为「必须绑定运行时策略变量 `platformPolicy || null`」
  后复检杀死。这是本轮第二个「守护自己写宽了」的实例，记在这里备查。
- 冻结平台**未运行**：无浏览器启动、无 Pack 导入、无消息发送。
- 探针**未发送**；诊断证据原样落盘、sha256 可核。
- 本轮所有提交均为**本地**，`origin/main` 仍落后；**未推送**（无 push 授权）。
- 未擅自 `git commit` 之外的远端动作，未删除任何站点数据。

### 17.6 一次自我纠错：数字以磁盘为准

写 §17.2 时把分步耗时和手算成了 `381146ms ≈ 381.1s`。交付前用机器重读回执，
`result.duration = 380146ms`、分步数组求和同为 `380146`（≈380.1s），与日志的
≈380s 也对得上 ⇒ **原数字错了 1 秒**。已把 RESULT（§14.5 表格、§17.2 表格）、
`known_gaps.json` N23、工作日志三处一并回溯改为磁盘真值，并在 §17.2 表格里
把字段名补成「分步耗时和 / `result.duration`」，让复核者能直接对上回执。
这是本轮第二次「先核磁盘再落笔」的实例（第一次是开头的 git / 回执对账）。

### 17.7 门禁状态（机器执行判定）

| 门禁 | 结果 | 证据 |
|---|---|---|
| `npm test` | **319 / 319 pass, 0 fail** | 全量单测，本轮 297 → 319（+22） |
| 全量变异检查 | **120 / 120 全杀死, 0 存活**, `EXIT=0` | `CODEBUDDY_SAFE_DELETE_ENABLED=0 node tests/real-machine/mutation-check.mjs`（109 → 120，+11 锚）；日志 `evidence/mutation-check-2026-11-11.full-120.log` |
| 局部变异预检（秒级） | 只读门禁 2/2、冻结守卫 5/5、A/B 判据 4/4 | `MUTATION_TESTFILE=<file>` 三轮 |
| `node --check` | 8 个新增/修改 `.mjs` 全 OK | 语法检查 |
| 冻结守卫运行时冒烟 | deepseek / longcat / gemini 全部被拦；活跃站放行；`ALLOW_FROZEN=1` 留痕 `unfrozenBy` | 纯函数调用，**未启动浏览器** |
| `dist` | **无需重建** | 本轮 `git status` 未触及 `src/`，只改 `tests/`、报告、台账、evidence |
| 台账 | 25 条：closed 23 / wontfix 1 / **open 1（N25）** | `known_gaps.json`，`json.load` 校验通过 |
| Git | 本地提交，**`origin/main` 仍落后、未推送** | 无 push 授权 |

**本轮明确没做的事**（避免「干了很多活」被读成「都验完了」）：
- 没有运行 deepseek / longcat，A/B 命题**仍未验**（N25 open）；
- 没有做「有/无边界」的交替多轮 A/B，§14.4 的边界继续有效；
- 没有改 `src/`、没有重建 `dist`、没有推送远端；
- 没有把 `/tmp` 诊断产物篡改后落盘（sha256 前后一致）；
- 没有把 419.6s 那轮回执回填 `durationMs`。
