# 🎯 即时行动清单 (Action Items)

**生成日期**: 2026-02-26  
**优先级排序**: 🔴红 > 🟡黄 > 🟢绿

---

## 第一梯队：立即处理 (本周)

### 🔴 P0-1: 解决 cli.py 文件冲突

**任务ID**: IMPLEMENT-CONFLICT-RESOLUTION  
**分配给**: Claude Code  
**预期时间**: 1-2 天  
**优先级**: 🔴 高

**具体步骤**:
```
[ ] 1. 分析冲突详情
      └─ 查看: logs/collaboration_issues.json
      └─ 冲突文件: ai_collab/cli.py
      └─ 涉及 AI: claude_code vs copilot

[ ] 2. 确定所有权
      └─ 在 rules/ 目录创建 OWNERSHIP.md
      └─ 声明: ai_collab/cli.py = Claude 所有权
      └─ 原因: 初始创作者 + 主要贡献者

[ ] 3. Copilot 回退
      └─ 通知 Copilot 回退对 cli.py 的修改
      └─ 保留对其他文件的改动

[ ] 4. Claude 整合版本
      └─ 提取 Copilot 版本的有益改动
      └─ 合并到 Claude 版本
      └─ 确保功能完整性

[ ] 5. 更新冲突状态
      └─ 将 CONFLICT-1772060801 标记为 resolved
      └─ 更新 logs/collaboration_issues.json
      └─ 记录解决方案到日志

[ ] 6. 验证测试
      └─ python3 -m ai_collab.cli --help (验证命令可用)
      └─ 所有子命令测试通过
```

**输出文件**:
- `rules/OWNERSHIP.md` (新建)
- `logs/collaboration_issues.json` (更新)
- `ai_collab/cli.py` (最终版本)

**验收标准**:
- ✅ cli.py 冲突状态改为 resolved
- ✅ 所有 CLI 命令都能执行
- ✅ 两个 AI 的改动都被合理整合

---

### 🔴 P0-2: 实现双向交接回通知

**任务ID**: IMPLEMENT-BIDIRECTIONAL-HANDOFF  
**分配给**: Claude Code  
**预期时间**: 2-3 天  
**优先级**: 🔴 高

**背景**:
当前交接流程是单向的:
```
Copilot 完成 → 写入 handoff_status.json → Claude 轮询读取 ❌
```

目标改为双向:
```
Copilot 完成 → Claude 接收 → Claude 回通知 ✅
```

**具体步骤**:
```
[ ] 1. 修改 state_manager.py
      └─ 添加方法: acknowledge_handoff(handoff_id, status)  
      └─ 在处理完成后更新 handoff_status.json
      └─ 传输信息: 处理时间、结果摘要、下步待办

[ ] 2. 更新 handoff_status.json 格式
      当前:
      {
        "from_ai": "copilot",
        "to_ai": "claude_code",
        "status": "RECEIVED_AND_PROCESSING"
      }
      
      目标格式:
      {
        "from_ai": "copilot",
        "to_ai": "claude_code",
        "status": "ACKNOWLEDGED_BY_CLAUDE",
        "processed_at": "2026-02-26T XX:XX:XX",
        "return_status": {
          "from_ai": "claude_code",
          "to_ai": "copilot",
          "message": "已处理，结果保存到...",
          "acknowledged_at": "2026-02-26T XX:XX:XX"
        }
      }

[ ] 3. 修改 cli.py
      └─ 添加 handoff acknowledge 命令
      └─ 命令格式: acknowledge-handoff --id HANDOFF-XXX --status completed

[ ] 4. 测试完整工作流
      └─ Copilot 创建交接任务
      └─ Claude 接收并处理
      └─ Claude 发送回通知
      └─ Copilot 接收回通知确认

[ ] 5. 文档更新
      └─ 更新 OPERATION_MANUAL.md 的交接流程说明
      └─ 添加双向交接示例
```

