"""
动态 Agent 角色编排

根据操作人意图 + 模型配置 + 可用资源，动态决定主辅角色并尽量并行利用空闲 agent。
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

INTENT_KEYWORDS = {
    "architecture": ["架构", "设计", "architecture", "design", "方案", "重构策略", "security", "安全"],
    "implementation": ["实现", "开发", "编码", "implement", "feature", "修复", "bugfix", "fix", "refactor"],
    "testing": ["测试", "test", "覆盖率", "qa", "验证", "verification", "e2e"],
    "documentation": ["文档", "readme", "docs", "说明", "注释"],
    "research": ["调研", "research", "探索", "feasibility"],
    "operation": ["发布", "部署", "release", "运维", "ops", "监控"],
}


DEFAULT_INTENT_LEAD = {
    "architecture": ["codex", "claude_code", "codearts_agent"],
    "implementation": ["claude_code", "codex", "codearts_agent"],
    "testing": ["codearts_agent", "claude_code", "codex"],
    "documentation": ["codearts_agent", "codex", "claude_code"],
    "research": ["codex", "claude_code", "codearts_agent"],
    "operation": ["codex", "claude_code", "codearts_agent"],
}


DEFAULT_MODEL_AGENT_MAP = {
    r"claude": "claude_code",
    r"copilot": "codearts_agent",
    r"glm|codearts": "codearts_agent",
    r"gpt|codex|o\d|openai": "codex",
}


AGENT_CAPABILITIES = {
    "claude_code": ["architecture", "review", "security", "integration", "coordination"],
    "codex": ["implementation", "debug", "refactor", "automation", "performance"],
    "codearts_agent": ["completion", "test_generation", "documentation", "quick_fix"],
    "copilot": ["completion", "test_generation", "documentation", "quick_fix"],
    "user": ["decision", "prioritization", "acceptance"],
}


@dataclass
class RolePlan:
    intent_category: str
    lead_agent: str
    support_agents: list[str]
    available_agents: list[str]
    model_agents: list[str]
    utilization_plan: list[dict[str, Any]]
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_category": self.intent_category,
            "lead_agent": self.lead_agent,
            "support_agents": self.support_agents,
            "available_agents": self.available_agents,
            "model_agents": self.model_agents,
            "utilization_plan": self.utilization_plan,
            "reasons": self.reasons,
        }


class AgentOrchestrator:
    """按意图动态分配主辅 Agent。"""

    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path).resolve()
        self.config = self._load_project_config()

    def classify_intent(self, intent: str) -> str:
        text = (intent or "").strip().lower()
        if not text:
            return "implementation"

        for category, keywords in INTENT_KEYWORDS.items():
            if any(k.lower() in text for k in keywords):
                return category

        return "implementation"

    def infer_agents_from_models(self, models: list[str] | None) -> list[str]:
        models = models or []
        model_map = dict(DEFAULT_MODEL_AGENT_MAP)
        model_map.update(self.config.get("agentOrchestration", {}).get("modelAgentMap", {}))

        inferred: list[str] = []
        for model in models:
            model_lower = model.lower()
            mapped = None
            for pattern, agent in model_map.items():
                if re.search(pattern, model_lower):
                    mapped = agent
                    break
            if mapped and mapped not in inferred:
                inferred.append(mapped)
        return inferred

    def get_available_agents(self, model_agents: list[str] | None = None) -> list[str]:
        orchestration = self.config.get("agentOrchestration", {})
        enabled = list(self.config.get("enabledAIs", []))
        auto_detect = orchestration.get("autoDetectAgents", True)
        include_user = orchestration.get("includeUserAsOperator", True)

        if auto_detect:
            if shutil.which("codex") and "codex" not in enabled:
                enabled.append("codex")
            if shutil.which("claude") and "claude_code" not in enabled:
                enabled.append("claude_code")

        if model_agents:
            for agent in model_agents:
                if agent not in enabled:
                    enabled.append(agent)

        disabled = set(orchestration.get("disabledAgents", []))
        available = [a for a in enabled if a not in disabled]

        if include_user and "user" not in available:
            available.append("user")

        return sorted(set(available))

    def build_plan(
        self,
        intent: str,
        models: list[str] | None = None,
        operator: str = "user",
        force_lead: str | None = None,
    ) -> RolePlan:
        category = self.classify_intent(intent)
        model_agents = self.infer_agents_from_models(models)
        available = self.get_available_agents(model_agents=model_agents)

        orchestration = self.config.get("agentOrchestration", {})
        intent_lead_map = dict(DEFAULT_INTENT_LEAD)
        intent_lead_map.update(orchestration.get("intentLeadMap", {}))
        preferred = intent_lead_map.get(category, DEFAULT_INTENT_LEAD["implementation"])

        reasons = [f"intent={category}"]
        if model_agents:
            reasons.append(f"models=>agents={','.join(model_agents)}")

        lead = self._select_lead(
            preferred=preferred,
            available=available,
            operator=operator,
            force_lead=force_lead or orchestration.get("forceLeadAgent"),
            operator_first=orchestration.get("operatorFirst", False),
        )
        reasons.append(f"lead={lead}")

        support = [a for a in available if a != lead]
        utilization = self._build_utilization_plan(category=category, lead=lead, support=support)
        if support:
            reasons.append(f"parallel_support={','.join(support)}")
        else:
            reasons.append("parallel_support=none")

        return RolePlan(
            intent_category=category,
            lead_agent=lead,
            support_agents=support,
            available_agents=available,
            model_agents=model_agents,
            utilization_plan=utilization,
            reasons=reasons,
        )

    def _select_lead(
        self,
        preferred: list[str],
        available: list[str],
        operator: str,
        force_lead: str | None,
        operator_first: bool,
    ) -> str:
        if force_lead and force_lead in available:
            return force_lead

        if operator_first and operator in available:
            return operator

        for candidate in preferred:
            if candidate in available:
                return candidate

        if operator in available:
            return operator
        return available[0] if available else "user"

    def _build_utilization_plan(
        self, category: str, lead: str, support: list[str]
    ) -> list[dict[str, Any]]:
        role_tasks = {
            "architecture": {
                "codex": "输出架构方案与边界",
                "claude_code": "并行实现候选方案/脚手架",
                "codearts_agent": "补充测试样例与文档草案",
                "copilot": "补充测试样例与文档草案",
                "user": "确认方案取舍与优先级",
            },
            "implementation": {
                "claude_code": "主实现与重构",
                "codex": "并行代码审阅与风险检查",
                "codearts_agent": "并行补测试与样板代码",
                "copilot": "并行补测试与样板代码",
                "user": "确认业务行为与验收标准",
            },
            "testing": {
                "codearts_agent": "主导测试补齐与执行",
                "copilot": "主导测试补齐与执行",
                "codex": "修复失败用例与回归",
                "claude_code": "验证关键场景和边界",
                "user": "确认验收阈值与发布决策",
            },
            "documentation": {
                "codearts_agent": "主导文档初稿",
                "copilot": "主导文档初稿",
                "claude_code": "校验技术准确性",
                "codex": "同步示例代码与命令",
                "user": "确认对外口径与可读性",
            },
            "research": {
                "codex": "主导方案比较与路线收敛",
                "claude_code": "并行 PoC 与数据验证",
                "codearts_agent": "整理结论模板",
                "copilot": "整理结论模板",
                "user": "决策方向与投入级别",
            },
            "operation": {
                "codex": "主导发布策略与风险",
                "claude_code": "自动化脚本与回滚演练",
                "codearts_agent": "补充监控/告警配置",
                "copilot": "补充监控/告警配置",
                "user": "审批窗口与变更策略",
            },
        }
        mapping = role_tasks.get(category, role_tasks["implementation"])

        plan = [{"agent": lead, "role": "lead", "task": mapping.get(lead, "主导当前目标")}]
        for agent in support:
            plan.append({"agent": agent, "role": "support", "task": mapping.get(agent, "并行支持任务")})
        return plan

    def _load_project_config(self) -> dict[str, Any]:
        config_path = self.workspace / ".vscode" / "ai-collab.json"
        if not config_path.exists():
            return {}
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
