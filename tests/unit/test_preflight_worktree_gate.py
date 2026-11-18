"""preflight 第六项「工作树分支冲突」：G11 从 concurrent guard 接进开工检查。

正反两侧都要证明：
- 正向：造出冲突 → 该项 FAIL 且总结论 FAIL；detail 点名分支与工作树数量；
- 反向：单工作树 / 不同分支 / 非 git 目录 / git 不可用 → 不得误判违规。

最后一条（`test_collision_does_not_disturb_other_checks`）是本组最要紧的：
它证明新项只影响自己，没有把既有五项挤歪——这正是上一轮把这次改动作独立的理由。
"""

import json
import subprocess
from pathlib import Path

from ai_collab import concurrent_guard, governance
from ai_collab.governance import preflight

CHECK_NAME = "工作树分支冲突"


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _prepare_workspace(tmp_path: Path) -> Path:
    """造一个「五项都已装备」的工作区，让新项成为唯一变量。"""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "gov@example.com")
    _git(repo, "config", "user.name", "gov")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    boundary = _git(repo, "rev-parse", "HEAD")
    (repo / "logs").mkdir(exist_ok=True)
    (repo / "logs" / "collaboration_state.json").write_text(
        json.dumps({"last_updated": "2026-11-15T00:00:00", "tasks": {}, "patches": {}}),
        encoding="utf-8",
    )
    (repo / "collaboration" / "governance").mkdir(parents=True, exist_ok=True)
    (repo / "collaboration" / "governance" / "governance-ledger.jsonl").write_text(
        json.dumps(
            {
                "kind": "enforcement",
                "commit_sha": boundary,
                "declared_at": "2026-11-15T00:00:00",
                "declared_by": "test",
                "reason": "测试用生效边界：此前的合并提交不参与覆盖率判定",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    for rel in governance.REQUIRED_READS:
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# {rel}\n", encoding="utf-8")
    governance.ack_required_reads(repo, session_id="preflight-g11")

    (repo / ".vscode").mkdir(exist_ok=True)
    (repo / ".vscode" / "ai-collab.json").write_text(
        json.dumps(
            {
                "concurrentGuard": {
                    "expectedBranch": "main",
                    "baselineCommit": boundary,
                    "watchPaths": ["README.md"],
                }
            }
        ),
        encoding="utf-8",
    )
    (repo / "logs" / "agent_ack_bridge_state.json").write_text(
        json.dumps({"version": "1.0.0", "items": {"T-1": {"task_id": "T-1", "source": "cli-ack"}}}),
        encoding="utf-8",
    )
    return repo


def _checks(report: dict) -> dict[str, dict]:
    return {item["name"]: item for item in report["checks"]}


def _make_collision(repo: Path, branch: str = "feat1") -> Path:
    """复刻事故形态：worktree 先签出 feat1，主工作区再用 -B 抢同一分支。"""
    wt = repo.parent / "wt-feat"
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "-q", "-b", branch, str(wt)],
        capture_output=True,
        text=True,
        check=True,
    )
    _git(repo, "symbolic-ref", "HEAD", f"refs/heads/{branch}")
    return wt


class TestCheckWiring:
    def test_preflight_reports_six_checks_ending_with_worktree_collision(self, tmp_path):
        repo = _prepare_workspace(tmp_path)

        report = preflight(repo)

        assert len(report["checks"]) == 6
        assert report["checks"][-1]["name"] == CHECK_NAME

    def test_existing_five_checks_keep_their_order(self, tmp_path):
        """既有五项的顺序是报告文案的既有契约，新项只能追加、不能插队。"""
        repo = _prepare_workspace(tmp_path)

        names = [item["name"] for item in preflight(repo)["checks"]]

        assert names[:5] == [
            "必读清单声明",
            "状态机时效",
            "门禁输入完整性",
            "HEAD 治理登记",
            "显式 ACK 证据",
        ]


class TestCollisionBlocks:
    def test_collision_fails_the_check_and_overall(self, tmp_path):
        repo = _prepare_workspace(tmp_path)
        _make_collision(repo)

        report = preflight(repo)
        item = _checks(report)[CHECK_NAME]

        assert item["pass"] is False
        assert report["pass"] is False

    def test_detail_names_branch_and_worktree_count(self, tmp_path):
        repo = _prepare_workspace(tmp_path)
        _make_collision(repo, branch="feat-x")

        detail = _checks(preflight(repo))[CHECK_NAME]["detail"]

        assert "feat-x" in detail
        assert "2 个工作树" in detail
        assert "1 个分支冲突" in detail
        assert "§14.6" in detail

    def test_collision_does_not_disturb_other_checks(self, tmp_path):
        """只让第六项变红：前五项结论必须与无冲突时逐项一致。"""
        repo = _prepare_workspace(tmp_path)
        before = _checks(preflight(repo))
        assert before[CHECK_NAME]["pass"] is True
        assert all(item["pass"] for item in before.values()), "夹具本身必须五项全绿"

        _make_collision(repo)
        after = _checks(preflight(repo))

        for name, item in before.items():
            if name == CHECK_NAME:
                continue
            assert after[name]["pass"] is item["pass"], f"{name} 的结论被新项挤歪了"


class TestNoFalsePositive:
    def test_clean_repo_passes_with_worktree_count(self, tmp_path):
        repo = _prepare_workspace(tmp_path)

        item = _checks(preflight(repo))[CHECK_NAME]

        assert item["pass"] is True
        assert "无重复分支" in item["detail"]
        assert "1 个工作树" in item["detail"]

    def test_detached_worktree_is_not_a_collision(self, tmp_path):
        repo = _prepare_workspace(tmp_path)
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(repo.parent / "wt-det")],
            capture_output=True,
            text=True,
            check=True,
        )

        item = _checks(preflight(repo))[CHECK_NAME]

        assert item["pass"] is True
        assert "2 个工作树" in item["detail"]

    def test_non_git_workspace_is_unavailable_not_violation(self, tmp_path):
        """非 git 目录：查不到不等于有冲突，不能判违规，但 detail 必须披露。"""
        plain = tmp_path / "plain"
        plain.mkdir()

        item = _checks(preflight(plain))[CHECK_NAME]

        assert item["pass"] is True
        assert "无法判定" in item["detail"]
        assert "未据此判违规" in item["detail"]

    def test_git_missing_is_unavailable_and_does_not_raise(self, tmp_path, monkeypatch):
        """git 不在 PATH 时不能让「开工检查」自己崩掉。"""

        def _boom(*args, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(concurrent_guard, "_run_git", _boom)

        signal = concurrent_guard.detect_worktree_branch_collisions(tmp_path)

        assert signal["collisions"] == []
        assert "git 不可用" in signal["error"]
