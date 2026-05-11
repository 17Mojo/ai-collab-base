# AI Collab System - Prompt Pack v2.0

一个本地优先的 AI 聊天自动化工具，通过 Chrome 扩展实现多 AI 平台的内容生成自动化，支持 NotebookLM 知识增强。

---

## 简介

**AI Collab System** 是一个**本地优先**的 Chrome 扩展 + 本地后端系统：

- 🎯 **多平台支持**: ChatGPT、Claude、Gemini、Kimi、通义千问、智谱清言等 10+ 平台
- 🔧 **Pack 工作流**: 支持 6 种步骤类型 + 分支逻辑 + 正则表达式匹配
- 📚 **知识增强**: NotebookLM 集成，21+ 知识源注入
- 🚀 **本地后端**: FastAPI + SQLite，59 个 API 端点
- 🤝 **AI 协作**: Claude Code + CodeArts Agent + Codex 多 AI 协同

**核心理念**：零成本、零配置、完全离线可用。

---

## 项目状态 (v1.0.0)

| 指标 | 状态 |
|------|------|
| Chrome Extension | ✅ 10 平台适配器 + PackExecutor |
| Backend API | ✅ 59 端点 + Prometheus Metrics |
| NotebookLM | ✅ 21+ 知识源集成 |
| CI/CD | ✅ 7 GitHub Actions 工作流 |
| 安全 | ✅ 5/5 安全头配置 |
| 文档 | ✅ 51 文档文件 |
| 测试 | ✅ 核心功能验证通过 |

**发布状态**: ✅ **已达到 v1.0.0 发布标准**

---

## 功能特性

### 🎯 Prompt Pack v2.0 核心功能

- ✅ **多平台支持**: ChatGPT、Claude、Kimi、通义千问、智谱清言
- ✅ **工作流引擎**: 支持 6 种步骤类型（本地、分析、生成、验证、融合、追踪）
- ✅ **多 AI 协同**: 支持多 AI 并行生成 + 交叉验证
- ✅ **质量指标**: 可配置的质量评估体系
- ✅ **示例库**: 好示例/差示例驱动的生成优化
- ✅ **性能追踪**: 执行时间、成功率、发布后效果追踪

### 🔧 系统组件

| 组件 | 技术栈 | 描述 |
|------|--------|------|
| **Chrome Extension** | Manifest V3 | 注入脚本、执行 Pack、监控 DOM |
| **Local Backend** | FastAPI + SQLite | Pack 注册、API 端点、数据存储 |
| **Pack Schema** | Python Dataclass | Pack v2.0 完整定义 |

### 🤝 AI 协作功能

- ✅ **双 AI 支持**: Claude Code + GitHub Copilot 无缝协作
- ✅ **冲突检测**: 保存时自动检测 + 命令触发检测
- ✅ **任务管理**: 统一注册、追踪和管理开发任务
- ✅ **通知系统**: broadcast / broadcast@mention / direct 三种模式

## 快速开始

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/17Mojo/ai-collab-system.git
cd ai-collab-system

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 安装开发依赖（可选，用于测试和开发）
pip install -r requirements-dev.txt

# 4. 初始化项目
python3 -m ai_collab.cli init

# 指定工作区（两种写法都支持）
python3 -m ai_collab.cli -w . init
python3 -m ai_collab.cli init --workspace .
```

### 启动后端服务

```bash
# 进入后端目录
cd local-backend

# 启动 FastAPI 服务（开发模式）
uvicorn app.main:app --reload --port 8000

# 或使用 Python 直接启动
python -m uvicorn app.main:app --port 8000

# 访问 API 文档
# http://127.0.0.1:8000/docs (Swagger UI)
# http://127.0.0.1:8000/redoc (ReDoc)
```

### 安装 Chrome 扩展

1. 打开 Chrome 浏览器，访问 `chrome://extensions/`
2. 开启右上角 **"开发者模式"**
3. 点击 **"加载已解压的扩展程序"**
4. 选择项目中的 `chrome-extension/` 目录
5. 扩展安装成功后，会在扩展栏显示 "AI Collab System"

**验证安装**:
- 访问任意支持的 AI 平台（如 `https://claude.ai`）
- 点击扩展图标，应显示平台适配状态

### 环境要求

- Visual Studio Code 1.80+
- Claude Code 扩展
- GitHub Copilot 扩展
- Python 3.8+

### 使用方式

#### 方式 1: VSCode 任务（推荐）

```
Ctrl+Shift+P → Tasks: Run Task
```

