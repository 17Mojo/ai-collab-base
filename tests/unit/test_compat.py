"""
Unit tests for Pack Compatibility Manager

Tests for:
- CompatibilityStatus
- BreakingChangeType
- CompatibilityIssue
- CompatibilityReport
- CompatibilityChecker
- DependencyValidator
- check_pack_compatibility
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ai_collab.prompt_pack.compatibility import (
    BreakingChangeType,
    CompatibilityChecker,
    CompatibilityIssue,
    CompatibilityReport,
    CompatibilityStatus,
    DependencyValidator,
    check_pack_compatibility,
)
from ai_collab.prompt_pack.version import PackVersion


class TestCompatibilityStatus:
    """Test CompatibilityStatus functionality"""

    def test_status_values(self):
        """Test compatibility status values"""
        assert CompatibilityStatus.COMPATIBLE.value == "compatible"
        assert CompatibilityStatus.MINOR_UPDATE.value == "minor_update"
        assert CompatibilityStatus.MAJOR_UPDATE.value == "major_update"
        assert CompatibilityStatus.INCOMPATIBLE.value == "incompatible"
        assert CompatibilityStatus.UNKNOWN.value == "unknown"


class TestBreakingChangeType:
    """Test BreakingChangeType functionality"""

    def test_change_type_values(self):
        """Test breaking change type values"""
        assert BreakingChangeType.API_CHANGE.value == "api_change"
        assert BreakingChangeType.REMOVED_FIELD.value == "removed_field"
        assert BreakingChangeType.TYPE_CHANGE.value == "type_change"
        assert BreakingChangeType.BEHAVIOR_CHANGE.value == "behavior_change"
        assert BreakingChangeType.DEPRECATED.value == "deprecated"


class TestCompatibilityIssue:
    """Test CompatibilityIssue functionality"""

    def test_issue_creation(self):
        """Test creating compatibility issue"""
        issue = CompatibilityIssue(
            issue_type=BreakingChangeType.API_CHANGE,
            description="API endpoint removed",
            severity="critical",
            affected_apis=["/api/v1/users"],
            migration_path="Use /api/v2/users instead",
        )

        assert issue.issue_type == BreakingChangeType.API_CHANGE
        assert issue.description == "API endpoint removed"
        assert issue.severity == "critical"
        assert issue.affected_apis == ["/api/v1/users"]
        assert issue.migration_path == "Use /api/v2/users instead"

    def test_issue_with_optional_fields(self):
        """Test creating issue without optional fields"""
        issue = CompatibilityIssue(
            issue_type=BreakingChangeType.BEHAVIOR_CHANGE,
            description="Default value changed",
            severity="low",
            affected_apis=[],
        )

        assert issue.migration_path is None


class TestCompatibilityReport:
    """Test CompatibilityReport functionality"""

    def test_report_creation(self):
        """Test creating compatibility report"""
        source = PackVersion.parse("1.0.0")
        target = PackVersion.parse("2.0.0")
        timestamp = datetime.now()

        issue = CompatibilityIssue(
            issue_type=BreakingChangeType.API_CHANGE,
            description="Breaking change",
            severity="high",
            affected_apis=["all"],
        )

        report = CompatibilityReport(
            source_version=source,
            target_version=target,
            status=CompatibilityStatus.MAJOR_UPDATE,
            issues=[issue],
            summary="Summary",
            recommendations=["Test everything"],
            timestamp=timestamp,
        )

        assert report.source_version == source
        assert report.target_version == target
        assert report.status == CompatibilityStatus.MAJOR_UPDATE
        assert len(report.issues) == 1

    def test_is_compatible(self):
        """Test compatibility check"""
        source = PackVersion.parse("1.0.0")
        target = PackVersion.parse("1.0.1")

        # Compatible report
        report1 = CompatibilityReport(
            source_version=source,
            target_version=target,
            status=CompatibilityStatus.COMPATIBLE,
            issues=[],
            summary="Compatible",
            recommendations=[],
            timestamp=datetime.now(),
        )
        assert report1.is_compatible() is True

        # Minor update
        report2 = CompatibilityReport(
            source_version=source,
            target_version=target,
            status=CompatibilityStatus.MINOR_UPDATE,
            issues=[],
            summary="Minor update",
            recommendations=[],
            timestamp=datetime.now(),
        )
        assert report2.is_compatible() is True

        # Major update
        report3 = CompatibilityReport(
            source_version=source,
            target_version=PackVersion.parse("2.0.0"),
            status=CompatibilityStatus.MAJOR_UPDATE,
            issues=[],
            summary="Major update",
            recommendations=[],
            timestamp=datetime.now(),
        )
        assert report3.is_compatible() is False

    def test_get_critical_issues(self):
        """Test getting critical issues"""
        source = PackVersion.parse("1.0.0")
        target = PackVersion.parse("2.0.0")

        issues = [
            CompatibilityIssue(
                issue_type=BreakingChangeType.REMOVED_FIELD,
                description="Critical issue",
                severity="critical",
                affected_apis=["field1"],
            ),
            CompatibilityIssue(
                issue_type=BreakingChangeType.BEHAVIOR_CHANGE,
                description="Minor issue",
                severity="low",
                affected_apis=[],
            ),
        ]

        report = CompatibilityReport(
            source_version=source,
            target_version=target,
            status=CompatibilityStatus.INCOMPATIBLE,
            issues=issues,
            summary="Has critical issues",
            recommendations=[],
            timestamp=datetime.now(),
        )

        critical = report.get_critical_issues()
        assert len(critical) == 1
        assert critical[0].description == "Critical issue"

    def test_to_dict(self):
        """Test converting report to dict"""
        source = PackVersion.parse("1.0.0")
        target = PackVersion.parse("1.0.1")
        timestamp = datetime.now()

        issue = CompatibilityIssue(
            issue_type=BreakingChangeType.API_CHANGE,
            description="Test issue",
            severity="medium",
            affected_apis=["api1"],
        )

        report = CompatibilityReport(
            source_version=source,
            target_version=target,
            status=CompatibilityStatus.MINOR_UPDATE,
            issues=[issue],
            summary="Test summary",
            recommendations=["Rec1"],
            timestamp=timestamp,
        )

        data = report.to_dict()

        assert data["source_version"] == "1.0.0"
        assert data["target_version"] == "1.0.1"
        assert data["status"] == "minor_update"
        assert len(data["issues"]) == 1
        assert data["issues"][0]["type"] == "api_change"
        assert data["summary"] == "Test summary"
        assert data["timestamp"] == timestamp.isoformat()


class TestCompatibilityChecker:
    """Test CompatibilityChecker functionality"""

    def test_check_compatibility_no_changes(self):
        """Test compatibility check with no breaking changes"""
        checker = CompatibilityChecker()

        source = PackVersion.parse("1.0.0")
        target = PackVersion.parse("1.0.1")
        breaking_changes = []

        report = checker.check_compatibility(source, target, breaking_changes)

        assert report.source_version == source
        assert report.target_version == target
        assert report.status == CompatibilityStatus.COMPATIBLE
        assert len(report.issues) == 0
        assert report.is_compatible() is True

    def test_check_compatibility_major_upgrade(self):
        """Test compatibility check with major version upgrade"""
        checker = CompatibilityChecker()

        source = PackVersion.parse("1.0.0")
        target = PackVersion.parse("2.0.0")
        breaking_changes = []

        report = checker.check_compatibility(source, target, breaking_changes)

        assert report.status == CompatibilityStatus.MAJOR_UPDATE
        assert len(report.issues) == 1
        assert report.issues[0].severity == "high"
        assert report.issues[0].issue_type == BreakingChangeType.API_CHANGE

    def test_check_compatibility_minor_upgrade(self):
        """Test compatibility check with minor version upgrade"""
        checker = CompatibilityChecker()

        source = PackVersion.parse("1.0.0")
        target = PackVersion.parse("1.1.0")
        breaking_changes = []

        report = checker.check_compatibility(source, target, breaking_changes)

        assert report.status == CompatibilityStatus.MINOR_UPDATE
        assert len(report.issues) == 1
        assert report.issues[0].severity == "low"
        assert report.is_compatible() is True

    def test_check_compatibility_with_removed_field(self):
        """Test compatibility check with removed field"""
        checker = CompatibilityChecker()

        source = PackVersion.parse("1.0.0")
        target = PackVersion.parse("1.1.0")
        breaking_changes = ["Removed old_field from manifest"]

        report = checker.check_compatibility(source, target, breaking_changes)

        assert report.status == CompatibilityStatus.INCOMPATIBLE
        assert len(report.issues) == 2  # Minor upgrade issue + removed field
        critical_issues = report.get_critical_issues()
        assert len(critical_issues) == 1
        assert critical_issues[0].issue_type == BreakingChangeType.REMOVED_FIELD

    def test_check_compatibility_with_type_change(self):
        """Test compatibility check with type change"""
        checker = CompatibilityChecker()

        source = PackVersion.parse("1.0.0")
        target = PackVersion.parse("1.1.0")
        breaking_changes = ["Field type changed from string to int"]

        report = checker.check_compatibility(source, target, breaking_changes)

        type_issues = [i for i in report.issues if i.issue_type == BreakingChangeType.TYPE_CHANGE]
        assert len(type_issues) == 1
        assert type_issues[0].severity == "medium"

    def test_check_compatibility_with_behavior_change(self):
        """Test compatibility check with behavior change"""
        checker = CompatibilityChecker()

        source = PackVersion.parse("1.0.0")
        target = PackVersion.parse("1.0.1")
        breaking_changes = ["Default value changed for field X"]

        report = checker.check_compatibility(source, target, breaking_changes)

        behavior_issues = [
            i for i in report.issues if i.issue_type == BreakingChangeType.BEHAVIOR_CHANGE
        ]
        assert len(behavior_issues) == 1
        assert behavior_issues[0].severity == "medium"

    def test_generate_recommendations_compatible(self):
        """Test generating recommendations for compatible versions"""
        checker = CompatibilityChecker()

        source = PackVersion.parse("1.0.0")
        target = PackVersion.parse("1.0.1")
        breaking_changes = []

        report = checker.check_compatibility(source, target, breaking_changes)

        assert any("安全升级" in rec for rec in report.recommendations)

    def test_generate_recommendations_incompatible(self):
        """Test generating recommendations for incompatible versions"""
        checker = CompatibilityChecker()

        source = PackVersion.parse("1.0.0")
        target = PackVersion.parse("2.0.0")
        breaking_changes = ["Removed field X", "Changed API Y"]

        report = checker.check_compatibility(source, target, breaking_changes)

        assert any("迁移文档" in rec for rec in report.recommendations)
        assert any("测试环境" in rec for rec in report.recommendations)


class TestDependencyValidator:
    """Test DependencyValidator functionality"""

    def test_validate_no_dependencies(self):
        """Test validating pack with no dependencies"""

        # Mock pack manager that returns a pack with no dependencies
        class MockPack:
            def __init__(self):
                self.manifest = type("obj", (object,), {"dependencies": []})()

        class MockPackManager:
            def load_pack(self, name):
                if name == "no-dep-pack":
                    return MockPack()
                raise FileNotFoundError(f"Pack not found: {name}")

        mock_manager = MockPackManager()
        validator = DependencyValidator(mock_manager)

        result = validator.validate_dependencies("no-dep-pack")

        assert result["has_dependencies"] is False
        assert result["message"] == "No dependencies"

    def test_validate_with_dependencies(self):
        """Test validating pack with dependencies"""

        # Mock pack manager that returns a pack with dependencies
        class MockPackWithDeps:
            def __init__(self):
                self.manifest = type("obj", (object,), {"dependencies": ["dep-pack"]})()

        class MockDepPack:
            def __init__(self):
                self.manifest = type("obj", (object,), {"dependencies": [], "version": "2.0.0"})()

        class MockPackManagerWithDeps:
            def load_pack(self, name):
                if name == "main-pack":
                    return MockPackWithDeps()
                elif name == "dep-pack":
                    return MockDepPack()
                raise FileNotFoundError(f"Pack not found: {name}")

        mock_manager = MockPackManagerWithDeps()
        validator = DependencyValidator(mock_manager)

        result = validator.validate_dependencies("main-pack")

        assert result["has_dependencies"] is True
        assert result["all_valid"] is True
        assert len(result["dependencies"]) == 1
        assert result["dependencies"][0]["name"] == "dep-pack"
        assert result["dependencies"][0]["version"] == "2.0.0"

    def test_validate_with_version_requirement(self):
        """Test validating dependency with version requirement"""

        class MockPackWithDeps:
            def __init__(self):
                self.manifest = type("obj", (object,), {"dependencies": ["dep-pack"]})()

        class MockDepPack:
            def __init__(self):
                self.manifest = type("obj", (object,), {"dependencies": [], "version": "2.0.0"})()

        class MockPackManagerWithDeps:
            def load_pack(self, name):
                if name == "main-pack":
                    return MockPackWithDeps()
                elif name == "dep-pack":
                    return MockDepPack()
                raise FileNotFoundError(f"Pack not found: {name}")

        mock_manager = MockPackManagerWithDeps()
        validator = DependencyValidator(mock_manager)

        result = validator.validate_dependencies("main-pack", required_version="2.0.0")

        assert result["all_valid"] is True

        result2 = validator.validate_dependencies("main-pack", required_version="3.0.0")

        assert result2["all_valid"] is False
        assert "Required: 3.0.0" in result2["dependencies"][0]["message"]

    def test_check_dependency_conflicts(self):
        """Test checking dependency conflicts"""

        # Mock pack manager that returns packs for conflict testing
        class MockPack1:
            def __init__(self):
                self.manifest = type(
                    "obj", (object,), {"dependencies": ["shared-dep"], "version": "1.0.0"}
                )()

        class MockPack2:
            def __init__(self):
                self.manifest = type(
                    "obj", (object,), {"dependencies": ["shared-dep"], "version": "2.0.0"}
                )()

        class MockSharedDep:
            def __init__(self):
                self.manifest = type("obj", (object,), {"dependencies": [], "version": "1.5.0"})()

        class MockPackManager:
            def load_pack(self, name):
                if name == "pack1":
                    return MockPack1()
                elif name == "pack2":
                    return MockPack2()
                elif name == "shared-dep":
                    return MockSharedDep()
                raise FileNotFoundError(f"Pack not found: {name}")

        mock_manager = MockPackManager()
        validator = DependencyValidator(mock_manager)

        # No conflicts expected as both depend on same dep with same version
        conflicts = validator.check_dependency_conflicts(["pack1", "pack2"])

        assert len(conflicts) == 0


class TestCheckPackCompatibility:
    """Test check_pack_compatibility helper"""

    def test_check_pack_compatibility_generates_report(self):
        """check_pack_compatibility should load version manager and return report data"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            pack_dir = workspace / "packs" / "demo-pack"
            pack_dir.mkdir(parents=True)

            manifest = {
                "name": "demo-pack",
                "version": "1.0.0",
                "description": "demo",
                "author": "tester",
            }
            (pack_dir / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            version_metadata = {
                "current_version": "1.0.0",
                "latest_version": "1.0.0",
                "history": [],
                "api_version": "1.0",
                "breaking_changes": ["Removed old_field from manifest"],
            }
            (pack_dir / "VERSION.json").write_text(
                json.dumps(version_metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result = check_pack_compatibility(
                "demo-pack",
                "1.1.0",
                workspace=str(workspace),
            )

            assert result["pack_name"] == "demo-pack"
            assert result["current_version"] == "1.0.0"
            assert result["target_version"] == "1.1.0"
            assert result["status"] == CompatibilityStatus.INCOMPATIBLE.value
            assert result["critical_issues"] == 1
            assert result["report"]["issues"][0]["type"] in {
                BreakingChangeType.BEHAVIOR_CHANGE.value,
                BreakingChangeType.REMOVED_FIELD.value,
            }

    def test_check_pack_compatibility_missing_pack(self):
        """Missing pack should raise FileNotFoundError"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                check_pack_compatibility("missing-pack", "1.0.1", workspace=tmpdir)
