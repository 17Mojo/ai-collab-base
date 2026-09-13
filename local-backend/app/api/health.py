"""
健康检查路由
"""

from datetime import datetime

from fastapi import APIRouter

from app.core.cache import get_cache_manager
from app.core.database import get_database_status

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    # 获取集成模式信息
    integration_status = get_integration_status()

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "prompt-pack-api",
        "cache": get_cache_manager().get_stats(),
        "integrations": integration_status,
    }


@router.get("/health/database")
async def database_health():
    """数据库状态检查

    返回数据库 journal_mode、连接池状态、各项 PRAGMA 配置。
    用于运维监控和诊断 WAL 模式是否生效。
    """
    db_status = get_database_status()

    return {
        "status": "healthy" if db_status.get("healthy") else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
    }


@router.get("/ready")
async def readiness_check():
    """就绪检查"""
    # 检查数据库连接等
    try:
        from app.core.database import engine

        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not ready", "error": str(e)}


def get_integration_status():
    """获取所有集成模块的状态"""
    try:
        from ai_collab.config.integration_flags import DEFAULT_INTEGRATION_MODES, get_mode

        status = {}
        for module_name in DEFAULT_INTEGRATION_MODES.keys():
            mode = get_mode(module_name)
            status[module_name] = {
                "mode": mode.value,
                "source": "environment" if _is_env_override(module_name) else "default",
                "fallback_enabled": mode.value in ["mock", "fallback"],
            }

        return status
    except Exception as e:
        return {"error": str(e)}


def _is_env_override(module_name: str) -> bool:
    """检查模块是否被环境变量覆盖"""
    import os

    # 检查全局覆盖
    if os.getenv("AI_INTEGRATION_MODE"):
        return True

    # 检查模块特定覆盖
    per_module_key = f"AI_INTEGRATION_MODE_{module_name.upper()}"
    if os.getenv(per_module_key):
        return True

    return False
