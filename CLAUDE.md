<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:

- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` learn:

- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

---

## 🔴 AI 协作强制规则

### 每次会话启动时必须执行

1. 阅读必读文件清单：`/collaboration/AI_BEHAVIOR_CONSTRAINT_FILES.md`

2. P0 核心规则（必须阅读，强制执行）

   - `/collaboration/COLLABORATION_GUIDELINES.md` ← 协同工作准则
   - `/collaboration/PROTOCOL.md` ← 协作协议
   - `/rules/AI-COLLABORATION-STANDARDS.md` ← AI 协作标准
   - `/rules/claude_code_memory.md` ← Claude Code 专属规则

**不阅读以上规则不得开始任何工作。**

### 任务执行强制流程

启动前：`[IN_PROGRESS]` + 检查看板 + 评估资源

执行中：使用 NotebookLM/Context7 + 每30分钟记录 + 遇阻塞标记

完成后：质量验证 + 结果报告到 `collaboration/results/` + 开发日志 + `[DONE]`

详细流程见：`/collaboration/COLLABORATION_GUIDELINES.md` 第二章节

### 文件放置强制规则

任务文件：`collaboration/tasks/TASK_*.md`（❌ 不得放根目录）

结果报告：`collaboration/results/RESULT_*.md`（❌ 不得放根目录）

开发日志：`logs/claude-code/YYYY-MM/*.md`（❌ 必须有日志）

违规后果：轻微（提醒）→ 中度（blocked+返工）→ 严重（回滚+重新分配）

### 资源调用强制要求

协作最佳实践 → NotebookLM

框架/库文档 → Context7

前端开发 → frontend-design 技能

国际化 → i18n-integration 技能

重要决策 → 知识图谱

### 动态角色编排架构

本项目采用**角色别名驱动**的动态协作架构。具体 Agent 提供商通过 `/menu` 或 `config/agent-orchestration.json` 配置。

**默认角色定义**:

```text
角色代号          显示名称      RACI 定位
───────────────────────────────────────────
AGENT_EXEC      主执行者      R (Responsible)
AGENT_ARCH      架构师        A (Accountable)
AGENT_TEST      测试验证      C (Consulted)
AGENT_DOC       文档编写      C (Consulted)
AGENT_PERF      性能优化      C (Consulted)
AGENT_OPS       运维部署      I (Informed)
```

**当前绑定状态**（通过 `/menu status` 查看）:

```text
绑定状态: uninitialized
启动模式: 未配置

角色绑定:
  ○ AGENT_EXEC → 未绑定
  ○ AGENT_ARCH → 未绑定
  ○ AGENT_TEST → 未绑定
```

**冷启动配置**:

```bash
# CLI 方式
python3 -m src.cli orchestration cold-start

# 或通过 /menu 技能
/menu cold-start
```

**协作协议**: 详见 `collaboration/PROTOCOL.md` (v3.0)

---

## Project Overview

This is an **AI Collaboration System** with dynamic role orchestration, focused on building **Prompt Pack v2.0** - a local-first Chrome extension that automates AI chat interactions.

### Architecture Philosophy: Local-First

```text
Zero cost, zero config, fully offline capable
─────────────────────────────────────────────
Chrome Extension ←→ VSCode ←→ FastAPI (local)
                                      ↓
                                  SQLite (single file)
```

- **No cloud services required** for MVP
- SQLite database (single file `data/packs.db`)
- FastAPI local server runs on `http://127.0.0.1:8000`
- All data remains on your machine

### The Three-Component System

| Component | Role | Location |
|-----------|------|----------|
| Chrome Extension | Injects scripts, executes Packs, monitors DOM | Future implementation |
| VSCode Extension | Pack editor, Native Messaging bridge | Future implementation |
| Local Backend | Pack registry (`packs.db`), API endpoints, OpenSpec engine | `local-backend/` (planned) |

---

## Role Orchestration Model

### Dynamic Role Binding

Agent providers are bound dynamically through `config/agent-orchestration.json`:

| Function | Role (Default) | Notes |
|----------|---------------|-------|
| Code implementation | AGENT_EXEC | Responsible for coding |
| Architecture design | AGENT_ARCH | Accountable for decisions |
| Testing & validation | AGENT_TEST | Consulted for quality |
| Documentation | AGENT_DOC | Consulted for docs |

### Command Protocol

```text
X.RUN → Triggers AGENT_EXEC
A.RUN → Triggers AGENT_ARCH
C.RUN → Triggers AGENT_TEST (or custom mapping)
```

### Configuration Management

Use `/menu` skill or CLI commands:

```bash
python3 -m src.cli orchestration status
python3 -m src.cli orchestration cold-start
python3 -m src.cli orchestration roles activate --role-id AGENT_EXEC --provider claude_code
```

## Common Commands

### Starting the Local Backend (once implemented)

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Using Python directly
cd local-backend
uvicorn main:app --reload --port 8000

# View logs
docker-compose logs -f api
```

### Checking Collaboration Status

```bash
# Check current task status
cat logs/collaboration_state.json

# Check Copilot handoff status
cat handoff_status.json
```

### Project State

- **Architecture**: Complete ([`ARCHITECTURE.md`](ARCHITECTURE.md))
- **Schema v2.0**: Partially defined ([`ai_collab/pack/schema_v2.py`](ai_collab/pack/schema_v2.py))
- **Notification System**: Complete ([`ai_collab/notification.py`](ai_collab/notification.py))
- **Backend alternatives researched**: See [`docs/backend-alternatives.md`](docs/backend-alternatives.md)

## Key File Locations

| Purpose | File |
|---------|------|
| Orchestration Config | `config/agent-orchestration.json` |
| Orchestration Schema | `config/agent-orchestration.schema.json` |
| Pack v2.0 Schema | `ai_collab/pack/schema_v2.py` |
| System Architecture | `ARCHITECTURE.md` |
| Collaboration Protocol | `collaboration/PROTOCOL.md` |
| Collaboration Guidelines | `collaboration/COLLABORATION_GUIDELINES.md` |
| Menu Interaction Spec | `collaboration/guides/MENU_INTERACTION_SPEC.md` |
| Collaboration State | `logs/collaboration_state.json` |

## Important Architecture Decisions

### Why Local-First?

| Criterion | Local-First | Cloud (Supabase, etc.) |
|----------|-------------|-----------------------|
| Cost | $0 | $0-10+/month |
| Setup time | <5 min | ~30 min |
| Offline capable | ✅ | ❌ |
| Data control | Full | Shared |

SQLite + `lru_cache` replaces MySQL + Redis for MVP.

### When to Use Copilot

Activate Copilot for:

1. Network research (WebSearch, WebFetch)
2. Comparing technical alternatives
3. Finding third-party tool options

**Do NOT use Copilot for:**

- Implementing core architecture (Claude's role)
- Writing database schema without research context

## Development Workflow

### For Pack Development

1. Design workflow in [`ARCHITECTURE.md`](ARCHITECTURE.md) section "2.3 执行流程"
2. Reference schema in [`ai_collab/pack/schema_v2.py`](ai_collab/pack/schema_v2.py)
3. Use `WorkflowStep` structure with `action` types: `input/select/validate/output`

### For Network Research Tasks

1. Update [`rules/copilot_tasks.md`](rules/copilot_tasks.md) with new task
2. Set priority: 🔴 high / 🟡 medium / 🟢 low
3. Wait for Copilot to complete
4. Read results from [`research/copilot-handoff/`](research/copilot-handoff/)
5. Update [`logs/collaboration_state.json`](logs/collaboration_state.json)

## Implementation Priority

Based on [`ARCHITECTURE.md`](ARCHITECTURE.md) Phase 1-5:

1. ✅ Architecture design
2. ⏳ Pack v2.0 complete Schema
3. ⏳ Chrome Extension Manifest V3
4. ⏳ Content Script + DOM Observer
5. ⏳ Local Backend (FastAPI + SQLite)

## Backwards Compatibility Notes

The system evolved from a cloud-first (Alibaba Cloud FC) design to local-first. References in older docs to:

- `cloud-backend/` functions → Replace with `local-backend/`
- MySQL/Redis → Replace with SQLite/lru_cache
- Alibaba Cloud FC → Replace with FastAPI local server

See [`docs/backend-alternatives.md`](docs/backend-alternatives.md) for complete migration path.

---

**更新时间**: 2026-03-01
**更新内容**: 添加 AI 协作强制规则章节

---

## 从 2026-09-15 覆盖率任务提炼的 3 条长期经验

来自 commit `7d2cc9d`（清理 4836 行死代码 + 修复 4 个生产 bug + 新增 81 个测试用例）的实战总结，**所有 AI 协作者必读**：

### 经验 1：改代码前先看测试在守护什么

81 个新测试覆盖了核心模块的高风险路径：
- `tests/unit/test_context_search.py`（30 用例）守护 `ai_collab/context/search.py`
- `tests/unit/test_pack_executor_mvp.py`（36 用例）守护 `ai_collab/pack/pack_executor_mvp.py`
- `tests/unit/test_consensus_engine_extra.py`（14 用例）守护 `ai_collab/engines/consensus_engine.py`
- `tests/unit/test_workspace_guard_extra.py`（31 用例）守护 `ai_collab/workspace_guard.py`
- `tests/unit/test_handoff_notification.py` 守护 `ai_collab/handoff_notification.py`
- `tests/unit/test_pack_schema_validator.py` 守护 `ai_collab/pack/schema_validator.py`

**强制流程**：修改任何 `ai_collab/` 下 .py 文件前，先 `grep` 相关测试文件了解守护范围；改完后**先跑相关测试**再跑全套。

### 经验 2：发现字段名错配 → 系统性排查，不要只修一处

2026-09-15 在 `ai_collab/context/search.py` 一次发现 3 处同类 bug：
- `item.score` → `item.confidence`（字段不存在）
- `item.source` → `item.source_type`（字段不存在）
- `_filter_by_scope` 函数定义缺 `query` 参数

**防御性方法**：发现一次「字段名错配」后，立即：
1. `grep -n '\.score\|\.source\|\.\w+\b' <file>` 同文件所有属性访问
2. 检查同模块其他文件是否同一字段错配
3. 用 dataclass / TypedDict 明确定义，避免动态属性陷阱
4. 考虑加 mypy 静态检查

**典型陷阱**：Python 动态属性运行时才报错，要么崩溃要么**静默失效**（程序跑着但功能错）——后者最危险。

### 经验 3：commit message 不撒谎，诚实标注限制

原 commit message 承诺「68% → 85%+」，但实测 TOTAL 80%（受 `_cli_main.py`（2605 行 63%）、`orchestration.py`（339 行 27%）、`codex_integration.py`（393 行 41%）等 CLI/集成入口结构性限制）。

**正确做法**（参考 commit `7d2cc9d` 实际写法）：
- 关键模块覆盖率达到的如实标注（如「context/search.py: 75% → 85%」）
- TOTAL 未达目标时**写明根因**（如「受 CLI/集成入口模块结构性限制」）
- 区分「超额交付」与「虚假承诺」

**行业惯例**：CLI 入口/编排层/集成层不适合单测覆盖，应该用 E2E 测试或显式 omit，**不该靠凑覆盖率数字掩盖结构性限制**。

---

**记录时间**: 2026-09-15
**来源**: 与用户协作完成覆盖率提升任务后总结
