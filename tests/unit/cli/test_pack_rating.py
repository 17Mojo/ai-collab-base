# Pack Rating CLI Tests
# Week 2 Day 2: Pack 评价系统测试

"""
Pack 评价 CLI 功能测试
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_collab.pack.market_api import PackMarketAPI


class TestPackRatingAPIEnhancements:
    """测试 Pack 市场 API 增强功能"""

    @pytest.fixture
    def temp_api(self):
        """创建临时 API 实例"""
        fd, path = tempfile.mkstemp(suffix=".db")
        db_path = path
        os.close(fd)

        api = PackMarketAPI(db_path)

        # 创建测试 Pack
        pack_result = api.create_pack(
            pack_name="Test Pack",
            version="1.0.0",
            description="Test description",
            author="test_user",
            category="productivity",
        )
        pack_id = pack_result["pack_id"]

        yield api, db_path, pack_id

        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_get_market_stats_with_distribution(self, temp_api):
        """测试市场统计包含星级分布"""
        api, db_path, pack_id = temp_api

        api.approve_pack(pack_id)

        result = api.get_market_stats()

        assert result["success"] is True
        assert "rating_distribution" in result["stats"]
        # Check that keys are integers
        distribution = result["stats"]["rating_distribution"]
        assert 1 in distribution
        assert 2 in distribution
        assert 3 in distribution
        assert 4 in distribution
        assert 5 in distribution

    def test_get_pack_rating_stats(self, temp_api):
        """测试 Pack 评分统计"""
        api, db_path, pack_id = temp_api

        # 添加评价
        api.rate_pack(pack_id, "user1", 5, "Great", "Excellent")
        api.rate_pack(pack_id, "user2", 4, "Good", "Nice")
        api.rate_pack(pack_id, "user3", 5, "Awesome", "Superb")

        result = api.get_pack_rating_stats(pack_id)

        assert result["success"] is True
        assert result["pack_id"] == pack_id
        assert result["rating_count"] == 3
        assert result["rating_distribution"] == {1: 0, 2: 0, 3: 0, 4: 1, 5: 2}
        assert result["high_quality_count"] == 3  # All have content

    def test_get_pack_rating_stats_nonexistent(self, temp_api):
        """测试不存在 Pack 的评分统计"""
        api, db_path, pack_id = temp_api

        result = api.get_pack_rating_stats("nonexistent_pack")

        assert result["success"] is False

    def test_get_high_quality_reviews(self, temp_api):
        """测试获取高质量评价"""
        api, db_path, pack_id = temp_api

        # 添加评价
        api.rate_pack(pack_id, "user1", 5, "Great", "Excellent")
        api.rate_pack(pack_id, "user2", 4, "Good", "Nice")  # With content
        api.rate_pack(pack_id, "user3", 5, "Awesome", "")  # Without content
        api.rate_pack(pack_id, "user4", 3, "Okay", "Average")  # Low rating

        result = api.get_high_quality_reviews(pack_id, min_rating=4)

        assert result["success"] is True
        # Should only return 4+ star with content
        assert result["count"] == 2
        assert all(r["rating"] >= 4 for r in result["reviews"])
        assert all(r.get("content") for r in result["reviews"])

    def test_get_high_quality_reviews_with_limit(self, temp_api):
        """测试高质量评价限制"""
        api, db_path, pack_id = temp_api

        # 添加多个高质量评价
        for i in range(5):
            api.rate_pack(pack_id, f"user{i}", 5, f"Review {i}", f"Content {i}")

        result = api.get_high_quality_reviews(pack_id, limit=3)

        assert result["success"] is True
        assert len(result["reviews"]) == 3

    def test_get_pack_rating_stats_recent_trend(self, temp_api):
        """测试最近评价趋势"""
        api, db_path, pack_id = temp_api

        # 添加评价
        api.rate_pack(pack_id, "user1", 5, "Great", "Excellent")

        result = api.get_pack_rating_stats(pack_id)

        assert result["success"] is True
        assert "recent_ratings_count" in result
        assert "recent_average_rating" in result

    def test_get_pack_rating_stats_seven_day_window(self, temp_api):
        """测试 7 天窗口的最近评价"""
        api, db_path, pack_id = temp_api

        # 添加评价（自动在 7 天内）
        api.rate_pack(pack_id, "user1", 5, "Great", "Excellent")

        result = api.get_pack_rating_stats(pack_id)

        assert result["success"] is True
        assert result["recent_ratings_count"] >= 1


class TestPackRatingScenarios:
    """测试 Pack 评价场景"""

    @pytest.fixture
    def temp_api(self):
        """创建临时 API 实例用于场景测试"""
        fd, path = tempfile.mkstemp(suffix=".db")
        db_path = path
        os.close(fd)

        api = PackMarketAPI(db_path)

        # 创建多个测试 Pack
        pack_ids = []
        for i in range(3):
            pack_result = api.create_pack(
                pack_name=f"Pack {i}",
                version="1.0.0",
                description=f"Description {i}",
                author="test_user",
                category="productivity",
            )
            pack_ids.append(pack_result["pack_id"])

        yield api, pack_ids, db_path

        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_full_rating_workflow(self, temp_api):
        """测试完整评价流程"""
        api, pack_ids, db_path = temp_api

        pack_id = pack_ids[0]

        # 1. 添加评价
        add_result = api.rate_pack(pack_id, "user1", 5, "Great", "Excellent")
        assert add_result["success"] is True

        # 2. 查看评分
        pack = api.get_pack(pack_id)["pack"]
        assert pack["rating_count"] == 1

        # 3. 添加更多评价
        for user_id, score in [("user2", 4), ("user3", 5), ("user4", 3)]:
            api.rate_pack(pack_id, user_id, score, "Test", "Test")

        # 4. 检查评分更新
        pack = api.get_pack(pack_id)["pack"]
        assert pack["rating_count"] == 4

    def test_multiple_packs_ratings(self, temp_api):
        """测试多个 Pack 的评价"""
        api, pack_ids, db_path = temp_api

        # 批准 Packs
        for pack_id in pack_ids[:2]:
            api.approve_pack(pack_id)

        # 为每个 Pack 添加评价
        for i, pack_id in enumerate(pack_ids):
            for j in range(3):
                api.rate_pack(pack_id, f"user{j}", (i + j) % 5 + 1, f"Review {j}", f"Content {j}")

        # 获取全局统计
        stats = api.get_market_stats()["stats"]
        assert stats["total_packs"] >= 2

    def test_rating_statistics(self, temp_api):
        """测试评分统计功能"""
        api, pack_ids, db_path = temp_api

        pack_id = pack_ids[0]

        # 添加多种评分
        api.rate_pack(pack_id, "user1", 5, "Excellent", "Great pack")
        api.rate_pack(pack_id, "user2", 4, "Good", "Nice work")
        api.rate_pack(pack_id, "user3", 3, "Average", "Could improve")
        api.rate_pack(pack_id, "user4", 2, "Fair", "Some issues")
        api.rate_pack(pack_id, "user5", 1, "Poor", "Not good")

        stats = api.get_pack_rating_stats(pack_id)

        assert stats["success"] is True
        assert stats["rating_count"] == 5
        assert stats["rating_distribution"][5] == 1
        assert stats["rating_distribution"][4] == 1
        assert stats["rating_distribution"][3] == 1
        assert stats["rating_distribution"][2] == 1
        assert stats["rating_distribution"][1] == 1

    def test_rating_updates_automatically(self, temp_api):
        """测试评分自动更新"""
        api, pack_ids, db_path = temp_api

        pack_id = pack_ids[0]

        # 初始评分
        api.rate_pack(pack_id, "user1", 5, "Great", "Excellent")

        pack1 = api.get_pack(pack_id)["pack"]
        initial_rating = pack1["rating"]
        initial_count = pack1["rating_count"]

        assert initial_rating == 5.0
        assert initial_count == 1

        # 添加更多评分
        api.rate_pack(pack_id, "user2", 3, "Okay", "average")
        api.rate_pack(pack_id, "user3", 4, "Good", "nice")

        pack2 = api.get_pack(pack_id)["pack"]
        new_rating = pack2["rating"]
        new_count = pack2["rating_count"]

        assert new_count == 3
        # Average should be (5 + 3 + 4) / 3 = 4.0
        assert new_rating == 4.0

    def test_high_quality_filter(self, temp_api):
        """测试高质量评价筛选"""
        api, pack_ids, db_path = temp_api

        pack_id = pack_ids[0]

        # 添加不同质量的评价
        api.rate_pack(pack_id, "user1", 5, "Great", "Excellent detailed review")  # High quality
        api.rate_pack(pack_id, "user2", 4, "Good", "Nice")  # High quality (short but has content)
        api.rate_pack(pack_id, "user3", 5, "Awesome", "")  # No content
        api.rate_pack(pack_id, "user4", 3, "Okay", "")  # Low rating, no content

        # 获取高质量评价
        result = api.get_high_quality_reviews(pack_id, min_rating=4)

        assert result["success"] is True
        assert result["count"] == 2  # Only two have content and 4+ rating

        # Check that all returned reviews have content
        for review in result["reviews"]:
            assert review["rating"] >= 4
            assert len(review["content"]) > 0


class TestPackMarketAPICompatibility:
    """测试 Pack 市场 API 兼容性"""

    @pytest.fixture
    def temp_api(self):
        """创建临时 API 实例"""
        fd, path = tempfile.mkstemp(suffix=".db")
        db_path = path
        os.close(fd)

        api = PackMarketAPI(db_path)

        # 创建测试 Pack
        pack_result = api.create_pack(
            pack_name="Test Pack",
            version="1.0.0",
            description="Test description",
            author="test_user",
            category="productivity",
        )
        pack_id = pack_result["pack_id"]

        yield api, db_path, pack_id

        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_existing_rate_pack_still_works(self, temp_api):
        """测试现有 rate_pack 方法仍然正常工作"""
        api, db_path, pack_id = temp_api

        result = api.rate_pack(pack_id, "user1", 5, "Great", "Excellent")

        assert result["success"] is True
        assert "rating_id" in result

    def test_existing_list_pack_ratings_still_works(self, temp_api):
        """测试现有 list_pack_ratings 方法仍然正常工作"""
        api, db_path, pack_id = temp_api

        # 添加评价
        api.rate_pack(pack_id, "user1", 5, "Great", "Excellent")
        api.rate_pack(pack_id, "user2", 4, "Good", "Nice")

        result = api.list_pack_ratings(pack_id)

        assert result["success"] is True
        assert result["count"] == 2

    def test_existing_get_rating_still_works(self, temp_api):
        """测试现有 get_rating 方法仍然正常工作"""
        api, db_path, pack_id = temp_api

        add_result = api.rate_pack(pack_id, "user1", 5, "Great", "Excellent")
        rating_id = add_result["rating_id"]

        result = api.get_rating(rating_id)

        assert result["success"] is True
        assert result["rating"]["rating"] == 5

    def test_existing_get_market_stats_will_distribution(self, temp_api):
        """测试 get_market_stats 包含新的分布信息但不破坏兼容性"""
        api, db_path, pack_id = temp_api

        api.approve_pack(pack_id)

        result = api.get_market_stats()

        assert result["success"] is True
        stats = result["stats"]

        # 原有字段仍然存在
        assert "total_packs" in stats
        assert "pending_packs" in stats
        assert "total_downloads" in stats
        assert "average_rating" in stats

        # 新字段存在
        assert "rating_distribution" in stats
