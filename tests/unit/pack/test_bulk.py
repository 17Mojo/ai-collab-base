# Pack Bulk Operations Tests
# Week 3 Day 2: Pack 批量操作测试

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from ai_collab.pack.bulk import (
    BulkOperation,
    BulkOperationEngine,
    BulkOperationResult,
    OperationStatus,
    OperationType,
)


class TestBulkOperation:
    """测试批量操作数据模型"""

    def test_bulk_operation_creation(self):
        """测试批量操作创建"""
        operation = BulkOperation(
            operation_id="test_op_001",
            operation_type=OperationType.CREATE,
            pack_ids=["pack1", "pack2", "pack3"],
        )

        assert operation.operation_id == "test_op_001"
        assert operation.operation_type == OperationType.CREATE
        assert len(operation.pack_ids) == 3
        assert operation.status == OperationStatus.PENDING
        assert len(operation.results) == 0
        assert operation.total == 3

    def test_bulk_operation_serialization(self):
        """测试批量操作序列化"""
        operation = BulkOperation(
            operation_id="test_op_002",
            operation_type=OperationType.UPDATE_VERSION,
            pack_ids=["pack1"],
            status=OperationStatus.COMPLETED,
            results=[{"pack_id": "pack1", "success": True}],
        )

        data = operation.to_dict()

        assert data["operation_id"] == "test_op_002"
        assert data["operation_type"] == "update_version"
        assert len(data["pack_ids"]) == 1
        assert data["status"] == "completed"
        assert len(data["results"]) == 1
        assert data["total"] == 1
        assert "created_at" in data
        assert "updated_at" in data

    def test_bulk_operation_deserialization(self):
        """测试批量操作反序列化"""
        data = {
            "operation_id": "test_op_003",
            "operation_type": "archive",
            "pack_ids": ["pack1", "pack2"],
            "status": "running",
            "results": [],
            "created_at": "2026-04-06T10:00:00",
            "updated_at": "2026-04-06T10:05:00",
        }

        operation = BulkOperation.from_dict(data)

        assert operation.operation_id == "test_op_003"
        assert operation.operation_type == OperationType.ARCHIVE
        assert len(operation.pack_ids) == 2
        assert operation.status == OperationStatus.RUNNING


class TestBulkOperationResult:
    """测试批量操作结果"""

    def test_bulk_operation_result_creation(self):
        """测试操作结果创建"""
        result = BulkOperationResult(operation_id="result_001", total=10, succeeded=8, failed=2)

        assert result.operation_id == "result_001"
        assert result.total == 10
        assert result.succeeded == 8
        assert result.failed == 2
        assert result.cancelled == 0
        assert result.success_rate == 80.0

    def test_success_rate_calculation(self):
        """测试成功率计算"""
        result = BulkOperationResult(operation_id="result_002", total=5, succeeded=4, failed=1)

        assert result.success_rate == 80.0

    def test_success_rate_zero_total(self):
        """测试零总数时的成功率"""
        result = BulkOperationResult(operation_id="result_003", total=0)

        assert result.success_rate == 0.0

    def test_result_serialization(self):
        """测试结果序列化"""
        result = BulkOperationResult(
            operation_id="result_004",
            total=3,
            succeeded=3,
            failed=0,
            started_at=datetime(2026, 4, 6, 10, 0, 0),
            completed_at=datetime(2026, 4, 6, 10, 1, 0),
        )

        data = result.to_dict()

        assert data["operation_id"] == "result_004"
        assert data["total"] == 3
        assert data["succeeded"] == 3
        assert data["failed"] == 0
        assert data["success_rate"] == 100.0
        assert data["started_at"] == "2026-04-06T10:00:00"
        assert data["completed_at"] == "2026-04-06T10:01:00"


