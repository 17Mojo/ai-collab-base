"""
Week 2 Integration Tests - End-to-End Validation
"""

from __future__ import annotations

from ai_collab.context.enhanced import ContextEnhancer, ScenarioContextBuilder
from ai_collab.context.learning import ActionType, ContextLearner
from ai_collab.context.recommender import ContextRecommender, RecommendationType
from ai_collab.context.schema import Context, FileContext, ScenarioType


class TestWeek2Integration:
    """Week 2 complete integration tests."""

    def test_complete_context_workflow(self):
        """Test complete context management workflow."""
        # 1. Create context
        context = Context(
            context_id="test-ctx",
            scenario=ScenarioType.CODING,
            name="Test Context",
        )

        # 2. Add files
        context.add_file(FileContext(path="main.py", language="python", size=100))
        context.add_file(FileContext(path="utils.py", language="python", size=50))

        # 3. Verify context
        assert len(context.file_contexts) == 2
        assert context.scenario == ScenarioType.CODING

    def test_recommendation_engine_workflow(self):
        """Test recommendation engine complete workflow."""
        recommender = ContextRecommender()

        # Get recommendations
        recommendations = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=["main.py"],
            project_files=["main.py", "utils.py", "test.py", "README.md"],
            top_n=3,
        )

        # Verify recommendations
        assert len(recommendations) > 0
        assert all(r.rec_type == RecommendationType.FILE for r in recommendations)

    def test_learning_workflow(self):
        """Test learning module complete workflow."""
        learner = ContextLearner()

        # Track actions
        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.EDIT, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)

        # Get personalized scores
        score = learner.get_personalized_score("main.py", ScenarioType.CODING)
        assert score > 0

        # Get top items
        top_items = learner.get_top_items(ScenarioType.CODING, top_n=3)
        assert len(top_items) > 0

    def test_enhanced_context_workflow(self):
        """Test enhanced context workflow."""
        enhancer = ContextEnhancer()
        builder = ScenarioContextBuilder(enhancer=enhancer)

        # Build context
        context = builder.build_for_coding(
            base_files=["main.py", "utils.py"],
        )

        # Verify context
        assert context.scenario == ScenarioType.CODING
        assert len(context.file_contexts) == 2

        # Extract summary
        summary = enhancer.extract_context_summary(context)
        assert summary["scenario"] == "coding"
        assert summary["file_count"] == 2

    def test_complete_recommendation_pipeline(self):
        """Test complete recommendation pipeline."""
        recommender = ContextRecommender()
        learner = ContextLearner()

        # Setup
        project_files = [
            "src/main.py",
            "src/utils.py",
            "src/models.py",
            "tests/test_main.py",
            "docs/README.md",
        ]

        # Track user behavior
        learner.track_action(ActionType.OPEN, "src/main.py", ScenarioType.CODING)
        learner.track_action(ActionType.EDIT, "src/main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "src/utils.py", ScenarioType.CODING)

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

        # Get personalized scores
        top_items = learner.get_top_items(ScenarioType.CODING, top_n=3)
        assert len(top_items) > 0


class TestQualityAssurance:
    """Quality assurance tests."""

    def test_all_scenarios_supported(self):
        """Test all scenario types are supported."""
        recommender = ContextRecommender()

        scenarios = [
            ScenarioType.CODING,
            ScenarioType.RESEARCH,
            ScenarioType.WRITING,
            ScenarioType.DEBUGGING,
            ScenarioType.DESIGN,
            ScenarioType.PROJECT_PLANNING,
            ScenarioType.DOCUMENTATION,
        ]

        for scenario in scenarios:
            recommendations = recommender.recommend_files(
                scenario=scenario,
                active_files=[],
                project_files=["test.py", "test.md"],
                top_n=2,
            )
            # Should not raise errors for any scenario
            assert isinstance(recommendations, list)

    def test_error_handling(self):
        """Test error handling."""
        recommender = ContextRecommender()
        learner = ContextLearner()

        # Empty inputs should not crash
        recommendations = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=[],
            project_files=[],
            top_n=5,
        )
        assert recommendations == []

        # Unknown items should return 0 score
        score = learner.get_frequency_score("unknown.py")
        assert score == 0.0

    def test_data_consistency(self):
        """Test data consistency."""
        context = Context(
            context_id="test-ctx",
            scenario=ScenarioType.CODING,
            name="Test",
        )

        # Add and remove files
        context.add_file(FileContext(path="main.py", language="python", size=100))
        assert len(context.file_contexts) == 1

        # Serialize and deserialize
        data = context.to_dict()
        restored = Context.from_dict(data)

        assert restored.context_id == context.context_id
        assert restored.scenario == context.scenario
        assert len(restored.file_contexts) == len(context.file_contexts)

    def test_performance_benchmarks(self):
        """Test performance benchmarks."""
        import time

        recommender = ContextRecommender()
        learner = ContextLearner()

        # Generate large dataset
        project_files = [f"file{i}.py" for i in range(100)]

        # Measure recommendation time
        start = time.time()
        recommendations = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=["file0.py"],
            project_files=project_files,
            top_n=10,
        )
        elapsed = time.time() - start

        # Should complete in reasonable time (< 1 second)
        assert elapsed < 1.0
        assert len(recommendations) <= 10

        # Measure learning time
        start = time.time()
        for i in range(100):
            learner.track_action(ActionType.OPEN, f"file{i}.py", ScenarioType.CODING)
        elapsed = time.time() - start

        # Should complete in reasonable time (< 1 second)
        assert elapsed < 1.0


