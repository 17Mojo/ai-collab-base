# 开发记录：真机回归准备（2026-10-25）——探针 / 手册 / 记录器 + 真机实测暴露的 adapter 漂移修复

## 记录信息

- **任务ID**: TASK-P1-REALMACHINE-REGRESSION-PREP-001
- **AI类型**: Claude Code（AGENT_EXEC）
- **时间**: 2026-10-25
- **分支**: `main`
- **结果文件**: `collaboration/results/RESULT-P1-REALMACHINE-REGRESSION-PREP-2026-10-25.md`
- **手册**: `docs/REAL_MACHINE_REGRESSION.md`
- **任务描述**: PR #2 合并并归档 OpenSpec 变更后，做「真机回归准备」——把路线 A/B 决策门禁
  剩下的唯一真证（「真机 3 平台回归 + 第一个外部用户」）的前半段做成可执行、可对账的规程；
  过程中真机实测抓到一个**真实产品缺陷**，连带修掉。

---

## 起因：绿灯与真实行为背离

准备真机回归的第一步是写一个**只读探针**，把生产 adapter 打进真实站点页面里跑。
第一轮实测就抓到了：

```
[BOT_CHECK] ChatGPT — 命中人机校验/机器人拦截页（信号：http-status-403）
[BOT_CHECK] Claude.ai — 同上
[PASS] Gemini — 生产 adapter 在真机 DOM 上找到输入框
```

Gemini 找到了输入框，但**发送按钮一个都命中不了**——页面上明明有发送按钮。
把选择器逐条在真机上量了一遍，才看清问题的形状：

| 界面语言 | 内层 `<button>` 的 aria-label | 旧选择器 `button[aria-label*="Send"]` |
|---|---|---|
| zh-CN | `发送` | **0 命中** |
| en-US | `Send message` | 1 命中（**侥幸**） |

也就是说：这个缺陷**只在中文界面出现**，在英文界面被旧选择器「侥幸」掩盖。
只跑默认语言就永远看不见它。

## 三处结构性缺陷（不是一行选择器写错）

| 编号 | 缺陷 | 后果 |
|---|---|---|
| F3 | 生产 `sendButton` 选择器漂移 | 中文界面下 Gemini 的 Pack 完全无法发送 |
| F4 | 模拟层**手抄**了一份 `SELECTORS` 表 | 生产选择器漂移了，矩阵**照样全绿** |
| F5 | `findElements` 全不匹配回退「页面全部 div」；`findElement` 把 `<body>` 当命中 | 消息计数虚高（真机 104）；Gemini 的 `<body>` 常驻 `enable-lm-loading-animation` → `isTyping()` 恒为 true → 响应等待必然超时 |

F4 是最值得记的一条：**矩阵测的是一个「平行宇宙」**。它自己实现了一套查找逻辑、
自己抄了一份选择器表，生产代码改了它一点感知都没有。修法不是「补几个用例」，
而是让矩阵**直接 import 生产 adapter 源码**——从「测副本」改成「测本体」。

F5 里的两处注释也是假的：`// fallback: empty NodeList` 写的和代码做的相反；
`findElement` 会把 `<body>` 当合法命中，而 Gemini 的 `<body>` class 里
`enable-lm-loading-animation` **常驻**，于是 `[class*="loading"]` 必然命中它。

## 顺带发现：元素存在 ≠ 正在打字

真实站点空闲态会把打字指示器**留在 DOM 里**，只是 `display:none`。
按「存在即命中」判定，`isTyping()` 恒为 true，`handleWaitForResponse`
永远等不到「不再打字」，每次执行都超时。

可见性判定**没有**用 `getBoundingClientRect`——jsdom 没有布局，rect 恒为 0×0，
用它会让矩阵里的所有元素都被判成「不可见」。最终用祖先链上的
`display` / `visibility` / `opacity` 逐级判定。

## 变异验证：绿是护栏，不是证据

新矩阵 110/114 全绿。但**绿灯本身不构成证据**——必须证明「把被守护的缺陷改回去，
它会变红」。于是逐条做了 6 个变异，每次只改一处、跑完立刻从备份恢复该文件：

| 变异 | 注入的缺陷 | 矩阵的反应 |
|---|---|---|
| M1 | Gemini `sendButton` 退回旧选择器 | `getSendButton() 返回 null` |
| M2 | `findElement` 不排除页面根节点 | `findElement() 返回了页面根节点 <body>` |
| M3 | `findElements` 恢复 div 回退 | `期望空集合，实际返回 9 个元素` |
| M4 | `isTyping()` 不做可见性判定 | `isTyping() 返回 true` |
| M5 | 千问 `getMessageList()` 只取第 1 个选择器 | `第 3 个及以后的选择器（.response-content）没有生效` |
| M6 | 矩阵漏掉一个生产 adapter | `生产新增了 adapter 但矩阵没覆盖：chatglm-adapter.js` |

