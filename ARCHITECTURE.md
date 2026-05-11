# Prompt Pack 系统架构设计 v2.0

## 系统概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Prompt Pack System Architecture v2.0                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────┐  │
│  │  Chrome     │     │   VS Code   │     │   Local Backend Server      │  │
│  │  Extension  │     │   Extension │     │   (FastAPI + Docker)        │  │
│  │  (Manifest  │     │   (Native    │     │                             │  │
│  │   V3)       │     │   Messaging) │     │  ┌──────────────────────┐  │  │
│  ├─────────────┤     ├─────────────┤     │  │  Pack Registry DB    │  │  │
│  │ Content     │◄────┤ Host Client │─────►─┼──┤ (SQLite - 单文件)     │  │  │
│  │ Script      │     │             │     │  └──────────────────────┘  │  │
│  │ Injector    │     ├─────────────┤     │                             │  │
│  │             │     │ Copilot/    │     │  ┌──────────────────────┐  │  │
│  │ Pack        │     │ Claude      │     │  │  OpenSpec Engine     │  │  │
│  │ Executor    │     │ Collab      │     │  │  (Python)            │  │  │
│  │             │     │ System      │     │  │  - Version Manager   │  │  │
│  │ DOM         │     │             │     │  │  - Delta Tracker     │  │  │
│  │ Observer    │     ├─────────────┤     │  └──────────────────────┘  │  │
│  │             │     │ Notification│     │                             │  │
│  │ Config      │     │ API         │     │  ┌──────────────────────┐  │  │
│  │ Manager     │     │             │     │  │  Pack Validator      │  │  │
│  └─────────────┘     └─────────────┘     │  │  (Quality Metrics)   │  │  │
│       │                  │               │  └──────────────────────┘  │  │
│       │                  │               │  ┌──────────────────────┐  │  │
│       └──────────────────┴───────────────►─┼──┤  Cache Layer         │  │  │
│                         ↕ API Sync        │  │  (lru_cache)         │  │  │
│                         http://127.0.0.1:8000  └──────────────────────┘  │  │
└─────────────────────────────────────────────────────────────────────────────┘

本地优先架构 (Local-First):
- 零成本、零配置
- 完全离线可用
- 数据安全可控
- 开发调试便捷

## 一、核心组件架构

### 1.1 Chrome 扩展 (Manifest V3)

#### 目录结构
```
prompt-pack-extension/
├── manifest.json                 # Manifest V3 配置
├── service-worker.js             # 后台服务 Worker
├── content-scripts/
│   ├── injector.js               # 注入到目标网站的脚本
│   ├── dom-observer.js           # DOM 变化监控
│   ├── pack-executor.js          # Pack 执行引擎
│   └── ai-site-handlers/
│       ├── qianwen-handler.js    # 千问专用处理器
│       ├── zhipu-handler.js      # 智谱专用处理器
│       └── kimi-handler.js       # Kimi 专用处理器
├── background/
│   ├── pack-manager.js           # Pack 管理
│   ├── config-manager.js         # 配置管理
│   └── notification-service.js   # 通知服务
├── popup/
│   ├── popup.html                # 扩展弹窗
│   ├── popup.js
│   └── popup.css
└── icons/
```

#### 关键设计点
```json
{
  "manifest_version": 3,
  "name": "Prompt Pack v2.0",
  "version": "2.0.0",
  "permissions": [
    "storage",
    "tabs",
    "activeTab",
    "scripting"
  ],
  "host_permissions": [
    "https://qianwen.aliyun.com/*",
    "https://chatglm.cn/*",
    "https://kimi.moonshot.cn/*"
  ],
  "background": {
    "service_worker": "service-worker.js"
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content-scripts/injector.js"],
      "run_at": "document_idle"
    }
  ],
  "action": {
    "default_popup": "popup/popup.html"
  }
}
```

### 1.2 Pack v2.0 Schema 模块

