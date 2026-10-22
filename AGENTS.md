# AGENTS.md — 双 Agent 协作规则入口

本文件是 Claude Code 与 CodeArts 的**共同规则入口**。完整协作规则以同目录 `CLAUDE.md` 为单一事实源。
本文件保留机读的必读文件清单，供 `scripts/validate_collaboration_governance.py` 校验。

## 必读文件（机读清单）

以下每行须为**纯相对路径**（不得加 `-`、反引号、引号或任何前缀），校验脚本按整行精确匹配。

collaboration/AI_BEHAVIOR_CONSTRAINT_FILES.md
collaboration/COLLABORATION_GUIDELINES.md
collaboration/PROTOCOL.md
rules/AI-COLLABORATION-STANDARDS.md

## 共享记忆

- 记忆镜像事实源：`memory/`（由 CodeArts 记忆单向同步生成，只读）
- 索引：`memory/MEMORY.md`
- 同步命令：`python3 scripts/sync_agent_memory.py`
- 校验命令：`python3 scripts/sync_agent_memory.py --check`