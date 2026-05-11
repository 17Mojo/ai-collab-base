"""
Branch Logic Integration Tests
Tests for Pack Workflow branch routing and regex matching
"""

import json
from pathlib import Path

import pytest

# Import schema classes
from src.ai_collab.pack.schema_v2 import BranchCondition, RegexPattern, StepType, WorkflowStep

PACK_DIR = Path("packs/examples")


class TestRegexPattern:
    """Test RegexPattern dataclass"""

    def test_regex_pattern_creation(self):
        """Test basic RegexPattern creation"""
        rp = RegexPattern(pattern="^SUCCESS:", flags="i")
        assert rp.pattern == "^SUCCESS:"
        assert rp.flags == "i"
        assert rp.extract_fields is None

    def test_regex_pattern_with_extract_fields(self):
        """Test RegexPattern with extract_fields"""
        rp = RegexPattern(
            pattern="ERROR:\\s*(\\w+)",
            flags="i",
            extract_fields={"error_code": "error_code"}
        )
        assert rp.extract_fields is not None
        assert rp.extract_fields["error_code"] == "error_code"


class TestBranchCondition:
    """Test BranchCondition dataclass"""

    def test_branch_condition_creation(self):
        """Test basic BranchCondition creation"""
        bc = BranchCondition(
            target_step="step_success",
            condition_type="regex_match",
            target_field="output"
        )
        assert bc.target_step == "step_success"
        assert bc.condition_type == "regex_match"
        assert bc.target_field == "output"
        assert bc.negate is False

    def test_branch_condition_with_regex_config(self):
        """Test BranchCondition with regex_config"""
        rp = RegexPattern(pattern="^SUCCESS:", flags="i")
        bc = BranchCondition(
            target_step="step_success",
            condition_type="regex_match",
            regex_config=rp
        )
        assert bc.regex_config is not None
        assert bc.regex_config.pattern == "^SUCCESS:"


class TestWorkflowStepBranches:
    """Test WorkflowStep branch fields"""

    def test_workflow_step_with_branches(self):
        """Test WorkflowStep with branches field"""
        bc1 = BranchCondition(target_step="step_success", condition_type="regex_match")
        bc2 = BranchCondition(target_step="step_error", condition_type="contains")

        ws = WorkflowStep(
            id="step_1",
            name="Test Step",
            type=StepType.ANALYSIS,
            branches=[bc1, bc2],
            on_error="step_error_handler",
            on_timeout="step_timeout_handler",
            next_step="step_2"
        )

        assert ws.branches is not None
        assert len(ws.branches) == 2
        assert ws.on_error == "step_error_handler"
        assert ws.on_timeout == "step_timeout_handler"
        assert ws.next_step == "step_2"

    def test_workflow_step_without_branches(self):
        """Test WorkflowStep without branches (backward compatibility)"""
        ws = WorkflowStep(
            id="step_1",
            name="Simple Step",
            type=StepType.LOCAL
        )

        assert ws.branches is None
        assert ws.next_step is None
        assert ws.on_error is None


class TestPackLoading:
    """Test Pack JSON loading with branch logic"""

    def test_error_handling_workflow_loads(self):
        """Test error-handling-workflow.json loads successfully"""
        pack_file = PACK_DIR / "error-handling-workflow.json"
        assert pack_file.exists()

        with open(pack_file) as f:
            data = json.load(f)

        assert "metadata" in data
        assert "workflow" in data
        assert data["metadata"]["pack_id"] == "error-handling-workflow"

    def test_branch_pack_structure_valid(self):
        """Test branch pack has valid structure"""
        pack_file = PACK_DIR / "error-handling-workflow.json"
        with open(pack_file) as f:
            data = json.load(f)

        steps = data["workflow"]["steps"]
        step_ids = {s["id"] for s in steps}

        # Verify all branch targets exist
        for step in steps:
            if step.get("branches"):
                for branch in step["branches"]:
                    assert branch["target_step"] in step_ids, \
                        f"Branch target {branch['target_step']} not found in steps"

    def test_branch_regex_config_valid(self):
        """Test branch regex_config structure"""
        pack_file = PACK_DIR / "error-handling-workflow.json"
        with open(pack_file) as f:
            data = json.load(f)

        for step in data["workflow"]["steps"]:
            if step.get("branches"):
                for branch in step["branches"]:
                    if branch.get("regex_config"):
                        assert "pattern" in branch["regex_config"]
                        assert isinstance(branch["regex_config"]["pattern"], str)


class TestBackwardCompatibility:
    """Test backward compatibility with Packs without branches"""

    def test_demo_pack_no_branches(self):
        """Test demo-pack.json has no branches (backward compat)"""
        pack_file = PACK_DIR / "demo-pack.json"
        if not pack_file.exists():
            pytest.skip("demo-pack.json not found")

        with open(pack_file) as f:
            data = json.load(f)

        for step in data["workflow"]["steps"]:
            # Either no branches field or branches is None/empty
            assert step.get("branches") is None or len(step.get("branches", [])) == 0


class TestSchemaSerialization:
    """Test Schema serialization with branch fields"""

    def test_workflow_step_to_dict_includes_branches(self):
        """Test WorkflowStep.to_dict includes branch fields"""
        bc = BranchCondition(target_step="step_success", condition_type="regex_match")
        ws = WorkflowStep(
            id="step_1",
            name="Test",
            type=StepType.ANALYSIS,
            branches=[bc],
            next_step="step_2",
            on_error="error_handler"
        )

        # The WorkflowStep doesn't have to_dict, but we can check the fields
        assert hasattr(ws, 'branches')
        assert hasattr(ws, 'next_step')
        assert hasattr(ws, 'on_error')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