```python
# src/ai_collab/pack/schema_v2.py

"""
Prompt Pack v2.0 Schema
基于 SemVer 版本控制的标准化生产力模块
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum

class PackState(Enum):
    """Pack 状态"""
    DRAFT = "draft"
    PROPOSED = "proposed"       # 已提交 OpenSpec
    APPROVED = "approved"       # 已通过审核
    PUBLISHED = "published"     # 已发布
    DEPRECATED = "deprecated"   # 已废弃

class PackCategory(Enum):
    """Pack 分类"""
    WORKFLOW = "workflow"           # 工作流辅助
    KNOWLEDGE = "knowledge"         # 知识库
    TEMPLATE = "template"           # 模板库
    TOOL = "tool"                   # 工具函数
    VALIDATOR = "validator"         # 验证器

@dataclass
class QualityMetrics:
    """质量指标"""
    test_coverage: float = 0.0              # 测试覆盖率
    success_rate: float = 0.0               # 成功率
    user_rating: float = 0.0                # 用户评分 (0-5)
    issue_count: int = 0                    # 问题数量
    last_tested_at: Optional[datetime] = None

@dataclass
class WorkflowStep:
    """工作流步骤"""
    step_id: str
    action: str                            # 动作类型: input/select/validate/output
    prompt: str                            # 提示词模板
    fallback_action: Optional[str] = None # 失败时的备选动作
    max_retries: int = 3
    timeout_ms: int = 30000

@dataclass
class ExampleCase:
    """示例用例"""
    case_id: str
    name: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    tags: List[str] = field(default_factory=list)

@dataclass
class PackMetadata:
    """Pack 元数据"""
    name: str
    display_name: str
    description: str
    version: str                          # SemVer: 2.0.0
    author: str
    category: PackCategory
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class PromptPackV2:
    """Prompt Pack v2.0 主类"""
    metadata: PackMetadata
    state: PackState = PackState.DRAFT
    workflow: List[WorkflowStep] = field(default_factory=list)
    quality: QualityMetrics = field(default_factory=QualityMetrics)
    examples: List[ExampleCase] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

    # OpenSpec 相关
    spec_id: Optional[str] = None         # OpenSpec 提案 ID
    delta_id: Optional[str] = None        # Spec Delta ID
    parent_spec: Optional[str] = None     # 父 Spec ID

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "metadata": self._serialize_metadata(),
            "state": self.state.value,
            "workflow": [self._serialize_step(s) for s in self.workflow],
            "quality": self._serialize_quality(),
            "examples": [self._serialize_example(e) for e in self.examples],
            "dependencies": self.dependencies,
            "config": self.config,
            "spec_id": self.spec_id,
            "delta_id": self.delta_id,
            "parent_spec": self.parent_spec
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptPackV2":
        """从字典反序列化"""
        return cls(
            metadata=cls._deserialize_metadata(data["metadata"]),
            state=PackState(data["state"]),
            workflow=[cls._deserialize_step(s) for s in data["workflow"]],
            quality=cls._deserialize_quality(data["quality"]),
            examples=[cls._deserialize_example(e) for e in data["examples"]],
            dependencies=data.get("dependencies", []),
            config=data.get("config", {}),
            spec_id=data.get("spec_id"),
            delta_id=data.get("delta_id"),
            parent_spec=data.get("parent_spec")
        )

    # ... 辅助序列化方法
```

### 1.3 AI 协作系统集成

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Collab System Integration                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────┐         ┌───────────────┐                   │
│  │  Claude Code  │         │   Copilot     │                   │
│  │  (无网络)     │◄─notify─►│  (有网络)     │                   │
│  ├───────────────┤         ├───────────────┤                   │
│  │ • 架构设计    │         │ • 网络调研    │                   │
│  │ • 代码编写    │         │ • 资源收集    │                   │
│  │ • 文档生成    │         │ • Pack 评审   │                   │
│  └───────┬───────┘         └───────┬───────┘                   │
│          │                         │                             │
│          └──────────┬──────────────┘                             │
│                     ↓                                            │
│         ┌─────────────────────────┐                              │
│         │  Notification Queue     │                              │
│         │  - broadcast            │                              │
│         │  - broadcast@mention    │                              │
│         │  - direct               │                              │
│         └───────────┬─────────────┘                              │
│                     ↓                                            │
│         ┌─────────────────────────┐                              │
│         │  Task Queue             │                              │
│         │  (copilot_tasks.md)     │                              │
│         └─────────────────────────┘                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.4 AI Integration 模式治理 (mock/fallback/real)

