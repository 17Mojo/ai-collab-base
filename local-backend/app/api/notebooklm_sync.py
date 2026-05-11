"""
NotebookLM 知识库同步管理
定期同步项目文档到 NotebookLM 知识库
"""

import glob
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# NotebookLM 配置
NOTEBOOK_ID = os.getenv("NOTEBOOKLM_NOTEBOOK_ID", "d2b04caa-257a-4aad-82b0-f58c28e0dad5")

# 知识源目录配置
KNOWLEDGE_DIRS = [
    "knowledge-sources",
    "docs",
    "collaboration/guidelines",
    "collaboration/protocols",
]

# 同步状态文件
SYNC_STATUS_FILE = Path("local-backend/data/notebooklm_sync_status.json")


class SyncRequest(BaseModel):
    """同步请求"""

    notebook_id: str = NOTEBOOK_ID
    directories: list[str] = []
    force: bool = False  # 强制同步所有文件


class SyncStatus(BaseModel):
    """同步状态"""

    last_sync: str
    files_synced: int
    files_pending: int
    total_sources: int
    status: str  # "idle", "syncing", "error"


class SyncResult(BaseModel):
    """同步结果"""

    success: bool
    files_added: list[str] = []
    files_skipped: list[str] = []
    errors: list[str] = []
    total_sources: int
    duration_seconds: float


def get_sync_status() -> SyncStatus:
    """
    获取当前同步状态

    Returns:
        SyncStatus: 同步状态信息
    """
    try:
        if SYNC_STATUS_FILE.exists():
            with open(SYNC_STATUS_FILE, "r") as f:
                status_data = json.load(f)

            return SyncStatus(
                last_sync=status_data.get("last_sync", "Never"),
                files_synced=status_data.get("files_synced", 0),
                files_pending=count_pending_files(),
                total_sources=status_data.get("total_sources", 17),
                status=status_data.get("status", "idle"),
            )
        else:
            return SyncStatus(
                last_sync="Never",
                files_synced=0,
                files_pending=count_pending_files(),
                total_sources=17,
                status="idle",
            )
    except Exception:
        return SyncStatus(
            last_sync="Error", files_synced=0, files_pending=0, total_sources=0, status="error"
        )


def count_pending_files() -> int:
    """
    计算待同步文件数量

    Returns:
        int: 待同步文件数量
    """
    count = 0
    for dir_path in KNOWLEDGE_DIRS:
        if os.path.exists(dir_path):
            md_files = glob.glob(f"{dir_path}/*.md")
            count += len(md_files)
    return count


def get_files_to_sync(force: bool = False) -> list[str]:
    """
    获取需要同步的文件列表

    Args:
        force: 是否强制同步所有文件

    Returns:
        list: 文件路径列表
    """
    files = []

    # 读取已同步文件列表
    synced_files = set()
    if SYNC_STATUS_FILE.exists() and not force:
        with open(SYNC_STATUS_FILE, "r") as f:
            status_data = json.load(f)
            synced_files = set(status_data.get("synced_files", []))

    # 收集所有知识源文件
    for dir_path in KNOWLEDGE_DIRS:
        if os.path.exists(dir_path):
            md_files = glob.glob(f"{dir_path}/*.md")
            for file_path in md_files:
                # 只添加未同步的文件（或强制同步时添加所有）
                if force or file_path not in synced_files:
                    files.append(file_path)

    return files


def save_sync_status(result: SyncResult, synced_files: list[str]):
    """
    保存同步状态

    Args:
        result: 同步结果
        synced_files: 已同步文件列表
    """
    status_data = {
        "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files_synced": len(synced_files),
        "synced_files": synced_files,
        "total_sources": result.total_sources,
        "status": "idle",
        "errors": result.errors,
    }

    # 确保 data 目录存在
    SYNC_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(SYNC_STATUS_FILE, "w") as f:
        json.dump(status_data, f, indent=2)


@router.get("/status", response_model=SyncStatus)
async def get_knowledge_sync_status():
    """
    获取知识库同步状态

    Returns:
        SyncStatus: 同步状态详情
    """
    return get_sync_status()


@router.post("/sync", response_model=SyncResult)
async def sync_knowledge_sources(request: SyncRequest):
    """
    同步知识源到 NotebookLM

    Args:
        request: 同步请求

    Returns:
        SyncResult: 同步结果
    """
    start_time = datetime.now()

    # 获取要同步的文件
    directories = request.directories if request.directories else KNOWLEDGE_DIRS
    files_to_sync = []

    for dir_path in directories:
        if os.path.exists(dir_path):
            md_files = glob.glob(f"{dir_path}/*.md")
            files_to_sync.extend(md_files)

    if request.force:
        # 强制同步时包含所有文件
        pass
    else:
        # 过滤已同步文件
        synced_files = set()
        if SYNC_STATUS_FILE.exists():
            with open(SYNC_STATUS_FILE, "r") as f:
                status_data = json.load(f)
                synced_files = set(status_data.get("synced_files", []))
        files_to_sync = [f for f in files_to_sync if f not in synced_files]

    # Mock 模式：模拟同步结果
    # 真实实现需要调用 nlm add text 或 NotebookLM skill
    files_added = []
    files_skipped = []
    errors = []

    for file_path in files_to_sync:
        # 模拟添加成功
        files_added.append(file_path)

    # 更新同步状态
    all_synced = list(set(files_added + (synced_files if SYNC_STATUS_FILE.exists() else [])))

    duration = (datetime.now() - start_time).total_seconds()

    result = SyncResult(
        success=True,
        files_added=files_added,
        files_skipped=files_skipped,
        errors=errors,
        total_sources=17 + len(files_added),
        duration_seconds=duration,
    )

    save_sync_status(result, all_synced)

    return result


@router.get("/directories")
async def get_knowledge_directories():
    """
    获取知识源目录列表

    Returns:
        dict: 目录信息
    """
    dirs_info = []

    for dir_path in KNOWLEDGE_DIRS:
        if os.path.exists(dir_path):
            md_files = glob.glob(f"{dir_path}/*.md")
            dirs_info.append(
                {
                    "path": dir_path,
                    "exists": True,
                    "file_count": len(md_files),
                    "files": [os.path.basename(f) for f in md_files[:10]],  # 显示前10个文件
                }
            )
        else:
            dirs_info.append({"path": dir_path, "exists": False, "file_count": 0, "files": []})

    return {"directories": dirs_info, "total_files": sum(d["file_count"] for d in dirs_info)}


@router.post("/schedule")
async def set_sync_schedule(interval_hours: int = 24):
    """
    设置自动同步计划

    Args:
        interval_hours: 同步间隔（小时）

    Returns:
        dict: 设置结果
    """
    schedule_file = SYNC_STATUS_FILE.parent / "sync_schedule.json"

    schedule_config = {
        "enabled": True,
        "interval_hours": interval_hours,
        "last_scheduled": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "next_sync": (datetime.now() + timedelta(hours=interval_hours)).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "directories": KNOWLEDGE_DIRS,
    }

    try:
        with open(schedule_file, "w") as f:
            json.dump(schedule_config, f, indent=2)

        return {
            "success": True,
            "interval_hours": interval_hours,
            "next_sync": schedule_config["next_sync"],
            "message": f"已设置每 {interval_hours} 小时自动同步知识库",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "message": "设置同步计划失败"}
