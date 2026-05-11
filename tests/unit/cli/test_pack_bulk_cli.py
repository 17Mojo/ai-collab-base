"""
Pack Bulk CLI Tests
"""

from datetime import datetime
from unittest.mock import MagicMock, patch


class TestPackBulkCLI:
    """Pack Bulk CLI Tests"""

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_init(self, mock_engine_class):
        """测试 CLI 初始化"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        cli = PackBulkCLI("data/packs.db", 5)

        assert cli.engine == mock_engine
        mock_engine_class.assert_called_once_with("data/packs.db", 5)

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_create_success(self, mock_engine_class, tmp_path):
        """测试批量创建成功"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        # 创建临时 JSON 文件
        specs_file = tmp_path / "specs.json"
        specs_file.write_text(
            '[{"pack_name": "Pack1", "version": "1.0.0", "author": "user1", "category": "productivity"}]'
        )

        mock_result = MagicMock()
        mock_result.total = 1
        mock_result.succeeded = 1
        mock_result.failed = 0
        mock_result.success_rate = 100.0
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.results = []

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.bulk_create.return_value = mock_result

        cli = PackBulkCLI()
        result = cli.bulk_create(str(specs_file), True)

        assert result == 0
        mock_engine.bulk_create.assert_called_once()

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_create_file_not_found(self, mock_engine_class):
        """测试批量创建（文件不存在）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        cli = PackBulkCLI()
        result = cli.bulk_create("nonexistent.json", True)

        assert result == 1
        mock_engine.bulk_create.assert_not_called()

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_create_invalid_json(self, mock_engine_class, tmp_path):
        """测试批量创建（无效 JSON）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        # 创建无效 JSON 文件
        specs_file = tmp_path / "invalid.json"
        specs_file.write_text("{invalid json")

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        cli = PackBulkCLI()
        result = cli.bulk_create(str(specs_file), True)

        assert result == 1
        mock_engine.bulk_create.assert_not_called()

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_create_not_list(self, mock_engine_class, tmp_path):
        """测试批量创建（非列表格式）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        specs_file = tmp_path / "specs.json"
        specs_file.write_text('{"pack_name": "Pack1"}')

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        cli = PackBulkCLI()
        result = cli.bulk_create(str(specs_file), True)

        assert result == 1
        mock_engine.bulk_create.assert_not_called()

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_create_partial_failure(self, mock_engine_class, tmp_path):
        """测试批量创建（部分失败）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        specs_file = tmp_path / "specs.json"
        specs_file.write_text('[{"pack_name": "Pack1", "version": "1.0.0"}]')

        mock_result = MagicMock()
        mock_result.total = 1
        mock_result.succeeded = 0
        mock_result.failed = 1
        mock_result.success_rate = 0.0
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.results = [{"pack_id": "pack1", "success": False, "error": "Failed"}]

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.bulk_create.return_value = mock_result

        cli = PackBulkCLI()
        result = cli.bulk_create(str(specs_file), True)

        assert result == 1

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_update_version_success(self, mock_engine_class):
        """测试批量更新版本成功"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_result = MagicMock()
        mock_result.total = 2
        mock_result.succeeded = 2
        mock_result.failed = 0
        mock_result.success_rate = 100.0
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.results = []

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.bulk_update_version.return_value = mock_result

        cli = PackBulkCLI()
        result = cli.bulk_update_version("pack1,pack2", "major", True)

        assert result == 0
        mock_engine.bulk_update_version.assert_called_once()

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_update_version_invalid_bump(self, mock_engine_class):
        """测试批量更新版本（无效升级类型）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        cli = PackBulkCLI()
        result = cli.bulk_update_version("pack1,pack2", "invalid", True)

        assert result == 1
        mock_engine.bulk_update_version.assert_not_called()

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_archive_success(self, mock_engine_class):
        """测试批量归档成功"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_result = MagicMock()
        mock_result.total = 1
        mock_result.succeeded = 1
        mock_result.failed = 0
        mock_result.success_rate = 100.0
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.results = []

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.bulk_archive.return_value = mock_result

        cli = PackBulkCLI()
        result = cli.bulk_archive("pack1", True)

        assert result == 0
        mock_engine.bulk_archive.assert_called_once()

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_delete_success(self, mock_engine_class):
        """测试批量删除成功"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_result = MagicMock()
        mock_result.total = 1
        mock_result.succeeded = 1
        mock_result.failed = 0
        mock_result.success_rate = 100.0
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.results = []

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.bulk_delete.return_value = mock_result

        cli = PackBulkCLI()
        result = cli.bulk_delete("pack1", "delete_1", True)

        assert result == 0
        mock_engine.bulk_delete.assert_called_once()

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_delete_invalid_token(self, mock_engine_class):
        """测试批量删除（无效令牌）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        cli = PackBulkCLI()
        result = cli.bulk_delete("pack1,pack2", "wrong_token", True)

        assert result == 1
        mock_engine.bulk_delete.assert_not_called()

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_get_status_running(self, mock_engine_class):
        """测试获取操作状态（运行中）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_result = MagicMock()
        mock_result.total = 5
        mock_result.succeeded = 2
        mock_result.failed = 0
        mock_result.success_rate = 40.0
        mock_result.started_at = datetime.now()
        mock_result.completed_at = None
        mock_result.results = []

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_operation_status.return_value = mock_result

        cli = PackBulkCLI()
        result = cli.get_status("op123")

        assert result == 0
        mock_engine.get_operation_status.assert_called_once_with("op123")

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_get_status_completed(self, mock_engine_class):
        """测试获取操作状态（已完成）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_result = MagicMock()
        mock_result.total = 5
        mock_result.succeeded = 5
        mock_result.failed = 0
        mock_result.success_rate = 100.0
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.results = [{"pack_id": "pack1", "success": True, "version": "1.0.0"}]

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_operation_status.return_value = mock_result

        cli = PackBulkCLI()
        result = cli.get_status("op123")

        assert result == 0

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_get_status_completed_with_errors(self, mock_engine_class):
        """测试获取操作状态（带错误）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_result = MagicMock()
        mock_result.total = 5
        mock_result.succeeded = 4
        mock_result.failed = 1
        mock_result.success_rate = 80.0
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.results = [{"pack_id": "pack1", "success": False, "error": "Failed"}]

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_operation_status.return_value = mock_result

        cli = PackBulkCLI()
        result = cli.get_status("op123")

        assert result == 0

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_list_operations_with_data(self, mock_engine_class):
        """测试列出所有操作（有数据）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_all_operations.return_value = [
            {
                "operation_id": "op1",
                "operation_type": "create",
                "status": "completed",
                "total": 5,
                "created_at": "2026-04-10",
            }
        ]

        cli = PackBulkCLI()
        result = cli.list_operations()

        assert result == 0
        mock_engine.get_all_operations.assert_called_once()

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_list_operations_no_data(self, mock_engine_class):
        """测试列出所有操作（无数据）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_all_operations.return_value = []

        cli = PackBulkCLI()
        result = cli.list_operations()

        assert result == 0


