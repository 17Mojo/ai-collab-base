# RESULT — 活跃五站点按实测（范例一）· 2026-11-18

- **执行时间**：2026-11-18 13:07–13:44（GMT+8；yuanbao 于 13:42 补跑对齐主题）
- **代码基线**：`origin/main` @ `ada4ceb`，在 worktree `/private/tmp/wt-g11` 执行
  （主工作区 HEAD 为 `36d9ec2`，落后 39 个提交，**不含 stepfun**，故不在主仓跑）
- **活跃五站**（`platform-freeze.mjs` 白名单唯一事实源）：`stepfun / yuanbao / chatglm / yiyan / kimi`
- **执行器**：`chrome-extension/tests/real-machine/l2-platform-auto.mjs`
  - Playwright `launchPersistentContext(headless:false)` + `--load-extension=dist`
  - 真实 `dist/` 扩展（本次重建，`npm run build`，13:07）
  - 持久登录 profile：`~/Library/Application Support/rm-qianwen-l2-profile`
- **被测 Pack**：`xiaohongshu-knowledge-creator`（8 步）
- **判档口径**：仅两条 —— `PASS`（`exec.success===true` 且 8 步全有产出且落 PNG）/ `FAIL`

## 0. 总判

| 平台 | 结果 | 步骤产出 | 投递方式 | status | 截图 | 回执 |
|---|---|---|---|---|---|---|
| stepfun | **PASS** | 8/8 | precise | completed | 589,546 B | `L2-nov18-stepfun.json` |
| yuanbao | **PASS** | 8/8 | precise | completed | 674,286 B | `L2-nov18-yuanbao.json` |
| chatglm | **PASS** | 8/8 | precise | completed | 607,022 B | `L2-nov18-chatglm.json` |
| yiyan | **PASS** | 8/8 | precise | completed | 715,883 B | `L2-nov18-yiyan.json` |
| kimi | **PASS** | 8/8 | precise | completed | 573,579 B | `L2-nov18-kimi.json` |

**五站 5/5 PASS，无 fail、无 timeout、无 not-run。** 每站均为真实浏览器、真实平台页面、真实发送按钮点按（生产代码 `content-script.js:303-308` 的 `button.click()`），并取回真实模型回复。

各站 `final_content` 实测首句（证明非 mock 占位）：

- stepfun：`📝点按式AI协作"省时间"是错觉？我实测一整天，省下的工夫全赔在核对上了…`
- yuanbao：`点按协作最反直觉的一点：它不替你点，只是把"该点哪"标得比你自己还准。你有没有过这种时候…`
- chatglm：`实测 200 次点按后确认：AI Collab Base 的卡顿，根源不在 AI 响应，而在每次点按后强制插入的 0.6…`
- yiyan：`点按实测AI Collab Base：多工具复杂任务直接压缩到3步内…`
- kimi：`逐项点过去才发现：会自己干活不算稀奇，该掏钱、该承诺之前会停下来问你的，才配叫智能体…`

## 1. 过程事实（含一次真实失败，不隐去）

1. **13:07 首次 stepfun 实测 FAIL**：`step_2_hook failed: Response timeout`。
   根因是 **stepfun 未登录**（profile 中 stepfun cookie 当时仅 4 条游客态），而脚本判据只看
   「输入框可见」，未登录首页同样有输入框 ⇒ **假阳性判定"已登录"** 后直接发消息而超时。
2. **13:13 扫码登录**：打开 `studio.stepfun.com`，用户在真机窗口完成登录；实测 `hasLoginEntry`
   由 true → false、`hasUserMenu` 由 false → true，`RESULT=LOGGED_IN`。
   登录态落盘：stepfun cookie 4 → 7 条，新增 `Oasis-Token`（`account.stepfun.com` / `studio.stepfun.com`）。
3. **13:15 重跑 stepfun PASS**；随后 yuanbao/chatglm/yiyan/kimi 依次 PASS。
4. **验证其余四站登录态**（独立探针，判据为「输入框可见 && 无登录入口 && 有用户菜单」）：
   四站均 `LOGGED_IN`，未再出现假阳性。
5. **一次操作瑕疵，已补跑修正**：首轮 yuanbao 漏传 `TOPIC`，用了 Pack 默认主题
   （"AI 智能体（Agent）到底是什么"），与其余四站不一致。**13:42 已用同一主题
   `AI Collab Base 点按实测 2026-11-18` 补跑**，`success:true`、8/8 步、`precise`，
   回执 `input.topic` 已核对为指定主题，截图同步覆盖（674,286 B）。五站主题现已一致。

## 2. 范例二~四：本次**未**获得点按实证，原因如下

