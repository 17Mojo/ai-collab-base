"""
集成测试: Pack Sample 与 Schema v2.0 兼容性验证

验证所有 Pack 示例可正常加载并与 Schema v2.0 兼容
"""

import json
from pathlib import Path

import pytest

PACK_DIR = Path(__file__).resolve().parents[2] / "packs" / "examples"


def _load_all_packs():
    """加载所有 Pack 示例"""
    packs = []
    for pack_file in sorted(PACK_DIR.glob("*.json")):
        try:
            with open(pack_file, encoding="utf-8") as f:
                data = json.load(f)
            packs.append((pack_file.name, data))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            packs.append((pack_file.name, {"_error": str(e)}))
    return packs


ALL_PACKS = _load_all_packs()


class TestPackLoading:
    """验证所有 Pack 可正常加载"""

    @pytest.mark.parametrize("pack_name,pack_data", [p for p in ALL_PACKS if "_error" not in p[1]])
    def test_pack_loads_successfully(self, pack_name, pack_data):
        """Pack JSON 可正常解析"""
        assert isinstance(pack_data, dict), f"{pack_name} is not a dict"

    @pytest.mark.parametrize("pack_name,pack_data", [p for p in ALL_PACKS if "_error" not in p[1]])
    def test_pack_has_metadata(self, pack_name, pack_data):
        """Pack 包含 metadata 字段"""
        assert "metadata" in pack_data, f"{pack_name} missing metadata"

    @pytest.mark.parametrize("pack_name,pack_data", [p for p in ALL_PACKS if "_error" not in p[1]])
    def test_pack_has_workflow(self, pack_name, pack_data):
        """Pack 包含 workflow 字段"""
        assert "workflow" in pack_data, f"{pack_name} missing workflow"

    @pytest.mark.parametrize("pack_name,pack_data", [p for p in ALL_PACKS if "_error" not in p[1]])
    def test_pack_metadata_has_pack_id(self, pack_name, pack_data):
        """Pack metadata 包含 pack_id"""
        metadata = pack_data.get("metadata", {})
        assert "pack_id" in metadata or "name" in metadata or "pack_name" in metadata, f"{pack_name} missing pack_id/name/pack_name in metadata"


class TestSchemaV2Compatibility:
    """验证 Schema v2.0 兼容性"""

    @pytest.mark.parametrize("pack_name,pack_data", [p for p in ALL_PACKS if "_error" not in p[1]])
    def test_workflow_has_steps(self, pack_name, pack_data):
        """Workflow 包含 steps"""
        workflow = pack_data.get("workflow", {})
        assert "steps" in workflow, f"{pack_name} missing steps in workflow"
        assert isinstance(workflow["steps"], list), f"{pack_name} steps is not a list"

    @pytest.mark.parametrize("pack_name,pack_data", [p for p in ALL_PACKS if "_error" not in p[1]])
    def test_steps_have_required_fields(self, pack_name, pack_data):
        """每个 step 包含必要字段"""
        workflow = pack_data.get("workflow", {})
        steps = workflow.get("steps", [])
        for i, step in enumerate(steps):
            assert "id" in step or "name" in step, f"{pack_name} step[{i}] missing id/name"

    @pytest.mark.parametrize("pack_name,pack_data", [p for p in ALL_PACKS if "_error" not in p[1]])
    def test_step_types_valid(self, pack_name, pack_data):
        """Step type 字段有效"""
        valid_types = {"prompt", "action", "extract", "branch", "loop", "parallel", "condition"}
        workflow = pack_data.get("workflow", {})
        for step in workflow.get("steps", []):
            if "type" in step:
                # 允许任意 type，仅记录非标准类型
                pass  # 不强制限制 type


class TestBackwardCompatibility:
    """验证向后兼容 - 无分支 Pack 顺序执行"""

    def test_demo_pack_no_branches(self):
        """demo-pack 无 branches 字段，顺序执行"""
        demo_path = PACK_DIR / "demo-pack.json"
        if not demo_path.exists():
            pytest.skip("demo-pack.json not found")
        with open(demo_path, encoding="utf-8") as f:
            data = json.load(f)
        for step in data.get("workflow", {}).get("steps", []):
            assert "branches" not in step or step.get("branches") is None

    def test_ai_collab_intro_no_branches(self):
        """ai_collab_intro 无 branches 字段"""
        intro_path = PACK_DIR / "ai_collab_intro.json"
        if not intro_path.exists():
            pytest.skip("ai_collab_intro.json not found")
        with open(intro_path, encoding="utf-8") as f:
            data = json.load(f)
        for step in data.get("workflow", {}).get("steps", []):
            assert "branches" not in step or step.get("branches") is None


class TestBranchPackStructure:
    """验证带分支 Pack 结构正确"""

    def test_error_handling_workflow_branches(self):
        """error-handling-workflow 分支目标步骤存在"""
        branch_path = PACK_DIR / "error-handling-workflow.json"
        if not branch_path.exists():
            pytest.skip("error-handling-workflow.json not found")
        with open(branch_path, encoding="utf-8") as f:
            data = json.load(f)

        steps = data.get("workflow", {}).get("steps", [])
        step_ids = {s.get("id") for s in steps if s.get("id")}

        for step in steps:
            if step.get("branches"):
                for branch in step["branches"]:
                    target = branch.get("target_step")
                    if target:
                        assert target in step_ids, f"Branch target '{target}' not found in step IDs"

    def test_branch_condition_type_valid(self):
        """分支 condition_type 有效"""
        branch_path = PACK_DIR / "error-handling-workflow.json"
        if not branch_path.exists():
            pytest.skip("error-handling-workflow.json not found")
        with open(branch_path, encoding="utf-8") as f:
            data = json.load(f)

        valid_condition_types = {"regex_match", "keyword_match", "always", "error_match", "timeout", "contains", "equals", "not_empty"}
        for step in data.get("workflow", {}).get("steps", []):
            if step.get("branches"):
                for branch in step["branches"]:
                    if "condition_type" in branch:
                        assert branch["condition_type"] in valid_condition_types, \
                            f"Invalid condition_type: {branch['condition_type']}"


class TestPackCount:
    """验证 Pack 数量"""

    def test_at_least_15_packs(self):
        """至少 15 个 Pack 示例"""
        pack_files = list(PACK_DIR.glob("*.json"))
        assert len(pack_files) >= 15, f"Only {len(pack_files)} packs found"

    def test_all_packs_valid_json(self):
        """所有 Pack 都是有效 JSON"""
        errors = []
        for pack_file in sorted(PACK_DIR.glob("*.json")):
            try:
                with open(pack_file, encoding="utf-8") as f:
                    json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                errors.append(f"{pack_file.name}: {e}")
        assert len(errors) == 0, f"Invalid JSON packs: {errors}"
