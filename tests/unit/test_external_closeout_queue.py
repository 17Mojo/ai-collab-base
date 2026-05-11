import json
from pathlib import Path

from ai_collab.external_closeout_queue import render_external_closeout_queue
from ai_collab.intervention_queue import enqueue_intervention


def _write_workspace_config(workspace: Path) -> None:
    config = {
        "version": "1.0.0",
        "stateFile": "logs/collaboration_state.json",
        "sessionOrchestration": {
            "interventionState": "logs/session_intervention_state.json",
            "interventionHistory": "logs/session_intervention_history.jsonl",
            "interventionSummary": "collaboration/monitoring/SESSION_INTERVENTION_SUMMARY_latest.md",
            "interventionPackDir": "collaboration/monitoring/intervention_packs",
        },
    }
    vscode_dir = workspace / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    (vscode_dir / "ai-collab.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_task_state(workspace: Path) -> None:
    state = {
        "tasks": {
            "TASK-TD-20260328-GOVERNANCE-STATE-CLI-HEALTH-SEMANTICS-CLAUDE-146": {
                "status": "blocked",
                "assignee": "claude_code",
                "ai_type": "claude_code",
                "description": "Claude closeout follow-up",
                "result_file": "collaboration/results/RESULT_TASK-TD-20260328-GOVERNANCE-STATE-CLI-HEALTH-SEMANTICS-CLAUDE-146.md",
                "updated_at": "2026-03-29T09:10:00",
                "notes": [
                    "[2026-03-29T09:10:00] reviewer reopen: refresh result scope and emit fresh C.ACK"
                ],
            },
            "TASK-TD-20260328-SESSION-INTERVENTION-QUEUE-AUDIT-CODEARTS-149": {
                "status": "pending",
                "assignee": "codearts_agent",
                "ai_type": "codearts_agent",
                "description": "CodeArts closeout follow-up",
                "result_file": "collaboration/results/RESULT_TASK-TD-20260328-SESSION-INTERVENTION-QUEUE-AUDIT-CODEARTS-149.md",
                "updated_at": "2026-03-29T09:11:00",
                "notes": [],
            },
        },
        "active_tasks": [
            "TASK-TD-20260328-GOVERNANCE-STATE-CLI-HEALTH-SEMANTICS-CLAUDE-146",
            "TASK-TD-20260328-SESSION-INTERVENTION-QUEUE-AUDIT-CODEARTS-149",
        ],
    }
    state_file = workspace / "logs" / "collaboration_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_pack(workspace: Path, assignee: str) -> None:
    pack_file = (
        workspace
        / "collaboration"
        / "monitoring"
        / "intervention_packs"
        / f"SESSION_INTERVENTION_PACK_{assignee}_latest.md"
    )
    pack_file.parent.mkdir(parents=True, exist_ok=True)
    pack_file.write_text(f"# Pack for {assignee}\n", encoding="utf-8")


def test_render_external_closeout_queue_writes_latest_markdown(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)
    _write_task_state(workspace)
    _write_pack(workspace, "claude_code")
    _write_pack(workspace, "codearts_agent")

    artifact = workspace / "collaboration" / "monitoring" / "session_interventions" / "closeout.md"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("# Intervention\n", encoding="utf-8")

    enqueue_intervention(
        workspace=workspace,
        session_id="claude-main",
        assignee="claude_code",
        reason_code="closeout_followup",
        severity="medium",
        message_artifact="collaboration/monitoring/session_interventions/closeout.md",
        intervention_id="intervention-claude-closeout",
    )
    enqueue_intervention(
        workspace=workspace,
        session_id="unregistered:codearts_agent",
        assignee="codearts_agent",
        reason_code="unregistered_session",
        severity="medium",
        message_artifact="collaboration/monitoring/session_interventions/closeout.md",
        intervention_id="intervention-codearts-unregistered",
    )

    report = render_external_closeout_queue(workspace=workspace)

    output_file = workspace / report["output_file"]
    assert output_file.exists()
    markdown = output_file.read_text(encoding="utf-8")
    assert "TASK-TD-20260328-GOVERNANCE-STATE-CLI-HEALTH-SEMANTICS-CLAUDE-146" in markdown
    assert "reviewer reopen: refresh result scope and emit fresh C.ACK" in markdown
    assert "SESSION_INTERVENTION_PACK_claude_code_latest.md" in markdown
    assert "intervention-codearts-unregistered" in markdown
    assert "先注册当前活跃会话" in markdown
    assert report["blocking_intervention_count"] == 1
    assert report["ready_pack_count"] == 2


def test_render_external_closeout_queue_surfaces_manual_packets_without_blockers(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)
    _write_pack(workspace, "claude_code")
    _write_pack(workspace, "codearts_agent")

    artifact = workspace / "collaboration" / "monitoring" / "session_interventions" / "closeout.md"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("# Intervention\n", encoding="utf-8")

    enqueue_intervention(
        workspace=workspace,
        session_id="claude-main",
        assignee="claude_code",
        reason_code="closeout_followup",
        severity="medium",
        message_artifact="collaboration/monitoring/session_interventions/closeout.md",
        intervention_id="intervention-claude-closeout",
    )
    enqueue_intervention(
        workspace=workspace,
        session_id="unregistered:codearts_agent",
        assignee="codearts_agent",
        reason_code="closeout_followup",
        severity="medium",
        message_artifact="collaboration/monitoring/session_interventions/closeout.md",
        intervention_id="intervention-codearts-closeout",
    )

    report = render_external_closeout_queue(workspace=workspace)

    assert report["active_task_count"] == 0
    assert report["blocking_intervention_count"] == 0
    assert report["open_intervention_count"] == 2
    assert report["recommended_order"] == [
        "1. `Claude` 当前无 health blocker，但仍有待转发的 manual intervention pack；按 `collaboration/monitoring/intervention_packs/SESSION_INTERVENTION_PACK_claude_code_latest.md` 人工投递并等待外部回执。",
        "2. `CodeArts` 当前无 health blocker，但会话仍未注册；先注册当前活跃会话，再按 `collaboration/monitoring/intervention_packs/SESSION_INTERVENTION_PACK_codearts_agent_latest.md` 人工投递并等待外部回执。",
    ]

    markdown = (workspace / report["output_file"]).read_text(encoding="utf-8")
    assert "当前没有 external closeout backlog" not in markdown
    assert "manual intervention pack" in markdown
