"""
pack/schema_validator.py 的最小测试覆盖
目标：从 0% 到 85%+ 局部覆盖率
"""

import json

import pytest

from ai_collab.pack.schema_validator import (
    PackSchemaValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    print_validation_report,
    validate_all_packs,
    validate_pack,
)


@pytest.fixture
def minimal_valid_pack():
    """最小合法 pack — 对齐 schema_v2.py PromptPackV2 的 9 个必需顶层字段"""
    return {
        "metadata": {
            "pack_id": "test-pack",
            "pack_name": "Test Pack",
            "version": "1.0.0",
            "type": "productivity",
            "description": "desc",
            "designer": "me",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-02T00:00:00",
        },
        "domain": {
            "primary_domain": "test",
        },
        "workflow": {
            "steps": [
                {
                    "id": "s1",
                    "name": "step1",
                    "type": "local",
                    "description": "d",
                    "input_fields": ["x"],
                    "output_field": "y",
                }
            ]
        },
        "quality_metrics": {
            "metrics": {
                "m1": {
                    "name": "m1",
                    "description": "metric",
                    "check_method": "check",
                    "weight": 1.0,
                }
            }
        },
        "example_library": {},
        "generation_params": {},
        "optimization": {},
        "performance_tracking": {},
        "collaboration": {},
    }


@pytest.fixture
def tmp_json(tmp_path):
    def _write(name, data):
        p = tmp_path / name
        p.write_text(json.dumps(data), encoding="utf-8")
        return p
    return _write


# ======================= 数据类 & 枚举 =======================

class TestEnums:
    def test_validation_severity_values(self):
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"


class TestValidationIssue:
    def test_issue_init(self):
        i = ValidationIssue(
            path="$.x", message="m", severity=ValidationSeverity.ERROR, suggestion="fix"
        )
        assert i.path == "$.x"
        assert i.suggestion == "fix"


class TestValidationResult:
    def test_default_valid(self):
        r = ValidationResult(is_valid=True)
        assert r.is_valid is True
        assert r.issues == []
        assert r.pack_id is None

    def test_add_error_invalidates(self):
        r = ValidationResult(is_valid=True)
        r.add_error("$.x", "bad")
        assert r.is_valid is False
        assert len(r.issues) == 1
        assert r.issues[0].severity == ValidationSeverity.ERROR

    def test_add_warning_keeps_valid(self):
        r = ValidationResult(is_valid=True)
        r.add_warning("$.x", "warn", suggestion="fix")
        assert r.is_valid is True
        assert r.issues[0].suggestion == "fix"

    def test_add_info(self):
        r = ValidationResult(is_valid=True)
        r.add_info("$.x", "info")
        assert r.issues[0].severity == ValidationSeverity.INFO

    def test_summary_valid(self):
        r = ValidationResult(is_valid=True)
        r.add_warning("$.a", "w")
        r.add_info("$.b", "i")
        assert "VALID" in r.summary()
        assert "0 errors" in r.summary()

    def test_summary_invalid(self):
        r = ValidationResult(is_valid=True)
        r.add_error("$.a", "e")
        r.add_warning("$.b", "w")
        s = r.summary()
        assert "INVALID" in s
        assert "1 errors" in s
        assert "1 warnings" in s


# ======================= validate_file =======================

class TestValidateFile:
    def test_file_not_found(self):
        r = PackSchemaValidator().validate_file("/nonexistent/path/x.json")
        assert r.is_valid is False
        assert "File not found" in r.issues[0].message

    def test_wrong_extension(self, tmp_path):
        bad = tmp_path / "x.txt"
        bad.write_text("{}")
        r = PackSchemaValidator().validate_file(str(bad))
        assert r.is_valid is False
        assert "extension" in r.issues[0].message.lower()

    def test_invalid_json(self, tmp_path):
        bad = tmp_path / "x.json"
        bad.write_text("{not json")
        r = PackSchemaValidator().validate_file(str(bad))
        assert r.is_valid is False
        assert "JSON parse error" in r.issues[0].message

    def test_valid_pack_via_file(self, tmp_json, minimal_valid_pack):
        f = tmp_json("good.json", minimal_valid_pack)
        r = PackSchemaValidator().validate_file(str(f))
        assert r.is_valid is True
        assert r.pack_id == "test-pack"
        assert r.pack_name == "Test Pack"


