"""
Pack Dependency CLI Full Test Suite
Comprehensive tests for pack_dependency.py CLI module
Uses modular test framework for consistent patterns
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import framework utilities
sys.path.insert(0, str(Path(__file__).parent))
from base_cli_test import assert_failure, assert_success


class TestPackDependencyCLIInit:
    """Test PackDependencyCLI initialization"""

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_init_default_db(self, mock_resolver_class, mock_api_class):
        """Test initialization with default database path"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.list_packs.return_value = {"packs": []}

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        PackDependencyCLI()

        mock_api_class.assert_called_once_with("data/packs.db")
        mock_api.list_packs.assert_called_once_with(status="approved")

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_init_custom_db(self, mock_resolver_class, mock_api_class):
        """Test initialization with custom database path"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.list_packs.return_value = {"packs": []}

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        PackDependencyCLI("/custom/path.db")

        mock_api_class.assert_called_once_with("/custom/path.db")

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_load_registry(self, mock_resolver_class, mock_api_class):
        """Test loading version registry from database"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.list_packs.return_value = {
            "packs": [
                {"pack_id": "lib1", "version": "1.0.0"},
                {"pack_id": "lib2", "version": "2.0.0"},
            ]
        }

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        PackDependencyCLI()

        # Verify resolver.register_version was called for each pack
        assert mock_resolver.register_version.call_count == 2
        mock_resolver.register_version.assert_any_call("lib1", "1.0.0")
        mock_resolver.register_version.assert_any_call("lib2", "2.0.0")


class TestPackDependencyCLIAddDependency:
    """Test add_dependency method"""

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_add_dependency_success(self, mock_resolver_class, mock_api_class):
        """Test successfully adding a new dependency"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_id": "test_pack", "version": "1.0.0", "dependencies": []},
        }
        mock_api.update_pack_version.return_value = {"success": True}
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        compatible = MagicMock()
        compatible.__str__return_value = "1.0.0"
        mock_resolver._find_compatible_version.return_value = compatible
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI()
        result = cli.add_dependency(pack_id="test_pack", dep_name="lib1", version_range="^1.0.0")

        assert_success(result)
        mock_resolver._find_compatible_version.assert_called_once_with("lib1", "^1.0.0")
        mock_api.update_pack_version.assert_called_once()

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_add_dependency_optional_with_reason(self, mock_resolver_class, mock_api_class):
        """Test adding an optional dependency with reason"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_id": "test_pack", "version": "1.0.0", "dependencies": []},
        }
        mock_api.update_pack_version.return_value = {"success": True}
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        compatible = MagicMock()
        compatible.__str__return_value = "2.0.0"
        mock_resolver._find_compatible_version.return_value = compatible
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI()
        result = cli.add_dependency(
            pack_id="test_pack",
            dep_name="lib2",
            version_range="^2.0.0",
            optional=True,
            reason="For advanced features",
        )

        assert_success(result)

        # Verify the dependency was added with correct attributes
        call_args = mock_api.update_pack_version.call_args
        dependencies = call_args[1]["dependencies"]
        assert len(dependencies) == 1
        assert dependencies[0]["optional"] is True
        assert dependencies[0]["reason"] == "For advanced features"

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_add_dependency_pack_not_found(self, mock_resolver_class, mock_api_class):
        """Test adding dependency to non-existent pack"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = None
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI()
        result = cli.add_dependency("nonexistent", "lib1", "^1.0.0")

        assert_failure(result)

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_add_dependency_no_compatible_version(self, mock_resolver_class, mock_api_class):
        """Test adding dependency when no compatible version found"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_id": "test_pack", "version": "1.0.0", "dependencies": []},
        }
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver._find_compatible_version.return_value = None
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI()
        result = cli.add_dependency("test_pack", "lib1", "^5.0.0")

        assert_failure(result)

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_add_dependency_update_existing(self, mock_resolver_class, mock_api_class):
        """Test updating an existing dependency"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {
                "pack_id": "test_pack",
                "version": "1.0.0",
                "dependencies": [
                    {"name": "lib1", "version_range": "^1.0.0", "optional": False, "reason": ""}
                ],
            },
        }
        mock_api.update_pack_version.return_value = {"success": True}
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        compatible = MagicMock()
        compatible.__str__return_value = "2.0.0"
        mock_resolver._find_compatible_version.return_value = compatible
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI()
        result = cli.add_dependency(
            pack_id="test_pack",
            dep_name="lib1",
            version_range="^2.0.0",
            optional=True,
            reason="New version",
        )

        assert_success(result)

        # Verify existing dependency was updated
        call_args = mock_api.update_pack_version.call_args
        dependencies = call_args[1]["dependencies"]
        assert len(dependencies) == 1
        assert dependencies[0]["version_range"] == "^2.0.0"
        assert dependencies[0]["optional"] is True

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_add_dependency_api_failure(self, mock_resolver_class, mock_api_class):
        """Test handling API failure during dependency addition"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_id": "test_pack", "version": "1.0.0", "dependencies": []},
        }
        mock_api.update_pack_version.return_value = {"success": False, "error": "Database error"}
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        compatible = MagicMock()
        mock_resolver._find_compatible_version.return_value = compatible
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI()
        result = cli.add_dependency("test_pack", "lib1", "^1.0.0")

        assert_failure(result)


