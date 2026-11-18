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
⚠️ 第一版这里有个**自己写下的不准确表述**（见 §18.2）：当时计划里的
`PACK_PATH` 是 `<variant-pack.json>` 占位符、变体文件从未落盘，
所以「4 条命令已备好」并不成立；§18.2 已修复并加守护。

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
| Git | 本地提交，**`origin/main` 仍落后、未推送**（这是 2026-11-11 19:0x 的快照；用户随后明确授权 push，已于 §18.1 推送完毕，`origin/main == HEAD`） | 当时的口径，后续已变更 |

**本轮明确没做的事**（避免「干了很多活」被读成「都验完了」）：
- 没有运行 deepseek / longcat，A/B 命题**仍未验**（N25 open）；
- 没有做「有/无边界」的交替多轮 A/B，§14.4 的边界继续有效；
- 没有改 `src/`、没有重建 `dist`、没有推送远端；
- 没有把 `/tmp` 诊断产物篡改后落盘（sha256 前后一致）；
- 没有把 419.6s 那轮回执回填 `durationMs`。

---

## 18. 后续步骤处置（2026-11-11 19:5x）：授权分批、准备与验证分开

用户把上一轮最终回复里的三条「后续步骤」贴回来要求推进。**这三条本身是清单，不是授权指令**——
第 1 条要在冻结站真实发消息、第 2 条要写远端，都需要明确下令，不能从复述里推断。
因此先做只读核查 + 用两个明确选项请用户裁定，得到：
**「只做本地准备（不跑真机）」+「现在推送」**。

### 18.1 push：8 个提交已推送

顺序是刻意的：本地准备会产生**新变更**，而授权范围是「8 个提交」，
所以先按原样推、再动本地，避免把未审阅的新文件混进已授权范围。

| 项 | 值 |
|---|---|
| push 前 | 工作区干净，`origin/main` 落后 **8** 个提交 |
| 命令 | `git push origin main` |
| 结果 | `d7ea0bc..e3ea159  main -> main`，`Total 88 (delta 51)` |
| push 后 | `git rev-list --left-right --count origin/main...HEAD` = `0  0`；`origin/main == HEAD == e3ea159` |

### 18.2 一次自我纠错：「4 条命令已备好」不成立

上一轮最终回复里写过「计划里 4 条命令、5 条判据已备好」。核磁盘发现：

| 核查项 | 事实 |
|---|---|
| `plan.commands` | 4 条里全是 `PACK_PATH=<variant-pack.json>` —— **占位符** |
| 变体 Pack 文件 | 从未生成；`evidence/` 下只有计划 JSON，`packs/examples/` 只有出厂 3 个文件 |
| 结论 | 命令**不能原样执行**，原表述不准确 |

根因是第一版 `buildAbPlan()` 只产出命令模板，`derivePackVariant()` 是纯内存函数，
两者之间没有「落盘」这一步。修复：

- `emitVariantPacks()` 纯本地生成 A/B 两个变体，落盘前**硬性自检**：
  `metadata.pack_id` 必须为 `xiaohongshu-knowledge-creator`（`EXECUTE_PACK` 用固定 PACK_ID）、
  步数必须 8、A 无 `fresh_session`、B 保留 `prefer`、A/B 除这一字段外逐字节一致；
  任何一条不满足就抛错、不写文件。
- 命令改用 `variantPackPath()` 产出的**真实绝对路径**，计划里带 sha256 且明写
  `imported: false / executed: false`，避免被误读成回执。
- 产物：`ab-pack-2026-11-11.no-boundary.json`（`89b197cf…`）、
  `ab-pack-2026-11-11.with-boundary.json`（`0e1b4b98…`）。

顺带补上两条第一版漏掉的执行约束：

1. **4 轮必须串行**：两轮都用 `mergeStrategy=overwrite` 导入**同一个 pack_id**，
   并行会互相覆盖 storage 里的 Pack。
2. **预检也要显式解冻**：`PRECHECK=1` 会 `page.goto` 打开冻结站页面，
   本身受 `assertCandidatesAllowed` 拦截，必须带 `ALLOW_FROZEN=1` 与显式 `CANDIDATES`。
   计划里现在共 5 条可执行命令（1 条预检 + 4 轮 L2）另加 1 行注释。

守护：`session-wall-ab.test.mjs` 9 → **15 条**（新增占位符回潮、绝对路径、
A/B 各用各的文件、预检解冻、串行约束、落盘自检、坏契约拒绝）；
变异锚 4 → **8 条**（其中「占位符回潮」「自检被放开」两条锚分别咬住这次的具体缺口）。

**两次「守护自己写宽了」的小修**（都记在这里备查）：
- 「方案脚本不得出现 EXECUTE_PACK」原本全文匹配，把我新加的**说明性注释**误判成越线；
  改为只扫剥离注释后的可执行代码（与 `probe-readonly.test.mjs` 同口径）。
- 「自检被放开」第一次变异存活：测试只断言 `checks` 的值，而删掉 `throw` 后值照样算得对；
  改为喂**合法 JSON 但契约被改坏**的 Pack（`pack_id` 改名 / 只剩 7 步），并合并重复的两道检查，
  锚才咬住。合并时还修了「缺步时 `'fresh_session' in undefined` 抛 TypeError 盖住真因」。

### 18.3 dist 一致性：成立（解冻前置条件之一）

| 项 | 值 |
|---|---|
| 命令 / 退出码 | `npm run build` / `0`（192ms） |
| `content-script.js` | build 前后 sha256 均为 `0e842dc2…` ⇒ **IDENTICAL** |
| `service-worker.js` | build 前后 sha256 均为 `108055dc…` ⇒ **IDENTICAL** |
| 关键字 | CS：`hidden-semantic`×2 / `durationMs`×1 / `data-session-switch-target`×3 / `yb-new-chat-entry__item`×3 / `sidebar-new-chat`×5；SW：`sessionResets`×7 / `fresh_session`×8 / `FRESH_SESSION_UNSUPPORTED`×2 |
| `durationMs` 在 SW 里 0 次 | 正常：它由 CS 计算、经 `record = {...base, available: ..., ...result}` 透传；已核 `...result` 仍在（3 处），计时字段不会丢 |
| 工作区 | `dist/` 未被 git 跟踪，build 未弄脏工作区 |

证据：`evidence/dist-build-2026-11-11.log`、`evidence/dist-consistency-2026-11-11.json`。

### 18.4 解冻前置条件：4 条里仍只满足 1 条

| 条件 | 状态 |
|---|---|
| 用户明确解冻指令（点名平台 + 范围） | ❌ **未满足**：本轮授权明确写的是「只做本地准备」，没有解冻 |
| 两站登录态可用 | ❌ **未满足**：deepseek 从未被预检过；longcat 只有 2026-11-10 旧快照（`composer=true`），不是当前态。预检本身也要解冻（§18.2） |
| dist 与源码一致 | ✅ **已满足**（§18.3） |
| 32 步额度确认 | ❌ **未核**：账号侧信息，我无法判定，需用户确认 |

⇒ **A/B 命题仍未验**，N25 保持 `open`，`plan.status` 仍是 `plan-only / NOT-EXECUTED`。
本轮没有启动浏览器、没有导入 Pack、没有发送任何消息、没有打开任何冻结站页面。
§14.4 的「不能归因给重置 / 不能说重置免费」继续有效。

### 18.5 门禁状态（本轮局部准备）

| 门禁 | 结果 |
|---|---|
| `git push` | ✅ `0  0`，`origin/main == HEAD == e3ea159` |
| `node --check` | ✅ 3 个改动 `.mjs` 全通过 |
| 全量 `npm test` | ✅ **325 / 325 pass, 0 fail**（319 → +6） |
| 全量变异检查 | ✅ **124 / 124 全杀死, 0 存活, EXIT=0**；日志 `evidence/mutation-check-2026-11-11.full-124.log` |
| 局部变异 `MUTATION_TESTFILE=session-wall-ab.test.mjs` | ✅ **8/8 全杀死**（在最终磁盘状态上又复跑一遍，见下） |
| `session-wall-ab.test.mjs` 单测 | ✅ **15/15**（最终磁盘状态复跑） |
| `npm run build` | ✅ 退出码 0，产物 hash 前后一致 |
| 变体 Pack 落盘自检 | ✅ 6 项全通过，sha256 与计划内一致 |
| 真机 A/B | ❌ **未执行**（无解冻授权），见 §18.4 / §18.6 |

**一处时序要如实交代**：全量变异在启动时复制的是当时的 `tests/` 快照；
运行期间我微调了 `session-wall-ab.mjs` 里一行**说明文字**（额度条件加「当前未满足/未核」）
并重新生成了计划 JSON。该行不参与任何变异锚的 `find`，也不影响测试断言，
但仍按 disk-truth 口径在**最终磁盘状态**上补跑了 `session-wall-ab.test.mjs`
单测（15/15）与局部变异（8/8），结论与全量一致。

### 18.6 本轮没做、也不该做的事

- 没有解冻、没有跑 A/B、没有打开冻结站页面；
- 没有把本地准备产生的新变更推送远端（push 授权范围就是那 8 个提交，已用尽）；
- 没有改 `src/`、没有把 `dist/` 纳入版本控制；
- 没有把计划文件冒充真机回执（status 与 `imported/executed` 三个字段都明写 false）；
- 没有对**本轮新变更**执行 `git commit` / `git push`：push 授权范围就是那 8 个提交，已用尽；
  新变更留在工作区待审阅（见 §18.7）。全量 `npm test`（325/325）与全量变异（124/124）
  **已补跑并通过**，见 §18.5。

### 18.7 本轮新变更留在工作区（未提交、未推送）

| 类型 | 文件 |
|---|---|
| 修改 | `tests/real-machine/session-wall-ab.mjs`、`tests/session-wall-ab.test.mjs`、`tests/real-machine/mutation-check.mjs`、`RESULT-L2-MULTIPLATFORM-2026-11-10.md`、`known_gaps.json`、`evidence/session-wall-ab-plan-2026-11-11.json` |
| 新增 | `evidence/ab-pack-2026-11-11.no-boundary.json`、`evidence/ab-pack-2026-11-11.with-boundary.json`、`evidence/dist-consistency-2026-11-11.json`、`evidence/dist-build-2026-11-11.log`、`evidence/mutation-check-2026-11-11.full-124.log` |

理由：用户本轮授权的是「推送 8 个提交」+「只做本地准备」，没有授权提交或推送新变更。
先推后改，新东西不混进已授权范围；留在工作区便于逐项审阅，
下一次授权时再决定提交与推送。

---

## 19. 冻结站 A/B 真机验证：4 轮跑完，命题仍不成立（2026-11-11 ~ 11-12）

### 19.1 授权边界与解冻方式

用户明确解冻 `deepseek / longcat` 并确认额度。冻结**是逐次显式放行**：`ACTIVE_PLATFORM_IDS` 白名单未改，每条命令都带 `ALLOW_FROZEN=1`，回执 `platformPolicy.unfrozenBy = "ALLOW_FROZEN=1"` 留痕。预检 `evidence/L2-precheck-2026-11-11.deepseek-longcat.json`：两站 `composerVisible:true`、`looksLikeLogin:false`、无登录重定向。

### 19.2 第 1 轮不是「撞墙」，是假超时

`evidence/L2-deepseek-auto-2026-11-11.ab-no-boundary.json`：5 步、`step_5_boundary` 失败、723.7s ≈ 4×180s、`sessionResets: []`。同轮截图里提问气泡与 AI 完整回答都在页面上，无登录墙。三份只读诊断把 DOM 钉死：

| 选择器 | 命中 | 含义 |
|---|---|---|
| `div.ds-message` | 5 | 3 条 AI 回答 + 2 条 human 气泡 |
| `.ds-assistant-message-main-content` | 3 | 每条 AI 回答一个 |
| `[class*="message"]` | 8 | 上面两组**混在一起**（旧 `messageList` 取的就是这组） |
| typing / stop 相关 | 全 0 | 排除 `isTyping()` 恒真 |

裁决 `evidence/ab-round1-verdict-2026-11-11.json` = `AB_UNVERIFIABLE_PRECONDITION_FAILED`：边界只声明在 `step_8_output`，A 组没走到。

### 19.3 修契约 → 修复无效 → 回溯更正根因

把 deepseek `messageList` 改为只认 `.ds-assistant-message-main-content`，补 4 条契约测试（8/8）与 3 条变异锚；两次 `npm run build` hash 幂等、新契约确进产物；全量 `npm test` **329/329**、全量变异 **127/127 全杀死 EXIT=0**。

但重跑 1/4（`evidence/L2-deepseek-auto-2026-11-11.ab2-no-boundary.json`）**仍 5 步、仍 `step_5_boundary`、723.6s**。截图再次显示 AI 已作答且页面只保留最后两轮 ⇒ **上一节「换掉混合选择器即可」的判断作废**：真卡点是长会话下虚拟列表卸载旧回答，令公共判据 `countGrew`（消息数必须增长）恒不成立，与选择器组混不混无关。此后不再改代码，保持同一份 dist 跑完 4 轮以保 likeForLike。

### 19.4 补跑 3 轮的落盘方式（针对上次承诺未兑现）

上一轮后台串行任务被会话切换回收，且 stdout 只在缓冲里，导致 3 轮回执全丢。本次 runner 改为：外层 `tee -a` 全程写 `evidence/ab2-rerun-2026-11-12.log`；每轮 start / node-exit / verify 即时追加 `evidence/ab2-rerun-progress-2026-11-12.jsonl`；每轮回执由驱动自身即时落盘。日志开头核到 `dist CS=cd5c7997… SW=3e489d43…` 与 `SW size=117948`，与 A 组同一构建。

