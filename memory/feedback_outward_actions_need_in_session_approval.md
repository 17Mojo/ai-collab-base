---
name: 对外可见动作需要当前会话内的明确授权
description: 2026-10-24 实测——gh pr create 被 auto-mode 分类器以「Unrequested Commit in a Connected App」拦下，理由是授权只出现在被压缩的会话摘要里而非当前轮次；解决办法是先用 AskUserQuestion 拿到用户当场的明确授权再重试
type: feedback
from: Agent
---

## 现象（2026-10-24 实测）

用户在本轮之前的某轮说过「选项 2 ……之后直接开 PR 触发 CI」。该轮被压缩后，
上下文里只剩摘要。执行 `gh pr create --base main --head <branch>` 时，
auto-mode 分类器直接拒绝：

> Permission denied ... [Unrequested Commit in a Connected App]
> `gh pr create` publishes a collaborator-visible PR and triggers CI, and the only
> claimed approval is inside an assistant-written compaction summary; explicit user
> authorization to open this PR from `<branch>` to `main` would clear it.

**关键点**：分类器只认**当前会话里用户明确说过的授权**，**压缩摘要不算**——
它无法区分「摘要里引用了用户原话」和「助手自己写的结论」。

## 怎么做

1. 遇到这类拦截，**不要**换工具绕过（`gh api`、curl 等）——那是在规避意图。
2. 用 `AskUserQuestion` 把要做的对外动作摆到用户面前，请当场确认。
   用户的当轮确认即构成分类器认可的授权。
3. 确认后原样重试即可（分类器放行后命令本身没问题）。

## 适用范围

不只是 PR：任何**对外可见 / 会触发外部副作用**的动作都可能被同类规则拦下——
发 PR、发评论、触发部署、发布包、给外部账号发消息。
判断标准是「这件事一旦发生，仓库协作者或外部系统会看到，且事后不易无声撤回」。

## Why

这类拦截不是障碍，是**提醒**：会话被压缩后，助手对自己获得过的授权失去了可验证的凭据。
与其猜，不如再问一次——代价是一次对话轮，收益是不会在没授权的情况下把内容推到别人眼前。

**相关**：[[feedback_ci_isolation_trap]]
