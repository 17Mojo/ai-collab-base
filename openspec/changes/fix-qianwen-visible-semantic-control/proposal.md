# Change Proposal: Fix qianwen Visible Semantic Control

## Why

`known_gaps.json` **N29**（P1 / open）记录：2026-11-18 活跃 5 站验证中，qianwen 的
`step_8_output` 会话重置从 11-11 的 `available=true / hidden-semantic / 12→0`
回落为 `available=false / click-no-effect / 6→6`。这是 N25 解冻 A/B 的前置阻断：
B 组判据要求 `available === true && after < before`，否则 32 步真实发送也拿不到有效结论。

磁盘证据给出三层因果：

**层 1 · 页面结构变了，不是代码 commit 回归。**
`new-session-control.js` 自 11-11 起未改。只读探针对比：

| 时间 | hover-reveal 外层祖先 | 外层 `div.newChatReveal-*` rendered |
|---|---|---|
| 11-11 | `pointer-events-none opacity-0` | false |
| 11-18 | 无这两个类，`pointer-events:auto / opacity:1` | true |

**层 2 · 生产选择器顺序因此踩中一个「同名容器」。**
`findNewSessionControl()` 原顺序是 adapter → 可见文案 → 隐藏语义。
可见文案层扫 `[class*="newChat"]`，而外层 `div.newChatReveal-*` 的类名正好命中，
其 `textContent` 也是「新对话」。11-11 它不可见所以被跳过；11-18 它可见，
于是先被返回并点击——但这个外层容器没有 click handler。
真入口 `div[data-session-switch-target="new-chat"]` 永远轮不到。

jsdom 用今天的 DOM 形状复现，结果逐字对上真机回执：

```
found.how = text-match
found.el  = <div class="newChatReveal-OikAdB newChatRevealFlat-hnO8At">…
handleNewSession = {"available":false,"strategy":"click-no-effect",
  "reason":"点了「新对话」但消息数没有下降（6 → 6）…","messageCountBefore":6,
  "messageCountAfter":6,"durationMs":910}
```

**层 3 · 真入口本身没坏。**
在持久化 profile 上打开一条历史会话（7 条消息），直接对
`[data-session-switch-target="new-chat"]` 调 `.click()`：1 秒内 URL 跳到 `/chat`，
消息数 7→0。所以问题只在「选错元素」，不在「点不动」。

## What Changes

- `findNewSessionControl()` 在「adapter」与「可见文案」之间插入一层
  **可见语义属性层**：只认 `HIDDEN_SEMANTIC_SELECTORS` 里属性直接声明了 new-chat 语义的元素，
  且必须通过 `isElementRendered`，命中返回 `how: "semantic"`。
- 新增共用判据 `semanticControlMatches()`：文案全等 / aria-label 全等 / 带 `new_chat` 的锚点。
  隐藏兜底层复用同一判据，避免两层对「什么算入口」的理解漂移。
- 隐藏兜底层**仍留在最后**：不因为新层而提前点击不可见元素，安全边界不变。
- 新增 1 条 jsdom 回归用例（今天的可视 hover 面板形状）与 1 条变异守护：
  清空可见语义层后，该用例必须变红。
- `known_gaps.json` N29 → closed，附真机前后对照证据。

## 明确不在本 change 范围

- **不改 adapter 的 `newChat` 表**。qianwen 的入口会随站点在可见 / hover 隐藏之间切换；
  写死选择器只会把问题从「容器抢答」换成「隐藏时命中不了」。语义层两种状态都覆盖。
- **不改文案表、不改 `NEW_SESSION_CONTROL_SELECTOR`**。放宽 `span` / `div` 会误点
  longcat 历史列表里的「新对话」诱饵（见 `deepseek-adapter.js` 的既有注释）。
- **不改 A/B 判据、不启动 N25 解冻**。本 change 只让活跃站的重置恢复可用。
  解冻仍需单独授权 + 冻结站登录态预检 + 32 步额度确认。
- **不改 `click-no-effect` 回执格式**。策略字段的语义保持原样；本次失败诊断靠 DOM 探针 +
  jsdom 复现完成，不需要趁机改回执契约。

## 验收标准（可机器判定）

1. jsdom 今天的可视 hover 面板形状下，`findNewSessionControl()` 返回真语义入口，
   `how === "semantic"`；`handleNewSession()` 报 `available:true / 6→0`。
2. 11-11 的隐藏态形状仍返回 `hidden-semantic`，行为不变。
3. 扩展全套 326 条测试全绿；变异检查全绿且新增那条被指定用例杀死。
4. 修复后 qianwen 完整 L2 真机：`success:true / 8/8 steps`，
   `sessionResets[0].available === true && messageCountAfter < messageCountBefore`，
   策略为 `semantic`，回执 `platformPolicy.unfrozenBy === null`。
5. 修复后其余 4 个活跃站完整 L2 真机同样满足第 4 条；冻结站未被触碰。
