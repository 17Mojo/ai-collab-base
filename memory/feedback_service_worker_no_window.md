---
name: service worker 里没有 window——页面侧函数不能直接调
description: MV3 的 service worker 里 typeof window === "undefined"，后台调页面侧的 adapter.detect() 会抛 ReferenceError 并挂掉整个 onMessage 处理器⇒永远不 sendResponse⇒扩展在任何站点上都拿不到适配器且不报错
type: feedback
from: Agent
---

跨执行环境搬代码前，先问「这段代码依赖的东西**在这里**存在吗」。

2026-10-26 实测：后台 `getAdapter()` 调了 `adapter.detect()`，
而 `detect()` 是**页面侧**函数（读 `window.location.hostname`）。
MV3 的 **service worker 里没有 `window`**（实测 `typeof window === "undefined"`）
⇒ 抛 `ReferenceError: window is not defined`。

**为什么后果被放大到整条链路死掉**：那个异常发生在
`chrome.runtime.onMessage` 的处理器里 ⇒ **整个处理器挂掉 ⇒ 永远不调用 `sendResponse`**
⇒ 内容脚本初始化时问的 `GET_ADAPTER` 收不到回答 ⇒ `currentConfig` 恒为 null
⇒ 之后每次 `SEND_TO_AI` 都抛「No adapter available for this page」。
**改之前，扩展在任何一个站点上都拿不到适配器，而且不报任何错。**

**Why:** `window` 这种「到处都有」的东西，换个执行环境就没了——
类型检查与单元测试都发现不了（测试环境里 jsdom 有 `window`）。
症状又被下游的「没适配器」兜住，进一步掩盖了真正的断点。

**How to apply:**
- 后台**只按 URL 判定**（从发消息过来的那个标签页的 URL 取主机名）；
  `detect()` 保留给页面侧用。
- 守护测试要覆盖**全部平台**（别只测一个），外加一条
  「不是 AI 站点的 URL 不该被认成任何平台」——防把「什么都认」测成通过。
- 与 `feedback_chrome_host_pattern.md`、`feedback_single_validation_authority.md` 并排读。
