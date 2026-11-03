---
name: Chrome 扩展真机验证只能由用户在真实 Chrome 完成
description: 2026-11-02 实测——IDE 内置 browser 工具只能开 URL、不能读页/点击/加载扩展，故永远无 [Prompt Pack] 日志，不能用于 L2；本机 9222 端口虽监听但 /json 返回 404，无法接管外部 Chrome；L2 的「人点发送」必须用户本人在真实 Chrome 完成
type: project
from: Agent
---

Chrome 扩展的真机回归（千问 `https://www.qianwen.com/` 等）**必须在用户自己打开的真实 Chrome 里做**，Agent 侧无法代替。2026-11-02 实测出的三条硬边界：

1. IDE 内置 `browser` 工具只接受 URL：能开页，但**不能读取页面内容、不能点击**，而且**不加载 Chrome 扩展** ⇒ 在里面永远看不到 `[Prompt Pack]` 日志，**不能用于 L2 观测**。
2. 本机 Chrome 虽在 **9222** 端口监听，但该端口的 `/json` 返回 **404**，不是可用的 DevTools 接口 ⇒ 无法列出或接管外部已打开的标签页。
3. 要让 Agent 接管需另起一个带 `--remote-debugging-port=9222` 的独立 Chrome 实例并自行加载 `dist` 扩展；代价是用户需重新登录 + 手动加载扩展，且 **L2 的「人点发送」仍必须由用户本人完成**（L2 观测器的设计前提就是「人点发送、脚本只读」）。

**Why:** 2026-11-02 为让千问站出现 `[Prompt Pack] Using adapter: qianwen`，补齐 manifest 的 `https://www.qianwen.com/*` host 匹配并重新构建产物后，真机仍无日志；排查到这一步才确认**扩展真机注入/适配器识别类问题在 Agent 侧没有可用观测面**。

**How to apply:**
- 谈 L2 / 真机 3 平台回归时，直接按「需用户在真实 Chrome 操作」排期，不要承诺 Agent 侧自行验证。
- 需要真机证据时，把用户的动作压缩成**一次可判定的操作**并给出成功标志（Console 里具体的日志串），而非让其反复回报中间态。
- 提「让我接管浏览器」的方案时同时说明代价：独立实例 + 重新登录 + 扩展需手动加载。
- 相关：`project_route_decision.md`（材料齐了，缺人）、`feedback_single_user_action_debugging.md`。
