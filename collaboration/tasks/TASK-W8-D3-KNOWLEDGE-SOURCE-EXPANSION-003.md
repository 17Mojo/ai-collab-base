---
task_id: TASK-W8-D3-KNOWLEDGE-SOURCE-EXPANSION-003
change_id: notebooklm-knowledge-source-expansion
status: completed
assignee: claude_code
reviewer: user
primary_skill: notebooklm
support_skills: ["content_creation", "knowledge_management"]
acceptance_commands: "nlm source list d2b04caa-... | wc -l"
created_at: 2026-04-26T09:00:00
estimated_hours: 1.0
priority: P1
depends_on: []
---

# TASK-W8-D3-KNOWLEDGE-SOURCE-EXPANSION-003

## 任务描述

扩展 NotebookLM 知识库内容，上传更多高质量知识源文档。

## 背景

当前知识库仅有 2 个知识源（北方旅游攻略、小红书创作指南），需要扩展以提升知识查询覆盖范围。

## 详细任务

### Task 1: 知识源内容规划 (15min)

**规划上传的知识源**:

| 知识源 | 来源 | 内容 | 优先级 |
|--------|------|------|--------|
| AI 协作系统架构文档 | ARCHITECTURE.md | 系统架构设计 | P1 |
| Chrome Extension 开发指南 | CHROME_EXTENSION_GUIDE.md | Extension 开发规范 | P1 |
| Pack Schema v2.0 文档 | schema_v2.py 注释 | Pack 结构定义 | P1 |
| API 文档 | API_DOCUMENTATION.md | Backend API 规范 | P2 |
| 测试指南 | MVP_TEST_REPORT.md | 测试规范 | P2 |

---

### Task 2: 创建知识源文档 (30min)

**位置**: `knowledge-sources/`

**创建文件**:

1. `ai_collab_system_architecture.md` - 系统架构摘要
2. `chrome_extension_dev_guide.md` - Extension 开发规范
3. `pack_schema_v2_guide.md` - Pack 结构指南

**内容格式**:

```markdown
# 知识源标题

## 核心概念
- 概念 1
- 概念 2

## 使用方法
- 方法 1
- 方法 2

## 最佳实践
- 实践 1
- 实践 2
```

---

### Task 3: 上传到 NotebookLM (15min)

**命令**:

```bash
# 上传架构文档
nlm add text d2b04caa-257a-4aad-82b0-f58c28e0dad5 "$(cat knowledge-sources/ai_collab_system_architecture.md)" --title "AI协作系统架构"

# 上传 Extension 开发指南
nlm add text d2b04caa-... "$(cat knowledge-sources/chrome_extension_dev_guide.md)" --title "Chrome Extension 开发指南"

# 上传 Pack Schema 指南
nlm add text d2b04caa-... "$(cat knowledge-sources/pack_schema_v2_guide.md)" --title "Pack Schema v2.0 指南"
```

---

### Task 4: 验证知识源可用 (10min)

**验证命令**:

```bash
# 检查知识源列表
nlm source list d2b04caa-...

# 查询测试
nlm query d2b04caa-... "AI 协作系统的架构是什么？"
nlm query d2b04caa-... "Pack Schema v2.0 的 WorkflowStep 有哪些字段？"
```

---

## 验收标准

| 标准 | 验证方法 |
|------|----------|
| 新增知识源 ≥ 3 个 | `nlm source list` 统计 |
| 知识源标题正确 | 列表显示正确标题 |
| 知识查询返回相关内容 | query 响应有引用 |
| 知识源文件存在于 knowledge-sources/ | `ls` 验证 |

---

## 文件清单

| 文件 | 操作 |
|------|------|
| knowledge-sources/ai_collab_system_architecture.md | 新建 |
| knowledge-sources/chrome_extension_dev_guide.md | 新建 |
| knowledge-sources/pack_schema_v2_guide.md | 新建 |

---

## 风险/回滚

| 风险 | 影响 | 缓解 |
|------|------|------|
| NotebookLM 认证过期 | 上传失败 | 检查认证状态 |
| 知识源格式不规范 | 查询效果差 | 按模板格式 |

---

**创建时间**: 2026-04-26T09:00:00+08:00