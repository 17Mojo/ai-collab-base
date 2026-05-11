import json
from datetime import datetime
from pathlib import Path

from ai_collab import session_continuation_handoff as handoff


def _write_workspace_config(workspace: Path) -> None:
    vscode_dir = workspace / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    (vscode_dir / "ai-collab.json").write_text(
        json.dumps(
            {
                "sessionOrchestration": {
                    "continuationHandoff": {
                        "report": "logs/session_continuation_handoff_report.json",
                        "history": "logs/session_continuation_handoff_history.jsonl",
                        "summary": "collaboration/monitoring/SESSION_CONTINUATION_HANDOFF_SUMMARY_latest.md",
                        "outputDir": "collaboration/results",
                        "filenamePrefix": "SESSION_CONTINUATION_HANDOFF",
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_session_continuation_handoff_writes_standard_outputs(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)
    (workspace / "openspec" / "changes" / "add-session-orchestration-control-plane").mkdir(parents=True)

    monkeypatch.setattr(
        handoff,
        "run_session_health_aggregation",
        lambda **kwargs: {
            "session_count": 3,
            "incident_count": 2,
            "open_intervention_count": 2,
            "unregistered_count": 1,
            "report_file": "logs/session_health_report.json",
            "summary_file": "collaboration/monitoring/SESSION_HEALTH_SUMMARY_latest.md",
            "incidents": [
                {
                    "assignee": "claude_code",
                    "reason_code": "unregistered_session",
                    "summary": "claude missing session registration",
                }
            ],
        },
    )
    monkeypatch.setattr(
        handoff,
        "run_claude_push_adapter",
        lambda **kwargs: {
            "candidate_count": 1,
            "artifact_only_count": 1,
            "failed_count": 0,
            "report_file": "logs/claude_adapter_report.json",
            "summary_file": "collaboration/monitoring/CLAUDE_ADAPTER_SUMMARY_latest.md",
        },
    )
    monkeypatch.setattr(
        handoff,
        "run_codearts_pull_adapter",
        lambda **kwargs: {
            "candidate_count": 2,
            "artifact_only_count": 2,
            "failed_count": 0,
            "report_file": "logs/codearts_adapter_report.json",
            "summary_file": "collaboration/monitoring/CODEARTS_ADAPTER_SUMMARY_latest.md",
        },
    )
    monkeypatch.setattr(
        handoff,
        "render_external_closeout_queue",
        lambda **kwargs: {
            "active_task_count": 2,
            "open_intervention_count": 3,
            "blocking_intervention_count": 1,
            "ready_pack_count": 2,
            "output_file": "collaboration/monitoring/EXTERNAL_CLOSEOUT_QUEUE_2026-03-29_latest.md",
            "report_file": "logs/external_closeout_queue_report.json",
            "history_file": "logs/external_closeout_queue_history.jsonl",
        },
    )

    report = handoff.run_session_continuation_handoff(
        workspace=workspace,
        next_slice="Implement the CodeArts pull adapter next.",
        completed_items=["Claude push adapter validated"],
        validation_commands=["python3 -m pytest -q tests/unit/test_claude_adapter.py"],
        related_files=["ai_collab/adapters/claude_adapter.py"],
    )

    output_file = workspace / report["output_file"]
    report_file = workspace / report["report_file"]
    summary_file = workspace / report["summary_file"]
    history_file = workspace / report["history_file"]

    assert output_file.exists()
    assert report_file.exists()
    assert summary_file.exists()
    assert history_file.exists()

    markdown = output_file.read_text(encoding="utf-8")
    assert "Session Continuation Handoff" in markdown
    assert "Implement the CodeArts pull adapter next." in markdown
    assert "继续 ai-collab-system 的 session-orchestration 控制面工作。" in markdown
    assert "EXTERNAL_CLOSEOUT_QUEUE_2026-03-29_latest.md" in markdown

    payload = json.loads(report_file.read_text(encoding="utf-8"))
    assert payload["health_snapshot"]["session_count"] == 3
    assert payload["claude_push_snapshot"]["candidate_count"] == 1
    assert payload["codearts_pull_snapshot"]["candidate_count"] == 2
    assert payload["closeout_queue_snapshot"]["active_task_count"] == 2
    assert "collaboration/monitoring/EXTERNAL_CLOSEOUT_QUEUE_2026-03-29_latest.md" in payload["related_files"]
    assert payload["active_changes"] == ["add-session-orchestration-control-plane"]


def test_session_continuation_handoff_allocates_unique_filename(tmp_path: Path, monkeypatch):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)
    output_dir = workspace / "collaboration" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().date().isoformat()
    (output_dir / f"SESSION_CONTINUATION_HANDOFF_{today}.md").write_text("existing", encoding="utf-8")

    monkeypatch.setattr(handoff, "run_session_health_aggregation", lambda **kwargs: {})
    monkeypatch.setattr(handoff, "run_claude_push_adapter", lambda **kwargs: {})
    monkeypatch.setattr(handoff, "run_codearts_pull_adapter", lambda **kwargs: {})
    monkeypatch.setattr(handoff, "render_external_closeout_queue", lambda **kwargs: {})

    report = handoff.run_session_continuation_handoff(workspace=workspace)

    assert report["output_file"].endswith(f"SESSION_CONTINUATION_HANDOFF_{today}_01.md")
