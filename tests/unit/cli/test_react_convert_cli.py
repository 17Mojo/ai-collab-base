"""
ReAct Requirement Conversion CLI Tests

守护 ``ai_collab/cli/react_convert.py``（Owner 需求 → Pack 草稿）。

背景
----
该文件此前是独立 argparse 脚本：逻辑埋在 ``main()`` 里，既无法被主 CLI 复用
（``ai-collab pack convert``），也没有任何测试覆盖（0%）。
现在转换逻辑抽到 ``convert_requirement_file()``，这里对两个方向做守护：

1. 行为正确——产物齐全、退出码正确
2. 与下游契约对齐——``draft_pack.json`` 的 ``metadata.pack_id`` / ``metadata.pack_name``
   正是 ``ai-collab pack import`` 读取的字段，两个子命令能串成闭环
"""

import json
import os

import pytest

from ai_collab.cli.react_convert import convert_requirement_file, main, save_artifacts


@pytest.fixture
def requirement_dict():
    """最小可用 Owner 需求"""
    return {
        "name": "Test Pack",
        "description": "A test pack for CLI testing",
        "type": "productivity",
        "owner": "test_user",
        "target_platform": "generic",
        "inputs": [{"key": "topic", "type": "string", "required": True}],
        "template": "Generate content about {topic}",
        "params": {"style_profile": "professional", "tone": "neutral"},
        "tags": ["test", "example"],
    }


@pytest.fixture
def requirement_file(tmp_path, requirement_dict):
    """把需求写成 JSON 文件"""
    path = tmp_path / "requirement.json"
    path.write_text(json.dumps(requirement_dict, ensure_ascii=False), encoding="utf-8")
    return str(path)


