---
name: 富文本编辑器的内容在框架模型里——DOM 有字不等于站点收到了
description: Slate/ProseMirror/Quill 把内容存在自己的模型中，execCommand 只动 DOM ⇒ 站点读到「用户没输入」⇒ 发送按钮保持 disabled ⇒ 点它等于没点；修法是派发真的 beforeinput，判据靠零宽叶子等**结构**信号，另注意 role="textbox" 分支顺序与后台标签页不用 rAF
type: feedback
from: Agent
---

现代富文本编辑器（Slate / ProseMirror / Quill …）把内容存在**框架自己的模型**里，
DOM 只是投影。往 DOM 里塞字，站点读到的是「用户没输入」。

2026-10-26 真机实测（千问 `https://www.qianwen.com/`）：

| 注入方式 | 文字在 DOM | 零宽叶子还在 | 发送按钮 `disabled` |
|---|---|---|---|
| `execCommand('insertText')` | 有 | **在** | **`true`**（注入前后一样） |
| `beforeinput`（`inputType=insertText` + `data`） | 有 | 没了 | **`false`** |

⇒ 差别不在「有没有把字放进去」，而在**站点自己的模型有没有收到**。

**判据要靠结构，不能靠事件返回值**：框架处理 `beforeinput` 时会 `preventDefault()`，
但忽略它的编辑器也会冒泡 ⇒ `dispatchEvent()` 的返回值区分不了两者。
可靠信号是 DOM 结构：**零宽叶子（`data-slate-zero-width`）在 ⇔ 模型是空的**。
注意**不能**用 `textContent` 判空——占位符（千问的「向千问提问」）是叶子的**子节点**。

**两个更隐蔽的坑**：

1. **分支顺序**：千问的编辑区是
   `div[data-slate-editor="true"][role="textbox"][contenteditable="true"]`。
   若 `injectTextSmart` 把 `role="textbox"` 排在 `isContentEditable` **前面**，
   千问就走了纯 `execCommand` 那条路 ⇒ **把修复写在 `injectIntoContentEditable`
   里对千问是死代码**。任何「按元素特征分支」的注入函数，分支顺序本身就是缺陷面。
2. **等待不能靠 `requestAnimationFrame`**：它在**后台标签页里不触发** ⇒ 会把 Pack 流程卡死。
   用 `setTimeout(0)`（一个宏任务）。

**替换语义**：编辑器里已有内容时，只派发 `beforeinput(insertText)` 是**追加**。
要替换必须先把**模型**里的选区变成「全选」，而且**选区同步是异步的**：
实测「只等 `selectionchange`」不够，还要再等一个宏任务，
否则删除时模型选区仍是折叠的 ⇒ 只删掉一个字。

**Why:** 这类缺陷**在单元测试里完全看不出来**——
静态 fixture 只有 DOM 结构，没有「模型」，于是「DOM 里有字」冒充了「模型收到了」，
矩阵与接线测试长期全绿（见 `feedback_fixture_needs_behavior.md`）。

**How to apply:**
- 生产代码：清空 → 插入 → **校验模型文本**，收不到就**抛错**，不许留「看起来成功」的假象。
- 注入改成异步 ⇒ 改 `async` 并把**所有**调用点 `await`（漏一个就是静默不等待）。
- 真机复验要跑**生产链路**（SW → 内容脚本 → 注入），不要在页面里手写探针算法。
- 与 `feedback_fixture_needs_behavior.md`、`feedback_failure_must_not_be_swallowed.md` 一起读。
