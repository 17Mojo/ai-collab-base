"""Hermes ConsensusEngine 单元测试。

覆盖四条主路径：
1. 多模型并发查询（asyncio.gather + Semaphore 限流）
2. 双层超时控制（全局 global_timeout + 单 provider timeout）
3. 重试退避（max_retries=3 + 指数退避）
4. 结果归一化（normalize_result 公开入口）
"""

from __future__ import annotations

import asyncio
import textwrap
import time

import pytest
from hermes_agent.engines import AIProvider, ConsensusEngine
from hermes_agent.engines.consensus_engine import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
    STATUS_TIMEOUT,
    IntegrationMode,
)


class AsyncClient:
    """异步 client：可配置延迟、返回值与异常。"""

    def __init__(self, delay: float = 0.0, response=None, error: Exception | None = None) -> None:
        self.delay = delay
        self.response = response
        self.error = error
        self.calls = 0

    async def query(self, topic):
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        if self.response is None:
            return {"ai": "async", "response": f"[async] {topic}", "confidence": 0.95}
        return self.response


class SyncClient:
    """同步 client（走 run_in_executor 分支）。"""

    def __init__(self, response: str = "[sync] ok") -> None:
        self.response = response
        self.calls = 0

    def query(self, topic):
        self.calls += 1
        return self.response


class NoQueryClient:
    """没有 query 方法的 client。"""


class FlakyClient:
    """首次调用超时、之后成功的 client（覆盖重试退避路径）。"""

    def __init__(self, first_delay: float = 0.2) -> None:
        self.first_delay = first_delay
        self.calls = 0

    async def query(self, topic):
        self.calls += 1
        if self.calls == 1:
            await asyncio.sleep(self.first_delay)
        return {"ai": "flaky", "response": "[flaky] ok", "confidence": 0.8}


class TrackingClient:
    """记录并发峰值的 client（覆盖 max_concurrent 限流）。"""

    def __init__(self, delay: float = 0.05) -> None:
        self.delay = delay
        self.active = 0
        self.peak = 0

    async def query(self, topic):
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(self.delay)
        self.active -= 1
        return {"ai": "tracking", "response": "[tracking] ok", "confidence": 0.5}


def _engine_with_clients(**kwargs) -> ConsensusEngine:
    """构造只含一个 provider 的引擎（便于精确断言）。"""
    client = kwargs.pop("client", None)
    models = {"only": AIProvider(name="only", client=client, timeout=kwargs.pop("timeout", 5.0))}
    return ConsensusEngine(models=models, **kwargs)


# ----------------------------------------------------------------------
# 基础结构
# ----------------------------------------------------------------------
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


def test_providers_alias_shares_models_mapping():
    """providers 与 models 指向同一 dict"""
    engine = ConsensusEngine()
    assert engine.providers is engine.models


def test_default_models_are_registered():
    """默认内置 4 个模型"""
    engine = ConsensusEngine()
    assert set(engine.models) == {"chatgpt", "claude", "kimi", "qianwen"}
    assert engine.VERSION == "1.3"


def test_global_timeout_from_env(monkeypatch):
    """CONSENSUS_GLOBAL_TIMEOUT 环境变量生效"""
    monkeypatch.setenv("CONSENSUS_GLOBAL_TIMEOUT", "12.5")
    engine = ConsensusEngine()
    assert engine.global_timeout == 12.5


def test_explicit_global_timeout_overrides_env(monkeypatch):
    """显式参数优先于环境变量"""
    monkeypatch.setenv("CONSENSUS_GLOBAL_TIMEOUT", "12.5")
    engine = ConsensusEngine(global_timeout=3.0)
    assert engine.global_timeout == 3.0


def test_config_file_is_loaded(tmp_path):
    """从 Hermes config.yaml 读取 engines.consensus 配置"""
    config = tmp_path / "config.yaml"
    config.write_text(
        textwrap.dedent(
            """
            engines:
              consensus:
                enabled: true
                max_concurrent: 7
                global_timeout: 33
                retry:
                  max_retries: 5
                fallback_mode: partial
            """
        ),
        encoding="utf-8",
    )
    engine = ConsensusEngine(config_path=str(config))
    assert engine.max_concurrent == 7
    assert engine.global_timeout == 33.0
    assert engine.max_retries == 5
    assert engine.fallback_mode == "partial"
    assert engine.models["chatgpt"].max_retries == 5


