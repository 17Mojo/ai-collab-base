import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.sync_agent_memory import (  # noqa: E402
    build_desired,
    build_index,
    default_source,
    diff_desired,
    main,
    main_repo_path,
    parse_frontmatter,
    resolve_type,
)


def _write_memory(root, name, body, meta=None):
    root.mkdir(parents=True, exist_ok=True)
    front = ""
    if meta is not None:
        front = "---\n" + "\n".join(f"{k}: {v}" for k, v in meta.items()) + "\n---\n\n"
    (root / name).write_text(front + body, encoding="utf-8")


def test_parse_frontmatter_reads_keys():
    text = "---\nname: Foo\ndescription: bar baz\ntype: project\n---\n\nbody\n"
    meta = parse_frontmatter(text)
    assert meta["name"] == "Foo"
    assert meta["description"] == "bar baz"
    assert meta["type"] == "project"


def test_parse_frontmatter_without_block_returns_empty():
    assert parse_frontmatter("# just a heading\n") == {}


def test_resolve_type_prefers_explicit():
    assert resolve_type("anything.md", {"type": "reference"}) == "reference"


def test_resolve_type_infers_from_filename_prefix():
    assert resolve_type("project_things.md", {}) == "project"
    assert resolve_type("user.md", {}) == "user"
    assert resolve_type("feedback_x.md", {}) == "feedback"
    assert resolve_type("reference_y.md", {}) == "reference"


def test_resolve_type_unknown_is_other():
    assert resolve_type("misc_notes.md", {}) == "other"


def test_build_index_groups_by_type():
    entries = [
        ("project.md", {"description": "P desc"}),
        ("user.md", {"description": "U desc"}),
    ]
    index = build_index(entries)
    assert "## Project" in index
    assert "## User" in index
    assert "- [project.md](project.md) — P desc" in index
    assert "- [user.md](user.md) — U desc" in index


def test_diff_desired_detects_add_update_remove():
    current = {"a.md": "1", "b.md": "2"}
    desired = {"a.md": "1", "b.md": "changed", "c.md": "3"}
    changes = diff_desired(current, desired)
    assert ("add", "c.md") in changes
    assert ("update", "b.md") in changes
    assert ("remove", "d.md") not in changes
    assert ("remove", "a.md") not in changes


def test_build_desired_regenerates_index_and_skips_ignored(tmp_path):
    src = tmp_path / "src"
    _write_memory(src, "project.md", "# p\n", {"type": "project", "description": "P"})
    _write_memory(src, "notes.txt", "ignored")
    _write_memory(src, ".runtime.json", "ignored")
    desired = build_desired(src)
    assert "project.md" in desired
    assert "MEMORY.md" in desired
    assert "notes.txt" not in desired
    assert ".runtime.json" not in desired
    assert "## Project" in desired["MEMORY.md"]


def test_sync_writes_mirror_and_is_idempotent(tmp_path, monkeypatch):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _write_memory(src, "project.md", "# p\n", {"type": "project", "description": "P"})
    _write_memory(src, "user.md", "# u\n", {"description": "U"})
    monkeypatch.setattr(
        sys, "argv",
        ["sync_agent_memory.py", "--source", str(src), "--dest", str(dst), "--quiet"],
    )
    assert main() == 0
    assert (dst / "project.md").exists()
    assert (dst / "MEMORY.md").exists()
    assert (dst / ".sync-manifest.json").exists()
    assert "## User" in (dst / "MEMORY.md").read_text(encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv",
        ["sync_agent_memory.py", "--source", str(src), "--dest", str(dst), "--check", "--quiet"],
    )
    assert main() == 0


def test_check_detects_drift(tmp_path, monkeypatch):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _write_memory(src, "project.md", "# p\n", {"type": "project"})
    monkeypatch.setattr(
        sys, "argv",
        ["sync_agent_memory.py", "--source", str(src), "--dest", str(dst), "--quiet"],
    )
    assert main() == 0
    _write_memory(src, "project.md", "# changed\n", {"type": "project"})
    monkeypatch.setattr(
        sys, "argv",
        ["sync_agent_memory.py", "--source", str(src), "--dest", str(dst), "--check", "--quiet"],
    )
    assert main() == 1


def test_missing_source_returns_nonzero(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys, "argv",
        ["sync_agent_memory.py", "--source", str(tmp_path / "nope"), "--dest", str(tmp_path / "dst"), "--quiet"],
    )
    assert main() == 1


def test_main_repo_path_resolves_worktree_to_main_repo(tmp_path, monkeypatch):
    """worktree 里的记忆源必须指向**主仓库**那一份，否则 --check 永远报警。

    2026-10-27 实测：`git worktree` 的工作目录路径与主仓库不同
    （主仓库 /Users/x/ai-collab-base，worktree /tmp/pr5-rebase），
    而记忆目录是按**仓库**分的 ⇒ 取错路径时源目录根本不存在，
    `pre-commit` 钩子只会一直喊「镜像过期」。
    """
    main_repo = tmp_path / "main-repo"
    worktree = tmp_path / "wt"
    (main_repo / ".git").mkdir(parents=True)
    worktree.mkdir(parents=True)

    class _Result:
        returncode = 0
        stdout = str(main_repo / ".git") + "\n"

    monkeypatch.setattr(
        "scripts.sync_agent_memory.subprocess.run",
        lambda cmd, **kwargs: _Result(),
    )
    assert main_repo_path(worktree) == main_repo


def test_main_repo_path_falls_back_when_git_fails(tmp_path, monkeypatch):
    """取不到 git common dir 时退回传入的路径（不许抛异常）。"""

    class _Result:
        returncode = 128
        stdout = ""

    monkeypatch.setattr(
        "scripts.sync_agent_memory.subprocess.run",
        lambda cmd, **kwargs: _Result(),
    )
    assert main_repo_path(tmp_path) == tmp_path


def test_default_source_uses_main_repo_slug(tmp_path, monkeypatch):
    """default_source 必须按**主仓库**路径算 slug，不是 worktree 路径。"""
    import scripts.sync_agent_memory as mod

    main_repo = tmp_path / "main-repo"
    worktree = tmp_path / "wt"
    monkeypatch.setattr(mod, "main_repo_path", lambda repo: main_repo)
    assert default_source(worktree).name == str(main_repo.resolve()).replace("/", "-")
