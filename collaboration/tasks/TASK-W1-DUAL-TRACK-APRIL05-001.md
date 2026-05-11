---
task_id: TASK-W1-DUAL-TRACK-APRIL05-001
change_id: add-session-orchestration-control-plane
status: completed
assignee: claude_code,codearts_agent
reviewer: claude
primary_skill: orchestration
support_skills: ["ai_collaboration", "testing", "documentation"]
acceptance_commands: "python3 -m ai_collab.cli sessions health && python3 -m ai_collab.cli tasks validate-contract --scope all --strict"
result_file: collaboration/results/RESULT_TASK-W1-DUAL-TRACK-APRIL05-001.md
created_at: 2026-04-05T06:35:00
estimated_hours: 6
priority: P0
---

# TASK-W1-DUAL-TRACK-APRIL05-001

## 目标

**Claude Code 和 CodeArts 双轨并行，同时推进 Prompt Pack v2.0 和 Context 管理**

### 控制面基准
- ✅ Session Orchestration 已就绪
- ✅ codearts_agent 已注册
- ✅ 质量门禁通过
- ✅ 协作协议激活

---

## 轨道 A: Prompt Pack v2.0 (Claude Code 主责 | CodeArts 辅助)

### A1. Pack Schema 收尾工作 (1h | Claude Code)

**位置**: `tests/unit/test_schema_v2.py`

**任务**:
1. 检查当前 Schema v2.0 测试覆盖率
2. 补充边界场景测试（空值、超长字符串、特殊字符）
3. 添加大 Pack 性能测试
4. 修复发现的 Schema Bug

**验收标准**:
```bash
pytest tests/unit/test_schema_v2.py --cov=src.ai_collab/pack/schema_v2 --cov-report=term
# coverage >= 90%
# 所有测试通过
```

### A2. Pack 示例库扩展 (3h | CodeArts 主责 | Claude Code 审查)

**目标**: 创建 5 个高质量 Pack 示例

**CodeArts 任务**:
1. [ ] 微博文案生成 Pack (`packs/examples/weibo_explosive_copy.json`)
2. [ ] 抖音视频脚本 Pack (`packs/examples/douyin_video_script.json`)
3. [ ] 知乎回答优化 Pack (`packs/examples/zhihu_answer_optimization.json`)
4. [ ] 邮件自动回复 Pack (`packs/examples/email_auto_reply.json`)
5. [ ] 技术文档生成 Pack (`packs/examples/tech_documentation.json`)

**每个 Pack 要求**:
- 完整 metadata
- 6 步 workflow (input/select/validate/output)
- quality_metrics
- example_library (各 2 个优秀/失败案例)

**Claude Code 任务**:
1. 提供 ARCHITECTURE.md 中的 WorkflowStep 规范
2. 审查每个 Pack 的 Schema 合规性
3. 运行验证命令并反馈

**验收标准**:
```bash
python3 -m ai_collab.cli pack validate --path packs/examples/*.json
```

### A3. CLI Pack 工具增强 (2h | 协作)

**Claude Code 任务**:
1. 设计 `pack validate` 命令架构
2. 设计 `pack template` 命令架构
3. 设计 `pack export/import` 命令架构
4. 提供错误提示规范

**CodeArts 任务**:
1. 实现三个 CLI 命令
2. 编写命令帮助文档
3. 创建命令测试用例

**验收标准**:
```bash
python3 -m ai_collab.cli pack validate --path packs/examples/*.json
python3 -m ai_collab.cli pack template --name demo --category content_generation
python3 -m ai_collab.cli pack export --source packs/demo.json
python3 -m ai_collab.cli pack import --source packs/demo.json
```

---

## 轨道 B: Context 管理 (CodeArts 主责 | Claude Code 辅助)

### B1. 场景识别增强 (2h | CodeArts)

**位置**: `src/ai_collab/context/scenario.py`

**任务**:
1. [ ] 完善场景识别规则
   - coding: `src/`, `app/`, `services/`
   - research: `docs/`, `research/`, `references/`
   - writing: `content/`, `posts/`, `articles/`
2. [ ] 提升识别准确度至 85%+
3. [ ] 添加测试用例覆盖边界情况

**验收标准**:
```python
from src.ai_collab.context.scenario import ScenarioDetector

detector = ScenarioDetector()
scenario = detector.detect(current_files)
assert scenario.type in ['coding', 'research', 'writing', 'debugging']
# accuracy >= 85%
```

**Claude Code 支持**: 运行验证命令，提供反馈

### B2. NotebookLM Context 桥接增强 (2h | CodeArts)

**位置**: `src/ai_collab/context/enhanced.py`

**任务**:
1. [ ] 优化 NotebookLM → Context 桥接逻辑
2. [ ] 添加自动文档上传功能
3. [ ] 增强知识检索准确性
4. [ ] 补充测试用例

**验收标准**:
```python
from src.ai_collab.context.enhanced import ContextEnhancer

enhancer = ContextEnhancer(notebooklm_integration)
context = enhancer.enrich(base_context, query="理解项目架构")
assert len(context.knowledge_sources) > 0
```