可选任务：
- `AI Collab: Activate Claude Code` - 激活 Claude Code
- `AI Collab: Activate Copilot` - 激活 Copilot
- `AI Collab: Check Conflicts` - 检查文件冲突
- `AI Collab: List Active Tasks` - 查看活跃任务
- `AI Collab: Initialize Project` - 初始化项目

#### 方式 2: 激活词

在输入中包含 `2X` 即可激活：

```python
# 示例
"开始重构用户认证 API 2X"  # 会触发激活
"开始重构用户认证 API"    # 不会触发
```

#### 方式 3: CLI 命令

```bash
# 激活 AI
python3 -m ai_collab.cli activate --ai claude
python3 -m ai_collab.cli activate --ai copilot

# 检查冲突
python3 -m ai_collab.cli check --ai claude --files src/api.ts

# 查看状态
python3 -m ai_collab.cli status

# 任务管理
python3 -m ai_collab.cli tasks list --status active
python3 -m ai_collab.cli tasks register --ai claude_code --description "xxx" --files "api.ts"

# 日志管理
python3 -m ai_collab.cli logs list
python3 -m ai_collab.cli logs show --month 2026-02 --log-file task.md

# 冲突管理
python3 -m ai_collab.cli conflicts list
python3 -m ai_collab.cli conflicts resolve --conflict-id CONFLICT-XXX

# Codex 协作（快速落地）
# 0) 单命令流水线（推荐）：plan -> progress -> run -> sync
python3 -m ai_collab.cli codex exec \
  --goal "登录接口第一批实现" \
  --intent "修复登录接口并补测试" \
  --model "gpt-5-codex" \
  --step "实现登录 API 与参数校验" \
  --step "补充单元测试并确保通过" \
  --file "local-backend/app/api/auth.py" \
  --file "tests/integration/test_api.py" \
  --test-cmd "pytest -q" \
  --task-id TASK-CODEX-LOGIN-001

# 1) 初始化 .cc-claude-codex/
python3 -m ai_collab.cli codex init --goal "实现登录接口并补单测"

# 2) 生成批次任务（可多次 --step）
python3 -m ai_collab.cli codex progress \
  --goal "登录接口第一批实现" \
  --step "实现登录 API 与参数校验" \
  --step "补充单元测试并确保通过" \
  --file "local-backend/app/api/auth.py" \
  --file "tests/integration/test_api.py" \
  --test-cmd "pytest -q"

# 3) 执行 Codex，并自动同步到 logs/collaboration_state.json
python3 -m ai_collab.cli codex run --sync --task-id TASK-CODEX-LOGIN-001

# 4) 单独同步状态（可选）
python3 -m ai_collab.cli codex sync --task-id TASK-CODEX-LOGIN-001

# 5) 动态角色规划（按意图+模型决定主辅）
python3 -m ai_collab.cli codex plan \
  --intent "修复登录接口并补测试" \
  --model "gpt-5-codex" \
  --model "claude-sonnet" \
  --emit-tasks

# 6) 安装 Claude hooks（Stop/PreCompact/SessionStart）
python3 -m ai_collab.cli codex hooks --hook-action install

# 7) hooks 诊断与自动修复（settings 结构异常时）
python3 -m ai_collab.cli codex hooks --hook-action doctor
```

## 发布前一键检查

```bash
# 安装本地门禁 hooks（pre-commit + pre-push）
make pre-commit-install

# 快速门禁（本地快速验证）
bash scripts/pre_release_check.sh --quick

# 严格门禁（状态漂移 + 锁校验 + 全量测试）
bash scripts/pre_release_check.sh --with-locks

# 正式发布（默认先执行门禁）
bash scripts/release.sh

# 手动触发 pre-push 发布快速门禁
pre-commit run pre-push-release-quick-gate --hook-stage pre-push
```

更多发布步骤见 [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md)。

## CI 门禁

- PR / 分支提交会自动触发 `.github/workflows/ci.yml`
- CI 先跑快速门禁（状态漂移 + 协同治理 + 锁看板 + 快速测试），再跑全量测试
- 发布标签流程由 `.github/workflows/release.yml` 负责
- 仓库已提供 Code Owners 配置：`.github/CODEOWNERS`
- 分支保护配置指南见 [docs/BRANCH_PROTECTION_SETUP.md](docs/BRANCH_PROTECTION_SETUP.md)

## 项目结构

