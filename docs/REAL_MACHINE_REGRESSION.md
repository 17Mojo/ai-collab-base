# 真机回归操作手册（L1 自动化只读 + L2 人工真实发送）

> 适用版本：2026-10-25 起
> 相关工具：`chrome-extension/tests/real-machine/dom-contract-probe.mjs`（L1 探针）、
> `scripts/real_machine_regression.py`（记录与对账）
> 相关背景：`collaboration/results/RESULT-P1-REALMACHINE-REGRESSION-PREP-2026-10-25.md`

---

## 0. 为什么要有这份手册

2026-10-25 的真机实测抓到一个**真实产品缺陷**：Gemini 的生产 `sendButton` 选择器
在**真实站点上一个都命中不了**（中文界面），而当时的模拟层测试长期
「120/120 全绿」。

根因不是某一行选择器写错了，而是**两处结构性缺陷**：

| 结构性缺陷 | 表现 | 本轮修法 |
|---|---|---|
| 模拟层手抄了一份 `SELECTORS` | 生产选择器漂移了，模拟层**照样全绿** | 矩阵改为直接 import 生产 adapter 源码 |
| CI 指向已归档的测试文件并用 `\|\| echo` 吞掉失败 | 扩展测试**根本没跑**，CI 长期绿灯 | CI 改跑真实矩阵，失败即红 |

结论：**模拟层绿灯不能替代真机回归**。这份手册规定真机回归怎么做、留什么证据、
谁负责判定，以及「跑过」和「没跑」在机器层面怎么区分。

---

## 1. 两层定义，以及它们**不可互相替代**

| 层 | 谁执行 | 是否需要登录 | 是否真实发送 | 产出证据 | 能证明什么 | **不能**证明什么 |
|---|---|---|---|---|---|---|
| **L1** 自动化只读 | 脚本 | 否（未登录时多半撞登录墙） | **否** | 探针 JSON 判定 | 生产 adapter 在**真实 DOM** 上还能找到输入框/发送按钮 | 不能证明能发消息、能等回复、能取回内容 |
| **L2** 人工真实发送 | 人 | **是** | **是** | 截图 + 页面控制台 + 记录条目 | 一次完整的 Pack 执行在真实账号上跑通 | 不能证明「外部用户会用」 |
| 第一个外部用户 | 外部人 | 是 | 是 | 外部使用反馈 | 产品对**非本团队用户**成立 | —— |

**三层是递进关系，不可跳级**：

- L1 全绿 **≠** L2 全绿（L1 只读，不碰额度，不等回复）；
- L1 + L2 全绿 **≠** 「第一个外部用户」——路线 A/B 决策门禁缺的恰恰是最后一环，
  因此 `scripts/real_machine_regression.py` **永远不会**把门禁判为关闭，
  每次 `verify` 都会打印这句话。

---

## 2. 前置条件

| 条件 | L1 | L2 | 说明 |
|---|---|---|---|
| 真实 Chrome | 建议 | 必须 | `--channel=chrome` 用系统装的 Google Chrome；默认用 Playwright 自带的 chromium |
| 网络可达目标站点 | 必须 | 必须 | 直连即可，不需要代理 |
| 已登录的浏览器 profile | 不需要 | **必须** | 用 `--profile-dir=` 指向 profile 的**副本**；直接用主 profile 会撞 Chrome 的 profile 锁 |
| 界面语言 | **每个目标语言各跑一次** | 同上 | 见 §3.4「语言相关的漂移」 |
| 账号额度 | 不消耗 | 消耗 | L1 默认只读（不注入文本、不点发送） |

---

## 3. L1：自动化只读探针

### 3.1 探针在做什么（以及不做什么）

探针用 esbuild 把 `src/platforms/<platform>-adapter.js` 连同依赖打成一个 IIFE，
注入**真实站点**的页面，然后在页面里 `new Adapter().getChatInput()` /
`getSendButton()`——跑的是**生产代码路径**（adapter 自己的方法 → 自己的
`SELECTORS` → 自己的 `findElement`），**不是抄一份选择器表**。

探针**默认只读**：不注入文本、不点发送、不消耗额度。
`--probe-send-button` 会额外在页面上找发送按钮并**与生产选择器比对**，
但**不会点击**。

### 3.2 命令

```bash
cd chrome-extension

# 基础跑法（3 个平台，Playwright 自带 chromium，只读）
node tests/real-machine/dom-contract-probe.mjs \
  --out=../collaboration/results/real-machine-runs/evidence/L1-gemini-en.json

# 真实 Chrome + 中文界面 + 发送按钮比对
node tests/real-machine/dom-contract-probe.mjs \
  --platform=gemini --channel=chrome --locale=zh-CN --probe-send-button \
  --out=../collaboration/results/real-machine-runs/evidence/L1-gemini-zh.json

# 用已登录 profile（persistent context），三个平台一次跑完
node tests/real-machine/dom-contract-probe.mjs \
  --profile-dir=/tmp/rm-profile --locale=zh-CN \
  --out=../collaboration/results/real-machine-runs/evidence/L1-zh-loggedin.json
```

