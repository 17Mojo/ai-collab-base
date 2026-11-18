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
    """替代 `VSCodeIntegration`，避免测试读到仓库真实的 `.vscode/ai-collab.json`。

    .. deprecated::
       N37 修复后 `concurrent guard` 不再经 `VSCodeIntegration` 取配置
       （它只读受跟踪层，正是缺陷本身）。保留这个 stub 只为历史用例可读，
       新用例请用 `_use_config` 换接缝，或直接写真实配置文件。
    """

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
    """替换门禁配置解析接缝，避免测试读到仓库真实配置。

    N37 之后 `concurrent guard` 走 `cli._resolve_guard_config`（与 preflight 同一实现），
    所以这里替换那个函数。**不要再改回 stub `VSCodeIntegration`**——一个只读受跟踪层的
    假对象正是 N37 那个缺陷的形态，stub 它等于把缺陷写进测试里。
    真实两层合并的行为由 `TestN37ConfigLayer` 用真配置文件覆盖。
    """
    guard = dict(config.get("concurrentGuard") or {}) if isinstance(config, dict) else {}
    monkeypatch.setattr(cli, "_resolve_guard_config", lambda workspace: (guard, {}))


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

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="main", session_started_at=datetime.now().isoformat()))

        assert rc == 0
        report = json.loads((ws / "logs/workspace_forensics/concurrent_guard_latest.json").read_text(encoding="utf-8"))
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
        report = json.loads((ws / "logs/workspace_forensics/concurrent_guard_latest.json").read_text(encoding="utf-8"))
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


class TestWorktreeCollision:
    """G11 在 CLI 层的可观测性：退出码、报告、以及分支冲突的提示语。"""

    def test_collision_blocks_with_exit_code_2(self, tmp_path, monkeypatch):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        wt = tmp_path / "wt-feat"
        subprocess.run(
            ["git", "-C", str(ws), "worktree", "add", "-q", "-b", "feat1", str(wt)],
            capture_output=True,
            text=True,
            check=True,
        )
        _git(ws, "symbolic-ref", "HEAD", "refs/heads/feat1")
        _use_config(monkeypatch, {})

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="feat1"))

        assert rc == 2
        report = json.loads((ws / "logs/workspace_forensics/concurrent_guard_latest.json").read_text(encoding="utf-8"))
        assert report["signals"]["worktree_collisions"]["collisions"][0]["branch"] == "feat1"
        assert any("worktree collision" in item for item in report["violations"])

    def test_collision_hint_explains_how_to_fix(self, tmp_path, monkeypatch, capsys):
        """阻断时必须给出修法：覆盖不是解，冲突状态本身会让 status 失真。"""
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        wt = tmp_path / "wt-feat"
        subprocess.run(
            ["git", "-C", str(ws), "worktree", "add", "-q", "-b", "feat1", str(wt)],
            capture_output=True,
            text=True,
            check=True,
        )
        _git(ws, "symbolic-ref", "HEAD", "refs/heads/feat1")
        _use_config(monkeypatch, {})

        cli.cmd_concurrent_guard(_args(ws, expected_branch="feat1"))

        out = capsys.readouterr().out
        assert "collisions: feat1 x2" in out
        assert "worktree 冲突不能靠覆盖解决" in out

    def test_no_collision_line_shows_none(self, tmp_path, monkeypatch, capsys):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        _use_config(monkeypatch, {})

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="main"))

        assert rc == 0
        assert "collisions: none" in capsys.readouterr().out


def _write_config(ws: Path, tracked: dict | None = None, local: dict | None = None) -> None:
    """把配置真的写到磁盘上（`.vscode/ai-collab.json` / `.local.json`）。"""
    cfg_dir = ws / ".vscode"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    if tracked is not None:
        (cfg_dir / "ai-collab.json").write_text(json.dumps(tracked, ensure_ascii=False), encoding="utf-8")
    if local is not None:
        (cfg_dir / "ai-collab.local.json").write_text(json.dumps(local, ensure_ascii=False), encoding="utf-8")


