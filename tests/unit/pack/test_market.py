# Pack Market Tests
# Track A Day 1: Pack 市场测试

"""
Pack 市场功能测试
"""

import os
import tempfile
from datetime import datetime

import pytest

from ai_collab.pack.market import PackListing, PackRating, PackStatus, UserFeedback
from ai_collab.pack.market_api import PackMarketAPI
from ai_collab.pack.market_store import PackMarketStore


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def store(temp_db):
    """创建存储实例"""
    return PackMarketStore(temp_db)


@pytest.fixture
def api(temp_db):
    """创建 API 实例"""
    return PackMarketAPI(temp_db)


@pytest.fixture
def sample_listing():
    """创建示例 Pack 列表项"""
    return PackListing(
        pack_id="test_pack_001",
        pack_name="Test Pack",
        version="1.0.0",
        description="A test pack for testing",
        author="test_user",
        category="productivity",
        tags=["test", "demo"],
    )


# ========== market.py 测试 ==========


class TestPackStatus:
    """测试 PackStatus 枚举"""

    def test_status_values(self):
        """测试状态值"""
        assert PackStatus.DRAFT.value == "draft"
        assert PackStatus.PENDING.value == "pending"
        assert PackStatus.APPROVED.value == "approved"
        assert PackStatus.REJECTED.value == "rejected"
        assert PackStatus.ARCHIVED.value == "archived"

    def test_status_from_string(self):
        """测试从字符串创建状态"""
        assert PackStatus("draft") == PackStatus.DRAFT
        assert PackStatus("pending") == PackStatus.PENDING
        assert PackStatus("approved") == PackStatus.APPROVED


