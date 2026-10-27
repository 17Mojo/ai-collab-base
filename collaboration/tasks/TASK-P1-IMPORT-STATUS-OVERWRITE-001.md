---
task_id: TASK-P1-IMPORT-STATUS-OVERWRITE-001
change_id: bugfix/no-spec
status: completed
priority: P1
assignee: claude_code
assignee_role: AGENT_EXEC
reviewer: codearts_agent
primary_skill: api-test-pro
support_skills:
  - testing
created_at: 2026-10-26T10:15:00+08:00
acceptance_commands:
  - "cd chrome-extension && node --test tests/external-user-path.test.mjs"
result_file: collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md
---

# TASK-P1-IMPORT-STATUS-OVERWRITE-001：导入成功的标志一闪就没了

> **本工单由 Claude Code（AGENT_EXEC）执行，CodeArts（AGENT_TEST）复核。**
>
> 来源：2026-10-26 的**外部用户排演**（W-D1），缺陷 #4。
> 完整结果：[`collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md`](../results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md)

## 一、要解决什么

《第一次试用指南》步骤 4 的**成功标志**是：

> 页面底部的状态栏显示 `导入成功: 1 个 Pack`。

而生产代码的顺序是：

```js
updateStatus(`导入成功: ${n} 个 Pack`, 'success');   // 先报成功
await loadPacks();                                    // 后刷新列表
```

`loadPacks()` 会把状态栏改写成「已加载 N 个 Pack」
⇒ **指南承诺的成功标志一闪就没了**
⇒ 外部用户停下来看状态栏时，看到的是「已加载 1 个 Pack」——
这句话**既没说导入成功，也没说导入的是哪个**。

这类缺陷测不出来，是因为「提示过这句话」≠「这句话留得住」。

## 二、修法

**先刷新列表、再报导入成功**：把顺序倒过来，状态栏最终停在成功标志上。

## 三、守护

`tests/external-user-path.test.mjs`：
选完文件点「确认导入」后，状态栏要出现**指南承诺的那句话**——
断言的是**最终状态**，不是「曾经出现过」。

## 四、验收

见 frontmatter 的 `acceptance_commands`。必须**逐字**可跑并通过。

## 五、回滚

回退 `chrome-extension/public/pack-editor.js` 即可
（与 [`TASK-P1-PACK-IMPORT-GATE-001`](TASK-P1-PACK-IMPORT-GATE-001.md) 改的是同一个文件，
两处改动彼此独立）。
