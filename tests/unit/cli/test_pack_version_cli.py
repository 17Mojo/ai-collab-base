"""
Pack Version CLI Tests
"""

from datetime import datetime
from unittest.mock import MagicMock, patch


class TestPackVersionCLI:
    """Pack Version CLI Tests"""

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_init(self, mock_manager_class, mock_api_class):
        """测试 CLI 初始化"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_path_instance = MagicMock()

        with patch("ai_collab.cli.pack_version.Path") as mock_path_class:
            mock_path_class.return_value = mock_path_instance

            mock_api = MagicMock()
            mock_api_class.return_value = mock_api

            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            cli = PackVersionCLI()

            assert cli.api == mock_api
            assert cli.manager == mock_manager
            mock_path_instance.mkdir.assert_called_once_with(exist_ok=True)

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_init_with_custom_manager(self, mock_manager_class, mock_api_class):
        """测试 CLI 初始化（自定义管理器）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        custom_manager = MagicMock()

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        cli = PackVersionCLI(manager=custom_manager)

        assert cli.manager == custom_manager
        mock_manager_class.assert_not_called()

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_list_versions_with_data(self, mock_manager_class, mock_api_class):
        """测试列出版本（有数据）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_name": "Test Pack", "version": "1.0.0"},
        }

        mock_version_history = MagicMock()
        mock_version_history.version = MagicMock()
        mock_version_history.version.__str__return_value = "1.0.0"
        mock_version_history.created_at = datetime.now()
        mock_version_history.created_by = "test_user"
        mock_version_history.changelog = "Initial release"

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.list_versions.return_value = [mock_version_history]

        cli = PackVersionCLI()
        result = cli.list_versions("test_pack")

        assert result == 0
        mock_api.get_pack.assert_called_once_with("test_pack")
        mock_manager.list_versions.assert_called_once_with("test_pack")

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_list_versions_no_data(self, mock_manager_class, mock_api_class):
        """测试列出版本（无数据）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.get_pack.return_value = {"success": False, "error": "Pack not found"}

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.list_versions.return_value = []

        cli = PackVersionCLI()
        result = cli.list_versions("nonexistent")

        assert result == 0

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_bump_version_success(self, mock_manager_class, mock_api_class):
        """测试升级版本成功"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_name": "Test Pack", "version": "1.0.0"},
        }

        mock_new_version = MagicMock()
        mock_new_version.__str__return_value = "1.1.0"

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.create_version.return_value = mock_new_version

        cli = PackVersionCLI()
        result = cli.bump_version("test_pack", "minor", "Added new features")

        assert result == 0
        mock_api.get_pack.assert_called_once_with("test_pack")
        mock_manager.create_version.assert_called_once()

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_bump_version_pack_not_found(self, mock_manager_class, mock_api_class):
        """测试升级版本（Pack 不存在）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.get_pack.return_value = {"success": False, "error": "Pack not found"}

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        cli = PackVersionCLI()
        result = cli.bump_version("nonexistent", "minor", "Test")

        assert result == 1
        mock_manager.create_version.assert_not_called()

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_bump_version_invalid_type(self, mock_manager_class, mock_api_class):
        """测试升级版本（无效类型）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_name": "Test", "version": "1.0.0"},
        }

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        cli = PackVersionCLI()
        result = cli.bump_version("test_pack", "invalid", "Test")

        assert result == 1
        mock_manager.create_version.assert_not_called()

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_show_version_found(self, mock_manager_class, mock_api_class):
        """测试显示版本详情（找到）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_version = MagicMock()
        mock_version.major = 1
        mock_version.minor = 0
        mock_version.patch = 0
        mock_version.prerelease = None
        mock_version.build_metadata = None

        mock_history = MagicMock()
        mock_history.version = mock_version
        mock_history.created_at = datetime.now()
        mock_history.created_by = "test_user"
        mock_history.changelog = "Test release"

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_version.return_value = mock_history

        cli = PackVersionCLI()
        result = cli.show_version("test_pack", "1.0.0")

        assert result == 0
        mock_manager.get_version.assert_called_once_with("test_pack", "1.0.0")

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_show_version_not_found(self, mock_manager_class, mock_api_class):
        """测试显示版本详情（未找到）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_version.return_value = None

        cli = PackVersionCLI()
        result = cli.show_version("test_pack", "nonexistent")

        assert result == 0

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_rollback_version_success(self, mock_manager_class, mock_api_class):
        """测试回滚版本成功"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_target = MagicMock()
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_version.return_value = mock_target
        mock_manager.get_latest_version.return_value = MagicMock()
        mock_manager.rollback_version.return_value = True

        cli = PackVersionCLI()
        result = cli.rollback_version("test_pack", "1.0.0")

        assert result == 0
        mock_manager.get_version.assert_called_once_with("test_pack", "1.0.0")
        mock_manager.rollback_version.assert_called_once_with("test_pack", "1.0.0")

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_rollback_version_not_found(self, mock_manager_class, mock_api_class):
        """测试回滚版本（目标版本不存在）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_version.return_value = None

        cli = PackVersionCLI()
        result = cli.rollback_version("test_pack", "nonexistent")

        assert result == 1
        mock_manager.rollback_version.assert_not_called()

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_compare_versions_equal(self, mock_manager_class, mock_api_class):
        """测试比较版本（相等）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_v1 = MagicMock()
        mock_v1.compare.return_value = 0
        mock_v1.__str__return_value = "1.0.0"

        mock_v2 = MagicMock()
        mock_v2.__str__return_value = "1.0.0"

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.calculate_distance.return_value = 0

        with patch("ai_collab.cli.pack_version.PackVersion") as mock_version_class:
            mock_version_class.from_string.side_effect = [mock_v1, mock_v2]

            cli = PackVersionCLI()
            result = cli.compare("1.0.0", "1.0.0")

            assert result == 0

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_compare_versions_greater(self, mock_manager_class, mock_api_class):
        """测试比较版本（大于）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_v1 = MagicMock()
        mock_v1.compare.return_value = 1
        mock_v1.__str__return_value = "2.0.0"

        mock_v2 = MagicMock()
        mock_v2.__str__return_value = "1.0.0"

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.calculate_distance.return_value = 1

        with patch("ai_collab.cli.pack_version.PackVersion") as mock_version_class:
            mock_version_class.from_string.side_effect = [mock_v1, mock_v2]

            cli = PackVersionCLI()
            result = cli.compare("2.0.0", "1.0.0")

            assert result == 0

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_show_latest_with_version(self, mock_manager_class, mock_api_class):
        """测试显示最新版本（有版本）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_latest = MagicMock()
        mock_latest.__str__return_value = "1.0.0"

        mock_version = MagicMock()
        mock_version.major = 1
        mock_version.minor = 0
        mock_version.patch = 0
        mock_version.prerelease = None
        mock_version.build_metadata = None

        mock_history = MagicMock()
        mock_history.version = mock_version
        mock_history.created_at = datetime.now()
        mock_history.created_by = "test_user"
        mock_history.changelog = "Initial release"

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_latest_version.return_value = mock_latest
        mock_manager.get_version.return_value = mock_history

        cli = PackVersionCLI()
        result = cli.show_latest("test_pack")

        assert result == 0
        mock_manager.get_latest_version.assert_called_once_with("test_pack")

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_show_latest_no_version(self, mock_manager_class, mock_api_class):
        """测试显示最新版本（无版本）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_latest_version.return_value = None

        cli = PackVersionCLI()
        result = cli.show_latest("test_pack")

        assert result == 0


class TestPackVersionCLIErrorHandling:
    """Pack Version CLI 错误处理测试"""

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_bump_version_all_types(self, mock_manager_class, mock_api_class):
        """测试所有版本类型"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_name": "Test", "version": "1.0.0"},
        }

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.create_version.return_value = MagicMock()

        cli = PackVersionCLI()

        # 测试所有类型
        for vtype in ["major", "minor", "patch"]:
            result = cli.bump_version("test_pack", vtype, f"Test {vtype}")
            assert result == 0

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_list_versions_multiple(self, mock_manager_class, mock_api_class):
        """测试列出版本（多个版本）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_name": "Test", "version": "1.2.0"},
        }

        mock_versions = []
        for i in range(3):
            mock_v = MagicMock()
            mock_v.version = MagicMock()
            mock_v.version.__str__return_value = f"1.{i}.0"
            mock_v.created_at = datetime.now()
            mock_v.created_by = f"user{i}"
            mock_v.changelog = f"Version {i}"
            mock_versions.append(mock_v)

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.list_versions.return_value = mock_versions

        cli = PackVersionCLI()
        result = cli.list_versions("test_pack")

        assert result == 0
        assert mock_manager.list_versions.called

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_rollback_version_failure(self, mock_manager_class, mock_api_class):
        """测试回滚版本失败"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_target = MagicMock()
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_version.return_value = mock_target
        mock_manager.get_latest_version.return_value = MagicMock()
        mock_manager.rollback_version.return_value = False

        cli = PackVersionCLI()
        result = cli.rollback_version("test_pack", "1.0.0")

        assert result == 1

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_compare_versions_less_than(self, mock_manager_class, mock_api_class):
        """测试比较版本（小于）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_v1 = MagicMock()
        mock_v1.compare.return_value = -1
        mock_v1.__str__return_value = "0.9.0"

        mock_v2 = MagicMock()
        mock_v2.__str__return_value = "1.0.0"

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.calculate_distance.return_value = 1

        with patch("ai_collab.cli.pack_version.PackVersion") as mock_version_class:
            mock_version_class.from_string.side_effect = [mock_v1, mock_v2]

            cli = PackVersionCLI()
            result = cli.compare("0.9.0", "1.0.0")

            assert result == 0


class TestPackVersionCLIPrereleaseAndBuild:
    """测试预发布版本和构建元数据 - 覆盖 lines 173, 175"""

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_show_version_with_prerelease(self, mock_manager_class, mock_api_class):
        """测试显示预发布版本 - 覆盖 line 173"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_version = MagicMock()
        mock_version.major = 2
        mock_version.minor = 0
        mock_version.patch = 0
        mock_version.prerelease = "beta.1"
        mock_version.build_metadata = None

        mock_history = MagicMock()
        mock_history.version = mock_version
        mock_history.created_at = datetime.now()
        mock_history.created_by = "dev"
        mock_history.changelog = "Beta release"

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_version.return_value = mock_history

        cli = PackVersionCLI()
        result = cli.show_version("test_pack", "2.0.0-beta.1")

        assert result == 0
        mock_manager.get_version.assert_called_once_with("test_pack", "2.0.0-beta.1")

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_show_version_with_build_metadata(self, mock_manager_class, mock_api_class):
        """测试显示带构建元数据的版本 - 覆盖 line 175"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_version = MagicMock()
        mock_version.major = 1
        mock_version.minor = 5
        mock_version.patch = 0
        mock_version.prerelease = None
        mock_version.build_metadata = "build.123"

        mock_history = MagicMock()
        mock_history.version = mock_version
        mock_history.created_at = datetime.now()
        mock_history.created_by = "ci"
        mock_history.changelog = "Automated build"

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_version.return_value = mock_history

        cli = PackVersionCLI()
        result = cli.show_version("test_pack", "1.5.0+build.123")

        assert result == 0
        mock_manager.get_version.assert_called_once_with("test_pack", "1.5.0+build.123")

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_show_version_with_all_metadata(self, mock_manager_class, mock_api_class):
        """测试显示带全部元数据的版本"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_version = MagicMock()
        mock_version.major = 3
        mock_version.minor = 0
        mock_version.patch = 0
        mock_version.prerelease = "rc.1"
        mock_version.build_metadata = "20260413"

        mock_history = MagicMock()
        mock_history.version = mock_version
        mock_history.created_at = datetime.now()
        mock_history.created_by = "release_manager"
        mock_history.changelog = "Release candidate"

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_version.return_value = mock_history

        cli = PackVersionCLI()
        result = cli.show_version("test_pack", "3.0.0-rc.1+20260413")

        assert result == 0