def test_config_missing_file_falls_back_to_defaults(tmp_path):
    """配置文件不存在时使用默认配置"""
    engine = ConsensusEngine(config_path=str(tmp_path / "nope.yaml"))
    assert engine.max_concurrent == 5
    assert engine.global_timeout == 60.0
    assert engine.max_retries == 3


def test_config_invalid_yaml_falls_back_to_defaults(tmp_path):
    """配置文件损坏时不阻断引擎启动"""
    config = tmp_path / "broken.yaml"
    config.write_text("engines: [unclosed\n", encoding="utf-8")
    engine = ConsensusEngine(config_path=str(config))
    assert engine.max_concurrent == 5


def test_config_non_mapping_payload_falls_back_to_defaults(tmp_path):
    """配置根节点不是 mapping 时使用默认配置"""
    config = tmp_path / "list.yaml"
    config.write_text("- a\n- b\n", encoding="utf-8")
    engine = ConsensusEngine(config_path=str(config))
    assert engine.max_concurrent == 5


def test_register_provider():
    """注册 provider 后两侧映射都可见"""
    engine = ConsensusEngine()
    engine.register_provider("custom", client=AsyncClient(), timeout=12.0)
    assert "custom" in engine.models
    assert "custom" in engine.providers
    assert engine.models["custom"].timeout == 12.0


def test_register_provider_honours_max_retries():
    """注册 provider 可单独指定重试次数"""
    engine = ConsensusEngine()
    engine.register_provider("custom", client=AsyncClient(), max_retries=1)
    assert engine.models["custom"].max_retries == 1


def test_health_check_requires_enabled_provider(monkeypatch):
    """无启用 provider 时健康检查失败"""
    monkeypatch.delenv("AI_CLIENTS_AVAILABLE", raising=False)
    engine = ConsensusEngine()
    for provider in engine.models.values():
        provider.enabled = False
    assert engine._check_ai_clients_health() is False


def test_health_check_true_with_client(monkeypatch):
    """存在真实 client 时健康检查通过"""
    monkeypatch.delenv("AI_CLIENTS_AVAILABLE", raising=False)
    engine = ConsensusEngine()
    engine.models["chatgpt"].client = AsyncClient()
    assert engine._check_ai_clients_health() is True


def test_health_check_true_with_env(monkeypatch):
    """环境变量声明客户端可用时健康检查通过"""
    monkeypatch.setenv("AI_CLIENTS_AVAILABLE", "true")
    engine = ConsensusEngine()
    assert engine._check_ai_clients_health() is True


# ----------------------------------------------------------------------
# 结果归一化
# ----------------------------------------------------------------------
def test_normalize_result_with_dict_payload():
    """dict 响应归一化"""
    engine = ConsensusEngine()
    result = engine.normalize_result({"ai": "x", "response": "body", "confidence": 0.7}, "prov")
    assert result["ai"] == "x"
    assert result["response"] == "body"
    assert result["confidence"] == 0.7
    assert result["provider"] == "prov"
    assert result["status"] == STATUS_SUCCESS
    assert "timestamp" in result


def test_normalize_result_with_string_payload():
    """字符串响应归一化"""
    engine = ConsensusEngine()
    result = engine.normalize_result("plain text", "prov")
    assert result["ai"] == "prov"
    assert result["response"] == "plain text"
    assert result["confidence"] == 0.0


def test_normalize_result_with_other_payload():
    """其它类型响应归一化为字符串"""
    engine = ConsensusEngine()
    result = engine.normalize_result(42, "prov")
    assert result["response"] == "42"
    assert result["confidence"] == 0.0


def test_normalize_result_with_none_payload_keeps_error():
    """失败归一化携带 error 字段"""
    engine = ConsensusEngine()
    result = engine.normalize_result(None, "prov", status=STATUS_FAILED, error="boom")
    assert result["status"] == STATUS_FAILED
    assert result["error"] == "boom"
    assert result["response"] == ""


# ----------------------------------------------------------------------
# 单模型查询：超时 / 重试 / 客户端兼容
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_query_model_without_client_uses_mock():
    """无 client 时走 mock 响应"""
    engine = _engine_with_clients()
    result = await engine.query_model("topic")
    assert result["status"] == STATUS_SUCCESS
    assert result["provider"] == "only"
    assert "[ONLY REAL]" in result["response"]


