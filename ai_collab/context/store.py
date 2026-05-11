"""
Context 持久化存储

使用 SQLite 实现 Context 的 CRUD 操作，支持数据持久化
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = "data/contexts.db"


class ContextStore:
    """Context 持久化存储"""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contexts (
                context_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                scenario TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}',
                file_contexts_json TEXT DEFAULT '[]',
                notebooklm_json TEXT DEFAULT 'null',
                tags_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS context_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                context_id TEXT NOT NULL,
                path TEXT NOT NULL,
                language TEXT DEFAULT '',
                size INTEGER DEFAULT 0,
                FOREIGN KEY (context_id) REFERENCES contexts(context_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_context_files_context_id
            ON context_files(context_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_contexts_scenario
            ON contexts(scenario)
        """)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def save(self, context_data: Dict[str, Any]) -> str:
        """
        保存 Context

        Args:
            context_data: Context 数据字典

        Returns:
            context_id
        """
        import uuid

        context_id = context_data.get("context_id") or str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn = self._get_conn()

        # 检查是否已存在
        existing = conn.execute(
            "SELECT context_id FROM contexts WHERE context_id = ?",
            (context_id,),
        ).fetchone()

        if existing:
            # 更新
            conn.execute(
                """UPDATE contexts SET
                    name = ?, scenario = ?, metadata_json = ?,
                    file_contexts_json = ?, notebooklm_json = ?,
                    tags_json = ?, updated_at = ?
                WHERE context_id = ?""",
                (
                    context_data.get("name", ""),
                    context_data.get("scenario", "unknown"),
                    json.dumps(context_data.get("metadata", {}), ensure_ascii=False),
                    json.dumps(context_data.get("file_contexts", []), ensure_ascii=False),
                    json.dumps(context_data.get("notebooklm"), ensure_ascii=False),
                    json.dumps(context_data.get("tags", []), ensure_ascii=False),
                    now,
                    context_id,
                ),
            )
        else:
            # 插入
            conn.execute(
                """INSERT INTO contexts
                    (context_id, name, scenario, metadata_json, file_contexts_json,
                     notebooklm_json, tags_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    context_id,
                    context_data.get("name", ""),
                    context_data.get("scenario", "unknown"),
                    json.dumps(context_data.get("metadata", {}), ensure_ascii=False),
                    json.dumps(context_data.get("file_contexts", []), ensure_ascii=False),
                    json.dumps(context_data.get("notebooklm"), ensure_ascii=False),
                    json.dumps(context_data.get("tags", []), ensure_ascii=False),
                    context_data.get("created_at", now),
                    now,
                ),
            )

        # 保存文件上下文
        conn.execute("DELETE FROM context_files WHERE context_id = ?", (context_id,))
        for file_ctx in context_data.get("file_contexts", []):
            if isinstance(file_ctx, dict):
                conn.execute(
                    """INSERT INTO context_files (context_id, path, language, size)
                    VALUES (?, ?, ?, ?)""",
                    (
                        context_id,
                        file_ctx.get("path", ""),
                        file_ctx.get("language", ""),
                        file_ctx.get("size", 0),
                    ),
                )

        conn.commit()
        return context_id

    def get(self, context_id: str) -> Optional[Dict[str, Any]]:
        """获取 Context"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM contexts WHERE context_id = ?",
            (context_id,),
        ).fetchone()

        if not row:
            return None

        return self._row_to_dict(row)

    def list_contexts(
        self,
        scenario: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """列出 Context"""
        conn = self._get_conn()

        if scenario:
            rows = conn.execute(
                """SELECT * FROM contexts WHERE scenario = ?
                ORDER BY updated_at DESC LIMIT ? OFFSET ?""",
                (scenario, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM contexts
                ORDER BY updated_at DESC LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def delete(self, context_id: str) -> bool:
        """删除 Context"""
        conn = self._get_conn()
        conn.execute("DELETE FROM context_files WHERE context_id = ?", (context_id,))
        cursor = conn.execute("DELETE FROM contexts WHERE context_id = ?", (context_id,))
        conn.commit()
        return cursor.rowcount > 0

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索 Context"""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM contexts
            WHERE name LIKE ? OR tags_json LIKE ?
            ORDER BY updated_at DESC LIMIT ?""",
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def count(self, scenario: Optional[str] = None) -> int:
        """统计 Context 数量"""
        conn = self._get_conn()
        if scenario:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM contexts WHERE scenario = ?",
                (scenario,),
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) as cnt FROM contexts").fetchone()
        return row["cnt"] if row else 0

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        return {
            "context_id": row["context_id"],
            "name": row["name"],
            "scenario": row["scenario"],
            "metadata": json.loads(row["metadata_json"]),
            "file_contexts": json.loads(row["file_contexts_json"]),
            "notebooklm": json.loads(row["notebooklm_json"]),
            "tags": json.loads(row["tags_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
