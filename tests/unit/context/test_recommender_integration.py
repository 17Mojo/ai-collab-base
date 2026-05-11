"""
Recommender integration tests.
"""

from __future__ import annotations

from ai_collab.context.learning import ActionType, ContextLearner
from ai_collab.context.recommender import ContextRecommender
from ai_collab.context.schema import Context, ScenarioType


class TestRecommenderLearningIntegration:
    """Test integration between recommender and learner."""

    def test_recommender_with_learner(self):
        """Test recommender using learner for personalization."""
        recommender = ContextRecommender()
        learner = ContextLearner()

        # Track user behavior
        learner.track_action(ActionType.OPEN, "src/main.py", ScenarioType.CODING)
        learner.track_action(ActionType.EDIT, "src/main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "src/utils.py", ScenarioType.CODING)

        # Get personalized scores
        main_score = learner.get_personalized_score("src/main.py", ScenarioType.CODING)
        utils_score = learner.get_personalized_score("src/utils.py", ScenarioType.CODING)

        # Use scores to adjust recommendations
        project_files = [
            "src/main.py",
            "src/utils.py",
            "src/models.py",
            "tests/test_main.py",
        ]

        recommendations = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=["src/main.py"],
            project_files=project_files,
            top_n=3,
        )

        # Verify recommendations
        assert len(recommendations) > 0
        # Personalized items should have higher scores
        assert main_score > 0 or utils_score > 0

    def test_learning_from_recommendations(self):
        """Test learning from user's recommendation choices."""
        recommender = ContextRecommender()
        learner = ContextLearner()

        # Get recommendations
        project_files = ["main.py", "utils.py", "test.py"]
        recommendations = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=["main.py"],
            project_files=project_files,
            top_n=3,
        )

        # Create history
        history = recommender.create_history(recommendations, ScenarioType.CODING)

        # User accepts some recommendations
        if len(recommendations) > 0:
            recommender.accept_recommendation(recommendations[0].rec_id, history.history_id)
            learner.track_action(
                ActionType.ACCEPT,
                recommendations[0].item_id,
                ScenarioType.CODING,
            )

        # Verify learning
        if len(recommendations) > 0:
            score = learner.get_frequency_score(recommendations[0].item_id)
            assert score > 0

    def test_sequence_based_recommendations(self):
        """Test recommendations based on sequence patterns."""
        learner = ContextLearner()

        # Learn sequence patterns
        for _ in range(3):
            learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
            learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)
            learner.track_action(ActionType.OPEN, "test.py", ScenarioType.CODING)

        # Get likely next items
        next_items = learner.get_likely_next_items("main.py", top_n=2)

        assert len(next_items) > 0
        # utils.py should be likely next
        assert any(item[0] == "utils.py" for item in next_items)

    def test_context_aware_recommendations(self):
        """Test context-aware recommendations."""
        recommender = ContextRecommender()
        learner = ContextLearner()

        # Track actions in different contexts
        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "paper.md", ScenarioType.RESEARCH)

        # Get context-specific scores
        coding_score = learner.get_personalized_score("main.py", ScenarioType.CODING)
        research_score = learner.get_personalized_score("paper.md", ScenarioType.RESEARCH)

        # Both should have positive scores in their contexts
        assert coding_score > 0
        assert research_score > 0

        # Get recommendations for each context
        coding_recs = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=[],
            project_files=["main.py", "paper.md"],
            top_n=2,
        )

        research_recs = recommender.recommend_files(
            scenario=ScenarioType.RESEARCH,
            active_files=[],
            project_files=["main.py", "paper.md"],
            top_n=2,
        )

        # Should have recommendations for both contexts
        assert len(coding_recs) > 0
        assert len(research_recs) > 0


