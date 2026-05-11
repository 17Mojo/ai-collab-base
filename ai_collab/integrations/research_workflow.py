"""
研究驱动开发工作流模块

利用 NotebookLM 的研究能力辅助任务拆解和决策。
提供:
- ResearchResult: 研究结果数据结构
- ResearchDrivenWorkflow: 研究驱动工作流类
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .notebooklm import NotebookLMIntegration


@dataclass
class ResearchResult:
    """研究结果数据结构。"""

    topic: str
    external_sources: list[dict[str, Any]] = field(default_factory=list)
    cross_notebook_insights: list[dict[str, Any]] = field(default_factory=list)
    feasibility_score: float = 0.0
    risks: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    researched_at: str = ""


class ResearchDrivenWorkflow:
    """研究驱动开发工作流。

    利用 NotebookLM 的研究能力辅助任务拆解和决策。
    """

    def __init__(
        self,
        *,
        notebook_id: str = "ai-collab-system-docs",
        mode: str = "FALLBACK",
    ):
        self.nlm = NotebookLMIntegration(notebook_id=notebook_id)
        self.notebook_id = notebook_id

    def research(self, topic: str) -> ResearchResult:
        """研究指定主题，收集相关源和见解。

        Args:
            topic: 研究主题

        Returns:
            研究结果
        """
        # 查询知识库获取技术上下文
        external_sources = []
        try:
            query_result = self.nlm.query_knowledge(topic)
            if "response" in query_result and query_result["response"]:
                external_sources.append(
                    {
                        "content": query_result["response"],
                        "source": "notebooklm",
                        "mode": query_result.get("mode", "unknown"),
                    }
                )
        except Exception:
            pass  # FALLBACK 模式可能不支持

        # 跨 notebook 查询 (通过 query_knowledge 模拟)
        cross_insights = []
        try:
            cross_query = f"跨领域见解: {topic}"
            cross_result = self.nlm.query_knowledge(cross_query)
            if "response" in cross_result and cross_result["response"]:
                cross_insights.append(
                    {
                        "content": cross_result["response"],
                        "source": "cross_notebook",
                        "dependencies": [],
                    }
                )
        except Exception:
            pass

        # 评估可行性
        feasibility_score = self._assess_feasibility(external_sources, cross_insights)

        # 识别风险
        risks = self._identify_risks(external_sources, cross_insights)

        # 识别依赖
        dependencies = self._identify_dependencies(external_sources, cross_insights)

        return ResearchResult(
            topic=topic,
            external_sources=external_sources,
            cross_notebook_insights=cross_insights,
            feasibility_score=feasibility_score,
            risks=risks,
            dependencies=dependencies,
            researched_at=datetime.now().isoformat(),
        )

    def synthesize(self, notebook_id: str | None = None) -> str:
        """综合 notebook 内容生成摘要。

        Args:
            notebook_id: Notebook ID (默认使用实例的 notebook_id)

        Returns:
            综合摘要
        """
        query = "总结所有源的关键见解"
        result = self.nlm.query_knowledge(query)
        return str(result.get("response", ""))

    def validate(self, query: str, expected_source: str) -> bool:
        """验证回答是否基于指定源。

        Args:
            query: 查询问题
            expected_source: 期望的源标识

        Returns:
            是否基于指定源
        """
        result = self.nlm.query_knowledge(query)
        sources = result.get("sources", [])
        return any(expected_source in str(s) for s in sources)

    def _assess_feasibility(
        self,
        external_sources: list[dict[str, Any]],
        cross_insights: list[dict[str, Any]],
    ) -> float:
        """评估技术可行性 (0-1)。"""
        score = 0.5  # 基础分
        score += min(0.2, len(external_sources) * 0.05)  # 外部源加分
        score += min(0.2, len(cross_insights) * 0.05)  # 跨 notebook 见解加分
        return min(1.0, score)

    def _identify_risks(
        self,
        external_sources: list[dict[str, Any]],
        cross_insights: list[dict[str, Any]],
    ) -> list[str]:
        """识别风险点。"""
        risks = []
        risk_keywords = ["风险", "警告", "注意", "限制", "deprecated", "breaking"]
        for source in external_sources:
            content = str(source.get("content", ""))
            for keyword in risk_keywords:
                if keyword in content.lower():
                    risks.append(f"检测到风险关键词: {keyword}")
        return risks

    def _identify_dependencies(
        self,
        external_sources: list[dict[str, Any]],
        cross_insights: list[dict[str, Any]],
    ) -> list[str]:
        """识别依赖关系。"""
        dependencies = []
        for insight in cross_insights:
            deps = insight.get("dependencies", [])
            dependencies.extend(deps)
        return list(set(dependencies))