class TestPackBulkCLIErrorHandling:
    """Pack Bulk CLI 错误处理测试"""

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_create_sequential(self, mock_engine_class, tmp_path):
        """测试批量创建（顺序执行）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        specs_file = tmp_path / "specs.json"
        specs_file.write_text('[{"pack_name": "Pack1"}]')

        mock_result = MagicMock()
        mock_result.total = 1
        mock_result.succeeded = 1
        mock_result.failed = 0
        mock_result.success_rate = 100.0
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.results = []

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.bulk_create.return_value = mock_result

        cli = PackBulkCLI()
        result = cli.bulk_create(str(specs_file), False)

        assert result == 0
        mock_engine.bulk_create.assert_called_once()

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_update_version_multiple(self, mock_engine_class):
        """测试批量更新版本（多个 Pack）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_result = MagicMock()
        mock_result.total = 3
        mock_result.succeeded = 3
        mock_result.failed = 0
        mock_result.success_rate = 100.0
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.results = []

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.bulk_update_version.return_value = mock_result

        cli = PackBulkCLI()
        result = cli.bulk_update_version("pack1,pack2,pack3", "minor", False)

        assert result == 0

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_delete_multiple(self, mock_engine_class):
        """测试批量删除（多个 Pack）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_result = MagicMock()
        mock_result.total = 3
        mock_result.succeeded = 3
        mock_result.failed = 0
        mock_result.success_rate = 100.0
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.results = []

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.bulk_delete.return_value = mock_result

        cli = PackBulkCLI()
        result = cli.bulk_delete("pack1,pack2,pack3", "delete_3", False)

        assert result == 0

    @patch("ai_collab.cli.pack_bulk.BulkOperationEngine")
    def test_bulk_archive_multiple(self, mock_engine_class):
        """测试批量归档（多个 Pack）"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        mock_result = MagicMock()
        mock_result.total = 2
        mock_result.succeeded = 2
        mock_result.failed = 0
        mock_result.success_rate = 100.0
        mock_result.started_at = datetime.now()
        mock_result.completed_at = datetime.now()
        mock_result.results = []

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.bulk_archive.return_value = mock_result

        cli = PackBulkCLI()
        result = cli.bulk_archive("pack1,pack2", True)

        assert result == 0


