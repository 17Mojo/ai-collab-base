# Pack Market Storage Layer
# Track A Day 1: Pack 市场存储实现

"""
Pack 市场存储层
使用 SQLite 提供持久化存储
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from .market import PackListing, PackRating, PackStatus, UserFeedback


@contextmanager
def _connect(db_path: str) -> Iterator[sqlite3.Connection]:
    """打开 SQLite 连接，退出时提交事务并关闭连接。

    sqlite3 的 ``with conn:`` 只管理**事务**（成功提交 / 异常回滚），**不关闭连接**。
    直接写 ``with sqlite3.connect(...) as conn:`` 会泄漏连接，
    表现为 ``ResourceWarning: unclosed database``。

    这里在事务上下文外层补上关闭语义：退出顺序为「先提交/回滚，后关闭」。
    注意不能只包 ``contextlib.closing`` —— 那会丢掉事务上下文导致写入不落盘。
    """
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


class PackMarketStore:
    """Pack 市场存储层"""

    def __init__(self, db_path: str = "data/packs.db"):
        """初始化存储

        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = db_path
        self._ensure_db_path()
        self._init_schema()

    def _ensure_db_path(self) -> None:
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_schema(self) -> None:
        """初始化数据库表结构（含旧库迁移）

        迁移策略（2026-11-05，known_gaps N17 收口）：
        - pack_listings 新库 DDL 直接带 ``dependencies TEXT NOT NULL DEFAULT '[]'``；
          旧库（无该列）通过 PRAGMA table_info 探测后 ``ALTER TABLE ADD COLUMN``
          就地补齐，既有行落默认 ``[]``，数据零丢失。
        - pack_versions 为**追加式版本历史**：PRIMARY KEY (pack_id, version)，
          INSERT OR IGNORE —— 每个版本只留「首次归档快照」（发布时状态），
          同版本的元数据改动（如 approve 改 status）不重写历史；
          pack_listings 仍是当前真值。update_listing 覆盖前先归档旧行，
          所以迁移前的存量行也会在首次更新时补进历史。
        """
        with _connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Pack 列表表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pack_listings (
                    pack_id TEXT PRIMARY KEY,
                    pack_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    description TEXT NOT NULL,
                    author TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    dependencies TEXT NOT NULL DEFAULT '[]',
                    downloads INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    rating_count INTEGER DEFAULT 0,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """
            )

            # 旧库迁移：pack_listings 缺 dependencies 列则就地补齐
            cursor.execute("PRAGMA table_info(pack_listings)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            if "dependencies" not in existing_cols:
                cursor.execute(
                    "ALTER TABLE pack_listings ADD COLUMN dependencies "
                    "TEXT NOT NULL DEFAULT '[]'"
                )

            # Pack 版本历史表（追加式，见方法 docstring 的语义说明）
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pack_versions (
                    pack_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    pack_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    author TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    dependencies TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived_at TEXT NOT NULL,
                    PRIMARY KEY (pack_id, version)
                )
            """
            )

            # Pack 评价表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pack_ratings (
                    rating_id TEXT PRIMARY KEY,
                    pack_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                    title TEXT DEFAULT '',
                    content TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (pack_id) REFERENCES pack_listings(pack_id) ON DELETE CASCADE
                )
            """
            )

            # 用户反馈表
            # CHECK constraint: feedback_type 必须为 bug/suggestion/request (OpenSpec Requirement)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    pack_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL CHECK(feedback_type IN ('bug', 'suggestion', 'request')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (pack_id) REFERENCES pack_listings(pack_id) ON DELETE CASCADE
                )
            """
            )

            # 创建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_pack_category ON pack_listings(category)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_status ON pack_listings(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pack_author ON pack_listings(author)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rating_pack ON pack_ratings(pack_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rating_user ON pack_ratings(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_pack ON user_feedback(pack_id)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_versions_pack ON pack_versions(pack_id)"
            )

            conn.commit()

    # ========== 内部工具 ==========

    @staticmethod
    def _row_to_listing(row: sqlite3.Row) -> PackListing:
        """把 pack_listings 行转为 PackListing（含 dependencies 反序列化）。

        dependencies 列损坏时降级为空列表，不阻断读取。
        """
        try:
            deps = json.loads(row["dependencies"] or "[]")
        except (json.JSONDecodeError, TypeError):
            deps = []
        return PackListing(
            pack_id=row["pack_id"],
            pack_name=row["pack_name"],
            version=row["version"],
            description=row["description"],
            author=row["author"],
            category=row["category"],
            tags=json.loads(row["tags"]),
            downloads=row["downloads"],
            rating=row["rating"],
            rating_count=row["rating_count"],
            status=PackStatus(row["status"]),
            dependencies=deps if isinstance(deps, list) else [],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _archive_version(conn: sqlite3.Connection, listing: PackListing) -> None:
        """把 listing 快照归档进 pack_versions（追加式，INSERT OR IGNORE）。

        (pack_id, version) 已归档则不覆盖——历史保留「首次归档快照」。
        """
        conn.execute(
            """
            INSERT OR IGNORE INTO pack_versions (
                pack_id, version, pack_name, description, author, category,
                tags, dependencies, status, created_at, updated_at, archived_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                listing.pack_id,
                listing.version,
                listing.pack_name,
                listing.description,
                listing.author,
                listing.category,
                json.dumps(listing.tags),
                json.dumps(listing.dependencies),
                listing.status.value,
                listing.created_at.isoformat(),
                listing.updated_at.isoformat(),
                datetime.now().isoformat(),
            ),
        )

    # ========== Pack 列表操作 ==========

    def create_listing(self, listing: PackListing) -> bool:
        """创建 Pack 列表项

        Args:
            listing: Pack 列表项

        Returns:
            是否创建成功
        """
        try:
            with _connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO pack_listings (
                        pack_id, pack_name, version, description, author, category,
                        tags, dependencies, downloads, rating, rating_count,
                        status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        listing.pack_id,
                        listing.pack_name,
                        listing.version,
                        listing.description,
                        listing.author,
                        listing.category,
                        json.dumps(listing.tags),
                        json.dumps(listing.dependencies),
                        listing.downloads,
                        listing.rating,
                        listing.rating_count,
                        listing.status.value,
                        listing.created_at.isoformat(),
                        listing.updated_at.isoformat(),
                    ),
                )
                self._archive_version(conn, listing)
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_listing(self, pack_id: str) -> PackListing | None:
        """获取 Pack 列表项

        Args:
            pack_id: Pack ID

        Returns:
            Pack 列表项，不存在返回 None
        """
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pack_listings WHERE pack_id = ?", (pack_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return self._row_to_listing(row)

    def update_listing(self, listing: PackListing) -> bool:
        """更新 Pack 列表项

        覆盖前先把库中旧行归档进 pack_versions（迁移前存量行由此补进历史），
        再归档新快照（同版本已归档则忽略，见 _archive_version）。

        Args:
            listing: Pack 列表项

        Returns:
            是否更新成功
        """
        try:
            with _connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM pack_listings WHERE pack_id = ?", (listing.pack_id,)
                )
                old_row = cursor.fetchone()
                if old_row is not None:
                    self._archive_version(conn, self._row_to_listing(old_row))
                cursor.execute(
                    """
                    UPDATE pack_listings SET
                        pack_name = ?, version = ?, description = ?, author = ?, category = ?,
                        tags = ?, dependencies = ?, downloads = ?, rating = ?, rating_count = ?,
                        status = ?, updated_at = ?
                    WHERE pack_id = ?
                """,
                    (
                        listing.pack_name,
                        listing.version,
                        listing.description,
                        listing.author,
                        listing.category,
                        json.dumps(listing.tags),
                        json.dumps(listing.dependencies),
                        listing.downloads,
                        listing.rating,
                        listing.rating_count,
                        listing.status.value,
                        listing.updated_at.isoformat(),
                        listing.pack_id,
                    ),
                )
                updated = cursor.rowcount > 0
                if updated:
                    self._archive_version(conn, listing)
                conn.commit()
                return updated
        except sqlite3.IntegrityError:
            return False

    def delete_listing(self, pack_id: str) -> bool:
        """删除 Pack 列表项

        Args:
            pack_id: Pack ID

        Returns:
            是否删除成功
        """
        with _connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pack_listings WHERE pack_id = ?", (pack_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_listings(
        self,
        category: str | None = None,
        status: PackStatus | None = None,
        author: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PackListing]:
        """列出 Pack 列表项（支持过滤）

        Args:
            category: 类别过滤
            status: 状态过滤
            author: 作者过滤
            limit: 限制数量
            offset: 偏移量

        Returns:
            Pack 列表项列表
        """
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM pack_listings WHERE 1=1"
            params: list[Any] = []

            if category:
                query += " AND category = ?"
                params.append(category)

            if status:
                query += " AND status = ?"
                params.append(status.value)

            if author:
                query += " AND author = ?"
                params.append(author)

            query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
            params.extend([int(limit), int(offset)])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_listing(row) for row in rows]

    def search_listings(self, query: str, limit: int = 100) -> list[PackListing]:
        """搜索 Pack 列表项（支持模糊匹配）

        Args:
            query: 搜索关键词
            limit: 限制数量

        Returns:
            Pack 列表项列表
        """
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            search_pattern = f"%{query}%"
            cursor.execute(
                """
                SELECT * FROM pack_listings
                WHERE pack_name LIKE ? OR description LIKE ? OR author LIKE ?
                ORDER BY rating DESC, downloads DESC LIMIT ?
            """,
                (search_pattern, search_pattern, search_pattern, limit),
            )

            rows = cursor.fetchall()

            return [self._row_to_listing(row) for row in rows]

    # ========== Pack 版本历史操作 ==========

    def list_versions(self, pack_id: str) -> list[dict[str, Any]]:
        """列出 Pack 版本历史（追加式归档，按归档时间升序）

        每个 (pack_id, version) 只有一条「首次归档快照」；即使 pack_listings
        中的当前行已被覆盖或删除，历史仍可查（回滚/审计依据）。

        Args:
            pack_id: Pack ID

        Returns:
            版本快照字典列表（含 archived_at），无历史返回空列表
        """
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM pack_versions
                WHERE pack_id = ? ORDER BY archived_at ASC, rowid ASC
            """,
                (pack_id,),
            )
            rows = cursor.fetchall()

            versions: list[dict[str, Any]] = []
            for row in rows:
                try:
                    deps = json.loads(row["dependencies"] or "[]")
                except (json.JSONDecodeError, TypeError):
                    deps = []
                versions.append(
                    {
                        "pack_id": row["pack_id"],
                        "version": row["version"],
                        "pack_name": row["pack_name"],
                        "description": row["description"],
                        "author": row["author"],
                        "category": row["category"],
                        "tags": json.loads(row["tags"]),
                        "dependencies": deps if isinstance(deps, list) else [],
                        "status": row["status"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "archived_at": row["archived_at"],
                    }
                )
            return versions

    # ========== Pack 评价操作 ==========

    def create_rating(self, rating: PackRating) -> bool:
        """创建 Pack 评价

        Args:
            rating: Pack 评价

        Returns:
            是否创建成功
        """
        try:
            with _connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO pack_ratings (
                        rating_id, pack_id, user_id, rating, title, content, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        rating.rating_id,
                        rating.pack_id,
                        rating.user_id,
                        rating.rating,
                        rating.title,
                        rating.content,
                        rating.created_at.isoformat(),
                    ),
                )
                conn.commit()

                # 更新平均评分
                self._update_pack_rating(rating.pack_id)

                return True
        except sqlite3.IntegrityError:
            return False

    def get_rating(self, rating_id: str) -> PackRating | None:
        """获取 Pack 评价

        Args:
            rating_id: 评价 ID

        Returns:
            Pack 评价，不存在返回 None
        """
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pack_ratings WHERE rating_id = ?", (rating_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return PackRating(
                rating_id=row["rating_id"],
                pack_id=row["pack_id"],
                user_id=row["user_id"],
                rating=row["rating"],
                title=row["title"],
                content=row["content"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    def list_ratings(self, pack_id: str, limit: int = 100) -> list[PackRating]:
        """列出 Pack 评价

        Args:
            pack_id: Pack ID
            limit: 限制数量

        Returns:
            Pack 评价列表
        """
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM pack_ratings
                WHERE pack_id = ? ORDER BY created_at DESC LIMIT ?
            """,
                (pack_id, limit),
            )

            rows = cursor.fetchall()

            return [
                PackRating(
                    rating_id=row["rating_id"],
                    pack_id=row["pack_id"],
                    user_id=row["user_id"],
                    rating=row["rating"],
                    title=row["title"],
                    content=row["content"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]

    def delete_rating(self, rating_id: str) -> bool:
        """删除 Pack 评价

        Args:
            rating_id: 评价 ID

        Returns:
            是否删除成功
        """
        with _connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 先获取 pack_id 用于更新评分
            cursor.execute("SELECT pack_id FROM pack_ratings WHERE rating_id = ?", (rating_id,))
            row = cursor.fetchone()

            if row is None:
                return False

            pack_id = row[0]

            cursor.execute("DELETE FROM pack_ratings WHERE rating_id = ?", (rating_id,))
            conn.commit()

            # 更新平均评分
            self._update_pack_rating(pack_id)

            return cursor.rowcount > 0

    def _update_pack_rating(self, pack_id: str) -> None:
        """更新 Pack 平均评分（内部方法）

        Args:
            pack_id: Pack ID
        """
        with _connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT AVG(rating), COUNT(*) FROM pack_ratings WHERE pack_id = ?
            """,
                (pack_id,),
            )

            row = cursor.fetchone()
            avg_rating = row[0] or 0.0
            rating_count = row[1] or 0

            # 更新 pack_listings
            cursor.execute(
                """
                UPDATE pack_listings SET rating = ?, rating_count = ?, updated_at = ?
                WHERE pack_id = ?
            """,
                (avg_rating, rating_count, datetime.now().isoformat(), pack_id),
            )

            conn.commit()

    # ========== 用户反馈操作 ==========

    def create_feedback(self, feedback: UserFeedback) -> bool:
        """创建用户反馈

        Args:
            feedback: 用户反馈

        Returns:
            是否创建成功
        """
        try:
            with _connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO user_feedback (
                        feedback_id, pack_id, user_id, feedback_type, content, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        feedback.feedback_id,
                        feedback.pack_id,
                        feedback.user_id,
                        feedback.feedback_type,
                        feedback.content,
                        feedback.created_at.isoformat(),
                    ),
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_feedback(self, feedback_id: str) -> UserFeedback | None:
        """获取用户反馈

        Args:
            feedback_id: 反馈 ID

        Returns:
            用户反馈，不存在返回 None
        """
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_feedback WHERE feedback_id = ?", (feedback_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return UserFeedback(
                feedback_id=row["feedback_id"],
                pack_id=row["pack_id"],
                user_id=row["user_id"],
                feedback_type=row["feedback_type"],
                content=row["content"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    def list_feedback(
        self, pack_id: str, feedback_type: str | None = None
    ) -> list[UserFeedback]:
        """列出用户反馈

        Args:
            pack_id: Pack ID
            feedback_type: 反馈类型过滤

        Returns:
            用户反馈列表
        """
        with _connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if feedback_type:
                cursor.execute(
                    """
                    SELECT * FROM user_feedback
                    WHERE pack_id = ? AND feedback_type = ?
                    ORDER BY created_at DESC
                """,
                    (pack_id, feedback_type),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM user_feedback
                    WHERE pack_id = ? ORDER BY created_at DESC
                """,
                    (pack_id,),
                )

            rows = cursor.fetchall()

            return [
                UserFeedback(
                    feedback_id=row["feedback_id"],
                    pack_id=row["pack_id"],
                    user_id=row["user_id"],
                    feedback_type=row["feedback_type"],
                    content=row["content"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]