为保证 AI 集成在不同环境下行为一致，系统统一采用 `IntegrationMode` 三模式治理：

| Mode | 含义 | 适用场景 |
|------|------|----------|
| `mock` | 仅返回模拟响应 | 本地开发、离线测试、回归演练 |
| `fallback` | 优先真实调用，失败时回退模拟 | 默认生产策略（兼顾可用性与可观测） |
| `real` | 仅真实调用，不允许模拟回退 | 严格生产环境、发布前联调 |

默认配置位于 `src/ai_collab/config/integration_flags.py`：

- `notebooklm`: `fallback`
- `consensus_engine`: `fallback`
- `soul_injection`: `fallback`
- `codex`: `real`

配置优先级：

1. `AI_INTEGRATION_MODE_<MODULE>=<mode>`（模块级覆盖）
2. `AI_INTEGRATION_MODE=<mode>`（全局覆盖）
3. `DEFAULT_INTEGRATION_MODES`（代码默认值）

示例：

```bash
# 全局 mock
export AI_INTEGRATION_MODE=mock

# 模块级覆盖（优先级高于全局）
export AI_INTEGRATION_MODE_NOTEBOOKLM=real
```

运行时约束：

- 所有模拟响应必须带 `_mock=True` 与 `_mock_reason`，用于审计。
- `fallback` 模式需记录回退原因与时间，支持健康检查与门禁统计。
- 无效 mode 值必须显式报错，禁止静默降级。

## 二、数据流设计

### 2.1 Pack 生命周期

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    DRAFT    │───►│  PROPOSED   │───►│  APPROVED   │───►│  PUBLISHED  │
│             │    │   (OpenSpec) │    │   (Review)  │    │  (Registry) │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │                  │
       │                  ▼                  │                  ▼
       │         ┌─────────────┐            │           ┌─────────────┐
       └────────►│    VOTE     │────────────┘           │   USE &    │
                 │  (Community)│                        │   UPDATE    │
                 └─────────────┘                        └──────┬──────┘
                                                            │
                                                            ▼
                                                      ┌─────────────┐
                                                      │  DEPRECATED │
                                                      └─────────────┘
```

### 2.2 OpenSpec 发布流程

```
1. 创建提案 (Proposal)
   └─> 提交到 cloud-backend/specs/proposals/
   └─> 生成 Spec ID: SPEC-2026-XXXX

2. 社区审核 (Community Review)
   └─> 公开评论和投票
   └─> Claude 代码审查
   └─> 用户反馈收集

3. 版本升级 (Version Bump)
   └─> SemVer: MAJOR.MINOR.PATCH
   └─> 记录 Spec-Delta
   └─> 向后兼容性检查

4. 注册发布 (Registry Publish)
   └─> 发布到 Pack Registry
   └─> 签名验证
   └─> CDN 分发
```

### 2.3 执行流程

```
用户选择 Pack
      ↓
Chrome 扩展加载 Pack JSON
      ↓
注入 Content Script 到目标网站
      ↓
DOM Observer 等待目标元素出现
      ↓
Pack Executor 执行工作流步骤
      ↓
根据步骤类型执行不同操作:
   ├─ input: 自动填入提示词
   ├─ select: 自动选择选项
   ├─ validate: 验证生成结果
   └─ output: 提取并格式化输出
      ↓
记录执行结果和日志
      ↓
更新 Pack 质量指标
```

## 三、API 设计

### 3.1 Chrome Native Messaging 协议

#### VSCode → Chrome
```json
{
  "version": "1.0.0",
  "message_type": "pack_request",
  "action": "execute_pack",
  "data": {
    "pack_id": "workflow-article-writer-v2",
    "version": "2.1.0",
    "context": {
      "tab_id": 12345,
      "url": "https://qianwen.aliyun.com/chat"
    },
    "parameters": {
      "topic": "AI 协作系统",
      "tone": "professional"
    }
  }
}
```

#### Chrome → VSCode
```json
{
  "version": "1.0.0",
  "message_type": "pack_response",
  "status": "success",
  "data": {
    "pack_id": "workflow-article-writer-v2",
    "execution_id": "EXEC-20260226-001",
    "result": {
      "output_text": "...",
      "duration_ms": 5234,
      "steps_completed": 4
    },
    "metrics": {
      "success_rate": 1.0,
      "user_satisfaction": null
    }
  }
}
```

### 3.2 本地后端 API (FastAPI)

```python
# local-backend/api/packs.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