class TestPackVersionCLIRollbackDetails:
    """测试回滚版本详细信息"""

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_rollback_version_no_current_version(self, mock_manager_class, mock_api_class):
        """测试回滚（当前版本未知）"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_target = MagicMock()
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_version.return_value = mock_target
        mock_manager.get_latest_version.return_value = None  # No current version
        mock_manager.rollback_version.return_value = True

        cli = PackVersionCLI()
        result = cli.rollback_version("test_pack", "1.0.0")

        assert result == 0
        mock_manager.get_latest_version.assert_called_once_with("test_pack")

    @patch("ai_collab.cli.pack_version.PackMarketAPI")
    @patch("ai_collab.cli.pack_version.VersionManager")
    def test_rollback_version_to_same(self, mock_manager_class, mock_api_class):
        """测试回滚到相同版本"""
        from ai_collab.cli.pack_version import PackVersionCLI

        mock_version = MagicMock()
        mock_version.__str__return_value = "1.5.0"

        mock_target = MagicMock()
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.get_version.return_value = mock_target
        mock_manager.get_latest_version.return_value = mock_version
        mock_manager.rollback_version.return_value = True

        cli = PackVersionCLI()
        result = cli.rollback_version("test_pack", "1.5.0")

        assert result == 0


class TestPackVersionCLIMain:
    """测试 CLI main() 入口 - 覆盖 lines 279-342, 346"""

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_no_arguments(self, mock_cli_class):
        """测试无参数调用"""
        from ai_collab.cli.pack_version import main

        with patch("sys.argv", ["pack_version.py", "list"]):
            result = main()

        # Need at least 3 args (command + list + pack_id)
        assert result == 1

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_short_arguments(self, mock_cli_class):
        """测试参数不足 (< 3)"""
        from ai_collab.cli.pack_version import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_version.py"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_unknown_command(self, mock_cli_class):
        """测试未知命令"""
        from ai_collab.cli.pack_version import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_version.py", "unknown", "pack1"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_list_command(self, mock_cli_class):
        """测试 list 命令"""
        from ai_collab.cli.pack_version import main

        mock_cli = MagicMock()
        mock_cli.list_versions.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_version.py", "list", "pack1"]):
            result = main()

        assert result == 0
        mock_cli.list_versions.assert_called_once_with("pack1")

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_list_missing_arg(self, mock_cli_class):
        """测试 list 命令缺少参数"""
        from ai_collab.cli.pack_version import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_version.py", "list"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_bump_command(self, mock_cli_class):
        """测试 bump 命令"""
        from ai_collab.cli.pack_version import main

        mock_cli = MagicMock()
        mock_cli.bump_version.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_version.py", "bump", "pack1", "minor", "New features"]):
            result = main()

        assert result == 0
        mock_cli.bump_version.assert_called_once_with("pack1", "minor", "New features")

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_bump_missing_args(self, mock_cli_class):
        """测试 bump 命令缺少参数"""
        from ai_collab.cli.pack_version import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_version.py", "bump", "pack1"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_show_command(self, mock_cli_class):
        """测试 show 命令"""
        from ai_collab.cli.pack_version import main

        mock_cli = MagicMock()
        mock_cli.show_version.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_version.py", "show", "pack1", "1.5.0"]):
            result = main()

        assert result == 0
        mock_cli.show_version.assert_called_once_with("pack1", "1.5.0")

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_show_missing_args(self, mock_cli_class):
        """测试 show 命令缺少参数"""
        from ai_collab.cli.pack_version import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_version.py", "show", "pack1"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_rollback_command(self, mock_cli_class):
        """测试 rollback 命令"""
        from ai_collab.cli.pack_version import main

        mock_cli = MagicMock()
        mock_cli.rollback_version.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_version.py", "rollback", "pack1", "1.0.0"]):
            result = main()

        assert result == 0
        mock_cli.rollback_version.assert_called_once_with("pack1", "1.0.0")

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_rollback_missing_args(self, mock_cli_class):
        """测试 rollback 命令缺少参数"""
        from ai_collab.cli.pack_version import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_version.py", "rollback", "pack1"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_compare_command(self, mock_cli_class):
        """测试 compare 命令"""
        from ai_collab.cli.pack_version import main

        mock_cli = MagicMock()
        mock_cli.compare.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_version.py", "compare", "1.5.0", "2.0.0"]):
            result = main()

        assert result == 0
        mock_cli.compare.assert_called_once_with("1.5.0", "2.0.0")

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_compare_missing_args(self, mock_cli_class):
        """测试 compare 命令缺少参数"""
        from ai_collab.cli.pack_version import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_version.py", "compare", "1.5.0"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_latest_command(self, mock_cli_class):
        """测试 latest 命令"""
        from ai_collab.cli.pack_version import main

        mock_cli = MagicMock()
        mock_cli.show_latest.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_version.py", "latest", "pack1"]):
            result = main()

        assert result == 0
        mock_cli.show_latest.assert_called_once_with("pack1")

    @patch("ai_collab.cli.pack_version.PackVersionCLI")
    def test_main_latest_missing_arg(self, mock_cli_class):
        """测试 latest 命令缺少参数"""
        from ai_collab.cli.pack_version import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_version.py", "latest"]):
            result = main()

        assert result == 1
