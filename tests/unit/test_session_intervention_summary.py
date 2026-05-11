"""Unit tests focused on intervention summary markdown rendering."""

from __future__ import annotations

from pathlib import Path

from ai_collab.intervention_queue import (
    DEFAULT_SUMMARY_PATH,
    build_summary_markdown,
    enqueue_intervention,
    read_intervention_items,
    render_intervention_pack,
    render_intervention_summary_markdown,
    summarize_intervention_items,
)


def test_build_summary_markdown_includes_pending_and_recent_sections():
    items = [
        {
            "intervention_id": "intervention-002",
            "session_id": "session-b",
            "assignee": "codearts_agent",
            "reason_code": "stale_payload",
            "message_artifact": "artifact-b.md",
            "delivery_mode": "bridge",
            "delivery_status": "queued_for_delivery",
            "created_at": "2026-03-28T20:00:02",
            "updated_at": "2026-03-28T20:00:02",
        },
        {
            "intervention_id": "intervention-001",
            "session_id": "session-a",
            "assignee": "claude_code",
            "reason_code": "ack_timeout",
            "message_artifact": "artifact-a.md",
            "delivery_mode": "manual",
            "delivery_status": "pending_operator_delivery",
            "created_at": "2026-03-28T20:00:01",
            "updated_at": "2026-03-28T20:00:03",
        },
    ]
    stats = summarize_intervention_items({item["intervention_id"]: item for item in items})
    report = {
        "generated_at": "2026-03-28T20:05:00",
        "workspace": "/tmp/ws",
        "mode": "summary",
        **stats,
    }

    summary = build_summary_markdown(report=report, items=items)
    assert "Pending Operator Delivery" in summary
    assert "Recent Interventions" in summary
    assert "`intervention-001`" in summary
    assert "artifact: `artifact-a.md`" in summary
    assert "queued_for_delivery" in summary


def test_render_intervention_summary_markdown_writes_file(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    enqueue_intervention(
        workspace=workspace,
        session_id="session-claude",
        assignee="claude_code",
        reason_code="ack_timeout",
        severity="high",
        message_artifact="collaboration/monitoring/AGENT_TRIGGER_claude_code_latest.md",
        intervention_id="intervention-claude",
    )
    enqueue_intervention(
        workspace=workspace,
        session_id="session-codex",
        assignee="codex",
        reason_code="result_mismatch",
        severity="medium",
        message_artifact="collaboration/monitoring/SESSION_INTERVENTION_PAYLOAD_codex.md",
        intervention_id="intervention-codex",
    )

    markdown = render_intervention_summary_markdown(workspace=workspace)
    assert "Session Intervention Summary" in markdown
    assert "intervention 总数: `2`" in markdown
    assert "`intervention-claude`" in markdown
    assert "`intervention-codex`" in markdown

    summary_file = workspace / DEFAULT_SUMMARY_PATH
    assert summary_file.exists()
    file_text = summary_file.read_text(encoding="utf-8")
    assert file_text == markdown

    records = read_intervention_items(workspace=workspace)
    assert len(records) == 2


def test_render_intervention_pack_writes_assignee_pack(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    artifact = workspace / "collaboration" / "monitoring" / "session_interventions" / "example.md"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        "# Session Intervention Artifact\n\n## Exact Forward Message\n\n```text\n请补发 ACK。\n```\n",
        encoding="utf-8",
    )

    enqueue_intervention(
        workspace=workspace,
        session_id="session-claude",
        assignee="claude_code",
        reason_code="missing_explicit_ack",
        severity="high",
        message_artifact="collaboration/monitoring/session_interventions/example.md",
        intervention_id="intervention-claude-pack",
    )
    enqueue_intervention(
        workspace=workspace,
        session_id="session-codearts",
        assignee="codearts_agent",
        reason_code="closeout_followup",
        severity="medium",
        message_artifact="collaboration/monitoring/session_interventions/example.md",
        intervention_id="intervention-codearts-pack",
    )

    report = render_intervention_pack(workspace=workspace, assignee="claude_code")

    pack_file = workspace / report["pack_file"]
    assert pack_file.exists()
    markdown = pack_file.read_text(encoding="utf-8")
    assert "intervention-claude-pack" in markdown
    assert "请补发 ACK。" in markdown
    assert "intervention-codearts-pack" not in markdown
