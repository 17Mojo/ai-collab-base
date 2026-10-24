import json
import os
import subprocess
import time
from pathlib import Path

from ai_collab.concurrent_guard import (
    assess_concurrent_risk,
    detect_baseline_staleness,
    detect_branch_drift,
    detect_foreign_changes,
    inspect_git_context,
    run_concurrent_guard,
)


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


class TestInspectGitContext:
    def test_collects_branch_head_clean(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        ctx = inspect_git_context(ws)
        assert ctx["ok"] is True
        assert ctx["branch"] == "main"
        assert len(ctx["head_commit"]) > 0
        assert ctx["dirty_total"] == 0

    def test_detached_head_branch_none(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        commit = _commit(ws)
        _git(ws, "checkout", "-q", commit)
        ctx = inspect_git_context(ws)
        assert ctx["branch"] is None

    def test_dirty_paths_untracked(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        (ws / "new_file.py").write_text("x")
        ctx = inspect_git_context(ws)
        assert ctx["dirty_total"] == 1
        assert "new_file.py" in ctx["dirty_paths"]

    def test_dirty_paths_normalize_renamed_entry(self, tmp_path):
        """重命名条目必须只记**新路径**。

        `git status --porcelain` 对重命名给的是 `R  old.py -> new.py`，
        原样塞进脏文件列表会让下游拿到一个根本不存在的路径
        （`old.py -> new.py`），按它去 stat 必然落空。

        用 `git mv` 让 rename 进入索引 —— 只有**已暂存**的重命名才会被
        git 折叠成 `->` 形式（工作区里裸 `mv` 只报 `D` + `??` 两条）。
        """
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "old.py").write_text("x")
        _commit(ws)
        _git(ws, "mv", "old.py", "new.py")

        ctx = inspect_git_context(ws)

        assert ctx["dirty_total"] == 1
        assert ctx["dirty_paths"] == ["new.py"]
        assert not any("->" in path for path in ctx["dirty_paths"])


class TestBranchDrift:
    def test_drifted(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        signal = detect_branch_drift(ws, "other-branch")
        assert signal["drifted"] is True
        assert signal["actual"] == "main"
        assert signal["severity"] == "high"

    def test_not_drifted(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        signal = detect_branch_drift(ws, "main")
        assert signal["drifted"] is False
        assert signal["severity"] == "none"

    def test_expected_none_skips(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        signal = detect_branch_drift(ws, None)
        assert signal["drifted"] is False
        assert signal["expected"] is None


class TestBaselineStaleness:
    def test_stale_when_watch_path_changed(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        watch = ws / "ai_collab" / "pack" / "schema_v2.py"
        watch.parent.mkdir(parents=True)
        watch.write_text("v1\n")
        baseline = _commit(ws)
        watch.write_text("v2\n")
        _commit(ws, "change schema")
        signal = detect_baseline_staleness(ws, baseline, ["ai_collab/pack/schema_v2.py"])
        assert signal["stale"] is True
        assert signal["severity"] == "high"
        assert signal["changed_watch_paths"][0]["commits_since"] == 1

    def test_not_stale_when_no_change(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "ai_collab").mkdir()
        (ws / "ai_collab" / "mod.py").write_text("1\n")
        baseline = _commit(ws)
        (ws / "other.txt").write_text("x")
        _commit(ws, "other change")
        signal = detect_baseline_staleness(ws, baseline, ["ai_collab/mod.py"])
        assert signal["stale"] is False

    def test_invalid_baseline_records_error(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "f.txt").write_text("x")
        _commit(ws)
        signal = detect_baseline_staleness(ws, "deadbeef", ["f.txt"])
        assert signal["stale"] is False
        assert signal["changed_watch_paths"][0]["commits_since"] is None
        assert "error" in signal["changed_watch_paths"][0]


class TestForeignChanges:
    def test_detects_foreign_untracked(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        foreign = ws / "tests" / "test_enhanced.py"
        foreign.parent.mkdir(parents=True)
        foreign.write_text("x")
        _set_old_mtime(foreign, hours_ago=1.0)
        session_at = datetime_now_iso()
        signal = detect_foreign_changes(ws, session_at)
        assert signal["foreign_count"] == 1
        assert signal["severity"] == "high"
        assert signal["foreign_paths"][0]["path"] == "tests/test_enhanced.py"

    def test_no_foreign_when_mtime_recent(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        recent = ws / "new.py"
        recent.write_text("x")
        session_at = datetime_now_iso(hours_ago=1.0)
        signal = detect_foreign_changes(ws, session_at)
        assert signal["foreign_count"] == 0

    def test_tracked_paths_excluded(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        foreign = ws / "mine.py"
        foreign.write_text("x")
        _set_old_mtime(foreign, hours_ago=1.0)
        session_at = datetime_now_iso()
        signal = detect_foreign_changes(ws, session_at, tracked_paths=["mine.py"])
        assert signal["foreign_count"] == 0

    def test_invalid_session_returns_error(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        signal = detect_foreign_changes(ws, "not-a-date")
        assert signal["foreign_count"] == 0
        assert "error" in signal


class TestAssessRisk:
    def test_high_risk_from_drift_and_stale(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        watch = ws / "ai_collab" / "pack" / "schema_v2.py"
        watch.parent.mkdir(parents=True)
        watch.write_text("v1\n")
        baseline = _commit(ws)
        _git(ws, "checkout", "-q", "-b", "refactor/slimming")
        watch.write_text("v2\n")
        _commit(ws, "change")
        result = assess_concurrent_risk(
            ws,
            expected_branch="main",
            baseline_commit=baseline,
            watch_paths=["ai_collab/pack/schema_v2.py"],
        )
        assert result["risk_level"] == "high"
        assert result["allowed"] is False
        assert any("branch drift" in v for v in result["violations"])
        assert any("baseline stale" in v for v in result["violations"])

    def test_low_risk_when_clean(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        baseline = _commit(ws)
        result = assess_concurrent_risk(
            ws,
            expected_branch="main",
            baseline_commit=baseline,
            watch_paths=["README.md"],
        )
        assert result["risk_level"] == "low"
        assert result["allowed"] is True

    def test_foreign_is_warning_not_blocking(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        baseline = _commit(ws)
        foreign = ws / "other.py"
        foreign.write_text("x")
        _set_old_mtime(foreign, hours_ago=1.0)
        session_at = datetime_now_iso()
        result = assess_concurrent_risk(
            ws,
            expected_branch="main",
            baseline_commit=baseline,
            watch_paths=["README.md"],
            session_started_at=session_at,
        )
        assert result["allowed"] is True
        assert result["risk_level"] == "medium"
        assert any("foreign changes" in w for w in result["warnings"])
        assert not any("foreign" in v for v in result["violations"])

    def test_foreign_high_severity_blocks(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        baseline = _commit(ws)
        foreign = ws / "other.py"
        foreign.write_text("x")
        _set_old_mtime(foreign, hours_ago=1.0)
        session_at = datetime_now_iso()
        result = assess_concurrent_risk(
            ws,
            expected_branch="main",
            baseline_commit=baseline,
            watch_paths=["README.md"],
            session_started_at=session_at,
            foreign_change_severity="high",
        )
        assert result["allowed"] is False
        assert result["risk_level"] == "high"

    def test_ahead_warning(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        remote = tmp_path / "remote.git"
        remote.mkdir(parents=True)
        _git(remote, "init", "-q", "--bare")
        _git(ws, "remote", "add", "origin", str(remote))
        _git(ws, "push", "-q", "-u", "origin", "main")
        (ws / "extra.txt").write_text("x")
        _commit(ws, "extra")
        result = assess_concurrent_risk(ws, ahead_warn_threshold=0)
        assert any("ahead of upstream" in w for w in result["warnings"])
        assert result["risk_level"] == "medium"


class TestRegressionSample20260926:
    def test_reproduces_branch_drift_baseline_stale_foreign(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        watch = ws / "ai_collab" / "pack" / "schema_v2.py"
        watch.parent.mkdir(parents=True)
        watch.write_text("# schema v1, 1022 lines\n")
        baseline_commit = _commit(ws, "schema v1")

        _git(ws, "checkout", "-q", "-b", "refactor/slimming-2026-09-20")
        watch.write_text("# schema v2, 962 lines (ReviewWorkflow removed)\n")
        _commit(ws, "remove ReviewWorkflow")

        foreign = ws / "tests" / "unit" / "test_enhanced.py"
        foreign.parent.mkdir(parents=True)
        foreign.write_text("# foreign uncommitted change\n")
        _set_old_mtime(foreign, hours_ago=2.0)

        session_started_at = datetime_now_iso()

        result = assess_concurrent_risk(
            ws,
            expected_branch="main",
            baseline_commit=baseline_commit,
            watch_paths=["ai_collab/pack/schema_v2.py"],
            session_started_at=session_started_at,
        )

        assert result["risk_level"] == "high"
        assert result["allowed"] is False

        branch_signal = result["signals"]["branch_drift"]
        assert branch_signal["drifted"] is True
        assert branch_signal["actual"] == "refactor/slimming-2026-09-20"
        assert branch_signal["expected"] == "main"

        baseline_signal = result["signals"]["baseline_stale"]
        assert baseline_signal["stale"] is True
        assert baseline_signal["changed_watch_paths"][0]["commits_since"] == 1

        foreign_signal = result["signals"]["foreign_changes"]
        assert foreign_signal["foreign_count"] == 1

        assert any("branch drift" in v for v in result["violations"])
        assert any("baseline stale" in v for v in result["violations"])
        assert any("foreign changes" in w for w in result["warnings"])


class TestRunConcurrentGuard:
    def test_persists_report_and_history(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        report = run_concurrent_guard(
            workspace=ws,
            expected_branch="main",
            guard_config={"enabled": True},
        )
        assert report["allowed"] is True
        report_file = Path(report["report_file"])
        history_file = Path(report["history_file"])
        assert report_file.exists()
        assert history_file.exists()
        loaded = json.loads(report_file.read_text(encoding="utf-8"))
        assert loaded["allowed"] is True
        assert loaded["risk_level"] == "low"

    def test_two_runs_append_two_parseable_history_lines(self, tmp_path):
        """连续跑两次 → 历史两行，且**每行都能解析成 JSON**。

        现有守护只断言「一次运行 → 一行存在」，钉不住「第二次运行是否
        真的追加」。若历史改成覆盖写，两行断言会当场变红；若是追加了但
        写坏（半行 JSON / 多个对象挤一行），逐行 `json.loads` 会当场变红。
        """
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)

        first = run_concurrent_guard(
            workspace=ws,
            expected_branch="main",
            guard_config={"enabled": True},
        )
        second = run_concurrent_guard(
            workspace=ws,
            expected_branch="main",
            guard_config={"enabled": True},
        )

        history_file = Path(second["history_file"])
        assert history_file == Path(first["history_file"])
        lines = [line for line in history_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 2, f"历史应为两行，实得 {len(lines)} 行：{lines}"

        parsed = [json.loads(line) for line in lines]
        assert [item["allowed"] for item in parsed] == [True, True]
        # 两次运行各自留下自己的结论对象（不是同一份被写两遍）
        assert all(item.get("generated_at") for item in parsed)

    def test_disabled_allows(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        report = run_concurrent_guard(
            workspace=ws,
            expected_branch="nonexistent",
            guard_config={"enabled": False},
        )
        assert report["allowed"] is True

    def test_force_allows_despite_violation(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        report = run_concurrent_guard(
            workspace=ws,
            expected_branch="nonexistent",
            guard_config={"enabled": True},
            force=True,
        )
        assert report["allowed"] is True
        assert report["forced"] is True

    def test_blocks_on_drift(self, tmp_path):
        ws = tmp_path / "ws"
        _init_repo(ws)
        (ws / "README.md").write_text("hi")
        _commit(ws)
        report = run_concurrent_guard(
            workspace=ws,
            expected_branch="nonexistent",
            guard_config={"enabled": True},
        )
        assert report["allowed"] is False
        assert report["risk_level"] == "high"


def datetime_now_iso(hours_ago: float = 0.0) -> str:
    from datetime import datetime, timedelta

    return (datetime.now() - timedelta(hours=hours_ago)).isoformat()
