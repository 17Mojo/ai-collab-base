import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_locks.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _write_lock_report(path: Path, row: str) -> None:
    path.write_text(
        "\n".join(
            [
                "# test",
                "",
                "## 当前认领看板（Current Locks）",
                "",
                "| 状态 | owner | task | start | note |",
                "|---|---|---|---|---|",
                row,
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_validate_locks_accepts_cancelled_status(tmp_path):
    report = tmp_path / "lock_report.md"
    _write_lock_report(
        report,
        "| `CANCELLED` | claude_code | TASK-CANCEL-001 | 2026-03-01T13:50:00+08:00 | no longer needed |",
    )

    result = _run("--files", str(report))
    assert result.returncode == 0, result.stderr
    assert "[OK] lock validation passed" in result.stdout


def test_validate_locks_rejects_unknown_status(tmp_path):
    report = tmp_path / "lock_report_unknown.md"
    _write_lock_report(
        report,
        "| `PAUSED` | claude_code | TASK-PAUSE-001 | 2026-03-01T13:50:00+08:00 | waiting |",
    )

    result = _run("--files", str(report))
    assert result.returncode == 1
    assert "unknown status 'PAUSED'" in result.stdout
