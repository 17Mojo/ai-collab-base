# Pack Version Management
# Week 2 Day 3: Pack 版本管理

"""
Pack 版本管理模块
支持 SemVer 版本号管理
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class VersionType(Enum):
    """版本类型"""

    MAJOR = "major"  # 主版本号：不兼容的 API 修改
    MINOR = "minor"  # 次版本号：向下兼容的功能性新增
    PATCH = "patch"  # 修订号：向下兼容的问题修正


@dataclass
class PackVersion:
    """Pack 版本数据"""

    major: int
    minor: int
    patch: int
    prerelease: str = ""  # 预发布标识 (alpha, beta, rc)
    build_metadata: str = ""  # 构建元数据

    def __post_init__(self):
        """验证版本号格式"""
        if not all(isinstance(x, int) and x >= 0 for x in [self.major, self.minor, self.patch]):
            raise ValueError("Version parts must be non-negative integers")

    @classmethod
    def from_string(cls, version_string: str) -> "PackVersion":
        """从字符串解析版本

        Args:
            version_string: 版本字符串 (如 "1.2.3", "1.2.3-alpha", "1.2.3+build")

        Returns:
            PackVersion 实例
        """
        # 移除构建元数据
        version, _, build_metadata = version_string.partition("+")

        # 解析主版本号
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([^+]*))?$", version)
        if not match:
            raise ValueError(f"Invalid version string: {version_string}")

        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3))
        prerelease = match.group(4) or ""

        return cls(
            major=major,
            minor=minor,
            patch=patch,
            prerelease=prerelease,
            build_metadata=build_metadata,
        )

    def __str__(self) -> str:
        """格式化为字符串"""
        result = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            result += f"-{self.prerelease}"
        if self.build_metadata:
            result += f"+{self.build_metadata}"
        return result

    def bump(self, version_type: VersionType) -> "PackVersion":
        """升级版本

        Args:
            version_type: 版本类型

        Returns:
            新版本号
        """
        new_version = PackVersion(major=self.major, minor=self.minor, patch=self.patch)

        if version_type == VersionType.MAJOR:
            new_version.major += 1
            new_version.minor = 0
            new_version.patch = 0
        elif version_type == VersionType.MINOR:
            new_version.minor += 1
            new_version.patch = 0
        elif version_type == VersionType.PATCH:
            new_version.patch += 1

        # 清除预发布标识
        new_version.prerelease = ""
        new_version.build_metadata = ""

        return new_version

    def compare(self, other: "PackVersion") -> int:
        """比较版本

        Args:
            other: 另一个版本

        Returns:
            -1: 自己 < other
             0: 自己 == other
             1: 自己 > other
        """
        # 比较主版本号、次版本号、修订号
        for a, b in [
            (self.major, other.major),
            (self.minor, other.minor),
            (self.patch, other.patch),
        ]:
            if a < b:
                return -1
            elif a > b:
                return 1

        # 比较预发布标识
        self_pre = self.prerelease or None
        other_pre = other.prerelease or None

        if self_pre is None and other_pre is None:
            return 0
        elif self_pre is None:
            return 1  # 正式版本 > 预发布版本
        elif other_pre is None:
            return -1
        else:
            # 预发布版本按字母顺序比较
            if self_pre < other_pre:
                return -1
            elif self_pre > other_pre:
                return 1
            else:
                return 0

    def __lt__(self, other: "PackVersion") -> bool:
        return self.compare(other) < 0

    def __le__(self, other: "PackVersion") -> bool:
        return self.compare(other) <= 0

    def __gt__(self, other: "PackVersion") -> bool:
        return self.compare(other) > 0

    def __ge__(self, other: "PackVersion") -> bool:
        return self.compare(other) >= 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PackVersion):
            return False
        return self.compare(other) == 0

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "prerelease": self.prerelease,
            "build_metadata": self.build_metadata,
            "version_string": str(self),
        }


@dataclass
class VersionHistory:
    """版本历史记录"""

    version_id: str
    pack_id: str
    version: PackVersion
    changelog: str
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "version_id": self.version_id,
            "pack_id": self.pack_id,
            "version": self.version.to_dict(),
            "changelog": self.changelog,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VersionHistory":
        """从字典反序列化"""
        version_data = data["version"]
        version = PackVersion(
            major=version_data["major"],
            minor=version_data["minor"],
            patch=version_data["patch"],
            prerelease=version_data.get("prerelease", ""),
            build_metadata=version_data.get("build_metadata", ""),
        )

        return cls(
            version_id=data["version_id"],
            pack_id=data["pack_id"],
            version=version,
            changelog=data["changelog"],
            created_at=datetime.fromisoformat(data["created_at"]),
            created_by=data.get("created_by", "unknown"),
        )


class VersionManager:
    """版本管理器"""

    def __init__(self):
        """初始化版本管理器"""
        self._history: Dict[str, List[VersionHistory]] = {}

    def create_version(
        self,
        pack_id: str,
        version_type: VersionType,
        changelog: str,
        created_by: str = "unknown",
        base_version: Optional[PackVersion] = None,
    ) -> PackVersion:
        """创建新版本

        Args:
            pack_id: Pack ID
            version_type: 版本类型
            changelog: 变更日志
            created_by: 创建者
            base_version: 基础版本（如不提供，使用历史最新版本）

        Returns:
            新版本号
        """
        # 获取当前版本（按创建时间获取最新，而不是按版本号）
        if base_version is None:
            versions = self._history.get(pack_id, [])
            if versions:
                # 按创建时间获取最新的（列表末尾）
                current_version = versions[-1].version
            else:
                # 对于第一个版本，根据版本类型决定初始版本
                if version_type == VersionType.MAJOR:
                    current_version = PackVersion(0, 0, 0)
                elif version_type == VersionType.MINOR:
                    current_version = PackVersion(0, 0, 0)
                else:  # PATCH
                    current_version = PackVersion(0, 1, 0)
        else:
            current_version = base_version

        # 升级版本
        next_version = current_version.bump(version_type)

        # 记录历史
        version_id = f"v_{pack_id}_{str(next_version).replace('.', '-')}"
        history_entry = VersionHistory(
            version_id=version_id,
            pack_id=pack_id,
            version=next_version,
            changelog=changelog,
            created_by=created_by,
        )

        if pack_id not in self._history:
            self._history[pack_id] = []

        self._history[pack_id].append(history_entry)

        return next_version

    def list_versions(self, pack_id: str) -> List[VersionHistory]:
        """列出 Pack 的所有版本

        Args:
            pack_id: Pack ID

        Returns:
            版本历史列表（按版本号降序）
        """
        versions = self._history.get(pack_id, [])
        # 按版本号降序排序
        versions.sort(key=lambda x: x.version, reverse=True)
        return versions

    def get_latest_version(self, pack_id: str) -> Optional[PackVersion]:
        """获取最新版本

        Args:
            pack_id: Pack ID

        Returns:
            最新版本号，不存在返回 None
        """
        versions = self.list_versions(pack_id)
        if versions:
            return versions[0].version
        return None

    def get_version(self, pack_id: str, version_string: str) -> Optional[VersionHistory]:
        """获取指定版本

        Args:
            pack_id: Pack ID
            version_string: 版本字符串

        Returns:
            版本历史记录，不存在返回 None
        """
        target_version = PackVersion.from_string(version_string)

        versions = self._history.get(pack_id, [])
        for v in versions:
            if v.version == target_version:
                return v

        return None

    def compare_versions(self, v1: str, v2: str) -> int:
        """比较两个版本

        Args:
            v1: 版本 1
            v2: 版本 2

        Returns:
            -1: v1 < v2
             0: v1 == v2
             1: v1 > v2
        """
        version1 = PackVersion.from_string(v1)
        version2 = PackVersion.from_string(v2)
        return version1.compare(version2)

    def calculate_distance(self, v1: str, v2: str) -> int:
        """计算版本之间的距离

        Args:
            v1: 版本 1
            v2: 版本 2

        Returns:
            距离值（越大表示差异越大）
        """
        version1 = PackVersion.from_string(v1)
        version2 = PackVersion.from_string(v2)

        # 权重：主版本 > 次版本 > 修订号
        major_distance = abs(version1.major - version2.major) * 100
        minor_distance = abs(version1.minor - version2.minor) * 10
        patch_distance = abs(version1.patch - version2.patch)

        return major_distance + minor_distance + patch_distance

    def rollback_version(self, pack_id: str, target_version: str) -> bool:
        """回滚到指定版本（仅记录回滚操作）

        Args:
            pack_id: Pack ID
            target_version: 目标版本

        Returns:
            是否成功
        """
        target = PackVersion.from_string(target_version)
        if target not in [v.version for v in self.list_versions(pack_id)]:
            return False

        # 创建回滚记录
        version_id = f"rollback_{pack_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        latest = self.get_latest_version(pack_id)

        history_entry = VersionHistory(
            version_id=version_id,
            pack_id=pack_id,
            version=target,  # 回滚后版本为目标版本
            changelog=f"Rollback from {latest} to {target_version}",
            created_by="system",
        )

        if pack_id not in self._history:
            self._history[pack_id] = []

        self._history[pack_id].append(history_entry)

        return True

    def get_version_range(
        self, pack_id: str, min_version: Optional[str] = None, max_version: Optional[str] = None
    ) -> List[VersionHistory]:
        """获取指定范围内的版本

        Args:
            pack_id: Pack ID
            min_version: 最小版本（包含）
            max_version: 最大版本（包含）

        Returns:
            符合条件的版本列表
        """
        versions = self.list_versions(pack_id)

        if min_version is not None:
            min_v = PackVersion.from_string(min_version)
            versions = [v for v in versions if v.version >= min_v]

        if max_version is not None:
            max_v = PackVersion.from_string(max_version)
            versions = [v for v in versions if v.version <= max_v]

        return versions

    def is_compatible(self, required_version: str, current_version: str) -> bool:
        """检查版本兼容性（基于 SemVer 兼容性）

        Args:
            required_version: 要求的版本（如 "^1.2.3"）
            current_version: 当前版本

        Returns:
            是否兼容
        """
        try:
            req = PackVersion.from_string(required_version.replace("^", ""))
            curr = PackVersion.from_string(current_version)

            # SemVer 兼容性：主版本号相同，次版本号和修订号可以更高
            if req.major == curr.major:
                return curr >= req

            return False
        except ValueError:
            return False