app = FastAPI(title="Prompt Pack Local API")

# CORS - 允许 Chrome 扩展和 VSCode 访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*", "moz-extension://*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PackCreate(BaseModel):
    metadata: dict
    workflow: list

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "mode": "local"}

@app.get("/api/v2/packs")
async def list_packs():
    """获取所有 Packs"""
    from pack_db import LocalPackDB
    db = LocalPackDB()
    return db.list_all_packs()

@app.get("/api/v2/packs/{pack_id}")
async def get_pack(pack_id: str, version: str = "latest"):
    """获取 Pack"""
    from pack_db import LocalPackDB
    db = LocalPackDB()
    pack = db.get_pack(pack_id, version)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    return pack

@app.post("/api/v2/packs")
async def create_pack(pack_data: PackCreate):
    """创建新 Pack"""
    from pack_db import LocalPackDB
    from pack_schema import PromptPackV2

    pack = PromptPackV2.from_dict(pack_data.dict())
    db = LocalPackDB()
    pack_id = db.create_pack(pack.to_dict())
    return {"id": pack_id, "status": "created"}

@app.post("/api/v2/packs/{pack_id}/vote")
async def vote_pack(pack_id: str, vote: bool):
    """投票审核 (本地模拟)"""
    # 本地模式下，投票功能简化为标记
    from pack_db import LocalPackDB
    db = LocalPackDB()
    db.vote_pack(pack_id, vote)
    return {"status": "success"}

@app.get("/api/v2/search")
async def search_packs(query: str, category: str = None):
    """搜索 Pack"""
    from pack_db import LocalPackDB
    db = LocalPackDB()
    return db.search_packs(query, category)
```

### 3.3 本地启动配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: ./local-backend
    container_name: prompt-pack-api
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./local-backend:/app/app
    environment:
      - DATABASE_PATH=/app/data/packs.db
    restart: unless-stopped
```

```bash
# 启命令
docker-compose up -d

# 停止
docker-compose down

# 查看日志
docker-compose logs -f api
```

## 四、数据库设计 (本地优先)

### 4.1 SQLite Pack Registry

