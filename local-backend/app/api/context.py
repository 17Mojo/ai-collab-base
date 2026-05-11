# Context API 端点
# local-backend/app/api/context.py

"""
Context 管理 API 端点

提供上下文的 CRUD 操作和查询接口
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...context.schema import (
    AISessionContext,
    Context,
    NotebookLMContext,
    ScenarioType,
    create_context,
)
from ..models.context import Base, ContextChangeLogModel, ContextModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/context", tags=["context"])


# ==================== 数据库初始化 ====================

DATABASE_URL = "sqlite:///local-backend/data/contexts.db"
DB_PATH = Path("local-backend/data/contexts.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})  # SQLite 需要
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_database():
    """初始化数据库表结构"""
    Base.metadata.create_all(bind=engine)
    logger.info("Context 数据库已初始化")


# ==================== 请求/响应模型 ====================


class FileContextRequest(BaseModel):
    """文件上下文请求"""

    path: str
    content: Optional[str] = None
    language: str = "text"
    size: int = 0
    modified_at: Optional[str] = None
    hash: Optional[str] = None


class AISessionRequest(BaseModel):
    """AI 会话请求"""

    session_id: str
    ai_type: str
    started_at: str
    messages: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class NotebookLMRequest(BaseModel):
    """NotebookLM 请求"""

    notebook_id: str
    notebook_name: str
    query_results: List[Dict[str, Any]] = []
    sources: List[str] = []
    last_updated: Optional[str] = None


class CreateContextRequest(BaseModel):
    """创建上下文请求"""

    scenario: ScenarioType
    name: str
    files: List[str] = []
    user_context: Dict[str, Any] = {}
    tags: List[str] = []


class UpdateContextRequest(BaseModel):
    """更新上下文请求"""

    name: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class ScenarioDetectionRequest(BaseModel):
    """场景检测请求"""

    active_files: List[str] = []
    include_content: bool = False


# ==================== 响应模型 ====================


class ContextResponse(BaseModel):
    """上下文响应"""

    context_id: str
    scenario: str
    name: str
    file_contexts: List[Dict[str, Any]] = []
    ai_sessions: List[Dict[str, Any]] = []
    notebooklm_context: Optional[Dict[str, Any]] = None
    user_context: Dict[str, Any] = {}
    metadata: Dict[str, Any]
    parent_id: Optional[str] = None
    children_ids: List[str] = []
    size: int


class ScenarioDetectionResponse(BaseModel):
    """场景检测结果"""

    scenario: str
    confidence: float
    is_confident: bool
    evidence: List[Dict[str, Any]] = []
    explanation: str


# ==================== 数据库操作 ====================


def get_db():
    """获取数据库会话（依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _model_to_context(model: ContextModel) -> Context:
    """将数据库模型转换为 Context 对象"""
    from ...context.schema import ContextMetadata, FileContext

    file_contexts = [
        FileContext(
            path=fc["path"],
            content=fc.get("content"),
            language=fc.get("language", "text"),
            size=fc.get("size", 0),
            modified_at=datetime.fromisoformat(fc["modified_at"])
            if fc.get("modified_at")
            else None,
            hash=fc.get("hash"),
        )
        for fc in (
            json.loads(model.file_contexts)
            if isinstance(model.file_contexts, str)
            else model.file_contexts or []
        )
    ]

    ai_sessions = [
        AISessionContext(
            session_id=ais["session_id"],
            ai_type=ais["ai_type"],
            started_at=datetime.fromisoformat(ais["started_at"]) if ais.get("started_at") else None,
            messages=ais.get("messages", []),
            metadata=ais.get("metadata", {}),
        )
        for ais in (
            json.loads(model.ai_sessions)
            if isinstance(model.ai_sessions, str)
            else model.ai_sessions or []
        )
    ]

    notebooklm_context = None
    if model.notebooklm_context:
        nlm_data = (
            json.loads(model.notebooklm_context)
            if isinstance(model.notebooklm_context, str)
            else model.notebooklm_context
        )
        notebooklm_context = NotebookLMContext(
            notebook_id=nlm_data.get("notebook_id"),
            notebook_name=nlm_data.get("notebook_name"),
            query_results=nlm_data.get("query_results", []),
            sources=nlm_data.get("sources", []),
            last_updated=datetime.fromisoformat(nlm_data["last_updated"])
            if nlm_data.get("last_updated")
            else None,
        )

    user_context = (
        json.loads(model.user_context)
        if isinstance(model.user_context, str)
        else model.user_context or {}
    )
    metadata_data = (
        json.loads(model.metadata) if isinstance(model.metadata, str) else model.metadata or {}
    )

    metadata = ContextMetadata(
        tags=metadata_data.get("tags", []),
        custom_attributes=metadata_data.get("custom_attributes", {}),
    )

    context = Context(
        context_id=model.context_id,
        scenario=ScenarioType(model.scenario),
        name=model.name,
        file_contexts=file_contexts,
        ai_sessions=ai_sessions,
        notebooklm_context=notebooklm_context,
        user_context=user_context,
        metadata=metadata,
    )

    context.parent_id = model.parent_id
    context.children_ids = (
        json.loads(model.children_ids)
        if isinstance(model.children_ids, str)
        else model.children_ids or []
    )
    context._size = model.size

    return context


