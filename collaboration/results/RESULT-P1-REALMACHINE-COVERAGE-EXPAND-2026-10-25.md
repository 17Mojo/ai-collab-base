# RESULT-P1-REALMACHINE-COVERAGE-EXPAND-2026-10-25

**状态**: completed
**任务**: `TASK-P1-REALMACHINE-COVERAGE-EXPAND-001`（真机回归覆盖面扩张）
**执行**: Claude Code（AGENT_EXEC）　**复核**: CodeArts（AGENT_TEST）
**分支**: `feat/realmachine-coverage-expand`（基线 `main` @ `71c9eac`）
**日期**: 2026-10-25

---

## 一句话结论

真机实测抓出 **4 个模拟层 110/114 全绿也没发现的生产缺陷**（文心一言/元宝的消息数被界面外壳撑大、
Kimi/ChatGLM 的 `isTyping()` 恒为 true ⇒ 每次发送必然 60 秒超时），已全部修复。
同时把探针扩到 10 平台、采到 7 家真实 DOM 快照、交付 L2 半自动观测器，
并新增**变异检查**——把「测试到底守住了什么」从口头承诺变成 CI 里的可执行断言。

---

## 执行命令

以下 7 条即工单契约里的 `acceptance_commands`，逐字执行，全部通过：

### 1. `cd chrome-extension && node tests/run-tests.mjs`

```
发现 6 个测试文件：
  - tests/ci-wiring.test.mjs
  - tests/platform-registry.test.mjs
  - tests/real-machine/l2-model.test.mjs
  - tests/real-machine/message-model.test.mjs
  - tests/real-machine/sanitize.test.mjs
  - tests/real-machine/snapshot-fixtures.test.mjs

ℹ tests 80
ℹ pass 80
ℹ fail 0
```

### 2. `cd chrome-extension && node tests/real-machine/mutation-check.mjs`

```
=== 变异检查（12 条）===
全部 12 条变异都被杀死。
```

12 条变异逐条对应一个具体缺陷（计数增长口径 / 生成中条件 / 基准取值 /
正文非空判定 / 证据脱敏 / 发送闸门 / 两条不变量 / class 结构保留 / 邮箱规则），
每条都要求**指定的那条测试**因此报错——不是「随便哪条红」就算数。

### 3. `cd chrome-extension && node tests/adapter-matrix/adapter-test-runner.js`

```
  Total: 109/114 passed, 0 failed, 5 skipped
```

5 个 skip 是**诚实跳过**（见「风险」一节），不是失败。

### 4. `cd chrome-extension && npm run build`

```
=== Build Complete ===
Output directory: dist/
```

### 5. `python3 -m pytest tests/ -q`

```
3038 passed, 6 skipped in 39.45s
```

6 个 skip 全部是环境原因（本地无 `client_tokens.db`、本地后端未启动），与本工单无关。

### 6. `python3 -m ruff check .`

```
All checks passed!
```

### 7. `python3 scripts/scan_secrets_pii.py --workspace .`

```
[OK] no secrets found
```

---

## 验证结果

### 修复的 4 个生产缺陷（真机实测抓出，模拟层矩阵全绿也没发现）

| # | 平台 | 缺陷 | 修法 | 直接后果 |
|---|---|---|---|---|
| 1 | 文心一言 | `messageList` 含 `[class*="chat"]` | 删除该条宽松选择器 | 真机命中 37 个**界面外壳**（`body.cos-chat` / `_chat-container_10y6s_1` / `history-chat-*`）⇒ 消息计数失真 |
| 2 | 腾讯元宝 | `messageList` 含 `[class*="chat"]` | 删除该条宽松选择器 | 真机命中 8 个（`yb-new-chat-entry` 按钮、svg）⇒ 同上 |
| 3 | Kimi | `typingIndicator` 含 `[class*="loading"]` | 收窄为 `.loading` / `.generating` | 命中 9 个侧边栏骨架屏（224×224）⇒ `isTyping()` 恒为 true ⇒ 每次发送必然 60 秒超时 |
| 4 | ChatGLM | `typingIndicator` 含 `[class*="loading"]` | 收窄为 `[class*="generating"]` / `.typing-indicator` | 命中「正在加载...」占位条（239×32）⇒ 同上 |

> 有一处**靠直觉会走错**：#3/#4 一开始打算用「零尺寸元素不算命中」来修。
> 实测数据否掉了它——Kimi 的骨架屏是 224×224、ChatGLM 的占位条是 239×32
> 且带可见文字，尺寸检查根本分不开。最后靠**收窄选择器**修。

