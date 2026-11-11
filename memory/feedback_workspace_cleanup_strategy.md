---
name: 工作区清理与提交策略
description: 2026-11-09 项目体检中的工作区清理模式——未跟踪目录加入 gitignore、Conventional Commits 提交、提交前验证
---

2026-11-09 项目体检中发现工作区存在未提交改动，执行清理流程：

**工作区状态：**
- 未暂存修改：`service-worker.js`、`service-worker-harness.mjs`、`mutation-check.mjs`、`extension-wiring.test.mjs`
- 未跟踪文件：`.arts/` 目录、`default-packs.js`

**清理策略：**
1. `.arts/` 是工具生成目录，加入 `.gitignore`
2. `default-packs.js` 是新架构文件，应提交
3. 其他修改是 N11 功能的一部分，应提交

**提交规范：**
- 使用 Conventional Commits：`feat(n11): 孤儿 pack_id 残留可见化`
- 提交前验证：`git diff --stat HEAD` + `git log --oneline -1`
- 提交后验证：`git status` 确认工作区干净

**Why:** 工作区脏状态会影响测试结果（新文件/修改未纳入版本控制），提交前验证确保提交内容正确

**How to apply:**
- 清理工作区时先区分"应忽略"（工具生成）与"应提交"（功能改动）
- 提交前用 `git diff --stat HEAD` 核对改动统计
- 遵循 Conventional Commits 规范写 commit message