**输出文件**:
- `ai_collab/state_manager.py` (修改)
- `ai_collab/cli.py` (修改)
- `handoff_status.json` (新格式)
- `OPERATION_MANUAL.md` (更新)

**验收标准**:
- ✅ 交接状态从 RECEIVED → ACKNOWLEDGED
- ✅ 回通知信息被正确写入
- ✅ 双向流畅，无死锁

---

### 🔴 P0-3: 创建文件所有权清单

**任务ID**: CREATE-OWNERSHIP-DOCUMENT  
**分配给**: Claude Code  
**预期时间**: 1 天  
**优先级**: 🔴 高

**输出**:
```
rules/OWNERSHIP.md
```

**内容模板**:
```markdown
# 文件所有权与职责分配表

**版本**: 1.0
**最后更新**: 2026-02-26
**维护者**: Claude Code

## 所有权分配原则

1. 初始创作者拥有所有权
2. 共享文件需标记 "shared"
3. 重大改动需通知所有者

## 所有权清单

| 文件 | 所有权 | 理由 | 协作方向 |
|------|--------|------|----------|
| ai_collab/activation_handler.py | Claude | 核心架构设计者 | R (可读) |
| ai_collab/cli.py | Claude | 初始创作 + 主要功能 | R (可读) |
| ai_collab/state_manager.py | Shared | 双方都需要修改 | RW (读写) |
| ai_collab/dev_logger.py | Claude | 实现者 + 维护者 | R (可读) |
| rules/copilot_rules.md | Copilot | Copilot 特定规则 | RO (仅读) |
| rules/claude_code_memory.md | Claude | Claude 特定规则 | RO (仅读) |
| rules/AI-COLLABORATION-STANDARDS.md | Shared | 双方遵守 | RO (仅读) |
| ... | | | |
```

**验收标准**:
- ✅ 所有源文件都有明确分配
- ✅ 所有权文档放在规则目录
- ✅ 两个 AI 都同意此分配

---

## 第二梯队：本周内完成 (2-3 天)

### 🟡 P1-1: 完成 Pack Schema v2.0

**任务ID**: COMPLETE-PACK-SCHEMA-V2  
**分配给**: Claude Code  
**预期时间**: 2 天  
**优先级**: 🔴 高

**现状**: 60% 完成 (`src/ai_collab/pack/schema_v2.py`)

**待完成项**:
```
[ ] 1. WorkflowStep 完整定义
      └─ 补充 step_config 字段细节
      └─ 添加验证方法
      └─ 支持所有 6 种 step_type

[ ] 2. AI-Roundtable 多 AI 配置
      └─ 定义 AIModel 数据类
      └─ 支持多 AI 并行执行
      └─ 定义 AI 选择策略

[ ] 3. Validator 类实现
      └─ validate_prompt() - 验证 prompt 格式
      └─ validate_workflow() - 验证工作流完整性
      └─ validate_examples() - 验证示例有效性

[ ] 4. 质量追踪器
      └─ 添加 QualityTracker 类
      └─ 记录每步执行质量
      └─ 计算综合质量分数

[ ] 5. 版本管理
      └─ 添加 VersionManager
      └─ 支持语义版本 (SemVer)
      └─ Delta 变更记录

[ ] 6. 单元测试
      └─ 测试所有 dataclass 序列化/反序列化
      └─ 测试 Validator 的验证规则
      └─ 测试版本升级流程

[ ] 7. 文档更新
      └─ 添加 Schema 使用示例
      └─ 添加 API 文档
```

**输出文件**:
- `src/ai_collab/pack/schema_v2.py` (完成)
- `src/ai_collab/pack/tests/test_schema_v2.py` (新建)
- `docs/pack-schema-guide.md` (新建)

**验收标准**:
- ✅ 所有类型定义完整
- ✅ 所有验证方法都有单元测试
- ✅ 序列化测试 100% 通过
- ✅ 文档完整且清晰

---

### 🟡 P1-2: 启动 Chrome Extension 核心模块

