#!/usr/bin/env python3
# ruff: noqa: E402
"""
PreCompact Hook:
- compact 前快照 .cc-claude-codex/status.md
- 同时快照 logs/collaboration_state.json
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_collab.session_autoregistration import register_claude_session_from_hook


def _get_cwd(hook_input: dict) -> Path:
    cwd = hook_input.get("cwd")
    if isinstance(cwd, bytes):
        # Decode bytes to string before creating Path
        return Path(cwd.decode('utf-8'))
    elif isinstance(cwd, str):
        return Path(cwd)
    return Path(".")


def _snapshot(src: Path, dest: Path):
    if src.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    cwd = _get_cwd(hook_input)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    try:
        register_claude_session_from_hook(
            workspace=cwd,
            hook_input=hook_input,
            event_name="PreCompact",
        )
    except Exception:
        pass

    snapshots = cwd / ".cc-claude-codex" / "snapshots"
    status_file = cwd / ".cc-claude-codex" / "status.md"
    state_file = cwd / "logs" / "collaboration_state.json"

    _snapshot(status_file, snapshots / f"{ts}-status.md")
    _snapshot(state_file, snapshots / f"{ts}-state.json")

    print(f"AI Collab PreCompact: snapshot at {snapshots}", file=sys.stderr)


if __name__ == "__main__":
    main()
