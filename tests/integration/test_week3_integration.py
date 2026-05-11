# Week 3 Integration Tests
# Pack Import/Export + Context Search End-to-End Tests

import json
import tempfile
from pathlib import Path

from ai_collab.context.aggregator import ContextAggregator
from ai_collab.context.search import ContextSearchEngine, SearchMethod
from ai_collab.pack.importer import ExportFormat, PackExporter, PackImporter
from ai_collab.pack.market import PackListing, PackStatus
from ai_collab.pack.market_api import PackMarketAPI


class TestPackImportExportIntegration:
    """Pack 导入导出集成测试"""

    def test_full_import_export_cycle(self):
        """测试完整的导入导出周期"""
        # 1. 创建原始 Pack
        original_pack = PackListing(
            pack_id="integration_test_001",
            pack_name="Integration Test Pack",
            version="1.0.0",
            description="Testing full import/export cycle",
            author="test_engineer",
            category="testing",
            tags=["integration", "test"],
            status=PackStatus.APPROVED,
        )

        # 2. 导出到 JSON
        exporter = PackExporter()
        export = exporter.export_pack(original_pack, export_format=ExportFormat.JSON)

        # 3. 转换为字典
        export_data = export.to_dict()

        # 4. 从字典导入
        importer = PackImporter()
        import_result = importer.import_from_dict(export_data)

        # 验证导入
        assert import_result.success
        assert import_result.pack_id == "integration_test_001"
        assert len(import_result.errors) == 0

        # 5. 重建 PackListing
        imported_pack = PackListing.from_dict(export_data["pack"])

        # 6. 验证数据一致性
        assert imported_pack.pack_id == original_pack.pack_id
        assert imported_pack.pack_name == original_pack.pack_name
        assert imported_pack.version == original_pack.version
        assert imported_pack.author == original_pack.author
        assert imported_pack.category == original_pack.category

    def test_import_with_database_integration(self):
        """测试导入与数据库集成"""
        # 创建测试数据库
        db_path = "data/test_integration.db"
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # 初始化 API
        api = PackMarketAPI(db_path)

        # 创建 Pack 数据
        pack_data = {
            "schema_version": "2.0",
            "export_date": "2026-04-07",
            "format": "json",
            "pack": {
                "pack_id": "db_integration_001",
                "pack_name": "DB Integration Pack",
                "version": "1.0.0",
                "description": "Testing database integration",
                "author": "test_engineer",
                "category": "testing",
                "tags": ["db", "integration"],
            },
            "dependencies": [],
            "versions": [],
        }

        # 通过 importer 验证
        importer = PackImporter()
        validation_result = importer.import_from_dict(pack_data)

        assert validation_result.success

        # 通过 API 创建
        create_result = api.create_pack(
            pack_name="DB Integration Pack",
            version="1.0.0",
            description="Testing database integration",
            author="test_engineer",
            category="testing",
            tags=["db", "integration"],
        )

        assert create_result["success"]

        # 验证 Pack 可查询
        get_result = api.get_pack(create_result["pack_id"])
        assert get_result["success"]
        assert get_result["pack"]["pack_name"] == "DB Integration Pack"

        # 清理
        Path(db_path).unlink(missing_ok=True)

    def test_yaml_export_file_roundtrip(self):
        """测试 YAML 文件导出的往返"""
        original_pack = PackListing(
            pack_id="yaml_test_001",
            pack_name="YAML Test Pack",
            version="1.0.0",
            description="Testing YAML export",
            author="test",
            category="test",
        )

        exporter = PackExporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            # 导出到 YAML 文件
            yaml_path = Path(tmpdir) / "test_pack.yaml"
            exporter.export_to_file(original_pack, str(yaml_path))

            # 验证文件存在
            assert yaml_path.exists()

            # 读取并验证内容
            content = yaml_path.read_text(encoding="utf-8")
            assert "pack_id: yaml_test_001" in content
            assert "pack_name: YAML Test Pack" in content

            # 通过 importer 导入
            importer = PackImporter()
            import_result = importer.import_from_file(str(yaml_path))

            assert import_result.success
            assert import_result.pack_id == "yaml_test_001"

    def test_batch_import_export_integration(self):
        """测试批量导入导出集成"""
        # 创建多个 Packs
        packs = [
            PackListing(
                pack_id=f"batch_test_{i:03d}",
                pack_name=f"Batch Test Pack {i}",
                version="1.0.0",
                description=f"Test pack {i}",
                author="test",
                category="test",
            )
            for i in range(5)
        ]

        exporter = PackExporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "exports"
            output_dir.mkdir()

            # 批量导出
            export_results = exporter.bulk_export(packs, str(output_dir), ExportFormat.JSON)

            # 验证导出结果
            assert len(export_results) == 5
            assert all(export_results.values())

            # 验证文件存在
            for i in range(5):
                file_path = output_dir / f"batch_test_{i:03d}.json"
                assert file_path.exists()

            # 批量导入
            importer = PackImporter()
            file_paths = [str(output_dir / f"batch_test_{i:03d}.json") for i in range(5)]
            import_results = importer.bulk_import(file_paths)

            # 验证导入结果
            assert len(import_results) == 5
            assert all(r.success for r in import_results)


