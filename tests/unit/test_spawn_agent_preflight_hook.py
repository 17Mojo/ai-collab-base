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
