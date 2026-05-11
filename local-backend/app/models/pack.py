"""
Pack 数据库模型
"""

import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class PackModel(Base):
    """Pack 存储模型"""

    __tablename__ = "packs"
    __table_args__ = (
        Index("idx_packs_active_category", "is_active", "category"),
        Index("idx_packs_active_created_at", "is_active", "created_at"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    pack_id = Column(String, unique=True, index=True, nullable=False)
    pack_name = Column(String, nullable=False)
    version = Column(String, default="1.0.0")
    type = Column(String, default="custom")
    description = Column(Text, default="")
    designer = Column(String, default="")
    category = Column(String, nullable=True)
    tags = Column(JSON, default=list)
    language = Column(String, default="zh")

    # 完整 Pack 数据 (JSON)
    pack_data = Column(JSON, nullable=False)

    # 元数据
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 状态
    is_active = Column(Boolean, default=True)
    execution_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime, nullable=True)


class ExecutionHistoryModel(Base):
    """执行历史模型"""

    __tablename__ = "execution_history"
    __table_args__ = (Index("idx_execution_history_pack_started_at", "pack_id", "started_at"),)

    id = Column(String, primary_key=True, default=generate_uuid)
    pack_id = Column(String, index=True, nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, error
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # 输入输出
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # 步骤执行记录
    step_results = Column(JSON, nullable=True)


class QualityMetricModel(Base):
    """质量指标模型"""

    __tablename__ = "quality_metrics"
    __table_args__ = (Index("idx_quality_metrics_pack_metric", "pack_id", "metric_name"),)

    id = Column(String, primary_key=True, default=generate_uuid)
    pack_id = Column(String, index=True, nullable=False)
    execution_id = Column(String, index=True, nullable=False)

    metric_name = Column(String, nullable=False)
    score = Column(Float, default=0.0)
    details = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