```python
# local-backend/pack_db.py

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

class LocalPackDB:
    """本地 Pack 数据库 (SQLite)"""

    def __init__(self, db_path: str = "data/packs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Packs 主表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS packs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            category TEXT NOT NULL,
            state TEXT NOT NULL,
            author_id TEXT,
            spec_id TEXT,
            delta_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            quality_score REAL DEFAULT 0,
            download_count INTEGER DEFAULT 0
        )
        """)

        # Pack 工作流
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pack_workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pack_id TEXT NOT NULL,
            step_order INTEGER NOT NULL,
            step_type TEXT NOT NULL,
            prompt TEXT,
            config TEXT,
            FOREIGN KEY (pack_id) REFERENCES packs(id)
        )
        """)

        # Pack 示例
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pack_examples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pack_id TEXT NOT NULL,
            name TEXT NOT NULL,
            input_data TEXT NOT NULL,
            output_data TEXT NOT NULL,
            FOREIGN KEY (pack_id) REFERENCES packs(id)
        )
        """)

        # OpenSpec 提案
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS spec_proposals (
            id TEXT PRIMARY KEY,
            spec_id TEXT NOT NULL,
            pack_id TEXT,
            proposal_type TEXT,
            state TEXT,
            votes_for INTEGER DEFAULT 0,
            votes_against INTEGER DEFAULT 0,
            created_at TEXT
        )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON packs(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_state ON packs(state)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_author ON packs(author_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_workflow ON pack_workflows(pack_id)")

        conn.commit()
        conn.close()

    def create_pack(self, pack_data: Dict) -> str:
        """创建 Pack"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        pack_id = pack_data['id']
        metadata = pack_data.get('metadata', {})

        cursor.execute(
            "INSERT INTO packs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                pack_id,
                metadata.get('name', ''),
                metadata.get('version', ''),
                metadata.get('category', ''),
                pack_data.get('state', 'draft'),
                metadata.get('author', ''),
                pack_data.get('spec_id'),
                pack_data.get('delta_id'),
                metadata.get('created_at'),
                metadata.get('updated_at'),
                0.0,
                0
            )
        )

        # 保存工作流
        for i, step in enumerate(pack_data.get('workflow', [])):
            cursor.execute(
                "INSERT INTO pack_workflows (pack_id, step_order, step_type, prompt, config) VALUES (?, ?, ?, ?, ?)",
                (pack_id, i + 1, step.get('action', ''), str(step.get('prompt', '')), str(step.get('config', '{}')))
            )

        # 保存示例
        for example in pack_data.get('examples', []):
            import json
            cursor.execute(
                "INSERT INTO pack_examples (pack_id, name, input_data, output_data) VALUES (?, ?, ?, ?)",
                (pack_id, example.get('name', ''), json.dumps(example.get('input_data', {})), json.dumps(example.get('output_data', {})))
            )

        conn.commit()
        conn.close()
        return pack_id

    def get_pack(self, pack_id: str, version: str = "latest") -> Optional[Dict]:
        """获取 Pack"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM packs WHERE id = ?", (pack_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        # 获取工作流
        cursor.execute("SELECT * FROM pack_workflows WHERE pack_id = ? ORDER BY step_order", (pack_id,))
        workflows = cursor.fetchall()

        # 获取示例
        cursor.execute("SELECT * FROM pack_examples WHERE pack_id = ?", (pack_id,))
        examples = cursor.fetchall()

        import json
        pack_data = {
            "id": row[0],
            "name": row[1],
            "version": row[2],
            "category": row[3],
            "state": row[4],
            "author_id": row[5],
            "spec_id": row[6],
            "delta_id": row[7],
            "created_at": row[8],
            "updated_at": row[9],
            "quality_score": row[10],
            "download_count": row[11],
            "workflow": [{"step_order": w[2], "step_type": w[3], "prompt": w[4], "config": json.loads(w[5])} for w in workflows],
            "examples": [{"name": e[2], "input_data": json.loads(e[3]), "output_data": json.loads(e[4])} for e in examples]
        }

        conn.close()
        return pack_data

    def list_all_packs(self) -> List[Dict]:
        """列出所有 Packs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, version, category, state, quality_score FROM packs")
        rows = cursor.fetchall()

        packs = [{
            "id": r[0],
            "name": r[1],
            "version": r[2],
            "category": r[3],
            "state": r[4],
            "quality_score": r[5]
        } for r in rows]

        conn.close()
        return packs

    def search_packs(self, query: str, category: str = None) -> List[Dict]:
        """搜索 Pack"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if category:
            cursor.execute(
                "SELECT id, name, version, category, state FROM packs WHERE (name LIKE ? OR id LIKE ?) AND category = ?",
                (f'%{query}%', f'%{query}%', category)
            )
        else:
            cursor.execute(
                "SELECT id, name, version, category, state FROM packs WHERE name LIKE ? OR id LIKE ?",
                (f'%{query}%', f'%{query}%')
            )

        rows = cursor.fetchall()
        packs = [{
            "id": r[0],
            "name": r[1],
            "version": r[2],
            "category": r[3],
            "state": r[4]
        } for r in rows]

        conn.close()
        return packs

    def vote_pack(self, pack_id: str, vote: bool):
        """投票 Pack"""
        # 本地模式下简化
        pass
```

### 4.2 数据库迁移

```python
# local-backend/migrations.py

"""数据库版本管理"""

def migrate(db_path: str, target_version: int):
    """
    数据库迁移

    Version 1: 初始表结构
    Version 2: 添加索引
    Version 3: 添加质量指标
    """
    # 迁移逻辑...
    pass
```

## 五、AI 网站检测器

### 5.1 目标网站配置

