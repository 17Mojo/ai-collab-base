"""
ai_collab/engines/consensus_engine.py 补测
目标: 84% → 95%+
覆盖: _extract_consensus / _verify_consensus / get_consensus_summary /
      模块便捷函数 / _check_ai_clients_health 边界 / retry 失败路径
"""

import asyncio

import pytest

from ai_collab.engines import consensus_engine as ce_mod
from ai_collab.engines.consensus_engine import (
    AIProvider,
    ConsensusEngine,
    generate_consensus,
)


@pytest.fixture
def engine():
    return ConsensusEngine()


# ============================================================
# _check_ai_clients_health 边界
# ============================================================

def test_check_ai_clients_health_returns_false_when_no_enabled_providers(engine):
    """所有 providers enabled=False → 返回 False"""
    for p in engine.providers.values():
        p.enabled = False
    assert engine._check_ai_clients_health() is False


def test_check_ai_clients_health_true_when_client_set(monkeypatch, engine):
    """provider 有 client 时即使环境变量未设也返回 True"""
    for p in engine.providers.values():
        p.enabled = True
        p.client = object()  # 非 None 即可
    monkeypatch.delenv("AI_CLIENTS_AVAILABLE", raising=False)
    assert engine._check_ai_clients_health() is True


# ============================================================
# _extract_consensus
# ============================================================

def test_extract_consensus_joins_responses(engine):
    responses = [
        {"response": "first", "ai": "a", "confidence": 0.9},
        {"response": "second", "ai": "b", "confidence": 0.8},
    ]
    out = engine._extract_consensus(responses)
    assert "first" in out and "second" in out
    assert "\n\n" in out


def test_extract_consensus_empty_returns_empty(engine):
    assert engine._extract_consensus([]) == ""


# ============================================================
# _verify_consensus 三分支
# ============================================================

def test_verify_consensus_short_content(engine):
    """len < 50 → 返回 '共识内容不足'"""
    out = engine._verify_consensus("too short")
    assert "不足" in out


def test_verify_consensus_uncertainty_detected(engine):
    long = "x" * 100 + " 不确定"
    out = engine._verify_consensus(long)
    assert "不确定" in out


def test_verify_consensus_error_detected(engine):
    long = "x" * 100 + " 错误"
    out = engine._verify_consensus(long)
    assert "不确定" in out


def test_verify_consensus_clean_returns_input(engine):
    long = "x" * 100
    assert engine._verify_consensus(long) == long


# ============================================================
# get_consensus_summary
# ============================================================

def test_get_consensus_summary_includes_all_sources(engine):
    result = {
        "topic": "AI 协作",
        "timestamp": "2026-09-15T00:00:00",
        "version": "1.0",
        "mode": "consensus",
        "consensus": "核心结论: 多 AI 协同可显著提升效率",
        "sources": [
            {"ai": "claude", "confidence": 0.9},
            {"ai": "gpt", "confidence": 0.8},
        ],
    }
    summary = engine.get_consensus_summary(result)
    assert "AI 协作" in summary
    assert "claude" in summary
    assert "gpt" in summary
    assert "0.9" in summary
    assert "0.8" in summary


def test_get_consensus_summary_no_sources(engine):
    result = {
        "topic": "T",
        "timestamp": "ts",
        "version": "v",
        "consensus": "c",
        "sources": [],
    }
    summary = engine.get_consensus_summary(result)
    assert "T" in summary


# ============================================================
# 模块便捷函数 generate_consensus
# ============================================================

@pytest.mark.asyncio
async def test_module_generate_consensus_function(monkeypatch):
    """generate_consensus(topic) → 走 ConsensusEngine().generate_consensus(topic)"""
    async def fake_generate(self, topic):
        return {"topic": topic, "sources": [], "consensus": "ok", "timestamp": "t", "version": "v"}
    monkeypatch.setattr(ConsensusEngine, "generate_consensus", fake_generate)
    out = await generate_consensus("hello")
    assert out["topic"] == "hello"
    assert out["consensus"] == "ok"


# ============================================================
# _query_single_provider retry 路径
# ============================================================

@pytest.mark.asyncio
async def test_query_single_provider_raises_after_max_retries(engine):
    """_call_provider_api 一直失败 → 重试 max_retries 次后 re-raise 最后一次异常。
    （ConnectionError 分支是死代码：for 循环最后一次失败总会先 raise）"""
    provider = AIProvider(name="test", client=None, max_retries=2)

    async def always_fail(topic, prov):
        raise RuntimeError("boom")

    engine._call_provider_api = always_fail
    with pytest.raises(RuntimeError) as exc_info:
        await engine._query_single_provider("topic", provider)
    assert "boom" in str(exc_info.value)


@pytest.mark.asyncio
async def test_query_single_provider_succeeds_on_retry(engine):
    """前 1 次失败, 第 2 次成功"""
    provider = AIProvider(name="test", client=None, max_retries=3)
    calls = {"n": 0}

    async def flaky(topic, prov):
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("transient")
        return {"response": "ok"}

    engine._call_provider_api = flaky
    out = await engine._query_single_provider("t", provider)
    assert out["response"] == "ok"
    assert calls["n"] == 2


# ============================================================
# __main__ 入口防御（避免 import 副作用触发异步执行）
# ============================================================

def test_main_module_reexported():
    """smoke: 模块顶层 import 不抛异常"""
    assert hasattr(ce_mod, "ConsensusEngine")
    assert hasattr(ce_mod, "AIProvider")
