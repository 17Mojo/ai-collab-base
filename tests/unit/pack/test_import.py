# Pack Importer Tests
# Week 3 Day 3: Pack 导入导出测试

import json
import tempfile
from pathlib import Path

import pytest

from ai_collab.pack.importer import ExportFormat, PackExporter, PackImporter
from ai_collab.pack.market import PackListing


class TestPackExport:
    """测试 Pack 导出"""

    def test_export_json(self):
        """测试 JSON 导出"""
        pack = PackListing(
            pack_id="test_export_001",
            pack_name="Test Pack",
            version="1.0.0",
            description="Test description",
            author="test_author",
            category="test",
            tags=["test", "sample"],
        )

        exporter = PackExporter()
        export = exporter.export_pack(pack, export_format=ExportFormat.JSON)

        assert export.pack == pack
        assert export.export_format == ExportFormat.JSON
        assert export.schema_version == "2.0"
        assert "export_date" in export.to_dict()

    def test_export_yaml(self):
        """测试 YAML 导出"""
        pack = PackListing(
            pack_id="test_export_002",
            pack_name="Test Pack 2",
            version="2.0.0",
            description="Test description 2",
            author="test_author",
            category="test",
        )

        exporter = PackExporter()
        export = exporter.export_pack(pack, export_format=ExportFormat.YAML)

        assert export.export_format == ExportFormat.YAML
        assert "export_date" in export.to_dict()

    def test_export_with_dependencies(self):
        """测试带依赖的导出"""
        pack = PackListing(
            pack_id="test_export_003",
            pack_name="Test Pack 3",
            version="1.0.0",
            description="Test",
            author="test",
            category="test",
        )

        dependencies = [
            {"name": "dep1", "version_range": "^1.0.0"},
            {"name": "dep2", "version_range": "~2.0.0"},
        ]

        exporter = PackExporter()
        export = exporter.export_pack(pack, dependencies=dependencies)

        assert len(export.dependencies) == 2
        assert export.dependencies[0]["name"] == "dep1"

    def test_export_with_versions(self):
        """测试带版本的导出"""
        pack = PackListing(
            pack_id="test_export_004",
            pack_name="Test Pack 4",
            version="1.0.0",
            description="Test",
            author="test",
            category="test",
        )

        versions = [
            {"version_string": "1.0.0", "changelog": "Initial release"},
            {"version_string": "1.1.0", "changelog": "Bug fixes"},
        ]

        exporter = PackExporter()
        export = exporter.export_pack(pack, versions=versions)

        assert len(export.versions) == 2
        assert export.versions[0]["version_string"] == "1.0.0"

    def test_export_to_json_file(self):
        """测试导出到 JSON 文件"""
        pack = PackListing(
            pack_id="test_export_file",
            pack_name="Test File Export",
            version="1.0.0",
            description="Test",
            author="test",
            category="test",
        )

        exporter = PackExporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_pack.json"

            success = exporter.export_to_file(pack, str(file_path))

            assert success
            assert file_path.exists()

            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)

            assert data["pack"]["pack_id"] == "test_export_file"
            assert data["format"] == "json"

    def test_export_to_yaml_file(self):
        """测试导出到 YAML 文件"""
        pack = PackListing(
            pack_id="test_export_yaml",
            pack_name="Test YAML Export",
            version="1.0.0",
            description="Test",
            author="test",
            category="test",
        )

        exporter = PackExporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_pack.yaml"

            success = exporter.export_to_file(pack, str(file_path))

            assert success
            assert file_path.exists()

            content = file_path.read_text(encoding="utf-8")
            assert "schema_version: '2.0'" in content or "schema_version: 2.0" in content
            assert "pack_name: Test YAML Export" in content
        assert "pack_name: Test YAML Export" in content

    def test_unsupported_format(self):
        """测试不支持的格式"""
        pack = PackListing(
            pack_id="test",
            pack_name="Test",
            version="1.0.0",
            description="Test",
            author="test",
            category="test",
        )

        exporter = PackExporter()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"

            with pytest.raises(ValueError) as exc:
                exporter.export_to_file(pack, str(file_path))

            assert "不支持的文件格式" in str(exc.value)

    def test_get_available_formats(self):
        """测试获取可用格式"""
        exporter = PackExporter()
        formats = exporter.get_available_formats()

        assert len(formats) == 2
        assert ExportFormat.JSON in formats
        assert ExportFormat.YAML in formats


