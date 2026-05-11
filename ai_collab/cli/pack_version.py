# Pack Version CLI Module
# Week 2 Day 3: Pack 版本管理 CLI

"""
Pack 版本管理 CLI 命令
支持版本列表、升级、回滚等操作
"""

import sys
from pathlib import Path
from typing import Optional

from ai_collab.pack.market_api import PackMarketAPI
from ai_collab.pack.version import PackVersion, VersionManager, VersionType


class PackVersionCLI:
    """Pack 版本管理 CLI"""

    def __init__(self, db_path: str = "data/packs.db", manager: Optional[VersionManager] = None):
        """初始化 CLI

        Args:
            db_path: 数据库路径
            manager: 版本管理器（可选）
        """
        self.api = PackMarketAPI(db_path)
        self.manager = manager or VersionManager()
        self._ensure_db_dir()

    def _ensure_db_dir(self) -> None:
        """确保数据库目录存在"""
        Path("data").mkdir(exist_ok=True)

    def list_versions(self, pack_id: str) -> int:
        """列出 Pack 的所有版本

        Args:
            pack_id: Pack ID

        Returns:
            退出码
        """
        print(f"\n{'='*60}")
        print(f"Versions for Pack: {pack_id}")
        print(f"{'='*60}\n")

        # 从市场获取 Pack 信息
        pack_result = self.api.get_pack(pack_id)
        if pack_result["success"]:
            pack = pack_result["pack"]
            print(f"Pack: {pack['pack_name']}")
            print(f"Current Version: {pack.get('version', '0.1.0')}")
            print()

        # 从版本管理器获取历史
        versions = self.manager.list_versions(pack_id)

        if not versions:
            print("No version history found.")
            return 0

        print(f"Version History ({len(versions)} versions):")
        print("-" * 60)

        for i, v in enumerate(versions, 1):
            print(f"\n  [{i}] Version: {v.version}")
            print(f"      Released: {v.created_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"      By: {v.created_by}")
            if v.changelog:
                changelog_preview = (
                    v.changelog[:60] + "..." if len(v.changelog) > 60 else v.changelog
                )
                print(f"      Changelog: {changelog_preview}")

        print(f"\n{'='*60}\n")

        return 0

    def bump_version(
        self, pack_id: str, version_type: str, changelog: str, created_by: str = "unknown"
    ) -> int:
        """升级版本

        Args:
            pack_id: Pack ID
            version_type: 版本类型 (major/minor/patch)
            changelog: 变更日志
            created_by: 创建者

        Returns:
            退出码
        """
        # 检查 Pack 是否存在
        pack_result = self.api.get_pack(pack_id)
        if not pack_result["success"]:
            print(f"✗ Pack not found: {pack_id}")
            return 1

        # 解析版本类型
        version_type_map = {
            "major": VersionType.MAJOR,
            "minor": VersionType.MINOR,
            "patch": VersionType.PATCH,
        }

        if version_type not in version_type_map:
            print(f"✗ Invalid version type: {version_type}")
            print("  Valid types: major, minor, patch")
            return 1

        vtype = version_type_map[version_type]

        # 获取当前版本
        pack = pack_result["pack"]
        current_version_str = pack.get("version", "0.1.0")
        base_version = PackVersion.from_string(current_version_str)

        print(f"Current version: {base_version}")
        print(f"Bumping {version_type} version...")

        # 创建新版本
        next_version = self.manager.create_version(
            pack_id=pack_id,
            version_type=vtype,
            changelog=changelog,
            created_by=created_by,
            base_version=base_version,
        )

        print(f"✓ New version: {next_version}")
        print(f"  Changelog: {changelog}")

        # 更新 Pack 的版本信息（暂不支持，仅记录）
        print("\nNote: Version created in history. Pack version in database not updated.")

        return 0

    def show_version(self, pack_id: str, version_string: str) -> int:
        """查看版本详情

        Args:
            pack_id: Pack ID
            version_string: 版本字符串

        Returns:
            退出码
        """
        print(f"\n{'='*60}")
        print("Version Details")
        print(f"{'='*60}\n")

        # 获取版本历史
        version_history = self.manager.get_version(pack_id, version_string)

        if version_history is None:
            print(f"✗ Version not found: {version_string}")
            return 0

        version_data = version_history.version

        print(f"Pack ID: {pack_id}")
        print(f"Version: {version_data}")
        print("\nVersion Components:")
        print(f"  Major: {version_data.major}")
        print(f"  Minor: {version_data.minor}")
        print(f"  Patch: {version_data.patch}")
        if version_data.prerelease:
            print(f"  Prerelease: {version_data.prerelease}")
        if version_data.build_metadata:
            print(f"  Build Metadata: {version_data.build_metadata}")

        print("\nRelease Information:")
        print(f"  Released: {version_history.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  By: {version_history.created_by}")
        print("\nChangelog:")
        print(f"  {version_history.changelog}")

        print(f"\n{'='*60}\n")

        return 0

    def rollback_version(self, pack_id: str, target_version: str) -> int:
        """回滚版本

        Args:
            pack_id: Pack ID
            target_version: 目标版本

        Returns:
            退出码
        """
        # 检查目标版本是否存在
        target_history = self.manager.get_version(pack_id, target_version)
        if target_history is None:
            print(f"✗ Target version not found: {target_version}")
            return 1

        # 获取当前版本
        current = self.manager.get_latest_version(pack_id)
        current_str = str(current) if current else "unknown"

        print(f"Rolling back from {current_str} to {target_version}...")

        success = self.manager.rollback_version(pack_id, target_version)

        if success:
            print("✓ Rollback successful")
            print(f"  Current version: {target_version}")
        else:
            print("✗ Rollback failed")

        return 0 if success else 1

    def compare(self, v1: str, v2: str) -> int:
        """比较两个版本

        Args:
            v1: 版本 1
            v2: 版本 2

        Returns:
            退出码
        """
        version1 = PackVersion.from_string(v1)
        version2 = PackVersion.from_string(v2)

        print(f"\n{'='*60}")
        print("Version Comparison")
        print(f"{'='*60}\n")

        print(f"Version 1: {version1}")
        print(f"Version 2: {version2}")

        result = version1.compare(version2)

        if result < 0:
            print(f"\nResult: {version1} < {version2}")
        elif result > 0:
            print(f"\nResult: {version1} > {version2}")
        else:
            print(f"\nResult: {version1} == {version2}")

        # 计算距离
        distance = self.manager.calculate_distance(v1, v2)
        print(f"Distance: {distance}")

        print(f"\n{'='*60}\n")

        return 0

    def show_latest(self, pack_id: str) -> int:
        """显示最新版本

        Args:
            pack_id: Pack ID

        Returns:
            退出码
        """
        latest = self.manager.get_latest_version(pack_id)

        if latest is None:
            print(f"No version history found for pack: {pack_id}")
            return 0

        print(f"Latest version: {latest}")

        # 显示详细信息
        return self.show_version(pack_id, str(latest))


def main():
    """CLI 入口"""
    if len(sys.argv) < 3:
        print("Usage: pack_version.py <command> [options]")
        print("Commands:")
        print("  list <pack_id>              - List all versions")
        print("  bump <pack_id> <type>       - Bump version (major/minor/patch)")
        print("  show <pack_id> <version>    - Show version details")
        print("  rollback <pack_id> <version> - Rollback to version")
        print("  compare <v1> <v2>           - Compare two versions")
        print("  latest <pack_id>            - Show latest version")
        return 1

    command = sys.argv[1]
    cli = PackVersionCLI()

    if command == "list":
        if len(sys.argv) < 3:
            print("Usage: pack_version.py list <pack_id>")
            return 1
        return cli.list_versions(sys.argv[2])

    elif command == "bump":
        if len(sys.argv) < 5:
            print("Usage: pack_version.py bump <pack_id> <type> <changelog>")
            print("Types: major, minor, patch")
            return 1

        pack_id = sys.argv[2]
        version_type = sys.argv[3]
        changelog = sys.argv[4]

        return cli.bump_version(pack_id, version_type, changelog)

    elif command == "show":
        if len(sys.argv) < 4:
            print("Usage: pack_version.py show <pack_id> <version>")
            return 1

        return cli.show_version(sys.argv[2], sys.argv[3])

    elif command == "rollback":
        if len(sys.argv) < 4:
            print("Usage: pack_version.py rollback <pack_id> <version>")
            return 1

        return cli.rollback_version(sys.argv[2], sys.argv[3])

    elif command == "compare":
        if len(sys.argv) < 4:
            print("Usage: pack_version.py compare <v1> <v2>")
            return 1

        return cli.compare(sys.argv[2], sys.argv[3])

    elif command == "latest":
        if len(sys.argv) < 3:
            print("Usage: pack_version.py latest <pack_id>")
            return 1

        return cli.show_latest(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        print("Available commands: list, bump, show, rollback, compare, latest")
        return 1


if __name__ == "__main__":
    sys.exit(main())