class TestConvertRequirementFile:
    """convert_requirement_file() 的成功与失败路径"""

    def test_missing_requirement_file_returns_1(self, tmp_path):
        """需求文件不存在 → 返回退出码 1，不抛异常"""
        missing = str(tmp_path / "nope.json")
        assert convert_requirement_file(missing, str(tmp_path / "out")) == 1

    def test_invalid_json_returns_1(self, tmp_path):
        """需求文件不是合法 JSON → 返回退出码 1"""
        bad = tmp_path / "bad.json"
        bad.write_text("{ not valid json", encoding="utf-8")

        assert convert_requirement_file(str(bad), str(tmp_path / "out")) == 1

    def test_happy_path_returns_0(self, requirement_file, tmp_path):
        """正常需求 → 返回 0"""
        out = tmp_path / "out"
        assert convert_requirement_file(requirement_file, str(out)) == 0

    def test_creates_all_four_artifacts(self, requirement_file, tmp_path):
        """产出 4 个产物文件"""
        out = tmp_path / "out"
        convert_requirement_file(requirement_file, str(out))

        for name in ("draft_pack.json", "change_manifest.md", "validation_report.md", "react_trace.json"):
            assert (out / name).exists(), f"缺少产物: {name}"

    def test_creates_output_dir(self, requirement_file, tmp_path):
        """输出目录不存在时自动创建"""
        out = tmp_path / "nested" / "deeper" / "out"
        assert not out.exists()

        convert_requirement_file(requirement_file, str(out))
        assert out.exists()

    def test_draft_pack_is_valid_json(self, requirement_file, tmp_path):
        """draft_pack.json 必须是合法 JSON"""
        out = tmp_path / "out"
        convert_requirement_file(requirement_file, str(out))

        data = json.loads((out / "draft_pack.json").read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert "metadata" in data
        assert "workflow" in data
        assert "quality_metrics" in data

    def test_draft_pack_metadata_aligns_with_pack_import(self, requirement_file, tmp_path):
        """与 `pack import` 的契约：metadata.pack_id / metadata.pack_name 必须存在

        `ai_collab/cli/_cli_main.py::_handle_import_command` 读取的正是这两个字段，
        缺失会导致 `pack convert` → `pack import` 闭环断裂。
        """
        out = tmp_path / "out"
        convert_requirement_file(requirement_file, str(out))

        data = json.loads((out / "draft_pack.json").read_text(encoding="utf-8"))
        metadata = data["metadata"]

        assert metadata.get("pack_id"), "缺少 metadata.pack_id，pack import 无法读取"
        assert metadata.get("pack_name"), "缺少 metadata.pack_name，pack import 无法读取"

    def test_validation_report_status_ready_for_owner_review(self, requirement_file, tmp_path):
        """合法需求 → 状态为 READY_FOR_OWNER_REVIEW"""
        out = tmp_path / "out"
        convert_requirement_file(requirement_file, str(out))

        report = (out / "validation_report.md").read_text(encoding="utf-8")
        assert "READY_FOR_OWNER_REVIEW" in report
        assert "Schema Valid**: ✓" in report

    def test_validation_report_lists_errors_section(self, requirement_file, tmp_path):
        """验证报告含 Errors / Warnings 段落"""
        out = tmp_path / "out"
        convert_requirement_file(requirement_file, str(out))

        report = (out / "validation_report.md").read_text(encoding="utf-8")
        assert "## Errors" in report
        assert "## Warnings" in report

    def test_change_manifest_sections(self, requirement_file, tmp_path):
        """变更清单含继承/新增/移除/冲突四个段落"""
        out = tmp_path / "out"
        convert_requirement_file(requirement_file, str(out))

        manifest = (out / "change_manifest.md").read_text(encoding="utf-8")
        for section in ("## Inherited Elements", "## New Elements", "## Removed Elements", "## Conflicts"):
            assert section in manifest, f"缺少段落: {section}"

    def test_react_trace_is_trace_list(self, requirement_file, tmp_path):
        """审计轨迹是 trace 列表，每项含三阶段字段"""
        out = tmp_path / "out"
        convert_requirement_file(requirement_file, str(out))

        traces = json.loads((out / "react_trace.json").read_text(encoding="utf-8"))
        assert isinstance(traces, list)
        assert traces, "审计轨迹不应为空"
        for trace in traces:
            for key in ("stage", "timestamp", "input_data", "output_data", "reasoning", "actions", "observations"):
                assert key in trace, f"trace 缺少字段: {key}"

    def test_verbose_adds_trace_details(self, requirement_file, tmp_path, capsys):
        """verbose 模式额外打印 trace 明细"""
        out = tmp_path / "out"
        convert_requirement_file(requirement_file, str(out), verbose=True)

        captured = capsys.readouterr().out
        assert "ReAct Traces:" in captured
        assert "Stage:" in captured


class TestSaveArtifacts:
    """save_artifacts() 直接调用路径"""

    def test_save_artifacts_writes_files(self, requirement_dict, tmp_path):
        """直接调用 save_artifacts 也能产出全部文件"""
        from ai_collab.pack.react_converter import ReActConverter

        artifacts = ReActConverter().convert(requirement_dict)
        out = tmp_path / "out"

        save_artifacts(artifacts, str(out))

        assert (out / "draft_pack.json").exists()
        assert (out / "change_manifest.md").exists()
        assert (out / "validation_report.md").exists()
        assert (out / "react_trace.json").exists()

    def test_save_artifacts_overwrites_existing(self, requirement_dict, tmp_path):
        """重复写入覆盖旧文件，不追加"""
        from ai_collab.pack.react_converter import ReActConverter

        artifacts = ReActConverter().convert(requirement_dict)
        out = tmp_path / "out"
        out.mkdir()
        (out / "draft_pack.json").write_text("STALE", encoding="utf-8")

        save_artifacts(artifacts, str(out))

        content = (out / "draft_pack.json").read_text(encoding="utf-8")
        assert "STALE" not in content
        assert json.loads(content)


class TestMainEntrypoint:
    """独立脚本入口 main()"""

    def test_main_returns_0(self, requirement_file, tmp_path, monkeypatch):
        """正常调用返回 0"""
        out = tmp_path / "out"
        monkeypatch.setattr(
            "sys.argv",
            ["react_convert", "--requirement", requirement_file, "--output", str(out)],
        )

        assert main() == 0
        assert (out / "draft_pack.json").exists()

    def test_main_missing_file_returns_1(self, tmp_path, monkeypatch):
        """文件缺失返回 1（而非抛 SystemExit）"""
        monkeypatch.setattr(
            "sys.argv",
            ["react_convert", "--requirement", str(tmp_path / "nope.json")],
        )

        assert main() == 1

    def test_main_default_output_dir(self, requirement_file, tmp_path, monkeypatch):
        """不传 --output 时落到默认目录 ./conversion_output"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("sys.argv", ["react_convert", "--requirement", requirement_file])

        assert main() == 0
        assert (tmp_path / "conversion_output" / "draft_pack.json").exists()
        assert os.path.isdir(tmp_path / "conversion_output")


class TestMainCLIRegistration:
    """`ai-collab pack convert` 子命令已注册到主 CLI"""

    def test_pack_convert_subcommand_exists(self):
        """主 CLI 的 pack 子命令列表包含 convert"""
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "ai_collab.cli", "pack", "convert", "--help"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, result.stderr
        assert "--requirement" in result.stdout
        assert "--output" in result.stdout
