"""
Pack 共享和权限管理

实现团队协作功能：
- Pack 权限管理
- 团队共享
- 权限验证
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class PermissionLevel(Enum):
    """权限级别"""

    READ = "read"  # 只读权限
    WRITE = "write"  # 读写权限
    ADMIN = "admin"  # 管理员权限


@dataclass
class Permission:
    """权限"""

    user: str
    level: PermissionLevel
    granted_at: datetime
    granted_by: str
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user": self.user,
            "level": self.level.value,
            "granted_at": self.granted_at.isoformat(),
            "granted_by": self.granted_by,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Permission":
        """从字典创建"""
        return cls(
            user=data["user"],
            level=PermissionLevel(data["level"]),
            granted_at=datetime.fromisoformat(data["granted_at"]),
            granted_by=data["granted_by"],
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
        )


@dataclass
class TeamInfo:
    """团队信息"""

    name: str
    display_name: str
    members: Set[str]
    packs: Set[str]  # 团队可访问的 Pack 列表

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "members": list(self.members),
            "packs": list(self.packs),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeamInfo":
        """从字典创建"""
        return cls(
            name=data["name"],
            display_name=data["display_name"],
            members=set(data.get("members", [])),
            packs=set(data.get("packs", [])),
        )


@dataclass
class PackShareInfo:
    """Pack 共享信息"""

    pack_name: str
    owner: str
    permissions: Dict[str, Permission]  # user -> Permission
    teams: Dict[str, PermissionLevel]  # team_name -> PermissionLevel
    is_public: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "pack_name": self.pack_name,
            "owner": self.owner,
            "permissions": {user: perm.to_dict() for user, perm in self.permissions.items()},
            "teams": {team: level.value for team, level in self.teams.items()},
            "is_public": self.is_public,
        }


class PermissionManager:
    """权限管理器"""

    def __init__(self, packs_root: Path):
        """
        初始化权限管理器

        Args:
            packs_root: Packs 根目录
        """
        self.packs_root = Path(packs_root)
        self.shares_dir = self.packs_root / ".shares"
        # 允许传入尚未创建的 packs_root 路径。
        self.shares_dir.mkdir(parents=True, exist_ok=True)
        self.teams_file = self.packs_root / ".teams.json"
        self.current_user: str = "default"  # 当前用户（实际应该从认证系统获取）

    def _get_share_file(self, pack_name: str) -> Path:
        """获取 Pack 共享文件路径"""
        return self.shares_dir / f"{pack_name}.json"

    def _load_share_info(self, pack_name: str) -> PackShareInfo:
        """加载 Pack 共享信息"""
        share_file = self._get_share_file(pack_name)
        if not share_file.exists():
            # 创建默认共享信息
            return PackShareInfo(
                pack_name=pack_name,
                owner=self.current_user,
                permissions={},
                teams={},
                is_public=False,
            )

        with open(share_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        permissions = {}
        for user, perm_data in data.get("permissions", {}).items():
            permissions[user] = Permission.from_dict(perm_data)

        teams = {}
        for team_name, level_str in data.get("teams", {}).items():
            teams[team_name] = PermissionLevel(level_str)

        return PackShareInfo(
            pack_name=data["pack_name"],
            owner=data["owner"],
            permissions=permissions,
            teams=teams,
            is_public=data.get("is_public", False),
        )

    def _save_share_info(self, share_info: PackShareInfo) -> None:
        """保存 Pack 共享信息"""
        share_file = self._get_share_file(share_info.pack_name)

        with open(share_file, "w", encoding="utf-8") as f:
            json.dump(share_info.to_dict(), f, ensure_ascii=False, indent=2)

    def _load_teams(self) -> Dict[str, TeamInfo]:
        """加载团队信息"""
        if not self.teams_file.exists():
            return {}

        with open(self.teams_file, "r", encoding="utf-8") as f:
            teams_data = json.load(f)

        return {name: TeamInfo.from_dict(data) for name, data in teams_data.items()}

    def _save_teams(self, teams: Dict[str, TeamInfo]) -> None:
        """保存团队信息"""
        with open(self.teams_file, "w", encoding="utf-8") as f:
            teams_data = {name: team.to_dict() for name, team in teams.items()}
            json.dump(teams_data, f, ensure_ascii=False, indent=2)

    def grant_permission(
        self, pack_name: str, user: str, level: PermissionLevel, granted_by: Optional[str] = None
    ) -> None:
        """
        授予用户权限

        Args:
            pack_name: Pack 名称
            user: 用户名
            level: 权限级别
            granted_by: 授予者（默认为当前用户）
        """
        share_info = self._load_share_info(pack_name)

        # 只有管理员可以授予权限
        effective_granted_by = granted_by or self.current_user
        if not self._is_admin(share_info, effective_granted_by):
            raise PermissionError(f"{effective_granted_by} does not have admin permission")

        permission = Permission(
            user=user, level=level, granted_at=datetime.now(), granted_by=effective_granted_by
        )

        share_info.permissions[user] = permission
        self._save_share_info(share_info)

    def revoke_permission(
        self, pack_name: str, user: str, revoked_by: Optional[str] = None
    ) -> bool:
        """
        撤销用户权限

        Args:
            pack_name: Pack 名称
            user: 用户名
            revoked_by: 撤销者（默认为当前用户）

        Returns:
            是否成功撤销
        """
        share_info = self._load_share_info(pack_name)

        # 只有管理员可以撤销权限
        effective_revoked_by = revoked_by or self.current_user
        if not self._is_admin(share_info, effective_revoked_by):
            raise PermissionError(f"{effective_revoked_by} does not have admin permission")

        if user not in share_info.permissions:
            return False

        del share_info.permissions[user]
        self._save_share_info(share_info)
        return True

    def check_permission(self, pack_name: str, user: str, required_level: PermissionLevel) -> bool:
        """
        检查用户是否有足够权限

        Args:
            pack_name: Pack 名称
            user: 用户名
            required_level: 需要的权限级别

        Returns:
            是否有足够权限
        """
        share_info = self._load_share_info(pack_name)

        # 拥有者有所有权限
        if user == share_info.owner:
            return True

        # 公开 Pack 只有读取权限
        if share_info.is_public and required_level == PermissionLevel.READ:
            return True

        # 检查用户权限
        if user in share_info.permissions:
            user_level = share_info.permissions[user].level
            return self._has_permission(user_level, required_level)

        # 检查团队权限
        teams = self._load_teams()
        for team_name, pack_team_level in share_info.teams.items():
            if team_name in teams and user in teams[team_name].members:
                return self._has_permission(pack_team_level, required_level)

        return False

    def get_user_permissions(self, pack_name: str, user: str = None) -> Dict[str, Any]:
        """
        获取用户的权限信息

        Args:
            pack_name: Pack 名称
            user: 用户名（默认为当前用户）

        Returns:
            权限信息字典
        """
        effective_user = user or self.current_user
        share_info = self._load_share_info(pack_name)

        result = {
            "pack_name": pack_name,
            "user": effective_user,
            "is_owner": effective_user == share_info.owner,
            "has_read": False,
            "has_write": False,
            "has_admin": False,
            "permission_level": None,
        }

        # 拥有者
        if effective_user == share_info.owner:
            result["has_read"] = True
            result["has_write"] = True
            result["has_admin"] = True
            result["permission_level"] = "admin"
            return result

        # 公开 Pack
        if share_info.is_public:
            result["has_read"] = True
            result["permission_level"] = "read"

        # 用户权限
        if effective_user in share_info.permissions:
            level = share_info.permissions[effective_user].level
            result["has_read"] = True
            result["has_write"] = level in [PermissionLevel.WRITE, PermissionLevel.ADMIN]
            result["has_admin"] = level == PermissionLevel.ADMIN
            result["permission_level"] = level.value
            return result

        # 团队权限
        teams = self._load_teams()
        for team_name, pack_team_level in share_info.teams.items():
            if team_name in teams and effective_user in teams[team_name].members:
                result["has_read"] = True
                result["has_write"] = pack_team_level in [
                    PermissionLevel.WRITE,
                    PermissionLevel.ADMIN,
                ]
                result["has_admin"] = pack_team_level == PermissionLevel.ADMIN
                result["permission_level"] = pack_team_level.value
                result["team"] = team_name
                return result

        return result

    def set_pack_public(self, pack_name: str, is_public: bool) -> None:
        """
        设置 Pack 是否公开

        Args:
            pack_name: Pack 名称
            is_public: 是否公开
        """
        share_info = self._load_share_info(pack_name)

        # 只有所有者可以修改公开状态
        if self.current_user != share_info.owner:
            raise PermissionError("Only owner can change public status")

        share_info.is_public = is_public
        self._save_share_info(share_info)

    def share_with_team(self, pack_name: str, team_name: str, level: PermissionLevel) -> None:
        """
        与团队分享 Pack

        Args:
            pack_name: Pack 名称
            team_name: 团队名称
            level: 权限级别
        """
        teams = self._load_teams()

        if team_name not in teams:
            raise ValueError(f"Team {team_name} does not exist")

        share_info = self._load_share_info(pack_name)

        # 检查权限
        if not self._is_admin(share_info, self.current_user):
            raise PermissionError(f"{self.current_user} does not have admin permission")

        share_info.teams[team_name] = level
        self._save_share_info(share_info)

    def unshare_with_team(self, pack_name: str, team_name: str) -> bool:
        """
        取消与团队的分享

        Args:
            pack_name: Pack 名称
            team_name: 团队名称

        Returns:
            是否成功取消
        """
        share_info = self._load_share_info(pack_name)

        if team_name not in share_info.teams:
            return False

        # 检查权限
        if not self._is_admin(share_info, self.current_user):
            raise PermissionError(f"{self.current_user} does not have admin permission")

        del share_info.teams[team_name]
        self._save_share_info(share_info)
        return True

    def list_accessible_packs(self, user: str = None) -> List[str]:
        """
        列出用户可访问的 Pack

        Args:
            user: 用户名（默认为当前用户）

        Returns:
            Pack 名称列表
        """
        effective_user = user or self.current_user
        accessible = []

        for share_file in self.shares_dir.glob("*.json"):
            pack_name = share_file.stem
            if self.check_permission(pack_name, effective_user, PermissionLevel.READ):
                accessible.append(pack_name)

        return accessible

    def _is_admin(self, share_info: PackShareInfo, user: str) -> bool:
        """检查用户是否是管理员"""
        if user == share_info.owner:
            return True

        if user in share_info.permissions:
            return share_info.permissions[user].level == PermissionLevel.ADMIN

        # 检查团队管理员权限
        teams = self._load_teams()
        for team_name, pack_team_level in share_info.teams.items():
            if team_name in teams and user in teams[team_name].members:
                if pack_team_level == PermissionLevel.ADMIN:
                    return True

        return False

    def _has_permission(self, user_level: PermissionLevel, required_level: PermissionLevel) -> bool:
        """检查权限级别是否满足要求"""
        level_order = {PermissionLevel.READ: 1, PermissionLevel.WRITE: 2, PermissionLevel.ADMIN: 3}

        return level_order[user_level] >= level_order[required_level]

    def transfer_ownership(self, pack_name: str, new_owner: str) -> None:
        """
        转移 Pack 所有权

        Args:
            pack_name: Pack 名称
            new_owner: 新拥有者
        """
        share_info = self._load_share_info(pack_name)

        # 只有当前所有者可以转移所有权
        if self.current_user != share_info.owner:
            raise PermissionError("Only current owner can transfer ownership")

        old_owner = share_info.owner
        share_info.owner = new_owner

        # 保留所有权用户的权限
        share_info.permissions[new_owner] = Permission(
            user=new_owner,
            level=PermissionLevel.ADMIN,
            granted_at=datetime.now(),
            granted_by=old_owner,
        )

        self._save_share_info(share_info)


def create_permission_manager(
    packs_root: str = ".", workspace: str = ".", user: str = "default"
) -> PermissionManager:
    """
    创建权限管理器

    Args:
        packs_root: Packs 根目录
        workspace: 工作区路径
        user: 当前用户名

    Returns:
        PermissionManager 实例
    """
    packs_path = Path(workspace) / packs_root
    manager = PermissionManager(packs_path)
    manager.current_user = user
    return manager
