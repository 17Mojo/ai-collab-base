import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_collaboration_governance.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _write_lock_report(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "# report",
                "",
                "## 当前认领看板（Current Locks）",
                "",
                "| 状态 | owner | task | start | note |",
                "|---|---|---|---|---|",
                "| `none` | - | - | - | 当前无进行中锁 |",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _prepare_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()

    # required files
    (ws / "collaboration").mkdir()
    (ws / "rules").mkdir()
    (ws / "scripts").mkdir()
    (ws / "collaboration" / "AI_BEHAVIOR_CONSTRAINT_FILES.md").write_text("ok", encoding="utf-8")
    (ws / "collaboration" / "COLLABORATION_GUIDELINES.md").write_text("ok", encoding="utf-8")
    (ws / "collaboration" / "PROTOCOL.md").write_text("ok", encoding="utf-8")
    (ws / "collaboration" / "CROSS_AI_COLLABORATION_STANDARDS.md").write_text(
        "ok", encoding="utf-8"
    )
    (ws / "collaboration" / "RESOURCE_USAGE_POLICY.md").write_text("ok", encoding="utf-8")
    (ws / "rules" / "AI-COLLABORATION-STANDARDS.md").write_text("ok", encoding="utf-8")

    # agents refs
    (ws / "AGENTS.md").write_text(
        "\n".join(
            [
                "collaboration/AI_BEHAVIOR_CONSTRAINT_FILES.md",
                "collaboration/COLLABORATION_GUIDELINES.md",
                "collaboration/PROTOCOL.md",
                "collaboration/RESOURCE_USAGE_POLICY.md",
                "rules/AI-COLLABORATION-STANDARDS.md",
            ]
        ),
        encoding="utf-8",
    )

    # lock files + validator script
    report_a = ws / "report_a.md"
    report_b = ws / "report_b.md"
    _write_lock_report(report_a)
    _write_lock_report(report_b)
    (ws / "scripts" / "validate_locks.py").write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import sys",
                "print('[OK] lock validation passed')",
                "sys.exit(0)",
            ]
        ),
        encoding="utf-8",
    )
    return ws


def test_validate_governance_passes_with_locks(tmp_path):
    ws = _prepare_workspace(tmp_path)

    result = _run(
        "--workspace",
        str(ws),
        "--with-locks",
        "--lock-files",
        "report_a.md",
        "report_b.md",
    )
    assert result.returncode == 0, result.stderr
    assert "[OK] collaboration governance validation passed" in result.stdout


def test_validate_governance_fails_on_missing_required_file(tmp_path):
    ws = _prepare_workspace(tmp_path)
    (ws / "collaboration" / "PROTOCOL.md").unlink()

    result = _run("--workspace", str(ws))
    assert result.returncode == 1
    assert "missing required governance file: collaboration/PROTOCOL.md" in result.stdout


def test_validate_governance_fails_on_missing_agents_reference(tmp_path):
    ws = _prepare_workspace(tmp_path)
    (ws / "AGENTS.md").write_text("collaboration/COLLABORATION_GUIDELINES.md\n", encoding="utf-8")

    result = _run("--workspace", str(ws))
    assert result.returncode == 1
    assert "missing required collaboration reference" in result.stdout