class TestEnhancedRecommenderIntegration:
    """Test enhanced recommender with all features."""

    def test_complete_workflow(self):
        """Test complete recommendation workflow."""
        recommender = ContextRecommender()
        learner = ContextLearner()

        # Setup project
        project_files = [
            "src/main.py",
            "src/utils.py",
            "src/models.py",
            "tests/test_main.py",
            "docs/README.md",
        ]

        # Simulate user workflow
        actions = [
            (ActionType.OPEN, "src/main.py", ScenarioType.CODING),
            (ActionType.EDIT, "src/main.py", ScenarioType.CODING),
            (ActionType.OPEN, "src/utils.py", ScenarioType.CODING),
            (ActionType.OPEN, "src/main.py", ScenarioType.CODING),
            (ActionType.OPEN, "tests/test_main.py", ScenarioType.CODING),
        ]

        for action_type, item_id, context in actions:
            learner.track_action(action_type, item_id, context)

        # Get recommendations
        recommendations = recommender.get_recommendations(
            scenario=ScenarioType.CODING,
            active_files=["src/main.py"],
            project_files=project_files,
            current_context=Context(
                context_id="ctx-1",
                scenario=ScenarioType.CODING,
                name="Test",
            ),
            top_n=5,
        )

        # Verify all recommendation types
        assert "files" in recommendations
        assert "context" in recommendations
        assert "next_actions" in recommendations
        assert len(recommendations["files"]) > 0
        assert len(recommendations["next_actions"]) > 0

        # Get personalized scores
        top_items = learner.get_top_items(ScenarioType.CODING, top_n=3)
        assert len(top_items) > 0

    def test_multi_scenario_workflow(self):
        """Test workflow across multiple scenarios."""
        recommender = ContextRecommender()
        learner = ContextLearner()

        # Coding workflow
        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.EDIT, "main.py", ScenarioType.CODING)

        # Research workflow
        learner.track_action(ActionType.OPEN, "paper.md", ScenarioType.RESEARCH)
        learner.track_action(ActionType.EDIT, "paper.md", ScenarioType.RESEARCH)

        # Get recommendations for each scenario
        coding_recs = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=["main.py"],
            project_files=["main.py", "utils.py", "paper.md", "notes.md"],
            top_n=2,
        )

        research_recs = recommender.recommend_files(
            scenario=ScenarioType.RESEARCH,
            active_files=["paper.md"],
            project_files=["main.py", "utils.py", "paper.md", "notes.md"],
            top_n=2,
        )

        # Should have recommendations for both
        assert len(coding_recs) > 0
        assert len(research_recs) > 0

        # Get personalized scores
        coding_score = learner.get_personalized_score("main.py", ScenarioType.CODING)
        research_score = learner.get_personalized_score("paper.md", ScenarioType.RESEARCH)

        assert coding_score > 0
        assert research_score > 0


class TestRecommendationAccuracy:
    """Test recommendation accuracy metrics."""

    def test_frequency_accuracy(self):
        """Test frequency-based recommendation accuracy."""
        learner = ContextLearner()

        # Create clear frequency pattern
        for _ in range(10):
            learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        for _ in range(5):
            learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "test.py", ScenarioType.CODING)

        # Get top items
        top_items = learner.get_top_items(ScenarioType.CODING, top_n=3)

        # main.py should be top
        assert len(top_items) > 0
        assert top_items[0][0] == "main.py"
        assert top_items[0][1] > 0.5  # High score

    def test_sequence_accuracy(self):
        """Test sequence-based recommendation accuracy."""
        learner = ContextLearner()

        # Create strong sequence pattern
        for _ in range(10):
            learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
            learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)

        # Get likely next items
        next_items = learner.get_likely_next_items("main.py", top_n=1)

        # utils.py should be highly likely
        assert len(next_items) > 0
        assert next_items[0][0] == "utils.py"
        assert next_items[0][1] > 0.9  # Very high probability

    def test_context_relevance_accuracy(self):
        """Test context relevance accuracy."""
        learner = ContextLearner()

        # Track actions in specific context
        for _ in range(5):
            learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
            learner.track_action(ActionType.EDIT, "main.py", ScenarioType.CODING)

        # Track actions in different context
        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.RESEARCH)

        # Get context-specific score
        coding_score = learner.get_personalized_score("main.py", ScenarioType.CODING)
        research_score = learner.get_personalized_score("main.py", ScenarioType.RESEARCH)

        # Should have higher score in coding context
        assert coding_score > research_score
        assert coding_score > 0.5
