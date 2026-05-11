"""
性能基准测试

测试批量操作性能、并发处理
"""

import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


class TestBulkOperationsPerformance:
    """批量操作性能测试"""

    def test_bulk_pack_creation_performance(self):
        """测试批量 Pack 创建性能"""
        from ai_collab.pack.market import PackListing, PackStatus

        start_time = time.time()
        packs = [
            PackListing(
                pack_id=f"perf-pack-{i}",
                pack_name=f"Pack {i}",
                version="1.0.0",
                description="Test",
                author="test",
                category="testing",
                status=PackStatus.DRAFT,
            )
            for i in range(100)
        ]
        elapsed = time.time() - start_time

        assert elapsed < 1.0, f"Bulk creation took {elapsed:.3f}s"
        assert len(packs) == 100

    def test_bulk_serialization_performance(self):
        """测试批量序列化性能"""
        from ai_collab.pack.market import PackListing, PackStatus

        packs = [
            PackListing(
                pack_id=f"serial-pack-{i}",
                pack_name=f"Pack {i}",
                version="1.0.0",
                description="Test",
                author="test",
                category="testing",
                status=PackStatus.DRAFT,
            )
            for i in range(50)
        ]

        start_time = time.time()
        serialized = [pack.to_dict() for pack in packs]
        elapsed = time.time() - start_time

        assert elapsed < 0.5, f"Bulk serialization took {elapsed:.3f}s"
        assert len(serialized) == 50

    def test_bulk_deserialization_performance(self):
        """测试批量反序列化性能"""
        from ai_collab.pack.market import PackListing, PackStatus

        dicts = [
            PackListing(
                pack_id=f"deserial-pack-{i}",
                pack_name=f"Pack {i}",
                version="1.0.0",
                description="Test",
                author="test",
                category="testing",
                status=PackStatus.DRAFT,
            ).to_dict()
            for i in range(50)
        ]

        start_time = time.time()
        packs = [PackListing.from_dict(d) for d in dicts]
        elapsed = time.time() - start_time

        assert elapsed < 0.5, f"Bulk deserialization took {elapsed:.3f}s"
        assert len(packs) == 50


class TestConcurrentOperations:
    """并发处理测试"""

    def test_concurrent_pack_creation(self):
        """测试并发 Pack 创建"""
        from ai_collab.pack.market import PackListing, PackStatus

        def create_pack(index):
            return PackListing(
                pack_id=f"concurrent-pack-{index}",
                pack_name=f"Pack {index}",
                version="1.0.0",
                description="Test",
                author="test",
                category="testing",
                status=PackStatus.DRAFT,
            )

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(create_pack, i) for i in range(20)]
            packs = [future.result() for future in as_completed(futures)]
        elapsed = time.time() - start_time

        assert len(packs) == 20
        assert elapsed < 1.0, f"Concurrent creation took {elapsed:.3f}s"

    def test_concurrent_context_operations(self):
        """测试并发上下文操作"""
        from ai_collab.context.schema import Context

        def create_context(index):
            return Context(
                context_id=f"ctx-{index}", scenario="conversation", name=f"Context {index}"
            )

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(create_context, i) for i in range(50)]
            contexts = [future.result() for future in as_completed(futures)]
        elapsed = time.time() - start_time

        assert len(contexts) == 50
        assert elapsed < 2.0, f"Concurrent context took {elapsed:.3f}s"

    def test_concurrent_file_operations(self):
        """测试并发文件操作"""
        from ai_collab.pack.importer import ExportFormat, PackExporter
        from ai_collab.pack.market import PackListing, PackStatus

        with tempfile.TemporaryDirectory() as tmpdir:

            def write_pack(index):
                pack = PackListing(
                    pack_id=f"file-pack-{index}",
                    pack_name=f"Pack {index}",
                    version="1.0.0",
                    description="Test",
                    author="test",
                    category="testing",
                    status=PackStatus.DRAFT,
                )
                exporter = PackExporter()
                export = exporter.export_pack(pack, export_format=ExportFormat.JSON)
                file_path = Path(tmpdir) / f"pack_{index}.json"
                import json

                with open(file_path, "w") as f:
                    json.dump(export.to_dict(), f)
                return file_path

            start_time = time.time()
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(write_pack, i) for i in range(20)]
                file_paths = [future.result() for future in as_completed(futures)]
            time.time() - start_time

            assert len(file_paths) == 20
            assert all(p.exists() for p in file_paths)


class TestMemoryEfficiency:
    """内存效率测试"""

    def test_pack_serialization_efficiency(self):
        """测试 Pack 序列化效率"""
        from ai_collab.pack.market import PackListing, PackStatus

        pack = PackListing(
            pack_id="large-pack",
            pack_name="Large Pack",
            version="1.0.0",
            description="Test",
            author="test",
            category="testing",
            status=PackStatus.DRAFT,
        )

        start_time = time.time()
        serialized = pack.to_dict()
        elapsed = time.time() - start_time

        assert serialized["pack_name"] == "Large Pack"
        assert elapsed < 0.01, f"Serialization took {elapsed:.3f}s"

    def test_context_creation_efficiency(self):
        """测试上下文创建效率"""
        from ai_collab.context.schema import Context

        start_time = time.time()
        contexts = [
            Context(context_id=f"ctx-{i}", scenario="conversation", name=f"Content {i}")
            for i in range(1000)
        ]
        elapsed = time.time() - start_time

        assert len(contexts) == 1000
        assert elapsed < 2.0, f"Creating 1000 contexts took {elapsed:.3f}s"


class TestSearchPerformance:
    """搜索性能测试"""

    def test_context_filter_performance(self):
        """测试上下文过滤性能"""
        from ai_collab.context.schema import Context

        contexts = [
            Context(context_id=f"ctx-{i}", scenario="conversation", name=f"Python tutorial {i}")
            for i in range(500)
        ]

        start_time = time.time()
        python_contexts = [ctx for ctx in contexts if "Python" in ctx.name]
        elapsed = time.time() - start_time

        assert elapsed < 0.1, f"Filter took {elapsed:.3f}s"
        assert len(python_contexts) == 500

    def test_pack_filter_performance(self):
        """测试 Pack 过滤性能"""
        from ai_collab.pack.market import PackListing, PackStatus

        packs = [
            PackListing(
                pack_id=f"filter-pack-{i}",
                pack_name=f"Pack {i}",
                version="1.0.0",
                description="Test",
                author="test",
                category="testing" if i % 2 == 0 else "workflow",
                status=PackStatus.DRAFT,
            )
            for i in range(200)
        ]

        start_time = time.time()
        testing_packs = [p for p in packs if p.category == "testing"]
        elapsed = time.time() - start_time

        assert len(testing_packs) == 100
        assert elapsed < 0.1, f"Filter took {elapsed:.3f}s"
