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


# ── 台账 N42：产物要求按状态分流 + 已 ACK 无产物的非终态扫描 ──────────────────


def _seed(workspace: Path, tasks: dict, acked: dict | None = None) -> None:
    """直接落状态与 ACK 桥，绕开契约校验链，专注审计判据本身。"""
    (workspace / "logs").mkdir(parents=True, exist_ok=True)
    (workspace / "collaboration" / "results").mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.0.0",
        "workspace": str(workspace),
        "tasks": tasks,
        "patches": {},
        "active_tasks": [],
        "completed_tasks": [],
        "conflicts": [],
        "file_status": {},
    }
    (workspace / "logs" / "collaboration_state.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    items = {}
    for task_id, status in (acked or {}).items():
        items[task_id] = {
            "task_id": task_id,
            "assignee": "claude_code",
            "ack_line": f"X.ACK|task={task_id}|status={status}|result=collaboration/results/x.md",
            "source": "cli-ack",
        }
    (workspace / "logs" / "agent_ack_bridge_state.json").write_text(
        json.dumps({"version": "1.0.0", "items": items}, ensure_ascii=False), encoding="utf-8"
    )


def _task(task_id: str, status: str, *, result_file: str = "", notes=None, reason: str = "") -> dict:
    return {
        "task_id": task_id,
        "status": status,
        "result_file": result_file,
        "notes": list(notes or []),
        "reason": reason,
        "ai_type": "claude_code",
        "assignee": "claude_code",
    }


def test_cancelled_task_without_artifact_is_not_an_issue(tmp_path: Path, monkeypatch):
    """取消的语义就是「不交付」——不该被要求交产物。

    修复前它会被记 missing_result_file，于是任何一次取消都让审计永久挂一条噪音。
    """
    _patch_state_paths(monkeypatch, tmp_path)
    _seed(tmp_path, {"T-CANCELLED": _task("T-CANCELLED", "cancelled")})
    report = run_terminal_result_consistency_audit(workspace=tmp_path)
    assert report["issue_count"] == 0
    assert report["missing_result_count"] == 0
    assert report["artifact_optional_count"] == 1
    assert report["audited_count"] == 1


def test_failed_task_without_artifact_requires_a_recorded_reason(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    _seed(tmp_path, {"T-FAILED": _task("T-FAILED", "failed")})
    report = run_terminal_result_consistency_audit(workspace=tmp_path)
    assert report["missing_failure_reason_count"] == 1
    assert [i["issue_type"] for i in report["issues"]] == ["missing_failure_reason"]


def test_failed_task_with_note_or_reason_is_not_an_issue(tmp_path: Path, monkeypatch):
    _patch_state_paths(monkeypatch, tmp_path)
    _seed(
        tmp_path,
        {
            "T-FAILED-NOTE": _task("T-FAILED-NOTE", "failed", notes=["接口不可达"]),
            "T-BLOCKED-REASON": _task("T-BLOCKED-REASON", "blocked", reason="等上游确认"),
        },
    )
    report = run_terminal_result_consistency_audit(workspace=tmp_path)
    assert report["issue_count"] == 0
    assert report["missing_failure_reason_count"] == 0
    assert report["artifact_optional_count"] == 2


def test_completed_task_without_artifact_is_still_required(tmp_path: Path, monkeypatch):
    """completed 声称「做完并交付」，产物要求不能被分流规则削掉。"""
    _patch_state_paths(monkeypatch, tmp_path)
    _seed(tmp_path, {"T-DONE": _task("T-DONE", "completed")})
    report = run_terminal_result_consistency_audit(workspace=tmp_path)
    assert report["missing_result_count"] == 1
    assert [i["issue_type"] for i in report["issues"]] == ["missing_result_file"]
    assert report["artifact_optional_count"] == 0


def test_ack_without_artifact_is_reported_for_non_terminal_task(tmp_path: Path, monkeypatch):
    """N42 另一半：已 ok ACK、产物不存在、任务停在 testing。

    修复前它同时躲开两张网——看门狗把它当「已 ACK」排除，终态审计因非终态不扫。
    """
    _patch_state_paths(monkeypatch, tmp_path)
    _seed(
        tmp_path,
        {"T-ACK-NOART": _task("T-ACK-NOART", "testing", result_file="collaboration/results/RESULT-GONE.md")},
        acked={"T-ACK-NOART": "ok"},
    )
    report = run_terminal_result_consistency_audit(workspace=tmp_path)
    assert report["ack_without_artifact_count"] == 1
    assert [i["issue_type"] for i in report["issues"]] == ["ack_without_artifact"]
    assert report["missing_result_count"] == 0  # 不走终态计数，口径分开


def test_ack_with_artifact_present_is_a_normal_transition(tmp_path: Path, monkeypatch):
    """已 ACK 且产物在、只是还没被 receipt 收口 —— 正常过渡态，不报问题。"""
    _patch_state_paths(monkeypatch, tmp_path)
    _seed(
        tmp_path,
        {"T-ACK-ART": _task("T-ACK-ART", "testing", result_file="collaboration/results/RESULT-OK.md")},
        acked={"T-ACK-ART": "ok"},
    )
    (tmp_path / "collaboration" / "results" / "RESULT-OK.md").write_text(
        "- **状态**: testing\n## 执行命令\nx\n", encoding="utf-8"
    )
    report = run_terminal_result_consistency_audit(workspace=tmp_path)
    assert report["issue_count"] == 0
    assert report["consistent_count"] == 1


def test_non_terminal_task_without_ack_is_not_audited(tmp_path: Path, monkeypatch):
    """非终态 + 没有 ACK = 正常在办任务，审计不介入。

    这条守的是「别把在办任务误报成问题」——否则新扫描会变成噪音源。
    """
    _patch_state_paths(monkeypatch, tmp_path)
    _seed(
        tmp_path,
        {"T-INPROG": _task("T-INPROG", "implementing", result_file="collaboration/results/RESULT-GONE2.md")},
    )
    report = run_terminal_result_consistency_audit(workspace=tmp_path)
    assert report["audited_count"] == 0
    assert report["ack_without_artifact_count"] == 0
    assert report["issue_count"] == 0


def test_non_ok_ack_does_not_trigger_artifact_scan(tmp_path: Path, monkeypatch):
    """ACK status=blocked/noop 不是「已交付」声明，不该触发产物扫描。"""
    _patch_state_paths(monkeypatch, tmp_path)
    _seed(
        tmp_path,
        {"T-ACK-BLOCKED": _task("T-ACK-BLOCKED", "testing", result_file="collaboration/results/RESULT-GONE3.md")},
        acked={"T-ACK-BLOCKED": "blocked"},
    )
    report = run_terminal_result_consistency_audit(workspace=tmp_path)
    assert report["audited_count"] == 0
    assert report["ack_without_artifact_count"] == 0
