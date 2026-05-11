# AI 行为约束文件清单

**生成时间**: 2026-03-01
**生成者**: CodeArts Agent (技术合伙人)
**用途**: 为不遵守规则的 AI 提供必读文件列表

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

**适用对象**: 所有 AI Agent

---

#### 2. 协作协议
**路径**: `/collaboration/PROTOCOL.md`
**重要性**: ⭐⭐⭐⭐⭐
**内容**:
- 多 Agent 协作协议
- 通信机制
- 任务分配规则
- 结果汇报格式

**适用对象**: 所有 AI Agent

---

#### 3. AI 协作标准
**路径**: `/rules/AI-COLLABORATION-STANDARDS.md`
**重要性**: ⭐⭐⭐⭐⭐
**内容**:
- AI 协作标准规范
- 代码风格要求
- 文档格式规范
- 测试覆盖要求

**适用对象**: 所有 AI Agent

---

#### 4. 跨 AI 协作推进标准
**路径**: `/collaboration/CROSS_AI_COLLABORATION_STANDARDS.md`
**重要性**: ⭐⭐⭐⭐⭐
**内容**:
- 任务启动准则
- 资源使用准则
- 质量标准准则
- 协同推进准则
- Checklist 模板

**适用对象**: 所有 AI Agent

---

### 🟡 P1 - Agent 专属规则 (按角色阅读)

#### 5. 资源使用最佳实践指南
**路径**: `/collaboration/RESOURCE_USAGE_GUIDE.md`
**重要性**: ⭐⭐⭐⭐⭐
**内容**:
- NotebookLM 使用指南
- Context7 使用指南
- Skills 使用指南
- 知识图谱使用指南
- 资源使用决策树

**适用对象**: 所有 AI Agent

---

#### 6. 规则遵守检查清单
**路径**: `/collaboration/RULE_COMPLIANCE_CHECKLIST.md`
**重要性**: ⭐⭐⭐⭐⭐
**内容**:
- 规则传播机制
- 规则遵守检查清单
- 违规检测流程
- 持续改进机制

**适用对象**: 所有 AI Agent

---

#### 7. Claude Code 规则
**路径**: `/rules/claude_code_memory.md`
**重要性**: ⭐⭐⭐⭐⭐
**角色**: 主控 AI
**内容**:
- Claude Code 专属规则
- 决策权限
- 任务分配职责
- 与其他 Agent 的协作方式

**适用对象**: Claude Code

---

#### 8. CodeArts Agent 规则
**路径**: `/rules/codearts_agent_rules.md`
**重要性**: ⭐⭐⭐⭐⭐
**角色**: 执行辅助者
**内容**:
- CodeArts Agent 专属规则
- 测试/文档/并行验证职责
- 代码生成标准
- 测试覆盖要求

**适用对象**: CodeArts Agent

---

#### 9. Codex Agent 规则
**路径**: `/rules/codex_agent_rules.md`
**重要性**: ⭐⭐⭐⭐⭐
**角色**: 技术合伙人 / 开发管理负责人
**内容**:
- Codex Agent 专属规则
- 技术路线与治理裁决职责
- `spawn_agent` 内部委派边界
- 复杂问题解决流程
- 云端任务执行规范

**适用对象**: Codex Agent

---

#### 9.1 Codex `spawn_agent` 使用准则
**路径**: `/collaboration/guides/CODEX_SPAWN_AGENT_USAGE_GUIDELINES.md`
**重要性**: ⭐⭐⭐⭐⭐
**角色**: Codex 内部子代理委派规范
**内容**:
- 单一父任务内委派边界
- 写集隔离与禁止场景
- 与 Claude / CodeArts / ACK 正式工单体系的衔接规则
- 资源最大化与回退规则

**适用对象**: Codex Agent

---

#### 10. Copilot 规则
**路径**: `/rules/copilot_rules.md`
**重要性**: ⭐⭐⭐⭐
**角色**: 助手 (暂时不可用)
**内容**:
- Copilot 专属规则
- 助手职责
- 任务执行标准