**6/6 全部被抓。**

这里踩过一个坑：M4 第一次跑显示「变异锚点没找到」，因为上一轮我把
`isTyping()` 写成了 `return !!findVisibleElement(...)` 而不是临时变量形式。
改锚点后重跑即通过——**变异脚本自身的锚点漂移**和**代码漂移**是两回事，
前者要改脚本，后者要改代码，不能混为一谈。

> 另一个坑：早期用 `git checkout -- <file>` 做还原，**把 qianwen 的生产改动一起退掉了**
> （那个文件当时没备份）。共享工作区里 `git checkout` 是危险动作——
> 正确做法是 `cp -R` 备份整棵 `src/` 再从备份恢复。

## 记录器：把「没跑」和「跑过」在机器层面分开

`scripts/real_machine_regression.py` 不做检测，只做记录与对账。8 条规则都是
**可机检**的，其中最有用的一条是**证据与结论交叉核对**：

```
$ python3 scripts/real_machine_regression.py verify --run-id RMR-DEMO
  一致性问题：
    - records[0]: 证据与结论不符——探针判定 outcome=bot_check，记录却写 pass
```

也就是说，**没人能靠「把未验证写成通过」把门禁糊弄过去**——探针的 JSON 证据
会被逐条对回记录里的结论。

另一条是**路线门禁恒开**：这份记录永远不构成「第一个外部用户」证据。
本轮 `RMR-2026-10-25-01` 的结论是 `partial`（ChatGPT / Claude.ai 无登录态未验证，
三个平台的 L2 全部 `not-run`），`verify` 退出码 **2**（一致但没跑完）。

## 顺手修掉的两处「口径不实」

1. 探针证据里的 `readOnly` 字段写的是 `!args.probeSendButton`——加了
   `--probe-send-button` 就变成 `readOnly: false`。但探针**从不**注入文本、
   **从不**点发送（那个参数只多做一次 DOM 形状比对）。证据文件里留着
   `readOnly: false` 会让复核方以为探针发过消息。改成恒为 `true`，
   并新增 `sendsMessages: false` 说清楚。
2. `list` 会把同目录下的探针证据 JSON 当成 run 记录，逐条报「6 处不一致」。
   改成按「有没有 `run_id` 字段」识别记录，其余跳过并提示。

## 交付物清单

| 类别 | 文件 |
|---|---|
| 生产修复 | `chrome-extension/src/platforms/adapter-utils.js`、10 个 `*-adapter.js`、`src/content/content-script.js` |
| 模拟层 | `chrome-extension/tests/adapter-matrix/{adapter-test-runner.js,adapter-test-utils.js,fixtures/*.html}`、`src/package.json`、矩阵 `package.json` |
| 真机层 | `chrome-extension/tests/real-machine/dom-contract-probe.mjs` |
| 规程与工具 | `docs/REAL_MACHINE_REGRESSION.md`、`scripts/real_machine_regression.py`、`tests/unit/test_real_machine_regression.py` |
| CI | `.github/workflows/test.yml`（`chrome-extension-tests` job） |
| 记录 | `collaboration/tasks/TASK-P1-REALMACHINE-REGRESSION-PREP-001.md`、`collaboration/results/RESULT-P1-REALMACHINE-REGRESSION-PREP-2026-10-25.md`、`collaboration/results/real-machine-runs/**` |

## 验证结果

- 矩阵 `110/114 passed, 0 failed, 4 skipped`（4 条 skipped 是**如实标记**的
  「该平台没有第 3 个选择器」路径，不是假装通过）
- `npm run build` 通过
- `python3 -m pytest tests/ -q` → `3037 passed, 6 skipped`（0 failed）
- `python3 -m ruff check .` → `All checks passed!`
- 密钥扫描 → `[OK] no secrets found`
- 6/6 变异全部被抓

## 留给下一轮的事（如实记录，未做）

1. Gemini 的 `messageList` / `messageContent` 与真实停止按钮 aria-label **未在真机验证**；
2. 其余 9 个平台的 fixture 仍是手写 mock，**只有 Gemini 是真实 DOM 快照**；
3. ChatGPT / Claude.ai 需要已登录 profile 才能得出 L1 结论；
4. **L2（人工真实发送）三个平台全部 `not-run`**——本工单没做；
5. 「第一个外部用户」不在本工单范围内，路线门禁**仍然开启**。
