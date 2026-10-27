---
task_id: TASK-P1-PACK-FAILURE-SWALLOWED-001
change_id: bugfix/no-spec
status: completed
priority: P1
assignee: claude_code
assignee_role: AGENT_EXEC
reviewer: codearts_agent
primary_skill: api-test-pro
support_skills:
  - testing
created_at: 2026-10-26T10:20:00+08:00
acceptance_commands:
  - "cd chrome-extension && node --test tests/external-user-path.test.mjs"
  - "cd chrome-extension && node tests/run-tests.mjs"
result_file: collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md
---

# TASK-P1-PACK-FAILURE-SWALLOWED-001：失败被跨层吞掉 ⇒ popup 显示「执行成功」而产物是空的

> **本工单由 Claude Code（AGENT_EXEC）执行，CodeArts（AGENT_TEST）复核。**
>
> 来源：2026-10-26 的**外部用户排演**（W-D1），缺陷 #5。
> 完整结果：[`collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md`](../results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md)

## 一、要解决什么

失败是在**三层之间**被吞掉的，每一层都只做了一半：

| 层 | 改前的行为 | 问题 |
|---|---|---|
| 内容脚本 | 如实回 `{success:false, error}` | ✅ 没问题 |
| 执行器 | 把回话**原样返回**，紧接着**无条件** `stepResult.success = true` | ❌ 失败被改成成功 |
| 后台 | 一律回 `sendResponse({success:true, result})` | ❌ 失败被改成成功 |

排演实测（修好前 3 处断点之后，在**匿名会话**下）：
popup 显示「状态: 执行成功」，**而页面上提示词还留在输入框里**（压根没发出去），
页面上还有「登录」两个字。

⇒ 外部用户**无法判断哪一步坏了**，还会以为链路通了。

## 二、修法

1. **执行器**：`assertAIStepSucceeded()` 在 try/catch **外面**校验 AI 步骤回执，
   失败就抛。放在外面是刻意的——否则它的错误信息会被上面的
   「无法把提示词发到标签页」再包一层，读起来像消息没送到。
2. **后台**：看 `result.status === "failed"` 时回 `{success:false, error}`，
   不再一律回 `success:true`。

## 三、守护

`tests/external-user-path.test.mjs`：

- 内容脚本报失败 ⇒ **整个 Pack 必须失败**（不许 popup 显示「执行成功」）；
- **内容脚本成功时 Pack 必须成功**——防把这条守成「永远失败」的假绿。

## 四、验收

见 frontmatter 的 `acceptance_commands`。全部必须**逐字**可跑并通过。

## 五、回滚

回退 `chrome-extension/src/background/service-worker.js` 与
`chrome-extension/src/background/pack-executor.js`。
回滚后「假成功」会回来——**这个缺陷比它修掉的症状更危险**。