class TestPackBulkCLIMain:
    """测试 CLI main 入口"""

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_create_command(self, mock_cli_class):
        """测试 create 命令"""
        from ai_collab.cli.pack_bulk import main

        mock_cli = MagicMock()
        mock_cli.bulk_create.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_bulk.py", "create", "--specs", "/path/to/specs.json"]):
            result = main()

        assert result == 0
        mock_cli.bulk_create.assert_called_once_with("/path/to/specs.json", True)

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_create_with_no_parallel(self, mock_cli_class):
        """测试 create 命令带 --no-parallel"""
        from ai_collab.cli.pack_bulk import main

        mock_cli = MagicMock()
        mock_cli.bulk_create.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch(
            "sys.argv",
            ["pack_bulk.py", "create", "--specs", "/path/to/specs.json", "--no-parallel"],
        ):
            result = main()

        assert result == 0
        mock_cli.bulk_create.assert_called_once_with("/path/to/specs.json", False)

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_create_missing_specs(self, mock_cli_class):
        """测试 create 命令缺少 specs 参数"""
        from ai_collab.cli.pack_bulk import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_bulk.py", "create"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_no_arguments(self, mock_cli_class):
        """测试无参数调用"""
        from ai_collab.cli.pack_bulk import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_bulk.py"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_unknown_command(self, mock_cli_class):
        """测试未知命令"""
        from ai_collab.cli.pack_bulk import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_bulk.py", "unknown_cmd"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_status_command(self, mock_cli_class):
        """测试 status 命令"""
        from ai_collab.cli.pack_bulk import main

        mock_cli = MagicMock()
        mock_cli.get_status.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_bulk.py", "status", "op123"]):
            result = main()

        assert result == 0
        mock_cli.get_status.assert_called_once_with("op123")

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_list_command(self, mock_cli_class):
        """测试 list 命令"""
        from ai_collab.cli.pack_bulk import main

        mock_cli = MagicMock()
        mock_cli.list_operations.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_bulk.py", "list"]):
            result = main()

        assert result == 0
        mock_cli.list_operations.assert_called_once()

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_update_version_command(self, mock_cli_class):
        """测试 update-version 命令"""
        from ai_collab.cli.pack_bulk import main

        mock_cli = MagicMock()
        mock_cli.bulk_update_version.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch(
            "sys.argv",
            ["pack_bulk.py", "update-version", "--pack-ids", "pack1,pack2", "--bump", "minor"],
        ):
            result = main()

        assert result == 0
        mock_cli.bulk_update_version.assert_called_once()

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_update_version_missing_args(self, mock_cli_class):
        """测试 update-version 命令缺少参数"""
        from ai_collab.cli.pack_bulk import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_bulk.py", "update-version"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_archive_command(self, mock_cli_class):
        """测试 archive 命令"""
        from ai_collab.cli.pack_bulk import main

        mock_cli = MagicMock()
        mock_cli.bulk_archive.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_bulk.py", "archive", "--pack-ids", "pack1,pack2"]):
            result = main()

        assert result == 0

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_delete_command(self, mock_cli_class):
        """测试 delete 命令"""
        from ai_collab.cli.pack_bulk import main

        mock_cli = MagicMock()
        mock_cli.bulk_delete.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch(
            "sys.argv",
            ["pack_bulk.py", "delete", "--pack-ids", "old_pack", "--confirm", "delete_1"],
        ):
            result = main()

        assert result == 0
        mock_cli.bulk_delete.assert_called_once()

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_with_workers_option(self, mock_cli_class):
        """测试 --workers 选项"""
        from ai_collab.cli.pack_bulk import main

        mock_cli = MagicMock()
        mock_cli.bulk_create.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch(
            "sys.argv", ["pack_bulk.py", "create", "--specs", "/path/specs.json", "--workers", "10"]
        ):
            result = main()

        # Should be initialized with max_workers=10
        mock_cli_class.assert_called_once_with(max_workers=10)
        assert result == 0

    @patch("ai_collab.cli.pack_bulk.PackBulkCLI")
    def test_main_delete_missing_token(self, mock_cli_class):
        """测试 delete 命令缺少确认令牌"""
        from ai_collab.cli.pack_bulk import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_bulk.py", "delete", "--pack-ids", "old_pack"]):
            result = main()

        assert result == 1
