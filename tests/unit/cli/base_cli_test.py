"""
Base CLI Test Framework - Fixture-Based Version
Modular base class for standardized CLI testing across all Pack CLI modules
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class BaseCLITestMixin:
    """Base mixin for CLI tests providing common patterns and utilities"""

    # Override in subclasses
    cli_module_path = None  # e.g., 'ai_collab.cli.pack_rating'
    cli_class_name = None  # e.g., 'PackRatingCLI'
    command_name = None  # e.g., 'pack_rating'

    @pytest.fixture
    def cli_class(self):
        """Get the CLI class being tested"""
        if not self.cli_module_path or not self.cli_class_name:
            raise NotImplementedError("Subclass must define cli_module_path and cli_class_name")
        from importlib import import_module

        module = import_module(self.cli_module_path)
        return getattr(module, self.cli_class_name)

    def mock_api_success(self, **kwargs):
        """Create a mock API with default success responses"""
        mock = MagicMock()
        mock.create_pack.return_value = {"success": True, "pack_id": "test_pack"}
        mock.get_pack.return_value = {
            "success": True,
            "pack": {
                "pack_id": "test_pack",
                "pack_name": "Test Pack",
                "version": "1.0.0",
                "status": "approved",
            },
        }
        mock.update_pack.return_value = {"success": True}
        mock.delete_pack.return_value = {"success": True}
        mock.list_packs.return_value = {"packs": []}
        mock.get_market_stats.return_value = {"success": True, "stats": {"total_packs": 10}}
        # Override with provided kwargs
        for key, value in kwargs.items():
            setattr(mock, key, value)
        return mock

    def mock_operation_result(self, total=1, succeeded=1, failed=0, success_rate=100.0):
        """Create a mock bulk operation result"""
        result = MagicMock()
        result.total = total
        result.succeeded = succeeded
        result.failed = failed
        result.success_rate = success_rate
        result.started_at = datetime.now()
        result.completed_at = datetime.now() if succeeded > 0 else None
        result.results = []
        return result

    def mock_bulk_operation_result(self, total=1, succeeded=1, failed=0):
        """Create a mock result for bulk operations"""
        result = MagicMock()
        result.total = total
        result.succeeded = succeeded
        result.failed = failed
        result.success_rate = (succeeded / total * 100) if total > 0 else 0
        result.started_at = None
        result.completed_at = None
        result.results = []
        return result

    @staticmethod
    def assert_success_exit_code(result, msg="Expected success (exit code 0)"):
        """Assert result is a successful exit code"""
        assert result == 0, f"{msg}, got {result}"

    @staticmethod
    def assert_failure_exit_code(result, msg="Expected failure (exit code 1)"):
        """Assert result is a failure exit code"""
        assert result == 1, f"{msg}, got {result}"

    @staticmethod
    def assert_exit_code_in(result, codes, msg="Expected exit code in allowed values"):
        """Assert result is one of the allowed exit codes"""
        assert result in codes, f"{msg}, got {result} (expected one of {codes})"


class BaseAPICLITestFixture:
    """Pytest fixture provider for API-backed CLI modules (uses PackMarketAPI)"""

    @pytest.fixture
    def mock_api(self):
        """Setup standard API mock for CLI tests"""
        mock = MagicMock()
        mock.create_pack.return_value = {"success": True, "pack_id": "test_pack"}
        mock.get_pack.return_value = {
            "success": True,
            "pack": {
                "pack_id": "test_pack",
                "pack_name": "Test Pack",
                "version": "1.0.0",
                "status": "approved",
            },
        }
        mock.update_pack.return_value = {"success": True}
        mock.delete_pack.return_value = {"success": True}
        mock.list_packs.return_value = {"packs": []}
        mock.rate_pack.return_value = {"success": True, "rating_id": "rating_123"}
        mock.list_pack_ratings.return_value = {"success": True, "count": 0, "ratings": []}
        mock.get_rating.return_value = {"success": True, "rating": {"rating_id": "test"}}
        return mock

    @pytest.fixture
    def mock_api_class(self, mock_api):
        """Mock API class that returns mock_api instance"""
        with patch("ai_collab.cli.pack_rating.PackMarketAPI", return_value=mock_api) as patcher:
            yield patcher


class BaseEngineCLITestFixture:
    """Pytest fixture provider for engine-backed CLI modules (BulkOperationEngine)"""

    @pytest.fixture
    def mock_engine(self):
        """Setup standard engine mock for CLI tests"""
        mock = MagicMock()
        mock.bulk_create.return_value = MagicMock(
            total=1, succeeded=1, failed=0, success_rate=100.0, results=[]
        )
        mock.bulk_update_version.return_value = MagicMock(
            total=1, succeeded=1, failed=0, success_rate=100.0, results=[]
        )
        mock.bulk_archive.return_value = MagicMock(
            total=1, succeeded=1, failed=0, success_rate=100.0, results=[]
        )
        mock.bulk_delete.return_value = MagicMock(
            total=1, succeeded=1, failed=0, success_rate=100.0, results=[]
        )
        mock.get_operation_status.return_value = MagicMock(
            total=1,
            succeeded=1,
            failed=0,
            success_rate=100.0,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            results=[],
        )
        mock.get_all_operations.return_value = []
        return mock


class BaseManagerCLITestFixture:
    """Pytest fixture provider for manager-backed CLI modules"""

    @pytest.fixture
    def mock_manager(self):
        """Setup standard manager mock for CLI tests"""
        mock = MagicMock()
        mock.list_versions.return_value = []
        mock.list_templates.return_value = []
        mock.get_categories.return_value = []
        mock.get_template.return_value = MagicMock(
            template_id="test",
            category=MagicMock(value="productivity"),
            name="Test Template",
            description="Test",
            tags=[],
            parameters={},
            workflow_data={"steps": []},
        )
        mock.search_templates.return_value = []
        mock.create_instance.return_value = MagicMock(instance_id="instance_123", parameters={})
        mock.get_version.return_value = None
        mock.get_latest_version.return_value = None
        mock.create_version.return_value = MagicMock()
        mock.rollback_version.return_value = True
        return mock


# Direct factory functions for immediate use (no fixtures needed)


def create_mock_api(**overrides):
    """Create a mock API instance with default responses"""
    mock = MagicMock()
    mock.create_pack.return_value = {"success": True, "pack_id": "test_pack"}
    mock.get_pack.return_value = {
        "success": True,
        "pack": {
            "pack_id": "test_pack",
            "pack_name": "Test Pack",
            "version": "1.0.0",
            "status": "approved",
        },
    }
    mock.update_pack.return_value = {"success": True}
    mock.delete_pack.return_value = {"success": True}
    mock.list_packs.return_value = {"packs": []}
    mock.get_market_stats.return_value = {"success": True, "stats": {"total_packs": 10}}
    mock.rate_pack.return_value = {"success": True, "rating_id": "rating_123"}
    mock.list_pack_ratings.return_value = {"success": True, "count": 0, "ratings": []}

    for key, value in overrides.items():
        setattr(mock, key, value)
    return mock


def create_mock_bulk_result(total=1, succeeded=1, failed=0):
    """Create a mock bulk operation result"""
    result = MagicMock()
    result.total = total
    result.succeeded = succeeded
    result.failed = failed
    result.success_rate = (succeeded / total * 100) if total > 0 else 0
    result.started_at = datetime.now()
    result.completed_at = datetime.now()
    result.results = []
    return result


def create_mock_template(template_id="test"):
    """Create a mock template"""
    template = MagicMock()
    template.template_id = template_id
    template.category = MagicMock(value="productivity")
    template.name = "Test Template"
    template.description = "Test description"
    template.tags = ["test"]
    template.parameters = {}
    template.workflow_data = {"steps": []}
    return template


def assert_success(result, msg="Expected success"):
    """Assert result is a successful exit code (0)"""
    assert result == 0, f"{msg}, got {result}"


def assert_failure(result, msg="Expected failure"):
    """Assert result is a failure exit code (1)"""
    assert result == 1, f"{msg}, got {result}"
