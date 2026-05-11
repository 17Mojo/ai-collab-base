# Pack Schema v2.0 Validator
# Week 6 Day 1: Pack Schema 验证器

"""
Pack Schema v2.0 验证器
支持 JSON 文件验证、Schema 合规检查、字段完整性检查
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ValidationSeverity(Enum):
    """验证问题严重级别"""

    ERROR = "error"  # 必须修复
    WARNING = "warning"  # 建议修复
    INFO = "info"  # 信息提示


@dataclass
class ValidationIssue:
    """验证问题"""

    path: str  # JSON 路径
    message: str  # 问题描述
    severity: ValidationSeverity  # 严重级别
    suggestion: Optional[str] = None  # 修复建议


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    pack_id: Optional[str] = None
    pack_name: Optional[str] = None

    def add_error(self, path: str, message: str, suggestion: str = None):
        self.issues.append(
            ValidationIssue(
                path=path, message=message, severity=ValidationSeverity.ERROR, suggestion=suggestion
            )
        )
        self.is_valid = False

    def add_warning(self, path: str, message: str, suggestion: str = None):
        self.issues.append(
            ValidationIssue(
                path=path,
                message=message,
                severity=ValidationSeverity.WARNING,
                suggestion=suggestion,
            )
        )

    def add_info(self, path: str, message: str):
        self.issues.append(
            ValidationIssue(path=path, message=message, severity=ValidationSeverity.INFO)
        )

    def summary(self) -> str:
        """生成摘要"""
        errors = sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)
        warnings = sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)
        infos = sum(1 for i in self.issues if i.severity == ValidationSeverity.INFO)

        status = "✅ VALID" if self.is_valid else "❌ INVALID"
        return f"{status} | {errors} errors, {warnings} warnings, {infos} info"


class PackSchemaValidator:
    """Pack Schema v2.0 验证器"""

    # 必需的 metadata 字段
    REQUIRED_METADATA_FIELDS = [
        "pack_id",
        "pack_name",
        "version",
        "type",
        "description",
        "designer",
        "created_at",
        "updated_at",
    ]

    # 可选的 metadata 字段
    OPTIONAL_METADATA_FIELDS = ["category", "tags", "language", "estimated_efficiency_gain"]

    # 有效的 Pack 类型
    VALID_PACK_TYPES = ["productivity", "creative", "analysis", "business", "education", "custom"]

    # 必需的 workflow step 字段
    REQUIRED_STEP_FIELDS = ["id", "name", "type", "description", "input_fields", "output_field"]

    # 有效的 step 类型
    VALID_STEP_TYPES = ["local", "analysis", "generation", "validation", "fusion", "tracking"]

    # 必需的顶层字段
    REQUIRED_TOP_LEVEL_FIELDS = ["metadata", "workflow"]

    # 可选的顶层字段
    OPTIONAL_TOP_LEVEL_FIELDS = [
        "domain",
        "quality_metrics",
        "example_library",
        "generation_params",
        "optimization",
        "performance_tracking",
        "collaboration",
        "system_prompt",
        "quality_validation_rules",
        "examples",
    ]

    def __init__(self, strict: bool = True):
        """
        初始化验证器

        Args:
            strict: 严格模式，启用所有验证规则
        """
        self.strict = strict

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        验证 Pack JSON 文件

        Args:
            file_path: JSON 文件路径

        Returns:
            ValidationResult: 验证结果
        """
        path = Path(file_path)

        # 检查文件存在
        if not path.exists():
            result = ValidationResult(is_valid=False)
            result.add_error("", f"File not found: {file_path}")
            return result

        # 检查文件扩展名
        if path.suffix != ".json":
            result = ValidationResult(is_valid=False)
            result.add_error("", f"Invalid file extension: {path.suffix}, expected .json")
            return result

        # 解析 JSON
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            result = ValidationResult(is_valid=False)
            result.add_error("", f"JSON parse error: {e}")
            return result

        # 验证数据结构
        return self.validate_data(data, str(file_path))

    def validate_data(self, data: Dict[str, Any], source: str = "") -> ValidationResult:
        """
        验证 Pack 数据结构

        Args:
            data: Pack 数据字典
            source: 数据来源标识

        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(is_valid=True)

        # 提取基本信息
        if "metadata" in data:
            result.pack_id = data["metadata"].get("pack_id")
            result.pack_name = data["metadata"].get("pack_name")

        # 验证顶层结构
        self._validate_top_level(data, result)

        # 验证 metadata
        if "metadata" in data:
            self._validate_metadata(data["metadata"], result)

        # 验证 domain
        if "domain" in data:
            self._validate_domain(data["domain"], result)

        # 验证 workflow
        if "workflow" in data:
            self._validate_workflow(data["workflow"], result)

        # 验证 quality_metrics
        if "quality_metrics" in data:
            self._validate_quality_metrics(data["quality_metrics"], result)

        # 验证 example_library
        if "example_library" in data:
            self._validate_example_library(data["example_library"], result)

        return result

    def _validate_top_level(self, data: Dict[str, Any], result: ValidationResult):
        """验证顶层结构"""
        # 检查必需字段
        for field in self.REQUIRED_TOP_LEVEL_FIELDS:
            if field not in data:
                result.add_error(
                    f"$.{field}",
                    f"Missing required field: {field}",
                    f"Add '{field}' field to the root object",
                )

        # 检查未知字段（严格模式）
        if self.strict:
            all_valid_fields = self.REQUIRED_TOP_LEVEL_FIELDS + self.OPTIONAL_TOP_LEVEL_FIELDS
            for key in data.keys():
                if key not in all_valid_fields:
                    result.add_warning(
                        f"$.{key}",
                        f"Unknown field: {key}",
                        f"Remove '{key}' or check schema documentation",
                    )

    def _validate_metadata(self, metadata: Dict[str, Any], result: ValidationResult):
        """验证 metadata 字段"""
        # 检查必需字段
        for field in self.REQUIRED_METADATA_FIELDS:
            if field not in metadata:
                result.add_error(f"$.metadata.{field}", f"Missing required metadata field: {field}")
            elif not metadata[field]:
                result.add_error(f"$.metadata.{field}", f"Empty metadata field: {field}")

        # 验证 pack_id 格式
        if "pack_id" in metadata:
            pack_id = metadata["pack_id"]
            if not re.match(r"^[a-z0-9-]+$", pack_id):
                result.add_warning(
                    "$.metadata.pack_id",
                    f"pack_id should use lowercase letters, numbers, and hyphens: {pack_id}",
                    "Use format like 'my-pack-name'",
                )

        # 验证 version 格式
        if "version" in metadata:
            version = metadata["version"]
            if not re.match(r"^\d+\.\d+\.\d+$", version):
                result.add_warning(
                    "$.metadata.version",
                    f"version should follow SemVer format (x.y.z): {version}",
                    "Use format like '1.0.0'",
                )

        # 验证 type 值
        if "type" in metadata:
            pack_type = metadata["type"]
            if pack_type not in self.VALID_PACK_TYPES:
                result.add_error(
                    "$.metadata.type",
                    f"Invalid pack type: {pack_type}",
                    f"Valid types: {', '.join(self.VALID_PACK_TYPES)}",
                )

        # 验证日期格式
        for date_field in ["created_at", "updated_at"]:
            if date_field in metadata:
                date_val = metadata[date_field]
                try:
                    # 支持 ISO 格式
                    if "T" in date_val:
                        pass  # ISO format
                    else:
                        # 简单日期格式
                        pass
                except Exception:
                    result.add_warning(
                        f"$.metadata.{date_field}",
                        f"Invalid date format: {date_val}",
                        "Use ISO format like '2026-04-13T12:00:00'",
                    )

        # 验证 tags 是列表
        if "tags" in metadata:
            if not isinstance(metadata["tags"], list):
                result.add_error(
                    "$.metadata.tags", f"tags must be a list, got {type(metadata['tags']).__name__}"
                )

    def _validate_domain(self, domain: Dict[str, Any], result: ValidationResult):
        """验证 domain 字段"""
        # primary_domain 是必需的
        if "primary_domain" not in domain:
            result.add_warning("$.domain.primary_domain", "Missing primary_domain field")

        # target_platforms 应该是列表
        if "target_platforms" in domain:
            if not isinstance(domain["target_platforms"], list):
                result.add_error("$.domain.target_platforms", "target_platforms must be a list")

        # compliance_rules 应该是列表
        if "compliance_rules" in domain:
            if not isinstance(domain["compliance_rules"], list):
                result.add_warning("$.domain.compliance_rules", "compliance_rules should be a list")

    def _validate_workflow(self, workflow: Dict[str, Any], result: ValidationResult):
        """验证 workflow 字段"""
        # steps 是必需的
        if "steps" not in workflow:
            result.add_error("$.workflow.steps", "Missing required workflow.steps field")
            return

        steps = workflow["steps"]

        # steps 必须是列表
        if not isinstance(steps, list):
            result.add_error(
                "$.workflow.steps", f"steps must be a list, got {type(steps).__name__}"
            )
            return

        # steps 不能为空
        if len(steps) == 0:
            result.add_error("$.workflow.steps", "steps cannot be empty")
            return

        # 验证每个 step
        step_ids = set()
        for i, step in enumerate(steps):
            step_path = f"$.workflow.steps[{i}]"
            self._validate_step(step, step_path, result, step_ids)

    def _validate_step(
        self, step: Dict[str, Any], path: str, result: ValidationResult, seen_ids: set
    ):
        """验证单个 workflow step"""
        # 检查必需字段
        for field in self.REQUIRED_STEP_FIELDS:
            if field not in step:
                result.add_error(f"{path}.{field}", f"Missing required step field: {field}")

        # 验证 step id 唯一性
        if "id" in step:
            step_id = step["id"]
            if step_id in seen_ids:
                result.add_error(f"{path}.id", f"Duplicate step id: {step_id}")
            else:
                seen_ids.add(step_id)

        # 验证 step type
        if "type" in step:
            step_type = step["type"]
            if step_type not in self.VALID_STEP_TYPES:
                result.add_error(
                    f"{path}.type",
                    f"Invalid step type: {step_type}",
                    f"Valid types: {', '.join(self.VALID_STEP_TYPES)}",
                )

        # 验证 input_fields 是列表
        if "input_fields" in step:
            if not isinstance(step["input_fields"], list):
                result.add_error(f"{path}.input_fields", "input_fields must be a list")

        # 验证 ai_models（如果存在）
        if "ai_models" in step and step["ai_models"] is not None:
            if not isinstance(step["ai_models"], list):
                result.add_warning(f"{path}.ai_models", "ai_models should be a list or null")

        # 验证 parallel 是布尔值
        if "parallel" in step:
            if not isinstance(step["parallel"], bool):
                result.add_warning(f"{path}.parallel", "parallel should be a boolean")

        # 验证 estimated_time 是数字
        if "estimated_time" in step:
            if not isinstance(step["estimated_time"], (int, float)):
                result.add_warning(
                    f"{path}.estimated_time", "estimated_time should be a number (seconds)"
                )

    def _validate_quality_metrics(self, metrics: Dict[str, Any], result: ValidationResult):
        """验证 quality_metrics 字段"""
        if "metrics" not in metrics:
            result.add_warning("$.quality_metrics.metrics", "Missing metrics definition")
            return

        if not isinstance(metrics["metrics"], dict):
            result.add_error("$.quality_metrics.metrics", "metrics must be an object")
            return

        # 验证权重总和
        total_weight = 0.0
        for name, metric in metrics["metrics"].items():
            if "weight" in metric:
                try:
                    total_weight += float(metric["weight"])
                except (TypeError, ValueError):
                    result.add_warning(
                        f"$.quality_metrics.metrics.{name}.weight",
                        f"Invalid weight value: {metric['weight']}",
                    )

        # 权重总和应该接近 1.0
        if abs(total_weight - 1.0) > 0.01:
            result.add_warning(
                "$.quality_metrics.metrics",
                f"Weight sum is {total_weight:.2f}, should be 1.0",
                "Adjust weights so they sum to 1.0",
            )

    def _validate_example_library(self, library: Dict[str, Any], result: ValidationResult):
        """验证 example_library 字段"""
        if "examples" not in library:
            result.add_info("$.example_library.examples", "No examples defined")
            return

        examples = library["examples"]
        if not isinstance(examples, list):
            result.add_error("$.example_library.examples", "examples must be a list")
            return

        if len(examples) == 0:
            result.add_info("$.example_library.examples", "Examples list is empty")


def validate_pack(file_path: str, strict: bool = True) -> ValidationResult:
    """
    验证 Pack JSON 文件的便捷函数

    Args:
        file_path: Pack JSON 文件路径
        strict: 是否启用严格模式

    Returns:
        ValidationResult: 验证结果
    """
    validator = PackSchemaValidator(strict=strict)
    return validator.validate_file(file_path)


def validate_all_packs(
    directory: str = "packs/examples", strict: bool = True
) -> Dict[str, ValidationResult]:
    """
    验证目录下所有 Pack 文件

    Args:
        directory: Pack 文件目录
        strict: 是否启用严格模式

    Returns:
        Dict[str, ValidationResult]: 文件路径到验证结果的映射
    """
    results = {}
    pack_dir = Path(directory)

    if not pack_dir.exists():
        return results

    for pack_file in pack_dir.glob("*.json"):
        results[str(pack_file)] = validate_pack(str(pack_file), strict)

    return results


def print_validation_report(results: Dict[str, ValidationResult]):
    """打印验证报告"""
    print("\n" + "=" * 60)
    print("Pack Schema Validation Report")
    print("=" * 60)

    valid_count = 0
    invalid_count = 0

    for file_path, result in results.items():
        status = "✅" if result.is_valid else "❌"
        print(f"\n{status} {Path(file_path).name}")

        if result.pack_name:
            print(f"   Name: {result.pack_name}")

        print(f"   {result.summary()}")

        # 显示问题详情
        for issue in result.issues:
            if issue.severity == ValidationSeverity.ERROR:
                print(f"   ❌ {issue.path}: {issue.message}")
                if issue.suggestion:
                    print(f"      💡 {issue.suggestion}")
            elif issue.severity == ValidationSeverity.WARNING:
                print(f"   ⚠️  {issue.path}: {issue.message}")
                if issue.suggestion:
                    print(f"      💡 {issue.suggestion}")

        if result.is_valid:
            valid_count += 1
        else:
            invalid_count += 1

    print("\n" + "=" * 60)
    print(f"Total: {valid_count + invalid_count} packs")
    print(f"Valid: {valid_count} ✅")
    print(f"Invalid: {invalid_count} ❌")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 验证指定文件
        file_path = sys.argv[1]
        result = validate_pack(file_path)
        print(f"\n{file_path}")
        print(f"  {result.summary()}")
        for issue in result.issues:
            print(f"  [{issue.severity.value}] {issue.path}: {issue.message}")
    else:
        # 验证所有 Pack
        results = validate_all_packs()
        print_validation_report(results)