### 3.3 参数

| 参数 | 含义 |
|---|---|
| `--platform=chatgpt,claude,gemini` | 只跑指定平台（默认三个都跑） |
| `--channel=chrome` | 用系统装的 Google Chrome（默认用 Playwright 自带 chromium） |
| `--locale=zh-CN` | 界面语言。**必须逐语言跑**，理由见 §3.4 |
| `--profile-dir=<path>` | 用已有 profile 目录（persistent context），可带上登录态 |
| `--probe-send-button` | 额外比对「页面上有发送按钮，但生产选择器命中不了」这种漂移（不点击） |
| `--headed` | 有头模式（需要肉眼确认时用） |
| `--out=<path>` | 把判定结果写成 JSON（**证据文件**，L1 记录必须挂它） |
| `--timeout=<ms>` | 页面导航超时（默认 30000） |
| `--composer-wait=<ms>` | 等待 composer 挂载的最长时间（默认 15000） |

### 3.4 语言相关的漂移（**两个语言都要跑**）

DOM 漂移**随界面语言变化**。2026-10-25 实测 Gemini 发送按钮内层 `<button>` 的
`aria-label`：

| 界面语言 | 实测 aria-label | 旧选择器 `button[aria-label*="Send"]` |
|---|---|---|
| 中文（zh-CN） | `发送` | **0 命中** ← 缺陷 |
| 英文（en-US） | `Send message` | 1 命中（**侥幸**） |

也就是说：旧选择器在英文界面能过、在中文界面完全失效。**只跑默认语言就看不见
这类漂移**——这正是本轮缺陷长期潜伏的原因之一。

修复后，两个语言都靠类名选择器命中（`gem-icon-button.send-button button`、
`.send-button button`），并补了 `button[aria-label="发送"]`。

### 3.5 判定口径

| outcome | 含义 | 算不算失败 | 记什么 |
|---|---|---|---|
| `pass` | 生产 adapter 在真实 DOM 上找到了输入框 | —— | L1 `pass` |
| `login_wall` | 命中登录墙 | **不算**失败（环境限制） | L1 `unverified` + reason |
| `bot_check` | 命中人机校验/机器人拦截（实测 ChatGPT / Claude.ai 无登录态时是 HTTP 403） | **不算**失败 | L1 `unverified` + reason |
| `no_composer` | 页面加载了但没有 composer | 算失败 | L1 `fail` |
| `unreachable` | 页面都打不开 | 算失败 | L1 `fail` |
| `adapter_build_failed` | 生产 adapter 打包失败 | 算失败 | L1 `fail` |

「未验证」不计为失败，是因为它是**环境限制**而不是回归结论；但它也**不构成**
DOM 契约通过——所以它必须记成 `unverified`，不能记成 `pass`。
`scripts/real_machine_regression.py` 会交叉核对证据文件：探针写着 `login_wall`，
记录却写 `pass`，判为**记录不一致**（退出码 1）。

### 3.6 发送按钮漂移的判读（`--probe-send-button`）

| 探针输出 | 含义 |
|---|---|
| `发送按钮：找到 <button> aria=…（命中：…）` | 生产选择器命中，正常 |
| `发送按钮：**adapter 选择器已漂移**——页面上存在发送按钮类元素…但生产 adapter 一个都没命中` | **产品缺陷**（不是站点行为变化），按缺陷处理 |
| `发送按钮：页面上未发现发送按钮类元素` | 站点形状可能变了，**需人工确认**，不能直接算 adapter 的结论 |

---

## 4. L2：人工真实发送

### 4.1 前置

- 一个**已登录**的平台账号（浏览器里能直接打开会话页）；
- 扩展已构建并加载到 `chrome://extensions`（`cd chrome-extension && npm run build`，
  然后「加载已解压的扩展程序」选 `dist/` 目录）；
- 准备好要发的 Pack（`packs/examples/*.json`）。

### 4.2 步骤（每个平台各做一遍）

1. **开新会话**：在目标站点新开一个空会话（避免历史消息干扰消息计数）。
2. **装扩展**：`chrome://extensions` → 开发者模式 → 加载已解压的扩展 → 选 `dist/`。
3. **确认 adapter 命中**：在目标页面打开 DevTools Console，应看到
   `[Prompt Pack] Using adapter: <platform>`。**没有这行**说明 adapter 都没挂上，
   后续步骤无意义。
