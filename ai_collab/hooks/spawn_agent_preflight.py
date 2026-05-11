#!/usr/bin/env python3
"""
PreToolUse Agent Hook:
- 在内部 Agent 委派前自动运行 spawn_agent guard
- 优先读取显式元数据，缺失时回退到 runtime.json / codex-progress.md
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_collab.spawn_agent_guard import run_spawn_agent_guard  # noqa: E402

TASK_PATTERN = re.compile(r"\bTASK-[A-Za-z0-9._-]+\b")
PATH_PATTERN = re.compile(r"(?<![\w/])(?:\.?[\w-]+/)*\.?[\w-]+\.[A-Za-z0-9_-]+\b")
PARENT_LABELS = ("parent task", "parent_task", "parent-task", "task")
FILE_LABELS = ("files", "file", "scope", "write set", "write-set", "paths", "负责文件", "修改文件")
READ_ONLY_LABELS = ("read only", "readonly", "read-only", "只读")
NEGATIVE_HINTS = ("do not", "don't", "不要", "不得", "禁止", "avoid", "exclude", "不可")
READ_ONLY_HINTS = (
    "read only",
    "readonly",
    "read-only",
    "do not modify",
    "don't modify",
    "inspect only",
    "review only",
    "analyze only",
    "不要修改",
    "仅分析",
    "只读",
    "仅检查",
)
WRITE_HINTS = (
    "edit",
    "modify",
    "update",
    "create",
    "write",
    "implement",
    "fix",
    "patch",
    "refactor",
    "change",
    "修改",
    "实现",
    "更新",
    "补测试",
    "新增",
    "修复",
    "重构",
)
ACTION_HINTS = (
    READ_ONLY_HINTS
    + WRITE_HINTS
    + (
        "inspect",
        "review",
        "analyze",
        "check",
        "核查",
        "检查",
        "验证",
    )
)
READ_ONLY_SUBAGENT_TYPES = {"review", "research", "analysis", "analyze", "inspect", "plan"}

INTERNAL_PARENT_PREFIXES = ("INTERNAL-CODEX-",)


def _get_cwd(hook_input: dict[str, Any]) -> Path:
    cwd = hook_input.get("cwd")
    if isinstance(cwd, bytes):
        return Path(cwd.decode("utf-8"))
    if isinstance(cwd, str):
        return Path(cwd)
    return Path(".")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_path(workspace: Path, raw: Any) -> str:
    text = str(raw or "").strip().strip(",;:")
    text = text.strip("`'\"")
    if not text or "://" in text or text.startswith("TASK-"):
        return ""

    candidate = Path(text)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(workspace.resolve())
        except ValueError:
            return candidate.as_posix()

    normalized = candidate.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _path_tokens(text: str, workspace: Path) -> list[str]:
    tokens = [
        _normalize_path(workspace, match.group(0)) for match in PATH_PATTERN.finditer(text or "")
    ]
    return _dedupe([token for token in tokens if token])


def _line_payload(line: str, labels: tuple[str, ...]) -> str:
    lower = line.lower()
    for label in labels:
        for separator in (":", "："):
            prefix = f"{label}{separator}"
            if lower.startswith(prefix):
                return line[len(prefix) :].strip()
    return ""


def _extract_parent_task(text: str, runtime: dict[str, Any]) -> tuple[str | None, str]:
    runtime_task = str(runtime.get("task_id", "")).strip()
    if runtime_task:
        return runtime_task, "runtime"

    for line in (text or "").splitlines():
        payload = _line_payload(line.strip(), PARENT_LABELS)
        if not payload:
            continue
        matches = TASK_PATTERN.findall(payload)
        if matches:
            return matches[0], "prompt-label"
        if payload:
            return payload, "prompt-label"

    matches = _dedupe(TASK_PATTERN.findall(text or ""))
    if len(matches) == 1:
        return matches[0], "prompt-text"
    return None, "missing"


def _is_internal_read_only_parent(parent_task_id: str | None, read_only: bool) -> bool:
    if not read_only:
        return False
    normalized = str(parent_task_id or "").strip().upper()
    if not normalized:
        return False
    return any(normalized.startswith(prefix) for prefix in INTERNAL_PARENT_PREFIXES)


def _extract_explicit_files(
    tool_input: dict[str, Any], text: str, workspace: Path
) -> tuple[list[str], str]:
    for key in ("files", "paths", "scope", "write_set", "writeSet"):
        value = tool_input.get(key)
        if isinstance(value, list):
            files = _dedupe(
                [
                    _normalize_path(workspace, item)
                    for item in value
                    if _normalize_path(workspace, item)
                ]
            )
            if files:
                return files, f"tool_input.{key}"
        if isinstance(value, str) and value.strip():
            files = _path_tokens(value, workspace)
            if files:
                return files, f"tool_input.{key}"

    candidates: list[str] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        payload = _line_payload(line, FILE_LABELS)
        if payload:
            candidates.extend(_path_tokens(payload, workspace))
            continue

        lower = line.lower()
        if any(marker in lower for marker in NEGATIVE_HINTS):
            continue
        if any(hint in lower for hint in ACTION_HINTS):
            candidates.extend(_path_tokens(line, workspace))

    deduped = _dedupe(candidates)
    if deduped:
        return deduped, "prompt"
    return [], "missing"


def _read_progress_scope(progress_file: Path, workspace: Path) -> list[str]:
    if not progress_file.exists():
        return []

    content = progress_file.read_text(encoding="utf-8")
    scope_matches = re.findall(r"- \*\*Scope:\*\* (.+)", content)
    scope_files: list[str] = []
    for scope in scope_matches:
        for item in scope.split(","):
            normalized = _normalize_path(workspace, item)
            if normalized and normalized not in {"TBD", "-"}:
                scope_files.append(normalized)
    return _dedupe(scope_files)


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on", "readonly", "read-only"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", "write", "workspace-write"}:
        return False
    return None


def _infer_read_only(tool_input: dict[str, Any], text: str, *, has_files: bool) -> tuple[bool, str]:
    for key in ("read_only", "readonly", "readOnly"):
        parsed = _parse_bool(tool_input.get(key))
        if parsed is not None:
            return parsed, f"tool_input.{key}"

    mode = _parse_bool(tool_input.get("mode"))
    if mode is not None:
        return mode, "tool_input.mode"

    for line in (text or "").splitlines():
        payload = _line_payload(line.strip(), READ_ONLY_LABELS)
        if payload:
            parsed = _parse_bool(payload)
            if parsed is not None:
                return parsed, "prompt-label"

    lower = (text or "").lower()
    if any(hint in lower for hint in READ_ONLY_HINTS):
        return True, "prompt-hint"
    if any(hint in lower for hint in WRITE_HINTS):
        return False, "prompt-hint"

    subagent_type = str(tool_input.get("subagent_type", "")).strip().lower()
    if subagent_type in READ_ONLY_SUBAGENT_TYPES and not has_files:
        return True, "subagent-type"
    return False, "default-write"


def _tool_text(tool_input: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("description", "prompt", "task", "message", "context"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return "\n".join(parts)


def build_preflight_request(hook_input: dict[str, Any]) -> dict[str, Any]:
    workspace = _get_cwd(hook_input).resolve()
    tool_input = hook_input.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    runtime = _load_json(workspace / ".cc-claude-codex" / "runtime.json")
    config = _load_json(workspace / ".vscode" / "ai-collab.json")
    text = _tool_text(tool_input)

    parent_task_id, parent_task_source = _extract_parent_task(text, runtime)
    files, files_source = _extract_explicit_files(tool_input, text, workspace)
    if not files:
        progress_scope = _read_progress_scope(
            workspace / ".cc-claude-codex" / "codex-progress.md", workspace
        )
        if progress_scope:
            files = progress_scope
            files_source = "progress-scope"

    read_only, read_only_source = _infer_read_only(tool_input, text, has_files=bool(files))
    if _is_internal_read_only_parent(parent_task_id, read_only):
        parent_task_source = "internal-read-only"

    return {
        "workspace": workspace,
        "config": config,
        "actor": "codex",
        "parent_task_id": parent_task_id,
        "files": files,
        "read_only": read_only,
        "metadata": {
            "trigger": "pretooluse-agent-hook",
            "tool_name": str(hook_input.get("tool_name", "Agent") or "Agent"),
            "parent_task_source": parent_task_source,
            "files_source": files_source,
            "read_only_source": read_only_source,
            "subagent_type": str(tool_input.get("subagent_type", "")).strip(),
        },
    }


def _deny_output(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _build_reason(request: dict[str, Any], report: dict[str, Any]) -> str:
    metadata = request.get("metadata", {}) if isinstance(request.get("metadata"), dict) else {}
    sources = (
        f"parent={metadata.get('parent_task_source', 'unknown')}",
        f"files={metadata.get('files_source', 'unknown')}",
        f"mode={metadata.get('read_only_source', 'unknown')}",
    )
    violations = report.get("violations", [])
    detail = (
        "; ".join(str(item) for item in violations[:3]) or "spawn_agent policy denied delegation"
    )
    return f"AI Collab spawn_agent preflight blocked ({', '.join(sources)}): {detail}"


def run_preflight(hook_input: dict[str, Any]) -> dict[str, Any]:
    request = build_preflight_request(hook_input)
    report = run_spawn_agent_guard(
        workspace=request["workspace"],
        actor=request["actor"],
        parent_task_id=request["parent_task_id"],
        files=request["files"],
        read_only=request["read_only"],
        metadata=request["metadata"],
        config=request["config"],
    )
    if report["allowed"]:
        return {"allowed": True, "request": request, "report": report, "hook_output": None}
    reason = _build_reason(request, report)
    return {
        "allowed": False,
        "request": request,
        "report": report,
        "hook_output": _deny_output(reason),
    }


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    try:
        result = run_preflight(hook_input)
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps(
                _deny_output(f"AI Collab spawn_agent preflight failed: {exc}"), ensure_ascii=False
            )
        )
        return

    if result["hook_output"] is not None:
        print(json.dumps(result["hook_output"], ensure_ascii=False))


if __name__ == "__main__":
    main()