class TestContextSearchIntegration:
    """Context Search 集成测试"""

    def test_search_with_empty_aggregator(self):
        """测试空聚合器的搜索"""
        aggregator = ContextAggregator()

        # 创建搜索引擎
        search_engine = ContextSearchEngine(aggregator)

        # 执行搜索（应该返回空结果）
        results, stats = search_engine.search("test")

        # 验证搜索结果
        assert isinstance(results, list)
        assert len(results) == 0

    def test_multiple_search_methods_integration(self):
        """测试多种搜索方法的集成"""
        aggregator = ContextAggregator()

        # 添加测试上下文
        aggregator.extract_knowledge(source_type="api", content="Python 编程语言", confidence=0.9)
        aggregator.extract_knowledge(source_type="api", content="JavaScript 前端开发", confidence=0.85)

        search_engine = ContextSearchEngine(aggregator)

        # 测试所有搜索方法
        methods = [
            SearchMethod.SEMANTIC,
            SearchMethod.KEYWORD,
            SearchMethod.HYBRID,
            SearchMethod.GRAPH,
        ]

        for method in methods:
            results, stats = search_engine.search("python", method=method)
            assert stats.method == method
            assert isinstance(results, list)

    def test_search_with_filters_integration(self):
        """测试搜索与过滤器的集成"""
        aggregator = ContextAggregator()

        # 添加不同置信度的上下文
        aggregator.extract_knowledge(source_type="api", content="高置信度内容 Python", confidence=0.9)
        aggregator.extract_knowledge(source_type="api", content="低置信度内容 python", confidence=0.4)

        search_engine = ContextSearchEngine(aggregator)

        # 测试不同过滤器
        results_high, _ = search_engine.search("python")
        results_filtered, _ = search_engine.search("python", min_score=0.7)

        # 验证过滤器效果
        for result in results_filtered:
            assert result.score >= 0.7


class TestCrossModuleIntegration:
    """跨模块集成测试"""

    def test_export_pack_simple(self):
        """测试简单 Pack 导出"""
        pack = PackListing(
            pack_id="simple_pack",
            pack_name="Simple Pack",
            version="1.0.0",
            description="Simple pack test",
            author="test",
            category="test",
        )

        # 导出
        exporter = PackExporter()
        export = exporter.export_pack(pack, export_format=ExportFormat.JSON)

        export_data = export.to_dict()

        # 验证导出的 Pack 数据包含 tags
        assert "tags" in export_data["pack"]


class TestEndToEndWorkflow:
    """端到端工作流测试"""

    def test_multi_format_pack_workflow(self):
        """测试多格式 Pack 工作流"""
        pack = PackListing(
            pack_id="multi_format_pack",
            pack_name="Multi Format Pack",
            version="1.0.0",
            description="Testing multiple formats",
            author="test",
            category="test",
        )

        exporter = PackExporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            # 导出为 JSON
            json_path = Path(tmpdir) / "pack.json"
            exporter.export_to_file(pack, str(json_path))

            # 导出为 YAML
            yaml_path = Path(tmpdir) / "pack.yaml"
            exporter.export_to_file(pack, str(yaml_path))

            # 验证两个文件存在
            assert json_path.exists()
            assert yaml_path.exists()

            # 从两种格式导入
            importer = PackImporter()
            json_result = importer.import_from_file(str(json_path))
            yaml_result = importer.import_from_file(str(yaml_path))

            # 验证两个导入都成功
            assert json_result.success
            assert yaml_result.success

            # 验证数据一致性
            assert json_result.pack_id == yaml_result.pack_id


class TestQualityAndPerformance:
    """质量和性能测试"""

    def test_batch_import_performance(self):
        """测试批量导入性能"""
        import time

        # 创建大量 Pack 数据
        packs_data = []
        for i in range(50):
            pack_data = {
                "schema_version": "2.0",
                "pack": {
                    "pack_id": f"perf_test_{i:03d}",
                    "pack_name": f"Performance Test Pack {i}",
                    "version": "1.0.0",
                    "description": f"Test pack {i}",
                    "author": "test",
                    "category": "performance",
                },
                "dependencies": [],
                "versions": [],
            }
            packs_data.append(pack_data)

        # 写入文件
        importer = PackImporter()
        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i, pack_data in enumerate(packs_data):
                file_path = Path(tmpdir) / f"pack_{i}.json"
                file_path.write_text(json.dumps(pack_data), encoding="utf-8")
                files.append(str(file_path))

            # 测量批量导入时间
            start = time.time()
            results = importer.bulk_import(files)
            elapsed = time.time() - start

            # 应该在合理时间内完成 (< 2 秒)
            assert elapsed < 2.0
            assert len(results) == 50

    def test_data_consistency_across_operations(self):
        """测试跨操作数据一致性"""
        pack = PackListing(
            pack_id="consistency_pack",
            pack_name="Consistency Pack",
            version="1.0.0",
            description="Testing data consistency",
            author="test",
            category="test",
            tags=["consistency", "test"],
        )

        # 导出
        exporter = PackExporter()
        export = exporter.export_pack(pack)

        # 转换为字典并验证
        export_dict = export.to_dict()
        pack_dict = PackListing.to_dict(pack)

        # 验证关键字段一致
        assert export_dict["pack"]["pack_id"] == pack_dict["pack_id"]
        assert export_dict["pack"]["pack_name"] == pack_dict["pack_name"]
        assert export_dict["pack"]["version"] == pack_dict["version"]

        # 从字典重建
        imported_pack = PackListing.from_dict(export_dict["pack"])

        # 验证重建后一致
        assert imported_pack.pack_id == pack.pack_id
        assert imported_pack.pack_name == pack.pack_name
        assert imported_pack.tags == pack.tags