class TestBulkOperationEngine:
    """测试批量操作引擎"""

    @patch("ai_collab.pack.bulk.PackMarketAPI")
    def test_engine_initialization(self, mock_api_class):
        """测试引擎初始化"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        engine = BulkOperationEngine(max_workers=3)

        assert engine.max_workers == 3
        assert isinstance(engine._operations, dict)
        assert len(engine._operations) == 0

    @patch("ai_collab.pack.bulk.PackMarketAPI")
    def test_create_operation(self, mock_api_class):
        """测试创建操作"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        engine = BulkOperationEngine()
        operation = engine.create_operation(OperationType.CREATE, ["pack1"])

        assert operation.operation_type == OperationType.CREATE
        assert len(operation.pack_ids) == 1
        assert operation.operation_id in engine._operations

    @patch("ai_collab.pack.bulk.PackMarketAPI")
    def test_get_operation(self, mock_api_class):
        """测试获取操作"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        engine = BulkOperationEngine()
        operation = engine.create_operation(OperationType.CREATE, ["pack1"])

        # 获取存在的操作
        retrieved = engine.get_operation(operation.operation_id)
        assert retrieved is not None
        assert retrieved.operation_id == operation.operation_id

        # 获取不存在的操作
        assert engine.get_operation("nonexistent") is None

    @patch("ai_collab.pack.bulk.PackMarketAPI")
    def test_bulk_create_success(self, mock_api_class):
        """测试批量创建成功"""
        mock_api = Mock()
        mock_api.create_pack.return_value = {"success": True, "pack_id": "created_pack_1"}
        mock_api_class.return_value = mock_api

        engine = BulkOperationEngine()
        pack_specs = [
            {"pack_name": "Pack 1", "version": "1.0.0"},
            {"pack_name": "Pack 2", "version": "1.0.0"},
        ]

        result = engine.bulk_create(pack_specs, parallel=False)

        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0
        assert result.success_rate == 100.0
        assert len(result.results) == 2

    @patch("ai_collab.pack.bulk.PackMarketAPI")
    def test_bulk_create_with_failures(self, mock_api_class):
        """测试批量创建带失败"""
        mock_api = Mock()

        call_count = 0

        def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"success": True, "pack_id": "pack1", "message": "Created"}
            else:
                return {"success": False, "message": "Invalid pack"}

        mock_api.create_pack.side_effect = mock_create
        mock_api_class.return_value = mock_api

        engine = BulkOperationEngine()
        pack_specs = [
            {"pack_name": "Pack 1", "version": "1.0.0"},
            {"pack_name": "Pack 2", "version": "1.0.0"},
        ]

        result = engine.bulk_create(pack_specs, parallel=False)

        assert result.total == 2
        assert result.succeeded == 1
        assert result.failed == 1
        assert result.success_rate == 50.0

    @patch("ai_collab.pack.bulk.PackMarketAPI")
    def test_bulk_update_version(self, mock_api_class):
        """测试批量更新版本"""
        mock_api = Mock()
        mock_api.get_pack.return_value = {"success": True, "pack": {"version": "1.0.0"}}
        mock_api.update_pack.return_value = {"success": True}
        mock_api_class.return_value = mock_api

        engine = BulkOperationEngine()
        result = engine.bulk_update_version(["pack1", "pack2"], "patch", parallel=False)

        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0

        # 验证版本更新
        for res in result.results:
            assert "version" in res
            assert res["version"] == "1.0.1"

    @patch("ai_collab.pack.bulk.PackMarketAPI")
    def test_bulk_archive(self, mock_api_class):
        """测试批量归档"""
        from ai_collab.pack.market import PackListing

        mock_api = Mock()
        mock_listing = PackListing(
            pack_id="pack1",
            pack_name="Test Pack",
            version="1.0.0",
            description="Test",
            author="test",
            category="test",
        )
        mock_api.store.get_listing.return_value = mock_listing
        mock_api.store.update_listing.return_value = True
        mock_api_class.return_value = mock_api

        engine = BulkOperationEngine()
        result = engine.bulk_archive(["pack1"], parallel=False)

        assert result.total == 1
        assert result.succeeded == 1
        assert result.failed == 0

    @patch("ai_collab.pack.bulk.PackMarketAPI")
    def test_bulk_delete_with_valid_token(self, mock_api_class):
        """测试批量删除有效令牌"""
        mock_api = Mock()
        from ai_collab.pack.market import PackListing

        mock_listing = PackListing(
            pack_id="pack1",
            pack_name="Test",
            version="1.0.0",
            description="Test",
            author="test",
            category="test",
        )
        mock_api.store.get_listing.return_value = mock_listing
        mock_api.delete_pack.return_value = {"success": True}
        mock_api_class.return_value = mock_api

        engine = BulkOperationEngine()
        result = engine.bulk_delete(["pack1"], confirm_token="delete_1", parallel=False)

        assert result.total == 1
        assert result.succeeded == 1
        assert result.failed == 0

    @patch("ai_collab.pack.bulk.PackMarketAPI")
    def test_bulk_delete_invalid_token(self, mock_api_class):
        """测试批量删除无效令牌"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        engine = BulkOperationEngine()
        result = engine.bulk_delete(["pack1", "pack2"], confirm_token="wrong_token", parallel=False)

        assert result.operation_id == "invalid"
        assert result.total == 2
        assert result.succeeded == 0
        assert result.failed == 0

    @patch("ai_collab.pack.bulk.PackMarketAPI")
    def test_cancel_operation(self, mock_api_class):
        """测试取消操作"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        engine = BulkOperationEngine()
        operation = engine.create_operation(OperationType.CREATE, ["pack1"])

        # 取消待处理操作
        assert engine.cancel_operation(operation.operation_id)
        assert engine.get_operation(operation.operation_id).status == OperationStatus.CANCELLED

        # 尝试取消已完成操作
        operation.status = OperationStatus.COMPLETED
        assert not engine.cancel_operation(operation.operation_id)

    @patch("ai_collab.pack.bulk.PackMarketAPI")
    def test_get_all_operations(self, mock_api_class):
        """测试获取所有操作"""
        mock_api = Mock()
        mock_api_class.return_value = mock_api

        engine = BulkOperationEngine()
        engine.create_operation(OperationType.CREATE, ["pack1"])
        engine.create_operation(OperationType.ARCHIVE, ["pack2"])

        operations = engine.get_all_operations()

        assert len(operations) == 2
        assert all("operation_id" in op for op in operations)
        assert all("operation_type" in op for op in operations)


class TestBulkCLI:
    """测试批量操作 CLI"""

    def test_cli_bulk_create(self):
        """测试 CLI 批量创建"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        # 创建真实的 Mock 对象，需要属性访问
        mock_result = type(
            "MockResult",
            (),
            {
                "total": 3,
                "succeeded": 3,
                "failed": 0,
                "completed_at": datetime.now(),
                "started_at": datetime.now(),
                "results": [],
                "success_rate": 100.0,
            },
        )()

        mock_engine = Mock()
        mock_engine.bulk_create.return_value = mock_result

        # 创建临时规格文件
        specs = [
            {"pack_name": "Test Pack 1", "version": "1.0.0"},
            {"pack_name": "Test Pack 2", "version": "1.0.0"},
            {"pack_name": "Test Pack 3", "version": "1.0.0"},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(specs, f)
            specs_path = f.name

        try:
            with patch("ai_collab.cli.pack_bulk.BulkOperationEngine", return_value=mock_engine):
                cli = PackBulkCLI()
                result = cli.bulk_create(specs_path, parallel=False)

            assert result == 0  # 成功返回 0
            mock_engine.bulk_create.assert_called_once()
        finally:
            Path(specs_path).unlink()

    def test_cli_bulk_update_version(self):
        """测试 CLI 批量更新版本"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        # 创建真实的 Mock 对象，需要属性访问
        mock_result = type(
            "MockResult",
            (),
            {
                "total": 2,
                "succeeded": 2,
                "failed": 0,
                "completed_at": datetime.now(),
                "started_at": datetime.now(),
                "results": [],
                "success_rate": 100.0,
            },
        )()

        mock_engine = Mock()
        mock_engine.bulk_update_version.return_value = mock_result

        with patch("ai_collab.cli.pack_bulk.BulkOperationEngine", return_value=mock_engine):
            cli = PackBulkCLI()
            result = cli.bulk_update_version("pack1,pack2", "patch", parallel=False)

        assert result == 0
        mock_engine.bulk_update_version.assert_called_once_with(["pack1", "pack2"], "patch", False)

    def test_cli_bulk_delete_invalid_token(self):
        """测试 CLI 批量删除无效令牌"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_engine = Mock()
        mock_engine.bulk_delete.return_value = Mock(
            operation_id="invalid", total=2, succeeded=0, failed=0, success_rate=0.0
        )

        with patch("ai_collab.cli.pack_bulk.BulkOperationEngine", return_value=mock_engine):
            cli = PackBulkCLI()
            result = cli.bulk_delete("pack1,pack2", "wrong_token", parallel=False)

        assert result == 1  # 失败返回 1

    def test_cli_get_status(self):
        """测试 CLI 获取状态"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        # 创建真实的 Mock 对象，需要属性访问
        mock_result = type(
            "MockResult",
            (),
            {
                "operation_id": "test_op",
                "total": 5,
                "succeeded": 4,
                "failed": 1,
                "started_at": datetime(2026, 4, 6, 10, 0, 0),
                "completed_at": datetime(2026, 4, 6, 10, 1, 0),
                "success_rate": 80.0,
                "results": [
                    {"pack_id": "p1", "success": True},
                    {"pack_id": "p2", "success": False},
                ],
            },
        )()

        mock_engine = Mock()
        mock_engine.get_operation_status.return_value = mock_result

        with patch("ai_collab.cli.pack_bulk.BulkOperationEngine", return_value=mock_engine):
            cli = PackBulkCLI()
            result = cli.get_status("test_op")

        assert result == 0
        mock_engine.get_operation_status.assert_called_once_with("test_op")