4. **触发 Pack**：从扩展弹窗触发目标 Pack（或按 Pack 定义的触发方式）。
5. **肉眼确认三件事**（缺一不可）：
   - 文本**确实进了输入框**（不是空发送）；
   - **确实发出去了**（会话里出现用户消息气泡）；
   - **回复被取回来了**（Pack 输出里有 AI 回复内容，不是超时/空）。
6. **留证据**：
   - 会话页整页截图（**含时间戳**，如系统状态栏时间）；
   - DevTools Console 的输出（可复制粘贴存成 `.log` 或 `.md`）；
   - Pack 执行结果（成功/失败/耗时）。
7. **登记记录**（§5）。

### 4.3 判据

| 结论 | 条件 |
|---|---|
| L2 `pass` | 第 5 步三件事全部成立，且证据文件（截图 + console 输出）齐全 |
| L2 `fail` | 任一件事不成立；**必须**写清是哪一步、什么现象 |
| L2 `unverified` | 环境不满足（无登录态、账号额度耗尽、网络问题）；**必须**写原因 |
| L2 `not-run` | 还没跑到；**必须**写原因 |

> L2 的 `pass` 必须附**可机检的证据文件**（截图或日志的实际路径），
> `scripts/real_machine_regression.py` 会检查文件**真实存在**。

### 4.4 用观测器做 L2（**推荐**：截图证明不了「正文取回来了」）

§4.2 的肉眼流程有一个**证明不了的东西**：界面上有字，不等于 adapter
真的取到了那段字。而「取回来的正文非空」恰恰是 Pack 能不能用的关键。

`tests/real-machine/l2-send-observer.mjs` 就是补这一段的：

- **人**在浏览器里输入并**手动点发送**；
- **脚本**全程只读 DOM，**不注入文本、不点发送**
  （「探针永不发送」是本仓红线，L1 探针必须无副作用）；
- 脚本**并行跑生产代码里的 `waitForResponse`**，把结果与采样时间线一起写成
  可机检的 JSON。

```bash
cd chrome-extension
# 单平台；--profile-dir 指向已登录的浏览器 profile（必须是持久 profile）
node tests/real-machine/l2-send-observer.mjs --i-will-send \
     --platform=gemini --profile-dir=/tmp/rm-profile

# 全部 10 个平台 × 中文
node tests/real-machine/l2-send-observer.mjs --i-will-send --profile-dir=/tmp/rm-profile
```

> `--i-will-send` 是硬闸门：没有它工具拒绝启动。
> 误跑一次就是在真站上发出一条真实消息、并在一个真实对话里。

产出的 JSON 里 `verdict` 直接回答「生产的等待逻辑在这条真实时间线上会不会成功」：

| 字段 | 含义 | 读法 |
|---|---|---|
| `countGrew` | 消息计数涨了 | false ⇒ 取消息列表的选择器有问题 |
| `typingCleared` | 生成中状态解除过 | 恒 true ⇒ 打字指示器选错，必然超时 |
| `contentNonEmpty` | 页面上取到的正文非空 | false ⇒ 看到了字但没取到 |
| `productionContentNonEmpty` | **生产代码自己**取到的正文非空 | false ⇒ 等待过了但回复是空的 |
| `wouldResolve` | 按生产口径重放时间线会不会成功 | false ⇒ 这条链路今天走不通 |
| `consistent` | 生产实际结果与重放是否一致 | false ⇒ 生产实现里有别的因素，值得单独看 |

登记方式与 §5.1 相同（`--evidence-file` 指向这个 JSON）。

**残留风险（必须记着）**：见 §6.2 的 #3——Kimi/ChatGLM 的真实「生成中」指示器
仍未验证。若收窄后的选择器都不命中，`isTyping()` 恒为 false，
`waitForResponse` 可能**中途提前返回**（拿到半截回复）。
观测器的 `wouldResolve` 只回答「会不会成功」，**答不了「会不会太早成功」**——
后者要靠人看时间线里 `contentNonEmpty` 是在第几个样本才变 true 的。

---

## 5. 记录与对账（`scripts/real_machine_regression.py`）

这个脚本**不做检测**，只做**记录与对账**——把「没跑」和「跑过」在机器层面区分开。

### 5.1 用法

```bash
# 1) 建一条 run 记录
python3 scripts/real_machine_regression.py init \
  --run-id RMR-2026-10-25-01 \
  --platforms chatgpt,claude,gemini \
  --locales zh-CN,en-US \
  --operator <执行人>

# 2) 登记 L1（证据文件 = 探针 --out 出来的 JSON）
python3 scripts/real_machine_regression.py record \
  --run-id RMR-2026-10-25-01 \
  --layer L1 --platform gemini --status pass --locale zh-CN \
  --evidence "探针判定 sendButtonVerdict=ok" \
  --evidence-file collaboration/results/real-machine-runs/evidence/L1-gemini-zh.json

# 3) 登记 L2（人工跑完）
python3 scripts/real_machine_regression.py record \
  --run-id RMR-2026-10-25-01 \
  --layer L2 --platform gemini --status pass \
  --evidence "真实发送成功，回复已取回" \
  --evidence-file collaboration/results/real-machine-runs/L2-gemini.png

# 4) 对账
python3 scripts/real_machine_regression.py verify --run-id RMR-2026-10-25-01
python3 scripts/real_machine_regression.py list
```

