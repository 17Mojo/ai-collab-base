# Pack Importer
# Week 3 Day 3: Pack 导入导出

"""
Pack 导入导出模块
支持 JSON/YAML 格式的 Pack 导入导出
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .market import PackListing


class ExportFormat(Enum):
    """导出格式"""

    JSON = "json"
    YAML = "yaml"


class ImportValidationError:
    """导入验证错误"""

    def __init__(self, field: str, message: str, severity: str = "error"):
        """初始化验证错误

        Args:
            field: 字段名
            message: 错误消息
            severity: 严重性 (error/warning/info)
        """
        self.field = field
        self.message = message

        if severity not in ["error", "warning", "info"]:
            raise ValueError(f"Invalid severity: {severity}")

        self.severity = severity

    def to_dict(self) -> Dict[str, str]:
        """转换为字典"""
        return {"field": self.field, "message": self.message, "severity": self.severity}


@dataclass
class PackExport:
    """Pack 导出数据"""

    pack: PackListing
    dependencies: List[dict]
    versions: List[dict]
    export_date: str
    export_format: ExportFormat
    schema_version: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "schema_version": self.schema_version,
            "export_date": self.export_date,
            "format": self.export_format.value,
            "pack": self.pack.to_dict(),
            "dependencies": self.dependencies,
            "versions": self.versions,
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_yaml(self) -> str:
        """转换为 YAML"""
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)


@dataclass
class ImportResult:
    """导入结果"""

    pack_id: Optional[str] = None
    success: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_errors: List[ImportValidationError] = field(default_factory=list)
    imported_at: Optional[str] = None


class PackImporter:
    """Pack 导入器"""

    def __init__(self):
        """初始化导入器"""
        self._schema_version = "2.0"

    def import_from_dict(self, data: Dict[str, Any]) -> ImportResult:
        """从字典导入

        Args:
            data: Pack 数据字典

        Returns:
            导入结果
        """
        result = ImportResult(imported_at=datetime.now().isoformat())

        # 验证 schema version
        if "schema_version" not in data:
            result.errors.append("缺少 schema_version 字段")
            return result

        if data["schema_version"] != self._schema_version:
            result.warnings.append(
                f"Schema version 不匹配 (期望: {self._schema_version}, 实际: {data['schema_version']})"
            )

        # 验证 pack 数据
        if "pack" not in data:
            result.errors.append("缺少 pack 字段")
            return result

        pack_data = data["pack"]

        # 验证必需字段
        required_fields = ["pack_id", "pack_name", "version", "description", "author"]
        for field in required_fields:
            if field not in pack_data:
                result.validation_errors.append(
                    ImportValidationError(field=field, message="缺少必需字段", severity="error")
                )

        if result.validation_errors:
            return result

        # 返回验证通过的数据（实际导入由市场 API 执行）
        result.success = True
        result.pack_id = pack_data.get("pack_id")

        return result

    def import_from_file(self, file_path: str) -> ImportResult:
        """从文件导入

        Args:
            file_path: 文件路径

        Returns:
            导入结果
        """
        path = Path(file_path)

        if not path.exists():
            return ImportResult(success=False, errors=[f"文件不存在: {file_path}"])

        # 根据扩展名确定格式
        if path.suffix == ".json":
            content = path.read_text(encoding="utf-8")
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                return ImportResult(success=False, errors=[f"JSON 解析失败: {e}"])

        elif path.suffix in [".yaml", ".yml"]:
            content = path.read_text(encoding="utf-8")
            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                return ImportResult(success=False, errors=[f"YAML 解析失败: {e}"])

        else:
            return ImportResult(success=False, errors=[f"不支持的文件格式: {path.suffix}"])

        return self.import_from_dict(data)

    def validate_import(self, data: Dict[str, Any]) -> List[ImportValidationError]:
        """验证导入数据

        Args:
            data: Pack 数据字典

        Returns:
            验证错误列表
        """
        errors: List[ImportValidationError] = []

        # 验证 schema version
        if "schema_version" not in data:
            errors.append(ImportValidationError("schema_version", "缺少版本字段", "error"))

        # 验证 pack 数据
        if "pack" not in data:
            errors.append(ImportValidationError("pack", "缺少 pack 数据", "error"))
            return errors

        pack_data = data["pack"]

        # 验证字段类型
        if "pack_id" in pack_data and not isinstance(pack_data["pack_id"], str):
            errors.append(ImportValidationError("pack_id", "pack_id 必须是字符串", "error"))

        if "version" in pack_data and not isinstance(pack_data["version"], str):
            errors.append(ImportValidationError("version", "version 必须是字符串", "error"))

        if "downloads" in pack_data:
            try:
                int(pack_data["downloads"])
            except (ValueError, TypeError):
                errors.append(ImportValidationError("downloads", "downloads 必须是整数", "error"))

        if "rating" in pack_data:
            try:
                float(pack_data["rating"])
                pack_data["rating"] = float(pack_data["rating"])
            except (ValueError, TypeError):
                errors.append(ImportValidationError("rating", "rating 必须是数字", "error"))

        if "tags" in pack_data and not isinstance(pack_data["tags"], list):
            errors.append(ImportValidationError("tags", "tags 必须是列表", "error"))

        # 验证 dependencies
        if "dependencies" in data:
            deps = data["dependencies"]
            if not isinstance(deps, list):
                errors.append(ImportValidationError("dependencies", "dependencies 必须是列表", "error"))
            else:
                for i, dep in enumerate(deps):
                    if not isinstance(dep, dict):
                        errors.append(
                            ImportValidationError(f"dependencies[{i}]", "依赖项必须是字典", "severity")
                        )
                        continue

                    if "name" not in dep:
                        errors.append(
                            ImportValidationError(f"dependencies[{i}]", "缺少 name 字段", "error")
                        )

                    if "version_range" not in dep:
                        errors.append(
                            ImportValidationError(
                                f"dependencies[{i}]", "缺少 version_range 字段", "warning"
                            )
                        )

        # 验证 versions
        if "versions" in data:
            versions = data["versions"]
            if not isinstance(versions, list):
                errors.append(ImportValidationError("versions", "versions 必须是列表", "error"))
            else:
                for i, ver in enumerate(versions):
                    if not isinstance(ver, dict):
                        errors.append(ImportValidationError(f"versions[{i}]", "版本项必须是字典", "error"))
                        continue

                    if "version_string" not in ver:
                        errors.append(
                            ImportValidationError(f"versions[{i}]", "缺少 version_string 字段", "error")
                        )

        return errors

    def bulk_import(self, file_paths: List[str]) -> List[ImportResult]:
        """批量导入

        Args:
            file_paths: 文件路径列表

        Returns:
            导入结果列表
        """
        return [self.import_from_file(path) for path in file_paths]


class PackExporter:
    """Pack 导出器"""

    def __init__(self):
        """初始化导出器"""
        self._schema_version = "2.0"

    def export_pack(
        self,
        pack: PackListing,
        dependencies: Optional[List[dict]] = None,
        versions: Optional[List[dict]] = None,
        export_format: ExportFormat = ExportFormat.JSON,
    ) -> PackExport:
        """导出 Pack

        Args:
            pack: Pack 数据
            dependencies: 依赖列表
            versions: 版本列表
            export_format: 导出格式

        Returns:
            Pack 导出数据
        """
        if dependencies is None:
            dependencies = pack.dependencies if pack.dependencies else []

        export = PackExport(
            pack=pack,
            dependencies=[d if isinstance(d, dict) else d.to_dict() for d in dependencies],
            versions=versions or [],
            export_date=datetime.now().isoformat(),
            export_format=export_format,
            schema_version=self._schema_version,
        )

        return export

    def export_to_file(
        self,
        pack: PackListing,
        file_path: str,
        dependencies: Optional[List[dict]] = None,
        versions: Optional[List[dict]] = None,
        export_format: Optional[ExportFormat] = None,
    ) -> bool:
        """导出 Pack 到文件

        Args:
            pack: Pack 数据
            file_path: 目标文件路径
            dependencies: 依赖列表
            versions: 版本列表
            export_format: 导出格式 (可选，默认根据文件扩展名判断)

        Returns:
            是否成功
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # 根据扩展名确定格式（如果没有明确指定）
        if export_format is None:
            if path.suffix == ".json":
                export_format = ExportFormat.JSON
            elif path.suffix in [".yaml", ".yml"]:
                export_format = ExportFormat.YAML
            else:
                raise ValueError(f"不支持的文件格式: {path.suffix}")

        if export_format not in [ExportFormat.JSON, ExportFormat.YAML]:
            raise ValueError(f"不支持的文件格式: {export_format.value}")

        export = self.export_pack(pack, dependencies, versions, export_format)

        # 写入文件
        if export_format == ExportFormat.JSON:
            content = export.to_json()
        else:
            content = export.to_yaml()

        path.write_text(content, encoding="utf-8")

        return True

    def bulk_export(
        self,
        packs: List[PackListing],
        output_dir: str,
        export_format: ExportFormat = ExportFormat.JSON,
    ) -> Dict[str, bool]:
        """批量导出

        Args:
            packs: Pack 列表
            output_dir: 输出目录
            export_format: 导出格式

        Returns:
            导出结果 {pack_id: success}
        """
        results = {}

        for pack in packs:
            file_path = Path(output_dir) / f"{pack.pack_id}"
            if export_format == ExportFormat.JSON:
                file_path = file_path.with_suffix(".json")
            else:
                file_path = file_path.with_suffix(".yaml")

            try:
                success = self.export_to_file(pack, str(file_path), export_format=export_format)
                results[pack.pack_id] = success
            except Exception:
                results[pack.pack_id] = False

        return results

    def get_available_formats(self) -> List[ExportFormat]:
        """获取可用的导出格式

        Returns:
            格式列表
        """
        return [ExportFormat.JSON, ExportFormat.YAML]