### 两条新引入的可机检不变量

| 不变量 | 表述 | 违反后果 |
|---|---|---|
| 无会话即无消息 | 落地页（无会话）上 `messageList` 命中的元素必须**全部无文本** | 命中界面外壳 ⇒ 计数被撑大 ⇒ 回复等待失真 |
| 空闲即不忙 | 空闲落地页上 `isTyping()` 必须是 `false` | 打字指示器误命中常驻 DOM ⇒ 等待必然超时 |

两条都是**在真机上量出来的**，不是设计出来的。判定逻辑拆成纯函数
（`message-model.mjs`）以便进单测，采集脚本只负责喂数据。

### 覆盖面扩张

| 项 | 之前 | 之后 |
|---|---|---|
| L1 探针覆盖平台 | 3 | **10**（pass 7 / unverified 3 / fail 0） |
| 真实 DOM 快照 | 1 家 | **7 家**（ChatGLM / Gemini / Kimi / LongCat / 千问 / 文心一言 / 元宝） |
| 平台名单事实源 | 散落 4 处 | **1 处**（`tests/platforms.mjs`），并有双向对账守护 |
| 真实快照的 CI 地位 | — | **不进硬门禁**：站点改版 ≠ 代码缺陷，「快照失效」是待办信号 |

未采到快照的 3 家及原因（均为环境限制，不是代码结论）：

| 平台 | 结果 | 原因 |
|---|---|---|
| ChatGPT | unverified | 机器人校验（HTTP 403） |
| Claude.ai | unverified | 机器人校验（HTTP 403 + 中文「安全验证」标记） |
| DeepSeek | unverified | 登录墙（`a[href*="auth"]`） |

### 新增的能力

| 交付物 | 作用 |
|---|---|
| `tests/real-machine/l2-send-observer.mjs` | **L2 观测器**：人点发送、脚本只读，并**并行跑生产 `waitForResponse`** ⇒ 产出可机检 JSON 而非截图 |
| `tests/real-machine/mutation-check.mjs` | 变异检查：改坏被守护的代码，对应测试必须变红（12/12 已被杀死） |
| `tests/run-tests.mjs` | 单测入口：`node --test` 的三种写法在 Node 20/23 上各有一坑（自动发现扫进第三方 node_modules 会卡死；目录形式报 `MODULE_NOT_FOUND`；glob 形式要 Node 21+） |
| `tests/ci-wiring.test.mjs` | 守护「CI 确实在跑扩展测试」——不许 `|| echo` 吞掉失败 |
| `tests/platform-registry.test.mjs` | 登记表 ↔ 生产 adapter ↔ content-script ↔ manifest ↔ fixture 双向对账 |

### 硬约束的落实

| 约束 | 落实方式 | 验证 |
|---|---|---|
| 探针永不发送 | L1 探针与 L2 观测器都不注入文本、不点发送 | 观测器必须带 `--i-will-send` 才启动；`l2-model.test.mjs` 有专门用例，变异检查确认该闸门失效会报红 |
| 真实快照不进 CI 硬门禁 | 快照只做离线守护，不进 workflow | `test.yml` 中无快照相关步骤 |
| node_modules 取消跟踪独立成工单 | 拆为 `TASK-P1-NODE-MODULES-UNTRACK-001`，独立分支/独立 PR | 本工单的 diff 不含任何 `node_modules` 变更 |

---

## 测试结论

**结论：通过。**

- 7 条验收命令全部执行通过（见上，逐条附实际输出）；
- 扩展单测 **80/80** 通过；
- 变异检查 **12/12** 变异被杀死——每条守护关系都被证明有效，不是「测试绿就算数」；
- Python 单测 **3038 通过 / 6 跳过**（跳过原因均为本地环境缺失，与本工单无关）；
- adapter 矩阵 **109/114 通过 / 0 失败 / 5 跳过**；
- 密钥扫描 **0 命中**；ruff **All checks passed**；扩展构建成功。

**新增测试的来源是实测数据，不是凭空编的形状**：
消息计数模型的 9 个用例用的是真机上抓到的 YIYAN_SHELL（37 命中）、
YUANBAO_BUTTON（8 命中）、KIMI_EMPTY_CONTAINER（2 命中）三组真实数据改写。

