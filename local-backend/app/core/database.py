"""
数据库配置
SQLite + SQLAlchemy 优化版
"""

import os
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

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


def optimize_database():
    """
    优化 SQLite 数据库性能

    执行 SQLite 优化命令
    """
    with engine.begin() as conn:
        # 启用 WAL 模式（提高并发性能）
        conn.execute(text("PRAGMA journal_mode = WAL"))
        # 设置同步模式为 NORMAL（提高性能）
        conn.execute(text("PRAGMA synchronous = NORMAL"))
        # 设置缓存大小（根据需要调整）
        conn.execute(text("PRAGMA cache_size = -64000"))  # 64MB
        # 使临时表保持在内存中
        conn.execute(text("PRAGMA temp_store = MEMORY"))
        # 启用外键约束
        conn.execute(text("PRAGMA foreign_keys = ON"))

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
