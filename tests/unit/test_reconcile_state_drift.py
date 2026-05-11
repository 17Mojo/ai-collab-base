import json
import subprocess
from pathlib import Path


def _run(script: Path, workspace: Path, *args: str):
    cmd = ["python3", str(script), "--workspace", str(workspace), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _write_state(workspace: Path, payload: dict):
    state_file = workspace / "logs" / "collaboration_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_explicit_ack(workspace: Path, *, task_id: str, assignee: str, result_file: str):
    state_file = workspace / "logs" / "agent_ack_bridge_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    prefix = {"claude_code": "C", "codearts_agent": "A", "codex": "X"}[assignee]
    status = "completed" if assignee == "codearts_agent" else "ok"
    state_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {
                    task_id: {
                        "task_id": task_id,
                        "assignee": assignee,
                        "result_file": result_file,
                        "ack_line": f"{prefix}.ACK|task={task_id}|status={status}|result={result_file}",
                        "receipt_completed_at": "2026-03-01T10:00:00+08:00",
                        "bridged_at": "2026-03-01T10:00:00+08:00",
                        "bridge_count": 1,
                        "source": "cli-ack",
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _base_state(workspace: Path) -> dict:
    return {
        "version": "2.0.0",
        "workspace": str(workspace),
        "last_updated": "2026-03-01T11:00:00+08:00",
        "tasks": {},
        "patches": {},
        "active_tasks": [],
        "completed_tasks": [],
        "conflicts": [],
        "file_status": {},
    }


def test_dry_run_detects_drift_and_can_fail(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "reconcile_state_drift.py"

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DRIFT-001"] = {
        "task_id": "TASK-DRIFT-001",
        "ai_type": "claude_code",
        "description": "drift task",
        "files": [],
        "status": "deferred",
        "created_at": "2026-03-01T10:00:00+08:00",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "completed_at": None,
        "notes": [],
        "vscode_context": {},
    }
    payload["active_tasks"] = ["TASK-DRIFT-001"]
    _write_state(workspace, payload)

    result_file = workspace / "collaboration" / "results" / "RESULT_TASK-DRIFT-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text("# done\n", encoding="utf-8")

    result = _run(
        script,
        workspace,
        "--report",
        "logs/reconcile_report.json",
        "--fail-on-drift",
    )
    assert result.returncode == 1

    report = json.loads((workspace / "logs" / "reconcile_report.json").read_text(encoding="utf-8"))
    assert report["mode"] == "dry-run"
    assert report["drift_count"] == 1
    assert report["applied_count"] == 0
    assert report["drifts"][0]["item_id"] == "TASK-DRIFT-001"


def test_apply_reconciles_task_and_patch(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "reconcile_state_drift.py"

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DRIFT-APPLY-001"] = {
        "task_id": "TASK-DRIFT-APPLY-001",
        "ai_type": "codex",
        "description": "task drift",
        "files": [],
        "status": "in_progress",
        "created_at": "2026-03-01T10:00:00+08:00",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "completed_at": None,
        "notes": [],
        "vscode_context": {},
    }
    payload["patches"]["PATCH-DRIFT-APPLY-001"] = {
        "patch_id": "PATCH-DRIFT-APPLY-001",
        "task_id": "TASK-DRIFT-APPLY-001",
        "title": "patch drift",
        "files": [],
        "assignee": "codex",
        "status": "blocked",
        "created_at": "2026-03-01T10:01:00+08:00",
        "updated_at": "2026-03-01T10:01:00+08:00",
        "completed_at": None,
        "result_file": None,
        "notes": [],
    }
    payload["active_tasks"] = ["TASK-DRIFT-APPLY-001"]
    _write_state(workspace, payload)

    result_file = workspace / "collaboration" / "results" / "RESULT_TASK-DRIFT-APPLY-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    # 符合新门禁要求：包含执行命令、测试结论、风险章节
    result_file.write_text(
        """# Result
## 执行命令
```bash
echo "test"
```
## 测试结论
- 验证通过
- 无错误
## 风险
- 无风险
""",
        encoding="utf-8",
    )
    _write_explicit_ack(
        workspace,
        task_id="TASK-DRIFT-APPLY-001",
        assignee="codex",
        result_file="collaboration/results/RESULT_TASK-DRIFT-APPLY-001.md",
    )

    result = _run(
        script,
        workspace,
        "--apply",
        "--report",
        "logs/reconcile_report_apply.json",
    )
    assert result.returncode == 0, result.stderr

    state = json.loads((workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8"))
    assert state["tasks"]["TASK-DRIFT-APPLY-001"]["status"] == "completed"
    assert state["patches"]["PATCH-DRIFT-APPLY-001"]["status"] == "completed"

    report = json.loads((workspace / "logs" / "reconcile_report_apply.json").read_text(encoding="utf-8"))
    assert report["mode"] == "apply"
    assert report["drift_count"] == 2
    assert report["applied_count"] == 2
    assert report["error_count"] == 0


def test_cancelled_items_are_not_reconciled(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "reconcile_state_drift.py"

    payload = _base_state(workspace)
    payload["tasks"]["TASK-CANCELLED-001"] = {
        "task_id": "TASK-CANCELLED-001",
        "ai_type": "claude_code",
        "description": "cancelled task",
        "files": [],
        "status": "cancelled",
        "created_at": "2026-03-01T10:00:00+08:00",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "completed_at": "2026-03-01T10:00:00+08:00",
        "notes": [],
        "vscode_context": {},
    }
    payload["patches"]["PATCH-CANCELLED-001"] = {
        "patch_id": "PATCH-CANCELLED-001",
        "task_id": "TASK-CANCELLED-001",
        "title": "cancelled patch",
        "files": [],
        "assignee": "claude_code",
        "status": "cancelled",
        "created_at": "2026-03-01T10:00:00+08:00",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "completed_at": "2026-03-01T10:00:00+08:00",
        "result_file": None,
        "notes": [],
    }
    payload["completed_tasks"] = ["TASK-CANCELLED-001"]
    _write_state(workspace, payload)

    result_file = workspace / "collaboration" / "results" / "RESULT_TASK-CANCELLED-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text("# done\n", encoding="utf-8")

    result = _run(
        script,
        workspace,
        "--report",
        "logs/reconcile_report_cancelled.json",
        "--fail-on-drift",
    )
    assert result.returncode == 0

    report = json.loads((workspace / "logs" / "reconcile_report_cancelled.json").read_text(encoding="utf-8"))
    assert report["drift_count"] == 0
    assert report["applied_count"] == 0


def test_apply_requires_explicit_ack_for_claude_task(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "reconcile_state_drift.py"

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DRIFT-CLAUDE-001"] = {
        "task_id": "TASK-DRIFT-CLAUDE-001",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "description": "claude drift",
        "files": [],
        "status": "testing",
        "created_at": "2026-03-01T10:00:00+08:00",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "completed_at": None,
        "notes": [],
        "vscode_context": {},
    }
    payload["active_tasks"] = ["TASK-DRIFT-CLAUDE-001"]
    _write_state(workspace, payload)

    result_file = workspace / "collaboration" / "results" / "RESULT_TASK-DRIFT-CLAUDE-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        """# Result
## 执行命令
```bash
echo "test"
```
## 测试结论
- 验证通过
## 风险
- 无风险
""",
        encoding="utf-8",
    )

    result = _run(
        script,
        workspace,
        "--apply",
        "--report",
        "logs/reconcile_report_claude.json",
    )
    assert result.returncode == 1

    state = json.loads((workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8"))
    assert state["tasks"]["TASK-DRIFT-CLAUDE-001"]["status"] == "testing"

    report = json.loads((workspace / "logs" / "reconcile_report_claude.json").read_text(encoding="utf-8"))
    assert report["drift_count"] == 1
    assert report["applied_count"] == 0
    assert report["error_count"] == 1
    assert "explicit ACK required" in report["errors"][0]["error"]


def test_apply_does_not_auto_complete_task_with_negative_signal_result(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    script = Path(__file__).resolve().parents[2] / "scripts" / "reconcile_state_drift.py"

    payload = _base_state(workspace)
    payload["tasks"]["TASK-DRIFT-NEG-001"] = {
        "task_id": "TASK-DRIFT-NEG-001",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "description": "negative signal drift",
        "files": [],
        "status": "implementing",
        "created_at": "2026-03-01T10:00:00+08:00",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "completed_at": None,
        "notes": [],
        "vscode_context": {},
        "acceptance_commands": [
            "rg -n 'Generate Playwright failure summary|Upload Playwright failure summary' .github/workflows/ci.yml .github/workflows/nightly.yml"
        ],
        "result_file": "collaboration/results/RESULT_TASK-DRIFT-NEG-001.md",
    }
    payload["active_tasks"] = ["TASK-DRIFT-NEG-001"]
    _write_state(workspace, payload)

    result_file = workspace / "collaboration" / "results" / "RESULT_TASK-DRIFT-NEG-001.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        "\n".join(
            [
                "# 结果",
                "## 执行命令",
                "rg -n 'Generate Playwright failure summary|Upload Playwright failure summary' .github/workflows/ci.yml .github/workflows/nightly.yml",
                "## 测试结论",
                "- [ ] 在 CI workflow 中添加 `Generate Playwright failure summary` 步骤",
                "当前仍未集成，需要返工。",
                "## 风险",
                "需要继续修改 workflow。",
            ]
        ),
        encoding="utf-8",
    )
    _write_explicit_ack(
        workspace,
        task_id="TASK-DRIFT-NEG-001",
        assignee="codearts_agent",
        result_file="collaboration/results/RESULT_TASK-DRIFT-NEG-001.md",
    )

    result = _run(
        script,
        workspace,
        "--apply",
        "--report",
        "logs/reconcile_report_negative.json",
    )
    assert result.returncode == 1

    state = json.loads((workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8"))
    assert state["tasks"]["TASK-DRIFT-NEG-001"]["status"] == "implementing"

    report = json.loads((workspace / "logs" / "reconcile_report_negative.json").read_text(encoding="utf-8"))
    assert report["drift_count"] == 1
    assert report["applied_count"] == 0
    assert report["error_count"] == 1
    assert "contains_negative_signals" in report["errors"][0]["error"]