**一处自曝**：本工单在写单测时发现自己的「class 属性不做长随机串脱敏」用例是**空转**的
（用了 20 字符的类名，而令牌规则是 40 字符起才触发）。已改成 40+ 字符的类名，
并补了变异条目确认该用例真的有牙齿。

---

## 风险

### 明确未验证、不得当成已通过的项

| 风险 | 影响 | 缓解 |
|---|---|---|
| **消息气泡选择器仍未在真机验证**（7 家已采样的平台） | 落地页上没有会话，只能证明「不误命中界面外壳」，**证不了「能命中真气泡」**——选择器写错和正确在落地页上表现一样 | 已写进 `docs/REAL_MACHINE_REGRESSION.md` §6.2 #1/#2；需已登录 profile + 一次真实发送 |
| **Kimi/ChatGLM 的真实「生成中」指示器未验证** | 收窄后的选择器若都不命中，`isTyping()` 恒为 false ⇒ `waitForResponse` 可能**中途提前返回**（拿到半截回复） | 已写进两份 adapter 的注释与 §6.2 #3；观测器的 `wouldResolve` 答不了「会不会太早成功」，要人看时间线里正文变非空是在第几个样本 |
| **L2 从未真跑过** | 「回复等待链路」仍未验证 | 观测器已交付并有 16 个单测 + 8 条变异；真跑需要人 + 已登录 profile |
| **千问的 messageList 命中 0 个** | 无法区分「选择器正确」与「选择器写错」 | 已写进 §6.2 #2；依赖 B-3（用第 1 刀采到的快照定选择器） |

### 未纳入本工单、需另行决策的问题

**后台↔内容脚本的消息协议有洞**（性质与 DOM 契约不同，故不混入本工单）：

- `src/background/pack-executor.js` 发 `SEND_TO_AI`，但 `service-worker.js` 的 13 个
  `onMessage` 分支里**没有**对应接收者——Pack 执行链路走不通；
- `src/background/multi-platform-executor.js` 是 `GET_LATEST_RESPONSE` 的唯一发送方，
  同样无人处理，且它读 `pageState.isTyping`，而 `content-script.js` 的 `getPageState()`
  **根本不返回**该字段；
- `multi-platform-executor.js` 目前**无人 import**，属死代码。

这是 **P0 级的产品缺陷**（Pack 执行走不通），与本工单的 DOM 契约问题性质不同。
处置决策（本工单内修 vs. 单独立项 + 文档化）**仍待定**，已记在
`docs/REAL_MACHINE_REGRESSION.md` §6.2 #6。

### 流程性风险

- 矩阵的 5 个 skip 是**诚实跳过**（如「`getMessageList()` 第 3 个及以后的选择器也能生效」
  在元宝上因 `.message-item` 被 `[class*="message"]` 包含而无独占目标）。已把跳过条件
  改成「是否存在独占目标」，并在测试里写明跳过原因——不是把失败藏起来。
- 真实快照入库意味着**站点改版会让快照过时**。这是刻意的分层：改版由 L1 探针（打真站）
  负责，快照只守「我们对真机 DOM 的理解被记录下来了，而且自洽」。

---

## 回滚

本工单**不涉及任何数据迁移、不改数据库 schema、不改运行时配置**，回滚成本低。

| 场景 | 回滚方式 |
|---|---|
| 整体回滚 | `git revert` 本工单在 `feat/realmachine-coverage-expand` 上的提交（PR 未合入前直接删分支即可） |
| 只回滚 4 个 adapter 缺陷修复 | `git revert` 对应提交；**注意这会把 60 秒必然超时的问题放回去** |
| 只回滚新增工具与测试 | 删除 `chrome-extension/tests/platforms.mjs`、`chrome-extension/tests/real-machine/`、相关 `.test.mjs` 与 `run-tests.mjs`，并同步撤掉 `test.yml` 新增的两个步骤 |
| 只回滚 CI 接线 | 撤掉 `test.yml` 的「Run extension unit tests」「Mutation check」两个步骤即可；`ci-wiring.test.mjs` 会因此报红，需一并撤掉 |
| 快照产物过时 | 重新跑 `snapshot-capture.mjs` 覆盖；快照是基线产物，无回滚风险 |

**回滚后 CI 仍会绿**——因为这些测试本来就是新增的，撤掉后回到 71c9eac 的状态。
这正是把「真实快照」排除在硬门禁之外的原因：站点改版不该让 CI 失败。
