"""
Pack 版本管理模块

实现 Pack 版本管理功能，包括：
- SemVer 版本解析和比较
- Pack 版本升级
- 版本迁移和兼容性
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class VersionBumpType(Enum):
    """版本升级类型"""

    MAJOR = "major"  # 主版本（不向后兼容的变更）
    MINOR = "minor"  # 次版本（向后兼容的新功能）
    PATCH = "patch"  # 修订版本（向后兼容的错误修复）


class VersionPart(Enum):
    """版本部分"""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"
    BUILD = "build"


@dataclass
class PackVersion:
    """Pack 版本类（基于 SemVer）"""

    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None  # e.g., "alpha", "beta", "rc1"
    build: Optional[str] = None  # e.g., "20260302"

    def __str__(self) -> str:
        """版本字符串表示"""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    @classmethod
    def parse(cls, version_str: str) -> "PackVersion":
        """解析版本字符串"""
        # 匹配 SemVer 格式: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9]+))?(?:\+([a-zA-Z0-9.]+))?$"
        match = re.match(pattern, version_str.strip())

        if not match:
            raise ValueError(f"Invalid version format: {version_str}")

        major, minor, patch, prerelease, build = match.groups()
        return cls(
            major=int(major), minor=int(minor), patch=int(patch), prerelease=prerelease, build=build
        )

    def bump(self, bump_type: VersionBumpType) -> "PackVersion":
        """升级版本"""
        new_version = PackVersion(
            major=self.major, minor=self.minor, patch=self.patch, prerelease=None, build=None
        )

        if bump_type == VersionBumpType.MAJOR:
            new_version.major += 1
            new_version.minor = 0
            new_version.patch = 0
        elif bump_type == VersionBumpType.MINOR:
            new_version.minor += 1
            new_version.patch = 0
        elif bump_type == VersionBumpType.PATCH:
            new_version.patch += 1

        return new_version

    def compare_to(self, other: "PackVersion") -> int:
        """比较版本

        Returns:
            -1 if self < other
            0 if self == other
            1 if self > other
        """
        if self.major != other.major:
            return -1 if self.major < other.major else 1
        if self.minor != other.minor:
            return -1 if self.minor < other.minor else 1
        if self.patch != other.patch:
            return -1 if self.patch < other.patch else 1

        # 比较 prerelease
        if self.prerelease is None and other.prerelease is None:
            return 0
        if self.prerelease is None:
            return 1  # 正式版本 > 预发布版本
        if other.prerelease is None:
            return -1  # 预发布版本 < 正式版本

        # 比较 prerelease 字符串（简单实现）
        if self.prerelease < other.prerelease:
            return -1
        elif self.prerelease > other.prerelease:
            return 1

        return 0

    def __lt__(self, other: "PackVersion") -> bool:
        return self.compare_to(other) < 0

    def __le__(self, other: "PackVersion") -> bool:
        return self.compare_to(other) <= 0

    def __eq__(self, other: "PackVersion") -> bool:
        return self.compare_to(other) == 0

    def __gt__(self, other: "PackVersion") -> bool:
        return self.compare_to(other) > 0

    def __ge__(self, other: "PackVersion") -> bool:
        return self.compare_to(other) >= 0


@dataclass
class PackVersionHistory:
    """Pack 版本历史记录"""

    version: PackVersion
    timestamp: datetime
    files: List[str]  # 在此版本中的文件列表
    changelog: str = ""
    migration_script: Optional[str] = None  # 迁移脚本路径

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version": str(self.version),
            "timestamp": self.timestamp.isoformat(),
            "files": self.files,
            "changelog": self.changelog,
            "migration_script": self.migration_script,
        }


@dataclass
class PackVersionMetadata:
    """Pack 版本元数据"""

    current_version: PackVersion
    latest_version: PackVersion
    history: List[PackVersionHistory]
    api_version: str  # 当前 Pack API 版本
    breaking_changes: List[str] = field(default_factory=list)  # 不向后兼容的变更列表

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "current_version": str(self.current_version),
            "latest_version": str(self.latest_version),
            "history": [h.to_dict() for h in self.history],
            "api_version": self.api_version,
            "breaking_changes": self.breaking_changes,
        }


class PackVersionManager:
    """Pack 版本管理器"""

    def __init__(self, pack_dir: Path):
        """
        初始化版本管理器

        Args:
            pack_dir: Pack 目录路径
        """
        self.pack_dir = Path(pack_dir)
        self.version_file = self.pack_dir / "VERSION.json"
        self.history_dir = self.pack_dir / ".versions"
        self.history_dir.mkdir(exist_ok=True)

    def get_current_version(self) -> PackVersion:
        """获取当前 Pack 版本"""
        if not self.version_file.exists():
            # 如果没有版本文件，从 manifest 读取
            manifest_file = self.pack_dir / "manifest.json"
            if not manifest_file.exists():
                raise FileNotFoundError(f"Pack not found at {self.pack_dir}")

            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            return PackVersion.parse(manifest.get("version", "1.0.0"))

        with open(self.version_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            return PackVersion.parse(metadata["current_version"])

    def get_latest_version(self) -> PackVersion:
        """获取最新 Pack 版本"""
        if not self.version_file.exists():
            return self.get_current_version()

        with open(self.version_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            return PackVersion.parse(metadata["latest_version"])

    def get_version_history(self) -> List[PackVersionHistory]:
        """获取版本历史"""
        if not self.version_file.exists():
            return []

        with open(self.version_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            history_data = metadata.get("history", [])

        history = []
        for h in history_data:
            entry = PackVersionHistory(
                version=PackVersion.parse(h["version"]),
                timestamp=datetime.fromisoformat(h["timestamp"]),
                files=h["files"],
                changelog=h.get("changelog", ""),
                migration_script=h.get("migration_script"),
            )
            history.append(entry)

        return history

    def bump_version(
        self,
        bump_type: VersionBumpType,
        changelog: str = "",
        breaking_changes: Optional[List[str]] = None,
    ) -> PackVersion:
        """
        升级 Pack 版本

        Args:
            bump_type: 升级类型（major/minor/patch）
            changelog: 变更日志
            breaking_changes: 不向后兼容的变更列表

        Returns:
            新版本
        """
        current = self.get_current_version()
        new_version = current.bump(bump_type)

        # 保存历史
        history = self.get_version_history()

        # 记录当前版本的文件列表
        current_files = list(self.pack_dir.glob("*"))
        current_files = [
            f.name for f in current_files if f.is_file() and not f.name.startswith(".")
        ]

        history_entry = PackVersionHistory(
            version=current, timestamp=datetime.now(), files=current_files, changelog=changelog
        )
        history.append(history_entry)

        # 更新 manifest 中的版本
        manifest_file = self.pack_dir / "manifest.json"
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        manifest["version"] = str(new_version)
        manifest["updated_at"] = datetime.now().isoformat()

        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        # 保存版本元数据
        version_metadata = PackVersionMetadata(
            current_version=new_version,
            latest_version=new_version,
            history=history,
            api_version="1.0",
            breaking_changes=breaking_changes or [],
        )

        with open(self.version_file, "w", encoding="utf-8") as f:
            json.dump(version_metadata.to_dict(), f, ensure_ascii=False, indent=2)

        return new_version

    def check_updates(self) -> Dict[str, Any]:
        """
        检查 Pack 更新

        Returns:
            更新信息字典
        """
        current = self.get_current_version()
        latest = self.get_latest_version()

        has_update = latest > current

        metadata = {}
        if self.version_file.exists():
            with open(self.version_file, "r", encoding="utf-8") as f:
                version_data = json.load(f)
                metadata = version_data

        return {
            "has_update": has_update,
            "current_version": str(current),
            "latest_version": str(latest),
            "breaking_changes": metadata.get("breaking_changes", []),
            "changelog": metadata.get("history", [])[-1].get("changelog", "")
            if metadata.get("history")
            else "",
        }

    def rollback_to_version(self, version: PackVersion, skip_migration: bool = False) -> bool:
        """
        回滚到指定版本

        Args:
            version: 要回滚到的版本
            skip_migration: 是否跳过迁移脚本

        Returns:
            是否成功回滚
        """
        history = self.get_version_history()

        # 查找目标版本的历史记录
        target_entry = None
        for entry in history:
            if entry.version == version:
                target_entry = entry
                break

        if not target_entry:
            return False

        # 执行迁移脚本（如果有）
        if not skip_migration and target_entry.migration_script:
            migration_script = self.pack_dir / target_entry.migration_script
            if migration_script.exists():
                # TODO: 执行迁移脚本
                pass

        # 恢复 manifest 版本
        manifest_file = self.pack_dir / "manifest.json"
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        manifest["version"] = str(version)
        manifest["updated_at"] = datetime.now().isoformat()

        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        return True

    def get_version_metadata(self) -> Optional[PackVersionMetadata]:
        """获取版本元数据"""
        if not self.version_file.exists():
            return None

        with open(self.version_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return PackVersionMetadata(
            current_version=PackVersion.parse(metadata["current_version"]),
            latest_version=PackVersion.parse(metadata["latest_version"]),
            history=self.get_version_history(),
            api_version=metadata.get("api_version", "1.0"),
            breaking_changes=metadata.get("breaking_changes", []),
        )


def create_version_manager(pack_name: str, workspace: str = ".") -> PackVersionManager:
    """
    创建 Pack 版本管理器

    Args:
        pack_name: Pack 名称
        workspace: 工作区路径

    Returns:
        PackVersionManager 实例
    """
    pack_dir = Path(workspace) / "packs" / pack_name
    return PackVersionManager(pack_dir)
