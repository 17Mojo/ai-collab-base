import json
from pathlib import Path

from ai_collab.spawn_agent_guard import run_spawn_agent_guard


def _write_state(workspace: Path, payload: dict) -> None:
    state_file = workspace / "logs" / "collaboration_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def test_spawn_agent_guard_allows_codex_write_delegation(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_state(workspace, _base_state())

    report = run_spawn_agent_guard(
        workspace=workspace,
        actor="codex",
        parent_task_id="TASK-PARENT",
        files=["tests/unit/test_spawn_agent_guard.py"],
        read_only=False,
        config={"stateFile": "./logs/collaboration_state.json"},
    )

    assert report["allowed"] is True
    assert report["mode"] == "write"
    assert (workspace / report["report_file"]).exists()
    assert (workspace / report["history_file"]).exists()


def test_spawn_agent_guard_allows_read_only_without_write_set(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_state(workspace, _base_state())

    report = run_spawn_agent_guard(
        workspace=workspace,
        actor="codex",
        parent_task_id="TASK-PARENT",
        files=[],
        read_only=True,
        config={"stateFile": "./logs/collaboration_state.json"},
    )

    assert report["allowed"] is True
    assert report["mode"] == "read-only"


def test_spawn_agent_guard_allows_internal_read_only_parent_without_warning(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_state(workspace, _base_state())

    report = run_spawn_agent_guard(
        workspace=workspace,
        actor="codex",
        parent_task_id="INTERNAL-CODEX-PARALLEL-20260328",
        files=[],
        read_only=True,
        config={"stateFile": "./logs/collaboration_state.json"},
    )

    assert report["allowed"] is True
    assert report["warnings"] == []
    assert report["parent_task_source"] == "internal-read-only"


def test_spawn_agent_guard_blocks_missing_parent_task(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_state(workspace, _base_state())

    report = run_spawn_agent_guard(
        workspace=workspace,
        actor="codex",
        parent_task_id=None,
        files=[],
        read_only=True,
        config={"stateFile": "./logs/collaboration_state.json"},
    )

    assert report["allowed"] is False
    assert any("parent_task_id is required" in item for item in report["violations"])


def test_spawn_agent_guard_keeps_unknown_internal_parent_warning_for_write_mode(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_state(workspace, _base_state())

    report = run_spawn_agent_guard(
        workspace=workspace,
        actor="codex",
        parent_task_id="INTERNAL-CODEX-PARALLEL-20260328",
        files=["tests/unit/test_spawn_agent_guard.py"],
        read_only=False,
        config={"stateFile": "./logs/collaboration_state.json"},
    )

    assert report["allowed"] is True
    assert any("not found in collaboration state" in item for item in report["warnings"])
    assert report["parent_task_source"] == "state-or-cli"


def test_spawn_agent_guard_blocks_non_codex_actor(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_state(workspace, _base_state())

    report = run_spawn_agent_guard(
        workspace=workspace,
        actor="claude_code",
        parent_task_id="TASK-PARENT",
        files=["tests/unit/test_spawn_agent_guard.py"],
        read_only=False,
        config={"stateFile": "./logs/collaboration_state.json"},
    )

    assert report["allowed"] is False
    assert any("not allowed" in item for item in report["violations"])


def test_spawn_agent_guard_blocks_protected_path(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_state(workspace, _base_state())

    report = run_spawn_agent_guard(
        workspace=workspace,
        actor="codex",
        parent_task_id="TASK-PARENT",
        files=[".vscode/ai-collab.json"],
        read_only=False,
        config={"stateFile": "./logs/collaboration_state.json"},
    )

    assert report["allowed"] is False
    assert any("protected paths" in item for item in report["violations"])
    assert ".vscode/ai-collab.json" in report["protected_hits"]


def test_spawn_agent_guard_blocks_active_task_conflict(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    state = _base_state()
    state["tasks"]["TASK-OTHER"] = {
        "task_id": "TASK-OTHER",
        "ai_type": "claude_code",
        "description": "other",
        "files": ["tests/unit/test_spawn_agent_guard.py"],
        "status": "testing",
    }
    state["active_tasks"] = ["TASK-PARENT", "TASK-OTHER"]
    _write_state(workspace, state)

    report = run_spawn_agent_guard(
        workspace=workspace,
        actor="codex",
        parent_task_id="TASK-PARENT",
        files=["tests/unit/test_spawn_agent_guard.py"],
        read_only=False,
        config={"stateFile": "./logs/collaboration_state.json"},
    )

    assert report["allowed"] is False
    assert report["active_conflicts"]
    assert report["active_conflicts"][0]["task_id"] == "TASK-OTHER"


def test_spawn_agent_guard_uses_safe_defaults_when_block_missing(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_state(workspace, _base_state())

    report = run_spawn_agent_guard(
        workspace=workspace,
        actor="codex",
        parent_task_id="TASK-PARENT",
        files=[".vscode/ai-collab.json"],
        read_only=False,
        config={"stateFile": "./logs/collaboration_state.json"},
    )

    assert report["allowed"] is False
    assert any("protected paths" in item for item in report["violations"])