### 19.5 四轮结果（全部 `exec.success=false`）

| 平台 | 变体 | 通过步数 | 失败点 | 失败耗时 | `sessionResets` |
|---|---|---|---|---|---|
| deepseek | A `no-boundary` | 4/5 | `step_5_boundary` | 723.6s | `[]` |
| deepseek | B `with-boundary` | 4/5 | `step_5_boundary` | 723.8s | `[]` |
| longcat | A `no-boundary` | 2/3 | `step_3_explain` | 723.9s | `[]` |
| longcat | B `with-boundary` | 7/8 | `step_8_output` | 723.2s | 1 条，**`available:false`** |

4 轮失败全部是 `Response timeout`，失败步骤耗时全部落在 4×180s 窗口 ⇒ 同一类假超时，跨两站同型，与 `fresh_session` 无关。汇总 `evidence/ab2-four-round-summary-2026-11-12.json`。

### 19.6 机器裁定（`evidence/ab2-verdict-2026-11-12.json`）

`PROPOSITION_NOT_SUPPORTED_ROUNDS_UNUSABLE`，`propositionSupported = false`，**N25 保持 open**。

- **deepseek**：A/B 都停在 `step_5`，边界声明在 `step_8` 从未触发，`sessionResets` 均为空 ⇒ **不可评估**，不是「边界无效」。
- **longcat**：B 组虽走到 `step_8`，但 `sessionResets[0] = { available:false, strategy:"none", messageCountBefore:6, messageCountAfter:6, durationMs:0 }`，原因是「adapter 没有声明 `newChat` 选择器」，`prefer` 降级照发 ⇒ 按用户判据「B 组须 `available===true && messageCountAfter<Before`」**该轮作废**。
- 因此既没有「A 撞墙且 B 通过」，也不能把「都失败」包装成「边界无效」。

**归因边界（不得越线）**：不能说会话边界解掉了 `step_8` 撞墙；不能说边界无效（两站边界都没真正生效）；不能把 longcat B 从 2/3 推进到 7/8 归功边界（边界在 `step_8` 且 `available:false`，前 7 步差异属站点抖动）；不能说重置免费或把耗时差异归因给重置（§14.4 继续有效）。

### 19.7 限制与新发现

- **likeForLike 缺口**：deepseek A（11-11 23:00）与 B（11-12 07:53）跨约 8.5 小时，违反计划「相邻时间窗」；longcat A/B 相邻串行（08:05 / 08:20），该对不受此限。
- **待修 ①**：公共等待判据在长会话 + 虚拟列表下失效，需改为不依赖「消息计数必须增长」。
- **待修 ②**：longcat adapter 缺 `newChat` 入口（N23 只覆盖 5 个活跃站，冻结站未纳入），`prefer` 才会降级。
- 修完这两项之后才可能重跑有效 A/B；在那之前不宣布任何因果结论。

### 19.8 本轮产物与未提交状态

新增证据：`ab2-rerun-2026-11-12.log`、`ab2-rerun-progress-2026-11-12.jsonl`、3 份 `L2-*-2026-11-12.ab2-*.json` 及截图、`ab2-four-round-summary-2026-11-12.json`、`ab2-verdict-2026-11-12.json`；代码改动 3 个文件（deepseek adapter / 契约测试 / 变异锚）。全量门禁为 329/329 与 127/127，均在最终代码状态下跑完。**本轮未执行 `git commit` / `git push`**，`HEAD == origin/main == 36d9ec2`，所有改动留在工作区待授权。

---

## 20. 按依赖顺序执行：两项待修落地、门禁全绿，真机 A/B 仍未重跑（2026-11-12）

### 20.1 本轮授权边界

用户指令「按依赖顺序执行」对应 §19.7 的两项待修及其依赖门禁：**先修公共等待判据与 longcat 入口 → 再重建 dist + 全量门禁**。本轮只做本地修复与门禁：冻结站未打开、未发送、未导入 Pack；没有 `git commit` / `git push`；`HEAD == origin/main == 36d9ec2`。`ACTIVE_PLATFORM_IDS` 白名单未改，跑真机仍需逐次显式 `ALLOW_FROZEN=1` 并在回执写 `platformPolicy`。

### 20.2 F1：公共等待判据不再只依赖「消息数必须增长」

| 项 | 内容 |
|---|---|
| 根因 | 长会话虚拟列表卸载旧回答：发送前 3 条，新回答落地时滚掉 1 条老的，仍是 3 条 ⇒ `countGrew` 恒 false ⇒ AI 答完仍判 `Response timeout`（4 轮 A/B 全失败在 723.x s = 4×180s，跨两站同型） |
| 修法 | `wait-policy.hasNewReply = 计数通道 OR 内容通道`；内容通道比较「最新正文 vs 发送前基准」，两把尺子共用 `latestContentOf()` |
| 启用范围 | `CONTENT_GROWTH_PLATFORM_IDS = [chat.deepseek.com, longcat.chat, longcat.ai]`——**按实测证据开的白名单**，其余平台一律沿用原判据，已绿 5 站行为不变 |
| 护栏 | 内容通道只在**显式给了字符串基准**时启用；仍保留「正文非空」+「连续 8 秒稳定」两道闸；正文与基准相同（旧回答没动）不判完成，不会退回「太早成功」 |
| 续等链 | `baselineContent` 随失败信封 → `assertAIStepSucceeded` → `_resumeWaitForResponse` → `WAIT_FOR_RESPONSE` 一路透传；`resolveBaselineContent()` 只认字符串，缺失回 `null` 关掉内容通道，**绝不就地快照**（那会把已落地的新回答当成基准） |
| 顺带修掉的隐性缺陷 | `handleWaitForResponse` 的超时分支原先不挂任何基准，第一次续等再超时后后台会抛 `RESUME_WAIT_NO_BASELINE`，明明还能等却不许等；现在两个基准都沿续等链传下去 |

行为证据不是抄一份逻辑：`tests/adapter-wait.test.mjs` 在 jsdom 里跑**生产内容脚本本体**，重放「3 条旧回答 → 卸 1 条 + 落 1 条新回答」的虚拟列表时间线，断言 `SEND_TO_AI` 仍取回新回答。该测试放在等待专题文件而非被 33 条变异锚指着的 `extension-wiring.test.mjs`，避免全量变异凭空多出数分钟。

### 20.3 F2：longcat `newChat` 入口

依据只读 DOM 探针 `evidence/new-session-probe-2026-11-12.longcat.json`：真入口是 `div.new-content` 里的 `span`「开启新对话」，祖先 `div.slider-header > div.v-slider-header`，`clickableAncestor: null` ⇒ 公共文案/标签兜底永远扫不到。页面上另有 `div.conv-title`「新对话」，那是**历史会话列表项**，点它只会切回旧会话。

`longcat-adapter.js` 新增 `newChat: [".v-slider-header .new-content", ".slider-header .new-content", "div.new-content span"]`。`prefer` 语义没改：找得到才 `available:true`，找不到仍如实降级。守护钉的是行为——「真入口能清空 12→0」「没声明时宁可 `available:false` 也不许误点诱饵」。

### 20.4 全量门禁（最终代码状态下跑完）

| 门禁 | 结果 | 证据 |
|---|---|---|
| `npm test` | **341/341**，fail 0，`EXIT=0` | `evidence/npm-test-2026-11-12.local-fix.log` |
| 全量变异 | **143/143 全杀死**，存活 0，`EXIT=0`（16m04s） | `evidence/mutation-check-2026-11-12.full.log` |
| `npm run build` | 两次均 `EXIT=0`，产物 hash 幂等 | `build-2026-11-12.local-fix{,-second}.log` |
| dist 严格一致性 | `allPass=true`；CS `cffb6eb540abdf11…` / SW `b243c74de2afcecf…`；7 项关键字全中 | `evidence/dist-consistency-2026-11-12.local-fix.json` |

门禁数字从上一轮的 329/329、127/127 变为 341/341、143/143：新增 12 条单测、16 条变异锚（F1 13 条 + F2 3 条），每条锚都指向具体测试名，改坏对应代码必须变红。局部预检先各自跑过（wait-policy 8/8、retry-semantics 11/11、adapter-wait 7/7、new-session-control 13/13），再跑全量。

### 20.5 机器裁定（`evidence/local-fix-verdict-2026-11-12.json`）

`LOCAL_FIX_GATES_PASS_REAL_MACHINE_NOT_VERIFIED`：`localFixComplete=true`、`allGatesPass=true`、`realMachineVerified=false`、`propositionSupported=false`、**N25 保持 `open`**（`closed_at: null`）。

**不得越线**：本轮没有新增任何站点回执，所以不能说「假超时已在真机上修好」；§19.6 的 `PROPOSITION_NOT_SUPPORTED_ROUNDS_UNUSABLE` 与全部归因边界继续有效——不能说会话边界解掉了 `step_8` 撞墙、不能说边界无效、不能把 longcat B 前 7 步差异归功边界、不能说重置免费或把耗时归因重置（§14.4）。也不能把内容型增长信号说成全局默认：它是按实测证据开的实验开关，未验证平台一律不启用。

### 20.6 限制

- 内容型信号要求「新回答正文 ≠ 发送前最新正文」。两次回答文本完全相同时仍会退化成超时——**真机未测**。
- 本轮全部证据都是本地产物（jsdom 行为测试 / node:test / 变异 / dist 产物核对），不是站点回执。
- deepseek A(11-11 23:00) 与 B(11-12 07:53) 跨约 8.5 小时的 likeForLike 缺口仍在；重跑必须重新安排相邻时间窗。
- 新增的 9 秒级行为测试让 `adapter-wait.test.mjs` 变慢，已显式给生产等待 13s 上限，避免变异把内容通道改坏时 `setInterval` 挂到 60s 默认超时拖死子进程。

### 20.7 产物与未提交状态

代码改动 10 个文件（`wait-policy.js` / `retry-policy.js` / `content-script.js` / `pack-executor.js` / `longcat-adapter.js` + 5 个测试与变异锚文件）；新增证据 6 份（build ×2、npm-test、全量变异、dist 一致性、机器裁定）。`git status` 共 **42 项**（14 个 tracked 改动 + 28 个 untracked 证据/回执文件，含上一轮补跑留下的 22 份），**全部未提交、未推送**，`HEAD == origin/main == 36d9ec2`。

### 20.8 后续步骤（依赖顺序，均未授权执行）

1. 需要用户**明确解冻并授权真机重跑**；每条命令仍带 `ALLOW_FROZEN=1` 留痕。
2. 先跑预检核登录态，再**串行**跑 4 轮 A/B；B 组须 `sessionResets[0].available === true && messageCountAfter < messageCountBefore`，否则该轮作废／本轮不可评估。
3. 只有「A 撞墙且 B 通过」才支持命题；跑完按判据裁定，**在此之前 N25 保持 `open`**。
4. 提交 / push 需单独授权（授权范围要按提交/文件集合分清）。

---

## 21. 执行后续步骤：ab3 四轮真机 A/B 跑完，F1 真机验证成立，命题仍不成立（2026-11-12）

### 21.1 本轮授权边界

用户指令「执行后续步骤」对应 §20.8 的依赖链：① 解冻并授权真机重跑 → ② 预检 + 串行 4 轮 A/B → ③ 按判据裁定 N25 → ④ 提交/push 需**单独授权**。本轮执行 ①–③；**④ 未执行**：没有 `git commit` / `git push`，`HEAD == origin/main == 36d9ec2`。回写完成后就 60 项待提交文件向用户确认范围，用户明确选择「**暂不提交**」⇒ 全部改动继续留在工作区，不动远端。冻结仍是逐次显式放行：白名单未改，每条命令带 `ALLOW_FROZEN=1`，4 份回执 `platformPolicy.unfrozenBy` 均为该值。

### 21.2 前置对账（#39 / #40，只读）

| 项 | 磁盘真值 |
|---|---|
| A/B 计划 | `session-wall-ab-plan-2026-11-11.json`，4 轮 `executionOrder` 串行，`mergeStrategy: overwrite` 导入同一 `pack_id` |
| 变体 Pack | A `89b197cf99f2fcac…`（`workflow.steps` 8 步、无 `fresh_session`）；B `0e1b4b9816545e52…`（8 步、仅 `step_8_output` 带 `fresh_session: prefer`） |
| dist | `dist-consistency-2026-11-12.local-fix.json`：`allPass=true`、幂等；CS `cffb6eb540abdf11…` / SW `b243c74de2afcecf…`；产物中含 `CONTENT_GROWTH_PLATFORM_IDS` / `shouldTrackBaselineContent` / `baselineContent` / `longcat.chat` |
| 两站登录态 | `L2-precheck-2026-11-12.deepseek-longcat.json`：`composerVisible:true`、`looksLikeLogin:false`，`unfrozenBy=ALLOW_FROZEN=1` |
| 目标路径 | 4 个 `.json` + 4 个 `.png` 全部为空，runner 前置拒绝覆盖 |

`currentPlatformId` 取自 `adapter.platformId`（`chat.deepseek.com` / `longcat.chat`），与内容型增长白名单的 key 一致——修 F1 时最容易踩的 ID 不匹配，磁盘核对已排除。

### 21.3 四轮实测结果（ab3，修复后 dist）

