# Pack Market Storage Layer
# Track A Day 1: Pack 市场存储实现

"""
Pack 市场存储层
使用 SQLite 提供持久化存储
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .market import PackListing, PackRating, PackStatus, UserFeedback


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
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
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
                    downloads INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0.0,
                    rating_count INTEGER DEFAULT 0,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
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

            conn.commit()

    # ========== Pack 列表操作 ==========

    def create_listing(self, listing: PackListing) -> bool:
        """创建 Pack 列表项

        Args:
            listing: Pack 列表项

        Returns:
            是否创建成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO pack_listings (
                        pack_id, pack_name, version, description, author, category,
                        tags, downloads, rating, rating_count, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        listing.pack_id,
                        listing.pack_name,
                        listing.version,
                        listing.description,
                        listing.author,
                        listing.category,
                        json.dumps(listing.tags),
                        listing.downloads,
                        listing.rating,
                        listing.rating_count,
                        listing.status.value,
                        listing.created_at.isoformat(),
                        listing.updated_at.isoformat(),
                    ),
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def get_listing(self, pack_id: str) -> Optional[PackListing]:
        """获取 Pack 列表项

        Args:
            pack_id: Pack ID

        Returns:
            Pack 列表项，不存在返回 None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pack_listings WHERE pack_id = ?", (pack_id,))
            row = cursor.fetchone()

            if row is None:
                return None

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
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    def update_listing(self, listing: PackListing) -> bool:
        """更新 Pack 列表项

        Args:
            listing: Pack 列表项

        Returns:
            是否更新成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE pack_listings SET
                        pack_name = ?, version = ?, description = ?, author = ?, category = ?,
                        tags = ?, downloads = ?, rating = ?, rating_count = ?, status = ?, updated_at = ?
                    WHERE pack_id = ?
                """,
                    (
                        listing.pack_name,
                        listing.version,
                        listing.description,
                        listing.author,
                        listing.category,
                        json.dumps(listing.tags),
                        listing.downloads,
                        listing.rating,
                        listing.rating_count,
                        listing.status.value,
                        listing.updated_at.isoformat(),
                        listing.pack_id,
                    ),
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            return False

    def delete_listing(self, pack_id: str) -> bool:
        """删除 Pack 列表项

        Args:
            pack_id: Pack ID

        Returns:
            是否删除成功
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pack_listings WHERE pack_id = ?", (pack_id,))
            conn.commit()
            return cursor.rowcount > 0

    def list_listings(
        self,
        category: Optional[str] = None,
        status: Optional[PackStatus] = None,
        author: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PackListing]:
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
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM pack_listings WHERE 1=1"
            params = []

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
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [
                PackListing(
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
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            ]

    def search_listings(self, query: str, limit: int = 100) -> List[PackListing]:
        """搜索 Pack 列表项（支持模糊匹配）

        Args:
            query: 搜索关键词
            limit: 限制数量

        Returns:
            Pack 列表项列表
        """
        with sqlite3.connect(self.db_path) as conn:
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

            return [
                PackListing(
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
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            ]

    # ========== Pack 评价操作 ==========

    def create_rating(self, rating: PackRating) -> bool:
        """创建 Pack 评价

        Args:
            rating: Pack 评价

        Returns:
            是否创建成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
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

    def get_rating(self, rating_id: str) -> Optional[PackRating]:
        """获取 Pack 评价

        Args:
            rating_id: 评价 ID

        Returns:
            Pack 评价，不存在返回 None
        """
        with sqlite3.connect(self.db_path) as conn:
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

    def list_ratings(self, pack_id: str, limit: int = 100) -> List[PackRating]:
        """列出 Pack 评价

        Args:
            pack_id: Pack ID
            limit: 限制数量

        Returns:
            Pack 评价列表
        """
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
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

    def get_feedback(self, feedback_id: str) -> Optional[UserFeedback]:
        """获取用户反馈

        Args:
            feedback_id: 反馈 ID

        Returns:
            用户反馈，不存在返回 None
        """
        with sqlite3.connect(self.db_path) as conn:
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
        self, pack_id: str, feedback_type: Optional[str] = None
    ) -> List[UserFeedback]:
        """列出用户反馈

        Args:
            pack_id: Pack ID
            feedback_type: 反馈类型过滤

        Returns:
            用户反馈列表
        """
        with sqlite3.connect(self.db_path) as conn:
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
