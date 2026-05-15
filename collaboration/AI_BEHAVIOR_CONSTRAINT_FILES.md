# AI 行为约束文件清单 (v3.0)

**生成时间**: 2026-05-15
**用途**: 为不遵守规则的 Agent 提供必读文件列表

---

## 📋 必读文件清单 (按优先级排序)

### 🔴 P0 - 核心规则 (必须阅读)

#### 1. 协同工作准则
**路径**: `/collaboration/COLLABORATION_GUIDELINES.md`
**重要性**: ⭐⭐⭐⭐⭐
**内容**:
- 任务执行流程 (启动前、执行中、完成后)
- 资源使用指南 (NotebookLM、Context7、Skills、知识图谱)
- 协同文档更新规则
- 质量标准
- 违规处理机制

**适用对象**: 所有 Agent (通过角色绑定)

---

#### 2. 协作协议
**路径**: `/collaboration/PROTOCOL.md`
**重要性**: ⭐⭐⭐⭐⭐
**内容**:
- 动态角色编排架构
- 冷启动机制
- 命令协议 (RUN/ACK)
- 任务分配规则
- 结果汇报格式

**适用对象**: 所有 Agent

---

#### 3. AI 协作标准
**路径**: `/rules/AI-COLLABORATION-STANDARDS.md`
**重要性**: ⭐⭐⭐⭐⭐
**内容**:
- AI 协作标准规范
- 代码风格要求
- 文档格式规范
- 测试覆盖要求
- 角色命令协议

**适用对象**: 所有 Agent

---

#### 4. 角色编排配置
**路径**: `/config/agent-orchestration.json`
**重要性**: ⭐⭐⭐⭐⭐
**内容**:
- 当前角色绑定状态
- 命令前缀映射
- Agent 提供商配置

**适用对象**: 所有 Agent (运行时解析)

---

#### 5. /menu 交互规范
**路径**: `/collaboration/guides/MENU_INTERACTION_SPEC.md`
**重要性**: ⭐⭐⭐⭐⭐
**内容**:
- 配置管理面板使用方法
- 角色激活/休眠操作
- Agent 绑定调整
- 命令重定义

**适用对象**: 所有 Agent

---

### 🟡 P1 - 操作指南

#### 6. 资源使用最佳实践指南
**重要性**: ⭐⭐⭐⭐
**内容**:
- NotebookLM 使用指南
- Context7 使用指南
- Skills 使用指南
- 知识图谱使用指南

**适用对象**: 所有 Agent

---

#### 7. 规则遵守检查清单
**重要性**: ⭐⭐⭐⭐
**内容**:
- 规则传播机制
- 规则遵守检查清单
- 违规检测流程
- 持续改进机制

**适用对象**: 所有 Agent

---

### 🟢 P2 - 历史参考文档

以下文件为历史 Agent 专属规则，可作为参考但不再强制执行：

| 文件 | 历史角色 | 说明 |
|------|---------|------|
| `/rules/claude_code_memory.md` | Claude Code 专属 | 历史参考 |
| `/rules/codearts_agent_rules.md` | CodeArts Agent 专属 | 历史参考 |
| `/rules/codex_agent_rules.md` | Codex Agent 专属 | 历史参考 |
| `/rules/copilot_rules.md` | Copilot 专属 | 历史参考 |

**注意**: 当前角色绑定通过 `/menu` 动态配置，不再依赖这些硬编码规则文件。

---

### 🔵 P3 - 架构文档

#### 8. 架构设计文档
**路径**: `/ARCHITECTURE.md`
**重要性**: ⭐⭐⭐⭐
**内容**:
- 系统架构设计
- 技术选型说明
- 模块依赖关系

**适用对象**: 所有 Agent

---

#### 9. CLAUDE.md 项目说明
**路径**: `/CLAUDE.md`
**重要性**: ⭐⭐⭐⭐
**内容**:
- 项目说明
- 动态角色架构
- 开发工作流

**适用对象**: 所有 Agent

---

## 📂 文件分类汇总

### 按类型分类

| 类型 | 文件数 | 路径 |
|------|--------|------|
| **协同规则** | 3 | `collaboration/*.md` |
| **配置文件** | 3 | `config/*.json` |
| **交互规范** | 2 | `collaboration/guides/*.md`, `collaboration/skills/*.md` |
| **架构文档** | 2 | `ARCHITECTURE.md`, `CLAUDE.md` |

### 按优先级分类

| 优先级 | 文件数 | 必读对象 |
|--------|--------|---------|
| **P0 (核心规则)** | 5 | 所有 Agent |
| **P1 (操作指南)** | 2 | 按需阅读 |
| **P2 (历史参考)** | 4 | 可选阅读 |
| **P3 (架构文档)** | 2 | 理解项目 |

---

## 🎯 阅读建议

### 新配置的 Agent

**必读顺序**:

1. `/config/agent-orchestration.json` (当前绑定状态)
2. `/collaboration/PROTOCOL.md` (协议规范 v3.0)
3. `/collaboration/COLLABORATION_GUIDELINES.md` (协同准则)
4. `/rules/AI-COLLABORATION-STANDARDS.md` (协作标准)
5. `/collaboration/guides/MENU_INTERACTION_SPEC.md` (配置管理)
6. `/CLAUDE.md` (项目说明)

### 已有 Agent (定期复习)

**每次会话复习**:
- `/config/agent-orchestration.json` (确认绑定状态)
- `/collaboration/PROTOCOL.md`

**每周复习**:
- `/collaboration/COLLABORATION_GUIDELINES.md`
- `/rules/AI-COLLABORATION-STANDARDS.md`

---

## 🚨 违规处理

### 发现违规行为

**处理流程**:

1. 指出违规文件和具体条款
2. 要求违规 Agent 阅读相关规则文件
3. 通过 `/menu` 调整角色绑定（如需要）
4. 记录违规行为到变更历史
5. 累计 3 次轻微违规 → 升级为中度违规
6. 中度违规 → 任务标记为 `blocked`，要求返工
7. 严重违规 → 回滚修改，重新分配任务

---

## 🔗 快速访问

### 核心规则文件

```bash
# 协同工作准则
/collaboration/COLLABORATION_GUIDELINES.md

# 协作协议
/collaboration/PROTOCOL.md

# AI 协作标准
/rules/AI-COLLABORATION-STANDARDS.md

# 角色编排配置
/config/agent-orchestration.json

# /menu 交互规范
/collaboration/guides/MENU_INTERACTION_SPEC.md
```

### CLI 快速命令

```bash
# 查看当前状态
python3 -m src.cli orchestration status

# 冷启动配置
python3 -m src.cli orchestration cold-start

# 检测 Agent 服务商
python3 -m src.cli orchestration detect

# 角色管理
python3 -m src.cli orchestration roles list
```

---

## 📝 更新记录

| 日期 | 更新内容 |
|------|---------|
| 2026-05-15 | 升级为动态角色编排架构 |
| 2026-03-01 | 创建文件清单 |

---

**本清单为所有 Agent 必读，违反规则将按违规处理流程执行**