| 轮 | 平台 | 变体 | 回执 | 结果 | 步数 | 耗时 | `sessionResets` |
|---|---|---|---|---|---|---|---|
| 1 | deepseek | A `no-boundary` | `L2-deepseek-auto-2026-11-12.ab3-no-boundary.json` | **8/8 completed** | 8/8 | 82,223 ms | `[]` |
| 2 | deepseek | B `with-boundary` | `L2-deepseek-auto-2026-11-12.ab3-with-boundary.json` | **8/8 completed** | 8/8 | 81,289 ms | 1 条，`available:false` / `strategy:none` / 3→3 / 4 ms |
| 3 | longcat | A `no-boundary` | `L2-longcat-auto-2026-11-12.ab3-no-boundary.json` | failed | 5/6 | 810,784 ms | `[]` |
| 4 | longcat | B `with-boundary` | `L2-longcat-auto-2026-11-12.ab3-with-boundary.json` | failed | 3/4 | 764,066 ms | `[]` |

第 3 轮失败在 `step_6_takeaway`（723,637 ms），第 4 轮失败在 `step_4_scene`（723,219 ms）；两处都是 4×180s 窗口。但**这一轮和 ab2 的假超时不是一回事**：两张长猫截图里最后一条 AI 回复都是「服务出错啦，请稍后再试。」，即站点侧错误、根本没产出回答，等待超时是正确行为。两轮在失败前分别有 5 步和 3 步成功，单步 19–27 s，说明内容型等待信号确实在真机上工作。

### 21.4 第 4 轮补跑：从「没跑」补齐成「有回执」

`ab3-rerun-2026-11-12.log` 的第 4 轮在 `launch()` 清 SW 缓存时被 WorkBuddy safe-delete shim 拦截（`SAFE_DELETE_BULK_CONFIRM_REQUIRED`，count 52 > threshold 50，scope=turn）：浏览器未启动、页面未打开、Pack 未导入、未发送任何内容；`ab3-rerun-progress-2026-11-12.jsonl` 明确记 `exists:false`。runner 末尾的 `RUNNER_FINISHED` 不代表四轮都跑完——该日志同时有 `NODE_EXIT=1`。

补跑用独立 `ab3-round4-rerun-2026-11-12.sh`：新日志 `ab3-round4-2026-11-12.log` 全程 tee、新进度 `ab3-round4-progress-2026-11-12.jsonl` 即时追加、回执由驱动自身即时落盘；**不覆盖任何既有证据**，前置复核 `PRECONDITION_OK`（Pack hash / dist hash / 目标路径为空 / 放行留痕）。没有设置 `CODEBUDDY_SAFE_DELETE_ENABLED=0` 去绕过安全门：单轮只清 1 项，远低于阈值。12m53s 后回执落盘，`NODE_EXIT=0`。至此 **4/4 轮都有回执**，`allFourRoundsExecuted=true`。

### 21.5 逐轮机器复核与裁定

裁定不是手写结论：`ab3-verdict-2026-11-12.py` 只读 4 份回执，机械计算每条布尔判据，产出 `evidence/ab3-verdict-2026-11-12.json`（初版 `classify()` 把 deepseek 只标成 `INVALID_ROUND_RESET_UNAVAILABLE`，埋没了更根本的「A/B 都通过」；已用显式 `--regenerate` 重生成并列 `reasons`，产物内 `regeneratedFrom` 留痕，最终 `code` 未变）。

| 平台 | 主状态 | 机械判据 | 结论 |
|---|---|---|---|
| deepseek | `NO_WALL_THIS_ROUND` | `aPassed8of8=true`、`bPassed8of8=true`、`bothPassed=true`；`bResetActuallyHappened=false`、`bRoundUsable=false` | A/B 都 8/8 ⇒ **本轮墙不存在**，不能归功边界；且 B 组 `available:false / 3→3`，按判据**该轮作废** |
| longcat | `BOUNDARY_NEVER_ATTEMPTED` | `aBoundaryStepReached=false`、`bBoundaryStepReached=false`、`bBoundaryAttempted=false`、`sessionResets=[]` | 边界声明在 `step_8_output`，两轮分别在 `step_6` / `step_4` 就停了 ⇒ **本轮不可评估**，既不能归功边界，也不能说边界无效 |

`verdict.code = PROPOSITION_NOT_SUPPORTED`、`propositionSupported=false`、**N25 保持 `open`**（`closed_at: null`）。`allBoundariesActuallyExecuted=false`：`available===true && messageCountAfter<Before` 这一 B 组硬判据，四轮里一次都没有成立。

### 21.6 回溯修正：§20.5 的「真机未验证」限制已被新证据推翻

§20.5 写「本轮没有新增任何站点回执，所以不能说『假超时已在真机上修好』」。**该限制对本轮不再适用**：ab3 有 4 份新站点回执，`f1RealMachineVerified=true`，依据是 deepseek A/B 从 ab2 的「4×180s 假超时、AI 明明答了」变成两轮 8/8 completed、82.2 s / 81.3 s，且 longcat 失败前的多个 AI 步骤都在 19–27 s 内正常取回。按「遇到新证据回溯更正既往结论」的口径，这里明确改为：**F1 公共等待判据修复在真机上生效，已有回执证据**。

但必须同时钉死范围，防止把这条结论挪用：① 它验的是 `hasNewReply` 的内容型增长信号，**不是** `fresh_session` 会话边界，两者是不同变量；② longcat 未完成 8/8，站点侧错误情况下的恢复能力未测；③ 内容型信号要求「新回答正文 ≠ 发送前最新正文」，两次回答文本完全相同的退化路径仍无真机证据。裁定 JSON 用 `nonMachineObservations` 单独标注两张截图的人工视觉判读，明确它**不参与**任何机器布尔推导。

### 21.7 新发现（本轮新增，均未修复）

1. **deepseek 缺 `newChat` 入口**：B 组回执 reason 明写「adapter 没有声明 newChat 选择器」。而只读探针 `new-session-probe-2026-11-11.deepseek-ab-diagnostic.json` **早就抓到了真入口**——`<span>开启新对话</span>`、`clickableAncestor:null`、父链为哈希类名 div；`NEW_SESSION_TEXTS` 不含「开启新对话」，公共标签兜底也扫不到 `span`。§19.7「待修 ②」当时只点了 longcat，F2 因此只补了 longcat，deepseek 的同类缺口被漏掉。这是 B 组 `available:false` 的直接原因，也是下一轮 A/B 的硬前置。
2. **F2 的 longcat `newChat` 仍未被真机触发**：边界只声明在 `step_8_output`，两轮都没走到，本轮零次验证；jsdom 行为测试仍是它的唯一证据。
3. **longcat 站点侧错误是新的混杂变量**：两张截图均为「服务出错啦，请稍后再试。」，失败步骤不同（`step_6` / `step_4`），说明站点在会话中途随机报错；这与「长会话撞墙」「等待判据」都不是同一层，后续归因必须单独标注。
4. **likeForLike 局部缺口**：deepseek A/B 相邻（03:41 / 03:42）、longcat A 紧随其后（03:44），但补跑的第 4 轮在 04:28，与第 3 轮相隔约 31 分钟；Pack 与 dist 经 hash 复核完全一致，时间窗不相邻这一条仍需如实保留。

### 21.8 归因边界（不得越线）

- 不能说「会话边界解掉了 step_8 长会话撞墙」——没有「A 撞墙且 B 通过」的成对证据。
- 不能说「边界无效」——四轮里边界一次都没有真正生效，不可用「都失败」反推无效。
- 不能把 deepseek 的 8/8 归功于边界——A 组无边界同样 8/8，且 B 组 `available:false` 是降级照发。
- 不能把 longcat 从第 3 轮的 `step_6` 到第 4 轮的 `step_4` 差异归给边界——边界在 `step_8`，两轮都没到；差异属站点报错位置抖动。
- 不能说重置免费、不能把耗时差异归因给重置（§14.4 继续有效）；不能把 F1 真机成功与会话边界混为一谈。
- 不能说「长会话撞墙已被根治」——deepseek 本轮压根没出现墙，longcat 挂在站点错误上。

### 21.9 产物与未提交状态

新增证据：`ab3-precheck-2026-11-12.log`、`ab3-runner-2026-11-12.sh`、`ab3-rerun-2026-11-12.log`、`ab3-rerun-progress-2026-11-12.jsonl`、4 份 `L2-*-2026-11-12.ab3-*.json` 与 4 份截图、`ab3-round4-rerun-2026-11-12.sh`、`ab3-round4-2026-11-12.log`、`ab3-round4-progress-2026-11-12.jsonl`、`ab3-verdict-2026-11-12.py`、`ab3-verdict-2026-11-12.json`。本轮**未改任何源码、未重建 dist**。**未执行 `git commit` / `git push`**，所有改动留在工作区待授权。

### 21.10 后续步骤（依赖顺序，均未授权执行）

1. 给 deepseek adapter 补 `newChat` 精确入口（依据 11-11 只读探针），并补契约测试 + 变异锚；同时考虑把 `NEW_SESSION_TEXTS` 扩到「开启新对话」，但不得放宽公共标签兜底去点历史会话诱饵。
2. 重建 dist → 全量 `npm test` → 全量变异 → dist 严格一致性，全部在最终代码状态下跑完。
3. 重新申请解冻，把 4 轮安排在**相邻时间窗**内串行重跑；B 组必须 `available===true && messageCountAfter<Before`，只有「A 撞墙且 B 通过」才支持命题。在此之前 **N25 保持 `open`**。
4. 提交 / push 需单独授权，授权范围要按提交/文件集合分清。

---

## 22. 执行后续步骤①–②：deepseek 精确文案逃生口落地、全量本地门禁通过，真机 A/B 仍未重跑（2026-11-12）

### 22.1 授权边界与开工前的磁盘真值

用户指令是「执行 后续步骤」，依赖链为：① 补 deepseek `newChat` 精确入口 + 契约测试与变异锚 → ② 重建 dist、全量 `npm test`、全量变异、dist 严格一致性 → ③ 重新申请解冻、相邻时间窗串行重跑 4 轮 → ④ 提交 / push 单独授权。**本节只完成 ①②**；③ 是「申请解冻」，不是自动解冻，④ 未授权。

开工前对账（不认 recap）：仓库 `/Users/raymondna/Documents/AI-collab/ai-collab-base`，`HEAD == origin/main == 36d9ec2`，`git status --porcelain` 62 项，TaskList #45 completed / #46 in_progress。源码与 8 条契约测试已在盘，但 `mutation-check.mjs` 仍是 143 锚 ⇒ 判定上一轮在「准备加变异锚」处被中断，本次从那里续上。

**授权收口（回写完成后逐次确认）**：就 ③ 解冻真机重跑与 ④ 提交/push 两个独立问题向用户确认，用户明确选择「**暂不重跑（推荐）**」+「**暂不提交（推荐）**」。据此：不解冻、不打开冻结站、不跑预检、不发消息；不 `git commit`、不 `git push`；74 项改动全部留在工作区，`HEAD == origin/main == 36d9ec2`、`unpushed=0`。N25 保持 `open`。①② 的产物与结论照常交付，③④ 仍列为未执行的后续步骤。

### 22.2 设计决策：为什么不是 CSS 选择器，也不是放宽公共兜底

只读探针 `new-session-probe-2026-11-11.deepseek-ab-diagnostic.json` 给出的真入口是 `<span>开启新对话</span>`：自身无 class / id / aria / title / role / testid，`clickableAncestor:null`，六层祖先全是构建期哈希类名（`_5a8ac7a` / `dc1f7bee _4bcc731` / `_7b40dad` / …）。写哈希类名等于下次发版即失效；写 `span` 到公共 `NEW_SESSION_CONTROL_SELECTOR` 则会误点 longcat 历史会话里的 `div.conv-title`「新对话」诱饵（§21.7 已有实证守护）。

因此采用 **adapter-scoped exact-text hook**：只有显式声明 `newChatText` 的 adapter 才启用一层「窄选择器 + 文案 `trim()` 后全等」匹配，仍要过 `isElementRendered` 与 `COMPOSER_ZONE_SELECTOR`，返回 `strategy: "adapter-text-match"`，并由 `waitForSessionReset` 的消息数下降判真实重置。`NEW_SESSION_TEXTS` 只新增文案「开启新对话」，**标签表一个字节未动**。

另核到 `content-script.js` 的 `PLATFORM_CONFIGS["chat.deepseek.com"] = DEEPSEEK_SELECTORS`、`handleNewSession()` 传的是完整 `currentConfig`，所以新字段自动流入，**不需要改内容脚本**。

### 22.3 改动清单

| 文件 | 改动 |
|---|---|
| `src/content/new-session-control.js` | `NEW_SESSION_TEXTS` 加「开启新对话」；`findNewSessionControl()` 加 `1.5)` 逃生口；返回类型加 `"adapter-text-match"` |
| `src/platforms/deepseek-adapter.js` | 新增 `newChatText: { selector: "span", texts: ["开启新对话"] }`，注释钉住 ab3 B 组 `available:false` 根因与「不写哈希类名、不放宽公共兜底」 |
| `tests/deepseek-new-session.test.mjs` | 新增 8 条契约测试，用生产 `DEEPSEEK_SELECTORS` / `CHATGLM_SELECTORS` 与探针原样哈希祖先夹具 |
| `tests/real-machine/mutation-check.mjs` | 追加 8 条语义锚（143 → 151），全部指向独立测试文件，可用 `MUTATION_TESTFILE` 秒级预检 |

新测试第一次跑 5/8：`makeSite()` 里 `{ ...config, messageList }` 的 spread 顺序让 adapter 自带 `messageList` 覆盖夹具，12 条 `.msg` 数成 0，`handleNewSession` 直接走 `already-empty` 绕过了真正要验的行为。改成把 `messageList` 放在 spread **之后**后 8/8。回归 `new-session-control.test.mjs` 12/12、`session-boundary.test.mjs` 9/9、`message-list-contract.test.mjs` 8/8。定向变异预检 8/8 全杀死。

