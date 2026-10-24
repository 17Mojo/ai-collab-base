"""ConsensusEngine 并发行为契约（OpenSpec Phase 4.2 / 设计文档 §6.3）。

`ConsensusEngine.cache` 是**实例级、无锁**的普通 dict。并发调用 `generate_consensus()`
时的当前行为被本文件**钉住**——不是为了赞颂它，而是为了让后续任何改动
都能看到既有契约。真正的并发修复（加锁 / 去重）属于另一个工单，不在本次范围。

契约要点：
- 同 topic 并发：可能**重复计算**（不保证只算一次）；`cache` 里该 topic 只有 1 条
  （dict 语义决定）；各协程拿到的 `consensus` 一致，但 `timestamp` 不保证一致。
- 不同 topic 并发：互不影响，按键隔离。
- 缓存命中：重复调用走 cache 路径，不再触发 provider。
- 异常隔离：单个协程抛错不影响其余协程，引擎不进入半损坏状态。
"""

from __future__ import annotations

import asyncio

from ai_collab.engines.consensus_engine import ConsensusEngine


def _mock_engine() -> ConsensusEngine:
    engine = ConsensusEngine()
    engine._mock = True
    engine._mock_reason = "test mock mode"
    return engine


async def test_same_topic_concurrent_requests_share_one_cache_entry():
    """同 topic 并发 N 次：结果一致、cache 只有 1 条。"""
    engine = _mock_engine()
    topic = "并发主题"

    results = await asyncio.gather(*[engine.generate_consensus(topic) for _ in range(5)])

    assert len(results) == 5
    assert all(item["mode"] == "mock" for item in results)
    assert all(item["topic"] == topic for item in results)
    assert len({item["consensus"] for item in results}) == 1
    # dict 单键语义：该 topic 在 cache 里最多 1 条
    assert len(engine.cache) == 1
    assert topic in engine.cache


async def test_same_topic_concurrency_may_recompute():
    """确定性复现「同 topic 并发可能重复计算」——这是当前契约，不是 bug。

    用屏障让 5 个协程全部先 cache miss 再放行，避免依赖 sleep 时序。
    """
    engine = _mock_engine()
    topic = "重复计算主题"
    calls: list[str] = []
    arrived = 0
    all_arrived = asyncio.Event()

    async def gated(topic: str) -> list[dict]:
        nonlocal arrived
        calls.append(topic)
        arrived += 1
        if arrived == 5:
            all_arrived.set()
        await all_arrived.wait()
        return [{"ai": "probe", "response": "r" * 60, "confidence": 0.9}]

    engine._query_multiple_ais_mock = gated

    tasks = [asyncio.create_task(engine.generate_consensus(topic)) for _ in range(5)]
    results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=10)

    assert len(results) == 5
    # 5 个协程全部 miss 了缓存 → provider 被调用 5 次（不保证只算一次）
    assert len(calls) == 5
    # 但 cache 里仍然只有 1 条（dict 单键赋值不会写坏）
    assert len(engine.cache) == 1
    assert engine.cache[topic]["topic"] == topic


async def test_distinct_topics_do_not_cross_contaminate():
    """不同 topic 并发：各占 1 条，互不串味。"""
    engine = _mock_engine()
    topics = ["主题甲", "主题乙", "主题丙"]

    results = await asyncio.gather(*[engine.generate_consensus(topic) for topic in topics])

    assert set(engine.cache.keys()) == set(topics)
    for topic, result in zip(topics, results, strict=True):
        assert result["topic"] == topic
        assert topic in result["consensus"]
        for other in topics:
            if other != topic:
                assert other not in result["consensus"]


async def test_repeated_request_hits_cache_without_recomputing():
    """缓存命中语义：第二次调用走 cache，不再触发 provider。"""
    engine = _mock_engine()
    topic = "缓存主题"
    calls: list[str] = []
    original = engine._query_multiple_ais_mock

    async def counting(topic: str) -> list[dict]:
        calls.append(topic)
        return await original(topic)

    engine._query_multiple_ais_mock = counting

    first = await engine.generate_consensus(topic)
    second = await engine.generate_consensus(topic)

    assert calls == [topic], "命中缓存时不应再次调用 provider"
    assert second == first
    assert engine.cache[topic] == first


async def test_exception_in_one_coroutine_does_not_break_others():
    """并发下的异常隔离：一路抛错，其余照常完成，引擎不半损坏。"""
    engine = _mock_engine()
    original = engine._query_multiple_ais_mock

    async def flaky(topic: str) -> list[dict]:
        if topic == "会炸的主题":
            raise RuntimeError("boom")
        return await original(topic)

    engine._query_multiple_ais_mock = flaky

    outcomes = await asyncio.gather(
        engine.generate_consensus("会炸的主题"),
        engine.generate_consensus("正常主题"),
        return_exceptions=True,
    )

    assert isinstance(outcomes[0], RuntimeError)
    assert isinstance(outcomes[1], dict)
    assert outcomes[1]["topic"] == "正常主题"
    assert "正常主题" in engine.cache

    # 引擎未进入半损坏状态：后续调用照常
    after = await engine.generate_consensus("后续主题")
    assert after["topic"] == "后续主题"
    assert after["mode"] == "mock"
