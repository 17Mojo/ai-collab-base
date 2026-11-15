"""G11 worktree 分支冲突守卫：同一分支被多个工作树签出。

正反两侧都要证明：
- 正向：造出冲突 → 必须判违规（默认 high，可降级为 warning）；
- 反向：单工作树 / 不同分支 / detached 工作树 → 不得误报。

冲突的构造方式刻意复刻真实事故：先 `worktree add -b` 让某工作树签出 feat1，
再在主仓用 `checkout -B feat1` 重置同一分支。这正是现场那次 `-B` 的形态。
"""

import subprocess
from pathlib import Path

from ai_collab.concurrent_guard import (
    assess_concurrent_risk,
    detect_worktree_branch_collisions,
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
    (path / "README.md").write_text("base\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "init")


def _add_worktree(repo: Path, target: Path, branch: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "-q", "-b", branch, str(target)],
        capture_output=True,
        text=True,
        check=True,
    )


class TestDetectCollisions:
    def test_single_worktree_no_collision(self, tmp_path):
        repo = tmp_path / "repo"
        _init_repo(repo)

        signal = detect_worktree_branch_collisions(repo)

        assert signal["collisions"] == []
        assert signal["worktree_count"] == 1
        assert signal["severity"] == "none"

    def test_distinct_branches_no_collision(self, tmp_path):
        repo = tmp_path / "repo"
        _init_repo(repo)
        _add_worktree(repo, tmp_path / "wt-feat", "feat1")

        signal = detect_worktree_branch_collisions(repo)

        assert signal["collisions"] == []
        assert signal["worktree_count"] == 2
        assert signal["severity"] == "none"

    def test_detached_worktree_not_counted_as_collision(self, tmp_path):
        """detached 工作树没有 branch 行，不该被当成冲突（也不该掩盖真冲突）。"""
        repo = tmp_path / "repo"
        _init_repo(repo)
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(tmp_path / "wt-det")],
            capture_output=True,
            text=True,
            check=True,
        )

        signal = detect_worktree_branch_collisions(repo)

        assert signal["collisions"] == []
        assert signal["worktree_count"] == 2

    def test_detects_collision_made_by_force_reset(self, tmp_path):
        """复刻事故：worktree 签出 feat1 后，主仓用 -B 抢走同一分支。"""
        repo = tmp_path / "repo"
        _init_repo(repo)
        wt = tmp_path / "wt-feat"
        _add_worktree(repo, wt, "feat1")
        _git(repo, "checkout", "-q", "-B", "feat1")

        signal = detect_worktree_branch_collisions(repo)

        assert signal["severity"] == "high"
        assert len(signal["collisions"]) == 1
        collision = signal["collisions"][0]
        assert collision["branch"] == "feat1"
        assert len(collision["paths"]) == 2
        assert str(repo) in collision["paths"]
        assert str(wt) in collision["paths"]


class TestSeverityWiring:
    def test_collision_blocks_by_default(self, tmp_path):
        repo = tmp_path / "repo"
        _init_repo(repo)
        _add_worktree(repo, tmp_path / "wt-feat", "feat1")
        _git(repo, "checkout", "-q", "-B", "feat1")

        assessment = assess_concurrent_risk(repo)

        assert assessment["allowed"] is False
        assert assessment["risk_level"] == "high"
        assert any("worktree collision" in item for item in assessment["violations"])
        assert assessment["signals"]["worktree_collisions"]["severity"] == "high"

    def test_collision_can_be_downgraded_to_warning(self, tmp_path):
        """降级后不阻断，但必须仍然出现在 warnings 里——静默放行等于没装。"""
        repo = tmp_path / "repo"
        _init_repo(repo)
        _add_worktree(repo, tmp_path / "wt-feat", "feat1")
        _git(repo, "checkout", "-q", "-B", "feat1")

        assessment = assess_concurrent_risk(repo, worktree_collision_severity="warning")

        assert assessment["allowed"] is True
        assert any("worktree collision" in item for item in assessment["warnings"])

    def test_clean_repo_stays_low_risk(self, tmp_path):
        repo = tmp_path / "repo"
        _init_repo(repo)

        assessment = assess_concurrent_risk(repo)

        assert assessment["allowed"] is True
        assert assessment["risk_level"] == "low"
        assert assessment["signals"]["worktree_collisions"]["collisions"] == []

    def test_run_persists_collision_signal_and_threshold(self, tmp_path):
        repo = tmp_path / "repo"
        _init_repo(repo)
        _add_worktree(repo, tmp_path / "wt-feat", "feat1")
        _git(repo, "checkout", "-q", "-B", "feat1")

        report = run_concurrent_guard(
            workspace=repo,
            guard_config={"report": "logs/g.json", "history": "logs/g.jsonl"},
        )

        assert report["allowed"] is False
        assert report["signals"]["worktree_collisions"]["collisions"][0]["branch"] == "feat1"
        assert report["thresholds"]["worktreeCollisionSeverity"] == "high"
        assert (repo / "logs/g.json").is_file()

    def test_severity_config_comes_from_guard_config(self, tmp_path):
        repo = tmp_path / "repo"
        _init_repo(repo)
        _add_worktree(repo, tmp_path / "wt-feat", "feat1")
        _git(repo, "checkout", "-q", "-B", "feat1")

        report = run_concurrent_guard(
            workspace=repo,
            guard_config={
                "report": "logs/g.json",
                "history": "logs/g.jsonl",
                "worktreeCollisionSeverity": "warning",
            },
        )

        assert report["allowed"] is True
        assert report["thresholds"]["worktreeCollisionSeverity"] == "warning"
        assert any("worktree collision" in item for item in report["warnings"])
