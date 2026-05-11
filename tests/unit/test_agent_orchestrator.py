"""
AgentOrchestrator 单元测试
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_collab.agent_orchestrator import AgentOrchestrator


def _write_config(workspace: Path, config: dict):
    vscode_dir = workspace / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    (vscode_dir / "ai-collab.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def test_plan_prefers_claude_for_implementation(tmp_path: Path):
    _write_config(
        tmp_path,
        {
            "enabledAIs": ["claude_code", "codearts_agent", "codex"],
            "agentOrchestration": {"autoDetectAgents": False},
        },
    )
    orchestrator = AgentOrchestrator(str(tmp_path))
    plan = orchestrator.build_plan(intent="实现登录接口并修复 bug", models=["gpt-5-codex"])
    assert plan.lead_agent == "claude_code"
    assert "codex" in plan.support_agents


def test_force_lead_overrides_dynamic(tmp_path: Path):
    _write_config(
        tmp_path,
        {
            "enabledAIs": ["claude_code", "codearts_agent", "codex"],
            "agentOrchestration": {"autoDetectAgents": False},
        },
    )
    orchestrator = AgentOrchestrator(str(tmp_path))
    plan = orchestrator.build_plan(intent="补测试", force_lead="claude_code")
    assert plan.lead_agent == "claude_code"


def test_operator_first_allows_user_lead(tmp_path: Path):
    _write_config(
        tmp_path,
        {
            "enabledAIs": ["claude_code", "codearts_agent", "codex"],
            "agentOrchestration": {"autoDetectAgents": False, "operatorFirst": True, "includeUserAsOperator": True},
        },
    )
    orchestrator = AgentOrchestrator(str(tmp_path))
    plan = orchestrator.build_plan(intent="架构设计", operator="user")
    assert plan.lead_agent == "user"
