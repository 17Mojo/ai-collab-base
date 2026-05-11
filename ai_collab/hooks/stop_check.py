#!/usr/bin/env python3
# ruff: noqa: E402
"""
Stop Hook:
- 若 .cc-claude-codex/status.md 里有未完成任务，阻止退出
- 若当前会话负责的任务仍未闭环，阻止退出
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_collab.ack_protocol import (
    SUPPORTED_ASSIGNEES,
    has_ack_evidence,
    load_ack_bridge_state,
    normalize_assignee,
    normalize_result_file,
    requires_explicit_ack,
)
from ai_collab.session_auto_register import record_hook_session_observation
from ai_collab.session_autoregistration import register_claude_session_from_hook

ACTIVE_STATUSES = {"pending", "planning", "implementing", "testing", "in_progress"}
TASK_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
PATCH_TERMINAL_STATUSES = {"completed", "cancelled"}
EXPLICIT_ACK_GUARD_STATUSES = {"testing", "completed"}
DEFAULT_MODEL_AGENT_MAP = {
    r"claude": "claude_code",
    r"copilot": "codearts_agent",
    r"glm|codearts": "codearts_agent",
    r"gpt|codex|openai": "codex",
}


def _get_cwd(hook_input: dict) -> Path:
    cwd = hook_input.get("cwd")
    if isinstance(cwd, bytes):
        return Path(cwd.decode("utf-8"))
    if isinstance(cwd, str):
        return Path(cwd)
    return Path(".")


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _read_status_unfinished(status_file: Path) -> list[str]:
    if not status_file.exists():
        return []
    content = status_file.read_text(encoding="utf-8-sig")
    if "🛑" in content:
        return []
    return re.findall(r"^- \[ \] (.+)$", content, re.MULTILINE)


def _infer_model_agents(models: list[str], model_map: dict[str, str]) -> list[str]:
    agents: list[str] = []
    for model in models:
        model_lower = str(model or "").lower()
        for pattern, agent in model_map.items():
            if re.search(pattern, model_lower):
                if agent not in agents:
                    agents.append(agent)
                break
    return agents


def _normalize_agent_name(value: object) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in SUPPORTED_ASSIGNEES else ""


def _load_runtime_and_config(cwd: Path) -> tuple[dict, dict]:
    runtime = _load_json(cwd / ".cc-claude-codex" / "runtime.json")
    config = _load_json(cwd / ".vscode" / "ai-collab.json")
    return runtime, config


def _infer_current_agent(hook_input: dict, cwd: Path) -> str:
    for key in ("agent", "assignee", "ai"):
        candidate = _normalize_agent_name(hook_input.get(key))
        if candidate:
            return candidate

    model_candidate = str(hook_input.get("model") or "").strip()
    if model_candidate:
        inferred = _infer_model_agents([model_candidate], DEFAULT_MODEL_AGENT_MAP)
        if inferred:
            return inferred[0]

    runtime, config = _load_runtime_and_config(cwd)

    current_agent = _normalize_agent_name(runtime.get("current_agent"))
    if current_agent:
        return current_agent

    role_plan = runtime.get("role_plan")
    if isinstance(role_plan, dict):
        lead_agent = _normalize_agent_name(role_plan.get("lead_agent"))
        if lead_agent:
            return lead_agent

    models = runtime.get("models", []) if isinstance(runtime.get("models"), list) else []
    model_map = dict(DEFAULT_MODEL_AGENT_MAP)
    orchestration = config.get("agentOrchestration", {}) if isinstance(config, dict) else {}
    if isinstance(orchestration.get("modelAgentMap"), dict):
        model_map.update(orchestration.get("modelAgentMap", {}))
    inferred_agents = _infer_model_agents(models, model_map)
    if len(inferred_agents) == 1:
        return inferred_agents[0]
    if "codex" in inferred_agents:
        return "codex"
    return ""


def _task_belongs_to_agent(task: dict, current_agent: str) -> bool:
    if not current_agent:
        return True
    return normalize_assignee(task) == current_agent


def _read_state_active(state_file: Path, *, current_agent: str = "") -> list[str]:
    state = _load_json(state_file)
    tasks = state.get("tasks", {})
    active = []
    if isinstance(tasks, dict):
        for task_id, task in tasks.items():
            if not isinstance(task, dict):
                continue
            if not _task_belongs_to_agent(task, current_agent):
                continue
            if str(task.get("status", "")).lower() in ACTIVE_STATUSES:
                active.append(task_id)
    return active


def _resolve_existing_path(workspace: Path, raw_path: object) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    candidate = Path(raw_path.strip())
    if not candidate.is_absolute():
        candidate = workspace / candidate
    return candidate if candidate.exists() else None


def _patch_belongs_to_agent(
    *,
    patch: dict,
    task_assignees: dict[str, str],
    current_agent: str,
) -> bool:
    if not current_agent:
        return True
    patch_assignee = _normalize_agent_name(patch.get("assignee"))
    if patch_assignee:
        return patch_assignee == current_agent
    task_id = str(patch.get("task_id", "")).strip()
    return task_assignees.get(task_id, "") == current_agent


def _read_state_drift(state_file: Path, workspace: Path, *, current_agent: str = "") -> list[str]:
    state = _load_json(state_file)
    drifts: list[str] = []
    task_assignees: dict[str, str] = {}

    tasks = state.get("tasks", {})
    if isinstance(tasks, dict):
        for task_id, task in tasks.items():
            if not isinstance(task, dict):
                continue
            task_assignees[str(task_id)] = normalize_assignee(task)
            if not _task_belongs_to_agent(task, current_agent):
                continue
            status = str(task.get("status", "")).lower()
            if status in TASK_TERMINAL_STATUSES:
                continue
            expected_result = workspace / "collaboration" / "results" / f"RESULT_{task_id}.md"
            hinted_result = _resolve_existing_path(workspace, task.get("result_file"))
            if expected_result.exists() or hinted_result is not None:
                drifts.append(f"task {task_id} ({status})")

    patches = state.get("patches", {})
    if isinstance(patches, dict):
        for patch_id, patch in patches.items():
            if not isinstance(patch, dict):
                continue
            if not _patch_belongs_to_agent(
                patch=patch,
                task_assignees=task_assignees,
                current_agent=current_agent,
            ):
                continue
            status = str(patch.get("status", "")).lower()
            if status in PATCH_TERMINAL_STATUSES:
                continue

            hinted_result = _resolve_existing_path(workspace, patch.get("result_file"))
            task_id = str(patch.get("task_id", "")).strip()
            expected_result = (
                workspace / "collaboration" / "results" / f"RESULT_{task_id}.md"
                if task_id
                else None
            )

            if hinted_result is not None or (
                expected_result is not None and expected_result.exists()
            ):
                drifts.append(f"patch {patch_id} ({status})")

    return drifts


def _build_ack_command(task_id: str, assignee: str) -> str:
    return f"python3 -m ai_collab.cli ack --task-id {task_id} --ai {assignee} --status ok"


def _read_missing_explicit_ack(
    state_file: Path,
    workspace: Path,
    *,
    current_agent: str = "",
) -> list[dict[str, str]]:
    state = _load_json(state_file)
    _, _, ack_items = load_ack_bridge_state(workspace)
    missing: list[dict[str, str]] = []

    tasks = state.get("tasks", {})
    if not isinstance(tasks, dict):
        return missing

    for task_id, task in tasks.items():
        if not isinstance(task, dict):
            continue

        assignee = normalize_assignee(task)
        if current_agent and assignee != current_agent:
            continue
        status = str(task.get("status", "")).strip().lower()
        if not requires_explicit_ack(assignee) or status not in EXPLICIT_ACK_GUARD_STATUSES:
            continue
        if has_ack_evidence(ack_items, task_id=str(task_id), assignee=assignee):
            continue

        result_file = normalize_result_file(str(task_id), task)
        result_path = _resolve_existing_path(workspace, result_file)
        if status == "testing" and result_path is None:
            continue

        missing.append(
            {
                "task_id": str(task_id),
                "status": status,
                "command": _build_ack_command(str(task_id), assignee),
            }
        )

    return missing


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    cwd = _get_cwd(hook_input)
    status_file = cwd / ".cc-claude-codex" / "status.md"
    state_file = cwd / "logs" / "collaboration_state.json"
    current_agent = _infer_current_agent(hook_input, cwd)

    try:
        if current_agent:
            record_hook_session_observation(
                workspace=cwd,
                assignee=current_agent,
                hook_input=hook_input,
                source="stop_check",
                transport_mode="manual",
            )
        register_claude_session_from_hook(
            workspace=cwd,
            hook_input=hook_input,
            event_name="StopActive",
        )
    except Exception:
        pass

    unfinished = _read_status_unfinished(status_file)
    active_tasks = _read_state_active(state_file, current_agent=current_agent)
    drifts = _read_state_drift(state_file, cwd, current_agent=current_agent)
    missing_explicit_ack = _read_missing_explicit_ack(
        state_file,
        cwd,
        current_agent=current_agent,
    )

    if not unfinished and not active_tasks and not drifts and not missing_explicit_ack:
        try:
            register_claude_session_from_hook(
                workspace=cwd,
                hook_input=hook_input,
                event_name="Stop",
            )
        except Exception:
            pass
        sys.exit(0)

    lines = ["AI Collab Stop Hook: 检测到未完成事项，阻止结束会话。"]
    if current_agent:
        lines.append(f"当前会话 agent: `{current_agent}`")
    if unfinished:
        lines.append("未完成 status.md 任务:")
        lines.extend([f"  - {item}" for item in unfinished[:10]])
    if active_tasks:
        lines.append("当前会话活跃协作任务:")
        lines.extend([f"  - {task_id}" for task_id in active_tasks[:10]])
    if missing_explicit_ack:
        lines.append("当前会话显式 ACK 缺失:")
        lines.extend(
            [f"  - {item['task_id']} ({item['status']})" for item in missing_explicit_ack[:10]]
        )
        lines.append("请先原样执行以下命令并将 stdout 回复到会话中:")
        lines.extend([f"  {item['command']}" for item in missing_explicit_ack[:10]])
    if drifts:
        lines.append("检测到状态漂移（结果文件已存在但状态未闭环）:")
        lines.extend([f"  - {item}" for item in drifts[:10]])
        if not missing_explicit_ack:
            lines.append("建议先执行: python3 scripts/reconcile_state_drift.py --workspace . --apply")
    lines.append("请完成任务，或在 status.md 标记 🛑 后再结束。")

    print("\n".join(lines), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