# ==================== 端点 ====================


@router.post("/create", response_model=ContextResponse)
async def create_context_endpoint(request: CreateContextRequest):
    """
    创建新上下文

    Args:
        request: 创建上下文请求

    Returns:
        创建的上下文
    """
    try:
        db = SessionLocal()

        context = create_context(
            scenario=request.scenario,
            name=request.name,
            files=request.files,
        )

        context.user_context = request.user_context
        context.metadata.tags = request.tags

        # 创建数据库记录
        context_model = ContextModel.from_dict(context.to_dict())
        db.add(context_model)

        # 记录变更日志
        change_log = ContextChangeLogModel(
            log_id=context.context_id,
            context_id=context.context_id,
            change_type="created",
            details={"source": "api", "user_context_keys": list(request.user_context.keys())},
            source="api",
        )
        db.add(change_log)

        db.commit()
        db.refresh(context_model)

        result = ContextResponse(**_model_to_context(context_model).to_dict())
        db.close()

        return result

    except Exception as e:
        logger.error(f"Failed to create context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{context_id}", response_model=ContextResponse)
async def get_context(context_id: str):
    """
    获取上下文

    Args:
        context_id: 上下文 ID

    Returns:
        上下文数据
    """
    db = SessionLocal()
    try:
        context_model = db.query(ContextModel).filter(ContextModel.context_id == context_id).first()

        if not context_model:
            raise HTTPException(status_code=404, detail="Context not found")

        result = ContextResponse(**_model_to_context(context_model).to_dict())
        return result
    finally:
        db.close()


