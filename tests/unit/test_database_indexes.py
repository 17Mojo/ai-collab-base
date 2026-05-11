"""
数据库索引验证测试
"""

import os
import sys

from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "local-backend"))

from app.core.database import create_tables, engine, optimize_database


def _index_names(table: str):
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA index_list('{table}')")).fetchall()
    return {row[1] for row in rows}


def test_core_indexes_exist():
    create_tables()
    optimize_database()

    packs_indexes = _index_names("packs")
    execution_indexes = _index_names("execution_history")
    metrics_indexes = _index_names("quality_metrics")

    assert "idx_packs_active_category" in packs_indexes
    assert "idx_packs_active_created_at" in packs_indexes
    assert "idx_execution_history_pack_started_at" in execution_indexes
    assert "idx_quality_metrics_pack_metric" in metrics_indexes
