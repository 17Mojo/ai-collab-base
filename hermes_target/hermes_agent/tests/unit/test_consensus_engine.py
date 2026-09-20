"""Hermes ConsensusEngine 单元测试。"""
import pytest

from hermes_agent.engines import ConsensusEngine, AIProvider


def test_consensus_engine_imports():
    """验证 ConsensusEngine 可导入"""
    engine = ConsensusEngine()
    assert engine is not None


def test_consensus_engine_has_models():
    """Hermes 适配: providers 重命名为 models"""
    engine = ConsensusEngine()
    assert hasattr(engine, "models") or hasattr(engine, "providers")


def test_ai_provider_dataclass():
    """AIProvider dataclass 可创建"""
    provider = AIProvider(name="test")
    assert provider.name == "test"
    assert provider.timeout == 30.0  # default
    assert provider.max_retries == 3  # default
