---
task_id: TASK-P1-PACK-IMPORT-GATE-001
change_id: bugfix/no-spec
status: completed
priority: P1
assignee: claude_code
assignee_role: AGENT_EXEC
reviewer: codearts_agent
primary_skill: api-test-pro
support_skills:
  - testing
created_at: 2026-10-26T10:10:00+08:00
acceptance_commands:
  - "cd chrome-extension && node --test tests/external-user-path.test.mjs"
  - "cd chrome-extension && node tests/run-tests.mjs"
result_file: collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md
---

# TASK-P1-PACK-IMPORT-GATE-001：导入界面比后台更严 ⇒ 指南里的导入步骤根本走不通

> **本工单由 Claude Code（AGENT_EXEC）执行，CodeArts（AGENT_TEST）复核。**
>
> 来源：2026-10-26 的**外部用户排演**（W-D1），缺陷 #3。
> 完整结果：[`collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md`](../results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md)

## 一、要解决什么

| 判定方 | 接受的形状 |
|---|---|
| 后台 `IMPORT_PACKS` | `{packs:[...]}` **和** 单个 Pack（`{metadata:{...}}`） |
| 前端 `pack-editor.js`（改前） | **只有** `{packs:[...]}` |

前端**比后台更严** ⇒ 外部用户照指南导入
`packs/examples/external-user-smoke.json`（**单个 Pack**）时，
前端直接报「文件格式错误: 无效的 Pack 导入格式」
⇒ 连「合并 / 覆盖」两个选项都出不来 ⇒ **指南第 4 步直接断掉**。

## 二、修法

前端**只做语法检查**（是不是 JSON），「什么算 Pack」**只有后台一个判定方**。

> 教训：前端多一道闸 = **两个判定方** = 迟早漂移。
> 这次漂移的方向还是「前端比后台严」——那等于把后台已经认的东西挡在门外。

## 三、守护

`tests/external-user-path.test.mjs`：

- 单个 Pack 文件**不该**被判成格式错误（在 jsdom 里跑**生产**的 Pack 编辑器）；
- **真的不是 JSON 仍然要报错**——防把闸门拆成没有闸门。

## 四、验收

见 frontmatter 的 `acceptance_commands`。全部必须**逐字**可跑并通过。

## 五、回滚

回退 `chrome-extension/public/pack-editor.js` 即可。
回滚后前端会重新比后台更严，指南第 4 步会重新断掉。
