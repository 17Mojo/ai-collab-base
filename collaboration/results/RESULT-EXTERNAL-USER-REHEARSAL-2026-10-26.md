# RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26

**状态**: completed
**任务**: W-D1 排演（本次拆成 6 个缺陷工单，见第二节）
**执行**: Claude Code（AGENT_EXEC）　**复核**: CodeArts（AGENT_TEST）
**分支**: `feat/realmachine-coverage-expand`（PR #5，基线 `main` @ `71c9eac`）
**日期**: 2026-10-26（缺陷 #6 的修复与真机复验跨到 2026-10-27）

---

## 一句话结论

照着《第一次试用指南》做一遍**排演**，查出 **6 个确定性的断点**——每一个都让外部用户
**走不到第 5 步**（把提示词发出去）。6 个全部已修，并为每个补了**能杀死对应缺陷**的守护；
其中最隐蔽的一个（编辑器模型没收到注入 ⇒ 发送按钮永远 disabled ⇒ 必然超时）
已在**真机**上用**生产链路**复验通过。

---

## 一、这次排演做了什么、没做什么

### 做了什么

按 `docs/EXTERNAL_USER_ONBOARDING.md` 的 5 步，以「第一次用这个扩展的人」的身份走一遍，
每一步都记录**卡在哪**。产物是**缺陷清单**，不是「指南没问题」的结论。

### 没做什么（边界必须写清楚）

| 没做 | 为什么 | 谁来补 |
|---|---|---|
| 没有真人外部用户 | 排演者能读源码 ⇒「照着做也卡住」只能证明**材料缺陷**，证明不了「真人会用」 | W-D2：需要**一个真人外部用户**（路线 A/B 决策门禁的最后一环） |
| 没有真实发送（点发送、等回复） | 要消耗账号额度，且发送必须由人点 | L2 第 1 轮：需要**人在机器前**登录并点发送 |
| 没有改指南以外的文案 | 本轮只修**确定性缺陷**；「材料好不好懂」属于 W-D2 的观察范围 | — |

> **别把「排演通过」读成「外部用户能用」**：排演只回答「材料自不自洽、代码有没有断点」。

---

## 二、查出来的 6 个缺陷（全部已修）

排演跑下来，第 1 步到第 5 步里**每一步都有断点**，而且**都是确定性的**（不是时序问题、
不是网络抖动——同样的输入必然复现）。

| # | 缺陷 | 断在哪一步 | 直接后果 | 工单 |
|---|---|---|---|---|
| 1 | manifest 的 host 模式写成 `https://qianwen.com/*`，而真站是 `https://www.qianwen.com/` | 第 1 步 | Chrome 的 host 匹配里 `qianwen.com` **只等于它自己**（`*.` 才是通配）⇒ 内容脚本**根本没注入** ⇒ 那个页面上扩展等于没装 | `TASK-P1-MANIFEST-HOST-PATTERN-001` |
| 2 | 后台 `getAdapter()` 在 **service worker** 里调了页面侧的 `adapter.detect()` | 第 2 步 | `detect()` 读 `window.location.hostname`，MV3 的 SW 里**没有 window** ⇒ `ReferenceError` ⇒ 整个 onMessage 处理器挂掉 ⇒ 永远不 `sendResponse` ⇒ `currentConfig` 恒为 null ⇒ **改之前，扩展在任何站点上都拿不到适配器** | `TASK-P1-SW-DETECT-PAGE-CODE-001` |
| 3 | 导入界面比后台**更严**：前端只认 `{packs:[...]}`，后台两种形状都收 | 第 4 步 | 照指南导入 `packs/examples/external-user-smoke.json`（单个 Pack）时，前端直接报「文件格式错误」⇒ 连「合并 / 覆盖」都出不来 | `TASK-P1-PACK-IMPORT-GATE-001` |
| 4 | 导入成功后，先报「导入成功」，**再**刷新列表——刷新把状态栏改写成「已加载 N 个 Pack」 | 第 4 步 | 指南承诺的成功标志**一闪就没了**；用户停下来看到的是一句既没说成功、也没说导入的是哪个的话 | `TASK-P1-IMPORT-STATUS-OVERWRITE-001` |
| 5 | 内容脚本报告失败时，后台**照样**回 `success` | 第 5 步 | 失败被跨层吞掉 ⇒ popup 显示「执行成功」而产物是空的 ⇒ 用户**无法判断哪一步坏了** | `TASK-P1-PACK-FAILURE-SWALLOWED-001` |
| 6 | 注入只改了 **DOM**，没进千问 Slate 编辑器**自己的模型** | 第 5 步 | 站点读到「用户没输入」⇒ **发送按钮保持 disabled** ⇒ 点它等于没点 ⇒ 提示词永远留在输入框里 ⇒ 60 秒后超时 | `TASK-P1-EDITOR-MODEL-INJECTION-001` |

