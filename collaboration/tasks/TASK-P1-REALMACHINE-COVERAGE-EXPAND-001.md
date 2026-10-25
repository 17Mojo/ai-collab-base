---
task_id: TASK-P1-REALMACHINE-COVERAGE-EXPAND-001
change_id: bugfix/no-spec
status: implementing
priority: P1
assignee: claude_code
assignee_role: AGENT_EXEC
reviewer: codearts_agent
primary_skill: api-test-pro
support_skills:
  - testing
  - documentation
created_at: 2026-10-25T08:40:13+08:00
acceptance_commands:
  - "cd chrome-extension && node tests/run-tests.mjs"
  - "cd chrome-extension && node tests/real-machine/mutation-check.mjs"
  - "cd chrome-extension && node tests/adapter-matrix/adapter-test-runner.js"
  - "cd chrome-extension && npm run build"
  - "python3 -m pytest tests/ -q"
  - "python3 -m ruff check ."
  - "python3 scripts/scan_secrets_pii.py --workspace ."
result_file: collaboration/results/RESULT-P1-REALMACHINE-COVERAGE-EXPAND-2026-10-25.md
---

# TASK-P1-REALMACHINE-COVERAGE-EXPAND-001：真机回归覆盖面扩张（探针扩 10 平台 + 真实快照 + L2 观测器 + 平台名单单一事实源）

> **本工单由 Claude Code（AGENT_EXEC）执行，CodeArts（AGENT_TEST）复核。**
>
> **范围拆分（用户明确要求）**：`node_modules` 取消跟踪**必须独立成工单**，
> 不与本工单的缺陷修复混在一起 → 已拆出
> [`TASK-P1-NODE-MODULES-UNTRACK-001`](TASK-P1-NODE-MODULES-UNTRACK-001.md)，
> 独立分支、独立 PR、独立门禁。

## 一、要解决什么

路线 A/B 拍板（`memory/project_route_decision.md`）唯一缺失的真证是
「真机 3 平台回归 + 第一个外部用户」。而 2026-10-25 的真机实测暴露了一个
**比覆盖面更严重的问题**：

> 110/114 全绿的模拟层矩阵，掩盖了 **4 个真机上才暴露的生产缺陷**。

绿不是因为对，是因为没测到。覆盖面扩张不是「多测几家」的工程量问题，
而是**现有测试根本没有能力发现这类缺陷**的问题。所以本工单的主线是
**让测试具备发现能力**，覆盖面扩张是它的副产品。

## 二、实测抓到的 4 个生产缺陷（本工单已修）

全部来自 [src/platforms/](chrome-extension/src/platforms/) 的生产 adapter，
改动前**模拟层矩阵全绿**。

| # | 平台 | 缺陷 | 直接后果 |
|---|---|---|---|
| 1 | 文心一言 | `messageList` 含 `[class*="chat"]` | 真机上命中 37 个**界面外壳**（`body.cos-chat` / `_chat-container_10y6s_1` / `history-chat-*`）⇒ 消息计数被撑大，`waitForResponse` 拿它做「发送前后比较」必然失真 |
| 2 | 腾讯元宝 | `messageList` 含 `[class*="chat"]` | 真机上命中 8 个（`yb-new-chat-entry` 按钮、svg）⇒ 同上 |
| 3 | Kimi | `typingIndicator` 含 `[class*="loading"]` | 命中 9 个**侧边栏骨架屏**（`next-sidebar__history-loading`，224×224）⇒ `isTyping()` 恒为 true ⇒ `waitForResponse` 的 `!isTyping()` **永远不成立** ⇒ 每次发送必然 60 秒超时 |
| 4 | ChatGLM | `typingIndicator` 含 `[class*="loading"]` | 命中「正在加载...」占位条（`list-loading`，239×32）⇒ 同上 |

> 有一处**靠直觉会走错**：#3/#4 一开始打算用「零尺寸元素不算命中」来修。
> 实测数据否掉了这个方案——Kimi 的骨架屏是 224×224、ChatGLM 的占位条是
> 239×32 且**带可见文字**，尺寸检查根本分不开。最后是**收窄选择器**修的。

## 三、交付物

| 类别 | 文件 | 作用 |
|---|---|---|
| 单一事实源 | `chrome-extension/tests/platforms.mjs` | 10 平台名单收敛到一处（此前散落 4 处） |
| 一致性守护 | `chrome-extension/tests/platform-registry.test.mjs` | 登记表 ↔ 生产 adapter ↔ content-script ↔ manifest ↔ fixture 双向对账 |
| 真实快照 | `chrome-extension/tests/real-machine/snapshot-capture.mjs` | 采真实 DOM + 判定两条不变量 + 脱敏入库 |
| 脱敏 | `chrome-extension/tests/real-machine/sanitize.mjs` | 邮箱 / 手机号 / 令牌 / 事件属性 / script |
| 不变量判定 | `chrome-extension/tests/real-machine/message-model.mjs` | 「无会话即无消息」/「空闲即不忙」 |
| L2 观测器 | `chrome-extension/tests/real-machine/l2-send-observer.mjs` | **人点发送，脚本只读**，并行跑生产 `waitForResponse` |
| 判定口径 | `chrome-extension/tests/real-machine/l2-model.mjs` | 观测器的纯逻辑（可单测） |
| 变异检查 | `chrome-extension/tests/real-machine/mutation-check.mjs` | 改坏被守护的代码，对应测试必须变红 |
| 单测入口 | `chrome-extension/tests/run-tests.mjs` | Node 18+ 通用（`node --test` 三种写法在 Node 20/23 上各有一坑） |
| CI 守护 | `chrome-extension/tests/ci-wiring.test.mjs` | 不许 `|| echo` 吞掉扩展测试的失败 |
| 真机快照 | `chrome-extension/tests/real-machine/fixtures/real/` | 7 家平台的真实 DOM（已脱敏） |

## 四、可达性体检表（探针实跑 10 平台）

| 结果 | 平台 | 原因 |
|---|---|---|
| pass | ChatGLM / Gemini / Kimi / LongCat / 千问 / 文心一言 / 元宝 | — |
| unverified | ChatGPT | 机器人校验（HTTP 403）——**不是** adapter 的结论 |
| unverified | Claude.ai | 机器人校验（HTTP 403 + 中文「安全验证」标记） |
| unverified | DeepSeek | 登录墙（`a[href*="auth"]`）——需要已登录 profile |
| **fail** | **无** | — |

> `login_wall` / `bot_check` 记为 `unverified`（环境限制），**不记为失败**。

## 五、硬约束（不得违反）

1. **探针永不发送**：L1 探针与 L2 观测器都**不注入文本、不点发送**。
   L2 观测器必须带 `--i-will-send` 才会启动，且发送动作由人在浏览器里完成。
2. **真实快照不进 CI 硬门禁**：站点改版 ≠ 代码缺陷。
   「快照失效」是一条**待办信号**，不是 CI 失败。
   快照守的是「我们对真机 DOM 的理解被记录下来了，而且自洽」。
3. **node_modules 取消跟踪独立成工单**（见本文开头的范围拆分）。

## 六、验收

见 frontmatter 的 `acceptance_commands`。全部必须**逐字**可跑并通过。
结果文件：[`collaboration/results/RESULT-P1-REALMACHINE-COVERAGE-EXPAND-2026-10-25.md`](../results/RESULT-P1-REALMACHINE-COVERAGE-EXPAND-2026-10-25.md)。