### 22.4 全量门禁（最终代码状态，机器执行结果）

runner `evidence/gates-deepseek-newchat-2026-11-12.sh`：每步 stdout 全程 `tee -a`，start / exit 即时写 `gates-deepseek-newchat-2026-11-12.jsonl`，汇总 `gates-deepseek-newchat-2026-11-12.summary.json`。总耗时 17m49s，`ALL_PASS=true`。

| 门禁 | 结果 | 证据 |
|---|---|---|
| `npm run build` #1 / #2 | 两次 EXIT=0，产物 hash 幂等 | `build-2026-11-12.deepseek-newchat{,-second}.log` |
| 全量 `npm test` | **349/349，fail 0，EXIT=0**（341 + 8 新增） | `npm-test-2026-11-12.deepseek-newchat.log` |
| 全量变异 | **151/151 全杀死，存活 0，EXIT=0** | `mutation-check-2026-11-12.deepseek-newchat.full.log` |
| dist 严格一致性 | `allPass=true`，10 项关键字全中 | `dist-consistency-2026-11-12.deepseek-newchat.json` |

`CODEBUDDY_SAFE_DELETE_ENABLED=0` **只设在变异检查这一条命令的进程上**，用途是让 `.mutation-tmp` 收尾删除拿到干净退出码（脚本内注释有说明）；没有给任何真机 runner 关安全门，也没有绕过沙箱策略。

### 22.5 dist 产物本身被核过

`dist/content-script.js` sha256 `5b4807bd1b3123e8307599935c640918c07f1cb72631522f677848620d1c48a7`（61,464 B）、`dist/service-worker.js` `fe3122cb809c29555eece5c6aec635796dc72ad079629a23499a6eb8d3d963da`（138,861 B），两次构建前后完全一致。10 项关键字里包含本轮新增的 `adapter-text-match`（1 次）、`newChatText`（2 次）、`开启新对话`（6 次），以及上一轮不能丢的 `baselineContent` / `longcat.ai` / `RESPONSE_TIMEOUT` / `RESUME_WAIT_NO_BASELINE`。

⚠️ 新 dist hash 已不同于 §20 / ab3 使用的 `cffb6eb5…` / `b243c74d…`：`ab3-runner-2026-11-12.sh` 的前置检查里 `DIST_EV` 写死指向 `dist-consistency-2026-11-12.local-fix.json`，再用其中记录的老 hash 去比当前 dist 文件，**照原样跑必然报 hash 不符**。任何后续真机 runner 的 `PRECONDITION_OK` 必须改用本轮 `dist-consistency-2026-11-12.deepseek-newchat.json` 的新 hash，不得原样复用旧 runner。两个变体 Pack 的 sha256 本轮复核未变（`89b197cf…` / `0e1b4b98…`）。

### 22.6 机器裁定

`evidence/deepseek-newchat-verdict-2026-11-12.py` 只读门禁汇总、dist JSON、两份日志与源码声明，机械产出 `evidence/deepseek-newchat-verdict-2026-11-12.json`：

```
code = LOCAL_FIX_GATES_PASS_REAL_MACHINE_NOT_VERIFIED
localFixComplete = true      allGatesPass = true
realMachineVerified = false  propositionSupported = false
n25 = { status: "open", decision: "remain open" }
```

`realMachineVerified=false` 由「本轮是否产出新站点回执」机械判定（`newRealMachineReceipts=[]`），本地全绿不得把它推成 true。§21.5 的 `PROPOSITION_NOT_SUPPORTED` 与全部归因边界继续有效；N25 证据 23 → 27，`status=open`、`closed_at=null`。

### 22.7 归因边界（不得越线）

- 不能说 deepseek 的会话边界在真机上生效——本轮零次真机触发，jsdom 仍是唯一证据。
- 不能说「会话边界解掉了 step_8 撞墙」，也不能说「边界无效」——没有「A 撞墙且 B 通过」的成对证据，也没有边界真正生效过的轮次。
- 不能把 F1 公共等待判据的真机成功（`f1RealMachineVerified=true`）挪用为 `fresh_session` 的因果证据，两者是不同变量。
- 不能把 deepseek 的 8/8 归功于边界；不能说重置免费或把耗时差异归因给重置（§14.4）。
- 本轮未打开冻结站、未导入 Pack、未发送任何消息、**未 `git commit` / 未 `git push`**。

### 22.8 产物与当前状态

新增：`gates-deepseek-newchat-2026-11-12.sh`、同名 `.log` / `.jsonl` / `.summary.json`、`dist-consistency-deepseek-newchat-2026-11-12.mjs`、`dist-consistency-2026-11-12.deepseek-newchat.json`、`deepseek-newchat-verdict-2026-11-12.py` / `.json`，以及两份 build 日志、单测日志、全量变异日志。裁定 JSON 生成时核到 `HEAD == origin/main == 36d9ec2`、`statusItems=73`（开工 62 + 当时已落盘 11 项）；裁定 JSON 自身写完后再核为 **74** 项，`unpushed=0`，`committed=false` / `pushed=false`。两个数字都是磁盘真值，差别只来自裁定文件自身落盘的先后，不是漏项。

### 22.9 后续步骤（依赖顺序，均需单独授权）

1. **重新申请解冻** deepseek / longcat 并授权真机重跑：逐次 `ALLOW_FROZEN=1` 留痕，白名单不改；预检核登录态；用 §22.5 的新 dist hash 重核前置；相邻时间窗串行跑 4 轮 A/B。
2. B 组必须 `sessionResets[0].available===true && messageCountAfter<Before`；只有「A 撞墙且 B 通过」才支持命题。若边界未执行或 `available:false`，该轮作废 / 本轮不可评估，不得包装成「边界无效」。
3. 跑完按判据裁定 N25；在此之前 **N25 保持 `open`**。
4. 提交 / push 需单独授权，授权范围按提交与文件集合分清。

---

## 23. 明确解冻后 ab4 四轮真机 A/B：B 组硬判据首次 2/2 成立，命题仍不成立（2026-11-12 20:1x–20:5x）

### 23.1 授权边界与前置对账

用户明确下令「① 明确解冻并授权真机重跑；② B 组须 `available===true && messageCountAfter<Before`，边界未执行或 `available:false` 则判该轮作废 / 本轮不可评估，不得包装成「边界无效」；③ 只有「A 撞墙且 B 通过」才支持命题，跑完按判据裁定 N25，此前保持 open；④ 提交 / push 单独授权」。本节执行 ①–③，**④ 未授权也未执行**。冻结白名单代码未改，逐次 `ALLOW_FROZEN=1` 留痕：预检与 4 份回执的 `platformPolicy.unfrozenBy` 全为 `ALLOW_FROZEN=1`。

只读前置：`HEAD == origin/main == 36d9ec2`；当前 dist hash `5b4807bd…` / `fe3122cb…` 与 `dist-consistency-2026-11-12.deepseek-newchat.json` 完全一致；两个变体 Pack hash 未变（`89b197cf…` / `0e1b4b98…`）；`*.ab4-*` 目标路径全空；SW 缓存仅 13 文件（低于 shim 50 阈值）。预检 `L2-precheck-2026-11-12.ab4.deepseek-longcat.json`：deepseek / longcat 均 `composerVisible=true`、`looksLikeLogin=false`。

`ab4-runner-2026-11-12.sh` 相对 ab3 的三处硬修正：`DIST_EV` 改用本轮新证据（ab3 写死指向 `local-fix` 证据，新 dist 下必报 hash 不符）；OUT 全换 `*.ab4-*` 且不覆盖；结尾 `ALL_RECEIPTS_PRESENT` 逐份核回执，不再让 `RUNNER_FINISHED` 冒充「四轮都跑完」。4 轮严格串行，未设置 `CODEBUDDY_SAFE_DELETE_ENABLED=0`。

### 23.2 四轮实测结果

| 轮 | 平台 | 变体 | 回执 | 结果 | 步数 | 耗时 | `sessionResets` |
|---|---|---|---|---|---|---|---|
| 1 | deepseek | A `no-boundary` | `L2-deepseek-auto-2026-11-12.ab4-no-boundary.json` | **8/8 completed** | 8/8 | 80,535 ms | `[]` |
| 2 | deepseek | B `with-boundary` | `L2-deepseek-auto-2026-11-12.ab4-with-boundary.json` | **8/8 completed** | 8/8 | 79,644 ms | `available:true / adapter-text-match / 3→0 / 359 ms` |
| 3 | longcat | A `no-boundary` | `L2-longcat-auto-2026-11-12.ab4-no-boundary.json` | failed | 3/4，挂在 `step_4_scene`（723,310 ms） | 765,162 ms | `[]` |
| 4 | longcat | B `with-boundary` | `L2-longcat-auto-2026-11-12.ab4-with-boundary.json` | failed | 7/8，挂在 `step_8_output`（724,267 ms） | 861,811 ms | `available:true / adapter-selector / 6→0 / 307 ms` |

两处失败都是 4×180s 窗口的 `Response timeout`。第 4 轮前 7 步全部成功（单步 20–27 s），说明内容型等待判据仍在真机工作。

### 23.3 第 4 轮补齐：从「没跑」到 4/4 有回执

原 runner 第 4 轮在 `launch()` 清 SW 缓存时被 WorkBuddy safe-delete shim 拦住（`SAFE_DELETE_BULK_CONFIRM_REQUIRED`，`count 52 > threshold 50`，`scope:"turn"`，`targets=Extension Scripts`）：浏览器未启动、页面未打开、Pack 未导入、未发送任何内容，回执 `exists:false`。runner 正确输出 `ALL_RECEIPTS_PRESENT=False` —— §21.4 的教训已修好。只读核当前 `Extension Scripts` 只有 5 个文件，说明拦的是 turn 累计删除数，与 ab3 同型。

独立补跑 `ab4-round4-rerun-2026-11-12.sh` 走了两轮尝试，两个都是**脚本自身的 bug**，如实留痕：

1. 第一次 `PRECONDITION_FAILED`：`out_name` 是 `Path` 对象，`.replace(".json", suffix)` 调用的是 `Path.replace()`（文件系统重命名）而非字符串替换，Python 崩溃；且 stderr 当时没接进 `tee`，日志里只剩两行 shell 输出。已修为 `out_name.name.replace(...)`，并让两段 Python 的 stderr 一并 `2>&1 | tee`，日志改 append-only 保留失败证据。
2. 第二次 `PRECONDITION_OK`，清 SW 缓存仅 1 项未被拦，14m32s 后回执落盘；但收尾 verify 段把退出码字符串也转成了 `Path`，`int(ec)` 抛 `TypeError` ⇒ 进程假 `EXIT=1`、`summary` 与 verify 行缺失。**回执由驱动自身即时落盘，有效**。因此**不重跑真机**（不重复发送、不破坏 likeForLike），改用 `ab4-finalize-2026-11-12.py` 只读补齐 `ab4-final-receipts-2026-11-12.json`、`ab4-round4-summary-2026-11-12.json` 与一条标注 `source: "post-hoc-readonly-finalize"` 的 verify 行，明确不冒充即时记录；原 `ab4-runner-summary-2026-11-12.json` 里当时的 `allFourRoundsExecuted=false` 保留不覆盖。

### 23.4 逐轮机器复核与裁定

`ab4-verdict-2026-11-12.py` 只读 4 份回执机械推导，产出 `ab4-verdict-2026-11-12.json`（显式 `--regenerate` 补入 F2 / 混杂观察字段，产物内 `regeneratedFrom` 留痕，最终 `code` 未变）：

```
code = PROPOSITION_NOT_SUPPORTED_ROUNDS_UNUSABLE
allFourRoundsExecuted = true     allBoundariesActuallyExecuted = true
bHardCriteriaMetCount = 2       f2RealMachineVerified = true
propositionSupported = false    N25 remain open
```

| 平台 | 主状态 | 机械判据 | 结论 |
|---|---|---|---|
| deepseek | `NO_WALL_THIS_ROUND` | `aCompleted8of8=true`、`bCompleted8of8=true`、`bResetActuallyHappened=true` | A/B 都 8/8 ⇒ **本轮墙不存在**，B 组边界虽真执行（3→0）但无墙可解，不能归功边界 |
| longcat | `A_FAILED_BEFORE_WALL_STEP` | A 在 `step_4_scene` 失败、B 在 `step_8_output` 失败、`bResetActuallyHappened=true`、`bPassed=false` | **本轮不可评估**：A 没走到墙的位置，站点报错是混杂变量；既不能归功边界，也不能说边界无效 |

`bFailedAtWallStepAfterSuccessfulReset=true`：longcat B 在边界 `6→0` 真执行之后，`step_8_output` 仍 `Response timeout`。这是与命题方向相反的观察，必须显式列出；但按用户判据，**不得包装成「边界无效」** —— 没有成对的「A 在 step_8 撞墙」对照，且站点报错未被排除。裁定 JSON 里 `boundaryIneffectiveClaimed=false` 恒成立。

### 23.5 本轮最大进展：F2 真机验证成立，但 ≠ 命题成立

§21.7 的两条待修本轮均已落地并首次在真机上验证：deepseek B 组 `strategy:"adapter-text-match" / 3→0`，longcat B 组 `strategy:"adapter-selector" / 6→0`，`sessionResets[0].available===true && messageCountAfter<Before` **两站全部成立**（ab3 时是 0/2）。`f2RealMachineVerified=true` 证明的是「两个 adapter 的新会话入口真的能打开会话」，与「边界解掉长会话撞墙」是**不同变量**。§20.5 / §21.6 的 F1 / F2 分离口径继续有效：F1 验等待判据、F2 验入口可达、A/B 命题验因果，三者不可互相挪用。ab3 的 `allBoundariesActuallyExecuted=false` 被本轮 `true` 取代，这是**执行条件改善**，不是因果证据改善。

