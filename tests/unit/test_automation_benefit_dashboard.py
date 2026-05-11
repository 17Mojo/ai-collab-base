import json
import subprocess
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "collaboration"
    / "scripts"
    / "build_automation_benefit_dashboard.py"
)


def _write_jsonl(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _run_dashboard(workspace: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        "python3",
        str(SCRIPT),
        "--workspace",
        str(workspace),
        "--dispatch-history",
        "logs/task_dispatch_history.jsonl",
        "--receipt-history",
        "logs/task_receipt_history.jsonl",
        "--target-ratio",
        "3",
        "--window",
        "14",
        "--report",
        "logs/automation_benefit_report_test.json",
        "--output",
        "collaboration/monitoring/AUTOMATION_BENEFIT_DASHBOARD_test.md",
    ]
    cmd.extend(list(extra_args))
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_benefit_dashboard_generates_report_and_markdown(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    _write_jsonl(
        workspace / "logs" / "task_dispatch_history.jsonl",
        [
            {
                "generated_at": "2026-03-03T09:00:00+08:00",
                "dispatched_count": 6,
            }
        ],
    )
    _write_jsonl(
        workspace / "logs" / "task_receipt_history.jsonl",
        [
            {
                "generated_at": "2026-03-03T09:10:00+08:00",
                "completed_count": 6,
            }
        ],
    )

    result = _run_dashboard(workspace)
    assert result.returncode == 0, result.stderr

    report_path = workspace / "logs" / "automation_benefit_report_test.json"
    output_path = (
        workspace / "collaboration" / "monitoring" / "AUTOMATION_BENEFIT_DASHBOARD_test.md"
    )
    assert report_path.exists()
    assert output_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["overall_efficiency_ratio"] >= 3.0
    assert report["overall_target_achieved"] is True
    assert report["day_count"] == 1

    content = output_path.read_text(encoding="utf-8")
    assert "自动化收益看板" in content
    assert "总体效率比" in content


def test_benefit_dashboard_handles_empty_history(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    result = _run_dashboard(workspace)
    assert result.returncode == 0, result.stderr

    report = json.loads(
        (workspace / "logs" / "automation_benefit_report_test.json").read_text(encoding="utf-8")
    )
    assert report["day_count"] == 0
    assert report["overall_efficiency_ratio"] == 0.0
    assert report["overall_target_achieved"] is False


def test_benefit_dashboard_dry_run_does_not_write_files(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    _write_jsonl(
        workspace / "logs" / "task_dispatch_history.jsonl",
        [{"generated_at": "2026-03-03T09:00:00+08:00", "dispatched_count": 2}],
    )
    _write_jsonl(
        workspace / "logs" / "task_receipt_history.jsonl",
        [{"generated_at": "2026-03-03T09:10:00+08:00", "completed_count": 2}],
    )

    result = _run_dashboard(workspace, "--dry-run")
    assert result.returncode == 0, result.stderr
    assert "mode=dry-run" in result.stdout
    assert not (workspace / "logs" / "automation_benefit_report_test.json").exists()
    assert not (
        workspace / "collaboration" / "monitoring" / "AUTOMATION_BENEFIT_DASHBOARD_test.md"
    ).exists()