记录落盘在 `collaboration/results/real-machine-runs/<run-id>.json`，
L1 探针的证据 JSON 放在同目录的 `evidence/` 子目录下。

### 5.2 对账规则

| 规则 | 触发的错误 |
|---|---|
| `pass` 必须有 `--evidence` **和** `--evidence-file` | 结论没有出处 |
| 证据文件必须**真实存在** | 结论指向不存在的文件 |
| 探针证据的 `outcome` 与记录状态必须一致 | 证据说未验证、记录说通过 |
| `unverified` / `not-run` 必须写 `--reason` | 没跑却没写为什么 |
| L1 记录必须带 `--locale` | 漏掉语言相关的漂移 |
| 每个平台都要有 L1 **和** L2 条目（L2 可以是 `not-run`） | 平台覆盖不全 |
| L2 记 `pass` 时，同平台的 L1 必须是 `pass` | 跳过 L1 直接宣称通过 |
| 同一 (layer, platform, locale) 不得重复 | 重复登记（后写覆盖先写） |

### 5.3 退出码

| 码 | 含义 |
|---|---|
| 0 | 记录一致**且**跑完（L1/L2 全 pass） |
| 1 | 记录**不一致**（有硬错误） |
| 2 | 记录一致但**没跑完**（还有 L2 是 `not-run`/`unverified`） |

`verify` 每次都会打印路线门禁提示，说明这份记录**不构成**「第一个外部用户」证据。

---

## 6. 已知缺口（截至 2026-10-25 晚，如实记录；已关闭的与仍开着的分开列）

### 6.1 本轮已关闭的缺口

