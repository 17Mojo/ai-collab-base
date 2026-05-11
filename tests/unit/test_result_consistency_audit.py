import json
from pathlib import Path

import ai_collab.state_manager as state_manager
from ai_collab.result_consistency_audit import (
    parse_result_header_status,
    run_terminal_result_consistency_audit,
)


def _patch_state_paths(monkeypatch, workspace: Path):
    monkeypatch.setattr(
        state_manager.VSCodeIntegration,
        "get_project_config",
        lambda: {"stateFile": "./logs/collaboration_state.json"},
    )
    monkeypatch.setattr(
        state_manager.VSCodeIntegration,
        "update_vscode_output",
        lambda message, channel="AI Collab": None,
    )
    monkeypatch.setattr(
        state_manager.VSCodeStateManager,
        "get_global_state_file",
        lambda: str(workspace / "global_collaboration_state.json"),
    )


def _write_result_file(path: Path, status_line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Result",
                status_line,
                "## 执行命令",
                "pytest -q tests/unit/test_result_consistency_audit.py",
                "## 测试结论",
                "all green",
                "## 风险与回滚",
                "none",
            ]
        ),
        encoding="utf-8",
    )


def test_parse_result_header_status_supports_cn_en_and_emoji():
    assert parse_result_header_status("**状态**: failed") == "failed"
    assert parse_result_header_status("**状态**: ✅ 完成") == "completed"
    assert parse_result_header_status("**Status**: blocked") == "blocked"
    assert parse_result_header_status("状态: 已取消") == "cancelled"
    assert parse_result_header_status("- **Status**: ✅ Completed") == "completed"
    assert parse_result_header_status("- Status: completed") == "completed"
    assert parse_result_header_status("**状态**: testing") == "testing"
    assert parse_result_header_status("**状态**: ✅ OK（基于 A.ACK 收口）") == "completed"


def test_parse_result_header_status_handles_current_status_variants():
    assert parse_result_header_status("当前状态: completed") == "completed"
    assert parse_result_header_status("当前控制面状态: blocked") == "blocked"
    assert parse_result_header_status("当前执行状态: ✅ OK") == "completed"


def test_parse_result_header_status_ignores_transition_history_lines():
    assert parse_result_header_status("**任务状态**: implementing → testing") == ""