| 范例 | 结论 | 磁盘证据 |
|---|---|---|
| 范例二 多平台并发注入 + 共识 + 风格注入 | **不可点按实测 —— 多平台执行器未接线** | `MultiPlatformExecutor` 仅 `multi-platform-executor.js:16` 定义、`:432` 导出；`executeAll` 只有类内自调用 `:341`；`src/` 全仓无 import；`dist/service-worker.js` 与 `dist/content-script.js` 各 **0 命中**；`public/popup.*` 无多平台 UI；`service-worker.js` 消息 switch 无多平台分支 |
| 范例三 多 Agent ACK 协议 | **无浏览器点按对象** | `agent_orchestrator.py`、`ack_protocol.py` 对 `playwright/chromium/page.` 引用数均为 **0**；该范例是 CLI + 状态机协议 |
| 范例四 NotebookLM 深度研究 | **REAL 通路不可达，且非活跃五站** | `notebooklm.py:49-62` 健康检查依赖 `builtins.mcp__plugin_notebooklm__get_health`（普通进程无此属性）；`integration_flags.py:22` 为 `IntegrationMode.FALLBACK`；五站白名单不含 NotebookLM |

因此 **"范例一至四全部点按实测"这一命题本次不成立**：成立的是范例一（五站 5/5 PASS），
范例二~四不具备点按条件，不能以任何替代证据充数。

## 3. 本次实测顺带发现的三条缺陷

> **立项状态（2026-11-18 回填）**：三条均已登记进 `known_gaps.json`，**不是「待登记」**：
> D1 → **N34**（P2 open）、D2 → **N35**（P3 open）、D3 → **N36**（P1 open）。
> 本节保留发现时的原始写法以便追溯，编号映射以本行为准；后续状态只看 `known_gaps.json`。
> 〔回填说明〕本节此前写「建议登记为独立 gap」，与磁盘不符——那三条在 `f8eeb0f` 就已入库，
> 是本节漏了交叉引用，导致读者以为尚未立项。2026-11-18 修正。

### D1（P2）登录判据假阳性：`composerVisible` 不能代表已登录 〔台账 N34〕

- 位置：`chrome-extension/tests/real-machine/l2-platform-auto.mjs:246-260`（`runOne` 的登录等待循环与断言；`:249-260` 是循环体到断言那一段）
- 事实：stepfun 未登录时 `composerVisible:true` 且 `hasLoginEntry:true`。脚本仅以输入框可见判定
  「已登录」，导致未登录时直接导入 Pack 发消息，浪费一轮真机并产出 `Response timeout`。
- 建议：判据改为 `composerVisible && !hasLoginEntry && hasUserMenu`（本次独立探针已验证该组合在
  五站均能正确区分），或改用 adapter 侧真实鉴权信号。

### D2（P3）冻结守卫日志误报：`!policy.active` 当成"已解冻" 〔台账 N35〕

- 位置：`chrome-extension/tests/real-machine/l2-platform-auto.mjs:391-394`
- 事实：PRECHECK 模式下 `PLATFORM` 默认仍是 `qianwen`（已移出白名单），`policy.active=false` ⇒
  打印 `⚠️ 冻结平台已按 ALLOW_FROZEN=1 放行: qianwen`，而环境变量 `ALLOW_FROZEN` **并未设置**。
  实际未打开 qianwen（预检只开 CANDIDATES 五站），属**日志误报**，但会误导排障者以为有人解冻过。
- 建议：条件改为 `policy.unfrozenBy !== null`；PRECHECK 模式下不对未使用的 `PLATFORM` 做该判定。

### D3（P1）范例二的核心链路未接线（详见 §2） 〔台账 N36〕

- `MultiPlatformExecutor` 是死代码，无任何生产入口。若文档/对外材料称"多平台并发共创可用"，
  与磁盘不符。
- **已登记（2026-11-18）**：`known_gaps.json` **N36**（P1 / open）。性质与 N31（Hook 脚本齐全
  但从未接线）同类——「文件存在 + 符号存在」但调用链没接上，自检全绿而能力为零。
  待裁定的仍是同一个岔路：接线上线，或明确标注未实现；倾向后者。
- 文档侧已同步：`docs/APPLICATION-EXAMPLES.md` 范例二阶段 1 已加〔修订注〕指向 N36。

## 4. 口径声明

- **这是机器判定，不是人工验收。** `success:true` 只证明「链路跑通且产出非空」，
  不代表内容质量合格、不代表产品验收通过。
- 截图与 JSON 为可机检证据；本报告不替代用户目检。
- ~~主仓基线（`36d9ec2`）不含 stepfun，若要把本次结论并回主仓，需先同步代码基线。~~
  **已办（2026-11-18）**：主仓已由 `36d9ec2` 同步至 `ada4ceb`（含 stepfun 与 N30），本报告与
  证据已随 `f8eeb0f` 入库；此后合并 `feat/wip-content-baseline-merge` 至 `0ae0c18`，
  `docs/APPLICATION-EXAMPLES.md` 的〔实测状态〕亦已回填。本条不再构成待办。

## 5. 证据清单

```
collaboration/results/real-machine-runs/evidence/
  L2-nov18-stepfun.{json,png}
  L2-nov18-yuanbao.{json,png}
  L2-nov18-chatglm.{json,png}
  L2-nov18-yiyan.{json,png}
  L2-nov18-kimi.{json,png}
  L2-precheck-2026-11-18.chatglm-kimi-stepfun-yiyan-yuanbao.json
```