class TestPackDependencyCLIListDependencies:
    """Test list_dependencies method"""

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    def test_list_dependencies_with_data(self, mock_api_class):
        """Test listing dependencies when pack has dependencies"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {
                "pack_id": "test_pack",
                "dependencies": [
                    {
                        "name": "lib1",
                        "version_range": "^1.0.0",
                        "optional": False,
                        "reason": "Core",
                    },
                    {
                        "name": "lib2",
                        "version_range": "^2.0.0",
                        "optional": True,
                        "reason": "Optional",
                    },
                ],
            },
        }
        mock_api_class.return_value = mock_api

        cli = PackDependencyCLI("data/packs.db")
        result = cli.list_dependencies("test_pack")

        assert_success(result)
        mock_api.get_pack.assert_called_once_with("test_pack")

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    def test_list_dependencies_empty(self, mock_api_class):
        """Test listing dependencies when pack has none"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_id": "test_pack", "dependencies": []},
        }
        mock_api_class.return_value = mock_api

        cli = PackDependencyCLI("data/packs.db")
        result = cli.list_dependencies("test_pack")

        assert_success(result)

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    def test_list_dependencies_pack_not_found(self, mock_api_class):
        """Test listing dependencies for non-existent pack"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = None
        mock_api_class.return_value = mock_api

        cli = PackDependencyCLI("data/packs.db")
        result = cli.list_dependencies("nonexistent")

        assert_failure(result)


class TestPackDependencyCLIResolveDependencies:
    """Test resolve_dependencies method"""

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_resolve_dependencies_success(self, mock_resolver_class, mock_api_class):
        """Test successful dependency resolution"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {
                "pack_id": "test_pack",
                "version": "1.0.0",
                "dependencies": [{"name": "lib1", "version_range": "^1.0.0"}],
            },
        }
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolve_result = MagicMock()
        mock_resolve_result.success = True
        mock_resolve_result.resolved = []
        mock_resolver.resolve.return_value = mock_resolve_result
        mock_resolver.get_install_order.return_value = ["test_pack", "lib1"]
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI("data/packs.db")
        result = cli.resolve_dependencies("test_pack")

        assert_success(result)
        mock_resolver.resolve.assert_called_once()
        mock_resolver.get_install_order.assert_called_once()

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_resolve_dependencies_pack_not_found(self, mock_resolver_class, mock_api_class):
        """Test resolving dependencies for non-existent pack"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = None
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI("data/packs.db")
        result = cli.resolve_dependencies("nonexistent")

        assert_failure(result)

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_resolve_dependencies_failure(self, mock_resolver_class, mock_api_class):
        """Test failed dependency resolution"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {
                "pack_id": "test_pack",
                "version": "1.0.0",
                "dependencies": [{"name": "lib1", "version_range": "^1.0.0"}],
            },
        }
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolve_result = MagicMock()
        mock_resolve_result.success = False
        mock_resolve_result.conflicts = [{"reason": "Version conflict", "pack": "lib1"}]
        mock_resolve_result.errors = ["Cannot satisfy version constraint"]
        mock_resolver.resolve.return_value = mock_resolve_result
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI("data/packs.db")
        result = cli.resolve_dependencies("test_pack")

        assert_failure(result)

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_resolve_dependencies_no_dependencies(self, mock_resolver_class, mock_api_class):
        """Test resolving dependencies when pack has none"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_id": "test_pack", "version": "1.0.0", "dependencies": []},
        }
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolve_result = MagicMock()
        mock_resolve_result.success = True
        mock_resolve_result.resolved = []
        mock_resolver.resolve.return_value = mock_resolve_result
        mock_resolver.get_install_order.return_value = ["test_pack"]
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI("data/packs.db")
        result = cli.resolve_dependencies("test_pack")

        assert_success(result)


class TestPackDependencyCLIRemoveDependency:
    """Test remove_dependency method"""

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    def test_remove_dependency_success(self, mock_api_class):
        """Test successfully removing a dependency"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        # Note: the CLI expects get_pack to return the pack object directly,
        # not wrapped in {"success": True, "pack": {...}}
        mock_api.get_pack.return_value = {
            "pack_id": "test_pack",
            "version": "1.0.0",
            "dependencies": [{"name": "lib1", "version_range": "^1.0.0", "optional": False}],
        }
        mock_api.update_pack_version.return_value = {"success": True}
        mock_api_class.return_value = mock_api

        cli = PackDependencyCLI("data/packs.db")
        result = cli.remove_dependency("test_pack", "lib1")

        assert_success(result)

        # Verify the dependency was removed
        call_args = mock_api.update_pack_version.call_args
        dependencies = call_args[1]["dependencies"]
        assert len(dependencies) == 0
        assert not any(dep.get("name") == "lib1" for dep in dependencies)

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    def test_remove_dependency_not_found(self, mock_api_class):
        """Test removing a dependency that doesn't exist"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_id": "test_pack", "version": "1.0.0", "dependencies": []},
        }
        mock_api.update_pack_version.return_value = {"success": True}
        mock_api_class.return_value = mock_api

        cli = PackDependencyCLI("data/packs.db")
        result = cli.remove_dependency("test_pack", "lib1")

        assert_failure(result)

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    def test_remove_dependency_pack_not_found(self, mock_api_class):
        """Test removing dependency from non-existent pack"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = None
        mock_api_class.return_value = mock_api

        cli = PackDependencyCLI("data/packs.db")
        result = cli.remove_dependency("nonexistent", "lib1")

        assert_failure(result)

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    def test_remove_dependency_api_failure(self, mock_api_class):
        """Test handling API failure during dependency removal"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {
                "pack_id": "test_pack",
                "version": "1.0.0",
                "dependencies": [{"name": "lib1", "version_range": "^1.0.0"}],
            },
        }
        mock_api.update_pack_version.return_value = {"success": False, "error": "Database error"}
        mock_api_class.return_value = mock_api

        cli = PackDependencyCLI("data/packs.db")
        result = cli.remove_dependency("test_pack", "lib1")

        assert_failure(result)


class TestPackDependencyCLICheckConflicts:
    """Test check_conflicts method"""

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_check_conflicts_no_conflicts(self, mock_resolver_class, mock_api_class):
        """Test conflict detection when no conflicts exist"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {
                "pack_id": "test_pack",
                "version": "1.0.0",
                "dependencies": [{"name": "lib1", "version_range": "^1.0.0"}],
            },
        }
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver.detect_conflicts.return_value = []
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI("data/packs.db")
        result = cli.check_conflicts("test_pack")

        assert_success(result)
        mock_resolver.detect_conflicts.assert_called_once()

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_check_conflicts_with_conflicts(self, mock_resolver_class, mock_api_class):
        """Test conflict detection when conflicts are found"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {
                "pack_id": "test_pack",
                "version": "1.0.0",
                "dependencies": [{"name": "lib1", "version_range": "^1.0.0"}],
            },
        }
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver.detect_conflicts.return_value = [
            {
                "reason": "Version conflict",
                "pack": "lib1",
                "conflicting_ranges": ["^1.0.0", "^2.0.0"],
            }
        ]
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI("data/packs.db")
        result = cli.check_conflicts("test_pack")

        assert_failure(result)

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_check_conflicts_pack_not_found(self, mock_resolver_class, mock_api_class):
        """Test checking conflicts for non-existent pack"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = None
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI("data/packs.db")
        result = cli.check_conflicts("nonexistent")

        assert_failure(result)