```javascript
// config/ai-sites.json

{
  "sites": {
    "qianwen": {
      "name": "阿里千问",
      "url_pattern": "https://qianwen.aliyun.com/*",
      "selectors": {
        "input": "[data-testid='chat-input'], textarea",
        "submit": "[data-testid='send-button'], button[type='submit']",
        "output": "[data-testid='chat-response'], .message-content",
        "clear": "[data-testid='clear-button']"
      },
      "wait_strategy": "mutation_observer",
      "timeout_ms": 30000
    },
    "zhipu": {
      "name": "智谱 GLM",
      "url_pattern": "https://chatglm.cn/*",
      "selectors": {
        "input": "textarea[placeholder*='输入']",
        "submit": "button[aria-label*='发送']",
        "output": ".chat-message.user + .chat-message.assistant",
        "clear": "button[title*='清空']"
      },
      "wait_strategy": "interval_check",
      "timeout_ms": 30000
    },
    "kimi": {
      "name": "Kimi 智能助手",
      "url_pattern": "https://kimi.moonshot.cn/*",
      "selectors": {
        "input": ".chat-input-container textarea",
        "submit": ".send-button",
        "output": ".message.outgoing + .message.incoming",
        "clear": ".clear-chat-btn"
      },
      "wait_strategy": "mutation_observer",
      "timeout_ms": 30000
    }
  }
}
```

### 5.2 DOM Observer 实现

```javascript
// content-scripts/dom-observer.js

class DOMObserver {
  constructor(targetSite) {
    this.site = targetSite;
    this.observers = new Map();
    this.siteConfig = this.loadSiteConfig(targetSite);
  }

  loadSiteConfig(site) {
    // 从配置文件加载
    return AI_SITES_CONFIG.sites[site];
  }

  observeOutput(callback) {
    const selector = this.siteConfig.selectors.output;

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        const addedNodes = [...mutation.addedNodes];
        addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE &&
              node.matches(selector) ||
              node.querySelector(selector)) {
            const content = node.querySelector(selector)?.innerText;
            if (content) {
              callback({
                type: 'output_received',
                content: content,
                timestamp: Date.now()
              });
            }
          }
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    this.observers.set('output', observer);
  }

  waitForElement(selector, timeout = 30000) {
    return new Promise((resolve, reject) => {
      const element = document.querySelector(selector);
      if (element) {
        return resolve(element);
      }

      const observer = new MutationObserver(() => {
        const element = document.querySelector(selector);
        if (element) {
          observer.disconnect();
          resolve(element);
        }
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true
      });

      setTimeout(() => {
        observer.disconnect();
        reject(new Error(`Element not found: ${selector}`));
      }, timeout);
    });
  }

  disconnect() {
    this.observers.forEach((observer) => observer.disconnect());
    this.observers.clear();
  }
}
```

## 六、部署架构 (本地优先)

### 6.1 本地开发环境

```bash
# 完整目录结构
prompt-pack-system/
├── local-backend/                 # 本地后端服务
│   ├── api/                       # FastAPI 路由
│   │   └── packs.py
│   ├── models/                    # 数据模型
│   │   └── pack_db.py             # SQLite 操作
│   ├── services/                  # 业务逻辑
│   │   ├── pack_validator.py
│   │   └── spec_engine.py
│   └── main.py                    # FastAPI 入口
├── data/                          # 本地数据目录
│   ├── packs.db                   # SQLite 数据库
│   └── packs/                     # Pack JSON 文件
├── docker-compose.yml             # Docker 启动配置
├── .env                           # 环境变量
└── requirements.txt               # Python 依赖
```

### 6.2 本地启动

```bash
# 方式1: Docker Compose (推荐)
docker-compose up -d

# 方式2: Python 直接运行
cd local-backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 方式3: VSCode 任务
# 按 Ctrl+Shift+P → "Tasks: Run Task" → "启动本地后端"
```

### 6.3 VSCode 集成配置

```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "启动本地后端",
      "type": "shell",
      "command": "docker-compose",
      "args": ["up", "-d"],
      "problemMatcher": []
    },
    {
      "label": "停止本地后端",
      "type": "shell",
      "command": "docker-compose",
      "args": ["down"],
      "problemMatcher": []
    },
    {
      "label": "查看后端日志",
      "type": "shell",
      "command": "docker-compose",
      "args": ["logs", "-f", "api"],
      "problemMatcher": []
    }
  ]
}
```

### 6.4 FastAPI 应用入口

