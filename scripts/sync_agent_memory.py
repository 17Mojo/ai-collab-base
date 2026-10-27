#!/usr/bin/env python3
"""Sync CodeArts-managed memory into the repo memory/ mirror.

Source: ~/.codeartsdoer/memory/<slug>/ (CodeArts-managed, treated read-only)
Dest:   <repo>/memory/ (mirror, consumed by Claude Code via CLAUDE.md @import)
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_NAME = ".sync-manifest.json"
INDEX_NAME = "MEMORY.md"
TYPE_ORDER = ["project", "user", "feedback", "reference"]


def resolve_type(name, meta):
    explicit = meta.get("type")
    if explicit:
        return explicit
    stem = name[:-3] if name.endswith(".md") else name
    for prefix in TYPE_ORDER:
        if stem == prefix or stem.startswith(prefix + "_"):
            return prefix
    return "other"


def repo_root():
    return Path(__file__).resolve().parent.parent


def main_repo_path(repo):
    """取**主仓库**的路径（worktree 场景下与 worktree 路径不同）。

    ## 为什么需要这个

    `git worktree` 会在 `.git/worktrees/<name>/` 下建一个工作区，
    它的**工作目录路径**与主仓库不同（例如主仓库在
    `/Users/x/ai-collab-base`，worktree 在 `/tmp/pr5-rebase`）。

    记忆目录是**按仓库**分的（`~/.codeartsdoer/memory/<仓库路径 slug>/`），
    所以在 worktree 里也得指向**主仓库**那一份——
    否则 worktree 里跑 `--check` 会因为「源目录不存在」而永远报警，
    `pre-commit` 钩子也会一直喊「镜像过期」。

    取法：`git rev-parse --git-common-dir` 指向主仓库的 `.git`，
    去掉末尾的 `.git` 即主仓库路径。取不到就退回传入的路径。
    """
    try:
        common = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        out = (common.stdout or "").strip()
        if common.returncode == 0 and out:
            common_path = Path(out)
            if not common_path.is_absolute():
                common_path = (repo / common_path).resolve()
            if common_path.name == ".git":
                return common_path.parent
    except (OSError, subprocess.SubprocessError):
        pass
    return repo


def derive_slug(repo):
    return str(repo.resolve()).replace("/", "-")


def default_source(repo):
    return Path.home() / ".codeartsdoer" / "memory" / derive_slug(main_repo_path(repo))


def parse_frontmatter(text):
    meta = {}
    if not text.startswith("---"):
        return meta
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta


def collect_source_files(source):
    if not source.is_dir():
        return []
    return sorted(
        p for p in source.iterdir()
        if p.is_file()
        and p.suffix == ".md"
        and not p.name.startswith(".")
        and p.name != INDEX_NAME
    )


def build_index(entries):
    groups = {}
    for name, meta in entries:
        groups.setdefault(resolve_type(name, meta), []).append((name, meta))
    order = TYPE_ORDER + [k for k in groups if k not in TYPE_ORDER]
    lines = ["# Memory Index", ""]
    for group in order:
        if group not in groups:
            continue
        lines.append("## " + group.capitalize())
        for name, meta in groups[group]:
            title = meta.get("name") or name
            desc = meta.get("description", "")
            lines.append(f"- [{title}]({name}) — {desc}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_desired(source):
    files = collect_source_files(source)
    entries = [(p.name, parse_frontmatter(p.read_text(encoding="utf-8"))) for p in files]
    desired = {p.name: p.read_text(encoding="utf-8") for p in files}
    desired[INDEX_NAME] = build_index(entries)
    return desired


def snapshot(dest):
    if not dest.is_dir():
        return {}
    result = {}
    for p in dest.iterdir():
        if p.is_file() and p.name != MANIFEST_NAME:
            result[p.name] = p.read_text(encoding="utf-8")
    return result


def diff_desired(current, desired):
    changes = []
    for name in sorted(set(current) | set(desired)):
        if name not in desired:
            changes.append(("remove", name))
        elif name not in current:
            changes.append(("add", name))
        elif current[name] != desired[name]:
            changes.append(("update", name))
    return changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source")
    parser.add_argument("--dest")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    repo = repo_root()
    source = Path(args.source) if args.source else default_source(repo)
    dest = Path(args.dest) if args.dest else repo / "memory"

    if not source.is_dir():
        print(f"source memory dir not found: {source}")
        return 1

    desired = build_desired(source)
    current = snapshot(dest)
    changes = diff_desired(current, desired)

    if args.check:
        if changes:
            for action, name in changes:
                print(f"{action}: {name}")
            print(f"memory mirror out of sync ({len(changes)} change(s)); run sync_agent_memory.py")
            return 1
        if not args.quiet:
            print(f"[OK] memory mirror in sync ({len(desired)} file(s))")
        return 0

    if args.dry_run:
        for action, name in changes:
            print(f"{action}: {name}")
        print(f"dry-run: {len(changes)} change(s)")
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    for name in sorted(desired):
        (dest / name).write_text(desired[name], encoding="utf-8")
    for action, name in changes:
        if action == "remove":
            (dest / name).unlink(missing_ok=True)

    manifest = {
        "source": str(source),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": sorted(desired),
        "count": len(desired),
    }
    (dest / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if not args.quiet:
        print(f"synced {len(desired)} file(s) -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
