import subprocess
from pathlib import Path

from ai_collab.workspace_guard import stage_domain_changes


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "-C", str(path), "init"], check=True, capture_output=True, text=True)


def test_stage_domain_changes_blocks_unsupported_domain(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    report = stage_domain_changes(workspace=workspace, domain="invalid", dry_run=True)
    assert report["ok"] is False
    assert "unsupported domain" in report["error"]


def test_stage_domain_changes_dry_run_counts_source_domain(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _init_repo(workspace)

    (workspace / "ai_collab").mkdir(parents=True, exist_ok=True)
    (workspace / "ai_collab" / "new_logic.py").write_text("print('source')\n", encoding="utf-8")
    (workspace / "docs").mkdir(parents=True, exist_ok=True)
    (workspace / "docs" / "guide.md").write_text("# guide\n", encoding="utf-8")

    report = stage_domain_changes(workspace=workspace, domain="source", dry_run=True)
    assert report["ok"] is True
    assert report["candidate_count"] == 1
    assert report["status_counts"]["untracked"] == 1
    assert "ai_collab/new_logic.py" in report["sample_paths"]


def test_stage_domain_changes_apply_stages_only_target_domain(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _init_repo(workspace)

    (workspace / "ai_collab").mkdir(parents=True, exist_ok=True)
    (workspace / "ai_collab" / "a.py").write_text("print('a')\n", encoding="utf-8")
    (workspace / "docs").mkdir(parents=True, exist_ok=True)
    (workspace / "docs" / "b.md").write_text("# b\n", encoding="utf-8")

    report = stage_domain_changes(workspace=workspace, domain="source", dry_run=False)
    assert report["ok"] is True
    assert report["candidate_count"] == 1

    staged = subprocess.run(
        ["git", "-C", str(workspace), "diff", "--cached", "--name-only"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert "ai_collab/a.py" in staged
    assert "docs/b.md" not in staged


def test_stage_domain_changes_other_domain(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _init_repo(workspace)

    (workspace / ".vscode").mkdir(parents=True, exist_ok=True)
    (workspace / ".vscode" / "tasks.json").write_text("{\"version\":\"2.0.0\"}\n", encoding="utf-8")
    (workspace / "docs").mkdir(parents=True, exist_ok=True)
    (workspace / "docs" / "c.md").write_text("# c\n", encoding="utf-8")

    report = stage_domain_changes(workspace=workspace, domain="other", dry_run=True)
    assert report["ok"] is True
    assert report["candidate_count"] == 1
    assert ".vscode/tasks.json" in report["sample_paths"]
