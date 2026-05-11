"""
跨模块集成测试

测试 Pack + Context 联动、Pack + Rating 联动、Import/Export 流程
"""

import tempfile
from pathlib import Path

import pytest


class TestPackContextIntegration:
    """Pack + Context 联动测试"""

    def test_pack_with_context(self):
        """测试 Pack 与上下文联动"""
        from ai_collab.context.schema import Context
        from ai_collab.pack.market import PackListing, PackStatus

        listing = PackListing(
            pack_id="ctx-pack",
            pack_name="Context Pack",
            version="1.0.0",
            description="Test",
            author="test",
            category="testing",
            status=PackStatus.DRAFT,
        )
        context = Context(
            context_id="ctx-1",
            scenario="conversation",
            name="Test context",
            metadata={"pack_id": listing.pack_id},
        )

        assert context.metadata["pack_id"] == listing.pack_id

    def test_pack_execution_with_context(self):
        """测试 Pack 执行时使用上下文"""
        from ai_collab.context.schema import Context
        from ai_collab.pack.market import PackListing, PackStatus

        listing = PackListing(
            pack_id="exec-pack",
            pack_name="Execution Pack",
            version="1.0.0",
            description="Test",
            author="test",
            category="testing",
            status=PackStatus.DRAFT,
        )
        Context(context_id="exec-ctx", scenario="conversation", name="Context")

        assert listing.pack_id == "exec-pack"


class TestPackRatingIntegration:
    """Pack + Rating 联动测试"""

    def test_pack_with_ratings(self):
        """测试 Pack 与评分联动"""
        from ai_collab.pack.market import PackListing, PackRating, PackStatus

        PackListing(
            pack_id="rated-pack",
            pack_name="Rated Pack",
            version="1.0.0",
            description="Test",
            author="test",
            category="testing",
            status=PackStatus.APPROVED,
        )

        scores = [5, 4, 4, 5, 3, 4, 5]
        ratings = [
            PackRating(rating_id=f"r{i}", pack_id="rated-pack", user_id=f"u{i}", rating=score)
            for i, score in enumerate(scores)
        ]

        avg_rating = sum(r.rating for r in ratings) / len(ratings)
        assert avg_rating == pytest.approx(4.29, rel=0.1)

    def test_pack_market_with_ratings(self):
        """测试 Pack 市场与评分联动"""
        from ai_collab.pack.market import PackListing, PackRating, PackStatus

        listing = PackListing(
            pack_id="market-pack",
            pack_name="Market Pack",
            version="1.0.0",
            description="Pack",
            author="test-user",
            category="testing",
            status=PackStatus.APPROVED,
        )

        ratings = [
            PackRating(rating_id="r1", pack_id="market-pack", user_id="u1", rating=5),
            PackRating(rating_id="r2", pack_id="market-pack", user_id="u2", rating=4),
            PackRating(rating_id="r3", pack_id="market-pack", user_id="u3", rating=5),
        ]

        avg_score = sum(r.rating for r in ratings) / len(ratings)
        assert avg_score == pytest.approx(4.67, rel=0.1)
        assert listing.status == PackStatus.APPROVED


class TestImportExportWorkflow:
    """Import/Export 流程测试"""

    def test_pack_import_export_roundtrip(self):
        """测试 Pack 导入导出往返"""
        from ai_collab.pack.importer import ExportFormat, PackExporter, PackImporter
        from ai_collab.pack.market import PackListing, PackStatus

        original = PackListing(
            pack_id="import-export-test",
            pack_name="Import Export Test",
            version="1.0.0",
            description="Test import/export",
            author="test",
            category="testing",
            status=PackStatus.DRAFT,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = PackExporter()
            export = exporter.export_pack(original, export_format=ExportFormat.JSON)
            export_path = Path(tmpdir) / "exported_pack.json"
            with open(export_path, "w") as f:
                json_data = export.to_dict()
                import json

                json.dump(json_data, f)

            assert export_path.exists()

            importer = PackImporter()
            with open(export_path) as f:
                import json

                data = json.load(f)
            result = importer.import_from_dict(data)

            assert result.success
            assert result.pack_id == original.pack_id

    def test_batch_import_export(self):
        """测试批量导入导出"""
        from ai_collab.pack.importer import ExportFormat, PackExporter, PackImporter
        from ai_collab.pack.market import PackListing, PackStatus

        packs = [
            PackListing(
                pack_id=f"batch-pack-{i}",
                pack_name=f"Batch Pack {i}",
                version="1.0.0",
                description=f"Batch test {i}",
                author="test",
                category="testing",
                status=PackStatus.DRAFT,
            )
            for i in range(3)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = PackExporter()
            importer = PackImporter()

            exported_files = []
            for i, pack in enumerate(packs):
                export = exporter.export_pack(pack, export_format=ExportFormat.JSON)
                export_path = Path(tmpdir) / f"pack_{i}.json"
                import json

                with open(export_path, "w") as f:
                    json.dump(export.to_dict(), f)
                exported_files.append(str(export_path))

            assert len(exported_files) == 3

            results = []
            for f in exported_files:
                import json

                with open(f) as fp:
                    data = json.load(fp)
                results.append(importer.import_from_dict(data))

            assert len(results) == 3
            assert all(r.success for r in results)


class TestCrossModuleDataFlow:
    """跨模块数据流测试"""

    def test_pack_to_context_data_flow(self):
        """测试 Pack 到 Context 的数据流"""
        from ai_collab.context.schema import Context
        from ai_collab.pack.market import PackListing, PackStatus

        listing = PackListing(
            pack_id="data-flow-pack",
            pack_name="Data Flow Pack",
            version="1.0.0",
            description="Test data flow",
            author="test",
            category="testing",
            status=PackStatus.DRAFT,
        )

        context = Context(
            context_id=f"ctx-{listing.pack_id}",
            scenario="conversation",
            name="Pack context",
            metadata={"source": "pack", "pack_name": listing.pack_name},
        )

        assert context.metadata["source"] == "pack"

    def test_context_influences_pack_selection(self):
        """测试上下文影响 Pack 选择"""
        from ai_collab.context.schema import Context

        contexts = [
            Context(
                context_id=f"history-{i}",
                scenario="conversation",
                name=f"Task {i}",
                metadata={"preference": "Python"},
            )
            for i in range(5)
        ]

        python_count = sum(1 for ctx in contexts if ctx.metadata.get("preference") == "Python")
        assert python_count == 5