### 缺陷 #6 的实测过程（唯一一个需要真机才能定位的）

真机（千问 `https://www.qianwen.com/`）上逐个试注入方式：

| 注入方式 | 文字在 DOM | 零宽叶子还在 | 发送按钮 `disabled` |
|---|---|---|---|
| `execCommand('insertText')`（改前用的） | 有 | **在** | **`true`**（注入前后一样） |
| `beforeinput`（`inputType=insertText`，带 `data`） | 有 | 没了 | **`false`** |

⇒ 差别不在「有没有把字放进去」，而在**站点自己的模型有没有收到**。

顺带查出两个**更隐蔽**的点：

1. **分支顺序坑**：千问的编辑区是
   `div[data-slate-editor="true"][role="textbox"][contenteditable="true"]`，
   而 `injectTextSmart` 把 `role="textbox"` 排在 `isContentEditable` **前面**
   ⇒ 千问走的是 `injectIntoTextbox`（纯 execCommand 路径）
   ⇒ **把修复写在 `injectIntoContentEditable` 里对千问是死代码**。
2. **替换语义**：编辑器里已有内容时，只派发 `beforeinput(insertText)` 是**追加**（旧+新）。
   要替换必须先把模型选区变成「全选」，而且**选区同步是异步的**：
   实测「只等 `selectionchange`」不够，还要再等一个宏任务，
   否则删除时模型选区仍是折叠的 ⇒ 只删掉一个字。
   （等待**不能**用 `requestAnimationFrame`：它在后台标签页里不触发，会把 Pack 流程卡死。）

---

## 三、修法与守护

| 缺陷 | 修法 | 守护 |
|---|---|---|
| #1 | manifest 补齐 `www.` 变体，且 `host_permissions` 与 `content_scripts.matches` **收敛成同一份清单** | `tests/external-user-path.test.mjs`：按 Chrome 的 host 匹配规则（`*.` 才通配）逐个平台核对；另加一条「构建产物的 manifest 必须由 `manifest.json` 生成」 |
| #2 | 后台改成**从发消息过来的那个标签页的 URL** 认平台，不再调页面侧代码 | 同文件两条测试：单平台 + **全部 10 个平台**都认得出；外加一条「不是 AI 站点的 URL 不该被认成任何平台」（防「什么都认」） |
| #3 | 前端只做**语法**检查，「什么算 Pack」**只有后台一个判定方** | 同文件：单个 Pack 文件不该被判成格式错误；**真的不是 JSON 仍然要报错**（防把闸门拆成没有闸门） |
| #4 | 先刷新列表、**再**报导入成功 | 同文件：选完文件点「确认导入」后，状态栏要出现指南承诺的那句话 |
| #5 | 后台在 `result.status === "failed"` 时回 `{success:false, error}`；执行器在 try/catch **外**校验 AI 步骤回执 | 同文件两条：内容脚本报失败 ⇒ 整个 Pack 必须失败；**内容脚本成功时 Pack 必须成功**（防「这条永远失败」） |
| #6 | 新增 `src/platforms/slate-editor.js`：**模型感知**的注入（清空 → 插入 → 校验模型文本），`injectTextSmart` 改 async 并把 Slate 分支排在 `role="textbox"` **前面** | `tests/editor-injection.test.mjs`（6 条）+ `tests/helpers/slate-site.mjs`（按真机结构仿真的站点） |

### 缺陷 #6 的守护设计要点

- **仿真只扮演第三方站点**（模型/选区的行为），判定一律由**生产代码**给出；
- 仿真结构照真机实测：模型与 DOM 分离、发送按钮读**模型**、占位符是叶子的**子节点**、
  零宽叶子表示「这个段落是空的」；
- 静态 fixture（手写 mock 与真机快照）**只有结构没有行为**，以前正是这一点让
  「DOM 里有字」冒充了「模型收到了」⇒ 现在 fixture 也补上站点行为
  （`tests/helpers/slate-site.mjs`，矩阵与接线测试共用同一份）。

---