class TestAPIIntegration:
    """API integration tests."""

    def test_context_api(self):
        """Test context API."""
        context = Context(
            context_id="api-test",
            scenario=ScenarioType.CODING,
            name="API Test",
        )

        # Test API methods
        assert context.context_id == "api-test"
        assert context.scenario == ScenarioType.CODING
        assert context.name == "API Test"

        # Test file operations
        context.add_file(FileContext(path="test.py", language="python", size=100))
        assert len(context.file_contexts) == 1

        # Test serialization
        data = context.to_dict()
        assert isinstance(data, dict)
        assert data["context_id"] == "api-test"

    def test_recommender_api(self):
        """Test recommender API."""
        recommender = ContextRecommender()

        # Test API methods
        recommendations = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=[],
            project_files=["test.py"],
            top_n=1,
        )
        assert isinstance(recommendations, list)

        # Test history creation
        history = recommender.create_history(recommendations, ScenarioType.CODING)
        assert history.history_id is not None
        assert history.context_scenario == "coding"

    def test_learner_api(self):
        """Test learner API."""
        learner = ContextLearner()

        # Test API methods
        action = learner.track_action(
            action_type=ActionType.OPEN,
            item_id="test.py",
            context=ScenarioType.CODING,
        )
        assert action.action_id is not None

        # Test score methods
        score = learner.get_frequency_score("test.py")
        assert 0 <= score <= 1.0

        # Test stats
        stats = learner.get_stats()
        assert stats["total_actions"] == 1
        assert stats["unique_items"] == 1


class TestWeek2FinalValidation:
    """Final validation for Week 2."""

    def test_all_modules_importable(self):
        """Test all modules can be imported."""
        # Should not raise ImportError
        from ai_collab.context import enhanced, learning, recommender, schema

        assert schema is not None
        assert recommender is not None
        assert learning is not None
        assert enhanced is not None

    def test_all_classes_instantiable(self):
        """Test all classes can be instantiated."""
        context = Context(
            context_id="test",
            scenario=ScenarioType.CODING,
            name="Test",
        )
        recommender = ContextRecommender()
        learner = ContextLearner()
        enhancer = ContextEnhancer()
        builder = ScenarioContextBuilder()

        assert context is not None
        assert recommender is not None
        assert learner is not None
        assert enhancer is not None
        assert builder is not None

    def test_week2_functionality_complete(self):
        """Test Week 2 functionality is complete."""
        # Context management
        context = Context(
            context_id="week2-test",
            scenario=ScenarioType.CODING,
            name="Week 2 Test",
        )
        context.add_file(FileContext(path="main.py", language="python", size=100))

        # Recommendation engine
        recommender = ContextRecommender()
        recommendations = recommender.recommend_files(
            scenario=ScenarioType.CODING,
            active_files=["main.py"],
            project_files=["main.py", "utils.py"],
            top_n=1,
        )

        # Learning module
        learner = ContextLearner()
        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        score = learner.get_personalized_score("main.py", ScenarioType.CODING)

        # Enhanced context
        enhancer = ContextEnhancer()
        summary = enhancer.extract_context_summary(context)

        # All should work without errors
        assert len(context.file_contexts) == 1
        assert isinstance(recommendations, list)
        assert score >= 0
        assert summary["scenario"] == "coding"
