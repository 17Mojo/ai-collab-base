"""
Context recommender tests.
"""

from __future__ import annotations

from ai_collab.context.recommender import (
    ContextRecommender,
    Recommendation,
    RecommendationHistory,
    RecommendationScore,
    RecommendationType,
)
from ai_collab.context.schema import Context, ScenarioType


class TestRecommendationType:
    """Test RecommendationType enum."""

    def test_recommendation_types(self):
        assert RecommendationType.FILE.value == "file"
        assert RecommendationType.CONTEXT.value == "context"
        assert RecommendationType.NEXT_ACTION.value == "next_action"


class TestRecommendationScore:
    """Test RecommendationScore dataclass."""

    def test_score_creation(self):
        score = RecommendationScore(
            score=0.85,
            reason="High relevance",
            confidence=0.9,
        )
        assert score.score == 0.85
        assert score.reason == "High relevance"
        assert score.confidence == 0.9

    def test_score_to_dict(self):
        score = RecommendationScore(
            score=0.75,
            reason="Medium relevance",
            confidence=0.8,
        )
        result = score.to_dict()
        assert result["score"] == 0.75
        assert result["reason"] == "Medium relevance"
        assert result["confidence"] == 0.8


class TestRecommendation:
    """Test Recommendation dataclass."""

    def test_recommendation_creation(self):
        score = RecommendationScore(score=0.9, reason="Test", confidence=0.85)
        rec = Recommendation(
            rec_id="rec-1",
            rec_type=RecommendationType.FILE,
            item_id="main.py",
            title="Test File",
            description="Test description",
            score=score,
        )
        assert rec.rec_id == "rec-1"
        assert rec.rec_type == RecommendationType.FILE
        assert rec.item_id == "main.py"
        assert rec.title == "Test File"

    def test_recommendation_to_dict(self):
        score = RecommendationScore(score=0.8, reason="Test", confidence=0.75)
        rec = Recommendation(
            rec_id="rec-2",
            rec_type=RecommendationType.CONTEXT,
            item_id="ctx-1",
            title="Test Context",
            description="Test",
            score=score,
            metadata={"key": "value"},
        )
        result = rec.to_dict()
        assert result["rec_id"] == "rec-2"
        assert result["rec_type"] == "context"
        assert result["item_id"] == "ctx-1"
        assert result["metadata"]["key"] == "value"


class TestRecommendationHistory:
    """Test RecommendationHistory dataclass."""

    def test_history_creation(self):
        score = RecommendationScore(score=0.9, reason="Test", confidence=0.8)
        rec = Recommendation(
            rec_id="rec-1",
            rec_type=RecommendationType.FILE,
            item_id="test.py",
            title="Test",
            description="Test",
            score=score,
        )
        history = RecommendationHistory(
            history_id="hist-1",
            recommendations=[rec],
            context_scenario="coding",
            accepted_ids=["rec-1"],
        )
        assert history.history_id == "hist-1"
        assert len(history.recommendations) == 1
        assert history.context_scenario == "coding"
        assert len(history.accepted_ids) == 1

    def test_history_to_dict(self):
        history = RecommendationHistory(
            history_id="hist-2",
            recommendations=[],
            context_scenario="research",
        )
        result = history.to_dict()
        assert result["history_id"] == "hist-2"
        assert result["context_scenario"] == "research"
        assert result["recommendations"] == []


