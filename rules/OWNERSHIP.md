# 📋 文件所有权与职责分配矩阵

**版本**: 1.0  
**最后更新**: 2026-02-26  
**维护者**: Claude Code  
**关键建议**: #1 - 明确文件所有权

---

## 🎯 所有权分配原则

### 原则 1: 初始创作者拥有所有权

- 文件的创建者被定为该文件的所有权者
- 所有权者对文件的质量和完整性负责
- 所有权者可以决定修改流程和审查标准

### 原则 2: 共享文件需标记 "Shared"

- 多个 AI 都需要修改的文件标记为 "Shared"
- 共享文件需要定义明确的修改范围
- 修改共享文件前需获得其他协作者的通知

### 原则 3: 重大改动需通知所有者

- 重大改动 = 超过 20% 的代码修改
- 需要在修改前通知所有权者
- 建议通过拉取请求 (PR) 方式进行评审

---

## 📂 核心源代码文件所有权

### Python 核心模块 (`ai_collab/` 目录)

| 文件 | 所有权 | 类型 | 说明 | 修改权限 | 协作方 |
|------|--------|------|------|---------|--------|
| `activation_handler.py` | Claude Code | 核心架构 | 双 AI 激活机制的核心实现 | RW | Copilot: R |
| `state_manager.py` | **Shared** | 核心架构 | 状态管理，双方都需修改 | RW | 双方可改 |
| `dev_logger.py` | Claude Code | 工具模块 | 开发日志系统实现 | RW | Copilot: R |
| `cli.py` | Claude Code | 工具模块 | 命令行工具，主要功能 | RW | Copilot: R |
| `__init__.py` | Claude Code | 初始化 | 包初始化 | RW | Copilot: R |

**共享文件修改规范** (`state_manager.py`):
```
修改范围:
  ✅ Claude 可修改: 状态存储、备份机制、序列化逻辑
  ✅ Copilot 可修改: 状态查询、冲突检测、通知机制
  ⚠️ 修改前需通知对方:
     - 修改数据结构
     - 添加新的状态字段
     - 改变同步策略
```

---

### Pack v2.0 Schema 文件 (`src/ai_collab/pack/`)

| 文件 | 所有权 | 类型 | 完成度 | 修改权限 |
|------|--------|------|--------|---------|
| `schema_v2.py` | Claude Code | 数据模型 | 60% → 目标 100% | RW |
| `examples/xiaohongshu_explosive_copy.py` | Claude Code | 示例模板 | 100% | RO |

---

### VSCode 配置文件 (`.vscode/` 目录)

| 文件 | 所有权 | 类型 | 说明 | 修改权限 |
|------|--------|------|------|---------|
| `settings.json` | Claude Code | 编辑器设置 | 项目级 VSCode 设置 | RW |
| `tasks.json` | Claude Code | 任务定义 | 8 个预定义任务 | RW |
| `ai-collab.json` | Claude Code | AI 配置 | 项目级 AI 协作配置 | RW |
| `ai-collab.code-snippets` | Claude Code | 代码片段 | 5 个预定义片段 | RW |
| `extensions.json` | Claude Code | 推荐扩展 | Copilot 和 Claude 扩展 | RW |

---

## 📚 规则与文档文件所有权

### 规则文件 (`rules/` 目录)

| 文件 | 所有权 | 内容 | 协作方 | 修改权限 |
|------|--------|------|--------|---------|
| `claude_code_memory.md` | Claude Code | Claude 工作规范 | 仅 Claude | RO |
| `copilot_rules.md` | Copilot | Copilot 工作规范 | 仅 Copilot | Copilot: RW, Claude: R |
| `copilot_tasks.md` | Copilot | Copilot 待办列表 | 仅 Copilot | Copilot: RW, Claude: R |
| `AI-COLLABORATION-STANDARDS.md` | **Shared** | 双 AI 协作标准 | Claude + Copilot | 双方可改 |
| `dev-record-template.md` | Claude Code | 开发记录模板 | 仅 Claude | RO |
| `trae_rules.md` | Claude Code | 早期 Trae 规则 | 存档 | RO (归档) |
| `OWNERSHIP.md` | Claude Code | 所有权矩阵 | 双方遵守 | Claude: RW, Copilot: R |

