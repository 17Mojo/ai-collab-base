# Pack Dependency CLI Module
# Week 3 Day 1: Pack 依赖管理系统 CLI

"""
Pack 依赖 CLI 命令
支持依赖添加、列出、解析、删除和冲突检查
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ai_collab.pack.dependency import DependencyNode, DependencyResolver, PackDependency
from ai_collab.pack.market_api import PackMarketAPI


class PackDependencyCLI:
    """Pack 依赖 CLI"""

    def __init__(self, db_path: str = "data/packs.db"):
        """初始化 CLI

        Args:
            db_path: 数据库路径
        """
        self.api = PackMarketAPI(db_path)
        self.resolver = DependencyResolver()
        self._load_registry()

    def _load_registry(self) -> None:
        """加载可用的 Pack 版本到注册表"""
        packs = self.api.list_packs(status="approved")

        for pack in packs.get("packs", []):
            pack_id = pack.get("pack_id")
            if pack_id:
                version = pack.get("version", "1.0.0")
                self.resolver.register_version(pack_id, version)

    def add_dependency(
        self,
        pack_id: str,
        dep_name: str,
        version_range: str,
        optional: bool = False,
        reason: str = "",
    ) -> int:
        """添加依赖

        Args:
            pack_id: Pack ID
            dep_name: 依赖名称
            version_range: 版本范围
            optional: 是否可选
            reason: 依赖原因

        Returns:
            退出码
        """
        print(f"Adding dependency {dep_name} ({version_range}) to {pack_id}...")

        # 创建依赖
        dep = PackDependency(
            name=dep_name, version_range=version_range, optional=optional, reason=reason
        )

        # 检查是否存在
        pack = self.api.get_pack(pack_id)
        if not pack:
            print(f"✗ Pack not found: {pack_id}")
            return 1

        # 解析依赖验证
        compatible_version = self.resolver._find_compatible_version(dep_name, version_range)

        if not compatible_version:
            print(f"✗ No compatible version found for {dep_name} {version_range}")
            return 1

        # 更新 Pack
        update_data = {
            "version": pack.get("version", "1.0.0"),
            "dependencies": pack.get("dependencies", []),
        }

        # 检查是否已存在
        existing = None
        for existing_dep in update_data["dependencies"]:
            if existing_dep.get("name") == dep_name:
                existing = existing_dep
                break

        if existing:
            print(f"✓ Updating existing dependency {dep_name}")
            existing["version_range"] = version_range
            existing["optional"] = optional
            existing["reason"] = reason
        else:
            print(f"✓ Adding new dependency {dep_name}")
            update_data["dependencies"].append(dep.to_dict())

        # 更新 Pack
        result = self.api.update_pack_version(
            pack_id, update_data["version"], dependencies=update_data["dependencies"]
        )

        if result["success"]:
            print("✓ Dependency added successfully")
            if compatible_version:
                print(f"  Compatible version: {compatible_version}")
        else:
            print(f"✗ Failed to add dependency: {result.get('error', 'Unknown error')}")
            return 1

        return 0

    def list_dependencies(self, pack_id: str) -> int:
        """列出依赖

        Args:
            pack_id: Pack ID

        Returns:
            退出码
        """
        pack = self.api.get_pack(pack_id)

        if not pack:
            print(f"✗ Pack not found: {pack_id}")
            return 1

        dependencies = pack.get("dependencies", [])

        print(f"\n{'='*60}")
        print(f"Dependencies for {pack_id}")
        print(f"{'='*60}\n")

        if not dependencies:
            print("No dependencies found.")
            return 0

        for i, dep in enumerate(dependencies, 1):
            print(f"{i}. {dep.get('name', 'unknown')}")
            print(f"   Version: {dep.get('version_range', '*')}")
            print(f"   Optional: {'Yes' if dep.get('optional', False) else 'No'}")
            if dep.get("reason"):
                print(f"   Reason: {dep['reason']}")
            print()

        print(f"{'='*60}")
        print(f"Total: {len(dependencies)} dependencies")
        print(f"{'='*60}\n")

        return 0

    def resolve_dependencies(self, pack_id: str) -> int:
        """解析依赖树

        Args:
            pack_id: Pack ID

        Returns:
            退出码
        """
        pack = self.api.get_pack(pack_id)

        if not pack:
            print(f"✗ Pack not found: {pack_id}")
            return 1

        print(f"\n{'='*60}")
        print(f"Resolving dependencies for {pack_id}")
        print(f"{'='*60}\n")

        # 构建根节点
        root = DependencyNode(pack_id=pack_id, version=pack.get("version", "1.0.0"), resolved=False)

        # 添加依赖
        for dep_data in pack.get("dependencies", []):
            try:
                dep = PackDependency(
                    name=dep_data["name"],
                    version_range=dep_data["version_range"],
                    optional=dep_data.get("optional", False),
                    reason=dep_data.get("reason", ""),
                )
                root.add_dependency(dep)
            except Exception as e:
                print(f"✗ Failed to parse dependency {dep_data.get('name')}: {e}")
                continue

        # 解析
        result = self.resolver.resolve(root)

        if not result.success:
            print("✗ Dependency resolution failed")
            print("\nConflicts:")
            for conflict in result.conflicts:
                print(f"  - {conflict.get('reason', 'Unknown conflict')}")
                print(f"    Pack: {conflict.get('pack')}")
            print("\nErrors:")
            for error in result.errors:
                print(f"  - {error}")
            return 1

        print("✓ Dependency resolution successful\n")

        # 显示解析结果
        print("Resolved dependencies (install order):")
        for i, node in enumerate(result.resolved, 1):
            indent = "  " * node.depth
            print(f"{indent}{i}. {node.pack_id} v{node.version} (depth: {node.depth})")

            # 显示依赖
            for dep in node.dependencies:
                print(f"{indent}   └─ {dep.name} ({dep.version_range})")

        print()

        # 获取安装顺序
        install_order = self.resolver.get_install_order(root)
        print(f"Install order: {' → '.join(install_order)}")

        return 0

    def remove_dependency(self, pack_id: str, dep_name: str) -> int:
        """删除依赖

        Args:
            pack_id: Pack ID
            dep_name: 依赖名称

        Returns:
            退出码
        """
        print(f"Removing dependency {dep_name} from {pack_id}...")

        pack = self.api.get_pack(pack_id)

        if not pack:
            print(f"✗ Pack not found: {pack_id}")
            return 1

        dependencies = pack.get("dependencies", [])

        # 查找并删除
        new_deps = []
        removed = False

        for dep in dependencies:
            if dep.get("name") == dep_name:
                removed = True
                print(f"✓ Removing {dep_name}")
            else:
                new_deps.append(dep)

        if not removed:
            print(f"✗ Dependency not found: {dep_name}")
            return 1

        # 更新 Pack
        result = self.api.update_pack_version(
            pack_id, pack.get("version", "1.0.0"), dependencies=new_deps
        )

        if result["success"]:
            print("✓ Dependency removed successfully")
        else:
            print(f"✗ Failed to remove dependency: {result.get('error', 'Unknown error')}")
            return 1

        return 0

    def check_conflicts(self, pack_id: str) -> int:
        """检查冲突

        Args:
            pack_id: Pack ID

        Returns:
            退出码
        """
        pack = self.api.get_pack(pack_id)

        if not pack:
            print(f"✗ Pack not found: {pack_id}")
            return 1

        print(f"\n{'='*60}")
        print(f"Checking dependency conflicts for {pack_id}")
        print(f"{'='*60}\n")

        # 构建图
        root = DependencyNode(pack_id=pack_id, version=pack.get("version", "1.0.0"))

        for dep_data in pack.get("dependencies", []):
            try:
                dep = PackDependency(name=dep_data["name"], version_range=dep_data["version_range"])
                root.add_dependency(dep)
            except Exception:
                continue

        # 检测冲突
        conflicts = self.resolver.detect_conflicts([root])

        if not conflicts:
            print("✓ No conflicts detected")
            return 0

        print(f"✗ Found {len(conflicts)} conflict(s):\n")

        for i, conflict in enumerate(conflicts, 1):
            print(f"{i}. {conflict.get('reason', 'Unknown conflict')}")
            print(f"   Pack: {conflict.get('pack')}")
            print(f"   Conflicting ranges: {conflict.get('conflicting_ranges')}")
            print()

        return 1


def main():
    """CLI 入口"""
    if len(sys.argv) < 3:
        print("Usage: pack_dependency.py <command> <pack_id> [options]")
        print("Commands:")
        print("  add <pack_id> <dep_name> --version <range> [--optional] [--reason <text>]")
        print("  list <pack_id>")
        print("  resolve <pack_id>")
        print("  remove <pack_id> <dep_name>")
        print("  check <pack_id>")
        return 1

    command = sys.argv[1]
    cli = PackDependencyCLI()

    if command == "add":
        if len(sys.argv) < 5:
            print(
                "Usage: pack_dependency.py add <pack_id> <dep_name> --version <range> [--optional] [--reason <text>]"
            )
            return 1

        pack_id = sys.argv[2]
        dep_name = sys.argv[3]

        # 解析参数
        version_range = ""
        optional = False
        reason = ""

        i = 4
        while i < len(sys.argv):
            if sys.argv[i] == "--version" and i + 1 < len(sys.argv):
                version_range = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--optional":
                optional = True
                i += 1
            elif sys.argv[i] == "--reason" and i + 1 < len(sys.argv):
                reason = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        return cli.add_dependency(pack_id, dep_name, version_range, optional, reason)

    elif command == "list":
        if len(sys.argv) < 3:
            print("Usage: pack_dependency.py list <pack_id>")
            return 1
        return cli.list_dependencies(sys.argv[2])

    elif command == "resolve":
        if len(sys.argv) < 3:
            print("Usage: pack_dependency.py resolve <pack_id>")
            return 1
        return cli.resolve_dependencies(sys.argv[2])

    elif command == "remove":
        if len(sys.argv) < 4:
            print("Usage: pack_dependency.py remove <pack_id> <dep_name>")
            return 1
        return cli.remove_dependency(sys.argv[2], sys.argv[3])

    elif command == "check":
        if len(sys.argv) < 3:
            print("Usage: pack_dependency.py check <pack_id>")
            return 1
        return cli.check_conflicts(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        print("Available commands: add, list, resolve, remove, check")
        return 1


if __name__ == "__main__":
    sys.exit(main())