class TestPackDependencyCLIMain:
    """Test CLI main entry point"""

    @patch("sys.argv", ["pack_dependency.py"])
    def test_main_no_arguments(self):
        """Test main with no arguments"""
        from ai_collab.cli.pack_dependency import main

        result = main()
        assert result == 1

    @patch("sys.argv", ["pack_dependency.py", "invalid_command", "test_pack"])
    def test_main_invalid_command(self):
        """Test main with invalid command"""
        from ai_collab.cli.pack_dependency import main

        result = main()
        assert result == 1

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_main_list_command(self, mock_resolver_class, mock_api_class):
        """Test main with list command"""
        from ai_collab.cli.pack_dependency import main

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_id": "test_pack", "dependencies": []},
        }
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        with patch("sys.argv", ["pack_dependency.py", "list", "test_pack"]):
            result = main()
            assert result == 0

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_main_add_command_missing_args(self, mock_resolver_class, mock_api_class):
        """Test main with add command but missing arguments"""
        from ai_collab.cli.pack_dependency import main

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        with patch("sys.argv", ["pack_dependency.py", "add", "test_pack"]):
            result = main()
            assert result == 1


class TestPackDependencyCLIMainFull:
    """Test CLI main entry point - full coverage"""

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_main_add_command_full(self, mock_resolver_class, mock_api_class):
        """Test main add command with all options - lines 370-392"""
        from ai_collab.cli.pack_dependency import main

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_id": "test_pack", "version": "1.0.0", "dependencies": []},
        }
        mock_api.update_pack_version.return_value = {"success": True}
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        with patch(
            "sys.argv",
            [
                "pack_dependency.py",
                "add",
                "test_pack",
                "lib1",
                "--version",
                "^1.0.0",
                "--optional",
                "--reason",
                "Required for feature X",
            ],
        ):
            result = main()
            assert result == 0

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_main_add_command_version_only(self, mock_resolver_class, mock_api_class):
        """Test main add command with version only"""
        from ai_collab.cli.pack_dependency import main

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_id": "test_pack", "version": "1.0.0", "dependencies": []},
        }
        mock_api.update_pack_version.return_value = {"success": True}
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        with patch(
            "sys.argv", ["pack_dependency.py", "add", "test_pack", "lib1", "--version", "^1.0.0"]
        ):
            result = main()
            assert result == 0

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_main_resolve_command(self, mock_resolver_class, mock_api_class):
        """Test main resolve command - lines 401-404"""
        from ai_collab.cli.pack_dependency import main

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_id": "test_pack", "version": "1.0.0", "dependencies": []},
        }
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolve_result = MagicMock()
        mock_resolve_result.success = True
        mock_resolve_result.resolved = []
        mock_resolver.resolve.return_value = mock_resolve_result
        mock_resolver.get_install_order.return_value = ["test_pack"]
        mock_resolver_class.return_value = mock_resolver

        with patch("sys.argv", ["pack_dependency.py", "resolve", "test_pack"]):
            result = main()
            assert result == 0

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_main_resolve_missing_args(self, mock_resolver_class, mock_api_class):
        """Test main resolve command missing args"""
        from ai_collab.cli.pack_dependency import main

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        with patch("sys.argv", ["pack_dependency.py", "resolve"]):
            result = main()
            assert result == 1

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_main_remove_command(self, mock_resolver_class, mock_api_class):
        """Test main remove command - lines 407-410"""
        from ai_collab.cli.pack_dependency import main

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "pack_id": "test_pack",
            "version": "1.0.0",
            "dependencies": [{"name": "lib1", "version_range": "^1.0.0"}],
        }
        mock_api.update_pack_version.return_value = {"success": True}
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        with patch("sys.argv", ["pack_dependency.py", "remove", "test_pack", "lib1"]):
            result = main()
            assert result == 0

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_main_remove_missing_args(self, mock_resolver_class, mock_api_class):
        """Test main remove command missing args"""
        from ai_collab.cli.pack_dependency import main

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        with patch("sys.argv", ["pack_dependency.py", "remove", "test_pack"]):
            result = main()
            assert result == 1

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_main_check_command(self, mock_resolver_class, mock_api_class):
        """Test main check command - lines 413-416"""
        from ai_collab.cli.pack_dependency import main

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "success": True,
            "pack": {"pack_id": "test_pack", "version": "1.0.0", "dependencies": []},
        }
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver.detect_conflicts.return_value = []
        mock_resolver_class.return_value = mock_resolver

        with patch("sys.argv", ["pack_dependency.py", "check", "test_pack"]):
            result = main()
            assert result == 0

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_main_check_missing_args(self, mock_resolver_class, mock_api_class):
        """Test main check command missing args"""
        from ai_collab.cli.pack_dependency import main

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        with patch("sys.argv", ["pack_dependency.py", "check"]):
            result = main()
            assert result == 1

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_main_list_missing_args(self, mock_resolver_class, mock_api_class):
        """Test main list command missing args - line 396-397"""
        from ai_collab.cli.pack_dependency import main

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        with patch("sys.argv", ["pack_dependency.py", "list"]):
            result = main()
            assert result == 1

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_main_unknown_command(self, mock_resolver_class, mock_api_class):
        """Test main with unknown command - lines 418-421"""
        from ai_collab.cli.pack_dependency import main

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        with patch("sys.argv", ["pack_dependency.py", "unknown", "test_pack"]):
            result = main()
            assert result == 1


