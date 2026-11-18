# 2026-10-25 真机回归覆盖面扩张（探针 10 平台 + 真实快照 + L2 观测器）

**任务**: `TASK-P1-REALMACHINE-COVERAGE-EXPAND-001`
**执行**: Claude Code（AGENT_EXEC）
**分支**: `feat/realmachine-coverage-expand`（基线 `main` @ `71c9eac`）
**并行工单**: `TASK-P1-NODE-MODULES-UNTRACK-001`（独立分支 `chore/untrack-node-modules`）

---

## 这轮最重要的一件事

不是「多测了几家平台」，而是：

> **110/114 全绿的模拟层矩阵，掩盖了 4 个真机上才暴露的生产缺陷。**

绿不是因为对，是因为没测到。所以本轮的主线是**让测试具备发现能力**，
覆盖面扩张只是副产品。

4 个缺陷：

| 平台 | 缺陷 | 后果 |
|---|---|---|
| 文心一言 | `messageList` 含 `[class*="chat"]` | 真机命中 37 个界面外壳 ⇒ 计数失真 |
| 腾讯元宝 | 同上 | 真机命中 8 个 ⇒ 计数失真 |
| Kimi | `typingIndicator` 含 `[class*="loading"]` | 命中 9 个侧边栏骨架屏 ⇒ `isTyping()` 恒为 true ⇒ **每次发送必然 60 秒超时** |
| ChatGLM | 同上 | 命中「正在加载...」占位条 ⇒ 同上 |

后两条是最严重的：**Pack 在这两家平台上根本发不出去**，而模拟层对此毫无察觉。

## 走错的一段路（记下来）

修 Kimi/ChatGLM 的打字指示器时，第一反应是「零尺寸元素不算命中」——
加个 `getBoundingClientRect()` 的尺寸检查。**实测数据否掉了这个方案**：
Kimi 的骨架屏是 224×224，ChatGLM 的占位条是 239×32 且**带可见文字**，
尺寸检查根本分不开。最后靠**收窄选择器**修。

> 教训：能靠测量否掉的方案，就别靠论证。
> （这也是 `memory/feedback_empirical_test_before_solution_choice.md` 那条。）

## 两条新引入的不变量

都是**在真机上量出来的**，不是设计出来的：

1. **无会话即无消息** —— 落地页上 `messageList` 命中的元素必须**全部无文本**。
   不用「消息数必须是 0」，是因为 Kimi 的 `message-list-container` 是个**空容器**，
   它把计数抬高了但不影响增长检测；真正致命的是命中**有内容的界面外壳**。
2. **空闲即不忙** —— 空闲落地页上 `isTyping()` 必须是 `false`。
   违反它 ⇒ `waitForResponse` 的 `!isTyping()` 永远不成立 ⇒ 必然超时。

判定逻辑拆成纯函数（`message-model.mjs`）以便进单测；
采集脚本只负责喂数据。

## L2 观测器的设计取舍

**缺口 #8「回复等待链路」从来没被机器验证过**——而这恰恰是 Pack 能不能用的关键。

- 纯人工（截图留证）：**截图证明不了「取回来的正文非空」**。界面上有字 ≠ adapter 取到了那段字。
- 纯自动（脚本自己打字点发送）：违反「探针永不发送」红线。

所以取中间：**人点一次发送，脚本负责其余的一切**。脚本全程只读 DOM，
同时**并行跑生产代码里的 `waitForResponse`**，产出可机检的 JSON 而不是截图。

产出里 `verdict.wouldResolve` 直接回答「生产的等待逻辑在这条真实时间线上会不会成功」。

## 变异检查（本轮最该留下的东西）

一套全绿的测试**什么都不能证明**，除非能证明「改坏被守护的那处代码，对应测试会变红」。

`mutation-check.mjs` 把「守护关系」变成 CI 里的可执行断言：12 条变异，
每条对应一个具体缺陷，要求**指定的那条测试**因此报错——不是「随便哪条红」就算数。

变异在**临时副本**上做（`chrome-extension/.mutation-tmp/`），工作区一个字节都不动。
（第一版就地改坏再还原，中途崩了就留下半个坏文件——改成副本更稳。）

