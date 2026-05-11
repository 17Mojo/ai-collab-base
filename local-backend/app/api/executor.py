"""
Pack Execution API 路由
"""

import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    ArtifactSchema,
    ExecutePackRequest,
    ExecutePackResponse,
    ExecutionStatusResponse,
    GenerateStudioRequest,
    GenerateStudioResponse,
    StepResultSchema,
)
from app.core.database import get_db
from app.models.pack import ExecutionHistoryModel, PackModel

router = APIRouter()

EXECUTION_TIMEOUT = int(os.getenv("EXECUTION_TIMEOUT", "60000"))  # 60 seconds


# ==================== Pack Execution ====================


@router.post("/execute-pack")
async def execute_pack(request: Dict[str, Any], db: Session = Depends(get_db)):
    """
    执行指定 Pack

    Args:
        pack_id: Pack ID
        platform: 目标平台 (claude, chatgpt, gemini, etc.)
        user_input: 用户输入内容
        enable_knowledge: 是否启用知识增强 (NotebookLM)
        context: 执行上下文数据

    Returns:
        execution_id: 执行 ID
        status: 执行状态 (pending, running, completed, failed)
        steps: 步骤执行结果列表
        duration_ms: 执行时长
    """
    pack_id = request.get("pack_id")
    platform = request.get("platform", "generic")
    user_input = request.get("user_input", "")
    enable_knowledge = request.get("enable_knowledge", False)
    context = request.get("context", {})

    if not pack_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pack_id is required",
        )

    # 获取 Pack
    pack = (
        db.query(PackModel)
        .filter(PackModel.pack_id == pack_id, PackModel.is_active.is_(True))
        .first()
    )

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pack {pack_id} not found",
        )

    pack_data = pack.pack_data or {}

    # 使用真实 PackExecutor 执行
    start_time = time.perf_counter()
    from app.core.pack_executor import execute_pack

    input_data = {"user_input": user_input, "platform": platform, "context": context}
    execution_result = execute_pack(pack_data, input_data)

    # 创建执行记录
    db_execution = ExecutionHistoryModel(
        pack_id=pack_id,
        status="running",
        input_data=input_data,
    )
    db.add(db_execution)
    db.commit()
    db.refresh(db_execution)
    execution_id = str(db_execution.id)

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    # 更新执行记录
    db_execution.status = "completed"
    db_execution.output_data = {
        "steps": execution_result["steps"],
        "iterations": execution_result["iterations"],
        "extracted_data": execution_result["extracted_data"],
        "duration_ms": duration_ms
    }
    db_execution.completed_at = time.time()
    db.commit()

    # 更新 Pack 执行计数
    pack.execution_count += 1
    db.commit()

    return {
        "execution_id": execution_id,
        "pack_id": pack_id,
        "status": "completed",
        "steps": execution_result["steps"],
        "output": None,
        "duration_ms": duration_ms,
        "knowledge_sources": [] if not enable_knowledge else ["notebooklm"],
        "platform": platform,
        "branch_logic_enabled": execution_result["branch_logic_enabled"],
        "iterations": execution_result["iterations"],
    }


# ==================== Studio Generation ====================


class GenerateStudioRequest:
    """Studio 产物生成请求"""

    content: str
    artifacts: List[str]  # ['audio', 'video', 'slides']
    focus: str
    notebook_id: Optional[str] = None


class GenerateStudioResponse:
    """Studio 产物生成响应"""

    artifact_id: str
    status: str
    artifacts: List[Dict[str, Any]]
    download_urls: Dict[str, str]


@router.post("/generate-studio")
async def generate_studio(request: Dict[str, Any], db: Session = Depends(get_db)):
    """
    生成 Studio 产物 (Audio, Video, Slides)

    Args:
        content: 生成内容
        artifacts: 产物类型列表 ['audio', 'video', 'slides']
        focus: 主题焦点
        notebook_id: NotebookLM notebook ID (可选)

    Returns:
        artifact_id: 产物 ID
        status: 生成状态
        download_urls: 各产物下载链接
    """
    content = request.get("content", "")
    artifacts = request.get("artifacts", [])
    focus = request.get("focus", "")
    notebook_id = request.get("notebook_id")

    if not artifacts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="artifacts list is required (audio, video, slides)",
        )

    artifact_id = f"studio-{int(time.time() * 1000)}"
    valid_artifacts = ["audio", "video", "slides"]

    # 验证产物类型
    invalid = [a for a in artifacts if a not in valid_artifacts]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid artifact types: {invalid}",
        )

    # 模拟产物生成 (实际生成需要调用 NotebookLM API)
    generated_artifacts: List[Dict[str, Any]] = []
    download_urls: Dict[str, str] = {}

    for artifact_type in artifacts:
        generated_artifacts.append({
            "type": artifact_type,
            "status": "generated",
            "size_mb": 10 if artifact_type == "audio" else (25 if artifact_type == "video" else 5),
        })
        download_urls[artifact_type] = f"/api/studio/download/{artifact_id}/{artifact_type}"

    return {
        "artifact_id": artifact_id,
        "status": "completed",
        "artifacts": generated_artifacts,
        "download_urls": download_urls,
        "focus": focus,
        "content_length": len(content),
        "notebook_id": notebook_id,
    }


@router.get("/studio/download/{artifact_id}/{artifact_type}")
async def download_studio_artifact(artifact_id: str, artifact_type: str):
    """
    下载 Studio 产物

    Args:
        artifact_id: 产物 ID
        artifact_type: 产物类型 (audio, video, slides)
    """
    # 实际实现需要连接文件存储
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Download endpoint not implemented - requires file storage integration",
    )


# ==================== Execution Status ====================


@router.get("/execution/{execution_id}")
async def get_execution_status(execution_id: str, db: Session = Depends(get_db)):
    """
    获取执行状态

    Args:
        execution_id: 执行 ID

    Returns:
        execution: 执行详情
    """
    execution = db.query(ExecutionHistoryModel).filter(
        ExecutionHistoryModel.id == int(execution_id)
    ).first()

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found",
        )

    return {
        "execution_id": str(execution.id),
        "pack_id": execution.pack_id,
        "status": execution.status,
        "input_data": execution.input_data,
        "output_data": execution.output_data,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
    }