```python
# local-backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# 创建应用
app = FastAPI(
    title="Prompt Pack API",
    description="Prompt Pack v2.0 本地后端服务",
    version="2.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*", "moz-extension://*", "http://localhost:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
data_dir = Path("../data")
data_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(data_dir)), name="static")

# 注册路由
from api import packs
app.include_router(packs.router, prefix="/api/v2", tags=["packs"])

# 健康检查
@app.get("/")
async def root():
    return {
        "name": "Prompt Pack API",
        "version": "2.0.0",
        "mode": "local",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 6.5 本地缓存机制

```python
# local-backend/services/cache.py

import json
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Optional, Dict, Any

class LocalCache:
    """本地缓存服务 (替代 Redis)"""

    CACHE_DIR = Path("../data/cache")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    @lru_cache(maxsize=128)
    def get(key: str) -> Optional[Dict]:
        """获取缓存"""
        cache_file = LocalCache.CACHE_DIR / f"{hashlib.md5(key.encode()).hexdigest()}.json"
        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)
        return None

    @staticmethod
    def set(key: str, value: Any, ttl: int = 3600):
        """设置缓存"""
        cache_file = LocalCache.CACHE_DIR / f"{hashlib.md5(key.encode()).hexdigest()}.json"
        with open(cache_file, 'w') as f:
            json.dump({"value": value, "expires_at": time.time() + ttl}, f)

    @staticmethod
    def delete(key: str):
        """删除缓存"""
        cache_file = LocalCache.CACHE_DIR / f"{hashlib.md5(key.encode()).hexdigest()}.json"
        if cache_file.exists():
            cache_file.unlink()
```

### 6.6 云服务迁移计划 (未来可选)

```
┌─────────────────────────────────────────────────────────────┐
│                 可选云服务迁移路径                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  本地 (当前)               →   云端 (未来可选)               │
│  ┌─────────────┐              ┌─────────────┐              │
│  │  SQLite     │      →       │  PostgreSQL │              │
│  │  (单文件)   │              │  (Supabase) │              │
│  └─────────────┘              └─────────────┘              │
│                                                             │
│  ┌─────────────┐              ┌─────────────┐              │
│  │  lru_cache  │      →       │  Redis      │              │
│  │  (Python)   │              │  (可选)     │              │
│  └─────────────┘              └─────────────┘              │
│                                                             │
│  ┌─────────────┐              ┌─────────────┐              │
│  │  FastAPI    │      →       │  Cloudflare │              │
│  │  (Docker)   │              │  Workers    │              │
│  └─────────────┘              └─────────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**推荐的免费云服务 (未来扩展):**
| 组件 | 本地方案 | 云端方案 | 免费额度 |
|------|---------|---------|---------|
| 数据库 | SQLite | Supabase/Neon | 500MB |
| 缓存 | lru_cache | Redis (可选) | - |
| API | FastAPI | Cloudflare Workers | 10万请求/天 |

## 七、安全设计

### 7.1 Pack 签名验证

```python
# cloud-backend/security/pack_signer.py

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key

class PackSigner:
    def __init__(self, private_key_path: str):
        with open(private_key_path, 'rb') as f:
            self.private_key = load_pem_private_key(f.read(), password=None)

    def sign_pack(self, pack_data: dict) -> str:
        """签名 Pack"""
        pack_json = json.dumps(pack_data, sort_keys=True)
        signature = self.private_key.sign(
            pack_json.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature.hex()

class PackVerifier:
    def __init__(self, public_key_path: str):
        with open(public_key_path, 'rb') as f:
            self.public_key = load_pem_public_key(f.read())

    def verify_pack(self, pack_data: dict, signature: str) -> bool:
        """验证 Pack 签名"""
        try:
            pack_json = json.dumps(pack_data, sort_keys=True)
            self.public_key.verify(
                bytes.fromhex(signature),
                pack_json.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except:
            return False
```

### 7.2 权限控制

```python
# cloud-backend/security/permissions.py

class PermissionManager:
    def __init__(self, db):
        self.db = db

    def can_create_pack(self, user_id: str) -> bool:
        """检查用户是否可以创建 Pack"""
        # 基础权限：所有注册用户
        return self.db.is_user_verified(user_id)

    def can_approve_pack(self, user_id: str) -> bool:
        """检查用户是否可以审核 Pack"""
        # 高级权限：社区贡献者
        return self.db.has_permission(user_id, 'pack_approver')

    def can_delete_pack(self, user_id: str, pack_id: str) -> bool:
        """检查用户是否可以删除 Pack"""
        pack = self.db.get_pack(pack_id)
        # 只有作者或管理员可以删除
        return pack['author_id'] == user_id or \
               self.db.has_permission(user_id, 'admin')
```

