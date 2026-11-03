---
name: 重活校验跑在独立 worktree，不碰用户工作区
description: 用户工作区有未提交改动时，全套校验/构建/大 diff 必须放 git worktree 里做；结论必须标注基线 commit（HEAD 还是 main），差异大时以目标分支为准重查
type: feedback
from: Agent
---

**用户工作区有未提交改动时，任何跑全套校验项、构建、真机对照这类重活都放 `git worktree add` 出来的独立目录里做，绝不碰用户工作区；结论必须写清基于哪个 commit。**

**Why:** 2026-11-03 架构审计第一轮是在本地 HEAD 上分析 `chrome-extension/` 得出的结论，被作废——main 上该目录相对 HEAD 多出数十个文件、上万行，"基于旧代码下判断"几乎必然错。用户因此纠正过根因判断，并主动要求用 worktree 隔离复跑。

**How to apply:**
- 动手前先看工作区状态；有未提交改动 → 直接上 worktree，别在用户目录里跑构建/大规模 diff。
- 先量 HEAD 与目标分支的差异量级（文件数/行数），量级大就先重查再下结论，别把上一轮分析当现状。
- 报告里把"worktree/commit 基线"写成结论的一部分；跨版本差异大时明确说明"上一轮分析基于旧代码"。
- 收尾时清理临时 worktree，保持用户工作区干净（本次用户明确要求过）。
