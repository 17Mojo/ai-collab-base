"""
Context learning tests.
"""

from __future__ import annotations

from datetime import datetime

from ai_collab.context.learning import ActionType, BehaviorPattern, ContextLearner, UserAction
from ai_collab.context.schema import ScenarioType


class TestActionType:
    """Test ActionType enum."""

    def test_action_types(self):
        assert ActionType.VIEW.value == "view"
        assert ActionType.OPEN.value == "open"
        assert ActionType.EDIT.value == "edit"
        assert ActionType.DELETE.value == "delete"
        assert ActionType.ACCEPT.value == "accept"
        assert ActionType.REJECT.value == "reject"


class TestUserAction:
    """Test UserAction dataclass."""

    def test_action_creation(self):
        action = UserAction(
            action_id="act-1",
            action_type=ActionType.OPEN,
            item_id="main.py",
            timestamp=datetime.now(),
            context=ScenarioType.CODING,
        )
        assert action.action_id == "act-1"
        assert action.action_type == ActionType.OPEN
        assert action.item_id == "main.py"
        assert action.context == ScenarioType.CODING

    def test_action_to_dict(self):
        action = UserAction(
            action_id="act-2",
            action_type=ActionType.EDIT,
            item_id="utils.py",
            timestamp=datetime.now(),
            context=ScenarioType.CODING,
            metadata={"lines": 10},
        )
        result = action.to_dict()
        assert result["action_id"] == "act-2"
        assert result["action_type"] == "edit"
        assert result["item_id"] == "utils.py"
        assert result["metadata"]["lines"] == 10


class TestBehaviorPattern:
    """Test BehaviorPattern dataclass."""

    def test_pattern_creation(self):
        pattern = BehaviorPattern(
            item_id="main.py",
            frequency=5,
            last_accessed=datetime.now(),
            avg_interval=2.5,
            time_scores={10: 0.8, 14: 0.6},
            sequence_patterns=[("utils.py", 0.7)],
        )
        assert pattern.item_id == "main.py"
        assert pattern.frequency == 5
        assert pattern.avg_interval == 2.5
        assert len(pattern.time_scores) == 2

    def test_pattern_to_dict(self):
        pattern = BehaviorPattern(
            item_id="test.py",
            frequency=3,
            last_accessed=datetime.now(),
            avg_interval=1.0,
            time_scores={9: 0.5},
            sequence_patterns=[],
        )
        result = pattern.to_dict()
        assert result["item_id"] == "test.py"
        assert result["frequency"] == 3
        assert result["avg_interval"] == 1.0


class TestContextLearner:
    """Test ContextLearner class."""

    def test_learner_initialization(self):
        learner = ContextLearner()
        assert learner._actions == []
        assert learner._patterns == {}

    def test_track_action(self):
        learner = ContextLearner()
        action = learner.track_action(
            action_type=ActionType.OPEN,
            item_id="main.py",
            context=ScenarioType.CODING,
        )

        assert action.action_id is not None
        assert action.action_type == ActionType.OPEN
        assert action.item_id == "main.py"
        assert len(learner._actions) == 1

    def test_track_multiple_actions(self):
        learner = ContextLearner()

        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.EDIT, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)

        assert len(learner._actions) == 3
        assert "main.py" in learner._patterns
        assert "utils.py" in learner._patterns

    def test_get_frequency_score(self):
        learner = ContextLearner()

        # Track multiple actions for same item
        for _ in range(5):
            learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)

        learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)

        # main.py should have higher frequency score
        main_score = learner.get_frequency_score("main.py")
        utils_score = learner.get_frequency_score("utils.py")

        assert main_score > utils_score
        assert 0 <= main_score <= 1.0
        assert 0 <= utils_score <= 1.0

    def test_get_frequency_score_unknown_item(self):
        learner = ContextLearner()
        score = learner.get_frequency_score("unknown.py")
        assert score == 0.0

    def test_get_time_preference_score(self):
        learner = ContextLearner()

        # Track action at current hour
        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)

        score = learner.get_time_preference_score("main.py")
        assert 0 <= score <= 1.0
        assert score > 0  # Should have some score for current hour

    def test_get_sequence_score(self):
        learner = ContextLearner()

        # Create sequence pattern
        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)

        # utils.py often follows main.py
        score = learner.get_sequence_score("main.py", "utils.py")
        assert 0 <= score <= 1.0
        assert score > 0  # Should have positive sequence score

    def test_get_personalized_score(self):
        learner = ContextLearner()

        # Track some actions
        for _ in range(3):
            learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)

        learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)

        # Get personalized scores
        main_score = learner.get_personalized_score("main.py", ScenarioType.CODING)
        utils_score = learner.get_personalized_score("utils.py", ScenarioType.CODING)

        assert 0 <= main_score <= 1.0
        assert 0 <= utils_score <= 1.0
        # main.py should have higher score due to frequency
        assert main_score >= utils_score

    def test_get_top_items(self):
        learner = ContextLearner()

        # Track actions with different frequencies
        for _ in range(5):
            learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        for _ in range(3):
            learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "test.py", ScenarioType.CODING)

        top_items = learner.get_top_items(ScenarioType.CODING, top_n=3)

        assert len(top_items) <= 3
        assert all(isinstance(item, tuple) for item in top_items)
        assert all(isinstance(score, float) for _, score in top_items)
        # Should be sorted by score
        if len(top_items) > 1:
            assert top_items[0][1] >= top_items[1][1]

    def test_get_likely_next_items(self):
        learner = ContextLearner()

        # Create sequence patterns
        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "test.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)

        next_items = learner.get_likely_next_items("main.py", top_n=3)

        assert len(next_items) <= 3
        assert all(isinstance(item, tuple) for item in next_items)
        # Should be sorted by probability
        if len(next_items) > 1:
            assert next_items[0][1] >= next_items[1][1]

    def test_clear_history(self):
        learner = ContextLearner()

        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)

        assert len(learner._actions) == 2

        learner.clear_history()

        assert len(learner._actions) == 0
        assert len(learner._patterns) == 0

    def test_get_stats(self):
        learner = ContextLearner()

        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)

        stats = learner.get_stats()

        assert stats["total_actions"] == 2
        assert stats["unique_items"] == 2
        assert stats["oldest_action"] is not None
        assert stats["newest_action"] is not None

    def test_max_history_limit(self):
        learner = ContextLearner(max_history=5)

        # Track more actions than max_history
        for i in range(10):
            learner.track_action(ActionType.OPEN, f"file{i}.py", ScenarioType.CODING)

        # Should only keep last 5 actions
        assert len(learner._actions) == 5