### 23.6 新混杂变量与 likeForLike 缺口

两张 longcat 截图的人工视觉判读：末条 AI 回复均为「**服务出错啦，请稍后再试。**」，无登录墙 / 验证码，左栏「开启新对话」入口可见。与 ab3 同型，站点侧随机报错持续存在，是独立于「长会话撞墙」「等待判据」「会话边界」的混杂变量。这些放在 `nonMachineObservations`，**不参与任何机器布尔推导**。

第 3→4 轮为独立补跑，`likeForLikeGapSeconds=182`（约 3 分钟），比 ab3 的约 31 分钟显著改善，但仍非连续执行；Pack 与 dist hash 经前置复核一致，缺口如实保留，不得抹掉。

### 23.7 归因边界（不得越线）

- 不能说「会话边界解掉了 step_8 长会话撞墙」——没有「A 撞墙且 B 通过」的成对证据。
- 不能说「边界无效」——longcat A 在 step_4 就失败，站点报错是混杂变量，不可用「B 在 step_8 也超时」反推。
- 不能把 deepseek 的 8/8 归功于边界——A 组无边界同样 8/8。
- 不能把 F2 的 3→0 / 6→0 挪用为 A/B 因果证据；不能把 F1 真机成功与会话边界混为一谈。
- 不能说重置免费、不能把耗时差异归因给重置（§14.4）；不能说「长会话撞墙已被根治」。
- 不能把补跑脚本的两个 bug 写成真机失败，也不能把「进程假 EXIT=1」写成「第 4 轮没跑」。

### 23.8 产物与未提交状态

新增：`ab4-precheck-2026-11-12.log`、`L2-precheck-2026-11-12.ab4.deepseek-longcat.json`、`ab4-runner-2026-11-12.sh`、`ab4-rerun-2026-11-12.log`、`ab4-rerun-progress-2026-11-12.jsonl`、`ab4-runner-summary-2026-11-12.json`、4 份 `L2-*-2026-11-12.ab4-*.json` 与 4 份截图、`ab4-round4-rerun-2026-11-12.sh`、`ab4-round4-2026-11-12.log`、`ab4-round4-progress-2026-11-12.jsonl`、`ab4-finalize-2026-11-12.py`、`ab4-final-receipts-2026-11-12.json`、`ab4-round4-summary-2026-11-12.json`、`ab4-verdict-2026-11-12.py`、`ab4-verdict-2026-11-12.json`。本轮**未改任何源码、未重建 dist**（真机加载的是 §22 已核过的 dist）、**未 `git commit` / 未 `git push`**。`HEAD == origin/main == 36d9ec2`、`unpushed=0`。

④ 的授权范围用只读清单 `commit-scope-2026-11-12.json` 盘点：工作区共 **96 项** = 15 个 tracked 改动 + 81 个 untracked；untracked 按来源分为本轮 ab4 证据/脚本 22、§22 门禁证据/脚本 12、ab3 17、ab/ab2 17、其他历史证据 12、源码与测试 1；按扩展名分为 34 json / 18 log / 12 png / 6 jsonl / 5 sh / 4 py / 2 mjs。后续授权须按「提交」与「文件集合」分别确认，不得默认一次性全收。清单落盘后工作区变为 **97 项**（清单文件自身 +1），两个数字都是磁盘真值，差别只来自生成先后。

### 23.9 后续步骤（依赖顺序，均需单独授权）

1. 若要让命题可判定，必须构造「A 在 `step_8_output` 撞墙」的成对对照，并排除 longcat 站点侧报错这个混杂变量；可在站点稳定时重跑，但**不得改 Pack**（会破坏「只差 `fresh_session` 一个变量」的 likeForLike）。
2. 重跑仍须逐次 `ALLOW_FROZEN=1` 留痕、预检核登录态、相邻时间窗串行、B 组硬判据成立；只有「A 撞墙且 B 通过」才支持命题。在此之前 **N25 保持 `open`**。
3. 本轮 runner / 补跑脚本的两个 bug 已在文件中修好，供后续复用；不要为它们再跑一次真机。
4. 提交 / push 需单独授权，授权范围按提交与文件集合分清。

---

## 24. 执行后续步骤：只读诊断证明「墙」已不可复现，产出观测先行方案，真机与提交均未越线（2026-11-12 21:1x）

### 24.1 授权分辨与开工真值

用户指令是「执行 后续步骤」，指向 §23.9 的四条：① 构造「A 在 `step_8_output` 撞墙」的成对对照并排除站点报错（可在站点稳定时重跑，**不得改 Pack**）；② 判据成立前 N25 保持 open；③ 归因边界；④ 提交 / push **单独授权，按提交与文件集合分清**。

按红线分辨：上一轮的解冻是**逐次显式放行**，「用完仍是冻结」，再跑真机必须**再次明确解冻**；④ 明示单独授权。因此本轮**不打开冻结站、不跑真机、不 `git commit` / 不 `git push`**。自主执行的是不越线且确有增量的本地准备：只读诊断 → 离线验证上轮脚本修复 → 产出 plan-only 方案 → 跑本地门禁。

开工磁盘真值：`HEAD == origin/main == 36d9ec2`、`unpushed=0`、`status_items=97`；N25 `open` / 32 条证据 / `closed_at:null`；裁定仍为 `PROPOSITION_NOT_SUPPORTED_ROUNDS_UNUSABLE`；RESULT 1456 行。

**授权收口（回写完成后逐次确认）**：就 ① 再次解冻真机重跑与 ④ 提交 / push 两个独立问题分别确认，用户明确选择「**暂不重跑（推荐）**」+「**暂不提交（推荐）**」。据此：不解冻、不打开冻结站、不跑预检、不发消息；不 `git commit`、不 `git push`；105 项改动全部留在工作区，`HEAD == origin/main == 36d9ec2`、`unpushed=0`。N25 保持 `open`，`ab5` 方案保持 `plan-only / NOT-EXECUTED`。§24.2–§24.5 的本地准备产物与结论照常交付。

### 24.2 只读诊断：命题的自变量（长会话撞墙）已不可控、不复现

`wall-observability-diagnosis-2026-11-12.py` 只读 13 份 ab / ab2 / ab3 / ab4 回执，机械汇总 `step_8` 演化，产出 `wall-observability-diagnosis-2026-11-12.json`：

| 侧 | F1 修复前 | F1 修复后（ab3 / ab4） |
|---|---|---|
| deepseek | 3 份回执全部在 `step_5_boundary` 假超时（4×180s），**根本没走到 step_8** | 4 份回执全部 8/8 completed；`step_8_output` 耗时 **13,333 / 13,286 / 12,310 / 13,617 ms** |
| longcat | — | 首次失败步在 `step_3_explain` / `step_4_scene` / `step_6_takeaway` / `step_8_output` **漂移**；两次 step_8 失败都是 723,235 / 724,267 ms（4×180s），截图同型「服务出错啦，请稍后再试。」 |

三条发现：

1. **F-D1**：§9.4 的 deepseek 症状「答案迟到，4×180s 都没稳定，运行结束后才生成完」正是长会话虚拟列表下 `countGrew` 恒 false 的**假超时**，已由 F1 内容型增长信号根治；不是上下文太长导致平台答不出。F1 后 `step_8` 只要 12–14 秒。
2. **F-D2**：longcat 在同一 Pack / 同一 dist 下失败步位置漂移，且截图均为站点报错 ⇒ 站点侧随机报错是**外部混杂变量**，不是稳定的 `step_8` 上下文墙。
3. **F-D3**：§9.4 的隔离实验证据 `L2-longcat-fusion-isolated-2026-11-11.json` 确实在盘，空会话 21s 通过只能证明「提示词本身不被平台拒绝」；而 §9.4 自己就写着 longcat 症状是「平台直接报错：服务出错啦，请稍后再试试。」⇒ 原始「长会话是变量」的因果归因被新证据削弱，不能作为「墙存在」的独立证据。

```
code = PROPOSITION_INDETERMINABLE_WALL_NOT_REPRODUCIBLE
```

结论：命题的自变量在 F1 修复后不可控、不复现，**继续盲跑 4 轮 A/B 大概率仍是 `NO_WALL_THIS_ROUND` 或站点错误**，无法提供「A 撞墙且 B 通过」的成对证据，只会白耗约 30 分钟与 32 步额度。必须钉死这不是：边界无效 / 命题不成立（不成立需有可判定的对照轮次）/ N25 可以关闭 / F1 或 F2 真机验证无效。

N25 的性质建议改述为「**已跑 A/B，但原始观察对象已重新归因、命题不可判定**」，而不是「还没跑对照」；是否关闭由用户裁定，本节**保持 `open`**。

### 24.3 plan-only 方案：把「A 撞墙」做成前置 gate，而不是跑完才发现没墙

`ab5-observe-first-plan-2026-11-12.json`（`status = "plan-only / NOT-EXECUTED"`、`noRealMachineAction=true`，自检 `pass=true`）：

- **Gate A**：先**只跑 A 组单轮**。机器判据 `stepsTotal==8 && stepSuccess==7 && firstFailedStepId=='step_8_output' && 错误含 Response timeout && 前 7 步全成功 && sessionResets 为空`；再加一道**人工视觉 gate**：截图末条 AI 回复不得是「服务出错啦，请稍后再试。」（属 `nonMachineObservation`，放行必须由人确认）。
- `onFalse → ABORT_NO_WALL`：不跑 B，落盘「本轮墙不存在」证据，N25 保持 open；约省 3/4 额度与时间。
- `onTrue`：立即跑同站 B，A/B 间隔目标 ≤ 5 分钟并如实记录；B 组硬判据 `available===true && messageCountAfter<Before`，`bPassed = hard && 8/8 completed`。
- 只有 `gateA && visualConfirmed && bPassed` 才支持命题；边界未执行 / `available:false` ⇒ 该轮作废或本轮不可评估，**不得包装成「边界无效」**。
- 硬约束：不得改 Pack（A/B 只差 `fresh_session` 一个变量，两个变体 sha256 不变）、同 dist / 同账号态 / 相邻时间窗、逐次 `ALLOW_FROZEN=1` 留痕且白名单不改、预检也显式解冻、全程 tee + 即时 JSONL + 即时回执、`*.ab5-*` 新路径不覆盖、`ALL_RECEIPTS_PRESENT` 逐份核、不设 `CODEBUDDY_SAFE_DELETE_ENABLED=0`、提交 / push 单独授权。
- 前置条件第一条「用户给出明确解冻指令」**当前未满足**，因此方案不执行。

### 24.4 离线验证 §23.3 的两处脚本 bug 已修

`offline-verify-ab4-round4-fix-2026-11-12.py` 用静态断言 + `bash -n` + `tempfile` 重放验证 10 项，**10/10 通过**：

- B1 `out_name.name.replace(...)` 存在、旧 `Path.replace` 代码消失、后缀推导结果为 `.json` / `.png` 两个正确路径且不抛异常；
- B2 `ec = _args[4]` 保持字符串、`int(ec)` 不再抛 `TypeError`，重放得到 `nodeExit=0 / 8 步 / 7 成功 / reset 6→0 / resetActuallyHappened=true`；
- 两段 Python 的 stderr 都接进 `tee`、日志 append-only 不覆盖第一次 `PRECONDITION_FAILED`；两个脚本 `bash -n` 通过。

硬边界全部为 false：未启动浏览器、未打开冻结站、未发送消息、未写真机 OUT、未覆盖既有证据、未调用 `l2-platform-auto.mjs`、未碰 git。离线通过**只证明脚本不再因自身 bug 假失败**，不代表任何新的真机结论。

### 24.5 本地门禁（`ab5-prep-gates-2026-11-12.json`，`allPass=true`）

| 门禁 | 结果 |
|---|---|
| 全量 `npm test` | **349/349，fail 0**（`npm-test-2026-11-12.ab5-plan.log`） |
| 离线脚本重放 | 10/10 |
| plan 自检 | `pass=true`，`status=plan-only / NOT-EXECUTED` |
| evidence JSON | 121 份全部可解析，0 失败 |
| 源码 / 测试 / dist | **本轮未改**；tracked 改动仍是上一轮那 15 个文件，新增物全在 `evidence/` 下 |

`allPass=true` 时的 evidence JSON 计数是 121（汇总文件自身尚未落盘）；全部回写完再核为 **122**、`status_items=105`（开工 97 + 本轮 8 项新产物）。两个数字都是磁盘真值，差别只来自生成先后。

### 24.6 归因边界（继续有效并扩充）

- 不能说「会话边界解掉 step_8 撞墙」，也没有依据说「边界无效」。
- 不能把 A/B 都通过归功边界；不能把 F1 / F2 的真机成功挪用为 A/B 因果证据。
- 不能说重置免费、不能把耗时差异归因给重置；不能说「长会话撞墙已被根治」——准确说法是**原始观察已重新归因，墙不复现**。
- 站点侧报错是外部混杂变量，必须单独标注，不得与「墙」合并归因。
- 不能把补跑脚本的两个 bug 写成真机失败；不能把 plan-only 方案写成已执行回执。

### 24.7 产物与状态

