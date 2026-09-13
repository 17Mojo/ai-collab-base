"""
Unit tests for Consensus Engine integration with PackExecutorMVP.

Tests:
- PackExecutorMVP correctly calls ConsensusEngine when ai_models is configured
- Fallback behavior when consensus fails
- Fusion strategies (concat, best, weighted)
- ConsensusConfig dataclass defaults and serialization
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from ai_collab.engines.consensus_engine import ConsensusEngine
from ai_collab.pack.pack_executor_mvp import PackExecutorMVP
from ai_collab.pack.schema_v2 import ConsensusConfig, WorkflowStep, StepType


# ==================== ConsensusConfig Schema Tests ====================


class TestConsensusConfig:
    """Test ConsensusConfig dataclass."""

    def test_default_values(self):
        """ConsensusConfig should have sensible defaults."""
        config = ConsensusConfig()
        assert config.enabled is False
        assert config.providers == []
        assert config.timeout == 30.0
        assert config.min_providers == 2
        assert config.fusion_strategy == "concat"

    def test_custom_values(self):
        """ConsensusConfig should accept custom values."""
        config = ConsensusConfig(
            enabled=True,
            providers=["chatgpt", "claude"],
            timeout=60.0,
            min_providers=1,
            fusion_strategy="weighted",
        )
        assert config.enabled is True
        assert config.providers == ["chatgpt", "claude"]
        assert config.timeout == 60.0
        assert config.min_providers == 1
        assert config.fusion_strategy == "weighted"

    def test_workflow_step_with_consensus_config(self):
        """WorkflowStep should accept consensus_config."""
        config = ConsensusConfig(enabled=True, providers=["chatgpt"])
        step = WorkflowStep(
            id="gen-1",
            name="generate",
            type=StepType.GENERATION,
            ai_models=["chatgpt"],
            consensus_config=config,
        )
        assert step.consensus_config is not None
        assert step.consensus_config.enabled is True

    def test_workflow_step_without_consensus_config(self):
        """WorkflowStep should default consensus_config to None."""
        step = WorkflowStep(id="gen-1", name="generate", type=StepType.GENERATION)
        assert step.consensus_config is None


# ==================== PackExecutorMVP Consensus Tests ====================


MOCK_CONSENSUS_RESULT = {
    "topic": "测试主题",
    "consensus": "这是一个关于测试主题的共识内容，来自多个AI的综合观点。",
    "sources": [
        {"ai": "chatgpt", "response": "ChatGPT 观点: 测试主题的核心是...", "confidence": 0.9},
        {"ai": "claude", "response": "Claude 观点: 测试主题的关键在于...", "confidence": 0.85},
        {"ai": "kimi", "response": "Kimi 观点: 从测试主题来看...", "confidence": 0.88},
    ],
    "timestamp": "2026-08-04T00:00:00",
    "version": "1.1",
    "mode": "mock",
}


def _make_pack_with_ai_models(ai_models=None, consensus_config=None):
    """Helper to create a test pack dict with ai_models on generation step."""
    step = {
        "name": "生成内容",
        "type": "GENERATION",
        "template": "默认模板",
    }
    if ai_models is not None:
        step["ai_models"] = ai_models
    if consensus_config is not None:
        step["consensus_config"] = consensus_config

    return {
        "metadata": {"pack_name": "测试包", "version": "1.0.0"},
        "workflow": {
            "steps": [
                {
                    "name": "收集输入",
                    "type": "LOCAL",
                    "inputs": [
                        {"key": "topic", "source": "user_input"},
                        {"key": "content", "source": "user_input"},
                    ],
                },
                {"name": "分析内容", "type": "ANALYSIS"},
                step,
            ]
        },
    }


class TestConsensusIntegration:
    """Test PackExecutorMVP + ConsensusEngine integration."""

    def test_generation_without_ai_models_uses_template(self):
        """Without ai_models, generation should use template (no consensus)."""
        pack = _make_pack_with_ai_models()
        executor = PackExecutorMVP(pack)
        result = executor.execute({"topic": "测试", "content": "内容"})

        assert result["status"] == "completed"
        # Should NOT have consensus_result in context
        assert "consensus_result" not in executor.context

    @patch("ai_collab.pack.pack_executor_mvp.ConsensusEngine")
    def test_generation_with_ai_models_calls_consensus(self, MockEngine):
        """With ai_models, generation should call ConsensusEngine."""
        mock_instance = MockEngine.return_value
        mock_instance.providers = {
            "chatgpt": type("P", (), {"enabled": True, "timeout": 30.0})(),
            "claude": type("P", (), {"enabled": True, "timeout": 30.0})(),
            "kimi": type("P", (), {"enabled": True, "timeout": 30.0})(),
            "qianwen": type("P", (), {"enabled": True, "timeout": 30.0})(),
        }
        mock_instance.generate_consensus = AsyncMock(return_value=MOCK_CONSENSUS_RESULT)

        pack = _make_pack_with_ai_models(ai_models=["chatgpt", "claude"])
        executor = PackExecutorMVP(pack)
        result = executor.execute({"topic": "测试主题", "content": "内容"})

        assert result["status"] == "completed"
        mock_instance.generate_consensus.assert_called_once_with("测试主题")
        assert executor.context.get("consensus_result") == MOCK_CONSENSUS_RESULT

    @patch("ai_collab.pack.pack_executor_mvp.ConsensusEngine")
    def test_consensus_enables_only_specified_providers(self, MockEngine):
        """Only specified providers should remain enabled."""
        mock_instance = MockEngine.return_value
        mock_providers = {}
        for name in ["chatgpt", "claude", "kimi", "qianwen"]:
            mock_providers[name] = type("P", (), {"enabled": True, "timeout": 30.0})()
        mock_instance.providers = mock_providers
        mock_instance.generate_consensus = AsyncMock(return_value=MOCK_CONSENSUS_RESULT)

        pack = _make_pack_with_ai_models(ai_models=["chatgpt", "claude"])
        executor = PackExecutorMVP(pack)
        executor.execute({"topic": "测试", "content": "内容"})

        # chatgpt and claude should be enabled; kimi and qianwen should be disabled
        assert mock_providers["chatgpt"].enabled is True
        assert mock_providers["claude"].enabled is True
        assert mock_providers["kimi"].enabled is False
        assert mock_providers["qianwen"].enabled is False

    @patch("ai_collab.pack.pack_executor_mvp.ConsensusEngine")
    def test_consensus_fallback_on_failure(self, MockEngine):
        """When consensus engine raises, executor should fall back gracefully."""
        mock_instance = MockEngine.return_value
        mock_instance.providers = {
            "chatgpt": type("P", (), {"enabled": True, "timeout": 30.0})(),
        }
        mock_instance.generate_consensus = AsyncMock(
            side_effect=ConnectionError("All providers failed")
        )

        pack = _make_pack_with_ai_models(ai_models=["chatgpt"])
        executor = PackExecutorMVP(pack)
        result = executor.execute({"topic": "测试", "content": "内容"})

        # Should complete with fallback, not crash
        assert result["status"] == "completed"
        # The final content should indicate fallback
        assert "回退" in result["final_content"] or "fallback" in executor.context.get("generated_content", "").lower()

    @patch("ai_collab.pack.pack_executor_mvp.ConsensusEngine")
    def test_consensus_with_consensus_config_dict(self, MockEngine):
        """consensus_config as dict should be handled correctly."""
        mock_instance = MockEngine.return_value
        mock_instance.providers = {
            "chatgpt": type("P", (), {"enabled": True, "timeout": 30.0})(),
        }
        mock_instance.generate_consensus = AsyncMock(return_value=MOCK_CONSENSUS_RESULT)

        config = {"timeout": 45.0, "fusion_strategy": "best", "min_providers": 1}
        pack = _make_pack_with_ai_models(
            ai_models=["chatgpt"], consensus_config=config
        )
        executor = PackExecutorMVP(pack)
        result = executor.execute({"topic": "测试", "content": "内容"})

        assert result["status"] == "completed"
        assert executor.context.get("consensus_result") is not None


# ==================== Fusion Strategy Tests ====================


class TestFusionStrategy:
    """Test _apply_fusion_strategy method."""

    def setup_method(self):
        """Set up executor for fusion tests."""
        pack = _make_pack_with_ai_models()
        self.executor = PackExecutorMVP(pack)

    def test_concat_strategy(self):
        """concat strategy should join all responses with separator."""
        result = self.executor._apply_fusion_strategy(MOCK_CONSENSUS_RESULT, "concat")
        assert "ChatGPT 观点" in result
        assert "Claude 观点" in result
        assert "Kimi 观点" in result
        assert "---" in result

    def test_best_strategy(self):
        """best strategy should pick highest confidence response."""
        result = self.executor._apply_fusion_strategy(MOCK_CONSENSUS_RESULT, "best")
        # chatgpt has confidence 0.9 (highest)
        assert "ChatGPT 观点" in result
        assert "---" not in result

    def test_weighted_strategy(self):
        """weighted strategy should include confidence annotations."""
        result = self.executor._apply_fusion_strategy(MOCK_CONSENSUS_RESULT, "weighted")
        assert "[置信度:" in result
        # Should be sorted by confidence descending, so chatgpt first
        chatgpt_pos = result.index("ChatGPT")
        claude_pos = result.index("Claude")
        assert chatgpt_pos < claude_pos

    def test_unknown_strategy_defaults_to_consensus(self):
        """Unknown strategy should fall back to consensus string."""
        result = self.executor._apply_fusion_strategy(MOCK_CONSENSUS_RESULT, "unknown")
        assert result == MOCK_CONSENSUS_RESULT["consensus"]

    def test_empty_sources_returns_consensus(self):
        """With no sources, should return the consensus string directly."""
        empty_result = {"consensus": "仅共识文本", "sources": []}
        result = self.executor._apply_fusion_strategy(empty_result, "concat")
        assert result == "仅共识文本"

    def test_consensus_config_dataclass_fusion_strategy(self):
        """Verify ConsensusConfig fusion_strategy values are valid."""
        for strategy in ["concat", "best", "weighted"]:
            config = ConsensusConfig(fusion_strategy=strategy)
            assert config.fusion_strategy == strategy
