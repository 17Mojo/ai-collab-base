"""并发守护的跨工作区复用性（OpenSpec Phase 4.3 / 设计文档 §6.3、§6.4）。

设计文档 §6.3 要求「治理层与被治理仓库解耦，可复用于任何共享工作区」。
本仓自己永远是唯一测试对象——**测不出**「实现里写死了本仓路径」这类缺陷。
所以必须在 `tmp_path` 构造一个与本仓无关的 mini git repo 上真跑一次。

**报告落点的真实规则**（2026-10-24 实测纠正，见
`tests/unit/test_concurrent_guard_reuse.py::test_default_report_path_stays_inside_guarded_workspace`）：
`run_concurrent_guard` 的落点是 `workspace / report_rel`
（`ai_collab/concurrent_guard.py`）——**相对路径**落在**被治理工作区**内部，
**绝对路径**按调用方给的位置落（pathlib 的 `Path / 绝对路径` 语义）。

所以「不传 `guard_config` 就会写进本仓」是**错的**：默认落在被治理工作区
自己的 `logs/workspace_forensics/` 下。真正会污染本仓的写法是**显式**传入
本仓的绝对路径。显式传 tmp 内部路径仍是推荐写法——它让落点不依赖默认值。
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ai_collab.concurrent_guard import run_concurrent_guard

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# 目录名刻意不含 `ai_collab` 之类字样，避免「实现认仓库名」也能蒙对
FOREIGN_REPO_NAME = "shared-workspace-sample"


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _init_foreign_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q")
    _git(path, "symbolic-ref", "HEAD", "refs/heads/main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    _git(path, "config", "commit.gpgsign", "false")
    (path / "README.md").write_text("foreign repo\n", encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "init")


def _assert_self_consistent(report: dict) -> None:
    """结论必须自洽：allowed ⇔ 无 violation；risk_level 与违规/警告数量一致。"""
    violations = report.get("violations") or []
    warnings = report.get("warnings") or []

    assert isinstance(report.get("allowed"), bool)
    assert isinstance(report.get("risk_level"), str)
    assert report["allowed"] is (not violations)
    expected_level = "high" if violations else ("medium" if warnings else "low")
    assert report["risk_level"] == expected_level


class TestCrossWorkspaceReuse:
    """跨工作区复用性：同一套守卫在无关工作区与本仓上都能跑，报告各归各位。"""

    def test_guard_runs_on_foreign_workspace(self, tmp_path):
        """在无关的 tmp repo 上跑：报告落在该 repo 内，且不写本仓。"""
        foreign = tmp_path / FOREIGN_REPO_NAME
        _init_foreign_repo(foreign)

        repo_report = PROJECT_ROOT / "logs/workspace_forensics/concurrent_guard_latest.json"
        before = repo_report.stat().st_mtime if repo_report.exists() else None

        report = run_concurrent_guard(
            workspace=foreign,
            expected_branch="main",
            guard_config={
                "report": str(foreign / "logs/forensics/latest.json"),
                "history": str(foreign / "logs/forensics/history.jsonl"),
            },
        )

        _assert_self_consistent(report)

        # 报告写进了被治理工作区内部，不是本仓
        report_file = Path(report["report_file"])
        assert report_file.exists()
        assert str(report_file).startswith(str(foreign))
        assert PROJECT_ROOT not in report_file.parents

        # 报告内容里的 workspace 也指向被治理工作区
        payload = json.loads(report_file.read_text(encoding="utf-8"))
        assert payload["workspace"] == str(foreign)
        assert payload["git_context"]["branch"] == "main"

        # 本仓的工作区没有被这次调用写入
        after = repo_report.stat().st_mtime if repo_report.exists() else None
        assert after == before, "在外部工作区跑守护不得改动本仓的 logs/"

    def test_guard_detects_drift_on_foreign_workspace(self, tmp_path):
        """跨工作区同样能识别漂移（治理能力与本仓解耦）。"""
        foreign = tmp_path / FOREIGN_REPO_NAME
        _init_foreign_repo(foreign)
        _git(foreign, "checkout", "-q", "-b", "other-branch")

        report = run_concurrent_guard(
            workspace=foreign,
            expected_branch="main",
            guard_config={
                "report": str(foreign / "logs/forensics/latest.json"),
                "history": str(foreign / "logs/forensics/history.jsonl"),
            },
        )

        _assert_self_consistent(report)
        assert report["allowed"] is False
        assert report["risk_level"] == "high"
        assert any("branch drift" in item for item in report["violations"])

    def test_default_report_path_stays_inside_guarded_workspace(self, tmp_path):
        """**默认落点**也必须在被治理工作区内部（不传 guard_config 的情形）。

        这条用例钉的是「治理层与被治理仓库解耦」的**默认路径**面：
        `run_concurrent_guard` 的落点是 `workspace / report_rel`，相对路径
        落在被治理工作区自己的目录下，**不会**落到本仓。

        2026-10-24 实测纠正：此前本文件的 docstring 与工单 R4 写的是
        「不传 guard_config 就会写进本仓」——**与实现不符**。本用例把
        真实行为钉成契约，避免同一句错话再次写进文档。
        """
        foreign = tmp_path / FOREIGN_REPO_NAME
        _init_foreign_repo(foreign)

        repo_report = PROJECT_ROOT / "logs/workspace_forensics/concurrent_guard_latest.json"
        before = repo_report.stat().st_mtime if repo_report.exists() else None

        # 故意**不传** guard_config，走默认落点
        report = run_concurrent_guard(workspace=foreign, expected_branch="main")

        _assert_self_consistent(report)

        report_file = Path(report["report_file"])
        assert report_file.exists()
        # 默认落点 = 被治理工作区内部的 logs/workspace_forensics/
        assert report_file.parent == foreign / "logs" / "workspace_forensics"
        assert str(report_file).startswith(str(foreign))
        assert PROJECT_ROOT not in report_file.parents

        # 本仓的 logs/ 未被写入
        after = repo_report.stat().st_mtime if repo_report.exists() else None
        assert after == before, "默认落点不得改动本仓的 logs/"

    def test_same_guard_also_works_on_this_repository(self):
        """同一套守卫在本仓上跑：报告写在本仓的 logs/workspace_forensics/ 下。

        这是「跨仓库通用」的正向证据——与上面两条（外部工作区）合起来说明
        治理层没有与被治理仓库耦合。
        """
        report = run_concurrent_guard(workspace=PROJECT_ROOT)

        _assert_self_consistent(report)
        report_file = Path(report["report_file"])
        assert report_file.exists()
        assert report_file.parent == PROJECT_ROOT / "logs" / "workspace_forensics"
