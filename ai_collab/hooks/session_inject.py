#!/usr/bin/env python3
# ruff: noqa: E402
"""
SessionStart Hook:
- 注入 .cc-claude-codex/status.md 摘要
- 注入 logs/collaboration_state.json 统计
- 注入动态角色建议（按配置 + 最近意图）
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_collab.session_auto_register import record_hook_session_observation
from ai_collab.session_autoregistration import register_claude_session_from_hook

DEFAULT_MODEL_AGENT_MAP = {
    r"claude": "claude_code",
    r"copilot": "codearts_agent",
    r"glm|codearts": "codearts_agent",
    r"gpt|codex|openai": "codex",
}


INTENT_KEYWORDS = {
    "architecture": ["架构", "design", "architecture", "安全", "security"],
    "implementation": ["实现", "开发", "feature", "fix", "bug", "refactor"],
    "testing": ["测试", "test", "coverage", "验证"],
    "documentation": ["文档", "docs", "readme"],
}


def _get_cwd(hook_input: dict) -> Path:
    cwd = hook_input.get("cwd")
    if isinstance(cwd, (str, bytes)):
        return Path(cwd)
    return Path(".")


def _normalize_supported_agent(value: object) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in {"claude_code", "codearts_agent", "codex"} else ""


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _classify_intent(text: str) -> str:
    lower = (text or "").lower()
    for cat, keywords in INTENT_KEYWORDS.items():
        if any(k.lower() in lower for k in keywords):
            return cat
    return "implementation"


def _infer_model_agents(models: list[str], model_map: dict[str, str]) -> list[str]:
    agents: list[str] = []
    for model in models:
        model_lower = model.lower()
        for pattern, agent in model_map.items():
            if re.search(pattern, model_lower):
                if agent not in agents:
                    agents.append(agent)
                break
    return agents


def _resolve_hook_assignee(hook_input: dict, model_agents: list[str]) -> str:
    for key in ("agent", "assignee", "ai"):
        candidate = _normalize_supported_agent(hook_input.get(key))
        if candidate:
            return candidate
    return model_agents[0] if model_agents else ""


def _available_agents(config: dict, model_agents: list[str]) -> list[str]:
    orchestration = config.get("agentOrchestration", {})
    enabled = list(config.get("enabledAIs", []))

    if orchestration.get("autoDetectAgents", True):
        if shutil.which("codex") and "codex" not in enabled:
            enabled.append("codex")
        if shutil.which("claude") and "claude_code" not in enabled:
            enabled.append("claude_code")

    for agent in model_agents:
        if agent not in enabled:
            enabled.append(agent)

    if orchestration.get("includeUserAsOperator", True) and "user" not in enabled:
        enabled.append("user")

    disabled = set(orchestration.get("disabledAgents", []))
    return sorted(a for a in set(enabled) if a not in disabled)


def _select_lead(intent_category: str, available: list[str], config: dict) -> str:
    intent_map = {
        "architecture": ["codex", "claude_code", "codearts_agent", "user"],
        "implementation": ["claude_code", "codex", "codearts_agent", "user"],
        "testing": ["codearts_agent", "claude_code", "codex", "user"],
        "documentation": ["codearts_agent", "codex", "claude_code", "user"],
    }
    orchestration = config.get("agentOrchestration", {})
    if isinstance(orchestration.get("forceLeadAgent"), str):
        forced = orchestration["forceLeadAgent"]
        if forced in available:
            return forced

    for candidate in intent_map.get(intent_category, intent_map["implementation"]):
        if candidate in available:
            return candidate
    return available[0] if available else "user"


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    cwd = _get_cwd(hook_input)

    status_file = cwd / ".cc-claude-codex" / "status.md"
    runtime_file = cwd / ".cc-claude-codex" / "runtime.json"
    state_file = cwd / "logs" / "collaboration_state.json"
    config_file = cwd / ".vscode" / "ai-collab.json"

    try:
        register_claude_session_from_hook(
            workspace=cwd,
            hook_input=hook_input,
            event_name="SessionStart",
        )
    except Exception:
        pass

    status_text = (
        status_file.read_text(encoding="utf-8-sig")
        if status_file.exists()
        else "(status.md not found)"
    )
    runtime = _load_json(runtime_file)
    state = _load_json(state_file)
    config = _load_json(config_file)

    tasks = state.get("tasks", {})
    active_count = 0
    completed_count = 0
    if isinstance(tasks, dict):
        for task in tasks.values():
            if isinstance(task, dict):
                if str(task.get("status", "")).lower() in {"completed", "failed", "cancelled"}:
                    completed_count += 1
                else:
                    active_count += 1

    intent = runtime.get("last_intent", "")
    models = runtime.get("models", []) if isinstance(runtime.get("models"), list) else []
    model_map = dict(DEFAULT_MODEL_AGENT_MAP)
    model_map.update(config.get("agentOrchestration", {}).get("modelAgentMap", {}))
    model_agents = _infer_model_agents(models, model_map)
    hook_assignee = _resolve_hook_assignee(hook_input, model_agents)
    available = _available_agents(config, model_agents)
    category = _classify_intent(intent)
    lead = _select_lead(category, available, config)
    support = [a for a in available if a != lead]

    try:
        if hook_assignee:
            record_hook_session_observation(
                workspace=cwd,
                assignee=hook_assignee,
                hook_input=hook_input,
                source="session_inject",
                transport_mode="manual",
            )
    except Exception:
        pass

    context = (
        "## AI Collab Session Context (Auto-injected)\n"
        f"- active_tasks: {active_count}\n"
        f"- completed_tasks: {completed_count}\n"
        f"- last_intent: {intent or 'N/A'}\n"
        f"- intent_category: {category}\n"
        f"- lead_agent: {lead}\n"
        f"- support_agents: {', '.join(support) if support else 'none'}\n"
        f"- model_agents: {', '.join(model_agents) if model_agents else 'N/A'}\n\n"
        "### status.md\n"
        f"{status_text}\n"
    )

    print(json.dumps({"additionalContext": context}, ensure_ascii=False))


if __name__ == "__main__":
    main()