| 原 # | 缺口 | 怎么关的 |
|---|---|---|
| 4 | 只有 Gemini 的 fixture 是真实 DOM 快照 | **7/10 平台已采到真实快照**（ChatGLM / Gemini / Kimi / LongCat / 千问 / 文心一言 / 元宝），脱敏后入库并有守护测试 |
| 6 | 探针只覆盖 3 个平台 | 探针扩到 **10 个平台**，并跑出可达性体检表（pass 7 / unverified 3 / fail 0） |
| 7 | 只有 3 家在真机上验证过 | 7 家有真实快照 + 10 家都有 L1 结论（含 3 家的「未验证」结论本身） |
| 2 | 千问（qianwen）的 messageList 三条选择器在落地页上**命中 0 个** | 做了**资产普查**（56 个资源 / 15.45 MB，含懒加载 async chunk）：旧选择器里的 `.response-content` / `.prose` / `chat-item` / `.typing-indicator` / `.message-content` **在千问自己的产物里根本不是类名**（前者是 URL 查询参数，后者是 Tailwind `max-w: prose` 与 prosemirror 库，其余是 CSS 变量）⇒ 它们是照别的站点抄来的，在千问上永远命中 0 个。已按**千问自己产物里的真实结构**重写（CSS 后代选择器 + React 渲染代码 + 站点自己的文本选择功能 `supportedSelectors` 三个独立来源互相印证），并配 12 条契约测试 + 6 条变异检查（18/18 被杀死） |
| — | 平台名单散落 4 处（矩阵 / 探针 / content-script / multi-platform-executor） | 收敛到 `tests/platforms.mjs` 单一事实源，并用 `tests/platform-registry.test.mjs` 双向对账 |
| — | 模拟层矩阵 110/114 全绿，却漏掉 4 个真机缺陷 | 新增两条**可机检的不变量**（「无会话即无消息」/「空闲即不忙」），并把「发现漂移的能力」本身纳入矩阵 |
| — | 千问的 mock fixture 是**照着旧选择器写的假 DOM**，矩阵因此「因为错的原因而绿」 | 按千问真实结构重写，并把发送按钮的 aria-label 故意改成英文——这样删掉稳定属性那条选择器后矩阵**也会红**，矩阵本身就守住了「不依赖本地化文案」 |
| 6a | **Pack 执行链路本身三段全断**（准备外部用户试用材料时逐段查出来的）：<br>① popup 用不存在的 `pack.id` ⇒ 渲染出 `data-id="undefined"`；<br>② 执行器从来没拿到过 Pack（`loadPack()` 定义了却没人调用，而 storage 才是事实源）⇒ 每次执行都是 "Pack not found"；<br>③ 后台发 `SEND_TO_AI`，内容脚本**没有分支处理它** ⇒ AI 步骤拿到 `undefined` 却仍被当成「成功」⇒ Pack「执行成功」但产物是空的 | 三处都修了，并加了 `tests/extension-wiring.test.mjs`（10 条静态+行为测试）与 5 条变异。**注意：这不等于「Pack 在真机上跑通了」**——只等于「链路接上了」，见 §6.2 的 #5 | — |
| 6b | **AI 步骤发到哪儿**没定义：后台用 `chrome.runtime.sendMessage` 广播 ⇒ 扩展里**每个**内容脚本都收到 ⇒ 用户开 3 个 AI 页面时提示词在 3 个页面里各发一次 | 改为「已知目标标签页 ⇒ `chrome.tabs.sendMessage` 精确投递；不知道才广播并标明是广播」，popup 负责把当前标签页 id 告诉后台（3 段各一条测试 + 3 条变异） | — |
| 6c | **外部用户根本走不到「导入 Pack」那一步**：popup 里没有导入入口（只有一个「请先导入 Pack」的提示），而设置页里打开 Pack 编辑器的 URL（`getURL('public/pack-editor.html')`）在**构建产物里 404**（产物里只有扁平的 `pack-editor.html`）⇒ 点了就是「文件不存在」 | popup 加「📥 导入 / 管理 Pack」按钮；静态资源复制逻辑收敛到 `static-assets.cjs` 一份，产物里**两种布局都保留**（`pack-editor.html` 与 `public/pack-editor.html`），并加测试逐个核对代码里 `getURL` 指到的页面在产物里真的存在 | — |
| 6d | **manifest 的 host 模式漏了 `www.` 变体**：写的是 `https://qianwen.com/*`，而真站是 `https://www.qianwen.com/`。Chrome 的 host 匹配里 `qianwen.com` **只等于它自己**（`*.` 才是通配）⇒ 内容脚本**根本没注入** ⇒ 那个页面上扩展等于没装 | manifest 补齐 `www.` 变体，且 `host_permissions` 与 `content_scripts.matches` **收敛成同一份清单**（不许各写一份）；`tests/external-user-path.test.mjs` 按 Chrome 的 host 匹配规则逐个平台核对，并加一条「构建产物的 manifest 必须由 `manifest.json` 生成」 | — |
| 6e | **后台在 service worker 里调了页面侧的 `adapter.detect()`**：`detect()` 读 `window.location.hostname`，而 MV3 的 SW 里 `typeof window === "undefined"` ⇒ `ReferenceError` 抛在 `chrome.runtime.onMessage` 处理器里 ⇒ **整个处理器挂掉 ⇒ 永远不 `sendResponse`** ⇒ `currentConfig` 恒为 null ⇒ **改之前，扩展在任何站点上都拿不到适配器** | 后台改成**从发消息过来的那个标签页的 URL** 认平台（`hostOf()` + 主机名判定），不再调页面侧代码；`detect()` 仍保留给页面侧用。守护覆盖**全部 10 个平台**（别只测一个），外加一条「不是 AI 站点的 URL 不该被认成任何平台」（防把「什么都认」测成通过） | — |
| 6f | **导入界面比后台更严**：前端只认 `{packs:[...]}`，后台两种形状都收 ⇒ 照指南导入 `packs/examples/external-user-smoke.json`（单个 Pack）时，前端直接报「文件格式错误」⇒ 连「合并 / 覆盖」都出不来 | 前端只做**语法**检查，「什么算 Pack」**只有后台一个判定方**（两个判定方 = 迟早漂移）。守护两条：单个 Pack 文件不该被挡在门外；**真的不是 JSON 仍然要报错**（防把闸门拆成没有闸门） | — |
| 6g | **导入成功后成功标志被冲掉**：先报「导入成功: N 个 Pack」，**再**刷新列表——刷新把状态栏改写成「已加载 N 个 Pack」⇒ 指南承诺的成功标志**一闪就没了** | 改成**先刷新列表、再报导入成功**；守护断言状态栏最终停在指南承诺的那句话上 | — |
| 6h | **失败被跨层吞掉**：内容脚本如实回 `{success:false, error}`，执行器却原样返回并无条件置 `stepResult.success = true`，后台再一律回 `success:true` ⇒ popup 显示「执行成功」而产物是空的 | 执行器在 try/catch **外**校验 AI 步骤回执（失败就抛，且错误信息不被「消息没送到」再包一层）；后台看 `result.status === "failed"` 时回 `{success:false, error}`。守护两条：内容脚本报失败 ⇒ 整个 Pack 必须失败；**内容脚本成功时 Pack 必须成功**（防这条永远失败） | — |
| 6i | **注入只改了 DOM，没进站点的编辑器模型**：千问用 Slate，内容存在框架自己的模型里，`execCommand` 只动 DOM ⇒ 站点读到「用户没输入」⇒ **发送按钮保持 disabled** ⇒ 点它等于没点 ⇒ 提示词永远留在输入框里 ⇒ 必然超时。**更隐蔽的一层**：`injectTextSmart` 把 `role="textbox"` 排在 `isContentEditable` **前面**，而千问的编辑区正好带 `role="textbox"` ⇒ 千问走的是纯 execCommand 那条路 ⇒ **把修复写在 `injectIntoContentEditable` 里对千问是死代码** | 新增 `src/platforms/slate-editor.js`（**模型感知**的注入：清空 → 插入 → **校验模型文本**，收不到就抛错而不是假成功）；`injectTextSmart` 改 async 并把 Slate 分支**排到 `role="textbox"` 前面**。替换语义靠「DOM 全选 → 等选区同步进模型 → `beforeinput(deleteContentBackward)` → 插入」，等待用 `setTimeout(0)`（**不用 `requestAnimationFrame`**：它在后台标签页里不触发，会把 Pack 流程卡死） | — |

