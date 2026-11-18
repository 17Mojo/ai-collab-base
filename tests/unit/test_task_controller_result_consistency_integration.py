from pathlib import Path

import pytest

daemon = pytest.importorskip("scripts.task_controller_daemon", reason="scripts/task_controller_daemon.py not present")


class _FakeManager:
    def __init__(self, *, workspace_path: str):
        self.workspace_path = workspace_path
        self.state = {
            "tasks": {},
            "patches": {},
            "active_tasks": [],
            "completed_tasks": [],
        }

    def validate_task_contracts(self, scope: str = "active"):
        assert scope == "active"
        return {
            "checked_tasks": 3,
            "skipped_tasks": 1,
            "invalid_count": 2,
            "issues": [{"task_id": "TASK-INVALID-001", "issue": "missing acceptance"}],
        }


def test_run_controller_once_exposes_result_consistency_metrics(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(daemon, "StateManager", _FakeManager)
    monkeypatch.setattr(
        daemon,
        "run_terminal_result_consistency_audit",
        lambda *, workspace: {
            "audited_count": 4,
            "consistent_count": 1,
            "mismatch_count": 2,
            "unparseable_count": 1,
            "missing_result_count": 0,
            "issue_count": 3,
            "report_file": "logs/task_result_consistency_report.json",
            "summary_file": "collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md",
        },
    )
    monkeypatch.setattr(daemon, "detect_state_drifts", lambda state, workspace: [])
    monkeypatch.setattr(daemon, "detect_prewarning_tasks", lambda **kwargs: [])
    monkeypatch.setattr(daemon, "detect_stale_tasks", lambda **kwargs: [])
    monkeypatch.setattr(daemon, "detect_patch_candidates", lambda state: [])
    monkeypatch.setattr(
        daemon,
        "run_ack_watchdog",
        lambda *, workspace, dry_run: {
            "candidate_count": 0,
            "redispatched_count": 0,
            "alerted_count": 0,
        },
    )

    report = daemon.run_controller_once(
        workspace=tmp_path,
        pending_timeout_sec=7200,
        active_timeout_sec=1800,
        blocked_timeout_sec=3600,
        prewarn_ratio=0.8,
        dry_run=True,
        default_assignee="codex",
    )

    assert report["mode"] == "dry-run"
    assert report["task_contract_checked"] == 3
    assert report["task_contract_invalid"] == 2
    assert report["result_consistency_audited"] == 4
    assert report["result_consistency_consistent"] == 1
    assert report["result_consistency_mismatch"] == 2
    assert report["result_consistency_unparseable"] == 1
    assert report["result_consistency_missing_result"] == 0
    assert report["result_consistency_issue_count"] == 3
    assert report["result_consistency_report_file"] == "logs/task_result_consistency_report.json"
    assert (
        report["result_consistency_summary_file"]
        == "collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md"
    )
    assert report["error_count"] == 0


def test_daemon_audit_delegates_to_the_authoritative_implementation(tmp_path: Path):
    """守护进程不许再自带一份弱化版一致性审计（台账 N45）。

    守的是一个真实后果：那份副本会**覆写真实现用的同一个报告文件**，
    于是「谁后跑谁说了算」。这里用一条副本根本做不到的判据来区分——
    「停在 testing、已 ok ACK、产物不存在」要能报出 ack_without_artifact。
    """
    import json

    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "collaboration" / "results").mkdir(parents=True, exist_ok=True)
    (tmp_path / "logs" / "collaboration_state.json").write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "workspace": str(tmp_path),
                "tasks": {
                    "T-STUCK": {
                        "task_id": "T-STUCK",
                        "status": "testing",
                        "result_file": "collaboration/results/RESULT-MISSING.md",
                        "ai_type": "claude_code",
                        "assignee": "claude_code",
                    }
                },
                "patches": {},
                "active_tasks": ["T-STUCK"],
                "completed_tasks": [],
                "conflicts": [],
                "file_status": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "logs" / "agent_ack_bridge_state.json").write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "items": {
                    "T-STUCK": {
                        "task_id": "T-STUCK",
                        "ack_line": "X.ACK|task=T-STUCK|status=ok|result=collaboration/results/RESULT-MISSING.md",
                        "source": "cli-ack",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = daemon.run_terminal_result_consistency_audit(workspace=tmp_path)
    assert report["ack_without_artifact_count"] == 1, (
        "守护进程的审计没跑权威实现——如果这里忽然变回 0，说明又长出了一份弱化副本（N45）"
    )
    assert [i["issue_type"] for i in report["issues"]] == ["ack_without_artifact"]