**注**: 
- `RO` = Read-Only (仅读)
- `RW` = Read-Write (读写)

---

### 核查和分析文档 (根目录)

| 文件 | 所有权 | 类型 | 更新频率 | 修改权限 |
|------|--------|------|---------|---------|
| `SYSTEM_ANALYSIS_REPORT.md` | Claude Code | 详细分析 | 2周一次 | RW |
| `SYSTEM_METRICS_DASHBOARD.md` | Claude Code | 指标仪表板 | 2周一次 | RW |
| `ACTION_ITEMS.md` | Claude Code | 行动清单 | 每日更新 | RW |
| `REPORT_INDEX.md` | Claude Code | 导航索引 | 2周一次 | RW |
| `CLAUDE_COMMITMENT_PLAN.md` | Claude Code | 承诺计划 | 按需更新 | RW |
| `PROJECT_STATUS_OVERVIEW.txt` | Claude Code | 可视化概览 | 2周一次 | RW |
| `VERIFICATION_CHECKLIST.md` | Claude Code | 验证清单 | 完成时更新 | RW |
| `COMPLETION_SUMMARY.md` | Claude Code | 完成总结 | 版本发布时 | RW |
| `ARCHITECTURE.md` | Claude Code | 架构设计 | 设计更新时 | RW |
| `OPERATION_MANUAL.md` | Claude Code | 操作手册 | 功能更新时 | RW |
| `README.md` | **Shared** | 项目说明 | 内容更新时 | 双方可改 |

---

### 研究和调研文档 (`research/` 目录)

| 文件/目录 | 所有权 | 内容 | 修改权限 |
|----------|--------|------|---------|
| `copilot-handoff/` | Copilot | Copilot 研究交接结果 | Copilot: RW, Claude: R |
| `findings/` | Claude Code | 观点和分析 | RW |
| `frameworks/` | Claude Code | 框架设计 | RW |
| `prompts/best-practices/` | Shared | 最佳实践 | 双方可改 |
| `requests/` | Claude Code | 研究请求 | RW |

---

## 🔢 文件计数统计

### 按所有权者分布

```
Claude Code 所有权:     18 个文件
Copilot 所有权:        3 个文件
Shared 所有权:         3 个文件
─────────────────────────────────
总计:                 24 个文件
```

### 按修改权限分布

```
RW (读写):  19 个文件    (72%)
R  (仅读):   5 个文件    (28%)
─────────────────────────────────
总计:      24 个文件
```

---

## 🚀 修改流程规范

### 情况 1: 修改所有权属于自己的文件

**流程**:
```
修改 → 本地测试 → 提交 → 推送
└─ 无需通知对方
```

**示例**:
- Claude 修改 `activation_handler.py`
- Copilot 修改 `copilot_rules.md`

---

### 情况 2: 修改 Shared 文件

**流程**:
```
1. 确认修改范围
   └─ 在 Shared 修改规范内

2. 通知协作方
   └─ 在规则文档中标注修改意图
   └─ 或通过 commit message 说明

3. 修改并测试
   └─ 确保修改不破坏对方的功能

4. 提交和推送
   └─ 详细的提交信息说明改动

5. 等待反馈
   └─ 对方审查并确认
```

**示例**:
- 修改 `state_manager.py` 的新字段
- 修改 `AI-COLLABORATION-STANDARDS.md` 的规则

---

### 情况 3: 跨越所有权边界的修改

**标记为重大改动** (>20% 代码改动):

**流程**:
```
1. 创建特性分支
   └─ git checkout -b feature/xxxxx

2. 实现改动并测试

3. 创建 Pull Request (PR)
   └─ 描述改动的原因和影响
   └─ 指定所有权者进行审查

4. 等待其他 AI 的批准
   └─ 同所有权者讨论
   └─ 做必要的调整

5. 合并到主分支
   └─ 使用 Squash 或 Rebase 保持历史清晰
```