@pytest.mark.asyncio
async def test_query_model_unknown_model_is_failed():
    """未知模型返回 failed 而不是抛异常"""
    engine = _engine_with_clients()
    result = await engine.query_model("topic", "ghost")
    assert result["status"] == STATUS_FAILED
    assert "unknown model" in result["error"]


@pytest.mark.asyncio
async def test_query_model_with_async_client():
    """异步 client 响应归一化"""
    engine = _engine_with_clients(client=AsyncClient())
    result = await engine.query_model("topic")
    assert result["status"] == STATUS_SUCCESS
    assert result["response"] == "[async] topic"
    assert result["confidence"] == 0.95


@pytest.mark.asyncio
async def test_query_model_with_sync_client():
    """同步 client 经 executor 调用"""
    client = SyncClient()
    engine = _engine_with_clients(client=client)
    result = await engine.query_model("topic")
    assert result["status"] == STATUS_SUCCESS
    assert result["response"] == "[sync] ok"
    assert client.calls == 1


@pytest.mark.asyncio
async def test_query_model_client_without_query_method_falls_back_to_mock():
    """client 缺少 query 方法时回退 mock"""
    engine = _engine_with_clients(client=NoQueryClient())
    result = await engine.query_model("topic")
    assert result["status"] == STATUS_SUCCESS
    assert "[ONLY REAL]" in result["response"]


@pytest.mark.asyncio
async def test_query_model_client_error_falls_back_to_mock():
    """client 调用异常时回退 mock（不打断整体查询）"""
    engine = _engine_with_clients(client=AsyncClient(error=RuntimeError("provider down")))
    result = await engine.query_model("topic")
    assert result["status"] == STATUS_SUCCESS
    assert "[ONLY REAL]" in result["response"]


@pytest.mark.asyncio
async def test_query_model_timeout_is_isolated():
    """provider 超时按 max_retries 重试后返回 timeout，不抛异常"""
    client = AsyncClient(delay=0.5)
    engine = _engine_with_clients(client=client, timeout=0.02)
    engine.models["only"].max_retries = 3
    result = await engine.query_model("topic")
    assert result["status"] == STATUS_TIMEOUT
    assert client.calls == 3
    assert "timeout" in result["error"]


@pytest.mark.asyncio
async def test_query_model_retries_then_succeeds():
    """首次超时后重试成功"""
    client = FlakyClient(first_delay=0.3)
    engine = _engine_with_clients(client=client, timeout=0.05)
    engine.models["only"].max_retries = 3
    result = await engine.query_model("topic")
    assert result["status"] == STATUS_SUCCESS
    assert result["response"] == "[flaky] ok"
    assert client.calls == 2


@pytest.mark.asyncio
async def test_query_model_retry_uses_exponential_backoff():
    """重试之间存在指数退避间隔"""
    engine = _engine_with_clients(client=AsyncClient(delay=0.2), timeout=0.01)
    engine.models["only"].max_retries = 3
    engine.models["only"].backoff_base = 0.05
    started = time.monotonic()
    result = await engine.query_model("topic")
    elapsed = time.monotonic() - started
    assert result["status"] == STATUS_TIMEOUT
    # 3 次超时(0.01x3) + 退避(0.05 + 0.1)
    assert elapsed >= 0.05 + 0.1


# ----------------------------------------------------------------------
# 多模型并发查询
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_query_models_concurrent_returns_all_results():
    """并发查询所有启用模型"""
    engine = ConsensusEngine()
    for name in ("chatgpt", "claude"):
        engine.models[name].client = AsyncClient()
    results = await engine.query_models("topic")
    assert len(results) == 4
    assert all(item["status"] == STATUS_SUCCESS for item in results)
    assert {item["provider"] for item in results} == set(engine.models)


@pytest.mark.asyncio
async def test_query_models_respects_max_concurrent():
    """max_concurrent 限制同时在跑的查询数"""
    client = TrackingClient(delay=0.05)
    models = {f"m{i}": AIProvider(name=f"m{i}", client=client, timeout=5.0) for i in range(4)}
    engine = ConsensusEngine(models=models, max_concurrent=2)
    await engine.query_models("topic")
    assert client.peak <= 2


@pytest.mark.asyncio
async def test_query_models_returns_empty_without_enabled_provider():
    """没有启用模型时返回空列表"""
    engine = ConsensusEngine()
    for provider in engine.models.values():
        provider.enabled = False
    assert await engine.query_models("topic") == []


