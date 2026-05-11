import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agent_dispatch_bridge.py"


def _base_state(workspace: Path) -> dict:
    return {
        "version": "2.0.0",
        "workspace": str(workspace),
        "last_updated": "2026-03-03T14:00:00+08:00",
        "tasks": {},
        "patches": {},
        "active_tasks": [],
        "completed_tasks": [],
        "conflicts": [],
        "file_status": {},
    }


def _write_state(workspace: Path, payload: dict) -> None:
    state_file = workspace / "logs" / "collaboration_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_dispatch(workspace: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        "python3",
        str(SCRIPT),
        "--workspace",
        str(workspace),
        "--report",
        "logs/task_dispatch_report.json",
        "--history",
        "logs/task_dispatch_history.jsonl",
        "--state",
        "logs/agent_dispatch_state.json",
        "--orders",
        "collaboration/monitoring/AGENT_DISPATCH_ORDERS_test.md",
    ]
    cmd.extend(list(extra_args))
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_dispatch_writes_orders_and_state(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-001"] = {
        "task_id": "TASK-DISPATCH-001",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "acceptance_commands": ["python3 -m pytest -q tests/unit/test_cli.py"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-001.md",
    }
    _write_state(workspace, payload)

    result = _run_dispatch(workspace)
    assert result.returncode == 0, result.stderr

    report_file = workspace / "logs" / "task_dispatch_report.json"
    report = json.loads(report_file.read_text(encoding="utf-8"))
    assert report["candidate_count"] == 1
    assert report["dispatched_count"] == 1
    assert report["already_dispatched_count"] == 0

    state_file = workspace / "logs" / "agent_dispatch_state.json"
    dispatch_state = json.loads(state_file.read_text(encoding="utf-8"))
    assert "TASK-DISPATCH-001" in dispatch_state["items"]

    orders_file = workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
    orders = orders_file.read_text(encoding="utf-8")
    assert "TASK-DISPATCH-001" in orders
    assert (
        "python3 -m ai_collab.cli tasks update --task-id TASK-DISPATCH-001 --ai claude_code --status implementing"
        in orders
    )


def test_dispatch_skips_already_dispatched_without_redispatch(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-002"] = {
        "task_id": "TASK-DISPATCH-002",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "acceptance_commands": ["python3 -m ai_collab.cli status -v"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-002.md",
    }
    _write_state(workspace, payload)

    first = _run_dispatch(workspace)
    assert first.returncode == 0, first.stderr
    second = _run_dispatch(workspace)
    assert second.returncode == 0, second.stderr

    report = json.loads(
        (workspace / "logs" / "task_dispatch_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 1
    assert report["dispatched_count"] == 0
    assert report["already_dispatched_count"] == 1


def test_dispatch_dry_run_keeps_candidate_even_if_already_dispatched(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-DRY-001"] = {
        "task_id": "TASK-DISPATCH-DRY-001",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "status": "planning",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "acceptance_commands": ["python3 -m ai_collab.cli status -v"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-DRY-001.md",
    }
    _write_state(workspace, payload)

    dispatch_state_file = workspace / "logs" / "agent_dispatch_state.json"
    dispatch_state_file.parent.mkdir(parents=True, exist_ok=True)
    dispatch_state_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {
                    "TASK-DISPATCH-DRY-001": {
                        "task_id": "TASK-DISPATCH-DRY-001",
                        "assignee": "codearts_agent",
                        "status": "planning",
                        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-DRY-001.md",
                        "updated_at": "2026-03-03T14:00:00+08:00",
                        "dispatched_at": "2026-03-03T14:00:30+08:00",
                        "dispatch_count": 1,
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _run_dispatch(workspace, "--dry-run")
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_dispatch_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 1
    assert report["dispatched_count"] == 1
    assert report["already_dispatched_count"] == 0

    orders = (
        workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
    ).read_text(encoding="utf-8")
    assert "TASK-DISPATCH-DRY-001" in orders


def test_dispatch_include_pending_switch(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-003"] = {
        "task_id": "TASK-DISPATCH-003",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "pending",
        "updated_at": "2026-03-03T14:00:00+08:00",
        "acceptance_commands": ["python3 -m ai_collab.cli status -v"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-003.md",
    }
    _write_state(workspace, payload)

    result_without_pending = _run_dispatch(workspace, "--dry-run")
    assert result_without_pending.returncode == 0, result_without_pending.stderr
    report_without = json.loads(
        (workspace / "logs" / "task_dispatch_report.json").read_text(encoding="utf-8")
    )
    assert report_without["candidate_count"] == 0

    result_with_pending = _run_dispatch(workspace, "--dry-run", "--include-pending")
    assert result_with_pending.returncode == 0, result_with_pending.stderr
    report_with = json.loads(
        (workspace / "logs" / "task_dispatch_report.json").read_text(encoding="utf-8")
    )
    assert report_with["candidate_count"] == 1
    assert report_with["dispatched_count"] == 1


def test_dispatch_redispatch_reopened_implementing_task_with_existing_record(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-004"] = {
        "task_id": "TASK-DISPATCH-004",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "implementing",
        "updated_at": "2026-03-03T14:05:00+08:00",
        "acceptance_commands": ["python3 -m pytest -q tests/unit/test_agent_dispatch_bridge.py"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-004.md",
        "notes": [
            "[2026-03-03T14:04:00+08:00] codex review rejected: previous result invalid",
            "[2026-03-03T14:04:30+08:00] Reopened by codex: rerun original acceptance commands",
        ],
    }
    _write_state(workspace, payload)

    dispatch_state_file = workspace / "logs" / "agent_dispatch_state.json"
    dispatch_state_file.parent.mkdir(parents=True, exist_ok=True)
    dispatch_state_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {
                    "TASK-DISPATCH-004": {
                        "task_id": "TASK-DISPATCH-004",
                        "assignee": "claude_code",
                        "status": "pending",
                        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-004.md",
                        "updated_at": "2026-03-03T14:00:00+08:00",
                        "dispatched_at": "2026-03-03T14:00:30+08:00",
                        "dispatch_count": 1,
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _run_dispatch(workspace, "--dry-run", "--redispatch")
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_dispatch_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 1
    assert report["dispatched_count"] == 1
    assert report["already_dispatched_count"] == 0
    assert report["candidate_tasks"][0]["status"] == "implementing"

    orders = (
        workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_test.md"
    ).read_text(encoding="utf-8")
    assert "TASK-DISPATCH-004" in orders
    assert "返工重派说明（必须先读）" in orders
    assert "禁止因为 result_file 已存在或任务曾到过 testing 就回复 noop。" in orders
    assert "Reopened by codex" in orders


def test_dispatch_redispatch_does_not_include_new_implementing_task_without_record(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DISPATCH-005"] = {
        "task_id": "TASK-DISPATCH-005",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "implementing",
        "updated_at": "2026-03-03T14:05:00+08:00",
        "acceptance_commands": ["python3 -m pytest -q tests/unit/test_agent_dispatch_bridge.py"],
        "result_file": "collaboration/results/RESULT_TASK-DISPATCH-005.md",
    }
    _write_state(workspace, payload)

    result = _run_dispatch(workspace, "--dry-run", "--redispatch")
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_dispatch_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 0
    assert report["dispatched_count"] == 0