## 四、变异检查（守护是不是真的在守）

改坏被守护的代码，对应的测试**必须**变红——不是「随便哪条红」就算数。

| 变异 | 结果 |
|---|---|
| 把 Slate 分支挪到 `role="textbox"` 之后（还原缺陷 #6 的分支顺序部分） | 6 条里 **5 条变红** |
| Slate 路径退回 `execCommand`（还原缺陷 #6 的模型部分） | 6 条里 **4 条变红** |

两条变异分别对应缺陷 #6 的两个独立成因，**都被杀死**。

---

## 五、真机复验（缺陷 #6）

复验跑的是**生产链路**，不是页面里手写的探针：

```
service worker → chrome.tabs.sendMessage(INJECT_TEXT)
  → 内容脚本（生产 dist 产物）→ injectTextSmart → slate-editor.js
    → beforeinput → 千问的 Slate 模型 → 发送按钮解禁
```

新增探针 `chrome-extension/tests/real-machine/injection-path-probe.mjs`
（**只注入、不发送**，且必须显式 `--i-will-inject` 才跑）。

```
$ node tests/real-machine/injection-path-probe.mjs --i-will-inject --platform=qianwen --profile-dir=.rm-profile
注入链路探针：Qianwen (千问)（https://www.qianwen.com/）——只注入，不发送。
{
  "platform": "qianwen",
  "outcome": "pass",
  "detail": "注入落到编辑器模型，发送按钮解禁",
  "modelLevelVerifiable": true,
  "receipt": { "success": true },
  "before": {
    "editorFound": true, "isSlate": true,
    "zeroWidthLeafPresent": true, "modelText": "",
    "sendButtonFound": true, "sendButtonDisabled": true
  },
  "after": {
    "editorFound": true, "isSlate": true,
    "zeroWidthLeafPresent": false,
    "modelText": "注入链路探针文本（不发送）",
    "sendButtonFound": true, "sendButtonDisabled": false
  }
}
```

**替换语义**也在真机上单独验过：先注入「旧文字残留」，再注入「新提示词」，
模型文本是**新提示词**（不是「旧文字残留+新提示词」）。

> 证据文件：`collaboration/results/real-machine-runs/evidence/L2-injection-qianwen-2026-10-26.json`
> （**只覆盖注入环节**；L2 的「发送 + 等回复」没跑，所以千问的 L2 结论是 `not-run`，不是 `pass`）。

---

## 执行命令

以下命令即 6 个工单契约里的 `acceptance_commands`，逐字执行，全部通过。

### 1. `cd chrome-extension && node tests/run-tests.mjs`

```
发现 10 个测试文件：
  - tests/ci-wiring.test.mjs
  - tests/editor-injection.test.mjs
  - tests/extension-wiring.test.mjs
  - tests/external-user-path.test.mjs
  - tests/platform-registry.test.mjs
  - tests/real-machine/l2-model.test.mjs
  - tests/real-machine/message-model.test.mjs
  - tests/real-machine/qianwen-contract.test.mjs
  - tests/real-machine/sanitize.test.mjs
  - tests/real-machine/snapshot-fixtures.test.mjs

ℹ tests 142
ℹ pass 142
ℹ fail 0
```

### 2. `cd chrome-extension && node --test tests/external-user-path.test.mjs`

```
ℹ tests 11
ℹ pass 11
ℹ fail 0
```

11 条分别守缺陷 #1～#5（manifest 覆盖 2 条、SW 认平台 3 条、失败不吞 2 条、
导入闸门 3 条、产物 manifest 1 条）。

### 3. `cd chrome-extension && node --test tests/editor-injection.test.mjs`

```
✔ Slate：注入后模型收到文本、发送按钮解禁（不靠 execCommand）
✔ Slate：编辑器里已有内容时是替换，不是追加
✔ Slate：多行提示词原样进模型
✔ Slate：模型收不到文本时必须抛错，不许假成功
✔ 路由：带 role=textbox 的 Slate 编辑区必须走模型感知路径
✔ 普通 contenteditable：仍走原来的注入路径，不受 Slate 逻辑影响
ℹ tests 6
ℹ pass 6
ℹ fail 0
```

### 4. `cd chrome-extension && node tests/adapter-matrix/adapter-test-runner.js`

