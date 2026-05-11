# Pack Bulk Operations CLI Module
# Week 3 Day 2: Pack 批量操作 CLI

"""
Pack 批量操作 CLI 命令
支持批量创建、更新版本、归档、删除 Pack
"""

import json
import sys

from ai_collab.pack.bulk import BulkOperationEngine
from ai_collab.pack.version import VersionType


class PackBulkCLI:
    """Pack 批量操作 CLI"""

    def __init__(self, db_path: str = "data/packs.db", max_workers: int = 5):
        """初始化 CLI

        Args:
            db_path: 数据库路径
            max_workers: 最大并发数
        """
        self.engine = BulkOperationEngine(db_path, max_workers)

    def bulk_create(self, specs_path: str, parallel: bool = True) -> int:
        """批量创建 Pack

        Args:
            specs_path: Pack 规格文件路径 (JSON)
            parallel: 是否并行执行

        Returns:
            退出码
        """
        print(f"Loading pack specs from {specs_path}...")

        try:
            with open(specs_path, "r", encoding="utf-8") as f:
                pack_specs = json.load(f)
        except FileNotFoundError:
            print(f"✗ File not found: {specs_path}")
            return 1
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON format: {e}")
            return 1

        if not isinstance(pack_specs, list):
            print("✗ Specs must be a list of pack specifications")
            return 1

        print(f"Creating {len(pack_specs)} packs ({'parallel' if parallel else 'sequential'})...")

        result = self.engine.bulk_create(pack_specs, parallel)

        self._print_result(result)

        return 0 if result.failed == 0 else 1

    def bulk_update_version(self, pack_ids: str, version_bump: str, parallel: bool = True) -> int:
        """批量更新版本

        Args:
            pack_ids: Pack ID 列表 (逗号分隔)
            version_bump: 版本升级类型 (major/minor/patch)
            parallel: 是否并行执行

        Returns:
            退出码
        """
        pack_id_list = [pid.strip() for pid in pack_ids.split(",")]

        try:
            VersionType(version_bump)
        except ValueError:
            print(f"✗ Invalid version bump: {version_bump}")
            print("Valid options: major, minor, patch")
            return 1

        print(
            f"Bumping {len(pack_id_list)} packs to {version_bump} version ({'parallel' if parallel else 'sequential'})..."
        )

        result = self.engine.bulk_update_version(pack_id_list, version_bump, parallel)

        self._print_result(result)

        return 0 if result.failed == 0 else 1

    def bulk_archive(self, pack_ids: str, parallel: bool = True) -> int:
        """批量归档 Pack

        Args:
            pack_ids: Pack ID 列表 (逗号分隔)
            parallel: 是否并行执行

        Returns:
            退出码
        """
        pack_id_list = [pid.strip() for pid in pack_ids.split(",")]

        print(
            f"Archiving {len(pack_id_list)} packs ({'parallel' if parallel else 'sequential'})..."
        )

        result = self.engine.bulk_archive(pack_id_list, parallel)

        self._print_result(result)

        return 0 if result.failed == 0 else 1

    def bulk_delete(self, pack_ids: str, confirm_token: str, parallel: bool = True) -> int:
        """批量删除 Pack

        Args:
            pack_ids: Pack ID 列表 (逗号分隔)
            confirm_token: 确认令牌
            parallel: 是否并行执行

        Returns:
            退出码
        """
        pack_id_list = [pid.strip() for pid in pack_ids.split(",")]

        # 生成预期令牌
        expected_token = f"delete_{len(pack_id_list)}"

        if confirm_token != expected_token:
            print("✗ Invalid confirmation token")
            print(f"Expected: {expected_token}")
            print(f"Received: {confirm_token}")
            print(f"\nTo confirm deletion of {len(pack_id_list)} packs, use:")
            print(f"  --confirm {expected_token}")
            return 1

        print(f"Deleting {len(pack_id_list)} packs ({'parallel' if parallel else 'sequential'})...")
        print("This action cannot be undone!")

        result = self.engine.bulk_delete(pack_id_list, confirm_token, parallel)

        self._print_result(result)

        return 0 if result.failed == 0 else 1

    def get_status(self, operation_id: str) -> int:
        """获取操作状态

        Args:
            operation_id: 操作 ID

        Returns:
            退出码
        """
        result = self.engine.get_operation_status(operation_id)

        print(f"\n{'='*60}")
        print(f"Operation Status: {operation_id}")
        print(f"{'='*60}\n")

        if result.completed_at is None:
            status = "RUNNING"
        elif result.failed > 0:
            status = "COMPLETED (WITH ERRORS)"
        else:
            status = "COMPLETED"

        print(f"Status: {status}")
        print(f"Total: {result.total}")
        print(f"Succeeded: {result.succeeded}")
        print(f"Failed: {result.failed}")
        print(f"Success Rate: {result.success_rate:.2f}%")

        if result.completed_at:
            elapsed = (result.completed_at - result.started_at).total_seconds()
            print(f"Elapsed Time: {elapsed:.2f}s")

        print()

        # 显示详细结果
        if result.results:
            print("Detailed Results:")
            for item in result.results:
                pack_id = item.get("pack_id", "unknown")
                success = item.get("success", False)
                error = item.get("error")
                version = item.get("version")

                status_icon = "✓" if success else "✗"
                version_str = f" → v{version}" if version else ""

                print(f"  {status_icon} {pack_id}{version_str}")
                if error:
                    print(f"      Error: {error}")

        print(f"\n{'='*60}\n")

        return 0

    def list_operations(self) -> int:
        """列出所有操作

        Returns:
            退出码
        """
        operations = self.engine.get_all_operations()

        print(f"\n{'='*60}")
        print("All Bulk Operations")
        print(f"{'='*60}\n")

        if not operations:
            print("No operations found.")
            return 0

        for op in operations:
            print(f"Operation ID: {op['operation_id']}")
            print(f"  Type: {op['operation_type']}")
            print(f"  Status: {op['status']}")
            print(f"  Pack Count: {op['total']}")
            print(f"  Created: {op['created_at']}")
            print()

        print(f"{'='*60}\n")
        print(f"Total: {len(operations)} operations")
        print(f"{'='*60}\n")

        return 0

    def _print_result(self, result) -> None:
        """打印操作结果

        Args:
            result: 操作结果
        """
        print(f"\n{'='*60}")
        print("Bulk Operation Result")
        print(f"{'='*60}\n")

        status = "SUCCESS" if result.failed == 0 else "PARTIAL FAILURE"
        if result.succeeded == 0:
            status = "FAILURE"

        print(f"Status: {status}")
        print(f"Total: {result.total}")
        print(f"Succeeded: {result.succeeded}")
        print(f"Failed: {result.failed}")
        print(f"Success Rate: {result.success_rate:.2f}%")

        if result.completed_at:
            elapsed = (result.completed_at - result.started_at).total_seconds()
            print(f"Elapsed Time: {elapsed:.2f}s")

        # 显示详细结果
        if result.results and result.failed > 0:
            print("\nFailed Operations:")
            for item in result.results:
                if not item.get("success"):
                    pack_id = item.get("pack_id", "unknown")
                    error = item.get("error", "Unknown error")
                    print(f"  ✗ {pack_id}")
                    print(f"      Error: {error}")

        print(f"\n{'='*60}\n")