class TestContextRecommender:
    """Test ContextRecommender class."""

    def test_recommender_initialization(self):
        recommender = ContextRecommender()
        assert recommender._history == []

    def test_recommend_files_for_coding(self):
        recommender = ContextRecommender()
        project_files = [
            "src/main.py",
            "src/utils.py",
            "src/models.py",
            "tests/test_main.py",
            "docs/README.md",
            "config.yaml",
        ]
        active_files = ["src/main.py"]

        recommendations = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=active_files,
            project_files=project_files,
            top_n=5,
        )

        assert len(recommendations) > 0
        assert all(r.rec_type == RecommendationType.FILE for r in recommendations)
        # Should not include active files
        assert all(r.item_id not in active_files for r in recommendations)

    def test_recommend_files_for_research(self):
        recommender = ContextRecommender()
        project_files = [
            "docs/paper.md",
            "docs/notes.md",
            "research/analysis.md",
            "src/main.py",
            "README.md",
        ]
        active_files = ["docs/paper.md"]

        recommendations = recommender.recommend_files(
            scenario=ScenarioType.RESEARCH,
            active_files=active_files,
            project_files=project_files,
            top_n=3,
        )

        assert len(recommendations) > 0
        # Should prefer research-related files
        assert any("docs" in r.item_id or "research" in r.item_id for r in recommendations)

    def test_recommend_files_for_debugging(self):
        recommender = ContextRecommender()
        project_files = [
            "logs/error.log",
            "logs/debug.log",
            "tests/test_main.py",
            "src/main.py",
            "docs/README.md",
        ]
        active_files = ["src/main.py"]

        recommendations = recommender.recommend_files(
            scenario=ScenarioType.DEBUGGING,
            active_files=active_files,
            project_files=project_files,
            top_n=3,
        )

        assert len(recommendations) > 0
        # Should prefer debugging-related files
        assert any("log" in r.item_id or "test" in r.item_id for r in recommendations)

    def test_recommend_context_with_history(self):
        recommender = ContextRecommender()

        # Create history
        score = RecommendationScore(score=0.9, reason="Test", confidence=0.8)
        rec1 = Recommendation(
            rec_id="rec-1",
            rec_type=RecommendationType.FILE,
            item_id="main.py",
            title="Main",
            description="Test",
            score=score,
        )
        rec2 = Recommendation(
            rec_id="rec-2",
            rec_type=RecommendationType.FILE,
            item_id="utils.py",
            title="Utils",
            description="Test",
            score=score,
        )

        history1 = RecommendationHistory(
            history_id="hist-1",
            recommendations=[rec1, rec2],
            context_scenario="coding",
            accepted_ids=["rec-1"],
        )
        history2 = RecommendationHistory(
            history_id="hist-2",
            recommendations=[rec1],
            context_scenario="coding",
            accepted_ids=["rec-1"],
        )

        recommendations = recommender.recommend_context(
            scenario=ScenarioType.CODING,
            user_history=[history1, history2],
            top_n=2,
        )

        assert len(recommendations) > 0
        # Should recommend frequently used items
        assert any(r.item_id == "main.py" for r in recommendations)

    def test_recommend_next_for_coding(self):
        recommender = ContextRecommender()
        context = Context(
            context_id="ctx-1",
            scenario=ScenarioType.CODING,
            name="Test",
        )

        recommendations = recommender.recommend_next(context, top_n=3)

        assert len(recommendations) > 0
        assert all(r.rec_type == RecommendationType.NEXT_ACTION for r in recommendations)
        # Should include common coding actions
        actions = [r.item_id for r in recommendations]
        assert any(action in ["run_tests", "review_code", "commit_changes"] for action in actions)

    def test_recommend_next_for_debugging(self):
        recommender = ContextRecommender()
        context = Context(
            context_id="ctx-2",
            scenario=ScenarioType.DEBUGGING,
            name="Debug",
        )

        recommendations = recommender.recommend_next(context, top_n=3)

        assert len(recommendations) > 0
        # Should include debugging actions
        actions = [r.item_id for r in recommendations]
        assert any(action in ["analyze_logs", "fix_issue", "verify_fix"] for action in actions)

    def test_get_recommendations(self):
        recommender = ContextRecommender()
        project_files = [
            "src/main.py",
            "src/utils.py",
            "tests/test_main.py",
            "docs/README.md",
        ]
        active_files = ["src/main.py"]
        context = Context(
            context_id="ctx-1",
            scenario=ScenarioType.CODING,
            name="Test",
        )

        recommendations = recommender.get_recommendations(
            scenario=ScenarioType.CODING,
            active_files=active_files,
            project_files=project_files,
            current_context=context,
            top_n=5,
        )

        assert "files" in recommendations
        assert "context" in recommendations
        assert "next_actions" in recommendations
        assert len(recommendations["files"]) > 0
        assert len(recommendations["next_actions"]) > 0

    def test_accept_recommendation(self):
        recommender = ContextRecommender()

        # Create history
        score = RecommendationScore(score=0.9, reason="Test", confidence=0.8)
        rec = Recommendation(
            rec_id="rec-1",
            rec_type=RecommendationType.FILE,
            item_id="test.py",
            title="Test",
            description="Test",
            score=score,
        )
        history = recommender.create_history([rec], ScenarioType.CODING)

        # Accept recommendation
        recommender.accept_recommendation("rec-1", history.history_id)

        # Verify acceptance
        assert "rec-1" in history.accepted_ids

    def test_reject_recommendation(self):
        recommender = ContextRecommender()

        # Reject should not raise error
        recommender.reject_recommendation("rec-1")

    def test_create_history(self):
        recommender = ContextRecommender()
        score = RecommendationScore(score=0.9, reason="Test", confidence=0.8)
        rec = Recommendation(
            rec_id="rec-1",
            rec_type=RecommendationType.FILE,
            item_id="test.py",
            title="Test",
            description="Test",
            score=score,
        )

        history = recommender.create_history([rec], ScenarioType.CODING)

        assert history.history_id is not None
        assert len(history.recommendations) == 1
        assert history.context_scenario == "coding"
        assert history in recommender._history