```
  ChatGPT                   10/11 (ALL PASS)
  Claude.ai                 10/11 (ALL PASS)
  Gemini                    10/11 (ALL PASS)
  DeepSeek                  11/11 (ALL PASS)
  Kimi AI                   10/11 (ALL PASS)
  LongCat AI                11/11 (ALL PASS)
  Qianwen (千问)              10/11 (ALL PASS)
  Yiyan (文心一言)            11/11 (ALL PASS)
  Yuanbao (腾讯元宝)            10/11 (ALL PASS)
  ChatGLM (智谱清言)            11/11 (ALL PASS)

  Total: 108/114 passed, 0 failed, 6 skipped
```

6 个 skip 是 `getMessageList() 第 3 个及以后的选择器也能生效`（fixture 只标了一个消息，
没有第 3 个选择器可验）——**诚实跳过**，与本轮改动无关。

### 5. `cd chrome-extension && node tests/real-machine/mutation-check.mjs`

```
全部 29 条变异都被杀死。
```

### 6. `cd chrome-extension && npm run build`

```
=== Chrome Extension Build ===
[1/5] Cleaned output directories
[2/5] Building Content Script (IIFE format)...
  ✅ Content Script built
[3/5] Building Service Worker (ESM format)...
  ✅ Service Worker built
[4/5] Merging build outputs...
  ✅ Content Script merged
  ✅ Service Worker merged
[5/5] Copying static assets...
  ✅ Static assets copied (16 files, 3 icons)
=== Build Complete ===
```

### 7. `python3 -m pytest tests/ -q`

```
3058 passed, 7 skipped in 47.02s
```

（7 个 skip 是需要本地后端在 `127.0.0.1:8000` 的集成测试。）

### 8. `python3 -m ruff check .`

```
All checks passed!
```

### 9. `python3 scripts/scan_secrets_pii.py --workspace .`

```
[OK] no secrets found
```

### 10. `python3 scripts/verify_task_file_contracts.py`

```
已登记并收口：TASK-P1-MANIFEST-HOST-PATTERN-001
已登记并收口：TASK-P1-SW-DETECT-PAGE-CODE-001
已登记并收口：TASK-P1-PACK-IMPORT-GATE-001
已登记并收口：TASK-P1-IMPORT-STATUS-OVERWRITE-001
已登记并收口：TASK-P1-PACK-FAILURE-SWALLOWED-001
已登记并收口：TASK-P1-EDITOR-MODEL-INJECTION-001

契约校验: checked=6 invalid=0 skipped=0

终态结果一致性审计: audited=6 consistent=6 mismatch=0 unparseable=0 missing_result=0

结论： 全部通过
```

> 这个脚本是本轮**新加**的：`python3 -m ai_collab.cli tasks validate-contract` 读的是
> **运行时状态库**，**不读** `collaboration/tasks/*.md`——
> 所以「工单文件写好了」**不等于**「工单过了门禁」。
> 脚本把「登记 → 收口 completed → 契约校验 → 终态一致性审计」串成一步，
> 并且**不写全局状态文件**（全局文件是跨工作区镜像，不是事实源）。

---

## 验证结果

| 验收项 | 结果 |
|---|---|
| 6 个缺陷是否都定位到**确定性**成因 | 是（每个都有真机或代码级证据，不是推测） |
| 6 个缺陷是否都修了 | 是 |
| 每个缺陷是否有**能杀死它**的守护 | 是（变异检查：缺陷 #6 的两条变异分别杀死 5/6、4/6 条用例） |
| 缺陷 #6 是否在**真机 + 生产链路**上复验 | 是（注入进模型、发送按钮解禁、重复注入是替换） |
| 失败是否还在被吞 | 否（内容脚本报错 ⇒ Pack 失败；注入收不到模型 ⇒ 抛错） |
| 6 个工单是否过了**仓库自己的**契约门禁 | 是（checked=6 / invalid=0；终态一致性 audited=6 / consistent=6 / mismatch=0） |
| 全量单测 / 矩阵 / 变异 / 构建 / pytest / ruff / 密钥扫描 | 全绿 |
| 真人外部用户是否已验证 | **否**——那是 W-D2，本轮不覆盖 |
| L2（真实发送 + 等回复）是否已跑 | **否**——10 个平台的 L2 结论都是 `not-run`（含原因） |

### 测试结论

- **本轮改动的回归面是绿的**：扩展单测 142/142、矩阵 108/114（6 个诚实跳过）、变异 29/29、
  构建通过、pytest 3058 通过、ruff 干净、密钥扫描 0 命中。
