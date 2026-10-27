---
task_id: TASK-P1-EDITOR-MODEL-INJECTION-001
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
created_at: 2026-10-26T10:25:00+08:00
acceptance_commands:
  - "cd chrome-extension && node --test tests/editor-injection.test.mjs"
  - "cd chrome-extension && node tests/run-tests.mjs"
  - "cd chrome-extension && node tests/adapter-matrix/adapter-test-runner.js"
  - "cd chrome-extension && npm run build"
result_file: collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md
---

# TASK-P1-EDITOR-MODEL-INJECTION-001：注入只改了 DOM，没进千问 Slate 编辑器**自己的模型** ⇒ 发送按钮永远禁用

> **本工单由 Claude Code（AGENT_EXEC）执行，CodeArts（AGENT_TEST）复核。**
>
> 来源：2026-10-26 的**外部用户排演**（W-D1），缺陷 #6——
> 六个缺陷里**唯一一个需要真机才能定位**的。
> 完整结果：[`collaboration/results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md`](../results/RESULT-EXTERNAL-USER-REHEARSAL-2026-10-26.md)

## 一、要解决什么

千问的输入框是 **Slate** 富文本编辑器。Slate 把内容存在**框架自己的模型**里，
DOM 只是投影。改前注入用的是 `execCommand('insertText')`——它**只动 DOM**
⇒ 站点读到的是「用户没输入」
⇒ **发送按钮保持 `disabled`**
⇒ 点它等于没点
⇒ 提示词永远留在输入框里 ⇒ 60 秒后超时。

真机实测（千问）：

| 注入方式 | 文字在 DOM | 零宽叶子还在 | 发送按钮 `disabled` |
|---|---|---|---|
| `execCommand('insertText')` | 有 | **在** | **`true`**（注入前后一样） |
| `beforeinput`（`insertText` + `data`） | 有 | 没了 | **`false`** |

⇒ 差别不在「有没有把字放进去」，而在**站点自己的模型有没有收到**。

### 两个更隐蔽的坑

1. **分支顺序**：千问的编辑区是
   `div[data-slate-editor="true"][role="textbox"][contenteditable="true"]`，
   而 `injectTextSmart` 把 `role="textbox"` 排在 `isContentEditable` **前面**
   ⇒ 千问走的是 `injectIntoTextbox`（纯 execCommand 路径）
   ⇒ **把修复写在 `injectIntoContentEditable` 里对千问是死代码**。
2. **替换语义**：编辑器里已有内容时，只派发 `beforeinput(insertText)` 是**追加**。
   要替换必须先把**模型**里的选区变成「全选」，而且**选区同步是异步的**：
   实测「只等 `selectionchange`」不够，还要再等一个宏任务，
   否则删除时模型选区仍是折叠的 ⇒ 只删掉一个字。

## 二、修法

新增 `chrome-extension/src/platforms/slate-editor.js`：**模型感知**的注入。

| 导出 | 作用 |
|---|---|
| `isSlateEditor(input)` | 是不是 Slate 编辑区 |
| `slateModelIsEmpty(input)` | 模型是不是空的（**零宽叶子**在 ⇒ 空；没有叶子 ⇒ 也空） |
| `slateModelText(input)` | 模型里的文本（扣掉占位符与零宽节点） |
| `injectIntoSlateEditor(input, text)` | 清空 → 插入 → **校验模型文本**，收不到就抛错 |

要点：

- **失败必须抛错**，不许留一个「看起来注入成功了」的假象；
- 等待用 `setTimeout(0)`（**不用 `requestAnimationFrame`**：它在后台标签页里不触发，
  会把 Pack 流程卡死）；
- `injectTextSmart` 改 `async`，Slate 分支**排到 `role="textbox"` 前面**，
  8 个调用点全部 `await`。

## 三、守护

`tests/editor-injection.test.mjs`（6 条）+ `tests/helpers/slate-site.mjs`（共享的站点仿真）。

仿真**只扮演第三方站点**（模型与选区的行为），判定一律由**生产代码**给出。
仿真结构照真机实测：模型与 DOM 分离、发送按钮读**模型**、
占位符是叶子的**子节点**、零宽叶子表示「这个段落是空的」。

> 静态 fixture（手写 mock 与真机快照）**只有结构没有行为**——
> 以前正是这一点让「DOM 里有字」冒充了「模型收到了」。
> 现在 fixture 也补上站点行为（矩阵、接线测试、注入守护共用同一份）。

**变异验证**（改坏被守护的代码，对应测试必须变红）：

| 变异 | 结果 |
|---|---|
| 把 Slate 分支挪到 `role="textbox"` 之后 | 6 条里 **5 条**变红 |
| Slate 路径退回 `execCommand` | 6 条里 **4 条**变红 |

## 四、真机复验

复验跑的是**生产链路**（不是页面里手写的探针）：

```
service worker → chrome.tabs.sendMessage(INJECT_TEXT)
  → 内容脚本（生产 dist 产物）→ injectTextSmart → slate-editor.js
    → beforeinput → 千问的 Slate 模型 → 发送按钮解禁
```

实测：模型文本 == 提示词、零宽叶子消失、发送按钮 `disabled` 变 `false`；
再注入一次是**替换**不是追加。

探针：`tests/real-machine/injection-path-probe.mjs`
（**只注入、不发送**，且必须显式 `--i-will-inject` 才跑）。
证据：`collaboration/results/real-machine-runs/evidence/L2-injection-qianwen-2026-10-26.json`。

> 该证据**只覆盖 L2 的注入环节**。L2 的「人工点发送 + 等回复」本轮**没有跑**
> ⇒ 千问的 L2 结论是 `not-run`，**不是** `pass`。

## 五、验收

见 frontmatter 的 `acceptance_commands`。全部必须**逐字**可跑并通过。

## 六、回滚

回退 `chrome-extension/src/platforms/slate-editor.js`（删除）、
`chrome-extension/src/platforms/adapter-utils.js`、
7 个 `*-adapter.js` 与 `chrome-extension/src/content/content-script.js`。

> 回滚提示：`injectTextSmart` 已改成 `async`。若只回退 `slate-editor.js`
> 而保留 `adapter-utils.js` 里的 async 改动，调用点仍需 `await`
> （`await` 一个非 Promise 是合法的，行为不变）⇒ **不会**因为半回滚而崩，
> 但模型感知的修复会失效。