@router.get("/list", response_model=List[ContextResponse])
async def list_contexts(
    scenario: Optional[ScenarioType] = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    列出所有上下文

    Args:
        scenario: 筛选场景类型
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        上下文列表
    """
    db = SessionLocal()
    try:
        query = db.query(ContextModel)

        if scenario:
            query = query.filter(ContextModel.scenario == scenario.value)

        query = query.order_by(ContextModel.created_at.desc())
        query = query.offset(offset).limit(limit)

        context_models = query.all()

        return [ContextResponse(**_model_to_context(cm).to_dict()) for cm in context_models]
    finally:
        db.close()


@router.put("/{context_id}", response_model=ContextResponse)
async def update_context(context_id: str, request: UpdateContextRequest):
    """
    更新上下文

    Args:
        context_id: 上下文 ID
        request: 更新请求

    Returns:
        更新后的上下文
    """
    db = SessionLocal()
    try:
        context_model = db.query(ContextModel).filter(ContextModel.context_id == context_id).first()

        if not context_model:
            raise HTTPException(status_code=404, detail="Context not found")

        # 更新字段
        if request.name:
            context_model.name = request.name
        if request.user_context is not None:
            context_model.user_context = json.dumps(request.user_context)
        if request.tags is not None:
            metadata = (
                json.loads(context_model.metadata)
                if isinstance(context_model.metadata, str)
                else context_model.metadata
            )
            metadata["tags"] = request.tags
            context_model.metadata = json.dumps(metadata)

        context_model.updated_at = datetime.utcnow()

        # 记录变更日志
        change_log = ContextChangeLogModel(
            log_id=f"{context_id}_{int(datetime.utcnow().timestamp())}",
            context_id=context_id,
            change_type="updated",
            details={
                "updated_fields": list(
                    filter(
                        None,
                        [
                            "name" if request.name else None,
                            "user_context" if request.user_context is not None else None,
                            "tags" if request.tags is not None else None,
                        ],
                    )
                )
            },
            source="api",
        )
        db.add(change_log)

        db.commit()
        db.refresh(context_model)

        result = ContextResponse(**_model_to_context(context_model).to_dict())
        return result
    finally:
        db.close()


@router.post("/{context_id}/files", response_model=ContextResponse)
async def add_file(context_id: str, request: FileContextRequest):
    """
    添加文件到上下文

    Args:
        context_id: 上下文 ID
        request: 文件上下文请求

    Returns:
        更新后的上下文
    """
    db = SessionLocal()
    try:
        context_model = db.query(ContextModel).filter(ContextModel.context_id == context_id).first()

        if not context_model:
            raise HTTPException(status_code=404, detail="Context not found")

        file_contexts = (
            json.loads(context_model.file_contexts)
            if isinstance(context_model.file_contexts, str)
            else context_model.file_contexts
        )
        file_contexts = file_contexts or []

        new_file = {
            "path": request.path,
            "content": request.content,
            "language": request.language,
            "size": request.size,
            "modified_at": request.modified_at,
            "hash": request.hash,
        }

        file_contexts.append(new_file)
        context_model.file_contexts = json.dumps(file_contexts)
        context_model.size = len(json.dumps(file_contexts))
        context_model.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(context_model)

        result = ContextResponse(**_model_to_context(context_model).to_dict())
        return result
    finally:
        db.close()


@router.post("/{context_id}/sessions", response_model=ContextResponse)
async def add_ai_session(context_id: str, request: AISessionRequest):
    """
    添加 AI 会话到上下文

    Args:
        context_id: 上下文 ID
        request: AI 会话请求

    Returns:
        更新后的上下文
    """
    db = SessionLocal()
    try:
        context_model = db.query(ContextModel).filter(ContextModel.context_id == context_id).first()

        if not context_model:
            raise HTTPException(status_code=404, detail="Context not found")

        ai_sessions = (
            json.loads(context_model.ai_sessions)
            if isinstance(context_model.ai_sessions, str)
            else context_model.ai_sessions
        )
        ai_sessions = ai_sessions or []

        new_session = {
            "session_id": request.session_id,
            "ai_type": request.ai_type,
            "started_at": request.started_at,
            "messages": request.messages,
            "metadata": request.metadata,
        }

        ai_sessions.append(new_session)
        context_model.ai_sessions = json.dumps(ai_sessions)
        context_model.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(context_model)

        result = ContextResponse(**_model_to_context(context_model).to_dict())
        return result
    finally:
        db.close()


@router.put("/{context_id}/notebooklm", response_model=ContextResponse)
async def update_notebooklm(context_id: str, request: NotebookLMRequest):
    """
    更新 NotebookLM 上下文

    Args:
        context_id: 上下文 ID
        request: NotebookLM 请求

    Returns:
        更新后的上下文
    """
    db = SessionLocal()
    try:
        context_model = db.query(ContextModel).filter(ContextModel.context_id == context_id).first()

        if not context_model:
            raise HTTPException(status_code=404, detail="Context not found")

        notebooklm_data = {
            "notebook_id": request.notebook_id,
            "notebook_name": request.notebook_name,
            "query_results": request.query_results,
            "sources": request.sources,
            "last_updated": request.last_updated,
        }

        context_model.notebooklm_context = json.dumps(notebooklm_data)
        context_model.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(context_model)

        result = ContextResponse(**_model_to_context(context_model).to_dict())
        return result
    finally:
        db.close()


@router.delete("/{context_id}")
async def delete_context(context_id: str):
    """
    删除上下文

    Args:
        context_id: 上下文 ID

    Returns:
        删除结果
    """
    db = SessionLocal()
    try:
        context_model = db.query(ContextModel).filter(ContextModel.context_id == context_id).first()

        if not context_model:
            raise HTTPException(status_code=404, detail="Context not found")

        db.delete(context_model)
        db.commit()

        return {"message": "Context deleted successfully"}
    finally:
        db.close()


@router.get("/{context_id}/summary")
async def get_context_summary(context_id: str):
    """
    获取上下文摘要

    Args:
        context_id: 上下文 ID

    Returns:
        上下文摘要
    """
    db = SessionLocal()
    try:
        context_model = db.query(ContextModel).filter(ContextModel.context_id == context_id).first()

        if not context_model:
            raise HTTPException(status_code=404, detail="Context not found")

        context = _model_to_context(context_model)
        summary = context.get_summary()

        return summary
    finally:
        db.close()


@router.post("/detect/scenario", response_model=ScenarioDetectionResponse)
async def detect_scenario(request: ScenarioDetectionRequest):
    """
    检测当前场景

    Args:
        request: 场景检测请求

    Returns:
        场景检测结果
    """
    from ...context.scenario import ScenarioDetector

    detector = ScenarioDetector()

    result = detector.detect(
        active_files=request.active_files or [],
        include_content=request.include_content,
    )

    is_confident = result.score >= 0.75

    return ScenarioDetectionResponse(
        scenario=result.scenario.value,
        confidence=result.score,
        is_confident=is_confident,
        evidence=[e.__dict__ for e in result.evidence],
        explanation=f"Detected {result.scenario.value} scenario with {result.score:.1%} confidence",
    )


@router.get("/scenarios/list")
async def list_scenarios():
    """
    列出所有场景类型

    Returns:
        场景类型列表
    """
    scenarios = [
        {
            "value": scenario.value,
            "name": scenario.value.replace("_", " ").title(),
            "weight": ScenarioDetector.SCENARIO_RULES.get(scenario, {}).get("weight", 0.0),
        }
        for scenario in ScenarioType
    ]

    return scenarios


# ==================== 健康检查 ====================


@router.get("/health")
async def health_check():
    """健康检查"""
    db = SessionLocal()
    try:
        from sqlalchemy import text

        result = db.execute(text("SELECT COUNT(*) FROM contexts")).scalar()
        contexts_count = result
        status = "healthy"
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        contexts_count = 0
        status = "unhealthy"
    finally:
        db.close()

    return {
        "status": status,
        "contexts_stored": contexts_count,
        "storage_type": "sqlite",
        "database_path": str(DB_PATH),
        "timestamp": datetime.now().isoformat(),
    }


# 自动初始化数据库
init_database()
