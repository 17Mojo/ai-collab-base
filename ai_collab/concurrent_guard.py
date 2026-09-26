"""Concurrent workspace guardrails: detect branch drift, baseline staleness, and foreign changes."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


def _run_git(workspace: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(workspace), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _git_text(workspace: Path, args: list[str]) -> str:
    result = _run_git(workspace, args)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _normalize_porcelain_path(raw: str) -> str:
    value = (raw or "").strip()
    if " -> " in value:
        value = value.split(" -> ", 1)[1]
    return value


def inspect_git_context(workspace: Path) -> dict[str, Any]:
    """Collect read-only git context: branch, HEAD, upstream, ahead/behind, dirty paths."""
    branch_raw = _git_text(workspace, ["rev-parse", "--abbrev-ref", "HEAD"])
    branch: str | None = branch_raw if branch_raw and branch_raw != "HEAD" else None

    head_commit = _git_text(workspace, ["rev-parse", "HEAD"])

    upstream: str | None = None
    ahead = 0
    behind = 0
    upstream_result = _run_git(workspace, ["rev-parse", "--abbrev-ref", "@{u}"])
    if upstream_result.returncode == 0:
        upstream = upstream_result.stdout.strip() or None
        count_result = _run_git(
            workspace, ["rev-list", "--left-right", "--count", "@{u}...HEAD"]
        )
        if count_result.returncode == 0:
            parts = count_result.stdout.strip().split()
            if len(parts) >= 2:
                try:
                    behind = int(parts[0])
                    ahead = int(parts[1])
                except ValueError:
                    pass

    status_result = _run_git(
        workspace, ["status", "--porcelain=v1", "--untracked-files=all"]
    )
    dirty_paths: list[str] = []
    dirty_total = 0
    if status_result.returncode == 0:
        for line in status_result.stdout.splitlines():
            if not line.strip():
                continue
            dirty_total += 1
            path = _normalize_porcelain_path(line[3:] if len(line) > 3 else "")
            if path and len(dirty_paths) < 50:
                dirty_paths.append(path)

    return {
        "ok": True,
        "branch": branch,
        "head_commit": head_commit,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "dirty_total": dirty_total,
        "dirty_paths": dirty_paths,
    }


def detect_branch_drift(
    workspace: Path, expected_branch: str | None
) -> dict[str, Any]:
    """Detect whether HEAD branch matches the expected branch (G1, git hard evidence)."""
    if expected_branch is None:
        return {"drifted": False, "expected": None, "actual": None, "severity": "none"}
    context = inspect_git_context(workspace)
    actual = context.get("branch")
    drifted = actual != expected_branch
    return {
        "drifted": drifted,
        "expected": expected_branch,
        "actual": actual,
        "severity": "high" if drifted else "none",
    }


def detect_baseline_staleness(
    workspace: Path,
    baseline_commit: str,
    watch_paths: list[str],
) -> dict[str, Any]:
    """Detect whether watched paths changed between baseline_commit and HEAD (G2, git hard evidence)."""
    head_commit = _git_text(workspace, ["rev-parse", "HEAD"])
    changed: list[dict[str, Any]] = []
    for path in watch_paths:
        result = _run_git(
            workspace,
            ["rev-list", "--count", f"{baseline_commit}..HEAD", "--", path],
        )
        if result.returncode != 0:
            changed.append(
                {"path": path, "commits_since": None, "error": result.stderr.strip()}
            )
            continue
        try:
            count = int(result.stdout.strip())
        except ValueError:
            count = 0
        changed.append({"path": path, "commits_since": count})
    stale = any(
        item.get("commits_since") is not None and item["commits_since"] > 0
        for item in changed
    )
    return {
        "stale": stale,
        "baseline_commit": baseline_commit,
        "head_commit": head_commit,
        "changed_watch_paths": changed,
        "severity": "high" if stale else "none",
    }


def detect_foreign_changes(
    workspace: Path,
    session_started_at: str,
    tracked_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Detect uncommitted changes whose mtime predates the session (G3, mtime heuristic)."""
    session_dt = _parse_iso(session_started_at)
    if session_dt is None:
        return {
            "foreign_count": 0,
            "foreign_paths": [],
            "severity": "none",
            "error": f"invalid session_started_at: {session_started_at}",
        }
    session_epoch = session_dt.timestamp()
    tracked_set = set(tracked_paths or [])

    status_result = _run_git(
        workspace, ["status", "--porcelain=v1", "--untracked-files=all"]
    )
    if status_result.returncode != 0:
        return {
            "foreign_count": 0,
            "foreign_paths": [],
            "severity": "none",
            "error": status_result.stderr.strip() or "git status failed",
        }

    foreign_paths: list[dict[str, Any]] = []
    for line in status_result.stdout.splitlines():
        if not line.strip():
            continue
        raw = _normalize_porcelain_path(line[3:] if len(line) > 3 else "")
        if not raw or raw in tracked_set:
            continue
        full = workspace / raw
        try:
            mtime = os.path.getmtime(full)
        except OSError:
            continue
        if mtime < session_epoch:
            foreign_paths.append(
                {
                    "path": raw,
                    "mtime": datetime.fromtimestamp(mtime).isoformat(),
                }
            )
    foreign_count = len(foreign_paths)
    return {
        "foreign_count": foreign_count,
        "foreign_paths": foreign_paths,
        "severity": "high" if foreign_count > 0 else "none",
    }


