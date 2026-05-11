"""
单元测试: ResearchDrivenWorkflow 类

测试研究驱动开发工作流功能
"""

import pytest

from ai_collab.integrations.research_workflow import ResearchDrivenWorkflow, ResearchResult


class TestResearchResult:
    """测试 ResearchResult 数据结构"""

    def test_default_values(self):
        """默认值应正确初始化"""
        result = ResearchResult(topic="测试主题")

        assert result.topic == "测试主题"
        assert result.external_sources == []
        assert result.cross_notebook_insights == []
        assert result.feasibility_score == 0.0
        assert result.risks == []
        assert result.dependencies == []
        assert result.researched_at == ""

    def test_custom_values(self):
        """自定义值应正确设置"""
        result = ResearchResult(
            topic="认证系统",
            external_sources=[{"content": "OAuth2 规范"}],
            cross_notebook_insights=[{"content": "安全最佳实践"}],
            feasibility_score=0.8,
            risks=["Token 过期风险"],
            dependencies=["oauthlib"],
            researched_at="2026-04-17T08:00:00",
        )

        assert result.topic == "认证系统"
        assert len(result.external_sources) == 1
        assert result.feasibility_score == 0.8
        assert len(result.risks) == 1
        assert len(result.dependencies) == 1


class TestResearchDrivenWorkflow:
    """测试 ResearchDrivenWorkflow 类"""

    @pytest.fixture
    def workflow(self):
        """创建工作流实例"""
        return ResearchDrivenWorkflow()

    def test_init_default(self):
        """默认初始化应正确"""
        wf = ResearchDrivenWorkflow()
        assert wf.notebook_id == "ai-collab-system-docs"

    def test_init_custom_notebook(self):
        """自定义 notebook_id 应正确"""
        wf = ResearchDrivenWorkflow(notebook_id="custom-notebook")
        assert wf.notebook_id == "custom-notebook"

    def test_research_returns_result(self, workflow):
        """research() 应返回 ResearchResult"""
        result = workflow.research("系统架构")

        assert isinstance(result, ResearchResult)
        assert result.topic == "系统架构"
        assert result.researched_at != ""

    def test_research_has_feasibility_score(self, workflow):
        """research() 结果应包含可行性评分"""
        result = workflow.research("数据库设计")

        assert 0.0 <= result.feasibility_score <= 1.0

    def test_research_has_risks(self, workflow):
        """research() 结果应包含风险列表"""
        result = workflow.research("API 设计")

        assert isinstance(result.risks, list)

    def test_research_has_dependencies(self, workflow):
        """research() 结果应包含依赖列表"""
        result = workflow.research("前端开发")

        assert isinstance(result.dependencies, list)

    def test_synthesize_returns_string(self, workflow):
        """synthesize() 应返回字符串"""
        result = workflow.synthesize()

        assert isinstance(result, str)

    def test_synthesize_custom_notebook(self, workflow):
        """synthesize() 应支持自定义 notebook_id"""
        result = workflow.synthesize(notebook_id="custom-notebook")

        assert isinstance(result, str)

    def test_validate_returns_bool(self, workflow):
        """validate() 应返回布尔值"""
        result = workflow.validate("系统架构", "document1.pdf")

        assert isinstance(result, bool)


class TestAssessFeasibility:
    """测试 _assess_feasibility 方法"""

    def test_base_score(self):
        """无源时基础分为 0.5"""
        wf = ResearchDrivenWorkflow()
        score = wf._assess_feasibility([], [])

        assert score == 0.5

    def test_external_sources_bonus(self):
        """外部源应加分"""
        wf = ResearchDrivenWorkflow()
        sources = [{"content": f"源{i}"} for i in range(4)]
        score = wf._assess_feasibility(sources, [])

        assert score > 0.5

    def test_cross_insights_bonus(self):
        """跨 notebook 见解应加分"""
        wf = ResearchDrivenWorkflow()
        insights = [{"content": f"见解{i}"} for i in range(4)]
        score = wf._assess_feasibility([], insights)

        assert score > 0.5

    def test_max_score_is_one(self):
        """评分上限为 1.0"""
        wf = ResearchDrivenWorkflow()
        sources = [{"content": f"源{i}"} for i in range(100)]
        insights = [{"content": f"见解{i}"} for i in range(100)]
        score = wf._assess_feasibility(sources, insights)

        assert score <= 1.0


class TestIdentifyRisks:
    """测试 _identify_risks 方法"""

    def test_no_risks(self):
        """无风险关键词时应返回空列表"""
        wf = ResearchDrivenWorkflow()
        sources = [{"content": "正常内容"}]
        risks = wf._identify_risks(sources, [])

        assert risks == []

    def test_detects_risk_keywords(self):
        """应检测风险关键词"""
        wf = ResearchDrivenWorkflow()
        sources = [{"content": "注意: 此操作有风险"}]
        risks = wf._identify_risks(sources, [])

        assert len(risks) > 0

    def test_detects_deprecated(self):
        """应检测 deprecated 关键词"""
        wf = ResearchDrivenWorkflow()
        sources = [{"content": "This API is deprecated"}]
        risks = wf._identify_risks(sources, [])

        assert len(risks) > 0

    def test_detects_breaking(self):
        """应检测 breaking 关键词"""
        wf = ResearchDrivenWorkflow()
        sources = [{"content": "Breaking change in v2"}]
        risks = wf._identify_risks(sources, [])

        assert len(risks) > 0


class TestIdentifyDependencies:
    """测试 _identify_dependencies 方法"""

    def test_no_dependencies(self):
        """无依赖时应返回空列表"""
        wf = ResearchDrivenWorkflow()
        deps = wf._identify_dependencies([], [])

        assert deps == []

    def test_extracts_dependencies(self):
        """应从见解中提取依赖"""
        wf = ResearchDrivenWorkflow()
        insights = [
            {"dependencies": ["pytest", "fastapi"]},
            {"dependencies": ["click"]},
        ]
        deps = wf._identify_dependencies([], insights)

        assert "pytest" in deps
        assert "fastapi" in deps
        assert "click" in deps

    def test_deduplicates_dependencies(self):
        """应去重依赖"""
        wf = ResearchDrivenWorkflow()
        insights = [
            {"dependencies": ["pytest"]},
            {"dependencies": ["pytest"]},
        ]
        deps = wf._identify_dependencies([], insights)

        assert deps.count("pytest") == 1
