"""
Unit tests for Pack Rating System

Tests for:
- Review
- RatingSummary
- RatingSystem
- create_rating_system
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ai_collab.prompt_pack.rating import (
    RatingSummary,
    RatingSystem,
    Review,
    create_rating_system,
)


class TestReview:
    """Test Review functionality"""

    def test_review_creation(self):
        """Test creating a review"""
        timestamp = datetime.now()

        review = Review(
            id="test-123",
            pack_name="test-pack",
            user="testuser",
            rating=5,
            title="Great pack!",
            content="This is a great pack for testing.",
            created_at=timestamp,
            helpful_count=10,
        )

        assert review.id == "test-123"
        assert review.pack_name == "test-pack"
        assert review.user == "testuser"
        assert review.rating == 5
        assert review.title == "Great pack!"
        assert review.helpful_count == 10

    def test_review_validation_invalid_rating(self):
        """Test review validation with invalid rating"""
        timestamp = datetime.now()

        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            Review(
                id="test-123",
                pack_name="test-pack",
                user="testuser",
                rating=6,  # Invalid rating
                title="Invalid",
                content="This should fail",
                created_at=timestamp,
            )

        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            Review(
                id="test-123",
                pack_name="test-pack",
                user="testuser",
                rating=0,  # Invalid rating
                title="Invalid",
                content="This should fail",
                created_at=timestamp,
            )

    def test_review_to_dict(self):
        """Test converting review to dict"""
        timestamp = datetime.now()

        review = Review(
            id="test-123",
            pack_name="test-pack",
            user="testuser",
            rating=5,
            title="Great pack!",
            content="This is great.",
            created_at=timestamp,
            helpful_count=10,
        )

        data = review.to_dict()

        assert data["id"] == "test-123"
        assert data["pack_name"] == "test-pack"
        assert data["user"] == "testuser"
        assert data["rating"] == 5
        assert data["title"] == "Great pack!"
        assert data["content"] == "This is great."
        assert data["created_at"] == timestamp.isoformat()
        assert data["helpful_count"] == 10

    def test_review_from_dict(self):
        """Test creating review from dict"""
        timestamp = datetime.now()

        data = {
            "id": "test-456",
            "pack_name": "another-pack",
            "user": "anotheruser",
            "rating": 4,
            "title": "Good pack",
            "content": "Pretty good",
            "created_at": timestamp.isoformat(),
            "helpful_count": 5,
        }

        review = Review.from_dict(data)

        assert review.id == "test-456"
        assert review.pack_name == "another-pack"
        assert review.user == "anotheruser"
        assert review.rating == 4


class TestRatingSummary:
    """Test RatingSummary functionality"""

    def test_rating_summary_creation(self):
        """Test creating rating summary"""
        summary = RatingSummary(
            pack_name="test-pack",
            average_rating=4.5,
            total_reviews=10,
            rating_distribution={1: 0, 2: 1, 3: 2, 4: 3, 5: 4},
        )

        assert summary.pack_name == "test-pack"
        assert summary.average_rating == 4.5
        assert summary.total_reviews == 10
        assert summary.rating_distribution[5] == 4

    def test_rating_summary_to_dict(self):
        """Test converting summary to dict"""
        summary = RatingSummary(
            pack_name="test-pack",
            average_rating=3.8,
            total_reviews=5,
            rating_distribution={1: 0, 2: 0, 3: 1, 4: 2, 5: 2},
        )

        data = summary.to_dict()

        assert data["pack_name"] == "test-pack"
        assert data["average_rating"] == 3.8
        assert data["total_reviews"] == 5
        assert data["rating_distribution"][3] == 1  # Use integer key


class TestRatingSystem:
    """Test RatingSystem functionality"""

    @pytest.fixture
    def temp_packs_dir(self):
        """Create temporary packs directory"""
        temp_dir = tempfile.mkdtemp()
        packs_dir = Path(temp_dir)

        yield packs_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_add_review(self, temp_packs_dir):
        """Test adding a review"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        review = rating_system.add_review(
            pack_name="test-pack",
            user="testuser",
            rating=5,
            title="Excellent!",
            content="This pack is excellent",
        )

        assert review.pack_name == "test-pack"
        assert review.user == "testuser"
        assert review.rating == 5
        assert review.title == "Excellent!"

    def test_add_duplicate_review(self, temp_packs_dir):
        """Test adding duplicate review from same user"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        # Add first review
        rating_system.add_review(
            pack_name="test-pack", user="testuser", rating=5, title="First review", content="First"
        )

        # Try to add second review from same user
        with pytest.raises(ValueError, match="has already reviewed"):
            rating_system.add_review(
                pack_name="test-pack",
                user="testuser",
                rating=4,
                title="Second review",
                content="Second",
            )

    def test_delete_review(self, temp_packs_dir):
        """Test deleting a review"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        # Add a review
        review = rating_system.add_review(
            pack_name="test-pack",
            user="testuser",
            rating=5,
            title="To be deleted",
            content="Delete me",
        )

        # Delete the review
        result = rating_system.delete_review("test-pack", review.id, "testuser")

        assert result is True

        # Verify it's deleted
        assert len(rating_system.get_reviews("test-pack")) == 0

    def test_delete_review_wrong_user(self, temp_packs_dir):
        """Test deleting review with wrong user"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        # Add a review
        review = rating_system.add_review(
            pack_name="test-pack", user="user1", rating=5, title="Review", content="Content"
        )

        # Try to delete with different user
        result = rating_system.delete_review("test-pack", review.id, "user2")

        assert result is False

    def test_get_reviews(self, temp_packs_dir):
        """Test getting reviews for a pack"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        # Add multiple reviews
        rating_system.add_review("test-pack", "user1", 5, "Great", "Great pack")
        rating_system.add_review("test-pack", "user2", 4, "Good", "Good pack")
        rating_system.add_review("test-pack", "user3", 3, "OK", "OK pack")

        reviews = rating_system.get_reviews("test-pack")

        assert len(reviews) == 3

    def test_get_reviews_empty(self, temp_packs_dir):
        """Test getting reviews for pack with no reviews"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        reviews = rating_system.get_reviews("nonexistent-pack")

        assert len(reviews) == 0

    def test_get_user_reviews(self, temp_packs_dir):
        """Test getting reviews by user"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        # Add reviews from different users
        rating_system.add_review("pack1", "user1", 5, "Review1", "Content1")
        rating_system.add_review("pack2", "user1", 4, "Review2", "Content2")
        rating_system.add_review("pack1", "user2", 3, "Review3", "Content3")

        user1_reviews = rating_system.get_user_reviews("user1")

        assert len(user1_reviews) == 2
        pack_names = [r.pack_name for r in user1_reviews]
        assert "pack1" in pack_names
        assert "pack2" in pack_names

    def test_get_rating_summary(self, temp_packs_dir):
        """Test getting rating summary"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        # Add reviews with different ratings
        rating_system.add_review("test-pack", "user1", 5, "Excellent", "Great")
        rating_system.add_review("test-pack", "user2", 4, "Good", "Nice")
        rating_system.add_review("test-pack", "user3", 5, "Excellent", "Awesome")

        summary = rating_system.get_rating_summary("test-pack")

        assert summary.pack_name == "test-pack"
        assert summary.total_reviews == 3
        assert summary.average_rating == pytest.approx(4.67, 0.1)
        assert summary.rating_distribution[5] == 2
        assert summary.rating_distribution[4] == 1

    def test_get_rating_summary_empty(self, temp_packs_dir):
        """Test getting rating summary for pack with no reviews"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        summary = rating_system.get_rating_summary("nonexistent-pack")

        assert summary.pack_name == "nonexistent-pack"
        assert summary.total_reviews == 0
        assert summary.average_rating == 0.0

    def test_mark_review_helpful(self, temp_packs_dir):
        """Test marking review as helpful"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        review = rating_system.add_review(
            pack_name="test-pack",
            user="testuser",
            rating=5,
            title="Helpful review",
            content="Please mark as helpful",
        )

        assert review.helpful_count == 0

        # Mark as helpful
        result = rating_system.mark_review_helpful("test-pack", review.id)

        assert result is True

        # Check updated helpful count
        reviews = rating_system.get_reviews("test-pack")
        assert reviews[0].helpful_count == 1

    def test_mark_review_helpful_nonexistent(self, temp_packs_dir):
        """Test marking nonexistent review as helpful"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        result = rating_system.mark_review_helpful("test-pack", "nonexistent-id")

        assert result is False

    def test_get_top_reviews(self, temp_packs_dir):
        """Test getting top reviews"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        # Add reviews with different helpfulness
        rating_system.add_review("test-pack", "user1", 3, "OK", "Average")
        review2 = rating_system.add_review("test-pack", "user2", 5, "Great", "Excellent")

        # Mark second review as helpful
        rating_system.mark_review_helpful("test-pack", review2.id)
        rating_system.mark_review_helpful("test-pack", review2.id)

        # Get top reviews
        top_reviews = rating_system.get_top_reviews("test-pack", limit=2)

        assert len(top_reviews) == 2
        # Top review should have higher helpful count
        assert top_reviews[0].helpful_count >= top_reviews[1].helpful_count

    def test_export_reviews(self, temp_packs_dir):
        """Test exporting reviews"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        # Add some reviews
        rating_system.add_review("test-pack", "user1", 5, "Great", "Excellent")
        rating_system.add_review("test-pack", "user2", 4, "Good", "Nice")

        # Export
        exported = rating_system.export_reviews("test-pack")

        assert exported["pack_name"] == "test-pack"
        assert exported["summary"]["total_reviews"] == 2
        assert len(exported["reviews"]) == 2

    def test_import_reviews(self, temp_packs_dir):
        """Test importing reviews"""
        rating_system = RatingSystem(".", str(temp_packs_dir))

        # Create import data
        import_data = {
            "pack_name": "import-pack",
            "summary": {
                "pack_name": "import-pack",
                "average_rating": 4.5,
                "total_reviews": 2,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 1, 5: 1},
            },
            "reviews": [
                {
                    "id": "import-1",
                    "pack_name": "import-pack",
                    "user": "importuser1",
                    "rating": 5,
                    "title": "Imported",
                    "content": "Imported review",
                    "created_at": datetime.now().isoformat(),
                    "helpful_count": 0,
                },
                {
                    "id": "import-2",
                    "pack_name": "import-pack",
                    "user": "importuser2",
                    "rating": 4,
                    "title": "Imported 2",
                    "content": "Another imported",
                    "created_at": datetime.now().isoformat(),
                    "helpful_count": 1,
                },
            ],
        }

        # Import
        count = rating_system.import_reviews(import_data)

        assert count == 2

        # Verify imported reviews
        reviews = rating_system.get_reviews("import-pack")
        assert len(reviews) == 2

        summary = rating_system.get_rating_summary("import-pack")
        assert summary.total_reviews == 2


class TestCreateRatingSystem:
    """Test create_rating_system function"""

    def test_create_rating_system(self):
        """Test creating rating system"""
        with tempfile.TemporaryDirectory() as temp_dir:
            rating_system = create_rating_system(".", temp_dir)

            assert isinstance(rating_system, RatingSystem)