> **#2 关掉的到底是什么、没关掉的是什么**（别把「关了」当成「验证过了」）：
> 关掉的是「选择器引用了千问上不存在的类名」这个**确定性缺陷**——现在每一条选择器
> 都能在千问自己的产物里找到出处，且有可复算的普查清单兜底。
> **没**关掉的是「它在真机上确实命中」——那仍然是缺口 #1 / #8，需要 L2。
> 普查工具：`node tests/real-machine/qianwen-asset-census.mjs`
> （只读抓站点自己的 JS/CSS，**不注入、不点击、不发送**）。

> **6d～6i 是从哪儿查出来的**：它们不是 L1/L2 探针查到的，而是
> **2026-10-26 的「外部用户排演」**（W-D1：照着《第一次试用指南》以第一次用的
> 人的身份走一遍，每一步记下卡住的地方）查出来的。
> 这个来源本身就说明一件事：**L1 探针只覆盖「能不能找到输入框」，
> 找不到「外部用户会卡在哪一步」**——那 5 个断点里，
> 有 4 个（6d/6e/6f/6g）在扩展的模拟层与真机探针里**全都是绿的**。
> 结果文件：`collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md`。
>
> **6i（编辑器模型）已经过了真机复验**，但复验的是**注入环节**，
> 不是「点发送 → 等回复」⇒ 缺口 #5（L2）并没有因为 6i 而缩小。

### 6.2 仍然开着的缺口