@pytest.mark.asyncio
async def test_query_consensus_partial_when_some_provider_fails():
    """部分 provider 失败时状态为 partial"""
    engine = ConsensusEngine()
    engine.models["chatgpt"].client = AsyncClient()
    engine.models["claude"].client = AsyncClient(delay=0.5)
    engine.models["claude"].timeout = 0.02
    engine.models["claude"].max_retries = 1
    result = await engine.query_consensus("topic")
    assert result["status"] == STATUS_PARTIAL
    assert result["topic"] == "topic"
    assert len(result["sources"]) == 4


@pytest.mark.asyncio
async def test_query_consensus_all_failed():
    """全部 provider 失败时状态为 failed"""
    engine = ConsensusEngine()
    for provider in engine.models.values():
        provider.client = AsyncClient(delay=0.5)
        provider.timeout = 0.02
        provider.max_retries = 1
    result = await engine.query_consensus("topic")
    assert result["status"] == STATUS_FAILED


@pytest.mark.asyncio
async def test_query_consensus_global_timeout():
    """全局超时把整体查询标记为 timeout"""
    engine = ConsensusEngine()
    for provider in engine.models.values():
        provider.client = AsyncClient(delay=0.5)
        provider.timeout = 5.0
    engine.global_timeout = 0.02
    result = await engine.query_consensus("topic")
    assert result["status"] == STATUS_TIMEOUT
    assert result["error"] == "global timeout"


@pytest.mark.asyncio
async def test_query_multiple_models_returns_one_result_per_topic():
    """多 topic 并发查询，结果与输入等长"""
    engine = ConsensusEngine()
    for provider in engine.models.values():
        provider.client = AsyncClient()
    results = await engine.query_multiple_models(["tech", "market"])
    assert len(results) == 2
    assert [item["topic"] for item in results] == ["tech", "market"]
    assert all(item["status"] == STATUS_SUCCESS for item in results)


@pytest.mark.asyncio
async def test_query_multiple_models_with_empty_input():
    """空输入返回空列表"""
    engine = ConsensusEngine()
    assert await engine.query_multiple_models([]) == []


@pytest.mark.asyncio
async def test_query_multiple_models_respects_max_concurrent():
    """多 topic 查询受 max_concurrent 限流"""
    client = TrackingClient(delay=0.05)
    models = {"only": AIProvider(name="only", client=client, timeout=5.0)}
    engine = ConsensusEngine(models=models, max_concurrent=2)
    await engine.query_multiple_models([f"t{i}" for i in range(6)])
    assert client.peak <= 2


@pytest.mark.asyncio
async def test_query_multiple_models_isolates_exceptions(monkeypatch):
    """单个 topic 抛异常不影响其它 topic"""
    engine = ConsensusEngine()
    for provider in engine.models.values():
        provider.client = AsyncClient()

    async def _boom(topic):
        raise RuntimeError("boom")

    monkeypatch.setattr(engine, "query_consensus", _boom)
    results = await engine.query_multiple_models(["tech"])
    assert results[0]["status"] == STATUS_FAILED
    assert "boom" in results[0]["error"]


@pytest.mark.asyncio
async def test_parallel_query_is_faster_than_serial():
    """并发查询显著快于串行查询（延迟收益证据）"""
    client = TrackingClient(delay=0.15)
    models = {"only": AIProvider(name="only", client=client, timeout=5.0)}
    engine = ConsensusEngine(models=models)
    topics = ["a", "b", "c", "d"]

    started = time.monotonic()
    await engine.query_multiple_models(topics)
    parallel_elapsed = time.monotonic() - started

    started = time.monotonic()
    for topic in topics:
        await engine.query_consensus(topic)
    serial_elapsed = time.monotonic() - started

    assert parallel_elapsed < serial_elapsed * 0.7


# ----------------------------------------------------------------------
# 兼容层：generate_consensus
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_generate_consensus_falls_back_to_mock():
    """REAL 链路不可用时回退 mock"""
    engine = ConsensusEngine()
    result = await engine.generate_consensus("知识付费")
    assert result["mode"] == "fallback"
    assert result["topic"] == "知识付费"
    assert len(result["sources"]) == 3


@pytest.mark.asyncio
async def test_generate_consensus_uses_cache():
    """相同 topic 命中缓存"""
    engine = ConsensusEngine()
    first = await engine.generate_consensus("topic")
    second = await engine.generate_consensus("topic")
    assert first is second


