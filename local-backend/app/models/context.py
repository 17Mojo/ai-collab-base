# Context 数据库模型
# local-backend/app/models/context.py

"""
Context 持久化数据模型
"""

import json
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, null
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ContextModel(Base):
    """上下文模型"""

    __tablename__ = "contexts"

    context_id = Column(String(36), primary_key=True, index=True)
    scenario = Column(String(50), not null, index=True)
    name = Column(String(255), not null)
    file_contexts = Column(JSON, default="[]")
    ai_sessions = Column(JSON, default="[]")
    notebooklm_context = Column(JSON, nullable=True)
    user_context = Column(JSON, default="{}")
    metadata = Column(JSON, default="{}")
    parent_id = Column(String(36), ForeignKey("contexts.context_id"), nullable=True)
    children_ids = Column(JSON, default="[]")
    size = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    parent = relationship("ContextModel", remote_side="ContextModel.context_id")
    changes = relationship(
        "ContextChangeLogModel", back_populates="context", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "context_id": self.context_id,
            "scenario": self.scenario,
            "name": self.name,
            "file_contexts": json.loads(self.file_contexts)
            if isinstance(self.file_contexts, str)
            else self.file_contexts,
            "ai_sessions": json.loads(self.ai_sessions)
            if isinstance(self.ai_sessions, str)
            else self.ai_sessions,
            "notebooklm_context": json.loads(self.notebooklm_context)
            if isinstance(self.notebooklm_context, str)
            else self.notebooklm_context
            if self.notebooklm_context
            else None,
            "user_context": json.loads(self.user_context)
            if isinstance(self.user_context, str)
            else self.user_context,
            "metadata": json.loads(self.metadata)
            if isinstance(self.metadata, str)
            else self.metadata,
            "parent_id": self.parent_id,
            "children_ids": json.loads(self.children_ids)
            if isinstance(self.children_ids, str)
            else self.children_ids,
            "size": self.size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict, session=None) -> "ContextModel":
        """从字典创建模型实例"""
        context = cls(
            context_id=data.get("context_id"),
            scenario=data.get("scenario"),
            name=data.get("name"),
            file_contexts=json.dumps(data.get("file_contexts", []))
            if isinstance(data.get("file_contexts"), list)
            else data.get("file_contexts", []),
            ai_sessions=json.dumps(data.get("ai_sessions", []))
            if isinstance(data.get("ai_sessions"), list)
            else data.get("ai_sessions", []),
            notebooklm_context=json.dumps(data.get("notebooklm_context"))
            if isinstance(data.get("notebooklm_context"), dict)
            else data.get("notebooklm_context"),
            user_context=json.dumps(data.get("user_context", {}))
            if isinstance(data.get("user_context"), dict)
            else data.get("user_context", {}),
            metadata=json.dumps(data.get("metadata", {}))
            if isinstance(data.get("metadata"), dict)
            else data.get("metadata", {}),
            parent_id=data.get("parent_id"),
            children_ids=json.dumps(data.get("children_ids", []))
            if isinstance(data.get("children_ids"), list)
            else data.get("children_ids", []),
            size=data.get("size", 0),
        )
        return context


class ContextChangeLogModel(Base):
    """上下文变更日志模型"""

    __tablename__ = "context_changes"

    log_id = Column(String(36), primary_key=True, index=True)
    context_id = Column(String(36), ForeignKey("contexts.context_id"), nullable=False, index=True)
    change_type = Column(String(50), not null, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    details = Column(JSON, default="{}")
    source = Column(String(50), not null, index=True)

    # 关系
    context = relationship("ContextModel", back_populates="changes")

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "log_id": self.log_id,
            "context_id": self.context_id,
            "change_type": self.change_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "details": json.loads(self.details) if isinstance(self.details, str) else self.details,
            "source": self.source,
        }


class ContextTagModel(Base):
    """上下文标签模型"""

    __tablename__ = "context_tags"

    tag_id = Column(Integer, primary_key=True, autoincrement=True)
    context_id = Column(String(36), ForeignKey("contexts.context_id"), nullable=False, index=True)
    tag = Column(String(100), not null, index=True)

    # 复合索引
    __table_args__ = (Index("ix_context_tag", "context_id", "tag"),)


class SessionModel(Base):
    """会话模型"""

    __tablename__ = "sessions"

    session_id = Column(String(36), primary_key=True, index=True)
    ai_type = Column(String(50), not null, index=True)
    started_at = Column(DateTime, nullable=False, index=True)
    messages = Column(JSON, default="[]")
    metadata = Column(JSON, default="{}")
    context_id = Column(String(36), ForeignKey("contexts.context_id"), nullable=True, index=True)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "ai_type": self.ai_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "messages": json.loads(self.messages)
            if isinstance(self.messages, str)
            else self.messages,
            "metadata": json.loads(self.metadata)
            if isinstance(self.metadata, str)
            else self.metadata,
            "context_id": self.context_id,
        }


# ==================== 索引定义 ====================

from sqlalchemy import Index

# Context 模型索引
Index("ix_context_scenario", ContextModel.scenario)
Index("ix_context_created_at", ContextModel.created_at)
Index("ix_context_updated_at", ContextModel.updated_at)

# ContextChangeLog 模型索引
Index("ix_change_context_id", ContextChangeLogModel.context_id)
Index("ix_change_timestamp", ContextChangeLogModel.timestamp)
Index("ix_change_type", ContextChangeLogModel.change_type)

# Session 模型索引
Index("ix_session_ai_type", SessionModel.ai_type)
Index("ix_session_started_at", SessionModel.started_at)


def get_db_session(database_url: Optional[str] = None):
    """
    获取数据库会话

    Args:
        database_url: 数据库连接字符串（可选）

    Returns:
        SQLAlchemy Session
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    url = database_url or "sqlite:///local-backend/data/contexts.db"

    engine = create_engine(
        url, connect_args={"check_same_thread": False} if "sqlite" in url else {}
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    return SessionLocal()


# 导出函数
__all__ = [
    "Base",
    "ContextModel",
    "ContextChangeLogModel",
    "ContextTagModel",
    "SessionModel",
    "get_db_session",
]
