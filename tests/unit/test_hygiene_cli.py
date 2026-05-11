from types import SimpleNamespace
from unittest.mock import call, patch

from ai_collab import cli


def _guard_report(allowed=True):
    return {
        "allowed": allowed,
        "violations": [] if allowed else ["blocked"],
        "report_file": "logs/workspace_forensics/workspace_guard_latest.json",
        "history_file": "logs/workspace_forensics/workspace_guard_history.jsonl",
    }


def _stage_report(mode: str, candidates: int):
    return {
        "ok": True,
        "mode": mode,
        "candidate_count": candidates,
        "status_counts": {"untracked": candidates, "deleted": 0, "modified": 0},
        "sample_paths": ["x"],
    }


@patch("ai_collab.cli._cli_main._set_workspace_env")
@patch("ai_collab.cli._cli_main.VSCodeIntegration")
@patch("ai_collab.cli._cli_main.run_workspace_guard")
@patch("ai_collab.cli._cli_main.stage_domain_changes")
@patch("ai_collab.cli._cli_main.inspect_workspace")
def test_cmd_hygiene_dry_run_preview_only(
    mock_inspect,
    mock_stage,
    mock_guard,
    mock_vscode,
    _mock_set_env,
    tmp_path,
):
    mock_vscode.get_project_config.return_value = {
        "workspaceHygiene": {
            "enabled": True,
            "domainOrder": ["ops", "docs", "other"],
            "autoStage": True,
            "maxCandidatesPerRun": 200,
        },
        "workspaceGuard": {},
    }
    mock_guard.return_value = _guard_report(True)
    mock_stage.side_effect = [
        _stage_report("dry-run", 2),
        _stage_report("dry-run", 1),
        _stage_report("dry-run", 0),
    ]
    mock_inspect.side_effect = [{"ok": True}, {"ok": True}]

    args = SimpleNamespace(
        workspace=str(tmp_path),
        dry_run=True,
        loop=False,
        interval_sec=None,
        max_iterations=0,
        include_source=False,
        auto_stage=None,
        max_candidates=None,
        force_workspace=False,
        trigger_source="manual",
    )

    assert cli.cmd_hygiene(args) == 0
    calls = [
        call(workspace=tmp_path, domain="ops", dry_run=True),
        call(workspace=tmp_path, domain="docs", dry_run=True),
        call(workspace=tmp_path, domain="other", dry_run=True),
    ]
    assert mock_stage.call_args_list == calls


@patch("ai_collab.cli._cli_main._set_workspace_env")
@patch("ai_collab.cli._cli_main.VSCodeIntegration")
@patch("ai_collab.cli._cli_main.run_workspace_guard")
@patch("ai_collab.cli._cli_main.stage_domain_changes")
@patch("ai_collab.cli._cli_main.inspect_workspace")
def test_cmd_hygiene_apply_runs_preview_then_apply_for_candidates(
    mock_inspect,
    mock_stage,
    mock_guard,
    mock_vscode,
    _mock_set_env,
    tmp_path,
):
    mock_vscode.get_project_config.return_value = {
        "workspaceHygiene": {
            "enabled": True,
            "domainOrder": ["ops", "docs", "other"],
            "autoStage": True,
            "maxCandidatesPerRun": 200,
        },
        "workspaceGuard": {},
    }
    mock_guard.return_value = _guard_report(True)
    mock_stage.side_effect = [
        _stage_report("dry-run", 2),
        _stage_report("dry-run", 0),
        _stage_report("dry-run", 1),
        _stage_report("apply", 2),
        _stage_report("apply", 1),
    ]
    mock_inspect.side_effect = [{"ok": True}, {"ok": True}]

    args = SimpleNamespace(
        workspace=str(tmp_path),
        dry_run=False,
        loop=False,
        interval_sec=None,
        max_iterations=0,
        include_source=False,
        auto_stage=None,
        max_candidates=None,
        force_workspace=False,
        trigger_source="manual",
    )

    assert cli.cmd_hygiene(args) == 0
    calls = [
        call(workspace=tmp_path, domain="ops", dry_run=True),
        call(workspace=tmp_path, domain="docs", dry_run=True),
        call(workspace=tmp_path, domain="other", dry_run=True),
        call(workspace=tmp_path, domain="ops", dry_run=False),
        call(workspace=tmp_path, domain="other", dry_run=False),
    ]
    assert mock_stage.call_args_list == calls


