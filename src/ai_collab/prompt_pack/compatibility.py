"""
Pack 版本兼容性检查模块

实现 Pack 版本兼容性检查功能：
- API 破坏性变更检测
- 版本依赖验证
- 兼容性报告生成
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .version import PackVersion, create_version_manager


class CompatibilityStatus(Enum):
    """兼容性状态"""

    COMPATIBLE = "compatible"  # 完全兼容
    MINOR_UPDATE = "minor_update"  # 需要小更新
    MAJOR_UPDATE = "major_update"  # 需要大更新
    INCOMPATIBLE = "incompatible"  # 不兼容
    UNKNOWN = "unknown"  # 未知


class BreakingChangeType(Enum):
    """破坏性变更类型"""

    API_CHANGE = "api_change"  # API 变更
    REMOVED_FIELD = "removed_field"  # 字段删除
    TYPE_CHANGE = "type_change"  # 类型变更
    BEHAVIOR_CHANGE = "behavior_change"  # 行为变更
    DEPRECATED = "deprecated"  # 已废弃


@dataclass
class CompatibilityIssue:
    """兼容性问题"""

    issue_type: BreakingChangeType
    description: str
    severity: str  # low, medium, high, critical
    affected_apis: List[str]
    migration_path: Optional[str] = None


@dataclass
class CompatibilityReport:
    """兼容性报告"""

    source_version: PackVersion
    target_version: PackVersion
    status: CompatibilityStatus
    issues: List[CompatibilityIssue]
    summary: str
    recommendations: List[str]
    timestamp: datetime

    def is_compatible(self) -> bool:
        """检查是否兼容"""
        return self.status in [CompatibilityStatus.COMPATIBLE, CompatibilityStatus.MINOR_UPDATE]

    def get_critical_issues(self) -> List[CompatibilityIssue]:
        """获取关键问题"""
        return [issue for issue in self.issues if issue.severity == "critical"]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_version": str(self.source_version),
            "target_version": str(self.target_version),
            "status": self.status.value,
            "issues": [
                {
                    "type": issue.issue_type.value,
                    "description": issue.description,
                    "severity": issue.severity,
                    "affected_apis": issue.affected_apis,
                    "migration_path": issue.migration_path,
                }
                for issue in self.issues
            ],
            "summary": self.summary,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


class CompatibilityChecker:
    """兼容性检查器"""

    def __init__(self):
        """初始化兼容性检查器"""
        self.known_api_breaking_changes = {
            "api-change": ["removed endpoint", "changed parameter name"],
            "removed-field": ["removed manifest field", "removed schema field"],
            "type-change": ["field type changed", "enum values changed"],
            "behavior-change": ["default value changed", "validation rule changed"],
        }

    def check_compatibility(
        self, source_version: PackVersion, target_version: PackVersion, breaking_changes: List[str]
    ) -> CompatibilityReport:
        """
        检查版本兼容性

        Args:
            source_version: 源版本（当前版本）
            target_version: 目标版本（新版本）
            breaking_changes: 破坏性变更列表

        Returns:
            兼容性报告
        """
        issues: List[CompatibilityIssue] = []

        # 分析版本跳跃
        if target_version.major > source_version.major:
            # 主版本升级，可能有不兼容变更
            issues.append(self._create_major_upgrade_issue(source_version, target_version))
        elif target_version.minor > source_version.minor:
            # 次版本升级，通常兼容但可能需要迁移
            issues.extend(self._create_minor_update_issues(source_version, target_version))

        # 分析破坏性变更
        for change in breaking_changes:
            issue = self._analyze_breaking_change(change, source_version, target_version)
            if issue:
                issues.append(issue)

        # 确定兼容性状态
        status = self._determine_status(source_version, target_version, issues)

        # 生成建议
        recommendations = self._generate_recommendations(source_version, target_version, issues)

        # 生成摘要
        summary = self._generate_summary(source_version, target_version, status, len(issues))

        return CompatibilityReport(
            source_version=source_version,
            target_version=target_version,
            status=status,
            issues=issues,
            summary=summary,
            recommendations=recommendations,
            timestamp=datetime.now(),
        )

    def _create_major_upgrade_issue(
        self, source: PackVersion, target: PackVersion
    ) -> CompatibilityIssue:
        """创建主版本升级问题"""
        return CompatibilityIssue(
            issue_type=BreakingChangeType.API_CHANGE,
            description=f"Major version upgrade from {source} to {target} may introduce breaking changes",
            severity="high",
            affected_apis=["all"],
            migration_path=f"Review pack documentation for migration guide from {source} to {target}",
        )

    def _create_minor_update_issues(
        self, source: PackVersion, target: PackVersion
    ) -> List[CompatibilityIssue]:
        """创建次版本更新问题"""
        issues: List[CompatibilityIssue] = []

        # 检查常见的次版本变更
        issues.append(
            CompatibilityIssue(
                issue_type=BreakingChangeType.BEHAVIOR_CHANGE,
                description=f"Minor version update from {source} to {target}",
                severity="low",
                affected_apis=[],
                migration_path="通常兼容，建议测试关键功能",
            )
        )

        return issues

    def _analyze_breaking_change(
        self, change: str, source: PackVersion, target: PackVersion
    ) -> Optional[CompatibilityIssue]:
        """
        分析破坏性变更

        Args:
            change: 变更描述
            source: 源版本
            target: 目标版本

        Returns:
            兼容性问题，如果没有破坏性则返回 None
        """
        change_lower = change.lower()

        # 检测 API 变更
        if any(keyword in change_lower for keyword in ["removed", "deleted"]):
            return CompatibilityIssue(
                issue_type=BreakingChangeType.REMOVED_FIELD,
                description=f"Removed field/API: {change}",
                severity="critical",
                affected_apis=[change],
                migration_path="检查 pack 文档或使用旧版本",
            )

        # 检测类型变更
        if "type change" in change_lower or "type changed" in change_lower:
            return CompatibilityIssue(
                issue_type=BreakingChangeType.TYPE_CHANGE,
                description=f"Type change: {change}",
                severity="medium",
                affected_apis=[change],
                migration_path="更新代码以适应新类型",
            )

        # 检测行为变更
        if "behavior change" in change_lower or "default value" in change_lower:
            return CompatibilityIssue(
                issue_type=BreakingChangeType.BEHAVIOR_CHANGE,
                description=f"Behavior change: {change}",
                severity="medium",
                affected_apis=[change],
                migration_path="测试受影响的功能",
            )

        return None

    def _determine_status(
        self, source: PackVersion, target: PackVersion, issues: List[CompatibilityIssue]
    ) -> CompatibilityStatus:
        """确定兼容性状态"""
        # 如果没有问题，完全兼容
        if not issues:
            return CompatibilityStatus.COMPATIBLE

        # 如果有关键问题，不兼容
        critical_issues = [i for i in issues if i.severity == "critical"]
        if critical_issues:
            return CompatibilityStatus.INCOMPATIBLE

        # 如果有高严重性问题，需要主版本升级
        high_issues = [i for i in issues if i.severity == "high"]
        if high_issues:
            return CompatibilityStatus.MAJOR_UPDATE

        # 次版本升级通常兼容
        return CompatibilityStatus.MINOR_UPDATE

    def _generate_recommendations(
        self, source: PackVersion, target: PackVersion, issues: List[CompatibilityIssue]
    ) -> List[str]:
        """生成升级建议"""
        recommendations: List[str] = []

        if not issues:
            recommendations.append(f"安全升级到 {target}（完全兼容）")
        else:
            recommendations.append(f"升级前请测试以下功能: {', '.join([i.description for i in issues[:3]])}")

            if any(i.severity == "critical" for i in issues):
                recommendations.append(f"建议查看 {source} 到 {target} 的迁移文档")
                recommendations.append("考虑在测试环境中先验证")

            if target.major > source.major:
                recommendations.append("主版本升级，请检查是否有不兼容变更")

        return recommendations

    def _generate_summary(
        self,
        source: PackVersion,
        target: PackVersion,
        status: CompatibilityStatus,
        issue_count: int,
    ) -> str:
        """生成兼容性摘要"""
        if status == CompatibilityStatus.COMPATIBLE:
            return f"{source} → {target}: 完全兼容，可以安全升级"
        elif status == CompatibilityStatus.MINOR_UPDATE:
            return f"{source} → {target}: 存在 {issue_count} 个非关键变更，建议测试后升级"
        elif status == CompatibilityStatus.MAJOR_UPDATE:
            return f"{source} → {target}: 存在 {issue_count} 个重要变更，需要仔细审查"
        elif status == CompatibilityStatus.INCOMPATIBLE:
            return f"{source} → {target}: 存在 {issue_count} 个关键变更，不兼容，请查看迁移文档"
        else:
            return f"{source} → {target}: 兼容性状态未知"


class DependencyValidator:
    """依赖验证器"""

    def __init__(self, pack_manager):
        """
        初始化依赖验证器

        Args:
            pack_manager: Pack 管理器实例
        """
        self.pack_manager = pack_manager

    def validate_dependencies(
        self, pack_name: str, required_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        验证 Pack 依赖

        Args:
            pack_name: Pack 名称
            required_version: 需要的版本（可选）

        Returns:
            验证结果字典
        """
        pack = self.pack_manager.load_pack(pack_name)
        dependencies = pack.manifest.dependencies

        if not dependencies:
            return {"has_dependencies": False, "message": "No dependencies", "dependencies": []}

        results = []
        all_valid = True

        for dep_name in dependencies:
            try:
                dep_pack = self.pack_manager.load_pack(dep_name)
                dep_version = PackVersion.parse(dep_pack.manifest.version)

                # 检查版本要求
                version_ok = True
                version_message = "OK"

                if required_version:
                    required = PackVersion.parse(required_version)
                    if dep_version < required:
                        version_ok = False
                        version_message = (
                            f"Required: {required_version}, Found: {dep_pack.manifest.version}"
                        )

                results.append(
                    {
                        "name": dep_name,
                        "version": dep_pack.manifest.version,
                        "valid": version_ok,
                        "message": version_message,
                    }
                )

                if not version_ok:
                    all_valid = False

            except FileNotFoundError:
                results.append(
                    {
                        "name": dep_name,
                        "version": None,
                        "valid": False,
                        "message": "Dependency not found",
                    }
                )
                all_valid = False

        return {
            "has_dependencies": True,
            "all_valid": all_valid,
            "dependencies": results,
            "message": "All dependencies valid" if all_valid else "Some dependencies are invalid",
        }

    def check_dependency_conflicts(self, pack_names: List[str]) -> Dict[str, List[str]]:
        """
        检查依赖冲突

        Args:
            pack_names: Pack 名称列表

        Returns:
            依赖冲突字典 {pack_name: [conflicting_packs]}
        """
        conflicts: Dict[str, List[str]] = {}

        # 收集所有依赖
        all_dependencies: Dict[str, List[str]] = {}
        for pack_name in pack_names:
            try:
                pack = self.pack_manager.load_pack(pack_name)
                all_dependencies[pack_name] = pack.manifest.dependencies
            except FileNotFoundError:
                all_dependencies[pack_name] = []

        # 查找冲突（不同 Pack 依赖同一依赖但需要不同版本）
        dependency_versions: Dict[str, Dict[str, str]] = {}  # dependency -> {pack -> version}

        for pack_name, deps in all_dependencies.items():
            for dep_name in deps:
                try:
                    dep_pack = self.pack_manager.load_pack(dep_name)
                    version = dep_pack.manifest.version

                    if dep_name not in dependency_versions:
                        dependency_versions[dep_name] = {}

                    dependency_versions[dep_name][pack_name] = version
                except FileNotFoundError:
                    continue

        # 检查版本冲突
        for dep_name, versions_by_pack in dependency_versions.items():
            if len(versions_by_pack) > 1:
                # 检查是否有版本冲突
                versions = set(versions_by_pack.values())
                if len(versions) > 1:
                    for pack_name in versions_by_pack:
                        if pack_name not in conflicts:
                            conflicts[pack_name] = []
                        conflicts[pack_name].append(
                            f"{dep_name} has conflicting versions: {versions}"
                        )

        return conflicts


def check_pack_compatibility(
    pack_name: str, target_version: str, workspace: str = "."
) -> Dict[str, Any]:
    """
    检查 Pack 兼容性（便捷函数）

    Args:
        pack_name: Pack 名称
        target_version: 目标版本
        workspace: 工作区路径

    Returns:
        兼容性检查结果
    """
    manager = create_version_manager(pack_name, workspace)
    current = manager.get_current_version()
    target = PackVersion.parse(target_version)

    metadata = manager.get_version_metadata()
    breaking_changes = metadata.breaking_changes if metadata else []

    checker = CompatibilityChecker()
    report = checker.check_compatibility(current, target, breaking_changes)

    return {
        "pack_name": pack_name,
        "current_version": str(current),
        "target_version": str(target),
        "is_compatible": report.is_compatible(),
        "status": report.status.value,
        "issues_count": len(report.issues),
        "critical_issues": len(report.get_critical_issues()),
        "report": report.to_dict(),
    }
