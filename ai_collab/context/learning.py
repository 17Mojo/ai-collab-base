# Context Learning Module
# src/ai_collab/context/learning.py

"""
User Behavior Learning for Context Recommendations

Tracks and learns from user actions to improve recommendation accuracy.
"""

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .schema import ScenarioType

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """User action type enumeration."""

    VIEW = "view"  # View file/context
    OPEN = "open"  # Open file
    EDIT = "edit"  # Edit file
    DELETE = "delete"  # Delete file
    ACCEPT = "accept"  # Accept recommendation
    REJECT = "reject"  # Reject recommendation


@dataclass
class UserAction:
    """User action record."""

    action_id: str
    action_type: ActionType
    item_id: str  # File path / context id
    timestamp: datetime
    context: ScenarioType
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "item_id": self.item_id,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context.value,
            "metadata": self.metadata,
        }


@dataclass
class BehaviorPattern:
    """Behavior pattern analysis."""

    item_id: str
    frequency: int  # Access frequency
    last_accessed: datetime
    avg_interval: float  # Average access interval in hours
    time_scores: Dict[int, float]  # Hour -> score
    sequence_patterns: List[Tuple[str, float]]  # (next_item, probability)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "item_id": self.item_id,
            "frequency": self.frequency,
            "last_accessed": self.last_accessed.isoformat(),
            "avg_interval": self.avg_interval,
            "time_scores": self.time_scores,
            "sequence_patterns": self.sequence_patterns,
        }