@patch("ai_collab.cli._cli_main._set_workspace_env")
@patch("ai_collab.cli._cli_main._run_workspace_guard_gate")
@patch("ai_collab.cli._cli_main._execute_hygiene_once")
@patch("ai_collab.cli._cli_main._read_json_if_exists")
@patch("ai_collab.cli._cli_main.VSCodeIntegration")
@patch("ai_collab.cli.subprocess.run")
def test_cmd_receipt_triggers_post_hygiene_when_completed(
    mock_run,
    mock_vscode,
    mock_read_json,
    mock_hygiene,
    mock_guard_gate,
    _mock_set_env,
    tmp_path,
):
    mock_run.return_value = SimpleNamespace(returncode=0)
    mock_guard_gate.return_value = True
    mock_hygiene.return_value = {"blocked": False, "error_count": 0, "report_file": "logs/x.json"}
    mock_read_json.return_value = {"completed_count": 2}
    mock_vscode.get_project_config.return_value = {
        "receipt": {
            "report": "logs/task_receipt_report.json",
            "history": "logs/task_receipt_history.jsonl",
            "state": "logs/agent_receipt_state.json",
            "summary": "collaboration/monitoring/AGENT_RECEIPT_SUMMARY_latest.md",
        },
        "workspaceHygiene": {"onReceiptClose": True, "autoStage": False},
        "workspaceGuard": {},
    }

    args = SimpleNamespace(
        workspace=str(tmp_path),
        dry_run=False,
        reclose=False,
        force_workspace=False,
        report=None,
        history=None,
        state=None,
        summary=None,
    )

    assert cli.cmd_receipt(args) == 0
    assert mock_hygiene.call_count == 1
    assert mock_hygiene.call_args.kwargs["trigger_source"] == "post-receipt"


@patch("ai_collab.cli._cli_main._set_workspace_env")
@patch("ai_collab.cli._cli_main._run_workspace_guard_gate")
@patch("ai_collab.cli._cli_main._execute_hygiene_once")
@patch("ai_collab.cli._cli_main._read_json_if_exists")
@patch("ai_collab.cli._cli_main.VSCodeIntegration")
@patch("ai_collab.cli.subprocess.run")
def test_cmd_receipt_skips_post_hygiene_when_no_completed(
    mock_run,
    mock_vscode,
    mock_read_json,
    mock_hygiene,
    mock_guard_gate,
    _mock_set_env,
    tmp_path,
):
    mock_run.return_value = SimpleNamespace(returncode=0)
    mock_guard_gate.return_value = True
    mock_read_json.return_value = {"completed_count": 0}
    mock_vscode.get_project_config.return_value = {
        "receipt": {
            "report": "logs/task_receipt_report.json",
            "history": "logs/task_receipt_history.jsonl",
            "state": "logs/agent_receipt_state.json",
            "summary": "collaboration/monitoring/AGENT_RECEIPT_SUMMARY_latest.md",
        },
        "workspaceHygiene": {"onReceiptClose": True, "autoStage": True},
        "workspaceGuard": {},
    }

    args = SimpleNamespace(
        workspace=str(tmp_path),
        dry_run=False,
        reclose=False,
        force_workspace=False,
        report=None,
        history=None,
        state=None,
        summary=None,
    )

    assert cli.cmd_receipt(args) == 0
    mock_hygiene.assert_not_called()