**适用对象**: Copilot (当恢复可用时)

---

### 🟢 P2 - 操作指南 (按需阅读)

#### 11. 操作手册
**路径**: `/OPERATION_MANUAL.md`
**重要性**: ⭐⭐⭐⭐
**内容**:
- 系统操作手册
- 日常维护流程
- 故障排查指南

**适用对象**: 所有 AI Agent

---

#### 12. 项目结构指南
**路径**: `/PROJECT_STRUCTURE_GUIDE.md`
**重要性**: ⭐⭐⭐⭐
**内容**:
- 项目目录结构说明
- 模块职责划分
- 文件组织规范

**适用对象**: 所有 AI Agent

---

#### 13. Chrome 扩展指南
**路径**: `/docs/CHROME_EXTENSION_GUIDE.md`
**重要性**: ⭐⭐⭐
**内容**:
- Chrome 扩展开发指南
- Manifest V3 规范
- 内容脚本注入规则

**适用对象**: 涉及前端开发的 AI

---

#### 14. 多 Agent 验证指南
**路径**: `/docs/MULTI_AGENT_VERIFICATION_GUIDE.md`
**重要性**: ⭐⭐⭐
**内容**:
- 多 Agent 协作验证流程
- 测试验证标准
- 质量保证机制

**适用对象**: 所有 AI Agent

---

#### 15. 手动测试指南
**路径**: `/MANUAL_TESTING_GUIDE.md`
**重要性**: ⭐⭐⭐
**内容**:
- 手动测试流程
- 测试用例设计
- 测试报告格式

**适用对象**: 涉及测试的 AI

---

### 🔵 P3 - 架构文档 (理解项目)

#### 16. 架构设计文档
**路径**: `/ARCHITECTURE.md`
**重要性**: ⭐⭐⭐⭐
**内容**:
- 系统架构设计
- 技术选型说明
- 模块依赖关系

**适用对象**: 所有 AI Agent

---

#### 17. 所有权文档
**路径**: `/rules/OWNERSHIP.md`
**重要性**: ⭐⭐⭐
**内容**:
- 模块所有权划分
- 责任人分配
- 权限管理

**适用对象**: 所有 AI Agent

---

## 📂 文件分类汇总

### 按类型分类

| 类型 | 文件数 | 路径 |
|------|--------|------|
| **协同规则** | 6 | `collaboration/*.md`, `rules/AI-COLLABORATION-STANDARDS.md` |
| **Agent 规则** | 4 | `rules/*_rules.md`, `rules/*_memory.md` |
| **操作指南** | 5 | `docs/*.md`, `*GUIDE.md`, `*MANUAL.md` |
| **架构文档** | 2 | `ARCHITECTURE.md`, `rules/OWNERSHIP.md` |

### 按优先级分类

| 优先级 | 文件数 | 必读对象 |
|--------|--------|---------|
| **P0 (核心规则)** | 6 | 所有 AI Agent |
| **P1 (Agent 专属)** | 4 | 对应角色的 AI |
| **P2 (操作指南)** | 5 | 按需阅读 |
| **P3 (架构文档)** | 2 | 理解项目 |

---

## 🎯 阅读建议

### 新加入的 AI Agent

**必读顺序**:
1. `/collaboration/AI_BEHAVIOR_CONSTRAINT_FILES.md` (必读文件清单)
2. `/collaboration/COLLABORATION_GUIDELINES.md` (协同工作准则)
3. `/collaboration/PROTOCOL.md` (协作协议)
4. `/collaboration/CROSS_AI_COLLABORATION_STANDARDS.md` (跨 AI 协作标准)
5. `/collaboration/RESOURCE_USAGE_GUIDE.md` (资源使用指南)
6. `/rules/AI-COLLABORATION-STANDARDS.md` (AI 协作标准)
7. 对应角色的专属规则文件
8. `/ARCHITECTURE.md` (架构设计文档)