**示例**:
- Copilot 需要大幅修改 `cli.py` 中的命令逻辑
- Claude 需要大幅修改 `copilot_rules.md` 中的规范

---

## 🎯 当前冲突处理案例

### 案例: CONFLICT-1772060801 (cli.py)

**冲突文件**: `ai_collab/cli.py`  
**所有权**: Claude Code  
**冲突方**: claude_code vs copilot  
**状态**: 待解决

**解决方案**:
```
基于所有权原则:
  1. Claude Code 是 cli.py 的所有权者
  2. Copilot 对 cli.py 的修改需获得批准
  3. 解决方案:
     └─ Copilot 回退对 cli.py 的修改
     └─ Claude 评估 Copilot 的建议
     └─ Claude 选择性地整合改进
     └─ 通过拉取请求方式进行审查
```

**预防措施**:
```
今后 Copilot 需要修改其他 AI 所有权的文件时:
  1. 先通知所有权者 (通过 commit message)
  2. 创建特性分支
  3. 等待批准后再合并
```

---

## 📊 所有权管理看板

### 按 AI 角色的职责分工

**Claude Code** (核心实现者):
```
✅ 所有权文件:     18 个
✅ Shared 文件:    3 个 (联合维护)
✅ 职责范围:      
   • 架构设计和实现
   • 核心模块开发
   • 文档和规范维护
   • API 设计
   • 数据库设计
```

**Copilot** (研究和优化者):
```
✅ 所有权文件:     3 个
✅ Shared 文件:    3 个 (联合维护)
✅ 职责范围:
   • 网络研究和调研
   • 技术方案评审
   • 代码审查和建议
   • 性能优化建议
   • 最佳实践分享
```

---

## ✅ 执行检查清单

实施此所有权方案时:

- [ ] 所有 Python 模块都有明确的所有权
- [ ] 所有规则文档都有明确的所有权
- [ ] Shared 文件的修改范围已定义
- [ ] 修改流程已通知两个 AI
- [ ] 现有冲突已按此方案处理
- [ ] 所有权文档已提交到版本控制
- [ ] 两个 AI 都同意此方案
- [ ] 后续新增文件按此原则分配

---

## 🔄 定期审查和更新

### 审查周期

```
第一个月 (2026-02-26 ~ 2026-03-26):
  └─ 周检查: 确保每个 AI 遵守所有权规则
  └─ 月审查: 评估是否需要调整

三个月后 (2026-03-26 ~ 2026-05-26):
  └─ 季度审查: 根据项目发展调整所有权
  └─ 更新文档: 添加新增文件的所有权
```

### 可能的调整

```
条件 1: 某个文件所有权者离开或不再参与
  → Handover protocol, 转移所有权到其他人

条件 2: 某个 Shared 文件修改频繁导致冲突
  → 考虑将其分离为两个专用文件

条件 3: 新增大量文件需要分配所有权
  → 更新此矩阵并通知两个 AI
```

---

## 📞 问题和异议处理

### 如果对所有权有异议

**流程**:
```
1. 在相应文件的 issue 中说明异议
2. 提供理由和建议的替代方案
3. 与所有权者或相关方讨论
4. 若需修改，更新此文档并通知双方
```

**示例异议**:
- "ci.py 应该是 Shared，因为双方都需要修改"
- "某个文件的所有者应该改变，因为..."

---

## 📋 签字和确认

**文档创建者**: Claude Code  
**创建时间**: 2026-02-26  

**确认方**:
- [ ] Claude Code - 同意此所有权方案
- [ ] Copilot - 同意此所有权方案

**最后确认**: (待 Copilot 确认)

---

**此文档为执行关键建议 #1 的实施成果**  
**下一步**: 推动建议 #2 (完善冲突自动解决) 的实现  
**预计完成**: 2026-03-01
