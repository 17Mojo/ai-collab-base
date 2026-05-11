"""Workspace dirty-tree guardrails for safe automation runs."""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

SOURCE_PREFIXES = (
    "ai_collab/",
    "src/",
    "tests/",
    "scripts/",
    "rules/",
)
OPS_PREFIXES = (
    "collaboration/results/",
    "collaboration/monitoring/",
    "logs/",
)
DOC_PREFIXES = (
    "docs/",
    "openspec/",
    "research/",
    "collaboration/tasks/",
    "collaboration/guides/",
    "collaboration/templates/",
)
STAGE_DOMAINS = {"source", "ops", "docs", "other"}


def _as_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_path(raw: str) -> str:
    value = (raw or "").strip()
    if " -> " in value:
        value = value.split(" -> ", 1)[1]
    return _decode_git_quoted_path(value)


def _decode_git_quoted_path(value: str) -> str:
    text = (value or "").strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        inner = text[1:-1]
        try:
            decoded = inner.encode("utf-8").decode("unicode_escape")
        except UnicodeDecodeError:
            decoded = inner
        # Git uses octal escapes for raw UTF-8 bytes; roundtrip latin1->utf8 restores true characters.
        try:
            decoded = decoded.encode("latin1").decode("utf-8")
        except UnicodeError:
            pass
        return decoded
    return text.strip('"')


def _status_type(xy: str) -> str:
    if xy == "??":
        return "untracked"
    if "D" in xy:
        return "deleted"
    if "M" in xy:
        return "modified"
    if "A" in xy:
        return "added"
    if "R" in xy:
        return "renamed"
    return "other"