def main():
    """CLI 入口"""
    if len(sys.argv) < 2:
        print("Usage: pack_bulk.py <command> [options]")
        print("Commands:")
        print("  create --specs <path> [--no-parallel]")
        print("  update-version --pack-ids <id1,id2> --bump <type> [--no-parallel]")
        print("  archive --pack-ids <id1,id2> [--no-parallel]")
        print("  delete --pack-ids <id1,id2> --confirm <token> [--no-parallel]")
        print("  status <operation_id>")
        print("  list")
        return 1

    command = sys.argv[1]

    # 解析通用参数
    parallel = True
    max_workers = 5

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--no-parallel":
            parallel = False
            i += 1
        elif sys.argv[i] == "--workers" and i + 1 < len(sys.argv):
            max_workers = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    cli = PackBulkCLI(max_workers=max_workers)

    if command == "create":
        # 解析参数
        specs_path = None

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--specs" and i + 1 < len(sys.argv):
                specs_path = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--no-parallel":
                i += 1
            else:
                i += 1

        if not specs_path:
            print("Usage: pack_bulk.py create --specs <path> [--no-parallel]")
            return 1

        return cli.bulk_create(specs_path, parallel)

    elif command == "update-version":
        # 解析参数
        pack_ids = None
        version_bump = None

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--pack-ids" and i + 1 < len(sys.argv):
                pack_ids = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--bump" and i + 1 < len(sys.argv):
                version_bump = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] in ["--no-parallel", "--workers"]:
                i += 2  # 已经处理
            else:
                i += 1

        if not pack_ids or not version_bump:
            print(
                "Usage: pack_bulk.py update-version --pack-ids <id1,id2> --bump <type> [--no-parallel]"
            )
            print("Version types: major, minor, patch")
            return 1

        return cli.bulk_update_version(pack_ids, version_bump, parallel)

    elif command == "archive":
        # 解析参数
        pack_ids = None

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--pack-ids" and i + 1 < len(sys.argv):
                pack_ids = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] in ["--no-parallel", "--workers"]:
                i += 2
            else:
                i += 1

        if not pack_ids:
            print("Usage: pack_bulk.py archive --pack-ids <id1,id2> [--no-parallel]")
            return 1

        return cli.bulk_archive(pack_ids, parallel)

    elif command == "delete":
        # 解析参数
        pack_ids = None
        confirm_token = None

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--pack-ids" and i + 1 < len(sys.argv):
                pack_ids = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--confirm" and i + 1 < len(sys.argv):
                confirm_token = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] in ["--no-parallel", "--workers"]:
                i += 2
            else:
                i += 1

        if not pack_ids or not confirm_token:
            print(
                "Usage: pack_bulk.py delete --pack-ids <id1,id2> --confirm <token> [--no-parallel]"
            )
            print("Example: delete --pack-ids pack1,pack2 --confirm delete_2")
            return 1

        return cli.bulk_delete(pack_ids, confirm_token, parallel)

    elif command == "status":
        if len(sys.argv) < 3:
            print("Usage: pack_bulk.py status <operation_id>")
            return 1
        return cli.get_status(sys.argv[2])

    elif command == "list":
        return cli.list_operations()

    else:
        print(f"Unknown command: {command}")
        print("Available commands: create, update-version, archive, delete, status, list")
        return 1


if __name__ == "__main__":
    sys.exit(main())