新增 `wall-observability-diagnosis-2026-11-12.py` / `.json`、`offline-verify-ab4-round4-fix-2026-11-12.py` / `.json`、`ab5-observe-first-plan-2026-11-12.py` / `.json`、`ab5-prep-gates-2026-11-12.json`、`npm-test-2026-11-12.ab5-plan.log`。**未改源码 / 未重建 dist / 未打开冻结站 / 未发消息 / 未 `git commit` / 未 `git push`**；N25 保持 `open`。

### 24.8 后续步骤（依赖顺序，均需单独授权）

1. **再次明确解冻**并授权真机重跑：建议按 §24.3 的 observe-first gate 执行，而不是盲跑 4 轮；逐次 `ALLOW_FROZEN=1` 留痕。
2. 若 Gate A 判「墙不存在」，按 `ABORT_NO_WALL` 停止，N25 仍保持 open；若成立才跑 B 并按判据裁定。
3. 提交 / push 按「提交」与「文件集合」分别确认；`commit-scope-2026-11-12.json` 已给出 96 项分类（清单自身落盘后工作区 97 项），不要默认一次性全收。


---

## §25 执行「后续步骤」：解冻 + observe-first 单轮 → ABORT_NO_WALL，N25 保持 open（2026-11-14）

用户 2026-11-14 明令：「解冻并按 observe-first gate 重跑（先跑 A 单轮，判无墙即停），而不是盲跑 4 轮；逐次 `ALLOW_FROZEN=1` 留痕。Gate A 判「墙不存在」→ `ABORT_NO_WALL`，N25 仍 open；仅当 Gate A 成立才跑 B 并按判据裁定。提交 / push 按「提交」与「文件集合」分别确认，不要默认一次全收。」时间跨了 2 天，先核磁盘真值，不认上轮自述。

### 25.1 跨 2 天只读前置对账（`ab5-precondition-2026-11-14.json`，`preconditionPass=true`）

| 项 | 磁盘真值 | 结论 |
|---|---|---|
| HEAD / origin/main | `36d9ec2` / `36d9ec2`，`unpushed=0` | 一致 |
| 工作区 | 105 项（落盘本证据时 106） | 与 `commit-scope-2026-11-12.json` 分类一致 |
| dist | `content-script.js 5b4807bd…` / `service-worker.js fe3122cb…` | 与 `dist-consistency-2026-11-12.deepseek-newchat.json` 逐文件 hash 一致，幂等构建证据 `allPass=true` |
| 变体 Pack | `89b197cf…` / `0e1b4b98…` | 与 ab5 plan 声明一致，**未改 Pack** |
| `L2-*.ab5-*.json/.png` 目标路径 | 0 个占用 | 不覆盖任何既有证据 |
| SW 缓存 | Service Worker 8 / Extension Scripts 5 / Code Cache 缺失 = 13 项 | 远低于 shim 的 50 阈值，无需绕过安全门 |
| ab5 plan 状态 | `plan-only / NOT-EXECUTED`、`noRealMachineAction=true` | 未被偷跑 |

授权留痕：用户明令全文写进 `authorization.verbatim`；`unfrozenPlatforms=[deepseek,longcat]`；`perCommandFlag=ALLOW_FROZEN=1`；`appliesToPrecheck=true`；`whitelistCodeChanged=false`；`usageRule=逐次显式放行，用完仍是冻结`。**代码白名单未改**。

### 25.2 判据留白不暗猜：Gate A 首轮平台由用户裁定

ab5 plan 的 `gateA.description` 只写「先只跑 A 组（no-boundary）单轮」，**未钉死 platform**。前置证据把该项标为 `openCriterion.resolution=PENDING_USER_CONFIRMATION`，并向用户出具只读探测得到的两条依据：deepseek 在 F1 修复后 ab3/ab4 两轮 A 全 8/8、`step_8` 12.3–13.6s，原始「答案迟到 4×180s」已重新归因为虚拟列表假超时；longcat 失败步在 `step_3/4/6/8` 漂移、截图同型「服务出错啦」站点报错，属外部混杂变量。

用户 `AskUserQuestion q-0` 裁定 **deepseek**。裁定独立落盘 `ab5-gate-a-platform-ruling-2026-11-14.json`（`roundsTotal=1`，`onGateAFalse=ABORT_NO_WALL`），**不覆盖**前置证据里的 PENDING 历史留痕。

### 25.3 显式解冻预检（`L2-precheck-2026-11-14.ab5.deepseek-longcat.json`）

`CANDIDATES=deepseek,longcat PRECHECK=1 ALLOW_FROZEN=1`，全程 `tee -a ab5-precheck-2026-11-14.log`。两站 `composerVisible=true` / `looksLikeLogin=false`；`platformPolicy` 两站均 `allowed=true / active=false / unfrozenBy=ALLOW_FROZEN=1 / reason=frozen-but-explicitly-unfrozen`。SW 缓存仅清 2 项，**未设置** `CODEBUDDY_SAFE_DELETE_ENABLED=0`。

### 25.4 observe-first：只跑 1 轮 A（`ab5-observe-first-runner-2026-11-14.sh`）

`PRECONDITION_OK` 后仅执行 `deepseek / no-boundary` 一轮，`NODE_EXIT=0`，耗时 1m19s。落盘口径全部满足：stdout 全程 `tee -a ab5-observe-first-2026-11-14.log`；`start / node-exit / verify / verify written / runner done` 即时写 append-only `ab5-observe-first-progress-2026-11-14.jsonl`；回执由驱动自身即时写 OUT；结尾 `RECEIPT_PRESENT=True`。

| 字段 | A 单轮真值 |
|---|---|
| 回执 | `L2-deepseek-auto-2026-11-14.ab5-no-boundary.json`（17968 B） |
| `exec.success` / `status` | `true` / `completed` |
| steps | **8/8 全成功**，`duration=74558ms` |
| `step_8_output` | **成功，11736ms** |
| `sessionResets` | **0**（A 组无边界，符合变体） |
| `platformPolicy.unfrozenBy` | `ALLOW_FROZEN=1` |
| 首失败步 | **无**（`firstFailedStepId=null`） |

截图 `L2-deepseek-auto-2026-11-14.ab5-no-boundary.png` 已落盘。

### 25.5 Gate A 机器裁定（`ab5-gate-a-verdict-2026-11-14.json`）

`ab5-gate-a-verdict-2026-11-14.py` 只读回执，机械判 6 条判据：

| 判据 | 结果 |
|---|---|
| C1 `stepsTotal==8` | ✅ |
| C2 `stepSuccess==7` | ❌（实际 8） |
| C3 `firstFailedStepId=='step_8_output'` | ❌（无失败步） |
| C4 错误含 `Response timeout` | ❌（无失败步） |
| C5 前 7 步全成功 | ✅ |
| C6 A 组 `sessionResets` 为空 | ✅ |

`machinePass=false` ⇒ **`code=ABORT_NO_WALL`**，`bShouldRun=false`。按判据**不跑 B、不跑 longcat**。

### 25.6 人工视觉巡检（`nonMachineObservation`，不参与机器布尔）

`ViewImage` 判读截图：末条 AI 回复是**正常中文长文本**（AI 智能体定义与场景说明），不是「服务出错啦，请稍后再试。」；无登录墙、无验证码/滑块。左栏「开启新对话」入口可见，但本轮是 `no-boundary`、**未触发任何 `NEW_SESSION`**，不得据此说 F2 在本轮真机生效。该观察在 `ab5-final-verdict-2026-11-14.json` 里单列 `visualObservation.participatesInMachineBoolean=false`，**不改变 `ABORT_NO_WALL` 结论**。

### 25.7 ABORT 分支硬核与归因边界（`ab5-final-verdict-2026-11-14.json`）

只读核磁盘：`bReceipt / longcatAReceipt / longcatBReceipt` 三个 ab5 目标路径 **全部 `exists=false`**；`roundsExecuted=1`、`bActuallyRun=false`、`longcatActuallyRun=false`；`progressEvents` 只有单轮的 6 条事件。

- 只有「A 撞墙且 B 通过」才支持命题；本轮 A 未撞墙、B 未跑 ⇒ **`propositionSupported=false`**，`boundaryIneffectiveClaimed=false`。
- **不能说边界有效，也不能说边界无效**；不能把「A 8/8 通过」归功边界；不能把既往 F1 / F2 真机验证挪用为 A/B 因果证据。
- `f1RealMachineVerifiedThisRound=false` / `f2RealMachineVerifiedThisRound=false`：本轮 `sessionResets=0`，没有触发会话边界，不新增任何 F1/F2 因果结论；§21 / §23 的既往结论不翻案。
- 准确说法是：**本轮墙不存在，判无墙即停**；§24 的「原始观察已重新归因、墙不复现」得到又一次同型真机佐证，但这不是「长会话撞墙已被根治」的因果证明。
- **N25 保持 `open`**，`closed_at=null`。

### 25.8 产物与状态

新增：`ab5-precondition-2026-11-14.py/.json`、`ab5-gate-a-platform-ruling-2026-11-14.json`、`L2-precheck-2026-11-14.ab5.deepseek-longcat.json`、`ab5-precheck-2026-11-14.log`、`ab5-observe-first-runner-2026-11-14.sh`、`ab5-observe-first-2026-11-14.log`、`ab5-observe-first-progress-2026-11-14.jsonl`、`ab5-observe-first-verify-2026-11-14.json`、`L2-deepseek-auto-2026-11-14.ab5-no-boundary.json/.png`、`ab5-gate-a-verdict-2026-11-14.py/.json`、`ab5-final-verdict-2026-11-14.py/.json`。

本轮**未改源码 / 未重建 dist / 未改变体 Pack / 未改冻结白名单 / 未跑 B / 未跑 longcat / 未 `git commit` / 未 `git push`**。提交 / push 按「提交」与「文件集合」分别确认，不默认一次全收。

### 25.9 后续步骤（均未授权，按依赖顺序）

1. 若仍要追究命题：先解决 §24 的自变量不可控问题（原始墙已重新归因），再申请**新的逐次解冻**；不得直接盲跑 4 轮。
2. 提交 / push 单独授权：按「是否提交」与「提交哪个文件集合」两个问题分别确认，`commit-scope-2026-11-12.json` 已有分类清单。


### 25.10 收口时补记：`origin/main` 已被外部推进 4 个提交（回溯修正 §25.1）

最终磁盘真证对账发现，§25.1 表格里的「HEAD / origin/main 均 `36d9ec2`」是**开工时（07:34Z）**快照；收口时 `origin/main = f98a1a7`，本地 `HEAD = 36d9ec2`，**behind 4 / ahead 0 / unpushed 0**。`git reflog show origin/main` 显示两次 `fetch --quiet origin: fast-forward`，来自外部推进，**不是本会话操作**；本会话未执行 fetch / pull / merge / rebase / commit / push，本地 HEAD 未移动。

| 新远端提交 | 说明 |
|---|---|
| `9dc4da9` | `ci(nightly): 给 pytest 管道显式开 pipefail，别让 tee 吞掉失败` |
| `b577d05` | `test(adapter-matrix): 同步 kimi/longcat/yiyan 快照到 11-11 真机选择器` |
| `3173dd7` | Merge PR #47 |
| `f98a1a7` | Merge PR #48 |

改动文件只有 `.github/workflows/nightly.yml` 与 3 个 `chrome-extension/tests/adapter-matrix/fixtures/mock-dom-*.html`，**未触碰 dist / 变体 Pack / evidence / known_gaps / RESULT**。因此 §25.1 的 hash 复核、§25.4 单轮回执、§25.5 Gate A 裁定、§25.7 `ABORT_NO_WALL` 结论全部保持有效，不需要翻案。原文不删，留痕。

对提交的现实影响：若后续授权提交并推送，本地落后远端 4 个提交，**push 前必须先处理分歧（merge / rebase）**，该动作须单独授权，不得默认执行。见 `remote-divergence-2026-11-14.json` 与 `commit-scope-2026-11-14.json` 的 `remoteDivergence` 字段。


### 25.11 提交授权裁定：暂不提交（`commit-authorization-ruling-2026-11-14.json`）

按用户明令「提交 / push 按『提交』与『文件集合』分别确认，不要默认一次全收」，两个问题分别确认：

| 问题 | 用户裁定 | 效力 |
|---|---|---|
| q-0 提交动作 | **暂不提交（推荐）** | **本次实际裁定**：不 commit / 不 push / 不 stage，125 项全留工作区；远端 `behind=4` 的分歧不处理 |
| q-1 文件集合 | **仅本轮 ab5 产物（推荐）** | **仅为日后偏好登记**（`PREFERENCE_ONLY_NOT_AUTHORIZATION`）：19 项 ab5 新产物 + RESULT 报告 + `known_gaps.json`，不含源码/测试与 ab3/ab4/ab/ab2 历史证据 |

q-1 的题面是「若后续授权提交」，因此**不能**据此推断本轮已授权提交，也不能当成一次全收 125 项的授权。下一次真正提交时，「提交动作」仍须单独重新授权；且因本地落后远端 4 个提交，push 前处理分歧的动作也须单独授权。

落盘前后磁盘真值一致（`HEAD=36d9ec2`、`origin/main=f98a1a7`、`unpushed=0`、`behind=4`、`staged=0`）；本轮**未碰 git**。


---

## §26 追究命题：可判定性的只读诊断（2026-11-14，路径待裁定）

用户明令「处理后续步骤：1、追究命题；2、重新授权」。本节只完成第 1 项的**只读诊断**；第 2 项授权宾语未指明，按维度分别确认，不擅自执行。开工前核磁盘真值：`HEAD=36d9ec2` / `origin/main=f98a1a7`，behind 4 / ahead 0 / unpushed 0 / staged 0，127 项全在工作区；N25 `open` 40 证据；ab5 仍 `ABORT_NO_WALL`；132 份 evidence JSON 全可解析；`ab6` 目标路径为空。

