"""
数据库配置
SQLite + SQLAlchemy 优化版
"""

import logging
import os
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# 数据库路径
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR}/packs.db"

# 创建优化引擎
# 使用 StaticPool 提供 SQLite 的单连接池，提高性能
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # SQLite 需要
        "timeout": 30,  # 超时时间 30 秒
    },
    poolclass=StaticPool,  # 静态连接池（SQLite 最佳实践）
    echo=False,  # 生产环境关闭 SQL 日志
    pool_pre_ping=True,  # 连接前检查连接有效性
    pool_recycle=3600,  # 连接回收时间（1小时）
)

# 会话工厂
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)  # 避免延迟加载问题
)

# 基类
Base = declarative_base()


def get_db() -> Generator:
    """
    获取数据库会话（依赖注入）

    Yields:
        数据库会话对象
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # 成功时提交
    except Exception:
        db.rollback()  # 失败时回滚
        raise
    finally:
        db.close()


def get_db_session():
    """
    获取数据库会话（直接调用）

    Returns:
        数据库会话对象，需要手动管理事务
    """
    return SessionLocal()


def create_tables():
    """
    创建所有表

    如果使用 Alembic 迁移工具，建议使用 Alembic 代替此函数
    """
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    删除所有表（危险操作！）

    仅在测试环境使用
    """
    Base.metadata.drop_all(bind=engine)


def optimize_database() -> dict:
    """
    优化 SQLite 数据库性能

    执行 SQLite 优化命令并验证 WAL 模式是否成功启用。

    Returns:
        dict: 包含优化结果的字典，包括:
            - success (bool): 是否全部成功
            - journal_mode (str): 当前日志模式
            - wal_enabled (bool): WAL 模式是否已启用
            - pragmas (dict): 各项 PRAGMA 的设置结果
    """
    result = {
        "success": False,
        "journal_mode": "unknown",
        "wal_enabled": False,
        "pragmas": {},
    }

    try:
        with engine.begin() as conn:
            # 启用 WAL 模式（提高并发性能）
            conn.execute(text("PRAGMA journal_mode = WAL"))

            # 验证 WAL 模式是否实际生效
            wal_check = conn.execute(text("PRAGMA journal_mode")).fetchone()
            journal_mode = wal_check[0] if wal_check else "unknown"
            result["journal_mode"] = journal_mode
            result["wal_enabled"] = journal_mode.lower() == "wal"

            if result["wal_enabled"]:
                logger.info("SQLite WAL 模式已成功启用")
            else:
                logger.warning(
                    "SQLite WAL 模式启用失败，当前模式: %s。"
                    "这在只读文件系统或某些网络共享上可能发生。",
                    journal_mode,
                )

            # 设置同步模式为 NORMAL（提高性能）
            conn.execute(text("PRAGMA synchronous = NORMAL"))
            sync_result = conn.execute(text("PRAGMA synchronous")).fetchone()
            result["pragmas"]["synchronous"] = sync_result[0] if sync_result else None

            # 设置缓存大小（根据需要调整）
            conn.execute(text("PRAGMA cache_size = -64000"))  # 64MB
            cache_result = conn.execute(text("PRAGMA cache_size")).fetchone()
            result["pragmas"]["cache_size"] = cache_result[0] if cache_result else None

            # 使临时表保持在内存中
            conn.execute(text("PRAGMA temp_store = MEMORY"))
            temp_result = conn.execute(text("PRAGMA temp_store")).fetchone()
            result["pragmas"]["temp_store"] = temp_result[0] if temp_result else None

            # 启用外键约束
            conn.execute(text("PRAGMA foreign_keys = ON"))
            fk_result = conn.execute(text("PRAGMA foreign_keys")).fetchone()
            result["pragmas"]["foreign_keys"] = fk_result[0] if fk_result else None

            # 补齐关键索引（兼容已有数据库）
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_packs_active_category "
                    "ON packs (is_active, category)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_packs_active_created_at "
                    "ON packs (is_active, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_execution_history_pack_started_at "
                    "ON execution_history (pack_id, started_at DESC)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_quality_metrics_pack_metric "
                    "ON quality_metrics (pack_id, metric_name)"
                )
            )

        result["success"] = True
        logger.info(
            "数据库优化完成: journal_mode=%s, synchronous=%s, cache_size=%s",
            result["journal_mode"],
            result["pragmas"].get("synchronous"),
            result["pragmas"].get("cache_size"),
        )

    except Exception as e:
        logger.error("数据库优化失败: %s", e, exc_info=True)
        result["success"] = False

    return result


def get_database_status() -> dict:
    """
    获取当前数据库状态信息

    Returns:
        dict: 数据库状态，包括 journal_mode、连接池状态等
    """
    status = {}

    try:
        with engine.connect() as conn:
            # 日志模式
            jm = conn.execute(text("PRAGMA journal_mode")).fetchone()
            status["journal_mode"] = jm[0] if jm else "unknown"

            # 同步模式
            sync = conn.execute(text("PRAGMA synchronous")).fetchone()
            status["synchronous"] = sync[0] if sync else "unknown"

            # 缓存大小
            cache = conn.execute(text("PRAGMA cache_size")).fetchone()
            status["cache_size"] = cache[0] if cache else "unknown"

            # 外键约束
            fk = conn.execute(text("PRAGMA foreign_keys")).fetchone()
            status["foreign_keys"] = bool(fk[0]) if fk else False

            # temp_store
            ts = conn.execute(text("PRAGMA temp_store")).fetchone()
            status["temp_store"] = ts[0] if ts else "unknown"

        # 连接池状态（StaticPool 没有 size/checkedin 等方法，需安全获取）
        pool = engine.pool
        pool_info = {"class": pool.__class__.__name__}
        for attr, getter in [
            ("size", lambda: pool.size()),
            ("checked_in", lambda: pool.checkedin()),
            ("checked_out", lambda: pool.checkedout()),
            ("overflow", lambda: pool.overflow()),
        ]:
            try:
                pool_info[attr] = getter()
            except AttributeError:
                pool_info[attr] = "N/A (StaticPool)"
        status["pool"] = pool_info

        status["healthy"] = status["journal_mode"].lower() == "wal"

    except Exception as e:
        logger.error("获取数据库状态失败: %s", e, exc_info=True)
        status["error"] = str(e)
        status["healthy"] = False

    return status
