---
name: 双 Agent（CodeArts + Claude Code）配置一致性与实时同步核查
description: 2026-10-22 核查结论：CodeArts 与 Claude Code 的规则文件/记忆目录既无 symlink 也无任何同步机制；治理门禁期望根 AGENTS.md 但缺失；用户目标是「配置信息一致 + 链接 + 实时同步」
type: project
from: Agent
---

用户在该项目**同时使用两个 Agent：CodeArts 与 Claude Code**，并于 2026-10-22 提出目标：**核查两者配置文件（`Agent.md`、记忆等）是否已链接并可实时同步**。同日核查结论为**证伪**——两者既无符号链接，也无任何同步机制（无 symlink / 无 git hook / 无 sync 脚本）。

## 核查真证（2026-10-22，分支 `refactor/slimming-2026-09-20`）

| 维度 | Claude Code | CodeArts |
|---|---|---|
| 规则文件 | 根 `CLAUDE.md`，已 git 跟踪 | `.codeartsdoer/AGENTS.md` 仅 8 行、只含 `Language: Python`，被 `.gitignore` 忽略未入库；同时本会话也注入了根 `CLAUDE.md` |
| 记忆 | `~/.claude/` 内无 memory 目录、无 `~/.claude/CLAUDE.md`；项目记忆即 `CLAUDE.md` 手工段 | `~/.codeartsdoer/memory/<项目slug>/`（`MEMORY.md` + user/project/feedback/reference，2026-10-22 实为 10 个文件） |

- 两套规则文件与两套记忆**均为普通文件、独立存储，且位于仓库之外**，故任何一侧改动都不会传导到另一侧。
- 唯一共同事实源是根 `CLAUDE.md`（两者都读）；`AGENTS.md` 是 CodeArts 独有空壳。
- **治理缺口**：`scripts/validate_collaboration_governance.py` 期望根目录存在 `AGENTS.md`，实际缺失 → 报 `missing_agents_reference`。
- **索引漂移**：CodeArts 记忆目录内的 `feedback_no_ceremony_tax.md`、`feedback_validator_false_positive.md`、`project_route_decision.md`、`project_hermes_port_line.md`、`reference_local_llm_endpoint.md` 等未被 `MEMORY.md` 收录，索引滞后于实际文件。

## 应做项（按用户目标反推，2026-10-22 给出，尚未落地确认）

| 优先级 | 应做项 |
|---|---|
| P0 | 规则单一事实源：`AGENTS.md` ↔ `CLAUDE.md` 链接，两 Agent 读同一份 |
| P0 | 记忆统一存储并链接：CodeArts 记忆目录 ↔ Claude Code 可读路径 |
| P0 | 加同步机制（git hook / 生成脚本）——「实时同步」是硬需求，只做链接仍会漂移 |
| P1 | 修复 `MEMORY.md` 索引漂移（补录已存在但未收录的文件） |
| P1 | 处理 `.codeartsdoer/AGENTS.md` 空壳 + 决定是否纳入版本控制 |

**待验证（不可裸承诺）**：软链方向能否被两端识别（需实测 CodeArts 是否读根 `AGENTS.md`、Claude Code 是否读 `~/.claude/CLAUDE.md`）；两侧记忆格式不兼容（CodeArts 带 frontmatter + `MEMORY.md` 索引，Claude Code 无原生记忆源），可能需要**生成**而非纯软链。

**Why**: 用户明确要求两个 Agent 的配置信息一致并能实时同步；工程侧已存在治理门禁在等根 `AGENTS.md`，补齐可顺带消除 `missing_agents_reference`。

**How to apply**: 涉及规则文件或 Agent 记忆的改动前，先确认该路径当前归属哪个 Agent、是否入库、以及是否与另一侧存在重复副本；不要假设「已同步」——2026-10-22 核验证明假设会被证伪。若实现同步，优先做「链接可行性实测」再定软链 vs 生成脚本。

## 落地结果（2026-10-22，分支 `feat/codearts-collab-wiring`）

用户拍板「单向镜像」口径后落地 v1，全部通过治理门禁与单测（11 passed）：

- 根 `AGENTS.md`：独立精简入口（4 行纯路径 + 指向 `CLAUDE.md`），过 `validate_collaboration_governance.py`。软链方案经隔离实验**证伪**：门禁要求 4 行逐行完全等于纯路径，而 `CLAUDE.md` 中对应行带反引号/中文注释，故 `AGENTS.md -> CLAUDE.md` 软链必报 `missing_refs`。
- `scripts/sync_agent_memory.py`：CodeArts 记忆目录 → 仓库 `memory/` **单向镜像**，重建索引修复漂移，支持 `--check` / `--dry-run`，源只读防写冲突（记忆为活跃写入，2026-10-22 观测仍在增长）。
- 根 `CLAUDE.md` 末尾追加 `@memory/MEMORY.md`：Claude Code 已实测支持 `CLAUDE.md` 的 `@import`（v2.1.302，`claude -p` 行为级验证命中 token）。
- `.gitignore` 白名单化 `memory/`（`memory/*` + `!memory/*.md` + `!memory/.sync-manifest.json`）。
- 触发：`scripts/install_memory_sync_hooks.sh` 装 pre-commit 非阻断检查；cron 定时（`*/5 * * * * ... --quiet`）用于近实时。

**关键约束**：`claude import` 仅支持 `codex/gemini/cursor`，**不含 codearts**；CodeArts 记忆路径软件固定（`~/.codeartsdoer/memory/<slug>/`），故「双向」需 symlink 且未证；v1 只做单向镜像。

**已验证（2026-10-22）**：`claude -p` 行为级确认根 `CLAUDE.md` 的 `@memory/MEMORY.md` 被加载（模型正确复述索引 Feedback 段条目标题）。**待验证**：CodeArts 是否读根 `AGENTS.md`（V1）需重启会话确认。