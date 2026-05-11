import json
import subprocess
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "collaboration"
    / "scripts"
    / "run_daily_benefit_snapshot.py"
)


def _write_jsonl(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _run_snapshot(workspace: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        "python3",
        str(SCRIPT),
        "--workspace",
        str(workspace),
        "--dispatch-history",
        "logs/task_dispatch_history.jsonl",
        "--receipt-history",
        "logs/task_receipt_history.jsonl",
        "--latest-report",
        "logs/automation_benefit_report_test.json",
        "--latest-dashboard",
        "collaboration/monitoring/AUTOMATION_BENEFIT_DASHBOARD_test.md",
        "--dated-report-dir",
        "logs/automation_benefit/daily-test",
        "--daily-history",
        "logs/automation_benefit_daily_history_test.jsonl",
    ]
    cmd.extend(list(extra_args))
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_daily_snapshot_writes_latest_and_dated_files(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    _write_jsonl(
        workspace / "logs" / "task_dispatch_history.jsonl",
        [{"generated_at": "2026-03-03T09:00:00+08:00", "dispatched_count": 4}],
    )
    _write_jsonl(
        workspace / "logs" / "task_receipt_history.jsonl",
        [{"generated_at": "2026-03-03T09:10:00+08:00", "completed_count": 4}],
    )

    result = _run_snapshot(workspace)
    assert result.returncode == 0, result.stderr

    latest_report = workspace / "logs" / "automation_benefit_report_test.json"
    latest_dashboard = (
        workspace / "collaboration" / "monitoring" / "AUTOMATION_BENEFIT_DASHBOARD_test.md"
    )
    assert latest_report.exists()
    assert latest_dashboard.exists()

    report = json.loads(latest_report.read_text(encoding="utf-8"))
    assert report["overall_efficiency_ratio"] >= 3.0
    assert report["overall_target_achieved"] is True

    history = workspace / "logs" / "automation_benefit_daily_history_test.jsonl"
    assert history.exists()
    lines = [line for line in history.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["overall_target_achieved"] is True


def test_daily_snapshot_dry_run_does_not_write(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    _write_jsonl(
        workspace / "logs" / "task_dispatch_history.jsonl",
        [{"generated_at": "2026-03-03T09:00:00+08:00", "dispatched_count": 1}],
    )
    _write_jsonl(
        workspace / "logs" / "task_receipt_history.jsonl",
        [{"generated_at": "2026-03-03T09:10:00+08:00", "completed_count": 1}],
    )

    result = _run_snapshot(workspace, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert "mode=dry-run" in result.stdout

    assert not (workspace / "logs" / "automation_benefit_report_test.json").exists()
    assert not (
        workspace / "collaboration" / "monitoring" / "AUTOMATION_BENEFIT_DASHBOARD_test.md"
    ).exists()
    assert not (workspace / "logs" / "automation_benefit_daily_history_test.jsonl").exists()


def test_daily_snapshot_upserts_same_date_history(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    dispatch = workspace / "logs" / "task_dispatch_history.jsonl"
    receipt = workspace / "logs" / "task_receipt_history.jsonl"

    _write_jsonl(dispatch, [{"generated_at": "2026-03-03T09:00:00+08:00", "dispatched_count": 2}])
    _write_jsonl(receipt, [{"generated_at": "2026-03-03T09:10:00+08:00", "completed_count": 2}])
    first = _run_snapshot(workspace)
    assert first.returncode == 0, first.stderr

    _write_jsonl(dispatch, [{"generated_at": "2026-03-03T10:00:00+08:00", "dispatched_count": 6}])
    _write_jsonl(receipt, [{"generated_at": "2026-03-03T10:10:00+08:00", "completed_count": 6}])
    second = _run_snapshot(workspace)
    assert second.returncode == 0, second.stderr

    history = workspace / "logs" / "automation_benefit_daily_history_test.jsonl"
    rows = [
        json.loads(line)
        for line in history.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    assert rows[0]["overall_efficiency_ratio"] == 6.0