```
ai-collab-system/
├── .vscode/                      # VSCode 配置
│   ├── settings.json            # VSCode 项目设置
│   ├── tasks.json               # 11 个预定义任务
│   ├── ai-collab.json           # AI 协作项目配置
│   └── ai-collab.code-snippets  # 5 个代码片段
│
├── ai_collab/                    # Python 主包
│   ├── __init__.py              # 包初始化
│   ├── activation_handler.py    # 激活处理器
│   ├── state_manager.py         # 状态管理器
│   ├── dev_logger.py           # 开发日志
│   └── cli.py                  # CLI 入口
│
├── src/                          # 源代码副本
│
├── rules/                        # 协作规则
│   ├── claude_code_memory.md   # Claude Code 规则
│   ├── copilot_rules.md        # Copilot 规则
│   └── dev-record-template.md  # 日志模板
│
├── logs/                         # 日志目录（自动生成）
│   ├── claude-code/            # Claude Code 日志
│   ├── copilot/                # Copilot 日志
│   └── collaboration_state.json # 协作状态
│
└── .git/ai-collab/               # Git 追踪日志
```

## Claude Code vs Copilot 职责分配

| 功能 | Claude Code | Copilot |
|------|-------------|---------|
| 架构设计 | ✅ 主要 | ❌ 不参与 |
| 单元测试 | ✅ 主要 | ⚠️ 辅助 |
| 文档生成 | ✅ 主要 | ❌ 不参与 |
| 代码补全 | ⚠️ 有限 | ✅ 主要 |
| 代码优化 | ✅ 主要 | ✅ 辅助 |
| 错误修复 | ✅ 主要 | ✅ 辅助 |
| 重复代码检测 | ❌ | ✅ 主要 |
| 网络研究 | ❌ | ✅ 主要 |

## 配置

编辑 `.vscode/ai-collab.json` 自定义配置：

```json
{
  "version": "1.0.0",
  "rulesDir": "./rules",
  "logsDir": "./logs",
  "stateFile": "./logs/collaboration_state.json",
  "activationKeyword": "2X",
  "watchExtensions": [".ts", ".tsx", ".js", ".py"],
  "conflictCheckOnSave": true,
  "conflictCheckOnCommand": true,
  "showOutputPanel": true,
  "autoLogToGit": true,
  "enabledAIs": ["claude_code", "copilot"],
  "agentOrchestration": {
    "autoDetectAgents": true,
    "includeUserAsOperator": true,
    "operatorFirst": false,
    "forceLeadAgent": null,
    "disabledAgents": [],
    "intentLeadMap": {
      "architecture": ["claude_code", "codex", "copilot"],
      "implementation": ["codex", "claude_code", "copilot"],
      "testing": ["copilot", "codex", "claude_code"],
      "documentation": ["copilot", "claude_code", "codex"]
    },
    "modelAgentMap": {
      "claude": "claude_code",
      "copilot": "copilot",
      "gpt|codex|openai": "codex"
    }
  }
}
```

## VSCode 代码片段

输入以下触发词快速插入：

| 触发词 | 描述 |
|--------|------|
| `2X-activate` | 激活 Claude Code |
| `2X-copilot` | 激活 Copilot |
| `ai-task` | AI 协作任务头部 |
| `conflict-mark` | 冲突区域标记 |
| `ai-progress` | 开发进度注释 |

## 文档

- [操作手册](OPERATION_MANUAL.md) - 完整的操作指南
- [快速参考](QUICK_REFERENCE.md) - 常用命令速查
- [完成报告](COMPLETION_SUMMARY.md) - 项目改造 v2.0.0 详情
- [进展快照](collaboration/results/PROJECT_PROGRESS_SYNC_2026-03-01.md) - 最新任务/patch/测试状态
- [剩余工单](REMAINING_TASKS_SUMMARY.md) - 当前未闭环事项
- [Long-running Harness](docs/LONG_RUNNING_HARNESS.md) - 持续任务循环（initializer + one-feature sessions）
- [更新日志](CHANGELOG.md) - 版本历史和变更记录
- [贡献指南](CONTRIBUTING.md) - 如何为项目做贡献
- [许可证](LICENSE) - MIT 许可证

## 协作流程

1. **Claude Code** 负责架构设计和核心逻辑实现
2. **Copilot** 协助代码补全和局部优化
3. 保存文件时自动触发冲突检测
4. 三重日志记录所有协作历史
5. Git 追踪记录供团队审查

## 日志位置

| 类型 | 位置 |
|------|------|
| 项目本地 | `logs/ai-type/YYYY-MM/file.md` |
| Git 追踪 | `.git/ai-collab/ai-type/file.md` |
| VSCode 输出 | `~/.vscode/ai-collab/output_YYYYMMDD.log` |

## 演示

运行演示代码查看所有功能：

```bash
python3 demo.py
```

## 版本历史

| 版本 | 日期 | 主要改动 |
|-----|------|---------|
| 2.0.0 | 2026-02-26 | VSCode 集成、支持 Copilot、三重日志 |
| 1.0.0 | 2026-01-xx | 初始版本 |

## 许可证

MIT License