def test_terminal_result_consistency_audit_reports_mismatch_and_takeover_ok(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    completed_result = tmp_path / "collaboration" / "results" / "RESULT_TASK-AUDIT-OK-001.md"
    _write_result_file(completed_result, "**状态**: completed")
    manager.register_task(
        task_id="TASK-AUDIT-OK-001",
        ai_type="claude_code",
        description="consistent completed task",
        files=["ai_collab/cli.py"],
        result_file="collaboration/results/RESULT_TASK-AUDIT-OK-001.md",
        acceptance_commands=["pytest -q tests/unit/test_result_consistency_audit.py"],
        contract_required=False,
    )
    manager.update_task_status(
        task_id="TASK-AUDIT-OK-001",
        status=state_manager.TaskStatus.COMPLETED,
        note="complete",
    )

    mismatch_result = tmp_path / "collaboration" / "results" / "RESULT_TASK-AUDIT-MISMATCH-001.md"
    _write_result_file(mismatch_result, "**状态**: testing")
    manager.register_task(
        task_id="TASK-AUDIT-MISMATCH-001",
        ai_type="codearts_agent",
        description="failed task with completed report",
        files=["ai_collab/cli.py"],
        result_file="collaboration/results/RESULT_TASK-AUDIT-MISMATCH-001.md",
        contract_required=False,
    )
    manager.update_task_status(
        task_id="TASK-AUDIT-MISMATCH-001",
        status=state_manager.TaskStatus.FAILED,
        note="review rejected",
    )

    unparseable_result = tmp_path / "collaboration" / "results" / "RESULT_TASK-AUDIT-UNPARSEABLE-001.md"
    unparseable_result.parent.mkdir(parents=True, exist_ok=True)
    unparseable_result.write_text(
        "# Result\n## 执行命令\npytest -q tests/unit/test_result_consistency_audit.py\n",
        encoding="utf-8",
    )
    manager.register_task(
        task_id="TASK-AUDIT-UNPARSEABLE-001",
        ai_type="codearts_agent",
        description="missing status header",
        files=["ai_collab/cli.py"],
        result_file="collaboration/results/RESULT_TASK-AUDIT-UNPARSEABLE-001.md",
        contract_required=False,
    )
    manager.update_task_status(
        task_id="TASK-AUDIT-UNPARSEABLE-001",
        status=state_manager.TaskStatus.FAILED,
        note="header missing",
    )

    takeover_result = tmp_path / "collaboration" / "results" / "RESULT_TASK-AUDIT-TAKEOVER-001.md"
    _write_result_file(takeover_result, "**状态**: completed")
    manager.register_task(
        task_id="TASK-AUDIT-TAKEOVER-001",
        ai_type="claude_code",
        description="takeover completed task",
        files=["ai_collab/state_manager.py"],
        result_file="collaboration/results/RESULT_TASK-AUDIT-TAKEOVER-001.md",
        acceptance_commands=["pytest -q tests/unit/test_result_consistency_audit.py"],
        contract_required=False,
    )
    manager.takeover_task(
        task_id="TASK-AUDIT-TAKEOVER-001",
        owner="codex",
        actor="codex",
        reason="takeover for direct completion",
    )
    manager.update_task_status(
        task_id="TASK-AUDIT-TAKEOVER-001",
        status=state_manager.TaskStatus.COMPLETED,
        note="takeover completed",
        actor="codex",
    )

    report = run_terminal_result_consistency_audit(workspace=tmp_path)

    assert report["audited_count"] == 4
    assert report["consistent_count"] == 2
    assert report["mismatch_count"] == 1
    assert report["unparseable_count"] == 1
    assert report["missing_result_count"] == 0
    issue_types = {item["issue_type"] for item in report["issues"]}
    assert issue_types == {"terminal_status_mismatch", "unparseable_result_header"}
    mismatch_task = next(item for item in report["issues"] if item["task_id"] == "TASK-AUDIT-MISMATCH-001")
    assert mismatch_task["result_header_status"] == "testing"
    takeover_task = next(item for item in report["tasks"] if item["task_id"] == "TASK-AUDIT-TAKEOVER-001")
    assert takeover_task["state_status"] == "completed"
    assert takeover_task["result_header_status"] == "completed"
    assert takeover_task["has_owner_lock"] is True
    assert report["summary_file"] == "collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md"
    assert report["report_file"] == "logs/task_result_consistency_report.json"
    assert (tmp_path / report["summary_file"]).exists()
    assert json.loads((tmp_path / report["report_file"]).read_text(encoding="utf-8"))["issue_count"] == 2


def test_terminal_result_consistency_summary_orders_issues(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    manager = state_manager.StateManager(workspace_path=str(tmp_path))

    beta_result = tmp_path / "collaboration" / "results" / "RESULT_TASK-ISSUE-BETA.md"
    _write_result_file(beta_result, "**状态**: testing")
    manager.register_task(
        task_id="TASK-ISSUE-BETA",
        ai_type="claude_code",
        description="beta mismatch",
        files=["ai_collab/result_consistency_audit.py"],
        result_file="collaboration/results/RESULT_TASK-ISSUE-BETA.md",
        contract_required=False,
    )
    manager.update_task_status(
        task_id="TASK-ISSUE-BETA",
        status=state_manager.TaskStatus.FAILED,
        note="beta failed",
    )

    alpha_result = tmp_path / "collaboration" / "results" / "RESULT_TASK-ISSUE-ALPHA.md"
    _write_result_file(alpha_result, "**Status**: testing")
    manager.register_task(
        task_id="TASK-ISSUE-ALPHA",
        ai_type="claude_code",
        description="alpha mismatch",
        files=["ai_collab/result_consistency_audit.py"],
        result_file="collaboration/results/RESULT_TASK-ISSUE-ALPHA.md",
        contract_required=False,
    )
    manager.update_task_status(
        task_id="TASK-ISSUE-ALPHA",
        status=state_manager.TaskStatus.COMPLETED,
        note="alpha complete but header mismatch",
    )

    report = run_terminal_result_consistency_audit(workspace=tmp_path)
    issue_ids = [issue["task_id"] for issue in report["issues"]]
    assert issue_ids == sorted(issue_ids)

    summary_text = (tmp_path / report["summary_file"]).read_text(encoding="utf-8")
    idx_alpha = summary_text.index("`TASK-ISSUE-ALPHA`")
    idx_beta = summary_text.index("`TASK-ISSUE-BETA`")
    assert idx_alpha < idx_beta