class TestContextLearnerScenarios:
    """Test context learner with different scenarios."""

    def test_coding_scenario_learning(self):
        learner = ContextLearner()

        # Simulate coding workflow
        learner.track_action(ActionType.OPEN, "src/main.py", ScenarioType.CODING)
        learner.track_action(ActionType.EDIT, "src/main.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "src/utils.py", ScenarioType.CODING)
        learner.track_action(ActionType.OPEN, "tests/test_main.py", ScenarioType.CODING)

        # Get recommendations
        top_items = learner.get_top_items(ScenarioType.CODING, top_n=3)
        assert len(top_items) > 0

    def test_research_scenario_learning(self):
        learner = ContextLearner()

        # Simulate research workflow
        learner.track_action(ActionType.OPEN, "docs/paper.md", ScenarioType.RESEARCH)
        learner.track_action(ActionType.EDIT, "docs/paper.md", ScenarioType.RESEARCH)
        learner.track_action(ActionType.OPEN, "research/notes.md", ScenarioType.RESEARCH)

        # Get recommendations
        top_items = learner.get_top_items(ScenarioType.RESEARCH, top_n=3)
        assert len(top_items) > 0

    def test_multi_scenario_learning(self):
        learner = ContextLearner()

        # Coding actions
        learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
        learner.track_action(ActionType.EDIT, "main.py", ScenarioType.CODING)

        # Research actions
        learner.track_action(ActionType.OPEN, "paper.md", ScenarioType.RESEARCH)
        learner.track_action(ActionType.EDIT, "paper.md", ScenarioType.RESEARCH)

        # Get context-specific scores
        coding_score = learner.get_personalized_score("main.py", ScenarioType.CODING)
        research_score = learner.get_personalized_score("paper.md", ScenarioType.RESEARCH)

        assert coding_score > 0
        assert research_score > 0


class TestContextLearnerIntegration:
    """Integration tests for context learner."""

    def test_complete_learning_workflow(self):
        learner = ContextLearner()

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

        # Get statistics
        stats = learner.get_stats()
        assert stats["total_actions"] == 5
        assert stats["unique_items"] == 3

        # Get recommendations
        top_items = learner.get_top_items(ScenarioType.CODING, top_n=3)
        assert len(top_items) > 0

        # Get sequence predictions
        next_items = learner.get_likely_next_items("src/main.py", top_n=3)
        assert len(next_items) >= 0

    def test_learning_with_metadata(self):
        learner = ContextLearner()

        # Track action with metadata
        action = learner.track_action(
            action_type=ActionType.EDIT,
            item_id="main.py",
            context=ScenarioType.CODING,
            metadata={"lines_changed": 10, "duration": 300},
        )

        assert action.metadata["lines_changed"] == 10
        assert action.metadata["duration"] == 300

    def test_sequence_pattern_learning(self):
        learner = ContextLearner()

        # Create strong sequence pattern
        for _ in range(5):
            learner.track_action(ActionType.OPEN, "main.py", ScenarioType.CODING)
            learner.track_action(ActionType.OPEN, "utils.py", ScenarioType.CODING)

        # utils.py should be highly likely after main.py
        next_items = learner.get_likely_next_items("main.py", top_n=1)
        assert len(next_items) > 0
        assert next_items[0][0] == "utils.py"
        assert next_items[0][1] > 0.8  # High probability