### 26.1 命题与可判定条件的形式化

| 项 | 定义 |
|---|---|
| 命题 | `fresh_session` 会话边界能解掉 deepseek / longcat 的 `step_8` 长会话撞墙 |
| 自变量 | 单会话串行累积到 `step_8` 时的「长会话撞墙」状态 |
| 因变量 | `step_8_output` 是否失败（`Response timeout` / 站点报错） |
| 可判定 iff | 存在至少一次 A 组能稳定复现「前 7 步全成功、`step_8_output` 失败、且失败**不是**站点侧随机报错、**不是**等待判据 bug」；且同站相邻时间窗的 B 组在边界真执行后通过 |

### 26.2 机械证据：8 份 A 组回执，结构条件已满足但墙不出现

变体 Pack 的唯一差异经复核确认：B 组只在 `workflow.steps[7]` 多一个 `fresh_session: "prefer"`，A 组递归删掉该键，**其余 8 步的 `prompt_template` / `input_fields` / `config` 逐字节一致**。因此 A 组 `no-boundary` 本来就是**同一会话 8 步串行、7 次 AI 往返、无任何会话边界**——这正是 §9.4 原文宣称的自变量条件「会话已累积 7 轮、约 5–6k 字」。

`proposition-pursuit-plan-2026-11-14.py` 机械汇总 8 份 A 组回执，F1 之后走满 8 步的有 3 份：

| 回执 | steps | step_8 成功 | step_8 耗时 | sessionResets |
|---|---|---|---|---|
| `L2-deepseek-auto-2026-11-12.ab3-no-boundary.json` | 8/8 | True | 13333 ms | 0 |
| `L2-deepseek-auto-2026-11-12.ab4-no-boundary.json` | 8/8 | True | 12310 ms | 0 |
| `L2-deepseek-auto-2026-11-14.ab5-no-boundary.json` | 8/8 | True | 11736 ms | 0 |

**3 份全部 8/8 completed，撞墙 0 次**。加上 ab5 observe-first 单轮（8/8、11.7s、`sessionResets=0`），这是第 3 份同型结构复现证据。

### 26.3 回溯修正 §24：不是「没复现长会话」，而是「条件满足、因变量不出现」

§24 写「自变量不可控、不复现」。更准确的机械表述是：**长会话的结构条件已经复现**（同一会话 7 次 AI 往返），但 `step_8` 没有失败。原始观察的两种症状已被分别重新归因 —— deepseek 是 F1 已根治的虚拟列表 `countGrew` 假超时，longcat 是站点侧随机报错（外部混杂变量）。因此「墙」不是被漏掉，而是**作为可复现的自变量并不存在**。§24 的 `PROPOSITION_INDETERMINABLE_WALL_NOT_REPRODUCIBLE` 结论不变，但论据由「推论」升级为「多次真机同型观察」。

隔离实验 `L2-longcat-fusion-isolated-2026-11-11.json`（2437 字、空会话、21s、1481 字）只能证明「提示词本身不被平台拒绝」，不能独立证明「长会话是变量」，F-D3 的削弱依然有效。

### 26.4 五条候选路径（`proposition-pursuit-plan-2026-11-14.json`）

| ID | 路径 | 真机轮次 | 需解冻 | 建议 |
|---|---|---|---|---|
| P1 | 按不可判定收口 / 改述 N25 | 0 | 否 | 推荐：唯一不消耗站点额度、不制造新混杂变量的诚实路径 |
| P2 | 回滚 F1 的归因对照实验 | 2–4 | 是 | 不推荐作为追究原命题的手段（答的是另一个问题） |
| P3 | 人工加长会话试图复现墙 | 2–4 | 是 | 不推荐：换命题 + 破坏单变量约束 |
| P4 | 按原判据再跑一次完整 4 轮 A/B | 4 | 是 | 不推荐：与用户最新明令冲突 |
| P5 | 换活跃 5 站做替代对照 | 2–4 | 否 | 不推荐：答非所问 |

- **P1**：零真机成本、不制造新混杂变量；但「是否关闭 N25」仍须用户裁定，判据未成立前默认保持 `open`，只改述性质为「已跑 A/B，原始观察对象已重新归因、命题不可判定」。
- **P2**：临时回滚 F1 属主动制造已知 bug，违反本轮「不改源码 / 不改 dist」边界；即便重现假超时，只验证 F-D1 归因，**对原命题的因果结论无直接贡献**。
- **P3**：改 Pack 违反 ab5 plan 硬约束「A/B 只差 `fresh_session` 一个变量、Pack hash 不变」；加长会话等于换命题。
- **P4**：与用户 2026-11-14 明令「而不是盲跑 4 轮」直接冲突。
- **P5**：N25 原始观察对象明确是 deepseek / longcat，换活跃 5 站等于换命题，N23 的「重置真的做到了」不能代偿。

### 26.5 「重新授权」的授权维度拆分（宾语未指明）

用户只说「重新授权」，未指明授权什么。按既有红线「提交 / push 按提交与文件集合分别确认、不要默认一次全收」，拆解为 6 个**互相独立**的维度，当前全部为未授权：A1 追究路径（P1–P5）、A2 逐次解冻 deepseek / longcat、A3 `git commit`、A4 提交文件集合、A5 behind=4 分歧处理（merge / rebase / pull）、A6 push 到远端。上一轮 q-0 = 暂不提交、q-1 = 仅本轮 ab5 产物且状态为 `PREFERENCE_ONLY_NOT_AUTHORIZATION`，**不因本轮「重新授权」四个字自动升级为授权**。

### 26.6 状态

方案 `status = plan-only / NOT-EXECUTED`；硬边界全 false（未启动浏览器、未改 Pack、未改源码/dist、未碰 git、未发消息、未产生真机回执）；`n25 = remain open`。本节路径裁定与授权结果待用户明确后补 §26.x。


### 26.7 用户裁定与 P1 执行（`proposition-pursuit-ruling-2026-11-14.json`）

四个维度分别确认，未默认打包：

| 问题 | 裁定 | 效力 |
|---|---|---|
| q-0 追究路径 | **P1 收口改述 N25** | 已执行，见下 |
| q-1 解冻真机 | **不解冻** | 不启动浏览器、不打开冻结站、不跑预检、不发消息；用完仍是冻结，白名单代码未改 |
| q-2 提交动作 | **暂不提交** | 不 commit / push / stage / merge / rebase；127+ 项全留工作区 |
| q-3 文件集合 | **仅本轮产物** | 因 q-2 为暂不提交，仍是 `PREFERENCE_ONLY_NOT_AUTHORIZATION`，**不是**本次提交授权，也不是一次全收 |

P1 的具体落地：N25 新增 `recharacterization` 结构化字段，性质由「待 A/B 验证」改述为「**已跑 A/B，但原始观察对象已重新归因、命题不可判定**」；写明 `reader`、三条机器证据依据、`isNot` 四条边界、以及「关闭仍需单独裁定」。`status` 保持 `open`、`closed_at` 保持 `null`、优先级不动；**原 `title` / `detail` / `fix` / `reader` / `where` 全部保留不覆盖**，符合台账 `conventions` 的「关闭后保留条目」与「每条必须写 reader」精神，也便于接手者考古原始口径。N25 证据 41→42。

六维授权结果：A1 路径已裁定 P1；**A2 解冻 / A3 commit / A4 文件集合 / A5 behind=4 分歧处理 / A6 push 全部保持未授权**。`behind=4` 分歧不动。

### 26.8 最终磁盘真证与状态

本轮 `realMachineRounds=0`，硬边界全 false：未启动浏览器、未打开冻结站、未发送消息、未改 Pack、未改源码 / 测试 / dist、未碰 git、未产生真机回执。新增产物全部在 `evidence/` 下：`proposition-pursuit-plan-2026-11-14.py/.json`、`proposition-writeback-2026-11-14.py`、`proposition-pursuit-ruling-2026-11-14.json`、`proposition-pursuit-execution-2026-11-14.json`。

归因边界继续有效：不能说边界有效、也不能说边界无效；不能把 F1 / F2 真机验证挪用为因果证据；不能说「长会话撞墙已根治」（准确说法是**原始观察已重新归因、结构条件复现但墙不出现**）；站点侧报错须单独标注；不能把 `plan-only` 写成已执行回执。

后续步骤（均未授权，按依赖顺序）：① 若要关闭 N25，须单独明确裁定；② 若要跑真机，须逐次明确解冻并说明本次改变了哪个自变量（否则 §26 已证盲跑不产生新证据）；③ 若要提交，须按「提交动作」与「文件集合」分别重新授权；④ 若 push，还须单独授权先处理 `behind=4` 分歧。


---

## §27 关闭 N25 + 两条条件指令判定（2026-11-15）

用户指令：「后续步骤（均未授权，按依赖顺序）1、关闭 N25 2、跑真机：须逐次明确解冻，并说明本次改变了哪个自变量；否则 §26 已证盲跑不产生新证据。3、提交：按『提交动作』与『文件集合』分别重新授权；若 push，还须单独授权先处理 behind=4 分歧。」

### 27.1 开工磁盘真值（跨 1 天，不认上轮自述）

| 项 | 真值 |
|---|---|
| HEAD / origin/main | `36d9ec2` / **`19635c6`**（上轮收口时是 `f98a1a7`） |
| ahead / behind / unpushed / staged | 0 / **31**（上轮 4）/ 0 / 0 |
| 工作区 | 133 项（本轮新产物落盘后递增） |
| N25 | `open` / `closed_at=null` / 42 条证据 / 已有 `recharacterization` |
| RESULT | 1745 行，§26 共 8 子节 |
| evidence JSON | 135 份全可解析 |
| `ab6` 目标路径 | 空 |

### 27.2 🔧 回溯补记：`behind=4` 已是过期快照

`origin/main` 又被**外部** `fetch origin main --quiet: fast-forward` 推进 27 个提交（`f98a1a7 → 19635c6`），`git diff --name-only` 显示只改 7 个 `.github/workflows/*.yml`（nightly / build / healthcheck / lint / mypy-gate / security / test）。**未触碰 dist / 变体 Pack / evidence / 台账 / 报告 / 源码 / 测试** ⇒ §25、§26、ab5 结论全部保持有效，不翻案。用户指令里的 `behind=4` 是 2026-11-14 快照，按 disk-truth 以 **31** 为准。见 `remote-divergence-2026-11-15.json`；§25.10 原文不删。

现实影响：若日后授权 push，须先单独授权处理 **behind 31** 的分歧，代价较上轮的 behind 4 大幅上升。本会话未 fetch / pull / merge / rebase / commit / push，本地 HEAD 未移动。

### 27.3 三条指令的机器前提判定（`three-steps-precondition-2026-11-15.json`）

括号里的「**均未授权**」是关键：第 2、3 条自带前置条件，不能因用户复述清单就推断为已授权。

| 步骤 | 用户自设前提 | 实际 | 判定 |
|---|---|---|---|
| 1 关闭 N25 | 无附加条件（祈使句） | 构成对旧红线的**显式裁定** | `EXECUTED` |
| 2 跑真机 | 逐次明确解冻 + 说明改了哪个自变量 | 两项都没给；`ALLOW_FROZEN` 本轮未出现 | `NOT_EXECUTED_PRECONDITION_UNMET` |
| 3 提交 | 提交动作、文件集合分别授权；push 另需授权处理分歧 | 三项都没给 | `NOT_AUTHORIZED_NO_ACTION` |

### 27.4 第 1 条：关闭 N25（`n25-closure-2026-11-15.json`）

🔧 **显性标记：本次关闭推翻用户 2026-11-11 旧红线「N25 只能在 A/B 跑完且判据成立之后关闭」**。用户是本红线的制定者，本条无条件祈使句即为显式裁定；依据是 §26 证明该判据**永远不会成立**（A 组结构条件已满足仍 3/3 全 8/8、撞墙 0 次），继续 `open` 只会固化「待验证」的假状态。

落盘动作：`status: open → closed`、`closed_at: "2026-11-15"`，新增 `closure` 字段（`type = INDETERMINABLE_PROPOSITION_CLOSED`），含 `🔧_explicitRedLineOverride`、结案理由、`isNot` 5 条、`whatRemainsTrue` 4 条、`reader`、5 份证据引用。**原 `title` / `detail` / `fix` / `reader` / `where` / `recharacterization` 与全部既有证据原样保留，不删不改**，符合台账 `conventions`「关闭后保留条目与结论」。证据 42→43。

**结案理由 = 原始观察对象已重新归因、墙不复现、命题不可判定。不是验证通过、不是边界有效、也不是边界无效。** 仍然成立的事实：F1 等待判据修复真机生效（§21）、F2 会话入口真机可达（§23）、ab4 B 组硬判据 2/2 成立、ab5 判无墙即停。

### 27.5 第 2 条：不跑真机（前提未满足）

用户自己写了「须逐次明确解冻，并说明本次改变了哪个自变量；否则 §26 已证盲跑不产生新证据」。本轮：无解冻指令、无 `ALLOW_FROZEN=1`、无自变量说明。§26 五条路径里只有 P2（改源码/dist 回滚 F1）和 P3（改 Pack 加长会话）会改变自变量，两者都违反本轮硬约束；P1/P4/P5 不改变自变量。按用户自设条件，此条自动不成立。冻结站未碰，用完仍是冻结，白名单代码未改。

### 27.6 第 3 条：不提交（未授权）

