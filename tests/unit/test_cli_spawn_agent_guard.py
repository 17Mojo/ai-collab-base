import argparse
from pathlib import Path
from unittest.mock import patch

from ai_collab import cli


@patch("ai_collab.cli._cli_main._set_workspace_env")
@patch("ai_collab.cli._cli_main.VSCodeIntegration")
@patch("ai_collab.cli._cli_main.run_spawn_agent_guard")
def test_cmd_spawn_agent_guard_uses_config_defaults_and_overrides(mock_run, mock_vscode, _mock_set_env, tmp_path: Path):
    mock_vscode.get_project_config.return_value = {
        "spawnAgentGuard": {
            "enabled": True,
            "allowedLeadAgents": ["codex"],
            "report": "logs/workspace_forensics/spawn_agent_guard_latest.json",
            "history": "logs/workspace_forensics/spawn_agent_guard_history.jsonl",
        }
    }
    mock_run.return_value = {
        "allowed": True,
        "actor": "codex",
        "mode": "write",
        "parent_task_id": "TASK-001",
        "files": ["ai_collab/cli.py"],
        "warnings": [],
        "violations": [],
        "active_conflicts": [],
        "report_file": "logs/custom-report.json",
        "history_file": "logs/custom-history.jsonl",
    }

    args = argparse.Namespace(
        workspace=str(tmp_path),
        actor="codex",
        parent_task="TASK-001",
        files=["ai_collab/cli.py"],
        read_only=False,
        report="logs/custom-report.json",
        history="logs/custom-history.jsonl",
    )

    result = cli.cmd_spawn_agent_guard(args)

    assert result == 0
    called = mock_run.call_args.kwargs
    assert called["workspace"] == Path(tmp_path)
    assert called["actor"] == "codex"
    assert called["parent_task_id"] == "TASK-001"
    assert called["files"] == ["ai_collab/cli.py"]
    assert called["read_only"] is False
    assert called["config"]["spawnAgentGuard"]["report"] == "logs/custom-report.json"
    assert called["config"]["spawnAgentGuard"]["history"] == "logs/custom-history.jsonl"


@patch("ai_collab.cli._cli_main._set_workspace_env")
@patch("ai_collab.cli._cli_main.VSCodeIntegration")
@patch("ai_collab.cli._cli_main.run_spawn_agent_guard")
def test_cmd_spawn_agent_guard_returns_2_when_denied(mock_run, mock_vscode, _mock_set_env, tmp_path: Path):
    mock_vscode.get_project_config.return_value = {"spawnAgentGuard": {"enabled": True}}
    mock_run.return_value = {
        "allowed": False,
        "actor": "codex",
        "mode": "write",
        "parent_task_id": "TASK-002",
        "files": [".vscode/ai-collab.json"],
        "warnings": [],
        "violations": ["declared files include protected paths: .vscode/ai-collab.json"],
        "active_conflicts": [],
        "report_file": "logs/workspace_forensics/spawn_agent_guard_latest.json",
        "history_file": "logs/workspace_forensics/spawn_agent_guard_history.jsonl",
    }

    args = argparse.Namespace(
        workspace=str(tmp_path),
        actor="codex",
        parent_task="TASK-002",
        files=[".vscode/ai-collab.json"],
        read_only=False,
        report=None,
        history=None,
    )

    result = cli.cmd_spawn_agent_guard(args)

    assert result == 2
