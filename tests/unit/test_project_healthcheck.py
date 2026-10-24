"""Unit tests for scripts/project_healthcheck.py."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "project_healthcheck.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("project_healthcheck", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _minimal_data(git, health):
    return {
        "generated_at": "2026-10-24T00:00:00",
        "date_stamp": "2026-10-24",
        "tests": {
            "passed": 100, "failed": 0, "skipped": 0,
            "coverage_pct": "88", "miss_lines": "10", "last_line": "100 passed",
        },
        "git": git,
        "code_health": {
            "py_files": 10, "py_lines": 1000,
            "test_files": 5, "test_lines": 500, "test_to_code_ratio": 0.5,
        },
        "coverage_breakdown": {"low_coverage_modules": []},
        "static_analysis": {"ruff_errors": 0, "mypy_errors": 0},
        "dependencies": {"pip_audit": "skipped"},
        "health_rules": health,
    }


def _git(**over):
    base = {
        "recent_commits": [],
        "untracked_count": 0,
        "modified_count": 0,
        "untracked_files": [],
        "remotes": "",
        "ahead_of_origin": [],
        "has_origin_main": True,
    }
    base.update(over)
    return base


def _health(**over):
    base = {
        "claude_md_has_rules": True,
        "claude_md_rules_count": 3,
        "gitignore_present": True,
    }
    base.update(over)
    return base


def test_check_git_no_origin_main_reports_unknown(monkeypatch):
    module = _load_module()

    def fake_run(cmd, cwd=None, timeout=60):
        if "rev-parse --verify origin/main" in cmd:
            return (128, "", "fatal: unknown revision")
        if "origin/main..HEAD" in cmd:
            return (128, "", "fatal: unknown revision")
        return (0, "", "")

    monkeypatch.setattr(module, "run", fake_run)
    g = module.check_git()
    assert g["has_origin_main"] is False
    assert g["ahead_of_origin"] == []

    md = module.render_markdown(_minimal_data(g, _health()))
    assert "未知" in md
    assert "与 origin/main 同步" not in md


def test_check_git_with_origin_main_ahead(monkeypatch):
    module = _load_module()

    def fake_run(cmd, cwd=None, timeout=60):
        if "rev-parse --verify origin/main" in cmd:
            return (0, "abc1234", "")
        if "origin/main..HEAD" in cmd:
            return (0, "aaaa111 first\nbbbb222 second", "")
        if "log --oneline -10" in cmd:
            return (0, "aaaa111 first commit", "")
        return (0, "", "")

    monkeypatch.setattr(module, "run", fake_run)
    g = module.check_git()
    assert g["has_origin_main"] is True
    assert len(g["ahead_of_origin"]) == 2

    md = module.render_markdown(_minimal_data(g, _health()))
    assert "领先 origin/main 2 个 commit" in md


def test_check_health_rules_count_matches_grep():
    module = _load_module()
    h = module.check_health_rules()

    rc, out, _ = module.run("grep -c '^### 经验 [0-9]' CLAUDE.md 2>/dev/null || echo 0")
    expected = int(out.strip()) if out.strip().isdigit() else 0

    assert h["claude_md_rules_count"] == expected
    assert h["claude_md_has_rules"] == (expected >= 3)


def test_check_coverage_breakdown_parses_4col(tmp_path, monkeypatch):
    module = _load_module()
    fake = tmp_path / "coverage.txt"
    fake.write_text(
        "Name          Stmts   Miss  Cover\n"
        "ai_collab/lowmod.py   100     40    60%\n"
        "ai_collab/highmod.py  200     10    95%\n"
        "TOTAL                 300     50    83%\n",
        encoding="utf-8",
    )

    def fake_run(cmd, cwd=None, timeout=60):
        new_cmd = cmd.replace("coverage report", f"cat {fake}")
        r = subprocess.run(new_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()

    monkeypatch.setattr(module, "run", fake_run)
    result = module.check_coverage_breakdown()
    low = dict(result["low_coverage_modules"])
    assert low.get("ai_collab/lowmod.py") == 60
    assert "ai_collab/highmod.py" not in low
