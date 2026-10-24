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

## 6. 已知缺口（截至 2026-10-25，全部如实记录，未修复）

| # | 缺口 | 影响 | 为什么现在不能修 |
|---|---|---|---|
| 1 | Gemini 的 `messageList` / `messageContent` 选择器**未在真机验证** | Gemini 的「等回复 + 取内容」链路仍是未验证状态 | 未登录的零状态会话页上没有消息气泡可测 |
| 2 | Gemini 真实**停止生成按钮**的 `aria-label` 未验证 | `isTyping()` 的停止按钮分支在 Gemini 上未验证 | 需要登录后真实发起一次生成才能看到 |
| 3 | 千问（qianwen）的 `messageList` 用了 `[class*="message"]` 这类**宽松选择器**，会连内容包装层一起命中 | 可能多计消息数、影响响应等待 | 改选择器需要真机 DOM 证据，现在没有；矩阵只把它标成「偏松」而没有断言其正确 |
| 4 | **只有 Gemini 的 fixture 是真实 DOM 快照**，其余 9 个平台仍是手写 mock | 其余 9 家一旦改版，矩阵同样可能假绿 | 需要逐个平台采集真实 DOM 快照（未做） |
| 5 | ChatGPT / Claude.ai 在**无登录态**下 L1 未验证（实测命中 bot check / HTTP 403） | 这两家的 DOM 契约目前无 L1 结论 | 需要已登录 profile（`--profile-dir=`）才能跑通 |
| 6 | 探针只覆盖 **3 个**平台（ChatGPT / Claude.ai / Gemini），矩阵覆盖 10 个 | 其余 7 家的真机回归还没做 | 探针按平台扩即可，不用改探针代码 |
| 7 | 10 个平台的 adapter 里，**只有 3 家**在真机上验证过 | 「矩阵 110/114 全绿」不等于「10 家都能用」 | 同上 |

> 表格里写「未验证」的项目**都不许**在别处被当成「已通过」引用。

---

## 7. 与路线 A/B 决策的关系

按 `memory/project_route_decision.md`，路线 A/B 拍板**唯一缺失的真证**是
「真机 3 平台回归 + 第一个外部用户」。

- 本手册的 L1/L2 是**前半段**（真机 3 平台回归）的执行规程；
- **后半段（第一个外部用户）不在这份手册的范围内**——它需要**外部人**，
  不是内部再跑一遍自动化；
- 因此即使 §5 的 `verify` 返回 0（记录一致且跑完），路线门禁**仍然是开启的**。