# ======================= validate_data — 顶层结构 =======================

class TestValidateTopLevel:
    def test_missing_metadata(self):
        v = PackSchemaValidator()
        r = v.validate_data({"workflow": {"steps": []}})
        assert any("metadata" in i.message for i in r.issues if i.severity == ValidationSeverity.ERROR)

    def test_missing_workflow(self):
        v = PackSchemaValidator()
        r = v.validate_data({"metadata": {}})
        assert any("workflow" in i.message for i in r.issues if i.severity == ValidationSeverity.ERROR)

    def test_strict_mode_warns_unknown_field(self, minimal_valid_pack):
        minimal_valid_pack["junk"] = "x"
        v = PackSchemaValidator(strict=True)
        r = v.validate_data(minimal_valid_pack)
        assert any(i.severity == ValidationSeverity.WARNING for i in r.issues)

    def test_non_strict_allows_unknown_field(self, minimal_valid_pack):
        minimal_valid_pack["junk"] = "x"
        v = PackSchemaValidator(strict=False)
        r = v.validate_data(minimal_valid_pack)
        assert not any(i.severity == ValidationSeverity.WARNING for i in r.issues)


# ======================= metadata 校验 =======================

class TestValidateMetadata:
    def test_missing_required_field(self, minimal_valid_pack):
        del minimal_valid_pack["metadata"]["pack_id"]
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("pack_id" in i.message for i in r.issues)

    def test_empty_required_field(self, minimal_valid_pack):
        minimal_valid_pack["metadata"]["pack_id"] = ""
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("Empty" in i.message for i in r.issues)

    def test_invalid_pack_id_format_warns(self, minimal_valid_pack):
        minimal_valid_pack["metadata"]["pack_id"] = "Bad_ID!"
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("lowercase" in i.message.lower() for i in r.issues)

    def test_valid_pack_id_no_warning(self, minimal_valid_pack):
        minimal_valid_pack["metadata"]["pack_id"] = "ok-1"
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert not any("lowercase" in i.message.lower() for i in r.issues)

    def test_invalid_version_format_warns(self, minimal_valid_pack):
        minimal_valid_pack["metadata"]["version"] = "v1"
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("SemVer" in i.message for i in r.issues)

    def test_invalid_type(self, minimal_valid_pack):
        minimal_valid_pack["metadata"]["type"] = "bogus"
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("Invalid pack type" in i.message for i in r.issues)

    def test_tags_must_be_list(self, minimal_valid_pack):
        minimal_valid_pack["metadata"]["tags"] = "tag1"
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("tags must be a list" in i.message for i in r.issues)

    def test_tags_as_list_ok(self, minimal_valid_pack):
        minimal_valid_pack["metadata"]["tags"] = ["a", "b"]
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        # 不应有 tags 相关错误
        assert not any("tags" in i.message and i.severity == ValidationSeverity.ERROR for i in r.issues)


# ======================= domain 校验 =======================

