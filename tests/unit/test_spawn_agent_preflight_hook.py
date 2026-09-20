import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ai_collab.hooks.spawn_agent_preflight import run_preflight  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_progress(path: Path, scope: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            "# Codex Task Progress\n\n"
            "## Steps\n\n"
            "- [ ] **Step 1: test**\n"
            f"  - **Scope:** {scope}\n"
            "  - **Acceptance:** pass\n"
        ),
        encoding="utf-8",
    )


def _base_state() -> dict:
    return {
        "version": "2.0.0",
        "workspace": "",
        "tasks": {
            "TASK-PARENT": {
                "task_id": "TASK-PARENT",
                "ai_type": "codex",
                "description": "parent",
                "files": ["ai_collab/cli.py"],
                "status": "implementing",
            }
        },
        "patches": {},
        "active_tasks": ["TASK-PARENT"],
        "completed_tasks": [],
        "conflicts": [],
        "file_status": {},
    }


def test_run_preflight_uses_runtime_parent_and_prompt_metadata(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_json(workspace / "logs" / "collaboration_state.json", _base_state())
    _write_json(workspace / ".cc-claude-codex" / "runtime.json", {"task_id": "TASK-PARENT"})

    result = run_preflight(
        {
            "cwd": str(workspace),
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "implement",
                "prompt": "Parent Task: TASK-PARENT\nFiles: tests/unit/test_cli.py\nRead Only: false",
            },
        }
    )

    assert result["allowed"] is True
    assert result["request"]["parent_task_id"] == "TASK-PARENT"
    assert result["request"]["files"] == ["tests/unit/test_cli.py"]
    assert result["request"]["read_only"] is False
    assert result["report"]["metadata"]["files_source"] == "prompt"


def test_run_preflight_falls_back_to_progress_scope(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_json(workspace / "logs" / "collaboration_state.json", _base_state())
    _write_json(workspace / ".cc-claude-codex" / "runtime.json", {"task_id": "TASK-PARENT"})
    _write_progress(
        workspace / ".cc-claude-codex" / "codex-progress.md", "tests/unit/test_spawn_agent_guard.py"
    )

    result = run_preflight(
        {
            "cwd": str(workspace),
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "implement",
                "prompt": "Please update the delegated test coverage.",
            },
        }
    )

    assert result["allowed"] is True
    assert result["request"]["files"] == ["tests/unit/test_spawn_agent_guard.py"]
    assert result["report"]["metadata"]["files_source"] == "progress-scope"


def test_run_preflight_denies_protected_write(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_json(workspace / "logs" / "collaboration_state.json", _base_state())
    _write_json(workspace / ".cc-claude-codex" / "runtime.json", {"task_id": "TASK-PARENT"})

    result = run_preflight(
        {
            "cwd": str(workspace),
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "implement",
                "prompt": "Parent Task: TASK-PARENT\nFiles: .vscode/ai-collab.json\nRead Only: false",
            },
        }
    )

    assert result["allowed"] is False
    assert result["hook_output"]["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert (
        "protected paths" in result["hook_output"]["hookSpecificOutput"]["permissionDecisionReason"]
    )


def test_run_preflight_allows_explicit_read_only_without_files(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_json(workspace / "logs" / "collaboration_state.json", _base_state())
    _write_json(workspace / ".cc-claude-codex" / "runtime.json", {"task_id": "TASK-PARENT"})

    result = run_preflight(
        {
            "cwd": str(workspace),
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "review",
                "prompt": "Parent Task: TASK-PARENT\nRead Only: true\nPlease inspect the flow.",
            },
        }
    )

    assert result["allowed"] is True
    assert result["request"]["files"] == []
    assert result["request"]["read_only"] is True


def test_run_preflight_internal_read_only_parent_sets_internal_source(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_json(workspace / "logs" / "collaboration_state.json", _base_state())

    result = run_preflight(
        {
            "cwd": str(workspace),
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "inspect",
                "prompt": "Parent Task: INTERNAL-CODEX-PARALLEL-20260328\nRead Only: true\nPlease review concurrency.",
            },
        }
    )

    assert result["allowed"] is True
    assert result["request"]["parent_task_id"] == "INTERNAL-CODEX-PARALLEL-20260328"
    assert result["request"]["read_only"] is True
    assert result["request"]["metadata"]["parent_task_source"] == "internal-read-only"
    assert result["report"]["metadata"]["parent_task_source"] == "internal-read-only"


