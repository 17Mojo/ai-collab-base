import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ai_collab.ack_protocol import record_ack_bridge


def _run(script: Path, workspace: Path, *args: str):
    cmd = ["python3", str(script), "--workspace", str(workspace), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _write_state(workspace: Path, payload: dict):
    state_file = workspace / "logs" / "collaboration_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_state(workspace: Path) -> dict:
    return {
        "version": "2.0.0",
        "workspace": str(workspace),
        "last_updated": "2026-03-02T11:00:00+08:00",
        "tasks": {},
        "patches": {},
        "active_tasks": [],
        "completed_tasks": [],
        "conflicts": [],
        "file_status": {},
    }


def _record_explicit_ack(workspace: Path, *, task_id: str, assignee: str, result_file: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    record_ack_bridge(
        workspace=workspace,
        task_id=task_id,
        assignee=assignee,
        result_file=result_file,
        completed_at=timestamp,
        source="cli-ack",
        bridged_at=timestamp,
        status="ok",
    )


def test_controller_dry_run_reports_without_mutation(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "task_controller_daemon.py"

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DRIFT-001"] = {
        "task_id": "TASK-DRIFT-001",
        "ai_type": "codex",
        "description": "drift task",
        "files": ["src/a.py"],
        "status": "implementing",
        "created_at": "2026-03-02T10:00:00+08:00",
        "updated_at": "2026-03-02T10:10:00+08:00",
        "completed_at": None,
        "notes": [],
        "vscode_context": {},
    }
    payload["tasks"]["TASK-STALE-001"] = {
        "task_id": "TASK-STALE-001",
        "ai_type": "claude_code",
        "description": "stale task",
        "files": ["src/b.py"],
        "status": "pending",
        "created_at": "2026-03-01T08:00:00+08:00",
        "updated_at": "2026-03-01T08:10:00+08:00",
        "completed_at": None,
        "notes": [],
        "vscode_context": {},
    }
    payload["tasks"]["TASK-REVIEW-001"] = {
        "task_id": "TASK-REVIEW-001",
        "ai_type": "codex",
        "description": "needs follow-up patch",
        "files": ["src/c.py"],
        "status": "completed",
        "conclusion": "action_required",
        "created_at": "2026-03-01T07:00:00+08:00",
        "updated_at": "2026-03-01T07:10:00+08:00",
        "completed_at": "2026-03-01T07:10:00+08:00",
        "notes": [],
        "vscode_context": {},
    }
    payload["active_tasks"] = ["TASK-DRIFT-001", "TASK-STALE-001"]
    payload["completed_tasks"] = ["TASK-REVIEW-001"]
    _write_state(workspace, payload)

    result_file = workspace / "collaboration" / "results" / "RESULT_TASK-DRIFT-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        "\n".join(
            [
                "# 结果",
                "## 执行命令",
                "controller dry-run",
                "## 测试结论",
                "ready",
                "## 风险与回滚",
                "none",
            ]
        ),
        encoding="utf-8",
    )

    result = _run(
        script,
        workspace,
        "--once",
        "--dry-run",
        "--active-timeout-sec",
        "99999999",
        "--pending-timeout-sec",
        "60",
        "--report",
        "logs/controller_dry_run.json",
    )
    assert result.returncode == 0, result.stderr

    state = json.loads((workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8"))
    assert state["tasks"]["TASK-DRIFT-001"]["status"] == "implementing"
    assert state["tasks"]["TASK-STALE-001"]["status"] == "pending"
    assert state["patches"] == {}

    report = json.loads((workspace / "logs" / "controller_dry_run.json").read_text(encoding="utf-8"))
    assert report["mode"] == "dry-run"
    assert report["drift_detected"] == 1
    assert report["drift_applied"] == 0
    assert report["prewarning_detected"] == 0
    assert report["prewarning_applied"] == 0
    assert report["stale_detected"] == 1
    assert report["stale_marked_failed"] == 0
    assert report["patch_candidates"] == 1
    assert report["patches_created"] == 0
    assert report["task_contract_checked"] == 2
    assert report["task_contract_invalid"] == 2
    assert report["result_consistency_audited"] == 1
    assert report["result_consistency_issue_count"] == 1

    history_file = workspace / "logs" / "task_controller_history.jsonl"
    assert history_file.exists()
    history_lines = [line for line in history_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(history_lines) == 1
    history_item = json.loads(history_lines[0])
    assert history_item["mode"] == "dry-run"
    assert history_item["prewarning_detected"] == 0
    assert history_item["stale_detected"] == 1
    assert history_item["result_consistency_audited"] == 1
    assert history_item["result_consistency_issue_count"] == 1


def test_controller_apply_requires_explicit_ack_before_auto_complete(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "task_controller_daemon.py"

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DRIFT-001"] = {
        "task_id": "TASK-DRIFT-001",
        "ai_type": "codex",
        "description": "drift task",
        "files": ["src/a.py"],
        "status": "implementing",
        "created_at": "2026-03-02T10:00:00+08:00",
        "updated_at": "2026-03-02T10:10:00+08:00",
        "completed_at": None,
        "notes": [],
        "vscode_context": {},
    }
    payload["tasks"]["TASK-STALE-001"] = {
        "task_id": "TASK-STALE-001",
        "ai_type": "claude_code",
        "description": "stale task",
        "files": ["src/b.py"],
        "status": "pending",
        "created_at": "2026-03-01T08:00:00+08:00",
        "updated_at": "2026-03-01T08:10:00+08:00",
        "completed_at": None,
        "notes": [],
        "vscode_context": {},
    }
    payload["tasks"]["TASK-REVIEW-001"] = {
        "task_id": "TASK-REVIEW-001",
        "ai_type": "codex",
        "description": "needs follow-up patch",
        "files": ["src/c.py"],
        "status": "completed",
        "review_conclusion": "action_required",
        "created_at": "2026-03-01T07:00:00+08:00",
        "updated_at": "2026-03-01T07:10:00+08:00",
        "completed_at": "2026-03-01T07:10:00+08:00",
        "notes": [],
        "vscode_context": {},
    }
    payload["active_tasks"] = ["TASK-DRIFT-001", "TASK-STALE-001"]
    payload["completed_tasks"] = ["TASK-REVIEW-001"]
    _write_state(workspace, payload)

    result_file = workspace / "collaboration" / "results" / "RESULT_TASK-DRIFT-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        "\n".join(
            [
                "# 结果",
                "## 执行命令",
                "controller apply",
                "## 测试结论",
                "ready",
                "## 风险与回滚",
                "none",
            ]
        ),
        encoding="utf-8",
    )

    result = _run(
        script,
        workspace,
        "--once",
        "--active-timeout-sec",
        "99999999",
        "--pending-timeout-sec",
        "60",
        "--default-assignee",
        "codex",
        "--report",
        "logs/controller_apply.json",
    )
    assert result.returncode == 1, result.stderr

    state = json.loads((workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8"))
    assert state["tasks"]["TASK-DRIFT-001"]["status"] == "implementing"
    assert state["tasks"]["TASK-STALE-001"]["status"] == "blocked"
    assert len(state["patches"]) == 1
    patch = next(iter(state["patches"].values()))
    assert patch["task_id"] == "TASK-REVIEW-001"
    assert patch["status"] == "pending"
    assert patch["assignee"] == "codex"

    report = json.loads((workspace / "logs" / "controller_apply.json").read_text(encoding="utf-8"))
    assert report["mode"] == "apply"
    assert report["drift_detected"] == 1
    assert report["drift_applied"] == 0
    assert report["prewarning_detected"] == 0
    assert report["prewarning_applied"] == 0
    assert report["stale_detected"] == 1
    assert report["stale_marked_blocked"] == 1
    assert report["stale_marked_failed"] == 0
    assert report["patch_candidates"] == 1
    assert report["patches_created"] == 1
    assert report["task_contract_checked"] == 2
    assert report["task_contract_invalid"] == 2
    assert report["result_consistency_audited"] == 1
    assert report["result_consistency_issue_count"] == 1
    assert report["error_count"] == 1
    assert len(report["errors"]) == 1
    assert report["errors"][0]["kind"] == "task"
    assert report["errors"][0]["item_id"] == "TASK-DRIFT-001"
    assert "explicit ACK required before auto-complete" in report["errors"][0]["error"]


def test_controller_apply_reconciles_stale_and_creates_patch_with_explicit_ack(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "task_controller_daemon.py"

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DRIFT-001"] = {
        "task_id": "TASK-DRIFT-001",
        "ai_type": "codex",
        "description": "drift task",
        "files": ["src/a.py"],
        "status": "implementing",
        "created_at": "2026-03-02T10:00:00+08:00",
        "updated_at": "2026-03-02T10:10:00+08:00",
        "completed_at": None,
        "notes": [],
        "vscode_context": {},
    }
    payload["tasks"]["TASK-STALE-001"] = {
        "task_id": "TASK-STALE-001",
        "ai_type": "claude_code",
        "description": "stale task",
        "files": ["src/b.py"],
        "status": "pending",
        "created_at": "2026-03-01T08:00:00+08:00",
        "updated_at": "2026-03-01T08:10:00+08:00",
        "completed_at": None,
        "notes": [],
        "vscode_context": {},
    }
    payload["tasks"]["TASK-REVIEW-001"] = {
        "task_id": "TASK-REVIEW-001",
        "ai_type": "codex",
        "description": "needs follow-up patch",
        "files": ["src/c.py"],
        "status": "completed",
        "review_conclusion": "action_required",
        "created_at": "2026-03-01T07:00:00+08:00",
        "updated_at": "2026-03-01T07:10:00+08:00",
        "completed_at": "2026-03-01T07:10:00+08:00",
        "notes": [],
        "vscode_context": {},
    }
    payload["active_tasks"] = ["TASK-DRIFT-001", "TASK-STALE-001"]
    payload["completed_tasks"] = ["TASK-REVIEW-001"]
    _write_state(workspace, payload)

    result_file = workspace / "collaboration" / "results" / "RESULT_TASK-DRIFT-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        "\n".join(
            [
                "# 结果",
                "## 执行命令",
                "controller apply",
                "## 测试结论",
                "ready",
                "## 风险与回滚",
                "none",
            ]
        ),
        encoding="utf-8",
    )
    _record_explicit_ack(
        workspace,
        task_id="TASK-DRIFT-001",
        assignee="codex",
        result_file="collaboration/results/RESULT_TASK-DRIFT-001.md",
    )

    result = _run(
        script,
        workspace,
        "--once",
        "--active-timeout-sec",
        "99999999",
        "--pending-timeout-sec",
        "60",
        "--default-assignee",
        "codex",
        "--report",
        "logs/controller_apply.json",
    )
    assert result.returncode == 0, result.stderr

    state = json.loads((workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8"))
    assert state["tasks"]["TASK-DRIFT-001"]["status"] == "completed"
    assert state["tasks"]["TASK-STALE-001"]["status"] == "blocked"
    assert len(state["patches"]) == 1
    patch = next(iter(state["patches"].values()))
    assert patch["task_id"] == "TASK-REVIEW-001"
    assert patch["status"] == "pending"
    assert patch["assignee"] == "codex"

    report = json.loads((workspace / "logs" / "controller_apply.json").read_text(encoding="utf-8"))
    assert report["mode"] == "apply"
    assert report["drift_detected"] == 1
    assert report["drift_applied"] == 1
    assert report["prewarning_detected"] == 0
    assert report["prewarning_applied"] == 0
    assert report["stale_detected"] == 1
    assert report["stale_marked_blocked"] == 1
    assert report["stale_marked_failed"] == 0
    assert report["patch_candidates"] == 1
    assert report["patches_created"] == 1
    assert report["task_contract_checked"] == 2
    assert report["task_contract_invalid"] == 2
    assert report["result_consistency_audited"] == 1
    assert report["result_consistency_issue_count"] == 1
    assert report["error_count"] == 0


def test_controller_apply_escalates_stale_blocked_to_failed(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "task_controller_daemon.py"

    payload = _base_state(workspace)
    payload["tasks"]["TASK-BLOCKED-STALE-001"] = {
        "task_id": "TASK-BLOCKED-STALE-001",
        "ai_type": "codearts_agent",
        "description": "blocked too long",
        "files": ["src/d.py"],
        "status": "blocked",
        "created_at": "2026-03-01T08:00:00+08:00",
        "updated_at": "2026-03-01T08:10:00+08:00",
        "completed_at": None,
        "notes": [],
        "vscode_context": {},
    }
    payload["active_tasks"] = ["TASK-BLOCKED-STALE-001"]
    _write_state(workspace, payload)

    result = _run(
        script,
        workspace,
        "--once",
        "--blocked-timeout-sec",
        "60",
        "--report",
        "logs/controller_blocked_escalation.json",
    )
    assert result.returncode == 0, result.stderr

    state = json.loads((workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8"))
    assert state["tasks"]["TASK-BLOCKED-STALE-001"]["status"] == "failed"

    report = json.loads((workspace / "logs" / "controller_blocked_escalation.json").read_text(encoding="utf-8"))
    assert report["prewarning_detected"] == 0
    assert report["prewarning_applied"] == 0
    assert report["stale_detected"] == 1
    assert report["stale_marked_blocked"] == 0
    assert report["stale_marked_failed"] == 1


def test_controller_does_not_duplicate_open_patch(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "task_controller_daemon.py"

    payload = _base_state(workspace)
    payload["tasks"]["TASK-REVIEW-001"] = {
        "task_id": "TASK-REVIEW-001",
        "ai_type": "codex",
        "description": "needs follow-up patch",
        "files": ["src/c.py"],
        "status": "completed",
        "conclusion": "action_required",
        "created_at": "2026-03-01T07:00:00+08:00",
        "updated_at": "2026-03-01T07:10:00+08:00",
        "completed_at": "2026-03-01T07:10:00+08:00",
        "notes": [],
        "vscode_context": {},
    }
    payload["patches"]["PATCH-TASK-REVIEW-001-001"] = {
        "patch_id": "PATCH-TASK-REVIEW-001-001",
        "task_id": "TASK-REVIEW-001",
        "title": "existing patch",
        "files": ["src/c.py"],
        "assignee": "codex",
        "status": "in_progress",
        "created_at": "2026-03-01T08:00:00+08:00",
        "updated_at": "2026-03-01T08:10:00+08:00",
        "completed_at": None,
        "result_file": None,
        "notes": [],
    }
    _write_state(workspace, payload)

    result = _run(
        script,
        workspace,
        "--once",
        "--report",
        "logs/controller_no_dup_patch.json",
    )
    assert result.returncode == 0, result.stderr

    state = json.loads((workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8"))
    assert len(state["patches"]) == 1
    assert "PATCH-TASK-REVIEW-001-001" in state["patches"]

    report = json.loads((workspace / "logs" / "controller_no_dup_patch.json").read_text(encoding="utf-8"))
    assert report["patch_candidates"] == 0
    assert report["patches_created"] == 0


def test_controller_apply_prewarning_before_timeout(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "task_controller_daemon.py"

    now = datetime.now(timezone.utc)
    updated_at = (now - timedelta(seconds=85)).isoformat()
    created_at = (now - timedelta(seconds=120)).isoformat()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-PREWARN-001"] = {
        "task_id": "TASK-PREWARN-001",
        "ai_type": "claude_code",
        "description": "near timeout",
        "files": ["src/prewarn.py"],
        "status": "implementing",
        "created_at": created_at,
        "updated_at": updated_at,
        "completed_at": None,
        "notes": [],
        "vscode_context": {},
    }
    payload["active_tasks"] = ["TASK-PREWARN-001"]
    _write_state(workspace, payload)

    result = _run(
        script,
        workspace,
        "--once",
        "--active-timeout-sec",
        "100",
        "--prewarn-ratio",
        "0.8",
        "--report",
        "logs/controller_prewarn_apply.json",
    )
    assert result.returncode == 0, result.stderr

    state = json.loads((workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8"))
    task = state["tasks"]["TASK-PREWARN-001"]
    assert task["status"] == "implementing"
    assert any("prewarning" in str(item).lower() for item in task.get("notes", []))
    assert isinstance(task.get("controller_alerts"), dict)

    report = json.loads((workspace / "logs" / "controller_prewarn_apply.json").read_text(encoding="utf-8"))
    assert report["prewarning_detected"] == 1
    assert report["prewarning_applied"] == 1
    assert report["stale_detected"] == 0

    # Re-run without heartbeat update: prewarning should not duplicate.
    result_second = _run(
        script,
        workspace,
        "--once",
        "--active-timeout-sec",
        "100",
        "--prewarn-ratio",
        "0.8",
        "--report",
        "logs/controller_prewarn_apply_second.json",
    )
    assert result_second.returncode == 0, result_second.stderr
    second_report = json.loads((workspace / "logs" / "controller_prewarn_apply_second.json").read_text(encoding="utf-8"))
    assert second_report["prewarning_detected"] == 1
    assert second_report["prewarning_applied"] == 0


def test_controller_supports_custom_history_path(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "task_controller_daemon.py"

    payload = _base_state(workspace)
    _write_state(workspace, payload)

    result = _run(
        script,
        workspace,
        "--once",
        "--dry-run",
        "--history",
        "logs/custom_history.jsonl",
        "--report",
        "logs/custom_report.json",
    )
    assert result.returncode == 0, result.stderr

    history_file = workspace / "logs" / "custom_history.jsonl"
    assert history_file.exists()
    lines = [line for line in history_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