class ContextLearner:
    """Context learning controller."""

    def __init__(self, max_history: int = 1000):
        """
        Initialize context learner.

        Args:
            max_history: Maximum number of actions to keep
        """
        self._actions: List[UserAction] = []
        self._patterns: Dict[str, BehaviorPattern] = {}
        self._max_history = max_history
        self._logger = logging.getLogger(__name__)

        # Sequence tracking
        self._sequences: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._sequence_totals: Dict[str, int] = defaultdict(int)

    def track_action(
        self,
        action_type: ActionType,
        item_id: str,
        context: ScenarioType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserAction:
        """
        Track user action.

        Args:
            action_type: Type of action
            item_id: Item identifier
            context: Current context
            metadata: Additional metadata

        Returns:
            UserAction record
        """
        action = UserAction(
            action_id=str(uuid.uuid4()),
            action_type=action_type,
            item_id=item_id,
            timestamp=datetime.now(),
            context=context,
            metadata=metadata or {},
        )

        self._actions.append(action)

        # Update patterns
        self._update_patterns(action)

        # Trim history if needed
        if len(self._actions) > self._max_history:
            self._actions = self._actions[-self._max_history :]

        return action

    def get_frequency_score(self, item_id: str) -> float:
        """
        Get frequency-based score for item.

        Args:
            item_id: Item identifier

        Returns:
            Frequency score (0.0 - 1.0)
        """
        if item_id not in self._patterns:
            return 0.0

        pattern = self._patterns[item_id]
        max_freq = max(p.frequency for p in self._patterns.values()) if self._patterns else 1

        return min(pattern.frequency / max_freq, 1.0)

    def get_time_preference_score(self, item_id: str) -> float:
        """
        Get time preference score for item.

        Args:
            item_id: Item identifier

        Returns:
            Time preference score (0.0 - 1.0)
        """
        if item_id not in self._patterns:
            return 0.0

        pattern = self._patterns[item_id]
        current_hour = datetime.now().hour

        # Get score for current hour
        hour_score = pattern.time_scores.get(current_hour, 0.0)

        # Consider adjacent hours
        prev_hour = (current_hour - 1) % 24
        next_hour = (current_hour + 1) % 24
        prev_score = pattern.time_scores.get(prev_hour, 0.0) * 0.5
        next_score = pattern.time_scores.get(next_hour, 0.0) * 0.5

        return min(hour_score + prev_score + next_score, 1.0)

    def get_sequence_score(self, current_item: str, next_item: str) -> float:
        """
        Get sequence probability score.

        Args:
            current_item: Current item
            next_item: Potential next item

        Returns:
            Sequence score (0.0 - 1.0)
        """
        if current_item not in self._sequences:
            return 0.0

        sequences = self._sequences[current_item]
        total = self._sequence_totals[current_item]

        if total == 0:
            return 0.0

        count = sequences.get(next_item, 0)
        return count / total

    def get_personalized_score(self, item_id: str, context: ScenarioType) -> float:
        """
        Get personalized recommendation score.

        Args:
            item_id: Item identifier
            context: Current context

        Returns:
            Personalized score (0.0 - 1.0)
        """
        # Weight factors
        freq_weight = 0.4
        time_weight = 0.3
        context_weight = 0.3

        # Frequency score
        freq_score = self.get_frequency_score(item_id)

        # Time preference score
        time_score = self.get_time_preference_score(item_id)

        # Context relevance score
        context_score = self._get_context_relevance(item_id, context)

        # Combined score
        score = freq_weight * freq_score + time_weight * time_score + context_weight * context_score

        return min(score, 1.0)

    def get_top_items(self, context: ScenarioType, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Get top items by personalized score.

        Args:
            context: Current context
            top_n: Number of items

        Returns:
            List of (item_id, score) tuples
        """
        scores = []
        for item_id in self._patterns:
            score = self.get_personalized_score(item_id, context)
            scores.append((item_id, score))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_n]

    def get_likely_next_items(self, current_item: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Get likely next items based on sequence patterns.

        Args:
            current_item: Current item
            top_n: Number of items

        Returns:
            List of (item_id, probability) tuples
        """
        if current_item not in self._sequences:
            return []

        sequences = self._sequences[current_item]
        total = self._sequence_totals[current_item]

        if total == 0:
            return []

        # Calculate probabilities
        probs = []
        for next_item, count in sequences.items():
            prob = count / total
            probs.append((next_item, prob))

        # Sort by probability
        probs.sort(key=lambda x: x[1], reverse=True)
        return probs[:top_n]

    def clear_history(self) -> None:
        """Clear action history and patterns."""
        self._actions.clear()
        self._patterns.clear()
        self._sequences.clear()
        self._sequence_totals.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        return {
            "total_actions": len(self._actions),
            "unique_items": len(self._patterns),
            "total_sequences": sum(self._sequence_totals.values()),
            "oldest_action": self._actions[0].timestamp.isoformat() if self._actions else None,
            "newest_action": self._actions[-1].timestamp.isoformat() if self._actions else None,
        }

    def _update_patterns(self, action: UserAction) -> None:
        """Update behavior patterns with new action."""
        item_id = action.item_id
        timestamp = action.timestamp

        # Update or create pattern
        if item_id in self._patterns:
            pattern = self._patterns[item_id]

            # Update frequency
            pattern.frequency += 1

            # Update average interval
            if pattern.last_accessed:
                interval = (timestamp - pattern.last_accessed).total_seconds() / 3600
                if pattern.avg_interval > 0:
                    pattern.avg_interval = (pattern.avg_interval + interval) / 2
                else:
                    pattern.avg_interval = interval

            # Update time scores
            hour = timestamp.hour
            pattern.time_scores[hour] = pattern.time_scores.get(hour, 0.0) + 0.1

            # Update last accessed
            pattern.last_accessed = timestamp
        else:
            # Create new pattern
            pattern = BehaviorPattern(
                item_id=item_id,
                frequency=1,
                last_accessed=timestamp,
                avg_interval=0.0,
                time_scores={timestamp.hour: 1.0},
                sequence_patterns=[],
            )
            self._patterns[item_id] = pattern

        # Update sequence patterns
        if len(self._actions) > 1:
            prev_action = self._actions[-2]
            if prev_action.item_id != item_id:
                self._sequences[prev_action.item_id][item_id] += 1
                self._sequence_totals[prev_action.item_id] += 1

    def _get_context_relevance(self, item_id: str, context: ScenarioType) -> float:
        """Get context relevance score."""
        # Count actions for this item in this context
        context_actions = [
            a for a in self._actions if a.item_id == item_id and a.context == context
        ]

        if not context_actions:
            return 0.0

        # Calculate relevance based on frequency and recency
        total_actions = len([a for a in self._actions if a.item_id == item_id])
        context_ratio = len(context_actions) / total_actions if total_actions > 0 else 0.0

        # Consider recency
        recent_actions = [
            a for a in context_actions if (datetime.now() - a.timestamp) < timedelta(days=7)
        ]
        recency_boost = len(recent_actions) / len(context_actions) if context_actions else 0.0

        return min(context_ratio * 0.7 + recency_boost * 0.3, 1.0)