class TestValidateDomain:
    def test_missing_primary_domain_errors(self, minimal_valid_pack):
        minimal_valid_pack["domain"] = {}
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any(
            "primary_domain" in i.message and i.severity == ValidationSeverity.ERROR
            for i in r.issues
        )

    def test_target_platforms_not_list(self, minimal_valid_pack):
        minimal_valid_pack["domain"] = {"primary_domain": "x", "target_platforms": "web"}
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("target_platforms" in i.message for i in r.issues)

    def test_compliance_rules_not_list_warns(self, minimal_valid_pack):
        minimal_valid_pack["domain"] = {
            "primary_domain": "x",
            "compliance_rules": "rule1",
        }
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("compliance_rules" in i.message for i in r.issues)

    def test_valid_domain(self, minimal_valid_pack):
        minimal_valid_pack["domain"] = {
            "primary_domain": "x",
            "target_platforms": ["web"],
            "compliance_rules": ["r1"],
        }
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        domain_issues = [i for i in r.issues if i.path.startswith("$.domain")]
        assert len(domain_issues) == 0


# ======================= workflow 校验 =======================

class TestValidateWorkflow:
    def test_missing_steps(self, minimal_valid_pack):
        minimal_valid_pack["workflow"] = {}
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("Missing required workflow.steps" in i.message for i in r.issues)

    def test_steps_not_list(self, minimal_valid_pack):
        minimal_valid_pack["workflow"]["steps"] = "not a list"
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("steps must be a list" in i.message for i in r.issues)

    def test_empty_steps(self, minimal_valid_pack):
        minimal_valid_pack["workflow"]["steps"] = []
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("steps cannot be empty" in i.message for i in r.issues)


class TestValidateStep:
    def test_step_missing_required_field(self, minimal_valid_pack):
        s = minimal_valid_pack["workflow"]["steps"][0]
        del s["id"]
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("Missing required step field: id" in i.message for i in r.issues)

    def test_duplicate_step_id(self, minimal_valid_pack):
        s = minimal_valid_pack["workflow"]["steps"][0]
        s["id"] = "dup"
        minimal_valid_pack["workflow"]["steps"].append(dict(s))
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("Duplicate step id" in i.message for i in r.issues)

    def test_invalid_step_type(self, minimal_valid_pack):
        minimal_valid_pack["workflow"]["steps"][0]["type"] = "bogus"
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("Invalid step type" in i.message for i in r.issues)

    def test_input_fields_not_list(self, minimal_valid_pack):
        minimal_valid_pack["workflow"]["steps"][0]["input_fields"] = "x"
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("input_fields must be a list" in i.message for i in r.issues)

    def test_ai_models_not_list_warns(self, minimal_valid_pack):
        minimal_valid_pack["workflow"]["steps"][0]["ai_models"] = "gpt"
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("ai_models" in i.message for i in r.issues)

    def test_parallel_not_bool_warns(self, minimal_valid_pack):
        minimal_valid_pack["workflow"]["steps"][0]["parallel"] = "yes"
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("parallel" in i.message for i in r.issues)

    def test_estimated_time_not_number_warns(self, minimal_valid_pack):
        minimal_valid_pack["workflow"]["steps"][0]["estimated_time"] = "long"
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("estimated_time" in i.message for i in r.issues)

    def test_ai_models_none_ok(self, minimal_valid_pack):
        minimal_valid_pack["workflow"]["steps"][0]["ai_models"] = None
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        # None 不应触发 ai_models 告警
        assert not any("ai_models" in i.message for i in r.issues)


# ======================= quality_metrics 校验 =======================

class TestValidateQualityMetrics:
    def test_missing_metrics(self, minimal_valid_pack):
        minimal_valid_pack["quality_metrics"] = {}
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("metrics" in i.message for i in r.issues)

    def test_metrics_not_dict(self, minimal_valid_pack):
        minimal_valid_pack["quality_metrics"] = {"metrics": "x"}
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("metrics must be an object" in i.message for i in r.issues)

    def test_weight_sum_not_one_warns(self, minimal_valid_pack):
        minimal_valid_pack["quality_metrics"] = {
            "metrics": {
                "accuracy": {"weight": 0.3},
                "speed": {"weight": 0.3},
            }
        }
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("Weight sum" in i.message for i in r.issues)

    def test_invalid_weight_value_warns(self, minimal_valid_pack):
        minimal_valid_pack["quality_metrics"] = {
            "metrics": {
                "a": {"weight": "bad"},
                "b": {"weight": 0.5},
            }
        }
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any("Invalid weight" in i.message for i in r.issues)

    def test_valid_metrics(self, minimal_valid_pack):
        minimal_valid_pack["quality_metrics"] = {
            "metrics": {
                "a": {"weight": 0.6},
                "b": {"weight": 0.4},
            }
        }
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        qm_issues = [i for i in r.issues if i.path.startswith("$.quality_metrics")]
        assert len(qm_issues) == 0


