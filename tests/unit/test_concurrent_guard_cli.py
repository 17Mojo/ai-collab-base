"""Unit tests for the `concurrent guard` CLI gate (OpenSpec Phase 2.2).

守护用例覆盖四件事：
1. argparse 接线（`concurrent guard` 二级子命令 + 可重复 `--watch-path`）；
2. 退出码契约（放行 0 / 阻断 2）；
3. 门禁分级（foreign 是 mtime 启发式 → 软警告不阻断；drift 是 git 真证 → 阻断）；
4. 报告落盘（latest.json + history.jsonl 落在被治理工作区内）。
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from ai_collab.cli import _cli_main as cli


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    _git(path, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    _git(path, "config", "commit.gpgsign", "false")


def _commit(path: Path, msg: str = "init") -> str:
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", msg)
    return _git(path, "rev-parse", "HEAD")


def _set_old_mtime(path: Path, hours_ago: float = 1.0) -> None:
    old = time.time() - hours_ago * 3600
    os.utime(path, (old, old))


class _StubVSCode:
    """替代 `VSCodeIntegration`，避免测试读到仓库真实的 `.vscode/ai-collab.json`。"""

    def __init__(self, config: dict) -> None:
        self._config = config

    def get_project_config(self) -> dict:
        return dict(self._config)


def _args(workspace: Path, **overrides) -> argparse.Namespace:
    defaults = {
        "concurrent_action": "guard",
        "workspace": str(workspace),
        "expected_branch": None,
        "baseline_commit": None,
        "watch_path": [],
        "session_started_at": None,
        "force_workspace": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _use_config(monkeypatch, config: dict) -> None:
    monkeypatch.setattr(cli, "VSCodeIntegration", _StubVSCode(config))


class TestArgumentParsing:
    def test_watch_path_repeatable_and_branch_parsed(self, monkeypatch):
        captured: dict = {}

        def fake(args):
            captured["args"] = args
            return 0

        monkeypatch.setattr(cli, "cmd_concurrent_guard", fake)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "ai-collab",
                "concurrent",
                "guard",
                "--expected-branch",
                "main",
                "--watch-path",
                "a",
                "--watch-path",
                "b",
            ],
        )

        rc = cli.main()

        assert rc == 0
        args = captured["args"]
        assert args.command == "concurrent"
        assert args.concurrent_action == "guard"
        assert args.expected_branch == "main"
        assert args.watch_path == ["a", "b"]

    def test_missing_action_prints_hint_without_crashing(self, monkeypatch, capsys):
        _use_config(monkeypatch, {})
        monkeypatch.setattr(sys, "argv", ["ai-collab", "concurrent"])

        rc = cli.main()

        assert rc == 0
        assert "concurrent guard" in capsys.readouterr().out


class TestExitCodes:
    def test_branch_drift_blocks_with_exit_code_2(self, tmp_path, monkeypatch):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        _git(ws, "checkout", "-q", "-b", "feature")
        _use_config(monkeypatch, {})

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="main"))

        assert rc == 2

    def test_clean_repo_exits_zero(self, tmp_path, monkeypatch):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        _use_config(monkeypatch, {})

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="main"))

        assert rc == 0

    def test_force_workspace_overrides_drift(self, tmp_path, monkeypatch):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        _git(ws, "checkout", "-q", "-b", "feature")
        _use_config(monkeypatch, {})

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="main", force_workspace=True))

        assert rc == 0


class TestSeverityLayering:
    def test_foreign_changes_are_warning_not_blocking(self, tmp_path, monkeypatch):
        """G3（mtime 启发式）只作软警告：退出码仍是 0，报告里 warnings 非空。"""
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        foreign = ws / "foreign.txt"
        foreign.write_text("not mine")
        _set_old_mtime(foreign)
        _use_config(monkeypatch, {})

        rc = cli.cmd_concurrent_guard(
            _args(ws, expected_branch="main", session_started_at=datetime.now().isoformat())
        )

        assert rc == 0
        report = json.loads(
            (ws / "logs/workspace_forensics/concurrent_guard_latest.json").read_text(encoding="utf-8")
        )
        assert report["violations"] == []
        assert report["warnings"]
        assert report["allowed"] is True

    def test_drift_is_blocking_violation(self, tmp_path, monkeypatch):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        _git(ws, "checkout", "-q", "-b", "feature")
        _use_config(monkeypatch, {})

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="main"))

        assert rc == 2
        report = json.loads(
            (ws / "logs/workspace_forensics/concurrent_guard_latest.json").read_text(encoding="utf-8")
        )
        assert report["violations"]
        assert report["allowed"] is False
        assert report["risk_level"] == "high"

    def test_require_baseline_without_baseline_is_warning_only(self, tmp_path, monkeypatch):
        """`requireBaselineCommit` 只作软警告：不得升级为阻断。"""
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        _use_config(monkeypatch, {"concurrentGuard": {"requireBaselineCommit": True}})

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="main"))

        assert rc == 0


class TestConfigWiring:
    def test_config_supplies_expected_branch_when_cli_absent(self, tmp_path, monkeypatch):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        _use_config(monkeypatch, {"concurrentGuard": {"expectedBranch": "other-branch"}})

        rc = cli.cmd_concurrent_guard(_args(ws))

        assert rc == 2

    def test_cli_argument_overrides_config(self, tmp_path, monkeypatch):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        _use_config(monkeypatch, {"concurrentGuard": {"expectedBranch": "other-branch"}})

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="main"))

        assert rc == 0

    def test_config_can_disable_guard(self, tmp_path, monkeypatch):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        _git(ws, "checkout", "-q", "-b", "feature")
        _use_config(monkeypatch, {"concurrentGuard": {"enabled": False}})

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="main"))

        assert rc == 0


class TestReportPersistence:
    def test_report_and_history_written_into_workspace(self, tmp_path, monkeypatch):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        _use_config(monkeypatch, {})

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="main"))

        assert rc == 0
        report_path = ws / "logs/workspace_forensics/concurrent_guard_latest.json"
        history_path = ws / "logs/workspace_forensics/concurrent_guard_history.jsonl"
        assert report_path.exists()
        assert history_path.exists()
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        assert payload["allowed"] is True
        assert "git_context" in payload
        assert "signals" in payload
        lines = [line for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0])["allowed"] is True

    def test_report_path_from_config_is_honoured(self, tmp_path, monkeypatch):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        _use_config(
            monkeypatch,
            {
                "concurrentGuard": {
                    "report": "logs/custom/report.json",
                    "history": "logs/custom/history.jsonl",
                }
            },
        )

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="main"))

        assert rc == 0
        assert (ws / "logs/custom/report.json").exists()
        assert (ws / "logs/custom/history.jsonl").exists()