def assess_concurrent_risk(
    workspace: Path,
    *,
    expected_branch: str | None = None,
    baseline_commit: str | None = None,
    watch_paths: list[str] | None = None,
    session_started_at: str | None = None,
    tracked_paths: list[str] | None = None,
    foreign_change_severity: str = "warning",
    ahead_warn_threshold: int = 20,
) -> dict[str, Any]:
    """Assess concurrent workspace risk across branch drift, baseline staleness, and foreign changes."""
    git_context = inspect_git_context(workspace)
    signals: dict[str, Any] = {}
    violations: list[str] = []
    warnings: list[str] = []

    branch_signal = detect_branch_drift(workspace, expected_branch)
    signals["branch_drift"] = branch_signal
    if branch_signal.get("drifted"):
        violations.append(
            f"branch drift: expected={branch_signal.get('expected')} "
            f"actual={branch_signal.get('actual')}"
        )

    if baseline_commit is not None and watch_paths:
        baseline_signal = detect_baseline_staleness(
            workspace, baseline_commit, watch_paths
        )
        signals["baseline_stale"] = baseline_signal
        if baseline_signal.get("stale"):
            changed = baseline_signal.get("changed_watch_paths", [])
            changed_count = sum(
                1
                for item in changed
                if item.get("commits_since") is not None and item["commits_since"] > 0
            )
            violations.append(
                f"baseline stale: {baseline_commit}.."
                f"{baseline_signal.get('head_commit')} "
                f"({changed_count} watched path(s) changed)"
            )
    else:
        signals["baseline_stale"] = {"stale": False, "severity": "none"}

    if session_started_at is not None:
        foreign_signal = detect_foreign_changes(
            workspace, session_started_at, tracked_paths
        )
        signals["foreign_changes"] = foreign_signal
        foreign_count = int(foreign_signal.get("foreign_count", 0))
        if foreign_count > 0:
            message = f"foreign changes detected: {foreign_count} files"
            if foreign_change_severity == "high":
                violations.append(message)
            else:
                warnings.append(message)
    else:
        signals["foreign_changes"] = {"foreign_count": 0, "severity": "none"}

    ahead = int(git_context.get("ahead", 0))
    if ahead > ahead_warn_threshold:
        warnings.append(
            f"ahead of upstream by {ahead} commits (threshold={ahead_warn_threshold})"
        )

    has_high = len(violations) > 0
    has_medium = len(warnings) > 0
    if has_high:
        risk_level = "high"
    elif has_medium:
        risk_level = "medium"
    else:
        risk_level = "low"
    allowed = not has_high

    return {
        "risk_level": risk_level,
        "allowed": allowed,
        "git_context": git_context,
        "signals": signals,
        "violations": violations,
        "warnings": warnings,
    }


def run_concurrent_guard(
    *,
    workspace: Path,
    expected_branch: str | None = None,
    baseline_commit: str | None = None,
    watch_paths: list[str] | None = None,
    session_started_at: str | None = None,
    tracked_paths: list[str] | None = None,
    guard_config: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Run concurrent guard assessment and persist latest + history reports."""
    cfg = guard_config if isinstance(guard_config, dict) else {}
    enabled = bool(cfg.get("enabled", True))
    foreign_change_severity = str(cfg.get("foreignChangeSeverity", "warning"))
    ahead_warn_threshold = int(cfg.get("aheadWarnThreshold", 20))

    assessment = assess_concurrent_risk(
        workspace,
        expected_branch=expected_branch,
        baseline_commit=baseline_commit,
        watch_paths=watch_paths,
        session_started_at=session_started_at,
        tracked_paths=tracked_paths,
        foreign_change_severity=foreign_change_severity,
        ahead_warn_threshold=ahead_warn_threshold,
    )

    violations = list(assessment.get("violations", []))
    warnings = list(assessment.get("warnings", []))
    if not enabled or force:
        allowed = True
    else:
        allowed = bool(assessment.get("allowed", True))

    generated_at = datetime.now().isoformat()
    report: dict[str, Any] = {
        "generated_at": generated_at,
        "workspace": str(workspace),
        "enabled": enabled,
        "forced": bool(force),
        "allowed": allowed,
        "risk_level": assessment.get("risk_level"),
        "git_context": assessment.get("git_context"),
        "signals": assessment.get("signals"),
        "violations": violations,
        "warnings": warnings,
        "thresholds": {
            "aheadWarnThreshold": ahead_warn_threshold,
            "foreignChangeSeverity": foreign_change_severity,
        },
    }

    report_rel = str(
        cfg.get("report", "logs/workspace_forensics/concurrent_guard_latest.json")
    )
    history_rel = str(
        cfg.get("history", "logs/workspace_forensics/concurrent_guard_history.jsonl")
    )
    report_file = workspace / report_rel
    history_file = workspace / history_rel
    _write_json(report_file, report)
    _append_jsonl(history_file, report)

    report["report_file"] = str(report_file)
    report["history_file"] = str(history_file)
    return report
