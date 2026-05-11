import subprocess
from pathlib import Path

from ai_collab.workspace_guard import run_workspace_guard


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "-C", str(path), "init"], check=True, capture_output=True, text=True)


def test_workspace_guard_allows_clean_apply(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _init_repo(workspace)

    report = run_workspace_guard(
        workspace=workspace,
        command="dispatch",
        mode="apply",
        guard_config={
            "enabled": True,
            "applyOnly": True,
            "requireSourceClean": True,
            "dirtyTotalThreshold": 120,
            "rootDeletedThreshold": 10,
        },
        force=False,
    )

    assert report["allowed"] is True
    assert report["totals"]["total"] == 0


def test_workspace_guard_blocks_source_dirty_on_apply(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _init_repo(workspace)
    source_file = workspace / "ai_collab" / "new_module.py"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("print('x')\n", encoding="utf-8")

    report = run_workspace_guard(
        workspace=workspace,
        command="dispatch",
        mode="apply",
        guard_config={
            "enabled": True,
            "applyOnly": True,
            "requireSourceClean": True,
            "dirtyTotalThreshold": 120,
            "rootDeletedThreshold": 10,
        },
        force=False,
    )

    assert report["allowed"] is False
    assert report["domains"]["source"] > 0
    assert any("source domain is not clean" in item for item in report["violations"])


def test_workspace_guard_dry_run_does_not_block(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _init_repo(workspace)
    source_file = workspace / "ai_collab" / "new_module.py"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("print('x')\n", encoding="utf-8")

    report = run_workspace_guard(
        workspace=workspace,
        command="dispatch",
        mode="dry-run",
        guard_config={
            "enabled": True,
            "applyOnly": True,
            "requireSourceClean": True,
            "dirtyTotalThreshold": 0,
            "rootDeletedThreshold": 0,
        },
        force=False,
    )

    assert report["allowed"] is True
    assert report["totals"]["total"] > 0