# ======================= example_library 校验 =======================

class TestValidateExampleLibrary:
    def test_no_examples_info(self, minimal_valid_pack):
        """example_library 无 good/bad examples → info 提示"""
        minimal_valid_pack["example_library"] = {}
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any(
            "No examples" in i.message and i.severity == ValidationSeverity.INFO
            for i in r.issues
        )

    def test_good_examples_not_list_errors(self, minimal_valid_pack):
        """good_examples 非 list → error"""
        minimal_valid_pack["example_library"] = {"good_examples": "x"}
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any(
            "good_examples must be a list" in i.message
            and i.severity == ValidationSeverity.ERROR
            for i in r.issues
        )

    def test_bad_examples_not_list_errors(self, minimal_valid_pack):
        """bad_examples 非 list → error"""
        minimal_valid_pack["example_library"] = {"bad_examples": 123}
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any(
            "bad_examples must be a list" in i.message
            and i.severity == ValidationSeverity.ERROR
            for i in r.issues
        )

    def test_few_shot_template_not_str_errors(self, minimal_valid_pack):
        """few_shot_template 非 str → error"""
        minimal_valid_pack["example_library"] = {"few_shot_template": 123}
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        assert any(
            "few_shot_template must be a string" in i.message
            and i.severity == ValidationSeverity.ERROR
            for i in r.issues
        )

    def test_valid_example_library(self, minimal_valid_pack):
        """合法 example_library → 无 example_library 路径的 error"""
        minimal_valid_pack["example_library"] = {
            "good_examples": [{"id": "g1"}],
            "bad_examples": [{"id": "b1"}],
            "few_shot_template": "tpl",
        }
        r = PackSchemaValidator().validate_data(minimal_valid_pack)
        el_issues = [i for i in r.issues if i.path.startswith("$.example_library")]
        assert len(el_issues) == 0


# ======================= 便捷函数 =======================

class TestConvenience:
    def test_validate_pack_function(self, tmp_json, minimal_valid_pack):
        f = tmp_json("v.json", minimal_valid_pack)
        r = validate_pack(str(f))
        assert r.is_valid is True

    def test_validate_pack_non_strict(self, tmp_json, minimal_valid_pack):
        minimal_valid_pack["extra"] = 1
        f = tmp_json("v.json", minimal_valid_pack)
        r = validate_pack(str(f), strict=False)
        assert not any(i.severity == ValidationSeverity.WARNING for i in r.issues)

    def test_validate_all_packs_nonexistent_dir(self, tmp_path):
        results = validate_all_packs(str(tmp_path / "nope"))
        assert results == {}

    def test_validate_all_packs_iterates_glob(self, tmp_path, minimal_valid_pack):
        (tmp_path / "a.json").write_text(json.dumps(minimal_valid_pack), encoding="utf-8")
        results = validate_all_packs(str(tmp_path))
        assert len(results) == 1
        assert results[list(results.keys())[0]].is_valid is True

    def test_print_validation_report(self, capsys, tmp_path, minimal_valid_pack):
        f = tmp_path / "p.json"
        f.write_text(json.dumps(minimal_valid_pack), encoding="utf-8")
        results = validate_all_packs(str(tmp_path))
        print_validation_report(results)
        captured = capsys.readouterr()
        assert "Validation Report" in captured.out
        assert "VALID" in captured.out or "p.json" in captured.out