class TestPackListing:
    """测试 PackListing 数据类"""

    def test_create_listing(self):
        """测试创建 Pack 列表项"""
        listing = PackListing(
            pack_id="test_001",
            pack_name="Test Pack",
            version="1.0.0",
            description="Test description",
            author="user1",
            category="productivity",
        )

        assert listing.pack_id == "test_001"
        assert listing.status == PackStatus.PENDING
        assert listing.downloads == 0
        assert listing.rating == 0.0

    def test_add_tag(self):
        """测试添加标签"""
        listing = PackListing(
            pack_id="test_001",
            pack_name="Test Pack",
            version="1.0.0",
            description="Test",
            author="user1",
            category="productivity",
        )

        listing.add_tag("new_tag")
        assert "new_tag" in listing.tags

        # 测试重复标签
        initial_count = len(listing.tags)
        listing.add_tag("new_tag")
        assert len(listing.tags) == initial_count

    def test_increment_downloads(self):
        """测试增加下载次数"""
        listing = PackListing(
            pack_id="test_001",
            pack_name="Test Pack",
            version="1.0.0",
            description="Test",
            author="user1",
            category="productivity",
        )

        initial = listing.downloads
        listing.increment_downloads()
        assert listing.downloads == initial + 1

    def test_update_rating(self):
        """测试更新评分"""
        listing = PackListing(
            pack_id="test_001",
            pack_name="Test Pack",
            version="1.0.0",
            description="Test",
            author="user1",
            category="productivity",
        )

        listing.update_rating(4.5, 10)
        assert listing.rating == 4.5
        assert listing.rating_count == 10

    def test_approve(self):
        """测试批准 Pack"""
        listing = PackListing(
            pack_id="test_001",
            pack_name="Test Pack",
            version="1.0.0",
            description="Test",
            author="user1",
            category="productivity",
        )

        listing.approve()
        assert listing.status == PackStatus.APPROVED

    def test_reject(self):
        """测试拒绝 Pack"""
        listing = PackListing(
            pack_id="test_001",
            pack_name="Test Pack",
            version="1.0.0",
            description="Test",
            author="user1",
            category="productivity",
        )

        listing.reject()
        assert listing.status == PackStatus.REJECTED

    def test_to_dict(self):
        """测试序列化"""
        listing = PackListing(
            pack_id="test_001",
            pack_name="Test Pack",
            version="1.0.0",
            description="Test",
            author="user1",
            category="productivity",
        )

        data = listing.to_dict()

        assert data["pack_id"] == "test_001"
        assert data["pack_name"] == "Test Pack"
        assert data["status"] == "pending"
        assert "created_at" in data
        assert "updated_at" in data

    def test_from_dict(self):
        """测试从字典反序列化"""
        data = {
            "pack_id": "test_001",
            "pack_name": "Test Pack",
            "version": "1.0.0",
            "description": "Test",
            "author": "user1",
            "category": "productivity",
            "tags": [],
            "downloads": 0,
            "rating": 0.0,
            "rating_count": 0,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        listing = PackListing.from_dict(data)

        assert listing.pack_id == "test_001"
        assert listing.pack_name == "Test Pack"
        assert listing.status == PackStatus.PENDING


class TestPackRating:
    """测试 PackRating 数据类"""

    def test_create_rating(self):
        """测试创建评价"""
        rating = PackRating(
            rating_id="rating_001",
            pack_id="test_pack",
            user_id="user1",
            rating=5,
            title="Great",
            content="Excellent pack",
        )

        assert rating.rating == 5
        assert rating.title == "Great"
        assert rating.user_id == "user1"

    def test_rating_validation(self):
        """测试评分验证"""
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            PackRating(rating_id="rating_001", pack_id="test_pack", user_id="user1", rating=6)

        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            PackRating(rating_id="rating_001", pack_id="test_pack", user_id="user1", rating=0)

    def test_to_dict(self):
        """测试序列化"""
        rating = PackRating(rating_id="rating_001", pack_id="test_pack", user_id="user1", rating=5)

        data = rating.to_dict()

        assert data["rating_id"] == "rating_001"
        assert data["rating"] == 5
        assert "created_at" in data


class TestUserFeedback:
    """测试 UserFeedback 数据类"""

    def test_create_feedback(self):
        """测试创建反馈"""
        feedback = UserFeedback(
            feedback_id="feedback_001",
            pack_id="test_pack",
            user_id="user1",
            feedback_type="bug",
            content="Found a bug",
        )

        assert feedback.feedback_type == "bug"
        assert feedback.pack_id == "test_pack"

    def test_feedback_type_validation(self):
        """测试反馈类型验证"""
        with pytest.raises(ValueError, match="Invalid feedback_type"):
            UserFeedback(
                feedback_id="feedback_001",
                pack_id="test_pack",
                user_id="user1",
                feedback_type="invalid",
                content="Test",
            )

    def test_to_dict(self):
        """测试序列化"""
        feedback = UserFeedback(
            feedback_id="feedback_001",
            pack_id="test_pack",
            user_id="user1",
            feedback_type="suggestion",
            content="Add feature",
        )

        data = feedback.to_dict()

        assert data["feedback_id"] == "feedback_001"
        assert data["feedback_type"] == "suggestion"
        assert "created_at" in data


# ========== market_store.py 测试 ==========


class TestPackMarketStore:
    """测试 PackMarketStore 类"""

    def test_init_creates_tables(self, temp_db):
        """测试初始化创建表"""
        PackMarketStore(temp_db)

        # 检查表是否存在
        import sqlite3

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            assert "pack_listings" in tables
            assert "pack_ratings" in tables
            assert "user_feedback" in tables

    def test_create_listing(self, store, sample_listing):
        """测试创建 Pack 列表项"""
        success = store.create_listing(sample_listing)
        assert success is True

    def test_create_duplicate_listing(self, store, sample_listing):
        """测试创建重复 Pack 列表项"""
        store.create_listing(sample_listing)
        success = store.create_listing(sample_listing)
        assert success is False

    def test_get_listing(self, store, sample_listing):
        """测试获取 Pack 列表项"""
        store.create_listing(sample_listing)
        result = store.get_listing(sample_listing.pack_id)

        assert result is not None
        assert result.pack_id == sample_listing.pack_id
        assert result.pack_name == sample_listing.pack_name

    def test_get_nonexistent_listing(self, store):
        """测试获取不存在的 Pack"""
        result = store.get_listing("nonexistent")
        assert result is None

    def test_update_listing(self, store, sample_listing):
        """测试更新 Pack 列表项"""
        store.create_listing(sample_listing)

        sample_listing.pack_name = "Updated Name"
        sample_listing.increment_downloads()

        success = store.update_listing(sample_listing)
        assert success is True

        result = store.get_listing(sample_listing.pack_id)
        assert result.pack_name == "Updated Name"
        assert result.downloads == 1

    def test_delete_listing(self, store, sample_listing):
        """测试删除 Pack 列表项"""
        store.create_listing(sample_listing)
        success = store.delete_listing(sample_listing.pack_id)
        assert success is True

        result = store.get_listing(sample_listing.pack_id)
        assert result is None

    def test_list_listings(self, store):
        """测试列出 Pack 列表项"""
        for i in range(5):
            listing = PackListing(
                pack_id=f"pack_{i}",
                pack_name=f"Pack {i}",
                version="1.0.0",
                description=f"Description {i}",
                author="user1",
                category="productivity",
            )
            store.create_listing(listing)

        listings = store.list_listings()
        assert len(listings) == 5

    def test_list_listings_with_category(self, store):
        """测试按类别列出 Pack"""
        listing1 = PackListing(
            pack_id="pack_1",
            pack_name="Pack 1",
            version="1.0.0",
            description="Desc 1",
            author="user1",
            category="productivity",
        )
        listing2 = PackListing(
            pack_id="pack_2",
            pack_name="Pack 2",
            version="1.0.0",
            description="Desc 2",
            author="user1",
            category="business",
        )

        store.create_listing(listing1)
        store.create_listing(listing2)

        productivity_packs = store.list_listings(category="productivity")
        business_packs = store.list_listings(category="business")

        assert len(productivity_packs) == 1
        assert len(business_packs) == 1
        assert productivity_packs[0].pack_id == "pack_1"

    def test_list_listings_with_status(self, store):
        """测试按状态列出 Pack"""
        listing1 = PackListing(
            pack_id="pack_1",
            pack_name="Pack 1",
            version="1.0.0",
            description="Desc 1",
            author="user1",
            category="productivity",
            status=PackStatus.APPROVED,
        )
        listing2 = PackListing(
            pack_id="pack_2",
            pack_name="Pack 2",
            version="1.0.0",
            description="Desc 2",
            author="user1",
            category="productivity",
        )

        store.create_listing(listing1)
        store.create_listing(listing2)

        approved_packs = store.list_listings(status=PackStatus.APPROVED)
        assert len(approved_packs) == 1

    def test_search_listings(self, store):
        """测试搜索 Pack"""
        listing1 = PackListing(
            pack_id="pack_1",
            pack_name="Email Helper",
            version="1.0.0",
            description="Help with email",
            author="user1",
            category="productivity",
        )
        listing2 = PackListing(
            pack_id="pack_2",
            pack_name="Task Manager",
            version="1.0.0",
            description="Manage tasks",
            author="user1",
            category="productivity",
        )

        store.create_listing(listing1)
        store.create_listing(listing2)

        results = store.search_listings("email")
        assert len(results) == 1
        assert results[0].pack_id == "pack_1"

    def test_create_rating(self, store, sample_listing):
        """测试创建评价"""
        store.create_listing(sample_listing)

        rating = PackRating(
            rating_id="rating_001",
            pack_id=sample_listing.pack_id,
            user_id="user1",
            rating=5,
            title="Great",
            content="Excellentcellent",
        )

        success = store.create_rating(rating)
        assert success is True

        # 检查 Pack 评分是否更新
        updated = store.get_listing(sample_listing.pack_id)
        assert updated.rating == 5.0
        assert updated.rating_count == 1

    def test_get_rating(self, store, sample_listing):
        """测试获取评价"""
        store.create_listing(sample_listing)

        rating = PackRating(
            rating_id="rating_001", pack_id=sample_listing.pack_id, user_id="user1", rating=5
        )

        store.create_rating(rating)
        result = store.get_rating("rating_001")

        assert result is not None
        assert result.rating_id == "rating_001"
        assert result.rating == 5

    def test_list_ratings(self, store, sample_listing):
        """测试列出 Pack 评价"""
        store.create_listing(sample_listing)

        for i in range(3):
            rating = PackRating(
                rating_id=f"rating_{i}",
                pack_id=sample_listing.pack_id,
                user_id=f"user{i}",
                rating=i + 1,
            )
            store.create_rating(rating)

        ratings = store.list_ratings(sample_listing.pack_id)
        assert len(ratings) == 3

    def test_delete_rating_updates_pack(self, store, sample_listing):
        """测试删除评价更新 Pack 评分"""
        store.create_listing(sample_listing)

        rating1 = PackRating(
            rating_id="rating_1", pack_id=sample_listing.pack_id, user_id="user1", rating=5
        )
        rating2 = PackRating(
            rating_id="rating_2", pack_id=sample_listing.pack_id, user_id="user2", rating=3
        )

        store.create_rating(rating1)
        updated = store.get_listing(sample_listing.pack_id)
        assert updated.rating_count == 1

        store.create_rating(rating2)
        updated = store.get_listing(sample_listing.pack_id)
        assert updated.rating_count == 2

        # 删除一个评价，评分应该重新计算
        store.delete_rating("rating_1")
        updated = store.get_listing(sample_listing.pack_id)
        assert updated.rating_count == 1
        assert updated.rating == 3.0

    def test_create_feedback(self, store, sample_listing):
        """测试创建反馈"""
        store.create_listing(sample_listing)

        feedback = UserFeedback(
            feedback_id="feedback_001",
            pack_id=sample_listing.pack_id,
            user_id="user1",
            feedback_type="bug",
            content="Bug found",
        )

        success = store.create_feedback(feedback)
        assert success is True

    def test_get_feedback(self, store, sample_listing):
        """测试获取反馈"""
        store.create_listing(sample_listing)

        feedback = UserFeedback(
            feedback_id="feedback_001",
            pack_id=sample_listing.pack_id,
            user_id="user1",
            feedback_type="suggestion",
            content="Suggestion",
        )

        store.create_feedback(feedback)
        result = store.get_feedback("feedback_001")

        assert result is not None
        assert result.feedback_type == "suggestion"

    def test_list_feedback_with_type(self, store, sample_listing):
        """测试按类型列出反馈"""
        store.create_listing(sample_listing)

        feedback1 = UserFeedback(
            feedback_id="feedback_1",
            pack_id=sample_listing.pack_id,
            user_id="user1",
            feedback_type="bug",
            content="Bug",
        )
        feedback2 = UserFeedback(
            feedback_id="feedback_2",
            pack_id=sample_listing.pack_id,
            user_id="user2",
            feedback_type="suggestion",
            content="Suggestion",
        )

        store.create_feedback(feedback1)
        store.create_feedback(feedback2)

        bugs = store.list_feedback(sample_listing.pack_id, "bug")
        suggestions = store.list_feedback(sample_listing.pack_id, "suggestion")

        assert len(bugs) == 1
        assert len(suggestions) == 1


# ========== market_api.py 测试 ==========


class TestPackMarketAPI:
    """测试 PackMarketAPI 类"""

    def test_create_pack(self, api):
        """测试创建 Pack"""
        result = api.create_pack(
            pack_name="Test Pack",
            version="1.0.0",
            description="Test pack",
            author="user1",
            category="productivity",
            tags=["test"],
        )

        assert result["success"] is True
        assert result["pack_id"] is not None

    def test_get_pack(self, api):
        """测试获取 Pack"""
        create_result = api.create_pack(
            pack_name="Test Pack",
            version="1.0.0",
            description="Test pack",
            author="user1",
            category="productivity",
        )

        pack_id = create_result["pack_id"]
        result = api.get_pack(pack_id)

        assert result["success"] is True
        assert result["pack"]["pack_name"] == "Test Pack"

    def test_get_nonexistent_pack(self, api):
        """测试获取不存在的 Pack"""
        result = api.get_pack("nonexistent")
        assert result["success"] is False
        assert "error" in result

    def test_update_pack(self, api):
        """测试更新 Pack"""
        create_result = api.create_pack(
            pack_name="Old Name",
            version="1.0.0",
            description="Old description",
            author="user1",
            category="productivity",
        )

        pack_id = create_result["pack_id"]
        result = api.update_pack(pack_id, pack_name="New Name", description="New description")

        assert result["success"] is True

        get_result = api.get_pack(pack_id)
        assert get_result["pack"]["pack_name"] == "New Name"
        assert get_result["pack"]["description"] == "New description"

    def test_delete_pack(self, api):
        """测试删除 Pack"""
        create_result = api.create_pack(
            pack_name="To Delete",
            version="1.0.0",
            description="Delete me",
            author="user1",
            category="productivity",
        )

        pack_id = create_result["pack_id"]
        result = api.delete_pack(pack_id)

        assert result["success"] is True

        get_result = api.get_pack(pack_id)
        assert get_result["success"] is False

    def test_list_packs(self, api):
        """测试列出 Pack"""
        for i in range(3):
            api.create_pack(
                pack_name=f"Pack {i}",
                version="1.0.0",
                description=f"Pack {i}",
                author="user1",
                category="productivity",
            )

        result = api.list_packs()
        assert result["success"] is True
        assert result["count"] == 3

    def test_list_packs_with_filters(self, api):
        """测试带过滤条件列出 Pack"""
        api.create_pack(
            pack_name="Pack 1",
            version="1.0.0",
            description="Pack 1",
            author="user1",
            category="productivity",
        )
        api.create_pack(
            pack_name="Pack 2",
            version="1.0.0",
            description="Pack 2",
            author="user2",
            category="business",
        )

        result = api.list_packs(category="productivity")
        assert result["count"] == 1
        assert result["packs"][0]["pack_name"] == "Pack 1"

    def test_search_packs(self, api):
        """测试搜索 Pack"""
        api.create_pack(
            pack_name="Email Helper",
            version="1.0.0",
            description="Help with email",
            author="user1",
            category="productivity",
        )
        api.create_pack(
            pack_name="Task Manager",
            version="1.0.0",
            description="Manage tasks",
            author="user1",
            category="productivity",
        )

        result = api.search_packs("email")
        assert result["count"] == 1
        assert result["packs"][0]["pack_name"] == "Email Helper"

    def test_rate_pack(self, api):
        """测试评价 Pack"""
        create_result = api.create_pack(
            pack_name="Test Pack",
            version="1.0.0",
            description="Test pack",
            author="user1",
            category="productivity",
        )

        pack_id = create_result["pack_id"]
        result = api.rate_pack(pack_id, "user1", 5, "Great", "Excellent")

        assert result["success"] is True

        get_result = api.get_pack(pack_id)
        assert get_result["pack"]["rating"] == 5.0
        assert get_result["pack"]["rating_count"] == 1

    def test_list_pack_ratings(self, api):
        """测试列出 Pack 评价"""
        create_result = api.create_pack(
            pack_name="Test Pack",
            version="1.0.0",
            description="Test pack",
            author="user1",
            category="productivity",
        )

        pack_id = create_result["pack_id"]
        api.rate_pack(pack_id, "user1", 5)
        api.rate_pack(pack_id, "user2", 4)

        result = api.list_pack_ratings(pack_id)
        assert result["count"] == 2

    def test_submit_feedback(self, api):
        """测试提交反馈"""
        create_result = api.create_pack(
            pack_name="Test Pack",
            version="1.0.0",
            description="Test pack",
            author="user1",
            category="productivity",
        )

        pack_id = create_result["pack_id"]
        result = api.submit_feedback(pack_id, "user1", "bug", "Found a bug")

        assert result["success"] is True
        assert result["feedback_id"] is not None

    def test_approve_pack(self, api):
        """测试批准 Pack"""
        create_result = api.create_pack(
            pack_name="Test Pack",
            version="1.0.0",
            description="Test pack",
            author="user1",
            category="productivity",
        )

        pack_id = create_result["pack_id"]
        result = api.approve_pack(pack_id)

        assert result["success"] is True

        get_result = api.get_pack(pack_id)
        assert get_result["pack"]["status"] == "approved"

    def test_reject_pack(self, api):
        """测试拒绝 Pack"""
        create_result = api.create_pack(
            pack_name="Test Pack",
            version="1.0.0",
            description="Test pack",
            author="user1",
            category="productivity",
        )

        pack_id = create_result["pack_id"]
        result = api.reject_pack(pack_id)

        assert result["success"] is True

        get_result = api.get_pack(pack_id)
        assert get_result["pack"]["status"] == "rejected"

    def test_increment_downloads(self, api):
        """测试增加下载次数"""
        create_result = api.create_pack(
            pack_name="Test Pack",
            version="1.0.0",
            description="Test pack",
            author="user1",
            category="productivity",
        )

        pack_id = create_result["pack_id"]
        result = api.increment_downloads(pack_id)

        assert result["success"] is True
        assert result["downloads"] == 1

    def test_get_market_stats(self, api):
        """测试获取市场统计信息"""
        api.create_pack(
            pack_name="Pack 1",
            version="1.0.0",
            description="Pack 1",
            author="user1",
            category="productivity",
        )
        pack_2 = api.create_pack(
            pack_name="Pack 2",
            version="1.0.0",
            description="Pack 2",
            author="user1",
            category="business",
        )

        api.approve_pack(pack_2["pack_id"])

        result = api.get_market_stats()

        assert result["success"] is True
        assert result["stats"]["total_packs"] == 1


# ========== SQLite CHECK Constraint 测试 ==========


class TestSQLiteCheckConstraints:
    """测试 SQLite CHECK 约束边界验证 (OpenSpec Requirement)."""

    def test_feedback_type_check_constraint_valid(self, temp_db):
        """测试 feedback_type CHECK 约束接受合法值."""
        import sqlite3

        # 创建数据库和表
        store = PackMarketStore(temp_db)

        # 创建 Pack
        listing = PackListing(
            pack_id="test_pack",
            pack_name="Test",
            version="1.0.0",
            description="Test",
            author="user1",
            category="productivity",
        )
        store.create_listing(listing)

        # 直接 SQL 插入合法 feedback_type
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_feedback (
                    feedback_id, pack_id, user_id, feedback_type, content, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    "feedback_001",
                    "test_pack",
                    "user1",
                    "bug",  # 合法值
                    "Bug report",
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

        # 验证插入成功
        feedback = store.get_feedback("feedback_001")
        assert feedback is not None
        assert feedback.feedback_type == "bug"

    def test_feedback_type_check_constraint_invalid(self, temp_db):
        """测试 feedback_type CHECK 约束拒绝非法值."""
        import sqlite3

        # 创建数据库和表
        store = PackMarketStore(temp_db)

        # 创建 Pack
        listing = PackListing(
            pack_id="test_pack",
            pack_name="Test",
            version="1.0.0",
            description="Test",
            author="user1",
            category="productivity",
        )
        store.create_listing(listing)

        # 直接 SQL 插入非法 feedback_type
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute(
                    """
                    INSERT INTO user_feedback (
                        feedback_id, pack_id, user_id, feedback_type, content, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        "feedback_002",
                        "test_pack",
                        "user1",
                        "invalid_type",  # 非法值
                        "Invalid feedback",
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()

    def test_feedback_type_check_constraint_all_valid_types(self, temp_db):
        """测试所有合法 feedback_type 值."""
        import sqlite3

        # 创建数据库和表
        store = PackMarketStore(temp_db)

        # 创建 Pack
        listing = PackListing(
            pack_id="test_pack",
            pack_name="Test",
            version="1.0.0",
            description="Test",
            author="user1",
            category="productivity",
        )
        store.create_listing(listing)

        # 测试所有合法值: bug, suggestion, request
        valid_types = ["bug", "suggestion", "request"]
        for i, valid_type in enumerate(valid_types):
            with sqlite3.connect(temp_db) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO user_feedback (
                        feedback_id, pack_id, user_id, feedback_type, content, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        f"feedback_{i}",
                        "test_pack",
                        "user1",
                        valid_type,
                        f"{valid_type} feedback",
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()

        # 验证所有插入成功
        feedbacks = store.list_feedback("test_pack")
        assert len(feedbacks) == 3

    def test_rating_check_constraint_boundary(self, temp_db):
        """测试 rating CHECK 约束边界值."""
        import sqlite3

        # 创建数据库和表
        store = PackMarketStore(temp_db)

        # 创建 Pack
        listing = PackListing(
            pack_id="test_pack",
            pack_name="Test",
            version="1.0.0",
            description="Test",
            author="user1",
            category="productivity",
        )
        store.create_listing(listing)

        # 测试边界值: 1 和 5 应该成功
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO pack_ratings (
                    rating_id, pack_id, user_id, rating, title, content, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "rating_1",
                    "test_pack",
                    "user1",
                    1,  # 边界下限
                    "Min rating",
                    "Test",
                    datetime.now().isoformat(),
                ),
            )
            cursor.execute(
                """
                INSERT INTO pack_ratings (
                    rating_id, pack_id, user_id, rating, title, content, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    "rating_5",
                    "test_pack",
                    "user2",
                    5,  # 边界上限
                    "Max rating",
                    "Test",
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()

        # 验证插入成功
        ratings = store.list_ratings("test_pack")
        assert len(ratings) == 2

    def test_rating_check_constraint_out_of_range(self, temp_db):
        """测试 rating CHECK 约束拒绝超出范围值."""
        import sqlite3

        # 创建数据库和表
        store = PackMarketStore(temp_db)

        # 创建 Pack
        listing = PackListing(
            pack_id="test_pack",
            pack_name="Test",
            version="1.0.0",
            description="Test",
            author="user1",
            category="productivity",
        )
        store.create_listing(listing)

        # 测试超出范围值: 0 和 6 应该失败
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            # rating = 0 应该失败
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute(
                    """
                    INSERT INTO pack_ratings (
                        rating_id, pack_id, user_id, rating, title, content, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        "rating_0",
                        "test_pack",
                        "user1",
                        0,  # 超下限
                        "Invalid",
                        "Test",
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            # rating = 6 应该失败
            with pytest.raises(sqlite3.IntegrityError):
                cursor.execute(
                    """
                    INSERT INTO pack_ratings (
                        rating_id, pack_id, user_id, rating, title, content, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        "rating_6",
                        "test_pack",
                        "user2",
                        6,  # 超上限
                        "Invalid",
                        "Test",
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