class TestPackDependencyCLIUpdateExisting:
    """Test updating existing dependency - lines 104-112"""

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_update_existing_dependency(self, mock_resolver_class, mock_api_class):
        """Test updating an existing dependency - lines 104-112"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "pack_id": "test_pack",
            "version": "1.0.0",
            "dependencies": [
                {"name": "lib1", "version_range": "^1.0.0", "optional": False, "reason": ""}
            ],
        }
        mock_api.update_pack_version.return_value = {"success": True}
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver._find_compatible_version.return_value = MagicMock(version="1.2.0")
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI()
        result = cli.add_dependency("test_pack", "lib1", "^2.0.0", False, "Updated reason")

        assert_success(result)


class TestPackDependencyCLIListOutput:
    """Test list dependencies output - lines 159-171"""

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_list_dependencies_with_multiple_deps(self, mock_resolver_class, mock_api_class):
        """Test listing multiple dependencies with output - lines 159-171"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "pack_id": "test_pack",
            "version": "1.0.0",
            "dependencies": [
                {
                    "name": "lib1",
                    "version_range": "^1.0.0",
                    "optional": False,
                    "reason": "Required",
                },
                {"name": "lib2", "version_range": "^2.0.0", "optional": True, "reason": "Optional"},
                {"name": "lib3", "version_range": "^3.0.0", "optional": False, "reason": ""},
            ],
        }
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI()
        result = cli.list_dependencies("test_pack")

        assert_success(result)


