# AI Collab Base - Prompt Pack v2.0 执行平台

> **定位**: 本地优先的 AI 聊天自动化执行平台
>
> **姊妹项目**: [ai-collab-research](https://github.com/17Mojo/ai-collab-research) - 研究成果 + 防遗忘工具

一个本地优先的 AI 聊天自动化工具，通过 Chrome 扩展实现多 AI 平台的内容生成自动化。

---

## 核心理念

零成本、零配置、完全离线可用

---

## 功能特性

### 🎯 Prompt Pack v2.0

- **多平台支持**: ChatGPT、Claude、Gemini、Kimi、通义千问、智谱清言等 10+ 平台
- **Pack 工作流**: 支持 6 种步骤类型 + 分支逻辑 + 正则表达式匹配
- **知识增强**: NotebookLM 集成，21+ 知识源注入

### 🔧 系统组件

| 组件 | 技术栈 | 描述 |
|------|--------|------|
| **Chrome Extension** | Manifest V3 | 注入脚本、执行 Pack、监控 DOM |
| **Local Backend** | FastAPI + SQLite | Pack 注册、API 端点、数据存储 |
| **Pack Schema** | Python Dataclass | Pack v2.0 完整定义 |

### 🤝 动态角色编排架构

本项目采用**角色别名驱动**的动态协作架构，Agent 提供商通过配置动态绑定：

```
角色代号 (Role ID)     职责定位
──────────────────────────────────
AGENT_EXEC           主执行者 (R)
AGENT_ARCH           架构师 (A)
AGENT_TEST           测试验证 (C)
AGENT_DOC            文档编写 (C)
```

**冷启动配置**：
```bash
# CLI 方式
python3 -m src.cli orchestration cold-start

# 或通过 /menu 技能
/menu
```

**命令协议**：
- `X.RUN` → AGENT_EXEC
- `A.RUN` → AGENT_ARCH
- `C.RUN` → AGENT_TEST

---

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/17Mojo/ai-collab-base.git
cd ai-collab-base

# 安装 Python 依赖
pip install -r requirements.txt
```

### 启动后端服务

```bash
cd local-backend

# 开发模式
uvicorn app.main:app --reload --port 8000

# 访问 API 文档
# http://127.0.0.1:8000/docs
```

### 安装 Chrome 扩展

1. Chrome 浏览器访问 `chrome://extensions/`
2. 开启 **开发者模式**
3. 点击 **加载已解压的扩展程序**
4. 选择 `chrome-extension/` 目录

---

## 项目结构

```
ai-collab-base/
├── chrome-extension/     # Chrome 扩展代码
├── local-backend/        # FastAPI 后端
├── src/                  # Python 源代码
├── tests/                # 测试文件
├── packs/                # Pack 示例
├── data/                 # SQLite 数据库
├── rules/                # AI 协作规则
├── collaboration/        # 协作配置与模板
│   ├── PROTOCOL.md       # 协作协议
│   ├── COLLABORATION_GUIDELINES.md  # 协作准则
│   └── guides/           # 操作指南
├── ARCHITECTURE.md       # 系统架构设计
└── CLAUDE.md             # 项目说明
```

---

## 详细文档

- [ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构设计
- [CLAUDE.md](CLAUDE.md) - 项目说明与 AI 协作规则
- [collaboration/PROTOCOL.md](collaboration/PROTOCOL.md) - 多 Agent 协作协议
- [collaboration/COLLABORATION_GUIDELINES.md](collaboration/COLLABORATION_GUIDELINES.md) - 协作准则

---

## 环境要求

- Python 3.8+
- Chrome 浏览器

---

## 许可证

MIT License