### 已有 AI Agent (定期复习)

**每次会话复习**:
- `/collaboration/AI_BEHAVIOR_CONSTRAINT_FILES.md`
- `/collaboration/CROSS_AI_COLLABORATION_STANDARDS.md`
- `/collaboration/RESOURCE_USAGE_GUIDE.md`

**每周复习**:
- `/collaboration/COLLABORATION_GUIDELINES.md`
- `/collaboration/RULE_COMPLIANCE_CHECKLIST.md`
- 对应角色的专属规则文件

**每月复习**:
- `/collaboration/PROTOCOL.md`
- `/rules/AI-COLLABORATION-STANDARDS.md`
- `/ARCHITECTURE.md`

---

## 🚨 违规处理

### 发现违规行为

**处理流程**:
1. 指出违规文件和具体条款
2. 要求违规 AI 阅读相关规则文件
3. 记录违规行为到知识图谱
4. 累计 3 次轻微违规 → 升级为中度违规
5. 中度违规 → 任务标记为 `blocked`,要求返工
6. 严重违规 → 回滚修改,重新分配任务

### 违规示例

**示例 1: 文档位置违规**
- **违规行为**: 将报告放在项目根目录而不是 `collaboration/results/`
- **违反文件**: `COLLABORATION_GUIDELINES.md` 第 4.1 节
- **处理**: 要求移动文件到正确位置

**示例 2: 未使用资源**
- **违规行为**: 没有使用 NotebookLM、Context7 等资源
- **违反文件**: `COLLABORATION_GUIDELINES.md` 第 3 节
- **处理**: 要求重新评估资源需求并使用

**示例 3: 未打标记**
- **违规行为**: 开始任务前没有打 `[IN_PROGRESS]` 标记
- **违反文件**: `COLLABORATION_GUIDELINES.md` 第 2.1 节
- **处理**: 要求补打标记并更新看板

---

## 📊 文件完整性检查

### 检查清单

- [x] 协同工作准则存在
- [x] 协作协议存在
- [x] AI 协作标准存在
- [x] Claude Code 规则存在
- [x] CodeArts Agent 规则存在
- [x] Codex Agent 规则存在
- [x] Copilot 规则存在
- [x] 操作手册存在
- [x] 项目结构指南存在
- [x] 架构设计文档存在

### 缺失文件

- [ ] `CONTRIBUTING.md` (贡献指南)
- [ ] `CHANGELOG.md` (变更日志)
- [ ] `CODE_OF_CONDUCT.md` (行为准则)

**建议**: 补充缺失文件以完善项目文档体系

---

## 🔗 快速访问

### 核心规则文件 (复制路径)

```bash
# 协同工作准则
/collaboration/COLLABORATION_GUIDELINES.md

# 协作协议
/collaboration/PROTOCOL.md

# AI 协作标准
/rules/AI-COLLABORATION-STANDARDS.md

# Claude Code 规则
/rules/claude_code_memory.md

# CodeArts Agent 规则
/rules/codearts_agent_rules.md

# Codex Agent 规则
/rules/codex_agent_rules.md
```

### 按角色快速访问

**Claude Code**:
```bash
/collaboration/COLLABORATION_GUIDELINES.md
/collaboration/PROTOCOL.md
/rules/claude_code_memory.md
```

**CodeArts Agent**:
```bash
/collaboration/COLLABORATION_GUIDELINES.md
/collaboration/PROTOCOL.md
/rules/codearts_agent_rules.md
```

**Codex Agent**:
```bash
/collaboration/COLLABORATION_GUIDELINES.md
/collaboration/PROTOCOL.md
/rules/codex_agent_rules.md
```

---

## 📝 更新记录

| 日期 | 更新内容 | 更新者 |
|------|---------|--------|
| 2026-03-01 | 创建文件清单 | CodeArts Agent |

---

**本清单为所有 AI Agent 必读,违反规则将按违规处理流程执行**

🎯