class TestPackDependencyCLIRemoveOutput:
    """Test remove dependency output - lines 276, 292-293"""

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    def test_remove_dependency_success_message(self, mock_api_class):
        """Test remove dependency success message - line 276"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "pack_id": "test_pack",
            "version": "1.0.0",
            "dependencies": [{"name": "lib1", "version_range": "^1.0.0", "optional": False}],
        }
        mock_api.update_pack_version.return_value = {"success": True}
        mock_api_class.return_value = mock_api

        cli = PackDependencyCLI()
        result = cli.remove_dependency("test_pack", "lib1")

        assert_success(result)

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    def test_remove_dependency_failure_message(self, mock_api_class):
        """Test remove dependency failure message - lines 292-293"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "pack_id": "test_pack",
            "version": "1.0.0",
            "dependencies": [{"name": "lib1", "version_range": "^1.0.0", "optional": False}],
        }
        mock_api.update_pack_version.return_value = {"success": False, "error": "Database error"}
        mock_api_class.return_value = mock_api

        cli = PackDependencyCLI()
        result = cli.remove_dependency("test_pack", "lib1")

        assert_failure(result)


class TestPackDependencyCLIResolveOutput:
    """Test resolve dependencies output - lines 201-211, 232-237"""

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_resolve_with_resolved_deps_output(self, mock_resolver_class, mock_api_class):
        """Test resolve with resolved dependencies output - lines 232-237"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "pack_id": "test_pack",
            "version": "1.0.0",
            "dependencies": [{"name": "lib1", "version_range": "^1.0.0"}],
        }
        mock_api_class.return_value = mock_api

        mock_resolved = MagicMock()
        mock_resolved.name = "lib1"
        mock_resolved.version = "1.2.0"
        mock_resolved.source = "registry"

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.resolved = [mock_resolved]

        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = mock_result
        mock_resolver.get_install_order.return_value = ["lib1", "test_pack"]
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI()
        result = cli.resolve_dependencies("test_pack")

        assert_success(result)

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_resolve_with_errors_output(self, mock_resolver_class, mock_api_class):
        """Test resolve with errors output - lines 201-211"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "pack_id": "test_pack",
            "version": "1.0.0",
            "dependencies": [{"name": "lib1", "version_range": "^1.0.0"}],
        }
        mock_api_class.return_value = mock_api

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.conflicts = [{"pack": "lib1", "reason": "Version conflict"}]
        mock_result.errors = ["Cannot find compatible version"]

        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = mock_result
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI()
        result = cli.resolve_dependencies("test_pack")

        assert_failure(result)