- **新增守护的有效性经过变异验证**，不是「写完就绿」。
- **但这不能推出「外部用户能用」**：L2（真实发送 + 等回复）本轮**没跑**，
  真人外部用户（W-D2）本轮**没有**。这两件事仍然是门禁。

---

## 风险

| # | 风险 | 影响面 | 现在的处置 |
|---|---|---|---|
| 1 | **L2 未跑** ⇒「点发送 → 等回复 → 拿到正文」这条链路仍未在真机验证 | 全平台 | 10 个平台的 L2 已登记为 `not-run` + 原因；需要人拿已登录账号跑第 1 轮（千问 zh-CN + Gemini en-US） |
| 2 | **真人外部用户未验证**（W-D2） | 路线 A/B 决策门禁 | 排演只覆盖材料自洽性；门禁仍为开启，**不得据此拍板路线** |
| 3 | 模型感知的注入**只对 Slate 生效**（千问已验） | Claude.ai（ProseMirror）、元宝（Quill）等 | 其余框架各自的模型机制不同，本轮**不做承诺**；仍走原路径，是否同样有「只改 DOM 不改模型」的问题**未验证** |
| 4 | 注入改成 async ⇒ 7 个 adapter 与内容脚本的调用点都加了 `await` | 扩展全部平台 | 全量单测 + 矩阵通过；真机只验了千问，其余平台的行为变化**未在真机确认** |
| 5 | 新增的注入探针会**往真实站点的输入框写字**（不发送） | 使用者自己的账号页面 | 必须显式 `--i-will-inject`；不登录；不点发送；不进 CI 硬门禁 |
| 6 | 缺陷 #3 的修法把「什么算 Pack」的判定**收到后台一处** | 前端 | 前端不再有第二套判定；但前端也因此**不再**提前拦截语义错误的文件，错误提示会变成后台回的口径 |
| 7 | 千问的 L2 结论是 `not-run` 而不是 `pass` | 路线门禁 | 证据文件里写明了「只覆盖注入环节」；不得被当成 L2 通过引用 |

---

## 回滚

本轮改动集中在 `chrome-extension/`（生产代码 + 测试）与 `collaboration/`（结果文件、
工单、回归手册台账），**没有**改动 Python 侧运行时代码（`ai_collab/`）与数据库结构。

- **单点回滚**：6 个缺陷各自独立，可单独回退。若只想保留部分修复，
  按工单对应的文件回退即可（清单见下表）。
- **整体回滚**：`git revert` 本轮提交即可；本轮**没有**数据迁移、**没有**对外 API 变更，
  回滚不需要任何补偿动作。
- **构建产物**：`npm run build` 会重建 `dist/`；回滚源码后必须重新构建，
  否则浏览器里跑的还是旧产物。

| 工单 | 回滚涉及的文件 |
|---|---|
| `TASK-P1-MANIFEST-HOST-PATTERN-001` | `chrome-extension/manifest.json`、`chrome-extension/static-assets.cjs`、`chrome-extension/build.js` |
| `TASK-P1-SW-DETECT-PAGE-CODE-001` | `chrome-extension/src/background/service-worker.js` |
| `TASK-P1-PACK-IMPORT-GATE-001` | `chrome-extension/public/pack-editor.js` |
| `TASK-P1-IMPORT-STATUS-OVERWRITE-001` | `chrome-extension/public/pack-editor.js` |
| `TASK-P1-PACK-FAILURE-SWALLOWED-001` | `chrome-extension/src/background/service-worker.js`、`chrome-extension/src/background/pack-executor.js` |
| `TASK-P1-EDITOR-MODEL-INJECTION-001` | `chrome-extension/src/platforms/slate-editor.js`（新增）、`chrome-extension/src/platforms/adapter-utils.js`、`chrome-extension/src/platforms/*-adapter.js`（7 个）、`chrome-extension/src/content/content-script.js` |

> 回滚提示：`injectTextSmart` 已改成 `async`。若只回退 `slate-editor.js` 而保留
> `adapter-utils.js` 里的 async 改动，调用点仍需 `await`（`await` 一个非 Promise
> 是合法的，行为不变）⇒ **不会**因为半回滚而崩，但模型感知的修复会失效。

本轮另外新增了一个**验证工具**（不属于任何单个缺陷的修复）：
`scripts/verify_task_file_contracts.py`。它是纯新增的只读校验脚本，
删掉它不影响任何运行路径，只是少了「工单过了门禁」的机检入口。