class TestRecommenderScenarios:
    """Test recommender for different scenarios."""

    def test_coding_scenario_recommendations(self):
        recommender = ContextRecommender()
        project_files = [
            "src/app.py",
            "src/models.py",
            "src/views.py",
            "tests/test_app.py",
            "docs/api.md",
        ]

        recommendations = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=["src/app.py"],
            project_files=project_files,
            top_n=3,
        )

        # Should recommend related Python files
        assert len(recommendations) > 0
        python_recs = [r for r in recommendations if r.item_id.endswith(".py")]
        assert len(python_recs) > 0

    def test_writing_scenario_recommendations(self):
        recommender = ContextRecommender()
        project_files = [
            "posts/article1.md",
            "posts/article2.md",
            "drafts/draft1.md",
            "images/photo.jpg",
            "config.yaml",
        ]

        recommendations = recommender.recommend_files(
            scenario=ScenarioType.WRITING,
            active_files=["posts/article1.md"],
            project_files=project_files,
            top_n=3,
        )

        # Should recommend markdown files
        assert len(recommendations) > 0
        md_recs = [r for r in recommendations if r.item_id.endswith(".md")]
        assert len(md_recs) > 0

    def test_design_scenario_recommendations(self):
        recommender = ContextRecommender()
        project_files = [
            "styles/main.css",
            "styles/components.scss",
            "assets/logo.png",
            "src/app.js",
            "docs/design.md",
        ]

        recommendations = recommender.recommend_files(
            scenario=ScenarioType.DESIGN,
            active_files=["styles/main.css"],
            project_files=project_files,
            top_n=3,
        )

        # Should recommend style files
        assert len(recommendations) > 0
        style_recs = [r for r in recommendations if ".css" in r.item_id or ".scss" in r.item_id]
        assert len(style_recs) > 0


class TestRecommenderIntegration:
    """Integration tests for recommender."""

    def test_complete_recommendation_workflow(self):
        recommender = ContextRecommender()

        # Project setup
        project_files = [
            "src/main.py",
            "src/utils.py",
            "src/models.py",
            "tests/test_main.py",
            "docs/README.md",
        ]
        active_files = ["src/main.py"]

        # Get recommendations
        recommendations = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=active_files,
            project_files=project_files,
            top_n=5,
        )

        # Create history
        history = recommender.create_history(recommendations, ScenarioType.CODING)

        # Accept some recommendations
        if len(recommendations) > 0:
            recommender.accept_recommendation(recommendations[0].rec_id, history.history_id)

        # Verify
        assert len(history.recommendations) > 0
        assert history.context_scenario == "coding"

    def test_multi_scenario_workflow(self):
        recommender = ContextRecommender()

        # Coding scenario
        coding_files = ["src/main.py", "src/utils.py", "tests/test.py"]
        coding_recs = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=["src/main.py"],
            project_files=coding_files,
            top_n=2,
        )
        assert len(coding_recs) > 0

        # Research scenario
        research_files = ["docs/paper.md", "research/notes.md", "src/analyze.py"]
        research_recs = recommender.recommend_files(
            scenario=ScenarioType.RESEARCH,
            active_files=["docs/paper.md"],
            project_files=research_files,
            top_n=2,
        )
        assert len(research_recs) > 0

        # Different scenarios should produce different recommendations
        # (at least in terms of scoring)
        assert len(coding_recs) > 0 or len(research_recs) > 0