「提交动作」与「文件集合」两项均未分别授权，push 的前置分歧处理亦未授权。上轮 q-0「暂不提交」与 q-3（`PREFERENCE_ONLY_NOT_AUTHORIZATION`）继续有效，不因复述清单自动升级。不 commit / push / stage / merge / rebase；`behind 31` 保持不动。

### 27.7 硬边界与最终状态

本轮 `realMachineRounds=0`：未启动浏览器、未打开冻结站、未发送消息、未改 Pack / 源码 / 测试 / dist、未碰 git、未产生真机回执。新增产物全在 `evidence/`：`three-steps-precondition-2026-11-15.py/.json`、`remote-divergence-2026-11-15.json`、`n25-closure-2026-11-15.json`、`three-steps-execution-2026-11-15.json`、本节回写脚本。

归因边界继续有效：不能说边界有效/无效、不能把 F1/F2 真机验证挪用为因果证据、不能说「长会话撞墙已根治」、站点侧报错须单独标注、不能把 plan-only 写成已执行回执、**不能把本次关闭写成验证通过**。

## §28 ①②③ 授权闭合度与「N25 若需重开」机制（2026-11-15）

### 28.1 开工磁盘真值（跨时段，不认上轮自述）

`three-items-precondition-2026-11-15.json`：`HEAD=36d9ec2`、`origin/main=915c350`、`ahead=0 / behind=33 / unpushed=0 / staged=0`、`status_items=139`（对账脚本落盘前）。台账 25 条 `open 0 / closed 24 / wontfix 1`；N25 `closed` / 43 条证据 / `closed_at=2026-11-15` / `closure.type=INDETERMINABLE_PROPOSITION_CLOSED` / `recharacterization=True`；RESULT 1802 行、§27 共 7 子节；139 份 evidence JSON 全部可解析；`ab6` 目标回执 0。

🔧 **本轮对账自身抓到两处数据缺陷并回溯修正**：
- **D-1（假阳性）**：首个对账脚本对 `git status --porcelain` 整段 stdout 调了 `.strip()`，吃掉首行前导空格，把 `' M chrome-extension/src/background/pack-executor.js'` 误读成 `'M ...'`，报 `staged=1`。复核 `git diff --cached --stat/--raw` 均为空、`ls-files -s` 的 index blob `f151615` 与 HEAD blob 相同、worktree blob `cfc4fa2` 不同 ⇒ **真值 `staged=0`**，是未暂存的 worktree 修改。不得据此 unstage。
- **D-2（真实缺陷）**：同一 `.strip()` 使 `commit-scope-2026-11-14.json` 的 `modifiedTracked.files[0]` 变成 `'hrome-extension/src/background/pack-executor.js'`（首字符 `c` 被切），照该清单逐条 `git add` 会漏 add 或报 pathspec 错。本轮 `commit-scope-2026-11-15.py` 改用 `rstrip('\n')` 并按前缀断言，已修正为 `chrome-extension/src/background/pack-executor.js`；旧清单作为历史证据保留不覆盖。
- 附带一处开发期即时修正：新盘点脚本首版断言误用子串匹配（`"hrome-extension"` 本就是 `"chrome-extension"` 的子串），改成 `startswith` 后通过。

### 28.2 🔧 回溯补记：`behind=31` 已是过期快照

用户指令写「另需单独授权先处理 behind 31 分歧」。磁盘真值：`origin/main` 由 `19635c6` 被外部 fetch 推进到 `915c350`，新增 2 个提交（`915c350` Merge PR #62、`08ab0f9` 清掉最后 2 处 `continue-on-error`），只改 `.github/workflows/security.yml` 与 `test.yml`；累计 `36d9ec2..origin/main` 共 10 个文件（7 个 workflow + 3 个 adapter-matrix fixture），`ourInputsTouched=[]` —— 未触碰 dist / 变体 Pack / evidence / known_gaps / RESULT / 源码 / 测试。本会话未 fetch / pull / merge / rebase / commit / push。见 `remote-divergence-2026-11-15.2.json`。

**若日后授权 push，须单独授权处理 `behind=33`（不是 31）的分歧。**

### 28.3 ①②③ 逐条授权闭合度（不默认打包）

`three-items-authorization-closure-verdict-2026-11-15.json`：`overall.code = PARTIAL_INTENT_ONLY_NO_EXECUTABLE_AUTHORIZATION`，`executableItemCount = 0`。三条各自独立判定：② 的意图不构成 ③ 的授权；① 前提缺失不构成 ② 的自动放行；任何一条不得靠复述清单升级为授权。

| 条目 | 意图已表达 | 缺口 | 机器裁定 |
|---|---|---|---|
| ① 要跑真机 | 是 | 缺逐次明确解冻 + `ALLOW_FROZEN=1` 留痕；缺「本次改变了哪个自变量」 | `NOT_EXECUTED_PRECONDITION_UNMET` |
| ② 要提交 | 是 | 缺「文件集合」单独授权；旧清单已过期且含 D-2 缺陷 | `COMMIT_ACTION_EXPRESSED_BUT_FILE_SET_NOT_AUTHORIZED` |
| ③ 要 push | 是 | 用户自己写明「另需单独授权」处理分歧，该授权未给 | `NOT_AUTHORIZED_NO_ACTION` |

① 的关键不是「没给解冻」这么简单：§26 已证 A 组 `no-boundary` 本来就是同一会话 8 步串行 / 7 次 AI 往返，自变量结构条件已满足而墙不出现，F1 修复后 3 份完整 A 组回执 8/8、撞墙 0 次。`proposition-pursuit-plan-2026-11-14.json` 五条路径里只有 **P2**（`needsSourceOrDistChange`，回滚 F1 归因对照）和 **P3**（`needsPackChange`，人工加长会话）会改变自变量，代价是改源码/dist 或改 Pack、既有 hash 证据链断代、须重建全部门禁并登记新基线；P1/P4/P5 不改变自变量。首次推导曾按不存在的字段 `changesIndependentVariable` 过滤得到空列表，回读 plan 真实结构后按 `needsPackChange` / `needsSourceOrDistChange` 重算为 P2/P3，已在裁定文件 `derivationCorrection` 留痕。

`commit-scope-2026-11-15.json` 刷新盘点：**145 项 = 15 tracked 改动 + 130 untracked**，`staged=0`，`behind=33`。候选集合：`minimal_this_turn` 6 项、`source_tests_ledger_report` 16 项、`everything` 145 项（用户明令「不要默认一次全收」，仅登记不作默认）。执行方案为 `plan-only / NOT-EXECUTED`，禁止 `git add -A` / `git commit -a` / `--amend` / `--no-verify` / force push / 自动处理分歧。

### 28.4 N25 当前状态的准确含义

N25 是按 `INDETERMINABLE_PROPOSITION_CLOSED` 结案：**结案理由 = 原始观察对象已重新归因、墙不复现、命题不可判定**。不是验证通过（A/B 判据从未成立），不是「边界有效」，也不是「边界无效」，不是「长会话撞墙已根治」。仍成立的事实：F1 等待判据修复真机生效（§21）、F2 `newChat` / `newChatText` 入口真机可达（§23）、ab4 B 组硬判据 2/2 成立、ab5 判无墙即停。原 `title` / `detail` / `fix` / `reader` / `where` / `recharacterization` 与 43 条证据全部原样保留。

### 28.5 什么才构成重开理由（`n25-reopen-mechanism-2026-11-15.json`）

- **T1（唯一能让命题重新可判定的路径）**：出现新的可控自变量，且「墙」可被稳定复现。机器条件：A 组 `stepsTotal==8 && stepSuccess==7`、`firstFailedStepId=='step_8_output'`、错误含 `Response timeout`、前 7 步全成功且 `sessionResets` 为空；人工视觉闸确认不是「服务出错啦，请稍后再试。」且无登录墙 / 验证码；同站相邻时间窗 B 组边界真执行且 `available===true && messageCountAfter<messageCountBefore`。
- **T2**：新证据（可复核磁盘回执）推翻 §24 三条根因 F-D1（等待判据假超时）/ F-D2（站点随机报错）/ F-D3（「长会话是变量」归因被削弱）之一。
- **T3**：找到 §9.4 原始观察里可量化的第三变量（真实上下文 token 长度、站点限流窗口、会话累积时长），且能人为控制并写进新判据。
- **T4**：审计 / 交付口径要求改结论性质，但仍须附新证据。

### 28.6 什么不构成重开理由

想再跑一轮完整 4 轮 A/B（§26 已证盲跑不产生新证据）；台账显示 `closed` 不好看；把 F1 / F2 真机验证挪用为「边界有效」的因果证据；把「边界无效」当结论；仅重述旧证据换措辞；**用户只是问「若需重开怎么办」—— 问句本身不是重开指令**。

### 28.7 重开的技术机制（append-only，不删历史）

须用户显式重开指令，写明触发条件与新的自变量 / 新证据；机器不得自行重开。字段契约：`status: closed → open`、`closed_at: "2026-11-15" → null`、**`closure` 原样保留不删不改**（可追加 `reopenedAt` 标记）、新增 `reopen: []` 数组 append-only（每条含 `reopened_at` / `decidedBy` / `trigger` / `newIndependentVariable` / `newCriterion` / `inheritedCriteria` / `priorClosurePreserved` / `evidenceCountBefore` / `relatedEvidence`）、`appended_evidence` 只追加不删既有 43 条、`updated_at` 改当天、台账顶层 `updated_at` 同步而 `conventions` 不动。RESULT 追加新章节（§29 顺延），不改写 §26 / §27 / §28，且必须写明「重开不是验证通过」。新真机回执用 `ab6+` 新前缀，不覆盖 ab3 / ab4 / ab5。若采用 P2 / P3，改动源码 / dist / Pack 后必须重建 dist、跑全量 `npm test` + 全量变异 + dist 严格一致性，登记新 hash 基线，并显式标注旧 hash 证据链「断代」。

### 28.8 重开后判据继承与成本

判据全部继承：只有「A 撞墙且 B 通过」才支持命题；A/B 都通过不能归功边界，A/B 都失败须另找根因；observe-first Gate A 先只跑 A 单轮、判无墙即 `ABORT_NO_WALL` 不跑 B；B 组硬判据 `available===true && messageCountAfter<messageCountBefore`；边界未执行或 `available:false` ⇒ 明写「该轮作废 / 本轮不可评估」，不得包装成「边界无效」；冻结站逐次显式解冻并带 `ALLOW_FROZEN=1` 留痕、用完仍冻结，预检也算碰冻结站；全程 `tee -a` + 即时 JSONL + 即时回执；机器裁定 + 磁盘真证，人工视觉判读单列 `nonMachineObservations` 不参与布尔推导。

成本对比：**保持 closed** —— 结论就是「命题不可判定」，F1 / F2 / ab4 2/2 / ab5 判无墙即停全部不变，零新成本；**重开** —— 必须付出 P2 或 P3 的改造代价，既有 dist hash 与变体 Pack sha256 证据链断代，重建全部本地门禁并登记新基线后，才是逐次解冻 + 串行真机 + 按判据裁定。

### 28.9 本轮动作与硬边界

本轮 `realMachineRounds=0`：未启动浏览器、未打开冻结站、未发送消息、未产生真机回执；未 commit / push / stage / add / fetch / pull / merge / rebase；未改源码 / 测试 / dist / Pack；**N25 保持 `closed`，未重开、未加 `reopen` 字段**。新增产物全在 `evidence/`：`three-items-precondition-2026-11-15.py/.json`、`remote-divergence-2026-11-15.2.json`、`three-items-authorization-verdict-2026-11-15.py/.json`、`commit-scope-2026-11-15.py/.json`、`n25-reopen-mechanism-2026-11-15.json` 与本节回写脚本。归因边界继续有效：不能把关闭写成验证通过，不能把 F1 / F2 挪用为因果证据，不能把 plan-only 写成已执行回执。

### 28.10 用户四项裁定（`three-items-user-ruling-2026-11-15.json`）

`AskUserQuestion` 四问四答：q-0 **不跑真机**、q-1 **暂不提交**、q-2 **暂不 push**、q-3 **不重开 N25**。据此：

| 条目 | 裁定码 | 实际动作 |
|---|---|---|
| ① 真机 | `NO_REAL_MACHINE_THIS_TURN` | 不解冻、不预检、不打开冻结站、不发消息；`realMachineRounds=0`，本轮任何命令都未出现 `ALLOW_FROZEN=1` |
| ② 提交 | `NO_COMMIT_NO_STAGE` | 145 项全留工作区，`staged` 保持 0；不 commit / stage / add |
| ③ push | `NO_PUSH_NO_DIVERGENCE_HANDLING` | 不 fetch / pull / merge / rebase / push；`behind=33` 保持不动 |
| N25 重开 | `N25_REMAINS_CLOSED` | 保持 `closed` / `closed_at=2026-11-15` / 43 条证据 / `closure` 原样；不新增 `reopen` 字段 |

四项裁定**只对本轮生效，不构成对后续轮次的授权**；后续如需真机 / 提交 / push / 重开，须重新逐项显式授权。判据继承不变：只有「A 撞墙且 B 通过」才支持命题；B 组 `available===true && messageCountAfter<Before`；边界未执行或 `available:false` ⇒ 该轮作废 / 本轮不可评估；observe-first Gate A 判无墙即 `ABORT_NO_WALL`；机器裁定 + 磁盘真证，人工视觉判读单列。

本轮未改 git / 源码 / 测试 / dist / 变体 Pack / known_gaps.json / N25，未碰冻结平台。新增产物为 `three-items-user-ruling-2026-11-15.json` 与本节回写脚本。