def test_run_preflight_internal_parent_write_mode_warns_missing_from_state(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_json(workspace / "logs" / "collaboration_state.json", _base_state())

    result = run_preflight(
        {
            "cwd": str(workspace),
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "implement",
                "prompt": "Parent Task: INTERNAL-CODEX-PARALLEL-20260328\nRead Only: false\nPlease patch hooks.",
            },
        }
    )

    assert result["allowed"] is False
    assert any("non-empty declared file set" in reason for reason in result["report"]["violations"])



class TestSpawnAgentPreflightHelpers:
    """Internal helper function coverage tests."""

    def test_get_cwd_bytes(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _get_cwd
        result = _get_cwd({"cwd": str(tmp_path).encode("utf-8")})
        assert result == Path(str(tmp_path))

    def test_get_cwd_string(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _get_cwd
        result = _get_cwd({"cwd": str(tmp_path)})
        assert result == Path(str(tmp_path))

    def test_get_cwd_missing_returns_dot(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _get_cwd
        result = _get_cwd({})
        assert result == Path(".")

    def test_load_json_nonexistent(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _load_json
        result = _load_json(tmp_path / "nope.json")
        assert result == {}

    def test_load_json_invalid(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _load_json
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid")
        result = _load_json(bad_file)
        assert result == {}

    def test_load_json_non_dict_returns_empty(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _load_json
        arr_file = tmp_path / "arr.json"
        arr_file.write_text("[1, 2, 3]")
        result = _load_json(arr_file)
        assert result == {}

    def test_normalize_path_url_skipped(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _normalize_path
        result = _normalize_path(tmp_path, "https://example.com")
        assert result == ""

    def test_normalize_path_task_id_skipped(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _normalize_path
        result = _normalize_path(tmp_path, "TASK-12345")
        assert result == ""

    def test_normalize_path_absolute_outside_workspace(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _normalize_path
        result = _normalize_path(tmp_path, "/etc/passwd")
        # Should return as_posix (not raise)
        assert result == "/etc/passwd"

    def test_normalize_path_relative_with_dot(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _normalize_path
        result = _normalize_path(tmp_path, "./foo/bar")
        assert result == "foo/bar"

    def test_dedupe_removes_duplicates(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _dedupe
        result = _dedupe(["a", "b", "a", "c", "", "b"])
        assert result == ["a", "b", "c"]

    def test_dedupe_empty_input(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _dedupe
        assert _dedupe([]) == []

    def test_path_tokens_extracts_paths(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _path_tokens
        text = "Edit files: foo.py bar/baz.py"
        result = _path_tokens(text, tmp_path)
        assert "foo.py" in result
        assert "bar/baz.py" in result

    def test_line_payload_extract_label_value(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _line_payload
        # labels must be lowercase per function implementation
        result = _line_payload("Parent Task: TASK-12345", ("parent task",))
        assert result == "TASK-12345"

    def test_line_payload_no_match(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _line_payload
        result = _line_payload("Random text", ("Parent Task",))
        assert result == ""

    def test_extract_parent_task_from_runtime(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _extract_parent_task
        runtime = {"task_id": "TASK-RUNTIME-1"}
        result_id, source = _extract_parent_task("any text", runtime)
        assert result_id == "TASK-RUNTIME-1"
        assert source == "runtime"

    def test_extract_parent_task_from_prompt_label(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _extract_parent_task
        result_id, source = _extract_parent_task(
            "Parent Task: TASK-PROMPT-1\nDo something.",
            {}
        )
        assert result_id == "TASK-PROMPT-1"
        assert source == "prompt-label"

    def test_extract_parent_task_missing(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _extract_parent_task
        result_id, source = _extract_parent_task("no task info here", {})
        assert result_id is None
        assert source == "missing"


class TestBuildPreflightRequest:
    def test_build_basic_request(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import build_preflight_request
        result = build_preflight_request({
            "cwd": str(tmp_path),
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "implement", "prompt": "fix bug"}
        })
        assert "workspace" in result
        # actor 硬编码为 "codex" (来自 spawn_agent_guard)
        assert result["actor"] == "codex"
        assert "files" in result

    def test_build_request_with_files(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import build_preflight_request
        result = build_preflight_request({
            "cwd": str(tmp_path),
            "tool_name": "Agent",
            "tool_input": {
                "subagent_type": "implement",
                "prompt": "fix foo.py and bar.py"
            }
        })
        assert "foo.py" in result["files"]
        assert "bar.py" in result["files"]



class TestExtractExplicitFiles:
    """_extract_explicit_files 覆盖测试"""

    def test_files_from_tool_input_list(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _extract_explicit_files
        files, source = _extract_explicit_files(
            {"files": ["foo.py", "bar.py"]},
            "no files here",
            tmp_path,
        )
        assert "foo.py" in files
        assert "bar.py" in files
        assert source == "tool_input.files"

    def test_files_from_tool_input_paths(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _extract_explicit_files
        files, source = _extract_explicit_files(
            {"paths": ["test.py"]},
            "",
            tmp_path,
        )
        assert files == ["test.py"]
        assert source == "tool_input.paths"

    def test_files_from_tool_input_scope_string(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _extract_explicit_files
        files, source = _extract_explicit_files(
            {"scope": "foo.py bar.py"},
            "",
            tmp_path,
        )
        assert "foo.py" in files
        assert source == "tool_input.scope"

    def test_files_from_prompt_line(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _extract_explicit_files
        files, source = _extract_explicit_files(
            {},
            "Edit files: foo.py",
            tmp_path,
        )
        assert "foo.py" in files
        assert source == "prompt"

    def test_files_from_action_hint(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _extract_explicit_files
        files, source = _extract_explicit_files(
            {},
            "Edit src/foo.py",
            tmp_path,
        )
        assert "src/foo.py" in files
        assert source == "prompt"

    def test_negative_hint_skipped(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _extract_explicit_files
        files, source = _extract_explicit_files(
            {},
            "DO NOT touch src/foo.py",
            tmp_path,
        )
        assert files == []
        assert source == "missing"

    def test_no_files_found(self, tmp_path: Path) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _extract_explicit_files
        files, source = _extract_explicit_files({}, "no file info here", tmp_path)
        assert files == []
        assert source == "missing"


class TestIsInternalReadOnlyParent:
    """_is_internal_read_only_parent 覆盖测试"""

    def test_read_only_false(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _is_internal_read_only_parent
        assert _is_internal_read_only_parent("TASK-INTERNAL-1", False) is False

    def test_internal_prefix_match(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _is_internal_read_only_parent
        # INTERNAL_PARENT_PREFIXES = ("INTERNAL-CODEX-",)
        assert _is_internal_read_only_parent("INTERNAL-CODEX-PARALLEL-12345", True) is True

    def test_non_internal_task(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _is_internal_read_only_parent
        assert _is_internal_read_only_parent("TASK-NORMAL-1", True) is False

    def test_empty_task_id(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _is_internal_read_only_parent
        assert _is_internal_read_only_parent("", True) is False
        assert _is_internal_read_only_parent(None, True) is False


class TestParseBool:
    """_parse_bool 覆盖测试"""

    def test_parse_bool_true_values(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _parse_bool
        for val in ["true", "True", "TRUE", "1", "yes"]:
            assert _parse_bool(val) is True

    def test_parse_bool_false_values(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _parse_bool
        for val in ["false", "False", "FALSE", "0", "no"]:
            assert _parse_bool(val) is False

    def test_parse_bool_none_for_invalid(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _parse_bool
        assert _parse_bool("maybe") is None
        assert _parse_bool("") is None
        assert _parse_bool(None) is None


class TestDenyOutput:
    """_deny_output 覆盖测试"""

    def test_deny_output_structure(self) -> None:
        from ai_collab.hooks.spawn_agent_preflight import _deny_output
        result = _deny_output("test reason")
        assert result["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert result["hookSpecificOutput"]["permissionDecisionReason"] == "test reason"