| # | 缺口 | 影响 | 为什么现在不能修 |
|---|---|---|---|
| 1 | 7 家已采样的平台，其**消息气泡选择器**仍未在真机上验证 | 落地页上没有会话，只能证明「不误命中界面外壳」，**证不了「能命中真气泡」**——选择器写错和选择器正确在落地页上表现一模一样 | 需要已登录 profile + 一次真实发送（L2） |
| 1b | **千问的消息气泡选择器**虽已按站点产物重写，**仍未在真机跑过** | 同 #1。若站点实况与产物有出入（灰度版本、按账号下发不同 chunk），仍会漏命中 | 同 #1 |
| 3 | Kimi / ChatGLM 的**真实「生成中」指示器**未验证 | 收窄后的选择器若都不命中，`isTyping()` 恒为 false ⇒ `waitForResponse` 可能**中途提前返回**（拿到半截回复） | 需要登录后真实发起一次生成 |
| 8 | **千问的「生成中」信号**（「停止回答」按钮 / 「接收中」点点点卡片）同样只是**从站点产物推导**，未在真机跑过 | 同 #3：`isTyping()` 若恒为 false ⇒ 拿到半截回复；若恒为 true ⇒ 永远等不到 | 同 #3 |
| 4 | ChatGPT / Claude.ai / DeepSeek 三家未采到真实快照 | 这三家的 DOM 契约仍无 L1 结论 | ChatGPT / Claude 撞 bot check（HTTP 403），DeepSeek 撞登录墙——都不是代码问题 |
| 5 | L2（真实发送后等回复）**尚未跑过任何一次** | 缺口「回复等待链路」仍未验证 | 需要人 + 已登录 profile；观测器已交付（见附录 A）。<br>**2026-10-26 更新**：10 个平台的 L2 已逐个登记为 `not-run` 并写明原因（而不是留空），`verify` 因此能区分「没跑」与「跑了但没过」。**第 1 轮**（千问 zh-CN + Gemini en-US）仍需**人在机器前**登录并点发送 |
| 6 | 后台↔内容脚本的**消息协议**还剩一个洞：`multi-platform-executor.js` 发 `GET_LATEST_RESPONSE` 无人处理，且它读 `pageState.isTyping`，而 `getPageState()` 根本不返回该字段 | 该模块**没有任何模块 import 它** ⇒ 是死代码，不在运行路径上（生产链路用的 `SEND_TO_AI` 已修，见 §6.1 的 6a） | 死代码要么删、要么接线，都属于「运行时收敛」这件事，不在本工单范围 |
| 7 | 真实快照是**冻结基线**，守不住「站点改版」 | 快照失效=一条待办信号，不是 CI 失败 | 这是刻意的分层：改版由 L1 探针（打真站）负责；快照只守「我们对真机 DOM 的理解被记录下来了，而且自洽」 |
| 9 | **Python 校验器与 JS 运行时对「步骤类型」的说法不一致**：`ai_collab/pack/schema_v2.py` 的 `StepType` 是 `local/analysis/generation/validation/fusion/tracking`，而 JS 执行器只认 `local` 和 `ai` | 一份按 Python 口径写的 Pack（`type: "generation"`）在 JS 侧会直接抛 `Unknown step type`；反过来 `type: "ai"` 的 Pack 过不了 Python 校验 | 两套口径要统一（要么 Python 侧加 `ai`，要么 JS 侧映射），这属于**契约变更**，不在本工单范围 |
| 10 | `packs/examples/` 下的 17 个示例 Pack **没有一个**能通过 Python 校验器 | 「照着示例写一个 Pack」这条路对使用者是断的——示例本身不合规 | 同 #9，且示例 Pack 本身要重写（本次只新增了一个走 JS 运行时的自检 Pack `external-user-smoke.json`，它同样过不了 Python 校验器） |
| 11 | `src/background/pack-storage-manager.js` 依赖一个**并不存在**的后端 API（本地 FastAPI 服务尚未实现） | 走那个模块的 Pack 管理路径直接不可用；当前实际可用的是「storage 既是事实源、也是唯一事实源」这条路径 | 后端未实现，属于路线 A/B 之外的工作 |
| 12 | **「提示词进到编辑器**模型**」只对 Slate（千问）验证过**：Claude.ai 是 ProseMirror、元宝是 Quill，各自的模型机制不同 ⇒ 「只改 DOM 不改模型」这个坑**在别的框架上同样可能存在，但没验过** | 若某个平台也是「文字进了框、发送按钮却一直是灰的」，那和 6i 是同一类问题，但本轮的修复**不覆盖它** | 每个框架要单独做一次模型级复验（探针已备好，见附录 A 的 `injection-path-probe.mjs`；非 Slate 平台它目前只能给 **DOM 级**证据，`modelLevelVerifiable:false`）——需要人拿已登录 profile 逐个平台跑 |
| 13 | **真人外部用户（W-D2）尚未开始**：2026-10-26 做的只是「排演」——排演者能读源码，所以它只能证明「材料与代码自不自洽」，**证明不了「真人会用」** | 路线 A/B 决策门禁的最后一环仍然空着 | 需要**一个真人外部用户**（不是本团队的人）按《第一次试用指南》走一遍 |

> 表格里写「未验证」的项目**都不许**在别处被当成「已通过」引用。
> 特别注意 #1 与 #1b：真实快照已入库 ≠ 消息气泡选择器已验证；
> 资产普查证明了「选择器有出处」，**证明不了**「真机上命中」。
> #3 与 #8 同理：结构推导 ≠ 行为验证。
> **#12 同理**：千问（Slate）的提示词进过模型 ⇒ 别的框架**没**进过；
> 而「扩展装上了、输入框找得到」**证明不了**「提示词进了站点自己的模型」——
> 2026-10-26 真机实测里，这两件事在千问上恰恰是**分开**的：
> 改前 DOM 里有字，模型里没有，发送按钮一直是灰的。

---

## 7. 与路线 A/B 决策的关系

按 `memory/project_route_decision.md`，路线 A/B 拍板**唯一缺失的真证**是
「真机 3 平台回归 + 第一个外部用户」。

- 本手册的 L1/L2 是**前半段**（真机 3 平台回归）的执行规程；
- **后半段（第一个外部用户）不在这份手册的范围内**——它需要**外部人**，
  不是内部再跑一遍自动化；
  （材料已备好：`docs/EXTERNAL_USER_ONBOARDING.md` 是一页说明书，
  `collaboration/results/external-user/` 是记录格式与模板；
  **缺的只是「人」**——没人跑过之前，这一栏仍然是空的。）
- 因此即使 §5 的 `verify` 返回 0（记录一致且跑完），路线门禁**仍然是开启的**。

---

## 附录 A：本仓新增的真机回归工具

