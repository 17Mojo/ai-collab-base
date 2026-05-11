# Context Recommender Module
# src/ai_collab/context/recommender.py

"""
Context-based Recommendation Engine

Provides intelligent recommendations based on scenario context and user history.
"""

import fnmatch
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .schema import Context, ScenarioType

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Recommendation type enumeration."""

    FILE = "file"  # File recommendation
    CONTEXT = "context"  # Context recommendation
    NEXT_ACTION = "next_action"  # Next action recommendation


@dataclass
class RecommendationScore:
    """Recommendation score with confidence."""

    score: float  # 0.0 - 1.0
    reason: str  # Reason for recommendation
    confidence: float  # Confidence level 0.0 - 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "score": self.score,
            "reason": self.reason,
            "confidence": self.confidence,
        }


@dataclass
class Recommendation:
    """Recommendation item."""

    rec_id: str
    rec_type: RecommendationType
    item_id: str  # file path / context id
    title: str
    description: str
    score: RecommendationScore
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rec_id": self.rec_id,
            "rec_type": self.rec_type.value,
            "item_id": self.item_id,
            "title": self.title,
            "description": self.description,
            "score": self.score.to_dict(),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class RecommendationHistory:
    """Recommendation history."""

    history_id: str
    context_scenario: str
    recommendations: List[Recommendation] = field(default_factory=list)
    accepted_ids: List[str] = field(default_factory=list)  # User accepted recommendations
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "history_id": self.history_id,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "context_scenario": self.context_scenario,
            "accepted_ids": self.accepted_ids,
            "timestamp": self.timestamp.isoformat(),
        }


class ContextRecommender:
    """Context-based recommendation engine."""

    # Scenario-specific file patterns
    SCENARIO_PATTERNS = {
        ScenarioType.CODING: {
            "high": ["src/**/*.py", "lib/**/*.py", "app/**/*.py", "*.py"],
            "medium": ["tests/**/*.py", "test_*.py", "*_test.py"],
            "low": ["docs/**/*.md", "README.md"],
        },
        ScenarioType.RESEARCH: {
            "high": ["docs/**/*.md", "research/**/*.md", "papers/**/*.pdf"],
            "medium": ["notes/**/*.md", "*.md"],
            "low": ["src/**/*.py"],
        },
        ScenarioType.WRITING: {
            "high": ["content/**/*.md", "posts/**/*.md", "articles/**/*.md"],
            "medium": ["drafts/**/*.md", "*.md"],
            "low": ["images/**/*"],
        },
        ScenarioType.DEBUGGING: {
            "high": ["logs/**/*.log", "test_*.py", "*_test.py"],
            "medium": ["debug/**/*", "src/**/*.py"],
            "low": ["docs/**/*.md"],
        },
        ScenarioType.DESIGN: {
            "high": ["design/**/*", "assets/**/*.css", "styles/**/*.scss"],
            "medium": ["*.css", "*.scss", "*.sass"],
            "low": ["docs/**/*.md"],
        },
        ScenarioType.PROJECT_PLANNING: {
            "high": ["plans/**/*.md", "tasks/**/*.md", "TODO.md"],
            "medium": ["*.md", "ROADMAP.md"],
            "low": ["src/**/*.py"],
        },
        ScenarioType.DOCUMENTATION: {
            "high": ["docs/**/*.md", "README.md", "CHANGELOG.md"],
            "medium": ["*.md", "CONTRIBUTING.md"],
            "low": ["src/**/*.py"],
        },
        ScenarioType.UNKNOWN: {
            "high": ["*.md", "*.py"],
            "medium": ["*"],
            "low": [],
        },
    }

    # File extension relevance
    EXTENSION_RELEVANCE = {
        ScenarioType.CODING: {
            ".py": 1.0,
            ".js": 0.9,
            ".ts": 0.9,
            ".java": 0.8,
            ".go": 0.8,
            ".md": 0.3,
            ".txt": 0.2,
        },
        ScenarioType.RESEARCH: {
            ".md": 1.0,
            ".pdf": 0.9,
            ".txt": 0.7,
            ".doc": 0.6,
            ".py": 0.3,
            ".js": 0.2,
        },
        ScenarioType.WRITING: {
            ".md": 1.0,
            ".txt": 0.8,
            ".doc": 0.7,
            ".py": 0.2,
            ".js": 0.2,
        },
        ScenarioType.DEBUGGING: {
            ".log": 1.0,
            ".py": 0.8,
            ".js": 0.7,
            ".txt": 0.6,
            ".md": 0.3,
        },
        ScenarioType.DESIGN: {
            ".css": 1.0,
            ".scss": 1.0,
            ".sass": 0.9,
            ".less": 0.8,
            ".md": 0.3,
            ".py": 0.2,
        },
        ScenarioType.PROJECT_PLANNING: {
            ".md": 1.0,
            ".txt": 0.7,
            ".yaml": 0.5,
            ".json": 0.5,
            ".py": 0.2,
        },
        ScenarioType.DOCUMENTATION: {
            ".md": 1.0,
            ".rst": 0.9,
            ".txt": 0.7,
            ".doc": 0.6,
            ".py": 0.3,
        },
        ScenarioType.UNKNOWN: {
            ".md": 0.5,
            ".py": 0.5,
            ".js": 0.5,
            ".txt": 0.4,
        },
    }

    def __init__(self):
        """Initialize recommender."""
        self._history: List[RecommendationHistory] = []
        self._logger = logging.getLogger(__name__)

    def recommend_files(
        self,
        scenario: ScenarioType,
        active_files: List[str],
        project_files: List[str],
        top_n: int = 10,
    ) -> List[Recommendation]:
        """
        Recommend files based on scenario and active files.

        Args:
            scenario: Current scenario type
            active_files: Currently active files
            project_files: All project files
            top_n: Number of recommendations

        Returns:
            List of file recommendations
        """
        recommendations = []

        # Get patterns for scenario
        patterns = self.SCENARIO_PATTERNS.get(
            scenario, self.SCENARIO_PATTERNS[ScenarioType.UNKNOWN]
        )
        extensions = self.EXTENSION_RELEVANCE.get(
            scenario, self.EXTENSION_RELEVANCE[ScenarioType.UNKNOWN]
        )

        # Score each file
        file_scores: Dict[str, float] = {}
        for file_path in project_files:
            if file_path in active_files:
                continue  # Skip active files

            score = self._calculate_file_score(file_path, patterns, extensions, active_files)
            if score > 0:
                file_scores[file_path] = score

        # Sort by score and create recommendations
        sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
        for file_path, score in sorted_files[:top_n]:
            rec = Recommendation(
                rec_id=str(uuid.uuid4()),
                rec_type=RecommendationType.FILE,
                item_id=file_path,
                title=f"Recommended: {file_path}",
                description=f"File relevant to {scenario.value} scenario",
                score=RecommendationScore(
                    score=score,
                    reason=self._get_score_reason(file_path, scenario),
                    confidence=min(score * 1.2, 1.0),
                ),
                metadata={"scenario": scenario.value},
            )
            recommendations.append(rec)

        return recommendations

    def recommend_context(
        self,
        scenario: ScenarioType,
        user_history: List[RecommendationHistory],
        top_n: int = 5,
    ) -> List[Recommendation]:
        """
        Recommend context based on user history.

        Args:
            scenario: Current scenario type
            user_history: User's recommendation history
            top_n: Number of recommendations

        Returns:
            List of context recommendations
        """
        recommendations = []

        # Analyze accepted recommendations
        accepted_items: Dict[str, int] = {}
        for history in user_history:
            for rec_id in history.accepted_ids:
                for rec in history.recommendations:
                    if rec.rec_id == rec_id:
                        key = f"{rec.rec_type.value}:{rec.item_id}"
                        accepted_items[key] = accepted_items.get(key, 0) + 1

        # Sort by frequency
        sorted_items = sorted(accepted_items.items(), key=lambda x: x[1], reverse=True)
        for key, count in sorted_items[:top_n]:
            rec_type_str, item_id = key.split(":", 1)
            rec = Recommendation(
                rec_id=str(uuid.uuid4()),
                rec_type=RecommendationType.CONTEXT,
                item_id=item_id,
                title=f"Frequently used: {item_id}",
                description=f"Used {count} times in similar scenarios",
                score=RecommendationScore(
                    score=min(count / 10.0, 1.0),
                    reason="Based on your usage history",
                    confidence=0.8,
                ),
                metadata={"usage_count": count, "scenario": scenario.value},
            )
            recommendations.append(rec)

        return recommendations

    def recommend_next(
        self,
        current_context: Context,
        top_n: int = 3,
    ) -> List[Recommendation]:
        """
        Recommend next actions based on current context.

        Args:
            current_context: Current context
            top_n: Number of recommendations

        Returns:
            List of action recommendations
        """
        recommendations = []

        # Scenario-specific next actions
        actions = self._get_scenario_actions(current_context.scenario)

        for i, (action, description, priority) in enumerate(actions[:top_n]):
            rec = Recommendation(
                rec_id=str(uuid.uuid4()),
                rec_type=RecommendationType.NEXT_ACTION,
                item_id=action,
                title=f"Next: {action}",
                description=description,
                score=RecommendationScore(
                    score=1.0 - (i * 0.2),
                    reason=f"Common next step for {current_context.scenario.value}",
                    confidence=0.7,
                ),
                metadata={"priority": priority, "scenario": current_context.scenario.value},
            )
            recommendations.append(rec)

        return recommendations

    def get_recommendations(
        self,
        scenario: ScenarioType,
        active_files: List[str],
        project_files: List[str],
        user_history: Optional[List[RecommendationHistory]] = None,
        current_context: Optional[Context] = None,
        top_n: int = 10,
    ) -> Dict[str, List[Recommendation]]:
        """
        Get all recommendations.

        Args:
            scenario: Current scenario
            active_files: Active files
            project_files: Project files
            user_history: User history
            current_context: Current context
            top_n: Number of recommendations per type

        Returns:
            Dictionary of recommendations by type
        """
        recommendations = {}

        # File recommendations
        recommendations["files"] = self.recommend_files(
            scenario, active_files, project_files, top_n
        )

        # Context recommendations
        if user_history:
            recommendations["context"] = self.recommend_context(scenario, user_history, top_n // 2)
        else:
            recommendations["context"] = []

        # Next action recommendations
        if current_context:
            recommendations["next_actions"] = self.recommend_next(current_context, top_n // 3)
        else:
            recommendations["next_actions"] = []

        return recommendations

    def accept_recommendation(self, rec_id: str, history_id: Optional[str] = None) -> None:
        """
        Mark recommendation as accepted.

        Args:
            rec_id: Recommendation ID
            history_id: History ID (optional)
        """
        if history_id:
            for history in self._history:
                if history.history_id == history_id:
                    if rec_id not in history.accepted_ids:
                        history.accepted_ids.append(rec_id)
                    break

    def reject_recommendation(self, rec_id: str) -> None:
        """
        Mark recommendation as rejected.

        Args:
            rec_id: Recommendation ID
        """
        # For now, just log the rejection
        self._logger.info(f"Recommendation rejected: {rec_id}")

    def create_history(
        self,
        recommendations: List[Recommendation],
        scenario: ScenarioType,
    ) -> RecommendationHistory:
        """
        Create recommendation history.

        Args:
            recommendations: Recommendations
            scenario: Scenario type

        Returns:
            Recommendation history
        """
        history = RecommendationHistory(
            history_id=str(uuid.uuid4()),
            recommendations=recommendations,
            context_scenario=scenario.value,
        )
        self._history.append(history)
        return history

    def _calculate_file_score(
        self,
        file_path: str,
        patterns: Dict[str, List[str]],
        extensions: Dict[str, float],
        active_files: List[str],
    ) -> float:
        """Calculate file recommendation score."""
        score = 0.0

        # Pattern matching
        import os

        file_name = os.path.basename(file_path)

        for priority, pattern_list in patterns.items():
            for pattern in pattern_list:
                if fnmatch.fnmatch(file_path, pattern) or fnmatch.fnmatch(file_name, pattern):
                    if priority == "high":
                        score += 0.5
                    elif priority == "medium":
                        score += 0.3
                    else:
                        score += 0.1
                    break

        # Extension relevance
        _, ext = os.path.splitext(file_path)
        ext_score = extensions.get(ext, 0.1)
        score += ext_score * 0.3

        # Active file similarity
        for active_file in active_files:
            # Same directory
            if os.path.dirname(file_path) == os.path.dirname(active_file):
                score += 0.2
            # Same extension
            active_ext = os.path.splitext(active_file)[1]
            if ext == active_ext:
                score += 0.1

        return min(score, 1.0)

    def _get_score_reason(self, file_path: str, scenario: ScenarioType) -> str:
        """Get reason for file score."""
        import os

        _, ext = os.path.splitext(file_path)
        dir_name = os.path.dirname(file_path)

        reasons = []
        if ext in self.EXTENSION_RELEVANCE.get(scenario, {}):
            reasons.append(f"{ext} files are relevant to {scenario.value}")
        if dir_name:
            reasons.append(f"Located in {dir_name} directory")

        return " | ".join(reasons) if reasons else "Matches scenario patterns"

    def _get_scenario_actions(self, scenario: ScenarioType) -> List[tuple]:
        """Get common next actions for scenario."""
        actions = {
            ScenarioType.CODING: [
                ("run_tests", "Run unit tests to verify changes", "high"),
                ("review_code", "Review code for quality issues", "high"),
                ("commit_changes", "Commit changes to version control", "medium"),
            ],
            ScenarioType.RESEARCH: [
                ("save_notes", "Save research notes", "high"),
                ("create_summary", "Create research summary", "medium"),
                ("update_docs", "Update documentation", "low"),
            ],
            ScenarioType.WRITING: [
                ("preview_content", "Preview written content", "high"),
                ("check_style", "Check writing style", "medium"),
                ("publish", "Publish content", "low"),
            ],
            ScenarioType.DEBUGGING: [
                ("analyze_logs", "Analyze error logs", "high"),
                ("fix_issue", "Fix identified issue", "high"),
                ("verify_fix", "Verify fix works", "medium"),
            ],
            ScenarioType.DESIGN: [
                ("preview_design", "Preview design changes", "high"),
                ("check_responsive", "Check responsive design", "medium"),
                ("optimize_assets", "Optimize design assets", "low"),
            ],
            ScenarioType.PROJECT_PLANNING: [
                ("update_tasks", "Update task list", "high"),
                ("review_progress", "Review project progress", "medium"),
                ("plan_next", "Plan next steps", "medium"),
            ],
            ScenarioType.DOCUMENTATION: [
                ("preview_docs", "Preview documentation", "high"),
                ("check_links", "Check documentation links", "medium"),
                ("update_toc", "Update table of contents", "low"),
            ],
            ScenarioType.UNKNOWN: [
                ("analyze_context", "Analyze current context", "high"),
                ("suggest_scenario", "Suggest scenario type", "medium"),
            ],
        }
        return actions.get(scenario, actions[ScenarioType.UNKNOWN])