def _classify_domain(path: str) -> str:
    if any(path.startswith(prefix) for prefix in SOURCE_PREFIXES):
        return "source"
    if any(path.startswith(prefix) for prefix in OPS_PREFIXES):
        return "ops"
    if any(path.startswith(prefix) for prefix in DOC_PREFIXES):
        return "docs"
    if "/" not in path and path.lower().endswith(".md"):
        return "docs"
    return "other"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _read_status_entries(workspace: Path) -> dict[str, Any]:
    """Read git porcelain entries and annotate status/domain."""
    result = subprocess.run(
        ["git", "-C", str(workspace), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {
            "ok": False,
            "error": result.stderr.strip() or "git status failed",
            "returncode": int(result.returncode),
        }

    entries: list[dict[str, Any]] = []
    lines = [line.rstrip("\n") for line in result.stdout.splitlines() if line.strip()]
    for line in lines:
        xy = line[:2]
        path = _normalize_path(line[3:] if len(line) > 3 else "")
        if not path:
            continue
        entries.append(
            {
                "xy": xy,
                "status": _status_type(xy),
                "path": path,
                "domain": _classify_domain(path),
                "top_dir": path.split("/", 1)[0] if "/" in path else "(root)",
            }
        )
    return {"ok": True, "entries": entries}


def inspect_workspace(workspace: Path) -> dict[str, Any]:
    """Inspect git workspace using porcelain output."""
    raw = _read_status_entries(workspace)
    if not raw.get("ok", False):
        return raw

    totals: Counter[str] = Counter()
    domains: Counter[str] = Counter()
    top_dirs: Counter[str] = Counter()
    results_untracked = 0
    root_deleted = 0

    entries = raw.get("entries", [])
    for item in entries:
        status = str(item.get("status", "other"))
        domain = str(item.get("domain", "other"))
        path = str(item.get("path", ""))
        top_dir = str(item.get("top_dir", "(root)"))

        totals["total"] += 1
        totals[status] += 1
        domains[domain] += 1
        top_dirs[top_dir] += 1

        if status == "deleted" and top_dir == "(root)":
            root_deleted += 1
        if status == "untracked" and path.startswith("collaboration/results/"):
            results_untracked += 1

    return {
        "ok": True,
        "totals": {
            "total": int(totals.get("total", 0)),
            "untracked": int(totals.get("untracked", 0)),
            "deleted": int(totals.get("deleted", 0)),
            "modified": int(totals.get("modified", 0)),
            "added": int(totals.get("added", 0)),
            "renamed": int(totals.get("renamed", 0)),
            "other": int(totals.get("other", 0)),
        },
        "domains": {
            "source": int(domains.get("source", 0)),
            "ops": int(domains.get("ops", 0)),
            "docs": int(domains.get("docs", 0)),
            "other": int(domains.get("other", 0)),
        },
        "root_deleted": int(root_deleted),
        "results_untracked": int(results_untracked),
        "top_dirs": [
            {"dir": name, "count": int(count)} for name, count in top_dirs.most_common(20)
        ],
    }


def run_workspace_guard(
    *,
    workspace: Path,
    command: str,
    mode: str,
    guard_config: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Run workspace guardrail checks and persist latest + history reports."""
    cfg = guard_config if isinstance(guard_config, dict) else {}
    enabled = bool(cfg.get("enabled", True))
    apply_only = bool(cfg.get("applyOnly", True))
    fail_on_git_error = bool(cfg.get("failOnGitError", False))

    thresholds = {
        "dirty_total": _as_int(cfg.get("dirtyTotalThreshold"), 120),
        "root_deleted": _as_int(cfg.get("rootDeletedThreshold"), 10),
        "source_dirty": _as_int(cfg.get("sourceDirtyThreshold"), 30),
        "results_untracked": _as_int(cfg.get("resultsUntrackedThreshold"), 40),
    }
    require_source_clean = bool(cfg.get("requireSourceClean", True))

    apply_mode = str(mode).strip().lower() == "apply"
    guard_applies = enabled and (apply_mode or not apply_only)

    inspection = inspect_workspace(workspace)
    violations: list[str] = []
    warnings: list[str] = []

    if not inspection.get("ok", False):
        message = f"git status inspect failed: {inspection.get('error', 'unknown error')}"
        if guard_applies and fail_on_git_error and not force:
            violations.append(message)
        else:
            warnings.append(message)
        totals = {
            "total": 0,
            "untracked": 0,
            "deleted": 0,
            "modified": 0,
            "added": 0,
            "renamed": 0,
            "other": 0,
        }
        domains = {"source": 0, "ops": 0, "docs": 0, "other": 0}
        root_deleted = 0
        results_untracked = 0
        top_dirs: list[dict[str, Any]] = []
    else:
        totals = inspection.get("totals", {})
        domains = inspection.get("domains", {})
        root_deleted = int(inspection.get("root_deleted", 0))
        results_untracked = int(inspection.get("results_untracked", 0))
        top_dirs = inspection.get("top_dirs", [])

        if guard_applies and not force:
            dirty_total = int(totals.get("total", 0))
            source_dirty = int(domains.get("source", 0))
            if dirty_total > thresholds["dirty_total"]:
                violations.append(
                    f"dirty_total={dirty_total} exceeds threshold={thresholds['dirty_total']}"
                )
            if root_deleted > thresholds["root_deleted"]:
                violations.append(
                    f"root_deleted={root_deleted} exceeds threshold={thresholds['root_deleted']}"
                )
            if require_source_clean and source_dirty > 0:
                violations.append(
                    f"source domain is not clean: source_dirty={source_dirty}, require_source_clean=true"
                )
            if (
                source_dirty > thresholds["source_dirty"]
                and results_untracked > thresholds["results_untracked"]
            ):
                violations.append(
                    "source+artifact squeeze detected: "
                    f"source_dirty={source_dirty}>{thresholds['source_dirty']} and "
                    f"results_untracked={results_untracked}>{thresholds['results_untracked']}"
                )

    allowed = (not guard_applies) or force or (len(violations) == 0)
    generated_at = datetime.now().isoformat()
    report = {
        "generated_at": generated_at,
        "workspace": str(workspace),
        "command": command,
        "mode": mode,
        "enabled": enabled,
        "apply_only": apply_only,
        "guard_applies": guard_applies,
        "forced": bool(force),
        "allowed": bool(allowed),
        "require_source_clean": require_source_clean,
        "thresholds": thresholds,
        "totals": totals,
        "domains": domains,
        "root_deleted": int(root_deleted),
        "results_untracked": int(results_untracked),
        "top_dirs": top_dirs,
        "violations": violations,
        "warnings": warnings,
    }

    report_rel = str(cfg.get("report", "logs/workspace_forensics/workspace_guard_latest.json"))
    history_rel = str(cfg.get("history", "logs/workspace_forensics/workspace_guard_history.jsonl"))
    report_file = workspace / report_rel
    history_file = workspace / history_rel
    _write_json(report_file, report)
    _append_jsonl(history_file, report)

    report["report_file"] = str(report_file)
    report["history_file"] = str(history_file)
    return report


def _chunked(items: list[str], size: int = 200) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def stage_domain_changes(
    *,
    workspace: Path,
    domain: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Safely stage git changes by domain."""
    normalized_domain = str(domain).strip().lower()
    if normalized_domain not in STAGE_DOMAINS:
        return {
            "ok": False,
            "error": f"unsupported domain: {domain}",
            "domain": normalized_domain,
        }

    raw = _read_status_entries(workspace)
    if not raw.get("ok", False):
        return {
            "ok": False,
            "error": str(raw.get("error", "git status failed")),
            "domain": normalized_domain,
        }

    entries = [item for item in raw.get("entries", []) if item.get("domain") == normalized_domain]
    paths = sorted(
        {str(item.get("path", "")).strip() for item in entries if str(item.get("path", "")).strip()}
    )
    status_counter = Counter(str(item.get("status", "other")) for item in entries)

    add_error = ""
    staged = False
    if paths and not dry_run:
        for chunk in _chunked(paths):
            result = subprocess.run(
                ["git", "-C", str(workspace), "add", "--", *chunk],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                add_error = result.stderr.strip() or "git add failed"
                break
        staged = add_error == ""

    generated_at = datetime.now().isoformat()
    report = {
        "generated_at": generated_at,
        "workspace": str(workspace),
        "domain": normalized_domain,
        "mode": "dry-run" if dry_run else "apply",
        "candidate_count": len(paths),
        "status_counts": {
            "untracked": int(status_counter.get("untracked", 0)),
            "deleted": int(status_counter.get("deleted", 0)),
            "modified": int(status_counter.get("modified", 0)),
            "added": int(status_counter.get("added", 0)),
            "renamed": int(status_counter.get("renamed", 0)),
            "other": int(status_counter.get("other", 0)),
        },
        "sample_paths": paths[:30],
        "ok": (add_error == ""),
        "staged": staged or dry_run,
        "error": add_error,
    }

    report_file = (
        workspace / "logs" / "workspace_forensics" / f"stage_{normalized_domain}_latest.json"
    )
    history_file = (
        workspace / "logs" / "workspace_forensics" / f"stage_{normalized_domain}_history.jsonl"
    )
    _write_json(report_file, report)
    _append_jsonl(history_file, report)
    report["report_file"] = str(report_file)
    report["history_file"] = str(history_file)
    return report
