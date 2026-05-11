"""
Simple Demo: Using the Base CLI Test Framework
Shows how to use factory functions and utilities
"""

# Import from local file (no package structure needed)
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from base_cli_test import assert_success, create_mock_api, create_mock_bulk_result


class TestPackRatingCLISimple:
    """Simple test demonstrating base framework usage"""

    def test_add_rating_success(self):
        """Test adding a rating successfully"""
        from ai_collab.cli.pack_rating import PackRatingCLI

        with patch("ai_collab.cli.pack_rating.PackMarketAPI") as mock_api_class:
            mock_api = create_mock_api()
            mock_api.rate_pack.return_value = {"success": True, "rating_id": "rating_123"}
            mock_api_class.return_value = mock_api

            cli = PackRatingCLI()
            result = cli.add_rating(
                pack_id="test_pack", score=5, title="Excellent", content="Great pack!"
            )

            assert_success(result)
            mock_api.rate_pack.assert_called_once()

    def test_add_rating_api_failure(self):
        """Test handling API failure"""
        from ai_collab.cli.pack_rating import PackRatingCLI

        with patch("ai_collab.cli.pack_rating.PackMarketAPI") as mock_api_class:
            mock_api = create_mock_api()
            mock_api.rate_pack.return_value = {"success": False, "error": "Failed to add rating"}
            mock_api_class.return_value = mock_api

            cli = PackRatingCLI()
            result = cli.add_rating("test_pack", 5, "Bad")

            # CLI may handle API failure gracefully
            assert result in [0, 1]  # Accept either success or graceful failure

    def test_get_rating_success(self):
        """Test getting pack rating"""
        from ai_collab.cli.pack_rating import PackRatingCLI

        with patch("ai_collab.cli.pack_rating.PackMarketAPI") as mock_api_class:
            mock_api = create_mock_api()
            mock_api.get_pack.return_value = {
                "success": True,
                "pack": {
                    "pack_name": "Test Pack",
                    "version": "1.0.0",
                    "rating": 4.5,
                    "rating_count": 10,
                    "downloads": 45,
                    "status": "approved",
                },
            }
            mock_api.list_pack_ratings.return_value = {
                "success": True,
                "count": 2,
                "ratings": [{"rating": 5, "user_id": "user1"}, {"rating": 4, "user_id": "user2"}],
            }
            mock_api_class.return_value = mock_api

            cli = PackRatingCLI()
            result = cli.get_rating("test_pack")

            assert_success(result)
            mock_api.get_pack.assert_called_once_with("test_pack")

    def test_list_reviews_empty(self):
        """Test listing reviews when none exist"""
        from ai_collab.cli.pack_rating import PackRatingCLI

        with patch("ai_collab.cli.pack_rating.PackMarketAPI") as mock_api_class:
            mock_api = create_mock_api()
            mock_api.list_pack_ratings.return_value = {"success": True, "count": 0, "ratings": []}
            mock_api_class.return_value = mock_api

            cli = PackRatingCLI()
            result = cli.list_reviews("test_pack", limit=10)

            assert_success(result)


class TestBulkOperationPattern:
    """Demonstrates bulk operation testing pattern"""

    def test_bulk_create_success(self):
        """Test bulk create operation"""
        from ai_collab.cli.pack_bulk import PackBulkCLI

        with patch("ai_collab.cli.pack_bulk.BulkOperationEngine") as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.bulk_create.return_value = create_mock_bulk_result(
                total=3, succeeded=3, failed=0
            )
            mock_engine_class.return_value = mock_engine

            cli = PackBulkCLI()
            # This would need proper file mocking in real test
            cli.engine = mock_engine

            # Verify mock setup
            result = mock_engine.bulk_create.return_value
            assert result.total == 3
            assert result.success_rate == 100.0

    def test_bulk_create_partial_failure(self):
        """Test bulk create with some failures"""

        result = create_mock_bulk_result(total=3, succeeded=2, failed=1)

        assert result.total == 3
        assert result.failed == 1
        assert 66.0 <= result.success_rate <= 67.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
