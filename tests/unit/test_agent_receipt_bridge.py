import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agent_receipt_bridge.py"


def _base_state(workspace: Path) -> dict:
    return {
        "version": "2.0.0",
        "workspace": str(workspace),
        "last_updated": "2026-03-01T10:00:00+08:00",
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


def _write_result(workspace: Path, relative_path: str, *, valid: bool) -> None:
    result_file = workspace / relative_path
    result_file.parent.mkdir(parents=True, exist_ok=True)
    if valid:
        content = "\n".join(
            [
                "# Result",
                "## 执行命令",
                "```bash",
                "echo test",
                "```",
                "## 测试结论",
                "- pass",
                "## 风险",
                "- none",
            ]
        )
    else:
        content = "# Result\n仅有标题\n"
    result_file.write_text(content, encoding="utf-8")


def _write_explicit_ack_state(
    workspace: Path,
    *,
    task_id: str,
    assignee: str,
    result_file: str,
) -> None:
    ack_file = workspace / "logs" / "agent_ack_bridge_state.json"
    ack_file.parent.mkdir(parents=True, exist_ok=True)
    prefix = {"claude_code": "C", "codearts_agent": "A", "codex": "X"}[assignee]
    status = "completed" if assignee == "codearts_agent" else "ok"
    ack_file.write_text(
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


def _run_receipt(workspace: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        "python3",
        str(SCRIPT),
        "--workspace",
        str(workspace),
        "--report",
        "logs/task_receipt_report.json",
        "--history",
        "logs/task_receipt_history.jsonl",
        "--state",
        "logs/agent_receipt_state.json",
        "--summary",
        "collaboration/monitoring/AGENT_RECEIPT_SUMMARY_test.md",
    ]
    cmd.extend(list(extra_args))
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_receipt_completes_testing_task(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-RECEIPT-001"] = {
        "task_id": "TASK-RECEIPT-001",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "status": "testing",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "notes": [],
        "result_file": "collaboration/results/RESULT_TASK-RECEIPT-001.md",
    }
    payload["active_tasks"] = ["TASK-RECEIPT-001"]
    _write_state(workspace, payload)
    _write_result(workspace, "collaboration/results/RESULT_TASK-RECEIPT-001.md", valid=True)
    _write_explicit_ack_state(
        workspace,
        task_id="TASK-RECEIPT-001",
        assignee="codearts_agent",
        result_file="collaboration/results/RESULT_TASK-RECEIPT-001.md",
    )

    result = _run_receipt(workspace)
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_receipt_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 1
    assert report["completed_count"] == 1
    assert report["error_count"] == 0

    state = json.loads(
        (workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8")
    )
    assert state["tasks"]["TASK-RECEIPT-001"]["status"] == "completed"

    receipt_state = json.loads(
        (workspace / "logs" / "agent_receipt_state.json").read_text(encoding="utf-8")
    )
    assert "TASK-RECEIPT-001" in receipt_state["items"]

    ack_bridge_state = json.loads(
        (workspace / "logs" / "agent_ack_bridge_state.json").read_text(encoding="utf-8")
    )
    assert ack_bridge_state["items"]["TASK-RECEIPT-001"]["ack_line"] == (
        "A.ACK|task=TASK-RECEIPT-001|status=completed|result=collaboration/results/RESULT_TASK-RECEIPT-001.md"
    )


def test_receipt_skips_claude_without_explicit_ack(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-RECEIPT-CLAUDE-001"] = {
        "task_id": "TASK-RECEIPT-CLAUDE-001",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "testing",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "notes": [],
        "result_file": "collaboration/results/RESULT_TASK-RECEIPT-CLAUDE-001.md",
    }
    payload["active_tasks"] = ["TASK-RECEIPT-CLAUDE-001"]
    _write_state(workspace, payload)
    _write_result(workspace, "collaboration/results/RESULT_TASK-RECEIPT-CLAUDE-001.md", valid=True)

    result = _run_receipt(workspace)
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_receipt_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 0
    assert report["completed_count"] == 0
    assert report["skipped_count"] == 1
    assert report["skipped_tasks"][0]["reason"] == "explicit ACK required before receipt close"

    state = json.loads(
        (workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8")
    )
    assert state["tasks"]["TASK-RECEIPT-CLAUDE-001"]["status"] == "testing"
    assert not (workspace / "logs" / "agent_ack_bridge_state.json").exists()


def test_receipt_allows_claude_after_explicit_cli_ack(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-RECEIPT-CLAUDE-002"] = {
        "task_id": "TASK-RECEIPT-CLAUDE-002",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "testing",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "notes": [],
        "result_file": "collaboration/results/RESULT_TASK-RECEIPT-CLAUDE-002.md",
    }
    payload["active_tasks"] = ["TASK-RECEIPT-CLAUDE-002"]
    _write_state(workspace, payload)
    _write_result(workspace, "collaboration/results/RESULT_TASK-RECEIPT-CLAUDE-002.md", valid=True)
    _write_state_file = workspace / "logs" / "agent_ack_bridge_state.json"
    _write_state_file.parent.mkdir(parents=True, exist_ok=True)
    _write_state_file.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {
                    "TASK-RECEIPT-CLAUDE-002": {
                        "task_id": "TASK-RECEIPT-CLAUDE-002",
                        "assignee": "claude_code",
                        "result_file": "collaboration/results/RESULT_TASK-RECEIPT-CLAUDE-002.md",
                        "ack_line": "C.ACK|task=TASK-RECEIPT-CLAUDE-002|status=ok|result=collaboration/results/RESULT_TASK-RECEIPT-CLAUDE-002.md",
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

    result = _run_receipt(workspace)
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_receipt_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 1
    assert report["completed_count"] == 1

    ack_bridge_state = json.loads(
        (workspace / "logs" / "agent_ack_bridge_state.json").read_text(encoding="utf-8")
    )
    assert ack_bridge_state["items"]["TASK-RECEIPT-CLAUDE-002"]["source"] == "cli-ack"


def test_receipt_dry_run_does_not_update_status_or_state(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-RECEIPT-002"] = {
        "task_id": "TASK-RECEIPT-002",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "status": "testing",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "notes": [],
        "result_file": "collaboration/results/RESULT_TASK-RECEIPT-002.md",
    }
    payload["active_tasks"] = ["TASK-RECEIPT-002"]
    _write_state(workspace, payload)
    _write_result(workspace, "collaboration/results/RESULT_TASK-RECEIPT-002.md", valid=True)
    _write_explicit_ack_state(
        workspace,
        task_id="TASK-RECEIPT-002",
        assignee="codearts_agent",
        result_file="collaboration/results/RESULT_TASK-RECEIPT-002.md",
    )

    result = _run_receipt(workspace, "--dry-run")
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_receipt_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 1
    assert report["completed_count"] == 1
    assert report["state_updated"] is False

    state = json.loads(
        (workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8")
    )
    assert state["tasks"]["TASK-RECEIPT-002"]["status"] == "testing"
    assert not (workspace / "logs" / "agent_receipt_state.json").exists()


def test_receipt_skips_task_with_open_patch(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-RECEIPT-003"] = {
        "task_id": "TASK-RECEIPT-003",
        "ai_type": "claude_code",
        "assignee": "claude_code",
        "status": "testing",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "notes": [],
        "result_file": "collaboration/results/RESULT_TASK-RECEIPT-003.md",
    }
    payload["patches"]["PATCH-TASK-RECEIPT-003-001"] = {
        "patch_id": "PATCH-TASK-RECEIPT-003-001",
        "task_id": "TASK-RECEIPT-003",
        "status": "pending",
    }
    payload["active_tasks"] = ["TASK-RECEIPT-003"]
    _write_state(workspace, payload)
    _write_result(workspace, "collaboration/results/RESULT_TASK-RECEIPT-003.md", valid=True)

    result = _run_receipt(workspace)
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_receipt_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 0
    assert report["completed_count"] == 0
    assert report["skipped_count"] == 1

    state = json.loads(
        (workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8")
    )
    assert state["tasks"]["TASK-RECEIPT-003"]["status"] == "testing"


def test_receipt_reports_gate_error_for_invalid_result_file(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-RECEIPT-004"] = {
        "task_id": "TASK-RECEIPT-004",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "status": "testing",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "notes": [],
        "result_file": "collaboration/results/RESULT_TASK-RECEIPT-004.md",
    }
    payload["active_tasks"] = ["TASK-RECEIPT-004"]
    _write_state(workspace, payload)
    _write_result(workspace, "collaboration/results/RESULT_TASK-RECEIPT-004.md", valid=False)
    _write_explicit_ack_state(
        workspace,
        task_id="TASK-RECEIPT-004",
        assignee="codearts_agent",
        result_file="collaboration/results/RESULT_TASK-RECEIPT-004.md",
    )

    result = _run_receipt(workspace)
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_receipt_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 1
    assert report["completed_count"] == 0
    assert report["error_count"] == 1
    assert "missing sections" in report["errors"][0]["error"]

    state = json.loads(
        (workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8")
    )
    assert state["tasks"]["TASK-RECEIPT-004"]["status"] == "testing"


def test_receipt_reports_gate_error_for_mismatched_acceptance_command(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-RECEIPT-005"] = {
        "task_id": "TASK-RECEIPT-005",
        "ai_type": "codearts_agent",
        "assignee": "codearts_agent",
        "status": "testing",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "notes": [],
        "result_file": "collaboration/results/RESULT_TASK-RECEIPT-005.md",
        "acceptance_commands": ["pytest -q tests/unit/test_agent_receipt_bridge.py"],
    }
    payload["active_tasks"] = ["TASK-RECEIPT-005"]
    _write_state(workspace, payload)
    _write_explicit_ack_state(
        workspace,
        task_id="TASK-RECEIPT-005",
        assignee="codearts_agent",
        result_file="collaboration/results/RESULT_TASK-RECEIPT-005.md",
    )

    result_file = workspace / "collaboration" / "results" / "RESULT_TASK-RECEIPT-005.md"
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        "\n".join(
            [
                "# Result",
                "## 执行命令",
                "```bash",
                "pytest -q tests/unit/test_cli.py",
                "```",
                "## 测试结论",
                "- pass",
                "## 风险",
                "- none",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_receipt(workspace)
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "task_receipt_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == 1
    assert report["completed_count"] == 0
    assert report["error_count"] == 1
    assert "missing acceptance_commands" in report["errors"][0]["error"]

    state = json.loads(
        (workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8")
    )
    assert state["tasks"]["TASK-RECEIPT-005"]["status"] == "testing"


def test_receipt_can_close_takeover_locked_task(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    payload = _base_state(workspace)
    payload["tasks"]["TASK-RECEIPT-006"] = {
        "task_id": "TASK-RECEIPT-006",
        "ai_type": "codearts_agent",
        "assignee": "codex",
        "status": "testing",
        "updated_at": "2026-03-01T10:00:00+08:00",
        "notes": [],
        "result_file": "collaboration/results/RESULT_TASK-RECEIPT-006.md",
        "ownership": {
            "owner": "codex",
            "previous_owner": "codearts_agent",
            "lock_active": True,
            "locked_by": "codex",
            "locked_at": "2026-03-01T09:59:00+08:00",
        },
    }
    payload["active_tasks"] = ["TASK-RECEIPT-006"]
    _write_state(workspace, payload)
    _write_result(workspace, "collaboration/results/RESULT_TASK-RECEIPT-006.md", valid=True)
    _write_explicit_ack_state(
        workspace,
        task_id="TASK-RECEIPT-006",
        assignee="codex",
        result_file="collaboration/results/RESULT_TASK-RECEIPT-006.md",
    )

    result = _run_receipt(workspace)
    assert result.returncode == 0, result.stderr

    state = json.loads(
        (workspace / "logs" / "collaboration_state.json").read_text(encoding="utf-8")
    )
    assert state["tasks"]["TASK-RECEIPT-006"]["status"] == "completed"


def test_receipt_error_classifies_not_found_correctly():
    """Test error classification for result_file_not_found"""
    from scripts.agent_receipt_bridge import ReceiptErrorCategory, classify_receipt_error

    exc = ValueError("任务结果门禁失败: TASK-001; result_file not found: path/to/file")
    category = classify_receipt_error(exc)
    assert category == ReceiptErrorCategory.RESULT_FILE_NOT_FOUND


def test_receipt_error_classifies_empty_correctly():
    """Test error classification for result_file_empty"""
    from scripts.agent_receipt_bridge import ReceiptErrorCategory, classify_receipt_error

    exc = ValueError("任务结果门禁失败: TASK-001; result_file is empty")
    category = classify_receipt_error(exc)
    assert category == ReceiptErrorCategory.RESULT_FILE_EMPTY


def test_receipt_error_classifies_invalid_correctly():
    """Test error classification for result_file_invalid"""
    from scripts.agent_receipt_bridge import ReceiptErrorCategory, classify_receipt_error

    exc = ValueError("任务结果门禁失败: TASK-001; result_file missing sections=[a,b]")
    category = classify_receipt_error(exc)
    assert category == ReceiptErrorCategory.RESULT_FILE_INVALID


def test_receipt_error_classifies_unknown_correctly():
    """Test error classification for unknown errors"""
    from scripts.agent_receipt_bridge import ReceiptErrorCategory, classify_receipt_error

    exc = ValueError("some unexpected error")
    category = classify_receipt_error(exc)
    assert category == ReceiptErrorCategory.UNKNOWN


def test_receipt_retry_logic_respects_max_attempts():
    """Test that retry logic respects max_attempts"""
    from scripts.agent_receipt_bridge import (
        ReceiptErrorCategory,
        ReceiptRetryConfig,
        should_retry_receipt_error,
    )

    config = ReceiptRetryConfig(max_attempts=3)

    # First two attempts should retry (attempt 0 and 1)
    assert should_retry_receipt_error(ReceiptErrorCategory.RESULT_FILE_NOT_FOUND, 0, config)
    assert should_retry_receipt_error(ReceiptErrorCategory.RESULT_FILE_NOT_FOUND, 1, config)

    # Third attempt (attempt 2) is still allowed because total attempts = 3
    # After attempt 2, we've made 3 attempts total
    assert should_retry_receipt_error(ReceiptErrorCategory.RESULT_FILE_NOT_FOUND, 2, config)

    # Fourth attempt (attempt 3) should not retry
    assert not should_retry_receipt_error(ReceiptErrorCategory.RESULT_FILE_NOT_FOUND, 3, config)


def test_receipt_retry_logic_skip_non_retryable_categories():
    """Test that non-retryable categories are not retried"""
    from scripts.agent_receipt_bridge import (
        ReceiptErrorCategory,
        ReceiptRetryConfig,
        should_retry_receipt_error,
    )

    config = ReceiptRetryConfig()

    # RESULT_FILE_EMPTY is not in retryable_categories
    assert not should_retry_receipt_error(ReceiptErrorCategory.RESULT_FILE_EMPTY, 0, config)
    assert not should_retry_receipt_error(ReceiptErrorCategory.RESULT_FILE_EMPTY, 1, config)

    # UNKNOWN is not in retryable_categories
    assert not should_retry_receipt_error(ReceiptErrorCategory.UNKNOWN, 0, config)


def test_receipt_error_suggestions_provided():
    """Test that error suggestions are provided"""
    from scripts.agent_receipt_bridge import ReceiptErrorCategory, get_error_suggestion

    assert "确认 result_file 路径" in get_error_suggestion(ReceiptErrorCategory.RESULT_FILE_NOT_FOUND)
    assert "结果文件内容为空" in get_error_suggestion(ReceiptErrorCategory.RESULT_FILE_EMPTY)
    assert "检查结果文件格式" in get_error_suggestion(ReceiptErrorCategory.RESULT_FILE_INVALID)
    assert "任务 ID 不存在" in get_error_suggestion(ReceiptErrorCategory.TASK_NOT_FOUND)
    assert "检查结果文件是否符合验收要求" in get_error_suggestion(ReceiptErrorCategory.VALIDATION_FAILED)
