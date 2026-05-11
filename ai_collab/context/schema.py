# 上下文数据模型定义
# src/ai_collab/context/schema.py

"""
上下文管理的数据模型定义

支持 Claude Code + 多 AI 平台的上下文管理
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ScenarioType(Enum):
    """场景类型枚举"""

    CODING = "coding"  # 编码场景
    RESEARCH = "research"  # 研究场景
    WRITING = "writing"  # 写作场景
    DEBUGGING = "debugging"  # 调试场景
    DESIGN = "design"  # 设计场景
    PROJECT_PLANNING = "project_planning"  # 项目规划场景
    DOCUMENTATION = "documentation"  # 文档编写场景
    UNKNOWN = "unknown"  # 未知场景


class ContextSource(Enum):
    """上下文来源枚举"""

    FILE_SYSTEM = "file_system"  # 文件系统
    AI_SESSION = "ai_session"  # AI 会话
    NOTEBOOKLM = "notebooklm"  # NotebookLM
    USER_INPUT = "user_input"  # 用户输入
    EXTERNAL_API = "external_api"  # 外部 API
    PACK_RESULT = "pack_result"  # Pack 执行结果


@dataclass
class FileContext:
    """文件上下文"""

    path: str  # 文件路径
    content: Optional[str] = None  # 文件内容 (可选，节省内存)
    language: str = "text"  # 文件语言/类型
    size: int = 0  # 文件大小 (bytes)
    modified_at: Optional[datetime] = None  # 最后修改时间
    hash: Optional[str] = None  # 内容哈希 (用于变更检测)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "content": self.content,
            "language": self.language,
            "size": self.size,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "hash": self.hash,
        }


@dataclass
class AISessionContext:
    """AI 会话上下文"""

    session_id: str  # 会话 ID
    ai_type: str  # AI 类型 (claude/codex/codearts)
    started_at: datetime  # 开始时间
    messages: List[Dict[str, Any]] = field(default_factory=list)  # 消息历史
    metadata: Dict[str, Any] = field(default_factory=dict)  # 会话元数据

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "ai_type": self.ai_type,
            "started_at": self.started_at.isoformat(),
            "messages": self.messages,
            "metadata": self.metadata,
        }


@dataclass
class NotebookLMContext:
    """NotebookLM 上下文"""

    notebook_id: str  # Notebook ID
    notebook_name: str  # Notebook 名称
    query_results: List[Dict[str, Any]] = field(default_factory=list)  # 查询结果
    sources: List[str] = field(default_factory=list)  # 引用来源
    last_updated: Optional[datetime] = None  # 最后更新时间

    def to_dict(self) -> Dict[str, Any]:
        return {
            "notebook_id": self.notebook_id,
            "notebook_name": self.notebook_name,
            "query_results": self.query_results,
            "sources": self.sources,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


@dataclass
class ContextMetadata:
    """上下文元数据"""

    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)  # 更新时间
    tags: List[str] = field(default_factory=list)  # 标签
    owner: str = "system"  # 所有者
    version: int = 1  # 版本号

    def touch(self):
        """更新时间戳"""
        self.updated_at = datetime.now()


@dataclass
class Context:
    """
    上下文数据模型

    表示特定场景下 AI 助手所需的完整上下文信息
    """

    # 基本信息
    context_id: str  # 上下文唯一标识
    scenario: ScenarioType  # 场景类型
    name: str  # 上下文名称

    # 上下文内容
    file_contexts: List[FileContext] = field(default_factory=list)  # 文件上下文
    ai_sessions: List[AISessionContext] = field(default_factory=list)  # AI 会话
    notebooklm_context: Optional[NotebookLMContext] = None  # NotebookLM 上下文
    user_context: Dict[str, Any] = field(default_factory=dict)  # 用户上下文

    # 元数据
    metadata: ContextMetadata = field(default_factory=ContextMetadata)  # 元数据
    parent_id: Optional[str] = None  # 父上下文 ID (用于上下文链)
    children_ids: List[str] = field(default_factory=list)  # 子上下文 ID

    # 统计信息
    size: int = 0  # 上下文大小 (bytes)

    def __post_init__(self):
        """初始化后处理"""
        self._recalculate_size()

    def add_file(self, file_context: FileContext):
        """添加文件上下文"""
        self.file_contexts.append(file_context)
        self.metadata.touch()
        self._recalculate_size()

    def add_ai_session(self, session: AISessionContext):
        """添加 AI 会话"""
        self.ai_sessions.append(session)
        self.metadata.touch()

    def update_notebooklm(self, notebooklm: NotebookLMContext):
        """更新 NotebookLM 上下文"""
        self.notebooklm_context = notebooklm
        self.metadata.touch()

    def get_file_by_path(self, path: str) -> Optional[FileContext]:
        """根据路径获取文件"""
        return next((f for f in self.file_contexts if f.path == path), None)

    def get_latest_session(self, ai_type: Optional[str] = None) -> Optional[AISessionContext]:
        """获取最新的 AI 会话"""
        filtered = self.ai_sessions
        if ai_type:
            filtered = [s for s in self.ai_sessions if s.ai_type == ai_type]
        if filtered:
            return max(filtered, key=lambda s: s.started_at)
        return None

    def get_summary(self) -> Dict[str, Any]:
        """获取上下文摘要"""
        return {
            "context_id": self.context_id,
            "scenario": self.scenario.value,
            "name": self.name,
            "file_count": len(self.file_contexts),
            "session_count": len(self.ai_sessions),
            "has_notebooklm": self.notebooklm_context is not None,
            "size": self.size,
            "updated_at": self.metadata.updated_at.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "context_id": self.context_id,
            "scenario": self.scenario.value,
            "name": self.name,
            "file_contexts": [f.to_dict() for f in self.file_contexts],
            "ai_sessions": [s.to_dict() for s in self.ai_sessions],
            "notebooklm_context": self.notebooklm_context.to_dict()
            if self.notebooklm_context
            else None,
            "user_context": self.user_context,
            "metadata": {
                "created_at": self.metadata.created_at.isoformat(),
                "updated_at": self.metadata.updated_at.isoformat(),
                "tags": self.metadata.tags,
                "owner": self.metadata.owner,
                "version": self.metadata.version,
            },
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Context":
        """从字典反序列化"""
        file_contexts = [FileContext(**f) for f in data.get("file_contexts", [])]
        ai_sessions = [AISessionContext(**s) for s in data.get("ai_sessions", [])]

        notebooklm_data = data.get("notebooklm_context")
        notebooklm_context = NotebookLMContext(**notebooklm_data) if notebooklm_data else None

        metadata = ContextMetadata(**data["metadata"])

        return cls(
            context_id=data["context_id"],
            scenario=ScenarioType(data["scenario"]),
            name=data["name"],
            file_contexts=file_contexts,
            ai_sessions=ai_sessions,
            notebooklm_context=notebooklm_context,
            user_context=data.get("user_context", {}),
            metadata=metadata,
            parent_id=data.get("parent_id"),
            children_ids=data.get("children_ids", []),
            size=data.get("size", 0),
        )

    def _recalculate_size(self):
        """重新计算上下文大小"""
        self.size = sum(f.size for f in self.file_contexts)
        # 估算其他部分的大小
        self.size += len(json.dumps(self.user_context).encode())
        if self.notebooklm_context:
            self.size += len(json.dumps(self.notebooklm_context.to_dict()).encode())


@dataclass
class ContextChangeLog:
    """上下文变更日志"""

    log_id: str  # 日志 ID
    context_id: str  # 上下文 ID
    change_type: str  # 变更类型 (create/update/delete/file_add/file_remove/session_add)
    timestamp: datetime  # 时间戳
    details: Dict[str, Any]  # 变更详情
    source: ContextSource  # 变更来源

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_id": self.log_id,
            "context_id": self.context_id,
            "change_type": self.change_type,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "source": self.source.value,
        }


# ==================== 工厂函数 ====================


def create_context(
    scenario: ScenarioType,
    name: str,
    files: Optional[List[str]] = None,
    context_id: Optional[str] = None,
) -> Context:
    """
    创建新上下文

    Args:
        scenario: 场景类型
        name: 上下文名称
        files: 初始文件列表
        context_id: 上下文 ID (可选，自动生成)

    Returns:
        新的 Context 实例
    """
    import uuid

    context = Context(
        context_id=context_id or str(uuid.uuid4()),
        scenario=scenario,
        name=name,
    )

    if files:
        for file_path in files:
            context.add_file(
                FileContext(
                    path=file_path,
                    language=_detect_language(file_path),
                    size=0,  # 需要外部填充
                )
            )

    return context


def _detect_language(path: str) -> str:
    """根据文件扩展名检测语言"""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".txt": "text",
        ".html": "html",
        ".css": "css",
    }

    import os

    _, ext = os.path.splitext(path)
    return ext_map.get(ext.lower(), "text")


# ==================== 示例 ====================

if __name__ == "__main__":
    print("=== 上下文数据模型示例 ===\n")

    # 创建编码场景上下文
    coding_context = create_context(
        scenario=ScenarioType.CODING,
        name="AI 协作系统编码场景",
        files=[
            "src/ai_collab/context/schema.py",
            "src/ai_collab/cli.py",
        ],
    )

    print(f"上下文 ID: {coding_context.context_id}")
    print(f"场景类型: {coding_context.scenario.value}")
    print(f"文件数量: {len(coding_context.file_contexts)}")
    print(f"摘要: {coding_context.get_summary()}")

    # 添加 AI 会话
    session = AISessionContext(
        session_id="session-123",
        ai_type="claude",
        started_at=datetime.now(),
        messages=[
            {"role": "user", "content": "帮我创建上下文管理模块"},
            {"role": "assistant", "content": "好的，我来设计数据模型"},
        ],
    )
    coding_context.add_ai_session(session)

    print(f"\n会话数量: {len(coding_context.ai_sessions)}")
    print(f"最新会话: {coding_context.get_latest_session().session_id}")

    # 序列化
    print(f"\n序列化大小: {len(json.dumps(coding_context.to_dict()).encode())} bytes")

    print("\n=== 完成 ===")
