# Pack Import Export CLI Module
# Week 3 Day 3: Pack 导入导出 CLI

"""
Pack 导入导出 CLI 命令
支持 JSON/YAML 格式的 Pack 导入导出
"""

import json
import sys
from pathlib import Path
from typing import Optional

from ai_collab.pack.importer import ExportFormat, PackExporter, PackImporter
from ai_collab.pack.market import PackListing
from ai_collab.pack.market_api import PackMarketAPI


class PackImportExportCLI:
    """Pack 导入导出 CLI"""

    def __init__(self, db_path: str = "data/packs.db"):
        """初始化 CLI

        Args:
            db_path: 数据库路径
        """
        self.api = PackMarketAPI(db_path)
        self.importer = PackImporter()
        self.exporter = PackExporter()

    def import_pack(self, file_path: str, dry_run: bool = False) -> int:
        """导入 Pack

        Args:
            file_path: 文件路径
            dry_run: 是否只验证不导入

        Returns:
            退出码
        """
        print(f"Importing Pack from {file_path}...")

        # 执行导入验证
        result = self.importer.import_from_file(file_path)

        if dry_run:
            print("\nValidation mode - no changes will be made")
            print(f"Success: {result.success}")
            if result.imported_at:
                print(f"Validated at: {result.imported_at}")

        # 显示错误
        if result.errors:
            print(f"\n✗ Errors ({len(result.errors)}):")
            for err in result.errors:
                print(f"  - {err}")

        # 显示警告
        if result.warnings:
            print(f"\n⚠ Warnings ({len(result.warnings)}):")
            for warn in result.warnings:
                print(f"  - {warn}")

        # 显示验证错误
        if result.validation_errors:
            print(f"\n✗ Validation Errors ({len(result.validation_errors)}):")
            for ve in result.validation_errors:
                print(f"  - [{ve.field}] {ve.message} ({ve.severity})")

        if not result.success:
            return 1

        print("\n✓ Validation successful")
        print(f"  Pack ID: {result.pack_id}")

        if not dry_run:
            # TODO: 实际导入逻辑
            # 读取 pack 数据并创建
            path = Path(file_path)
            content = path.read_text(encoding="utf-8")

            if path.suffix == ".json":
                data = json.loads(content)
            else:
                import yaml

                data = yaml.safe_load(content)

            pack_data = data["pack"]
            create_result = self.api.create_pack(
                pack_name=pack_data.get("pack_name", ""),
                version=pack_data.get("version", "1.0.0"),
                description=pack_data.get("description", ""),
                author=pack_data.get("author", ""),
                category=pack_data.get("category", ""),
                tags=pack_data.get("tags", []),
            )

            if create_result["success"]:
                print("✓ Pack imported successfully")
                print(f"  New Pack ID: {create_result['pack_id']}")
            else:
                print(f"✗ Failed to import Pack: {create_result.get('message', 'Unknown error')}")
                return 1

        return 0

    def export_pack(self, pack_id: str, file_path: str) -> int:
        """导出 Pack

        Args:
            pack_id: Pack ID
            file_path: 目标文件路径

        Returns:
            退出码
        """
        print(f"Exporting Pack {pack_id} to {file_path}...")

        # 获取 Pack
        pack_data = self.api.get_pack(pack_id)

        if not pack_data.get("success"):
            print(f"✗ Pack not found: {pack_id}")
            return 1

        # 转换为 PackListing
        raw_pack = pack_data["pack"]
        pack = PackListing.from_dict(raw_pack)

        # 导出到文件
        try:
            success = self.exporter.export_to_file(pack, file_path)

            if success:
                print(f"✓ Pack exported successfully to {file_path}")
            else:
                print("✗ Failed to export Pack")
                return 1

            # 显示导出信息
            export_format = "JSON" if Path(file_path).suffix == ".json" else "YAML"
            print("\nExport Details:")
            print(f"  Format: {export_format}")
            print(f"  Pack ID: {pack.pack_id}")
            print(f"  Name: {pack.pack_name}")
            print(f"  Version: {pack.version}")
            print(f"  Status: {pack.status.value}")

        except ValueError as e:
            print(f"✗ {e}")
            return 1

        return 0

    def validate(self, file_path: str) -> int:
        """验证 Pack 文件

        Args:
            file_path: 文件路径

        Returns:
            退出码
        """
        print(f"Validating Pack file: {file_path}...")

        # 读取并验证
        result = self.importer.import_from_file(file_path)

        # 只执行详细验证
        path = Path(file_path)
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            import yaml

            data = yaml.safe_load(path.read_text(encoding="utf-8"))

        validation_errors = self.importer.validate_import(data)

        print(f"\n{'='*60}")
        print("Validation Results")
        print(f"{'='*60}\n")

        # Schema 信息
        print(f"Schema Version: {data.get('schema_version', 'N/A')}")
        print(f"Export Date: {data.get('export_date', 'N/A')}")
        print(f"Format: {data.get('format', 'N/A')}")

        # Pack 信息
        if "pack" in data:
            pack = data["pack"]
            print("\nPack Information:")
            print(f"  ID: {pack.get('pack_id', 'N/A')}")
            print(f"  Name: {pack.get('pack_name', 'N/A')}")
            print(f"  Version: {pack.get('version', 'N/A')}")
            print(f"  Author: {pack.get('author', 'N/A')}")

        # Dependencies
        deps = data.get("dependencies", [])
        print(f"\nDependencies: {len(deps)}")

        # Versions
        versions = data.get("versions", [])
        print(f"Versions: {len(versions)}")

        # 错误和警告
        if result.errors:
            print(f"\n✗ Critical Errors ({len(result.errors)}):")
            for err in result.errors:
                print(f"  - {err}")

        if result.warnings:
            print(f"\n⚠ Warnings ({len(result.warnings)}):")
            for warn in result.warnings:
                print(f"  - {warn}")

        if validation_errors:
            error_count = sum(1 for ve in validation_errors if ve.severity == "error")
            warning_count = sum(1 for ve in validation_errors if ve.severity == "warning")

            print(f"\n{'='*60}")
            print("Field Validation")
            print(f"{'='*60}\n")

            # 按类型分组
            errors = [ve for ve in validation_errors if ve.severity == "error"]
            warnings = [ve for ve in validation_errors if ve.severity == "warning"]

            if errors:
                print(f"✗ Errors ({error_count}):")
                for ve in errors:
                    print(f"  - [{ve.field}] {ve.message}")

            if warnings:
                print(f"\n⚠ Warnings ({warning_count}):")
                for ve in warnings:
                    print(f"  - [{ve.field}] {ve.message}")

        print(f"\n{'='*60}")

        if result.success and not any(ve.severity == "error" for ve in validation_errors):
            print("✓ Validation PASSED")
            return 0
        else:
            print("✗ Validation FAILED")
            return 1

    def list_packs(self, status_filter: Optional[str] = None) -> int:
        """列出可导出的 Packs

        Args:
            status_filter: 状态过滤器

        Returns:
            退出码
        """
        result = self.api.list_packs(status=status_filter)

        packs = result.get("packs", [])

        print(f"\n{'='*60}")
        print("Available Packs for Export")
        print(f"{'='*60}\n")

        if not packs:
            print("No packs found.")
            return 0

        for i, pack in enumerate(packs, 1):
            print(f"{i}. {pack.get('pack_id', 'unknown')}")
            print(f"   Name: {pack.get('pack_name', 'N/A')}")
            print(f"   Version: {pack.get('version', 'N/A')}")
            print(f"   Status: {pack.get('status', 'N/A')}")
            print()

        print(f"{'='*60}")
        print(f"Total: {len(packs)} packs")
        print(f"{'='*60}\n")

        return 0

    def bulk_import(self, directory: str, dry_run: bool = False) -> int:
        """批量导入

        Args:
            directory: 文件目录
            dry_run: 是否只验证

        Returns:
            退出码
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            print(f"✗ Directory not found: {directory}")
            return 1

        # 查找所有支持的文件
        files = (
            list(dir_path.glob("*.json"))
            + list(dir_path.glob("*.yaml"))
            + list(dir_path.glob("*.yml"))
        )

        if not files:
            print(f"✗ No import files found in {directory}")
            return 1

        print(f"Found {len(files)} files for bulk import")

        # 批量导入
        results = self.importer.bulk_import([str(f) for f in files])

        # 显示结果
        success_count = sum(1 for r in results if r.success)
        error_count = len(results) - success_count

        print(f"\n{'='*60}")
        print("Bulk Import Results")
        print(f"{'='*60}\n")
        print(f"Total: {len(results)}")
        print(f"Success: {success_count}")
        print(f"Failed: {error_count}")

        if error_count > 0:
            print("\nFailed files:")
            for file_path, result in zip([str(f) for f in files], results):
                if not result.success:
                    print(f"  - {file_path}")
                    for err in result.errors:
                        print(f"      {err}")

        print(f"\n{'='*60}\n")

        return 0 if error_count == 0 else 1

    def bulk_export(self, output_dir: str, export_format: str = "json") -> int:
        """批量导出

        Args:
            output_dir: 输出目录
            export_format: 导出格式

        Returns:
            退出码
        """
        # 获取所有 Packs
        result = self.api.list_packs(status="approved")
        packs_data = result.get("packs", [])

        # 转换为 PackListing
        packs = []
        for p_data in packs_data:
            pack = PackListing.from_dict(p_data)
            packs.append(pack)

        if not packs:
            print("✗ No packs found for export")
            return 1

        # 解析格式
        try:
            fmt = ExportFormat(export_format.lower())
        except ValueError:
            print(f"✗ Invalid format: {export_format}")
            print("Supported formats: json, yaml")
            return 1

        # 批量导出
        print(f"Exporting {len(packs)} packs to {output_dir} ({fmt.value})...")

        export_results = self.exporter.bulk_export(packs, output_dir, fmt)

        # 显示结果
        success_count = sum(1 for success in export_results.values() if success)
        error_count = len(export_results) - success_count

        print(f"\n{'='*60}")
        print("Bulk Export Results")
        print(f"{'='*60}\n")
        print(f"Total: {len(packs)}")
        print(f"Success: {success_count}")
        print(f"Failed: {error_count}")

        if error_count > 0:
            print("\nFailed packs:")
            for pack_id, success in export_results.items():
                if not success:
                    print(f"  - {pack_id}")

        print(f"\n✓ Exported {success_count} packs")
        print(f"  Directory: {output_dir}")
        print(f"  Format: {fmt.value}")

        print(f"\n{'='*60}\n")

        return 0 if error_count == 0 else 1


def main():
    """CLI 入口"""
    if len(sys.argv) < 2:
        print("Usage: pack_import.py <command> [options]")
        print("Commands:")
        print("  import <file_path> [--dry-run]")
        print("  export <pack_id> <file_path>")
        print("  validate <file_path>")
        print("  list [--status <filter>]")
        print("  bulk-import <directory> [--dry-run]")
        print("  bulk-export <directory> [--format <json|yaml>]")
        return 1

    command = sys.argv[1]
    cli = PackImportExportCLI()

    if command == "import":
        if len(sys.argv) < 3:
            print("Usage: pack_import.py import <file_path> [--dry-run]")
            return 1

        file_path = sys.argv[2]
        dry_run = "--dry-run" in sys.argv[3:]

        return cli.import_pack(file_path, dry_run)

    elif command == "export":
        if len(sys.argv) < 4:
            print("Usage: pack_import.py export <pack_id> <file_path>")
            return 1

        pack_id = sys.argv[2]
        file_path = sys.argv[3]

        return cli.export_pack(pack_id, file_path)

    elif command == "validate":
        if len(sys.argv) < 3:
            print("Usage: pack_import.py validate <file_path>")
            return 1

        file_path = sys.argv[2]
        return cli.validate(file_path)

    elif command == "list":
        status_filter = None
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--status" and i + 1 < len(sys.argv):
                status_filter = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        return cli.list_packs(status_filter)

    elif command == "bulk-import":
        if len(sys.argv) < 3:
            print("Usage: pack_import.py bulk-import <directory> [--dry-run]")
            return 1

        directory = sys.argv[2]
        dry_run = "--dry-run" in sys.argv[3:]

        return cli.bulk_import(directory, dry_run)

    elif command == "bulk-export":
        if len(sys.argv) < 3:
            print("Usage: pack_import.py bulk-export <directory> [--format <json|yaml>]")
            return 1

        directory = sys.argv[2]
        export_format = "json"
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--format" and i + 1 < len(sys.argv):
                export_format = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        return cli.bulk_export(directory, export_format)

    else:
        print(f"Unknown command: {command}")
        print("Available commands: import, export, validate, list, bulk-import, bulk-export")
        return 1


if __name__ == "__main__":
    sys.exit(main())
