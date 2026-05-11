"""
Unit tests for Pack Version Manager

Tests for:
- PackVersion
- VersionBumpType
- PackVersionManager
- PackVersionHistory
- PackVersionMetadata
"""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ai_collab.prompt_pack.version import (
    PackVersion,
    PackVersionHistory,
    PackVersionManager,
    PackVersionMetadata,
    VersionBumpType,
)


class TestPackVersion:
    """Test PackVersion functionality"""

    def test_parse_basic_version(self):
        """Test parsing a basic version"""
        version = PackVersion.parse("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert str(version) == "1.2.3"

    def test_parse_version_with_prerelease(self):
        """Test parsing version with prerelease"""
        version = PackVersion.parse("1.2.3-beta")
        assert version.prerelease == "beta"
        assert str(version) == "1.2.3-beta"

    def test_parse_version_with_build(self):
        """Test parsing version with build metadata"""
        version = PackVersion.parse("1.2.3+20260302")
        assert version.build == "20260302"
        assert str(version) == "1.2.3+20260302"

    def test_parse_version_with_both(self):
        """Test parsing version with prerelease and build"""
        version = PackVersion.parse("1.2.3-beta+20260302")
        assert version.prerelease == "beta"
        assert version.build == "20260302"
        assert str(version) == "1.2.3-beta+20260302"

    def test_string_representation(self):
        """Test version string representation"""
        version = PackVersion.parse("1.2.3")
        assert str(version) == "1.2.3"

        version2 = PackVersion.parse("1.2.3-beta")
        assert str(version2) == "1.2.3-beta"

    def test_invalid_version_format(self):
        """Test parsing invalid version format"""
        with pytest.raises(ValueError, match="Invalid version format"):
            PackVersion.parse("invalid")

        with pytest.raises(ValueError, match="Invalid version format"):
            PackVersion.parse("1")

        with pytest.raises(ValueError, match="Invalid version format"):
            PackVersion.parse("1.2.3.4.5")

    def test_bump_major(self):
        """Test bumping major version"""
        version = PackVersion.parse("1.2.3")
        new_version = version.bump(VersionBumpType.MAJOR)

        assert new_version.major == 2
        assert new_version.minor == 0
        assert new_version.patch == 0
        assert str(new_version) == "2.0.0"

    def test_bump_minor(self):
        """Test bumping minor version"""
        version = PackVersion.parse("1.2.3")
        new_version = version.bump(VersionBumpType.MINOR)

        assert new_version.major == 1
        assert new_version.minor == 3
        assert new_version.patch == 0
        assert str(new_version) == "1.3.0"

    def test_bump_patch(self):
        """Test bumping patch version"""
        version = PackVersion.parse("1.2.3")
        new_version = version.bump(VersionBumpType.PATCH)

        assert new_version.major == 1
        assert new_version.minor == 2
        assert new_version.patch == 4
        assert str(new_version) == "1.2.4"

    def test_comparison_equal(self):
        """Test equal versions"""
        v1 = PackVersion.parse("1.2.3")
        v2 = PackVersion.parse("1.2.3")
        assert v1 == v2
        assert v1 <= v2
        assert v1 >= v2

    def test_comparison_less_than(self):
        """Test version less than"""
        v1 = PackVersion.parse("1.2.3")
        v2 = PackVersion.parse("1.5.0")

        assert v1 < v2
        assert v1 <= v2
        assert not v1 >= v2
        assert not v1 == v2

    def test_comparison_greater_than(self):
        """Test version greater than"""
        v1 = PackVersion.parse("2.0.0")
        v2 = PackVersion.parse("1.5.0")

        assert v1 > v2
        assert v1 >= v2
        assert not v1 <= v2
        assert not v1 == v2

    def test_comparison_with_prerelease(self):
        """Test comparison with prerelease versions"""
        PackVersion.parse("1.0.0")
        PackVersion.parse("1.0.0-beta")

        v1 = PackVersion.parse("1.0.0")
        v2 = PackVersion.parse("1.0.0-beta")
        assert v1 > v2  # stable > prerelease


class TestPackVersionManager:
    """Test PackVersionManager functionality"""

    @pytest.fixture
    def sample_pack_dir(self):
        """Create a sample pack for testing"""
        temp_dir = tempfile.mkdtemp()
        pack_dir = Path(temp_dir) / "sample-pack"

        pack_dir.mkdir()

        # Create manifest
        manifest = {
            "name": "sample-pack",
            "version": "1.0.0",
            "category": "domain",
            "description": "Sample pack for testing",
            "author": "Test Author",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "dependencies": [],
            "compatible_tools": ["universal"],
            "tags": ["test"],
            "metadata": {},
        }

        with open(pack_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        # Create core.md
        with open(pack_dir / "core.md", "w", encoding="utf-8") as f:
            f.write("# Test core rules\n")

        yield pack_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_get_current_version(self, sample_pack_dir):
        """Test getting current version"""
        manager = PackVersionManager(sample_pack_dir)
        version = manager.get_current_version()

        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0

    def test_bump_version_patch(self, sample_pack_dir):
        """Test bumping patch version"""
        manager = PackVersionManager(sample_pack_dir)

        new_version = manager.bump_version(VersionBumpType.PATCH)

        assert new_version.major == 1
        assert new_version.minor == 0
        assert new_version.patch == 1

        # Verify manifest was updated
        with open(sample_pack_dir / "manifest.json", "r", encoding="utf-8") as f:
            manifest = json.load(f)
            assert manifest["version"] == "1.0.1"

    def test_bump_version_with_breaking_changes(self, sample_pack_dir):
        """Test bumping version with breaking changes"""
        manager = PackVersionManager(sample_pack_dir)

        breaking_changes = ["API change", "Removed field"]

        new_version = manager.bump_version(
            VersionBumpType.MAJOR,
            changelog="Breaking changes in API",
            breaking_changes=breaking_changes,
        )

        assert new_version.major == 2
        assert new_version.minor == 0
        assert new_version.patch == 0

    def test_version_history(self, sample_pack_dir):
        """Test version history tracking"""
        manager = PackVersionManager(sample_pack_dir)

        # First bump
        manager.bump_version(VersionBumpType.PATCH)

        # Second bump
        manager.bump_version(VersionBumpType.MINOR)

        # Check history
        history = manager.get_version_history()

        assert len(history) == 2
        # History records the version BEFORE each bump
        assert history[0].version == PackVersion.parse("1.0.0")  # Recorded when 1.0.0 → 1.0.1
        assert history[1].version == PackVersion.parse("1.0.1")  # Recorded when 1.0.1 → 1.1.0

    def test_get_version_metadata(self, sample_pack_dir):
        """Test getting version metadata"""
        manager = PackVersionManager(sample_pack_dir)

        # Perform a bump to create metadata
        manager.bump_version(VersionBumpType.PATCH)

        metadata = manager.get_version_metadata()

        assert metadata is not None
        assert metadata.current_version.major == 1
        assert metadata.current_version.minor == 0
        assert metadata.current_version.patch == 1
        assert len(metadata.history) == 1

    def test_check_updates(self, sample_pack_dir):
        """Test checking for updates"""
        manager = PackVersionManager(sample_pack_dir)

        # Initial state: no updates
        update_info = manager.check_updates()
        assert update_info["has_update"] is False
        assert update_info["current_version"] == "1.0.0"
        assert update_info["latest_version"] == "1.0.0"

        # After bump, there's an update
        manager.bump_version(VersionBumpType.PATCH)
        update_info = manager.check_updates()
        assert update_info["has_update"] is False  # latest updated
        assert update_info["current_version"] == "1.0.1"
        assert update_info["latest_version"] == "1.0.1"

    def test_rollback_to_version(self, sample_pack_dir):
        """Test rollback to previous version"""
        manager = PackVersionManager(sample_pack_dir)

        # Create multiple versions
        manager.bump_version(VersionBumpType.PATCH)  # 1.0.1
        manager.bump_version(VersionBumpType.MINOR)  # 1.1.0

        # Rollback
        success = manager.rollback_to_version(PackVersion.parse("1.0.1"), skip_migration=True)
        assert success is True

        # Verify manifest was updated
        with open(sample_pack_dir / "manifest.json", "r", encoding="utf-8") as f:
            manifest = json.load(f)
            assert manifest["version"] == "1.0.1"

    def test_rollback_nonexistent_version(self, sample_pack_dir):
        """Test rollback to nonexistent version"""
        manager = PackVersionManager(sample_pack_dir)

        success = manager.rollback_to_version(PackVersion.parse("2.0.0"), skip_migration=True)
        assert success is False


class TestPackVersionHistory:
    """Test PackVersionHistory functionality"""

    def test_to_dict(self):
        """Test converting history to dict"""
        timestamp = datetime.now()
        history = PackVersionHistory(
            version=PackVersion.parse("1.0.0"),
            timestamp=timestamp,
            files=["core.md", "manifest.json"],
            changelog="Initial release",
        )

        data = history.to_dict()

        assert data["version"] == "1.0.0"
        assert data["timestamp"] == timestamp.isoformat()
        assert data["files"] == ["core.md", "manifest.json"]
        assert data["changelog"] == "Initial release"


class TestPackVersionMetadata:
    """Test PackVersionMetadata functionality"""

    def test_to_dict(self):
        """Test converting metadata to dict"""
        version1 = PackVersion.parse("1.0.0")
        version2 = PackVersion.parse("1.1.0")

        metadata = PackVersionMetadata(
            current_version=version1,
            latest_version=version2,
            history=[],
            api_version="1.0",
            breaking_changes=["API change"],
        )

        data = metadata.to_dict()

        assert data["current_version"] == "1.0.0"
        assert data["latest_version"] == "1.1.0"
        assert data["api_version"] == "1.0"
        assert data["breaking_changes"] == ["API change"]