class TestN37ConfigLayer:
    """N37 回归：`concurrent guard` 必须读会话级覆盖层，与 preflight 同口径。

    缺陷原形：守卫只读受跟踪 `.vscode/ai-collab.json`，而 preflight 读两层合并。
    照源码注释把基线写进 gitignore 的 `.local.json` 后，preflight 六项全 PASS，
    `concurrent guard` 却输出 `baseline: none (skipped)` + 退出码 0 ——
    G2 在最该拦它的命令里静默失效，而绿得和「判过了」一模一样。

    这一组**不 stub 任何东西**：写真实配置文件，走真实的 `_resolve_guard_config`。
    """

    def test_local_layer_baseline_arms_g2(self, tmp_path, monkeypatch, capsys):
        """基线只写在 local 层时，G2 必须真的跑起来，而不是 skipped。"""
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        head = _commit(ws)
        _write_config(
            ws,
            tracked={
                "concurrentGuard": {
                    "expectedBranch": None,
                    "baselineCommit": None,
                    "watchPaths": [],
                    "requireBaselineCommit": True,
                }
            },
            local={"concurrentGuard": {"expectedBranch": "main", "baselineCommit": head, "watchPaths": ["README.md"]}},
        )
        # 注意：这里不 monkeypatch，故意让实现自己去读两层

        rc = cli.cmd_concurrent_guard(_args(ws))

        out = capsys.readouterr().out
        assert rc == 0
        assert "baseline: none (skipped)" not in out, "N37 复现：基线写在 local 层却被跳过 —— 守卫没读覆盖层。\n" + out
        assert head in out, "基线没被真正采用：\n" + out
        assert "watched path(s) changed" in out

    def test_provenance_names_the_local_layer(self, tmp_path, monkeypatch, capsys):
        """输出必须写明每个输入来自哪一层，否则「绿」和「没判」外观一样。"""
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        head = _commit(ws)
        _write_config(
            ws,
            tracked={"concurrentGuard": {"expectedBranch": "main"}},
            local={"concurrentGuard": {"baselineCommit": head, "watchPaths": ["README.md"]}},
        )

        cli.cmd_concurrent_guard(_args(ws))

        out = capsys.readouterr().out
        assert "配置来源:" in out
        assert "expectedBranch←.vscode/ai-collab.json" in out
        assert "baselineCommit←.vscode/ai-collab.local.json" in out

    def test_cli_argument_wins_and_provenance_says_so(self, tmp_path, monkeypatch, capsys):
        """CLI 参数优先于两层配置；来源行不得把人误导成「来自配置文件」。"""
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        _write_config(ws, tracked={"concurrentGuard": {"expectedBranch": "other-branch"}})

        rc = cli.cmd_concurrent_guard(_args(ws, expected_branch="main"))

        out = capsys.readouterr().out
        assert rc == 0
        assert "expectedBranch←CLI 参数" in out

    def test_guard_and_preflight_see_the_same_inputs(self, tmp_path, monkeypatch):
        """两条路径对「是否武装」必须给出同一个答案（N37 的核心断言）。"""
        from ai_collab import governance as gov

        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        head = _commit(ws)
        _write_config(
            ws,
            tracked={"concurrentGuard": {"expectedBranch": None, "baselineCommit": None}},
            local={"concurrentGuard": {"expectedBranch": "main", "baselineCommit": head, "watchPaths": ["README.md"]}},
        )

        preflight_view = gov.guard_input_report(ws)
        cli_guard, _sources = cli._resolve_guard_config(str(ws))

        assert preflight_view["complete"] is True
        assert cli_guard.get("baselineCommit") == head, (
            "preflight 说输入齐全，守卫却拿不到基线 —— 两条读取路径口径仍不一致（N37）"
        )
        assert cli_guard.get("expectedBranch") == "main"
        assert cli_guard.get("watchPaths") == ["README.md"]

    def test_unarmed_guard_says_so_instead_of_looking_green(self, tmp_path, monkeypatch, capsys):
        """完全没装备时必须明说「未提供」，不能让读者以为判定跑过了。"""
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        # 不写任何配置文件

        rc = cli.cmd_concurrent_guard(_args(ws))

        out = capsys.readouterr().out
        assert rc == 0
        assert "配置来源:" in out
        assert "expectedBranch←未提供" in out
        assert "baseline: none (skipped)" in out