| 工具 | 干什么 | 是不是无副作用 |
|---|---|---|
| `tests/platforms.mjs` | 10 平台的**单一事实源**（矩阵 / 探针 / 观测器 / 快照都从这里取） | 是（纯数据） |
| `tests/platform-registry.test.mjs` | 登记表 ↔ 生产 adapter ↔ content-script ↔ manifest ↔ fixture 的**双向**对账 | 是（只读） |
| `tests/real-machine/snapshot-capture.mjs` | 采真实 DOM 快照 + 判定两条不变量 + 脱敏 | 是（只读） |
| `tests/real-machine/sanitize.mjs` | 快照脱敏（邮箱 / 手机号 / 令牌 / 事件属性 / script） | 是（纯函数） |
| `tests/real-machine/message-model.mjs` | 「无会话即无消息」/「空闲即不忙」两条不变量的判定 | 是（纯函数） |
| `tests/real-machine/qianwen-asset-census.mjs` | **站点资产普查**：只读抓站点自己的 JS/CSS，产出「哪些 token 真的是站点类名」的清单（千问选择器的依据） | 是（只 GET 静态资源，**不注入、不点击、不发送**） |
| `tests/real-machine/qianwen-contract.test.mjs` | 千问 DOM 契约测试：拿**站点自己产物里的结构**当契约，跑**生产 adapter 源码** | 是（jsdom） |
| `tests/real-machine/l2-send-observer.mjs` | L2 观测器：**人发消息，脚本只读**，并并行跑生产 `waitForResponse` | 是（**不注入、不点发送**） |
| `tests/real-machine/l2-model.mjs` | 观测器的判定口径（纯函数，可单测） | 是（纯函数） |
| `tests/real-machine/mutation-check.mjs` | **变异检查**：改坏被守护的代码，对应测试必须变红 | 是（在临时副本上跑） |
| `tests/run-tests.mjs` | 单测入口（Node 18+ 通用；`node --test` 的三种写法在 Node 20/23 上各有一坑） | 是 |
| `tests/ci-wiring.test.mjs` | 守护「CI 确实在跑扩展测试」——**不许** `|| echo` 吞掉失败 | 是（只读） |
| `tests/extension-wiring.test.mjs` | **扩展内部接线**：popup ↔ 后台 ↔ 内容脚本（消息类型双向对账 + 真的跑一次 SEND_TO_AI + Pack 找得到 + 标签页定向 + 产物里页面真的存在） | 是（jsdom + 临时目录） |
| `tests/external-user-path.test.mjs` | **外部用户走的那条路**：manifest 的 host 覆盖 / 后台能认出平台 / 失败不被吞 / 导入闸门只有后台一个判定方 | 是（jsdom + 临时目录） |
| `tests/editor-injection.test.mjs` | **编辑器模型**守护：注入后模型收到文本、发送按钮解禁（不靠 `execCommand`）、替换而非追加、收不到就抛错 | 是（jsdom + 站点仿真） |
| `tests/helpers/slate-site.mjs` | 按真机实测结构仿真的**站点行为**（模型与 DOM 分离、发送按钮读模型、占位符是叶子的子节点）——矩阵 / 接线测试 / 注入守护共用**同一份** | 是（仿真） |
| `tests/real-machine/injection-path-probe.mjs` | **注入链路探针**：走**生产链路**（SW → 内容脚本 → 注入）验「提示词进了站点编辑器**模型**」 | 否——**会往真实站点的输入框写字**（不发送）；必须显式 `--i-will-inject`；不登录；不进 CI 硬门禁 |
| `static-assets.cjs` | 静态资源复制（**唯一一份**实现，产物里保留扁平与 `public/` 嵌套两种布局） | 是（复制文件） |

### A.1 为什么要做变异检查

一套全绿的测试**什么都不能证明**，除非你能证明：
「把被守护的那处代码改坏，对应的测试会变红」。

本仓的教训很具体：110/114 全绿的模拟层矩阵，掩盖了 4 个真机上才暴露的生产缺陷
（文心一言/元宝的消息数被界面外壳撑大、Kimi/ChatGLM 的 `isTyping()` 恒为 true
⇒ 每次发送必然 60 秒超时）。绿不是因为对，是因为没测到。

`mutation-check.mjs` 把「守护关系」本身变成可执行的：每条变异对应一个**具体缺陷**，
要求**指定的那条测试**因此报错。变异在临时副本上进行，工作区一个字节都不动。

```bash
cd chrome-extension && node tests/real-machine/mutation-check.mjs
```

### A.2 单测怎么跑

```bash
cd chrome-extension && node tests/run-tests.mjs
```

不要用 `node --test`（自动发现）——它会扫进 `tests/playwright/node_modules`
里的第三方测试，本机实测直接卡死。也不要写 `node --test tests/xxx/`
（Node 23 报 `MODULE_NOT_FOUND`）或 `node --test "tests/**/*.test.mjs"`
（要 Node 21+，CI 钉的是 20）。`run-tests.mjs` 三种坑都绕开了。