@pytest.mark.asyncio
async def test_generate_consensus_mock_mode():
    """MOCK 模式直接返回 mock 响应"""
    engine = ConsensusEngine(mode=IntegrationMode.MOCK)
    result = await engine.generate_consensus("topic")
    assert result["mode"] == "mock"


@pytest.mark.asyncio
async def test_generate_consensus_real_mode_uses_clients():
    """REAL 模式在 client 可用时走真实链路"""
    engine = ConsensusEngine(mode=IntegrationMode.REAL)
    for provider in engine.models.values():
        provider.client = AsyncClient()
    result = await engine.generate_consensus("topic")
    assert result["mode"] == "real"
    assert len(result["sources"]) == 4


@pytest.mark.asyncio
async def test_real_mode_raises_when_clients_unavailable():
    """REAL 模式且无 client 时抛错（不回退）"""
    engine = ConsensusEngine(mode=IntegrationMode.REAL)
    with pytest.raises(ConnectionError):
        await engine.generate_consensus("topic")


@pytest.mark.asyncio
async def test_query_multiple_ais_real_raises_when_all_providers_fail(monkeypatch):
    """全部 provider 异常时抛 ConnectionError"""
    engine = ConsensusEngine()
    for provider in engine.models.values():
        provider.client = AsyncClient()

    async def _boom(topic, provider):
        raise RuntimeError("boom")

    monkeypatch.setattr(engine, "_call_provider_api", _boom)
    with pytest.raises(ConnectionError):
        await engine._query_multiple_ais_real("topic")


@pytest.mark.asyncio
async def test_query_multiple_ais_real_raises_without_enabled_providers(monkeypatch):
    """无启用 provider 时抛 ConnectionError"""
    monkeypatch.setenv("AI_CLIENTS_AVAILABLE", "true")
    engine = ConsensusEngine()
    for provider in engine.models.values():
        provider.enabled = False
    with pytest.raises(ConnectionError):
        await engine._query_multiple_ais_real("topic")


@pytest.mark.asyncio
async def test_query_multiple_ais_real_global_timeout(monkeypatch):
    """全局超时时抛 ConnectionError"""
    monkeypatch.setenv("AI_CLIENTS_AVAILABLE", "true")
    engine = ConsensusEngine()
    for provider in engine.models.values():
        provider.client = AsyncClient(delay=0.5)
        provider.timeout = 5.0
    engine.global_timeout = 0.02
    with pytest.raises(ConnectionError):
        await engine._query_multiple_ais_real("topic")


@pytest.mark.asyncio
async def test_query_multiple_ais_legacy_wrapper():
    """兼容旧接口走 mock 响应"""
    engine = ConsensusEngine()
    responses = await engine._query_multiple_ais("topic")
    assert len(responses) == 3


# ----------------------------------------------------------------------
# 共识整理与摘要
# ----------------------------------------------------------------------
def test_verify_consensus_too_short():
    """内容不足时给出提示"""
    engine = ConsensusEngine()
    assert engine._verify_consensus("短") == "共识内容不足，需要更多信息"


def test_verify_consensus_uncertain():
    """含不确定性关键词时给出提示"""
    engine = ConsensusEngine()
    message = "这是一个包含不确定性的很长很长的共识内容，" * 3
    assert engine._verify_consensus(message) == "共识内容存在不确定性，需要进一步验证"


def test_verify_consensus_passes():
    """正常共识原样返回"""
    engine = ConsensusEngine()
    message = "这是一个正常的长共识内容，" * 5
    assert engine._verify_consensus(message) == message


def test_get_consensus_summary():
    """摘要包含主题、版本与来源"""
    engine = ConsensusEngine()
    result = {
        "topic": "知识付费",
        "timestamp": "2026-10-23T00:00:00",
        "version": "1.3",
        "mode": "mock",
        "consensus": "共识内容",
        "sources": [{"ai": "chatgpt", "confidence": 0.9}],
    }
    summary = engine.get_consensus_summary(result)
    assert "知识付费" in summary
    assert "chatgpt" in summary
    assert "0.9" in summary


@pytest.mark.asyncio
async def test_module_level_generate_consensus():
    """模块级便捷函数可用"""
    from hermes_agent.engines.consensus_engine import generate_consensus as generate

    result = await generate("知识付费")
    assert result["topic"] == "知识付费"