**任务ID**: BOOTSTRAP-CHROME-EXTENSION  
**分配给**: Claude Code  
**预期时间**: 3-4 天  
**优先级**: 🔴 高

**工作范围**:
```
创建目录结构和基础文件

prompt-pack-extension/
├── manifest.json                ← 主要配置
├── service-worker.js            ← 后台脚本
├── content-scripts/
│   ├── injector.js              ← 脚本注入
│   ├── dom-observer.js          ← DOM 监听
│   └── pack-executor.js         ← Pack 执行
├── background/
│   └── pack-manager.js          ← Pack 管理
├── popup/
│   ├── popup.html
│   ├── popup.js
│   └── popup.css
└── icons/
    ├── icon-16.png
    ├── icon-32.png
    ├── icon-128.png
    └── icon-256.png
```

**具体步骤**:
```
[ ] 1. 初始化项目
      └─ mkdir prompt-pack-extension
      └─ 创建基础目录结构

[ ] 2. 创建 manifest.json (v3)
      └─ 基于 ARCHITECTURE.md 的设计
      └─ 定义权限、host_permissions
      └─ 配置 service_worker
      └─ 配置 content_scripts

[ ] 3. 实现 service-worker.js
      └─ 处理 onMessage 事件
      └─ 管理 Pack 状态
      └─ 与本地后端通信

[ ] 4. 创建 content-scripts/injector.js
      └─ 检测目标网站
      └─ 加载 Pack
      └─ 初始化通信

[ ] 5. 创建 content-scripts/dom-observer.js
      └─ DOM 元素监听模板
      └─ 等待元素出现的逻辑
      └─ 超时处理

[ ] 6. 创建 content-scripts/pack-executor.js
      └─ 执行工作流步骤
      └─ 处理 input/select/validate/output 类型

[ ] 7. 创建 popup UI
      └─ 基础 HTML 结构
      └─ Pack 列表显示
      └─ 快速操作按钮

[ ] 8. 生成图标资源
      └─ 创建 4 个不同尺寸的图标

[ ] 9. 测试加载
      └─ chrome://extensions 加载扩展
      └─ 验证 manifest 有效性
      └─ 确保没有权限警告
```

**输出**:
- `prompt-pack-extension/` 完整项目结构
- GitHub repo 推荐: `prompt-pack-chrome-ext`

**验收标准**:
- ✅ Extension 可加载到 Chrome
- ✅ Service Worker 正常运行
- ✅ Popup 可打开显示
- ✅ manifest validation 通过

---

## 第三梯队：下周启动 (3-5 天)

### 🟡 P1-3: 启动 Local Backend FastAPI

**任务ID**: BOOTSTRAP-LOCAL-BACKEND  
**分配给**: Claude Code  
**预期时间**: 3-5 天  
**优先级**: 🔴 高

**项目结构**:
```
local-backend/
├── main.py                      ← FastAPI 主应用
├── requirements.txt             ← 依赖
├── Dockerfile
├── docker-compose.yml
├── api/
│   ├── packs.py                 ← Pack API
│   ├── search.py                ← 搜索 API
│   └── health.py                ← 健康检查
├── db/
│   ├── models.py                ← SQLite 模型
│   ├── migrations.py            ← 数据库迁移
│   └── init_db.py               ← 初始化
├── services/
│   ├── pack_service.py          ← Pack 业务逻辑
│   └── spec_service.py          ← OpenSpec 业务逻辑
├── tests/
│   ├── test_api.py
│   ├── test_db.py
│   └── conftest.py
└── data/
    └── packs.db                 ← SQLite 数据库文件
```