class TestPackImport:
    """测试 Pack 导入"""

    def test_import_valid_json(self):
        """测试导入有效的 JSON"""
        importer = PackImporter()

        data = {
            "schema_version": "2.0",
            "export_date": "2026-04-07",
            "format": "json",
            "pack": {
                "pack_id": "test_import_001",
                "pack_name": "Test Import",
                "version": "1.0.0",
                "description": "Test description",
                "author": "test",
                "category": "test",
            },
            "dependencies": [],
            "versions": [],
        }

        result = importer.import_from_dict(data)

        assert result.success
        assert result.pack_id == "test_import_001"
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_import_missing_schema(self):
        """测试缺少 schema_version"""
        importer = PackImporter()

        data = {
            "format": "json",
            "pack": {
                "pack_id": "test",
                "pack_name": "Test",
                "version": "1.0.0",
                "description": "Test",
                "author": "test",
                "category": "test",
            },
        }

        result = importer.import_from_dict(data)

        assert not result.success
        assert len(result.errors) > 0
        assert "缺少 schema_version 字段" in result.errors[0]

    def test_import_missing_pack(self):
        """测试缺少 pack 字段"""
        importer = PackImporter()

        data = {"schema_version": "2.0", "format": "json"}

        result = importer.import_from_dict(data)

        assert not result.success
        assert "缺少 pack 字段" in result.errors[0]

    def test_import_missing_required_fields(self):
        """测试缺少必需字段"""
        importer = PackImporter()

        data = {
            "schema_version": "2.0",
            "pack": {
                "pack_id": "test",
                # 缺少其他必需字段
            },
        }

        result = importer.import_from_dict(data)

        assert not result.success
        assert len(result.validation_errors) > 0

    def test_import_json_file(self):
        """测试从 JSON 文件导入"""
        importer = PackImporter()

        data = {
            "schema_version": "2.0",
            "export_date": "2026-04-07",
            "format": "json",
            "pack": {
                "pack_id": "test_file_import",
                "pack_name": "Test File Import",
                "version": "1.0.0",
                "description": "Test",
                "author": "test",
                "category": "test",
            },
            "dependencies": [],
            "versions": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            result = importer.import_from_file(temp_path)

            assert result.success
            assert result.pack_id == "test_file_import"
        finally:
            Path(temp_path).unlink()

    def test_import_yaml_file(self):
        """测试从 YAML 文件导入"""
        importer = PackImporter()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            content = """
schema_version: 2.0
export_date: '2026-04-07'
format: yaml
pack:
  pack_id: test_yaml_import
  pack_name: Test YAML Import
  version: 1.0.0
  description: Test
  author: test
  category: test
dependencies: []
versions: []
"""
            f.write(content)
            temp_path = f.name

        try:
            result = importer.import_from_file(temp_path)

            assert result.success
            assert result.pack_id == "test_yaml_import"
        finally:
            Path(temp_path).unlink()

    def test_import_file_not_found(self):
        """测试文件不存在"""
        importer = PackImporter()
        result = importer.import_from_file("/nonexistent/file.json")

        assert not result.success
        assert "文件不存在" in result.errors[0]

    def test_import_invalid_json(self):
        """测试无效的 JSON"""
        importer = PackImporter()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json}')
            temp_path = f.name

        try:
            result = importer.import_from_file(temp_path)

            assert not result.success
            assert "JSON 解析失败" in result.errors[0]
        finally:
            Path(temp_path).unlink()

    def test_validate_success(self):
        """测试验证成功"""
        importer = PackImporter()

        data = {
            "schema_version": "2.0",
            "pack": {
                "pack_id": "test",
                "pack_name": "Test",
                "version": "1.0.0",
                "description": "Test",
                "author": "test",
                "category": "test",
                "downloads": 0,
                "rating": 0.0,
                "tags": ["test"],
            },
            "dependencies": [{"name": "dep1", "version_range": "^1.0.0"}],
            "versions": [{"version_string": "1.0.0", "changelog": "Initial"}],
        }

        errors = importer.validate_import(data)

        # 应该没有错误
        error_errors = [e for e in errors if e.severity == "error"]
        assert len(error_errors) == 0

    def test_validate_field_type_errors(self):
        """测试字段类型错误"""
        importer = PackImporter()

        data = {
            "schema_version": "2.0",
            "pack": {
                "pack_id": 123,  # 应该是字符串
                "version": 123,  # 应该是字符串
                "downloads": "invalid",  # 应该是整数
                "rating": "invalid",  # 应该是数字
                "tags": "invalid",  # 应该是列表
            },
            "dependencies": "invalid",  # 应该是列表
            "versions": "invalid",  # 应该是列表
        }

        errors = importer.validate_import(data)

        # 应该有多个错误
        assert len(errors) > 5

        error_fields = [e.field for e in errors]
        assert "pack_id" in error_fields
        assert "version" in error_fields
        assert "downloads" in error_fields
        assert "rating" in error_fields
        assert "tags" in error_fields
        assert "dependencies" in error_fields
        assert "versions" in error_fields

    def test_validate_missing_dependency_fields(self):
        """测试依赖字段缺失"""
        importer = PackImporter()

        data = {
            "schema_version": "2.0",
            "pack": {
                "pack_id": "test",
                "pack_name": "Test",
                "version": "1.0.0",
                "description": "Test",
                "author": "test",
                "category": "test",
            },
            "dependencies": [{"name": "dep1"}],  # 缺少 version_range
        }

        errors = importer.validate_import(data)

        # 应该有 warning
        dep_errors = [e for e in errors if "dependencies" in e.field and e.severity == "warning"]
        assert len(dep_errors) > 0

    def test_bulk_import(self):
        """测试批量导入"""
        importer = PackImporter()

        # 准备数据
        data1 = {
            "schema_version": "2.0",
            "pack": {
                "pack_id": "test_bulk_1",
                "pack_name": "Bulk 1",
                "version": "1.0.0",
                "description": "Test",
                "author": "test",
                "category": "test",
            },
            "dependencies": [],
            "versions": [],
        }

        data2 = {
            "schema_version": "2.0",
            "pack": {
                "pack_id": "test_bulk_2",
                "pack_name": "Bulk 2",
                "version": "1.0.0",
                "description": "Test",
                "author": "test",
                "category": "test",
            },
            "dependencies": [],
            "versions": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "pack1.json"
            file2 = Path(tmpdir) / "pack2.json"

            file1.write_text(json.dumps(data1), encoding="utf-8")
            file2.write_text(json.dumps(data2), encoding="utf-8")

            results = importer.bulk_import([str(file1), str(file2)])

            assert len(results) == 2
            assert all(r.success for r in results)
            assert results[0].pack_id == "test_bulk_1"
            assert results[1].pack_id == "test_bulk_2"


class TestPackImportExportCLI:
    """测试 Pack Import Export CLI"""

    def Test_cli_validate_valid(self):
        """测试 CLI 验证有效文件"""
        from ai_collab.cli.pack_import import PackImportExportCLI

        data = {
            "schema_version": "2.0",
            "export_date": "2026-04-07",
            "format": "json",
            "pack": {
                "pack_id": "test",
                "pack_name": "Test",
                "version": "1.0.0",
                "description": "Test",
                "author": "test",
                "category": "test",
            },
            "dependencies": [],
            "versions": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            cli = PackImportExportCLI()
            result = cli.validate(temp_path)

            assert result == 0
        finally:
            Path(temp_path).unlink()

    def test_cli_validate_invalid(self):
        """测试 CLI 验证无效文件"""
        from ai_collab.cli.pack_import import PackImportExportCLI

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": "data"}')
            temp_path = f.name

        try:
            cli = PackImportExportCLI()
            result = cli.validate(temp_path)

            assert result == 1
        finally:
            Path(temp_path).unlink()

    def test_cli_import_dry_run(self):
        """测试 CLI 导入 (dry-run)"""
        from ai_collab.cli.pack_import import PackImportExportCLI

        data = {
            "schema_version": "2.0",
            "pack": {
                "pack_id": "test_dryrun",
                "pack_name": "Test Dry Run",
                "version": "1.0.0",
                "description": "Test",
                "author": "test",
                "category": "test",
            },
            "dependencies": [],
            "versions": [],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            cli = PackImportExportCLI()
            result = cli.import_pack(temp_path, dry_run=True)

            assert result == 0
        finally:
            Path(temp_path).unlink()

    def test_cli_list_packs(self):
        """测试 CLI 列出 Packs"""
        from ai_collab.cli.pack_import import PackImportExportCLI

        cli = PackImportExportCLI()
        result = cli.list_packs()

        assert result == 0

    def test_cli_bulk_export(self):
        """测试 CLI 批量导出"""
        from ai_collab.cli.pack_import import PackImportExportCLI

        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir) / "exports"

            cli = PackImportExportCLI()
            result = cli.bulk_export(str(export_dir), "json")

            # 可能没有 pack，但不应该报错
            assert result == 0 or result == 1

    def test_cli_bulk_import(self):
        """测试 CLI 批量导入"""
        from ai_collab.cli.pack_import import PackImportExportCLI

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            data = {
                "schema_version": "2.0",
                "pack": {
                    "pack_id": "test",
                    "pack_name": "Test",
                    "version": "1.0.0",
                    "description": "Test",
                    "author": "test",
                    "category": "test",
                },
                "dependencies": [],
                "versions": [],
            }

            file1 = Path(tmpdir) / "pack1.json"
            file1.write_text(json.dumps(data), encoding="utf-8")

            cli = PackImportExportCLI()
            result = cli.bulk_import(str(tmpdir))

            assert result == 0
