---
task_id: TASK-P1-SW-DETECT-PAGE-CODE-001
change_id: bugfix/no-spec
status: completed
priority: P1
assignee: claude_code
assignee_role: AGENT_EXEC
reviewer: codearts_agent
primary_skill: api-test-pro
support_skills:
  - testing
created_at: 2026-10-26T10:05:00+08:00
acceptance_commands:
  - "cd chrome-extension && node --test tests/external-user-path.test.mjs"
  - "cd chrome-extension && node tests/run-tests.mjs"
result_file: collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md
---

# TASK-P1-SW-DETECT-PAGE-CODE-001：后台在 service worker 里调页面侧的 `detect()` ⇒ 扩展在任何站点上都拿不到适配器

> **本工单由 Claude Code（AGENT_EXEC）执行，CodeArts（AGENT_TEST）复核。**
>
> 来源：2026-10-26 的**外部用户排演**（W-D1），缺陷 #2。
> 完整结果：[`collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md`](../results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md)

## 一、要解决什么

后台 `getAdapter()` 原来长这样：

```js
if (url.includes(platform) && adapter?.detect?.()) { ... }
```

`detect()` 是**页面侧**函数——它读 `window.location.hostname`。
而这个函数跑在 **service worker** 里：MV3 的 SW **没有 `window`**
（2026-10-26 实测：`typeof window === "undefined"`）
⇒ `adapter.detect()` 抛 `ReferenceError: window is not defined`。

那个异常发生在 `chrome.runtime.onMessage` 的处理器里 ⇒
**整个处理器挂掉 ⇒ 永远不调用 `sendResponse`**
⇒ 内容脚本初始化时问的那句 `GET_ADAPTER` 收不到回答
⇒ `currentConfig` 恒为 null
⇒ 之后每一次 `SEND_TO_AI` 都抛「No adapter available for this page」。

也就是说：**改之前，扩展在任何一个站点上都拿不到适配器**——
整条 Pack 链路是死的，而且**不报任何错**（只是「没适配器」）。

## 二、修法

后台改成**只按 URL 判定**：从发消息过来的那个标签页的 URL 取主机名，
按注册表的域名片段做子串判定（注册表的 key 本来就是「URL 中匹配的域名片段」，
与各 adapter 自己 `detect()` 里的写法一致，例如 `www.qianwen.com` 命中 `qianwen.com`）。

`detect()` **仍然保留**——它是**页面侧**该用的函数（content-script 在用），
只是**不许**在 service worker 里调。

> 教训：跨执行环境（SW ↔ 页面）搬代码前，先问「这段代码依赖的东西在这里存在吗」。
> `window` 这种「到处都有」的东西，换个环境就没了。

## 三、守护

`tests/external-user-path.test.mjs`：

- 后台对**每一个**平台都能从 URL 认出适配器（**别只测一个**——
  只测一个的话，漏掉的平台照样绿）；
- **不是 AI 站点的 URL 不该被认成任何平台**（防把「什么都认」测成通过）。

## 四、验收

见 frontmatter 的 `acceptance_commands`。全部必须**逐字**可跑并通过。

## 五、回滚

回退 `chrome-extension/src/background/service-worker.js` 即可。
注意：回滚会让扩展重新变成「在任何站点上都拿不到适配器」，
所以**不要**在别的缺陷依赖这条链路的前提下单独回滚。
