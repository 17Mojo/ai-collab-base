"""
数据库索引验证测试
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent / "local-backend"
sys.path.insert(0, str(BACKEND_ROOT))

# Skip when backend database doesn't exist (CI without data dir)
DATABASE_PATH = BACKEND_ROOT / "data" / "client_tokens.db"
if not DATABASE_PATH.exists():
    pytest.skip(f"backend database not found at {DATABASE_PATH}", allow_module_level=True)

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