class TestPackDependencyCLICheckConflictsOutput:
    """Test check conflicts output - lines 323-330"""

    @patch("ai_collab.cli.pack_dependency.PackMarketAPI")
    @patch("ai_collab.cli.pack_dependency.DependencyResolver")
    def test_check_conflicts_with_conflict_details(self, mock_resolver_class, mock_api_class):
        """Test check conflicts with detailed conflict output - lines 323-330"""
        from ai_collab.cli.pack_dependency import PackDependencyCLI

        mock_api = MagicMock()
        mock_api.get_pack.return_value = {
            "pack_id": "test_pack",
            "version": "1.0.0",
            "dependencies": [
                {"name": "lib1", "version_range": "^1.0.0"},
                {"name": "lib2", "version_range": "^2.0.0"},
            ],
        }
        mock_api_class.return_value = mock_api

        mock_resolver = MagicMock()
        mock_resolver.detect_conflicts.return_value = [
            {
                "pack": "lib1",
                "reason": "Version conflict between ^1.0.0 and ^2.0.0",
                "conflicting_ranges": ["^1.0.0", "^2.0.0"],
            },
            {"pack": "lib2", "reason": "Circular dependency detected", "conflicting_ranges": []},
        ]
        mock_resolver_class.return_value = mock_resolver

        cli = PackDependencyCLI()
        result = cli.check_conflicts("test_pack")

        assert_failure(result)