**工作步骤**:
```
[ ] 1. 项目初始化
      └─ mkdir local-backend && cd local-backend
      └─ python -m venv venv
      └─ pip install fastapi uvicorn sqlalchemy

[ ] 2. 创建 main.py
      └─ FastAPI 应用初始化
      └─ CORS 配置
      └─ 中间件配置

[ ] 3. 实现 DB 层
      └─ SQLAlchemy 模型定义
      └─ 创建 SQLite 初始化脚本
      └─ 实现数据库迁移框架

[ ] 4. 实现 API 端点
      └─ GET /health
      └─ GET /api/v2/packs
      └─ GET /api/v2/packs/{pack_id}
      └─ POST /api/v2/packs
      └─ POST /api/v2/packs/{pack_id}/vote
      └─ GET /api/v2/search

[ ] 5. 实现业务逻辑
      └─ PackService
      └─ SpecService (OpenSpec 管理)
      └─ 验证逻辑

[ ] 6. 添加错误处理
      └─ 统一错误响应格式
      └─ 日志集成
      └─ 异常处理中间件

[ ] 7. 创建 Docker 支持
      └─ Dockerfile
      └─ docker-compose.yml
      └─ .dockerignore

[ ] 8. 添加测试
      └─ test_api.py (API 端点测试)
      └─ test_db.py (数据库测试)
      └─ pytest 配置

[ ] 9. 验证运行
      └─ docker-compose up
      └─ curl http://127.0.0.1:8000/health
      └─ 所有 API 端点都能响应
```

**输出**:
- `local-backend/` 完整项目
- 可通过 `docker-compose up` 启动
- API 文档: http://127.0.0.1:8000/docs (Swagger UI)

**验收标准**:
- ✅ 所有 API 端点可用
- ✅ SQLite 数据库正常创建
- ✅ Docker Compose 启动成功
- ✅ API 单元测试 > 80% 覆盖率

---

## 第四梯队：抽时间完成

### 🟢 P2-1: VSCode Extension 框架搭建

**任务ID**: BOOTSTRAP-VSCODE-EXTENSION  
**分配给**: Claude Code  
**预期时间**: 2-3 周 (暂时)(后续)  
**优先级**: 🟡 中

**暂时搁置原因**: 等待 Chrome Extension 和 Backend 初步完成

**预计启动时间**: v0.8 阶段 (4-6 周后)

---

## 进度追踪表

### 基座项目 (AI 协作系统)

| 任务 | P0 | 分配给 | 状态 | 完成度 | Due |
|------|-----|--------|------|--------|-----|
| 🔴 P0-1 解决 cli.py 冲突 | 1 | Claude | 进行中 | 0% | 2026-02-27 |
| 🔴 P0-2 双向交接回通知 | 2 | Claude | 待开始 | 0% | 2026-03-01 |
| 🔴 P0-3 文件所有权清单 | 3 | Claude | 待开始 | 0% | 2026-02-26 |
| v2.0.1 发布 | - | Claude | 待开始 | 0% | 2026-03-05 |

### Prompt Pack 项目

| 任务 | P0 | 分配给 | 状态 | 完成度 | Due |
|------|-----|--------|------|--------|-----|
| 🔴 P1-1 完成 Schema v2.0 | 1 | Claude | 进行中 | 60% | 2026-03-01 |
| 🔴 P1-2 Chrome Ext 核心 | 2 | Claude | 待开始 | 0% | 2026-03-04 |
| 🔴 P1-3 Local Backend API | 3 | Claude | 待开始 | 0% | 2026-03-07 |
| v0.5 完成标志 | - | Claude | 待开始 | 0% | 2026-03-08 |

---

## 关键截止日期

```
2026-02-27   │ P0-1 解决冲突
2026-02-28   │ P0-3 所有权文档
2026-03-01   │ P0-2 交接回通知 + P1-1 Schema 完成
2026-03-04   │ P1-2 Chrome Ext 初版
2026-03-05   │ v2.0.1 发布 (基座)
2026-03-07   │ P1-3 Backend 初版
2026-03-08   │ v0.5 完成 (Pack)
2026-03-12   │ 首个里程碑 + 核查汇总
```

---

**最后更新**: 2026-02-26  
**维护者**: Claude Code  
**同步频率**: 每日更新进度