**Claude Code 支持**: 使用 notebooklm skill 验证集成效果

### B3. Context 持久化存储实现 (2h | 协作)

**CodeArts 任务**:
1. 创建 Context 数据库表
2. 实现 SQLite CRUD
3. 替换内存存储

**Claude Code 任务**:
1. 设计数据库 schema
2. 审查 CRUD 实现质量
3. 验证数据持久化效果

**验收标准**:
- API 端点正常工作
- 数据重启后保持
- SQLite 文件正确创建

---

## 协作分工图

```text
                    ┌─────────────────────────────────────┐
                    │     Session Orchestration Control    │
                    │        (已就绪, codearts_registered) │
                    └──────────────────┬──────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
           ┌────────▼────────┐                   ┌────────▼────────┐
           │  Claude Code    │                   │   CodeArts      │
           │  (主责 A轨)     │                   │  (主责 B轨)     │
           └────────┬────────┘                   └────────┬────────┘
                    │                                     │
        ┌───────────┴───────────┐           ┌─────────────┴─────────────┐
        │       Track A         │           │        Track B           │
        │  Prompt Pack v2.0     │           │    Context 管理          │
        ├───────────────────────┤           ├───────────────────────────┤
        │ A1 Schema 收尾 (1h)   │           │ B1 场景识别增强 (2h)      │
        │ A2 Pack 示例 (3h)     │           │ B2 NotebookLM (2h)       │
        │ A3 CLI 工具 (2h)      │           │ B3 持久化存储 (2h)       │
        └───────────────────────┘           └───────────────────────────┘
```

---

## 协作通信协议

### 每小时 Checkpoint (自动触发)

**CodeArts → Claude Code**:
- 当前进度
- 遇到的问题
- 需要的审查/验证

**Claude Code → CodeArts**:
- 审查结果
- 验证命令输出
- 下一步建议

### 阻塞处理
- 立即使用 Notification API 广播
- 优先级: 🟡 medium (非阻塞性) / 🔴 high (阻塞进度)

### 结果提交
- CodeArts 提交到 `collaboration/results/RESULT_*.md`
- Claude Code 验证后更新状态
- Session health 自动监控健康度

---

## 执行命令

### 系统初始化 (Claude Code)
```bash
# 注册当前会话
python3 -m ai_collab.cli sessions register --assignee claude --session-id claude-tracka-april05 --transport-mode bridge

# 检查系统健康
python3 -m ai_collab.cli sessions health

# 验证任务契约
python3 -m ai_collab.cli tasks validate-contract --scope all --strict
```

### Track A 验证 (Claude Code)
```bash
# Schema 测试
pytest tests/unit/test_schema_v2.py --cov=src.ai_collab/pack/schema_v2 --cov-report=term

# Pack 验证
python3 -m ai_collab.cli pack validate --path packs/examples/*.json

# CLI 测试
python3 -m ai_collab.cli pack --help
```

### Track B 验证 (Claude Code)
```bash
# 场景识别测试
pytest tests/unit/context/test_scenario.py -v

# NotebookLM 集成测试
pytest tests/unit/context/test_enhanced.py -v

# Context API 测试
pytest tests/integration/test_context_api.py -v
```

---

## 验收标准

### Track A 验收
- [ ] Schema 测试覆盖率 ≥ 90%
- [ ] 5 个 Pack 示例完整通过验证
- [ ] 3 个 CLI 命令正常工作
- [ ] 无 P0/P1 Bug

### Track B 验收
- [ ] 场景识别准确度 ≥ 85%
- [ ] NotebookLM 集成正常工作
- [ ] Context 可持久化到 SQLite
- [ ] 重启后数据保持

### 综合验收
- [ ] Session health 显示 healthy
- [ ] 无 unregistered incidents
- [ ] Contract validation 通过
- [ ] Result consistency 100%
- [ ] 协作日志完整

---

## 心跳要求

每 30 分钟更新一次进度到结果文件，包含：
- 轨道进度 (A/B)
- 完成的子任务
- 遇到的阻塞
- 下一步计划
- 与另一方的协作状态

---

## 开始指令

### Claude Code 开始
```bash
# 1. 注册会话
python3 -m ai_collab.cli sessions register --assignee claude --session-id claude-tracka-april05 --transport-mode bridge

# 2. 开始 A1 (Schema 收尾)
cd tests/unit && vim test_schema_v2.py

# 3. 启动监控
python3 -m ai_collab.cli --watch
```

### CodeArts 开始
```bash
# 1. 确认会话已注册
python3 -m ai_collab.cli sessions inspect --assignee codearts_agent

# 2. 开始 B1 (场景识别增强)
cd src/ai_collab/context && vim scenario.py

# 3. 每 30min 报告进度
```

---

创建人: Claude (Technical Partner)
协作方: Claude Code + CodeArts Agent
控制面: Session Orchestration (已就绪)
开始时间: 2026-04-05 06:35
目标完成时间: 2026-04-05 12:35 (6h)