## 八、开发计划

### Phase 1: 基础框架 (Week 1-2)
- [ ] Pack v2.0 Schema 实现
- [ ] Chrome 扩展 Manifest V3 配置
- [ ] Content Script 注入机制
- [ ] DOM Observer 基础功能

### Phase 2: Pack 执行引擎 (Week 3-4)
- [ ] Pack Executor 实现
- [ ] 工作流步骤控制器
- [ ] AI 网站适配器
- [ ] 错误处理和重试

### Phase 3: 本地后端 (Week 5-6)

- [x] 了解免费云服务方案
- [ ] FastAPI 本地服务器框架
- [ ] SQLite Pack 数据库封装
- [ ] Docker Compose 配置
- [ ] 本地缓存机制 (lru_cache)
- [ ] API 端点实现

### Phase 4: VSCode 集成 (Week 7)

- [ ] Native Messaging 配置
- [ ] VSCode 扩展开发
- [ ] Pack 编辑器
- [ ] 本地后端启动任务

### Phase 5: 通知协作系统 (Week 8)

- [x] Notification API 实现
- [x] Copilot 交接机制
- [x] 本地优先架构方案

### 可选扩展 (Phase 6+)

- [ ] Supabase 云端集成 (社区 Packs)
- [ ] GitHub Gist 备份同步
- [ ] Cloudflare Workers 部署

## 九、技术选型总结 (本地优先)

| 组件 | 技术选型 | 理由 |
|------|---------|------|
| Chrome 扩展 | Manifest V3, Service Worker | 最新的扩展标准，支持长期维护 |
| 通信协议 | Native Messaging | VSCode ↔ Chrome 官方推荐方案 |
| **后端架构** | **FastAPI (本地) + SQLite** | **零成本、零配置、完全离线** |
| **数据库** | **SQLite (单文件)** | **Python 内置、无需部署** |
| **缓存** | **lru_cache (Python 内置)** | **无需额外服务** |
| 可选云端 | Supabase / Cloudflare Workers | 免费额度，用于社区功能 |
| 认证 | (本地无) / JWT (云端) | 优先本地，云端可选 |
| 版本控制 | SemVer | 清晰的版本语义 |
| 许可证 | MIT | 开源友好 |

## 十、依赖关系 (本地优先)

```text
Prompt Pack System (Local-First Architecture)
├─ Notification System ✓ (已完成)
│   └─ Notification API ✓
│
├─ Pack v2.0 Schema
│   ├─ Pack State Enum
│   ├─ Quality Metrics
│   ├─ Workflow Engine
│   └─ Examples Library
│
├─ Chrome Extension
│   ├─ Manifest V3 Template
│   ├─ Content Script Injector
│   ├─ DOM Observer
│   └─ Pack Executor
│
├─ VSCode Extension
│   ├─ Native Messaging Proxy
│   └─ Pack Editor
│
└─ Local Backend ( NEW - 本地优先)
    ├─ FastAPI Server
    ├─ SQLite Database (packs.db)
    ├─ Local Cache (lru_cache)
    ├─ OpenSpec Engine
    └─ API Endpoints

---

## 十一、成本对比

| 方案 | 月成本 | 启动时间 | 复杂度 | 适用场景 |
|------|--------|---------|--------|---------|
| **本地优先 (推荐)** | **$0** | **<5 分钟** | **低** | MVP、个人开发 |
| 混合模式 | $0-5 | ~30 分钟 | 中 | 个人 + 社区分享 |
| 完全云端 | $5-20+ | >1 小时 | 高 | 团队协作 |

---

## 十二、迁移路径

```text
当前方案              →           未来扩展
─────────────────────────────────────────
本地 SQLite      →    Supabase PostgreSQL
lru_cache        →    Redis (可选)
FastAPI 本地     →    Cloudflare Workers
文件签名          →    JWT 认证
```

---

**文档版本**: v2.0 (Local-First)
**创建日期**: 2026-02-26
**作者**: Claude Code
**更新日期**: 2026-02-26
**状态**: 🟢 本地优先架构设计完成
