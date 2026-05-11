"""
Unit tests for Pack Sharing and Permission Management

Tests for:
- PermissionLevel
- Permission
- TeamInfo
- PackShareInfo
- PermissionManager
- create_permission_manager
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ai_collab.prompt_pack.sharing import (
    PackShareInfo,
    Permission,
    PermissionLevel,
    PermissionManager,
    TeamInfo,
    create_permission_manager,
)


class TestPermissionLevel:
    """Test PermissionLevel functionality"""

    def test_permission_level_values(self):
        """Test permission level values"""
        assert PermissionLevel.READ.value == "read"
        assert PermissionLevel.WRITE.value == "write"
        assert PermissionLevel.ADMIN.value == "admin"


class TestPermission:
    """Test Permission functionality"""

    def test_permission_creation(self):
        """Test creating permission"""
        timestamp = datetime.now()

        permission = Permission(
            user="testuser", level=PermissionLevel.WRITE, granted_at=timestamp, granted_by="admin"
        )

        assert permission.user == "testuser"
        assert permission.level == PermissionLevel.WRITE
        assert permission.granted_by == "admin"
        assert permission.expires_at is None

    def test_permission_with_expiry(self):
        """Test creating permission with expiry"""
        timestamp = datetime.now()
        expiry = datetime.now()

        permission = Permission(
            user="testuser",
            level=PermissionLevel.READ,
            granted_at=timestamp,
            granted_by="admin",
            expires_at=expiry,
        )

        assert permission.expires_at == expiry

    def test_permission_to_dict(self):
        """Test converting permission to dict"""
        timestamp = datetime.now()

        permission = Permission(
            user="user1", level=PermissionLevel.ADMIN, granted_at=timestamp, granted_by="owner"
        )

        data = permission.to_dict()

        assert data["user"] == "user1"
        assert data["level"] == "admin"
        assert data["granted_at"] == timestamp.isoformat()
        assert data["granted_by"] == "owner"

    def test_permission_from_dict(self):
        """Test creating permission from dict"""
        timestamp = datetime.now()

        data = {
            "user": "user2",
            "level": "write",
            "granted_at": timestamp.isoformat(),
            "granted_by": "admin",
        }

        permission = Permission.from_dict(data)

        assert permission.user == "user2"
        assert permission.level == PermissionLevel.WRITE


class TestTeamInfo:
    """Test TeamInfo functionality"""

    def test_team_creation(self):
        """Test creating team info"""
        team = TeamInfo(
            name="team1",
            display_name="Team One",
            members={"user1", "user2", "user3"},
            packs={"pack1", "pack2"},
        )

        assert team.name == "team1"
        assert team.display_name == "Team One"
        assert len(team.members) == 3
        assert "user1" in team.members
        assert len(team.packs) == 2

    def test_team_to_dict(self):
        """Test converting team to dict"""
        team = TeamInfo(
            name="team1", display_name="Team One", members={"user1", "user2"}, packs={"pack1"}
        )

        data = team.to_dict()

        assert data["name"] == "team1"
        assert data["display_name"] == "Team One"
        assert len(data["members"]) == 2
        assert len(data["packs"]) == 1
        assert isinstance(data["members"], list)
        assert isinstance(data["packs"], list)

    def test_team_from_dict(self):
        """Test creating team from dict"""
        data = {
            "name": "team2",
            "display_name": "Team Two",
            "members": ["user3", "user4"],
            "packs": ["pack2"],
        }

        team = TeamInfo.from_dict(data)

        assert team.name == "team2"
        assert len(team.members) == 2
        assert len(team.packs) == 1


class TestPackShareInfo:
    """Test PackShareInfo functionality"""

    def test_pack_share_creation(self):
        """Test creating pack share info"""
        share_info = PackShareInfo(
            pack_name="test-pack", owner="owner1", permissions={}, teams={}, is_public=False
        )

        assert share_info.pack_name == "test-pack"
        assert share_info.owner == "owner1"
        assert share_info.is_public is False

    def test_pack_share_to_dict(self):
        """Test converting pack share to dict"""
        timestamp = datetime.now()

        permission = Permission(
            user="user1", level=PermissionLevel.READ, granted_at=timestamp, granted_by="owner"
        )

        share_info = PackShareInfo(
            pack_name="my-pack",
            owner="owner1",
            permissions={"user1": permission},
            teams={"team1": PermissionLevel.WRITE},
            is_public=True,
        )

        data = share_info.to_dict()

        assert data["pack_name"] == "my-pack"
        assert data["owner"] == "owner1"
        assert data["is_public"] is True
        assert "user1" in data["permissions"]
        assert "team1" in data["teams"]


class TestPermissionManager:
    """Test PermissionManager functionality"""

    @pytest.fixture
    def temp_packs_dir(self):
        """Create temporary packs directory"""
        temp_dir = tempfile.mkdtemp()
        packs_dir = Path(temp_dir)

        yield packs_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_load_default_share_info(self, temp_packs_dir):
        """Test loading default share info"""
        manager = PermissionManager(temp_packs_dir)
        manager.current_user = "owner"

        share_info = manager._load_share_info("new-pack")

        assert share_info.pack_name == "new-pack"
        assert share_info.owner == "owner"
        assert share_info.is_public is False
        assert len(share_info.permissions) == 0

    def test_grant_permission(self, temp_packs_dir):
        """Test granting permission"""
        manager = PermissionManager(temp_packs_dir)
        manager.current_user = "owner"

        # Grant write permission
        manager.grant_permission("test-pack", "user1", PermissionLevel.WRITE)

        # Check permission
        share_info = manager._load_share_info("test-pack")
        assert "user1" in share_info.permissions
        assert share_info.permissions["user1"].level == PermissionLevel.WRITE

    def test_grant_permission_non_admin(self, temp_packs_dir):
        """Test granting permission as non-admin"""
        manager = PermissionManager(temp_packs_dir)
        manager._save_share_info(
            PackShareInfo(
                pack_name="test-pack", owner="owner", permissions={}, teams={}, is_public=False
            )
        )
        manager.current_user = "user1"

        with pytest.raises(PermissionError, match="does not have admin permission"):
            manager.grant_permission("test-pack", "user2", PermissionLevel.READ)

    def test_revoke_permission(self, temp_packs_dir):
        """Test revoking permission"""
        manager = PermissionManager(temp_packs_dir)
        manager.current_user = "owner"

        # Grant permission first
        manager.grant_permission("test-pack", "user1", PermissionLevel.READ)

        # Revoke permission
        result = manager.revoke_permission("test-pack", "user1")

        assert result is True

        # Verify revoked
        share_info = manager._load_share_info("test-pack")
        assert "user1" not in share_info.permissions

    def test_revoke_nonexistent_permission(self, temp_packs_dir):
        """Test revoking nonexistent permission"""
        manager = PermissionManager(temp_packs_dir)
        manager.current_user = "owner"

        result = manager.revoke_permission("test-pack", "nonexistent")

        assert result is False

    def test_check_permission_owner(self, temp_packs_dir):
        """Test permission check for owner"""
        manager = PermissionManager(temp_packs_dir)
        manager.current_user = "owner"

        # Owner should have all permissions
        assert manager.check_permission("test-pack", "owner", PermissionLevel.READ) is True
        assert manager.check_permission("test-pack", "owner", PermissionLevel.WRITE) is True
        assert manager.check_permission("test-pack", "owner", PermissionLevel.ADMIN) is True

    def test_check_permission_user_level(self, temp_packs_dir):
        """Test permission check with user levels"""
        manager = PermissionManager(temp_packs_dir)
        manager.current_user = "owner"

        # Grant write permission
        manager.grant_permission("test-pack", "user1", PermissionLevel.WRITE)

        # Write permission includes read
        assert manager.check_permission("test-pack", "user1", PermissionLevel.READ) is True
        assert manager.check_permission("test-pack", "user1", PermissionLevel.WRITE) is True
        assert manager.check_permission("test-pack", "user1", PermissionLevel.ADMIN) is False

    def test_set_pack_public(self, temp_packs_dir):
        """Test setting pack public status"""
        manager = PermissionManager(temp_packs_dir)
        manager.current_user = "owner"

        # Set public
        manager.set_pack_public("test-pack", True)

        share_info = manager._load_share_info("test-pack")
        assert share_info.is_public is True

        # Set private
        manager.set_pack_public("test-pack", False)

        share_info = manager._load_share_info("test-pack")
        assert share_info.is_public is False

    def test_set_pack_public_non_owner(self, temp_packs_dir):
        """Test setting public status as non-owner"""
        manager = PermissionManager(temp_packs_dir)
        manager._save_share_info(
            PackShareInfo(
                pack_name="test-pack", owner="owner", permissions={}, teams={}, is_public=False
            )
        )
        manager.current_user = "user1"

        with pytest.raises(PermissionError, match="Only owner can change public status"):
            manager.set_pack_public("test-pack", True)

    def test_transfer_ownership(self, temp_packs_dir):
        """Test transferring ownership"""
        manager = PermissionManager(temp_packs_dir)
        manager.current_user = "owner1"

        manager.transfer_ownership("test-pack", "owner2")

        share_info = manager._load_share_info("test-pack")
        assert share_info.owner == "owner2"

        # Check new owner has admin permission
        assert "owner2" in share_info.permissions
        assert share_info.permissions["owner2"].level == PermissionLevel.ADMIN

    def test_transfer_ownership_non_owner(self, temp_packs_dir):
        """Test transferring ownership as non-owner"""
        manager = PermissionManager(temp_packs_dir)
        manager._save_share_info(
            PackShareInfo(
                pack_name="test-pack", owner="owner1", permissions={}, teams={}, is_public=False
            )
        )
        manager.current_user = "user1"

        with pytest.raises(PermissionError, match="Only current owner can transfer ownership"):
            manager.transfer_ownership("test-pack", "newowner")

    def test_create_permission_manager(self):
        """Test creating permission manager"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = create_permission_manager("packs", temp_dir, "testuser")

            assert manager.current_user == "testuser"
            assert isinstance(manager, PermissionManager)