## 自曝：自己写的测试是空转的

「class 属性不做长随机串脱敏」这条用例用了 20 字符的类名，
而令牌规则是 **40 字符起**才触发——**这条用例从来没测到任何东西**。
已改成 40+ 字符的类名，并补了变异条目确认它真的有牙齿。

> 一个测试文件自己都可能空转。这就是为什么要做变异检查。

## 踩到的 `node --test` 三种坑

| 写法 | 结果 |
|---|---|
| `node --test`（自动发现） | 扫进 `tests/playwright/node_modules` 的第三方测试，**本机实测直接卡死** |
| `node --test tests/real-machine/` | Node 23 报 `MODULE_NOT_FOUND`（目录形式不被接受） |
| `node --test "tests/**/*.test.mjs"` | 要 Node 21+，而 CI 钉的是 Node 20 |

最后自建 `tests/run-tests.mjs`：枚举文件、显式传路径，Node 18+ 通用，
本地与 CI 同一条命令。

## 范围拆分

用户明确要求「C-1（node_modules）**必须独立成工单，不与缺陷修复混在一起**」。

做法：C-1 走**独立分支 + 独立 worktree**（`/tmp/rm-c1`），
本工单的 diff 里一个 `node_modules` 字都没有。两个 PR 各自独立评审与合并。

## 交付物清单

| 类别 | 文件 |
|---|---|
| 生产修复 | `chrome-extension/src/platforms/{yiyan,yuanbao,kimi,chatglm}-adapter.js` |
| 单一事实源 | `chrome-extension/tests/platforms.mjs` |
| 一致性守护 | `chrome-extension/tests/platform-registry.test.mjs`、`chrome-extension/tests/ci-wiring.test.mjs` |
| 真实快照 | `chrome-extension/tests/real-machine/snapshot-capture.mjs`、`sanitize.mjs`、`message-model.mjs`、`fixtures/real/**`（7 家） |
| L2 观测器 | `chrome-extension/tests/real-machine/l2-send-observer.mjs`、`l2-model.mjs` |
| 变异检查 | `chrome-extension/tests/real-machine/mutation-check.mjs` |
| 单测入口 | `chrome-extension/tests/run-tests.mjs` |
| 矩阵增强 | `chrome-extension/tests/adapter-matrix/{adapter-test-runner,adapter-test-utils}.js` |
| 文档 | `docs/REAL_MACHINE_REGRESSION.md`（§4.4、§6 重写、附录 A） |
| CI | `.github/workflows/test.yml`（新增 2 个步骤） |
| 记录 | `collaboration/tasks/TASK-P1-REALMACHINE-COVERAGE-EXPAND-001.md`、`collaboration/results/RESULT-P1-REALMACHINE-COVERAGE-EXPAND-2026-10-25.md` |

## 验证结果

- 单测 `80/80`；变异检查 `12/12` 变异被杀死
- 矩阵 `109/114 passed, 0 failed, 5 skipped`（skip 是**诚实跳过**，有原因）
- `npm run build` 通过；`pytest tests/` → `3038 passed, 6 skipped`
- ruff `All checks passed!`；密钥扫描 `0 命中`

## 留给下一轮的事（如实记录）

1. **消息气泡选择器仍未在真机验证**（7 家）——落地页证不了「能命中真气泡」；
2. **Kimi/ChatGLM 的真实「生成中」指示器未验证**——若都不命中，等待可能**中途提前返回**（半截回复）；
3. **L2 从未真跑过**——观测器已交付，真跑需要人 + 已登录 profile；
4. **后台↔内容脚本的消息协议有洞**（`SEND_TO_AI` 无人处理、`GET_LATEST_RESPONSE` 无人处理、
   `pageState.isTyping` 字段不存在）——P0 级产品缺陷，性质与 DOM 契约不同，
   **本工单未处理，处置决策待定**；
5. 千问的 `messageList` 落地页命中 0 个——依赖 B-3（用快照定选择器）；
6. 路线门禁**仍然开启**（「第一个外部用户」不在本工单范围）。
