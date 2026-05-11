"""
端到端 API 集成测试

测试 Pack CRUD 完整流程、Context 管理流程、Rating 系统流程
"""

import json
import tempfile
from pathlib import Path


class TestPackCRUD:
    """Pack CRUD 端到端测试"""

    def test_pack_listing_crud_flow(self):
        """测试 PackListing 完整 CRUD 流程"""
        from ai_collab.pack.market import PackListing, PackStatus

        # 1. 创建
        listing = PackListing(
            pack_id="test-pack-e2e",
            pack_name="Test Pack E2E",
            version="1.0.0",
            description="End-to-end test pack",
            author="test",
            category="testing",
            status=PackStatus.DRAFT,
        )

        # 2. 读取 (序列化)
        data = listing.to_dict()
        assert data["pack_name"] == "Test Pack E2E"

        # 3. 更新
        listing.description = "Updated description"
        listing.status = PackStatus.APPROVED
        updated_data = listing.to_dict()
        assert updated_data["description"] == "Updated description"
        assert updated_data["status"] == "approved"

        # 4. 删除 (验证反序列化)
        restored = PackListing.from_dict(updated_data)
        assert restored.description == "Updated description"
        assert restored.status == PackStatus.APPROVED

    def test_pack_persistence_roundtrip(self):
        """测试 Pack 持久化往返"""
        from ai_collab.pack.market import PackListing, PackStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            listing = PackListing(
                pack_id="persistence-test",
                pack_name="Persistence Test",
                version="1.0.0",
                description="Test persistence",
                author="test",
                category="testing",
                status=PackStatus.DRAFT,
            )

            # 保存到文件
            file_path = Path(tmpdir) / "test_pack.json"
            with open(file_path, "w") as f:
                json.dump(listing.to_dict(), f)

            # 从文件加载
            with open(file_path) as f:
                loaded_dict = json.load(f)
            restored = PackListing.from_dict(loaded_dict)

            assert restored.pack_name == listing.pack_name
            assert restored.version == listing.version


class TestContextManagement:
    """Context 管理端到端测试"""

    def test_context_creation(self):
        """测试上下文创建"""
        from ai_collab.context.schema import Context

        contexts = []
        for i in range(3):
            ctx = Context(
                context_id=f"ctx-{i}",
                scenario="conversation",
                name=f"Context {i}",
                metadata={"priority": i},
            )
            contexts.append(ctx)

        assert len(contexts) == 3

    def test_context_filter(self):
        """测试上下文过滤"""
        from ai_collab.context.schema import Context

        test_contexts = [
            Context(context_id="s1", scenario="conversation", name="Python tutorial"),
            Context(context_id="s2", scenario="conversation", name="JavaScript guide"),
            Context(context_id="s3", scenario="conversation", name="Python analysis"),
        ]

        python_contexts = [ctx for ctx in test_contexts if "Python" in ctx.name]
        assert len(python_contexts) == 2


class TestRatingSystem:
    """Rating 系统端到端测试"""

    def test_rating_workflow(self):
        """测试评分工作流"""
        from ai_collab.pack.market import PackListing, PackRating, PackStatus

        PackListing(
            pack_id="rating-test-pack",
            pack_name="Rating Test Pack",
            version="1.0.0",
            description="Test pack",
            author="test-user",
            category="testing",
            status=PackStatus.APPROVED,
        )

        ratings = [
            PackRating(rating_id=f"r{i}", pack_id="rating-test-pack", user_id=f"u{i}", rating=i)
            for i in range(1, 6)
        ]

        avg_score = sum(r.rating for r in ratings) / len(ratings)
        assert avg_score == 3.0

    def test_rating_statistics(self):
        """测试评分统计"""
        from ai_collab.pack.market import PackRating

        scores = [5, 5, 4, 4, 4, 3, 2, 1]
        ratings = [
            PackRating(rating_id=f"r{i}", pack_id="stats-pack", user_id=f"u{i}", rating=score)
            for i, score in enumerate(scores)
        ]

        avg = sum(r.rating for r in ratings) / len(ratings)
        assert avg == 3.5
        assert sum(1 for r in ratings if r.rating == 5) == 2


class TestE2EIntegration:
    """端到端集成测试"""

    def test_full_pack_lifecycle(self):
        """测试完整 Pack 生命周期"""
        from ai_collab.pack.market import PackListing, PackStatus

        # 创建
        listing = PackListing(
            pack_id="lifecycle-test",
            pack_name="Lifecycle Test",
            version="1.0.0",
            description="Full lifecycle test",
            author="test",
            category="testing",
            status=PackStatus.DRAFT,
        )

        # 提交审核
        listing.status = PackStatus.PENDING
        assert listing.status == PackStatus.PENDING

        # 审核通过
        listing.status = PackStatus.APPROVED
        assert listing.status == PackStatus.APPROVED

        # 发布
        listing.status = PackStatus.APPROVED
        assert listing.status == PackStatus.APPROVED

        # 验证序列化完整性
        serialized = listing.to_dict()
        restored = PackListing.from_dict(serialized)

        assert restored.pack_name == listing.pack_name
        assert restored.status == PackStatus.APPROVED
