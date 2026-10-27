---
task_id: TASK-P1-MANIFEST-HOST-PATTERN-001
change_id: bugfix/no-spec
status: completed
priority: P1
assignee: claude_code
assignee_role: AGENT_EXEC
reviewer: codearts_agent
primary_skill: api-test-pro
support_skills:
  - testing
  - documentation
created_at: 2026-10-26T10:00:00+08:00
acceptance_commands:
  - "cd chrome-extension && node --test tests/external-user-path.test.mjs"
  - "cd chrome-extension && node tests/run-tests.mjs"
  - "cd chrome-extension && npm run build"
result_file: collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md
---

# TASK-P1-MANIFEST-HOST-PATTERN-001：manifest 的 host 模式漏了 `www.` 变体 ⇒ 内容脚本根本没注入

> **本工单由 Claude Code（AGENT_EXEC）执行，CodeArts（AGENT_TEST）复核。**
>
> 来源：2026-10-26 的**外部用户排演**（W-D1）——照着《第一次试用指南》以第一次用的
> 人的身份走一遍，步骤 3 直接断掉。
> 完整结果：[`collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md`](../results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md)（缺陷 #1）。

## 一、要解决什么

`manifest.json` 里写的是：

```json
"https://qianwen.com/*"
```

而千问的真站是 **`https://www.qianwen.com/`**。

**Chrome 的 host 匹配规则**：`qianwen.com` **只等于它自己**，不等于 `www.qianwen.com`
——只有 `*.qianwen.com` 才是通配（且它也不覆盖裸域）。
⇒ 内容脚本**根本没有注入**到真站上
⇒ 在那个页面上，扩展等于没装（而且**不报任何错**，只是「没适配器」）。

同一个坑还有 Kimi（真站 `www.kimi.com`，写的却是 `kimi.com`）。

## 二、修法

1. `host_permissions` 与 `content_scripts.matches` **补齐 `www.` 变体**；
2. 两处**收敛成同一份清单**（不许各写一份——各写一份就迟早会漏），
   清单由 `manifest.json` 单点持有，`static-assets.cjs` 生成产物 manifest 时复用它；
3. 产物里的 `manifest.json` **必须由源 `manifest.json` 生成**（不许手写第二份），
   并有测试逐字段核对。

## 三、守护

`tests/external-user-path.test.mjs`：

- 按 **Chrome 的 host 匹配规则**（`*.` 才通配）**逐个平台**核对覆盖；
- 断言 `host_permissions` 与 `content_scripts.matches` **是同一份清单**；
- 断言构建产物里的 manifest 是由源文件生成的。

## 四、验收

见 frontmatter 的 `acceptance_commands`。全部必须**逐字**可跑并通过。

## 五、回滚

回退 `chrome-extension/manifest.json`、`chrome-extension/static-assets.cjs`、
`chrome-extension/build.js` 三个文件即可，本缺陷与其它 5 个缺陷**互不依赖**。
回滚后必须重新 `npm run build`，否则浏览器里跑的还是旧产物。
