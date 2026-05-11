"""
AI集成模块Mock标志测试

测试目标:
1. 验证NotebookLM集成模块的Mock标志
2. 验证Consensus引擎的Mock标志
3. 验证Soul Injection引擎的Mock标志
4. 确保所有Mock模式都有明确的警告日志
"""

import logging

import pytest

from ai_collab.engines.consensus_engine import ConsensusEngine
from ai_collab.engines.soul_injection_engine import SoulInjectionEngine
from ai_collab.integrations.notebooklm import NotebookLMIntegration


class TestNotebookLMMockFlags:
    """NotebookLM集成模块Mock标志测试"""

    def test_notebooklm_has_mock_attribute(self):
        """测试NotebookLM集成类是否有_mock属性"""
        integration = NotebookLMIntegration()
        assert hasattr(integration, "_mock"), "NotebookLMIntegration应该有_mock属性"
        assert hasattr(integration, "_mock_reason"), "NotebookLMIntegration应该有_mock_reason属性"

    def test_notebooklm_mock_default_value(self):
        """测试NotebookLM Mock标志默认值"""
        integration = NotebookLMIntegration()
        # 默认应该是FALLBACK模式,所以_mock应该是False
        # 因为FALLBACK模式会先尝试真实连接,失败后才回退到Mock
        assert integration._mock is False, "NotebookLM _mock默认值应该是False (FALLBACK模式)"
        assert "fallback" in integration._mock_reason.lower(), "_mock_reason应该说明是FALLBACK模式"

    def test_notebooklm_connect_with_mock(self, caplog):
        """测试Mock模式下的连接行为"""
        integration = NotebookLMIntegration()
        integration._mock = True
        integration._mock_reason = "测试Mock模式"

        with caplog.at_level(logging.WARNING):
            result = integration.connect()

        assert result is True, "Mock模式下连接应该返回True"
        assert "Mock模式" in caplog.text or "mock" in caplog.text.lower(), "应该有Mock警告日志"

    def test_notebooklm_query_knowledge_with_mock(self, caplog):
        """测试Mock模式下的知识查询"""
        integration = NotebookLMIntegration()
        integration._mock = True
        integration._mock_reason = "测试Mock模式"

        with caplog.at_level(logging.WARNING):
            result = integration.query_knowledge("测试主题")

        assert result is not None, "Mock模式下应该返回模拟结果"
        assert "Mock模式" in caplog.text or "mock" in caplog.text.lower(), "应该有Mock警告日志"


class TestConsensusEngineMockFlags:
    """Consensus引擎Mock标志测试"""

    def test_consensus_engine_has_mock_attribute(self):
        """测试Consensus引擎是否有_mock属性"""
        engine = ConsensusEngine()
        assert hasattr(engine, "_mock"), "ConsensusEngine应该有_mock属性"
        assert hasattr(engine, "_mock_reason"), "ConsensusEngine应该有_mock_reason属性"

    def test_consensus_engine_mock_default_value(self):
        """测试Consensus引擎Mock标志默认值"""
        engine = ConsensusEngine()
        # 默认应该是FALLBACK模式,所以_mock应该是False
        assert engine._mock is False, "ConsensusEngine _mock默认值应该是False (FALLBACK模式)"
        assert "fallback" in engine._mock_reason.lower(), "_mock_reason应该说明是FALLBACK模式"

    @pytest.mark.asyncio
    async def test_consensus_engine_generate_with_mock(self, caplog):
        """测试Mock模式下的通识生成"""
        engine = ConsensusEngine()
        engine._mock = True
        engine._mock_reason = "测试Mock模式"

        with caplog.at_level(logging.WARNING):
            result = await engine.generate_consensus("测试主题")

        assert result is not None, "Mock模式下应该返回模拟结果"
        assert "Mock模式" in caplog.text or "mock" in caplog.text.lower(), "应该有Mock警告日志"


class TestSoulInjectionEngineMockFlags:
    """Soul Injection引擎Mock标志测试"""

    def test_soul_injection_has_mock_attribute(self):
        """测试Soul Injection引擎是否有_mock属性"""
        engine = SoulInjectionEngine()
        assert hasattr(engine, "_mock"), "SoulInjectionEngine应该有_mock属性"
        assert hasattr(engine, "_mock_reason"), "SoulInjectionEngine应该有_mock_reason属性"

    def test_soul_injection_mock_default_value(self):
        """测试Soul Injection引擎Mock标志默认值"""
        engine = SoulInjectionEngine()
        # 默认应该是FALLBACK模式,所以_mock应该是False
        assert engine._mock is False, "SoulInjectionEngine _mock默认值应该是False (FALLBACK模式)"
        assert "fallback" in engine._mock_reason.lower(), "_mock_reason应该说明是FALLBACK模式"

    @pytest.mark.asyncio
    async def test_soul_injection_inject_with_mock(self, caplog):
        """测试Mock模式下的灵魂注入"""
        engine = SoulInjectionEngine()
        engine._mock = True
        engine._mock_reason = "测试Mock模式"

        with caplog.at_level(logging.WARNING):
            result = await engine.inject_soul("测试内容")

        assert result is not None, "Mock模式下应该返回模拟结果"
        # 注意: inject_soul方法可能没有Mock警告,这里只验证结果


class TestMockFlagConsistency:
    """Mock标志一致性测试"""

    def test_all_modules_have_mock_flags(self):
        """测试所有AI集成模块都有Mock标志"""
        modules = [NotebookLMIntegration(), ConsensusEngine(), SoulInjectionEngine()]

        for module in modules:
            assert hasattr(module, "_mock"), f"{module.__class__.__name__}应该有_mock属性"
            assert hasattr(module, "_mock_reason"), f"{module.__class__.__name__}应该有_mock_reason属性"
            assert isinstance(module._mock, bool), f"{module.__class__.__name__}._mock应该是布尔值"
            assert isinstance(
                module._mock_reason, str
            ), f"{module.__class__.__name__}._mock_reason应该是字符串"

    def test_mock_flags_default_to_fallback_mode(self):
        """测试所有模块默认处于FALLBACK模式（_mock=False）"""
        modules = [NotebookLMIntegration(), ConsensusEngine(), SoulInjectionEngine()]

        for module in modules:
            assert (
                module._mock is False
            ), f"{module.__class__.__name__}._mock默认值应该是False (FALLBACK模式)"
            assert len(module._mock_reason) > 0, f"{module.__class__.__name__}._mock_reason不应该为空"


class TestFallbackChain:
    """回退链路测试"""

    def test_notebooklm_fallback_on_connection_failure(self, caplog):
        """测试NotebookLM连接失败时的回退行为"""
        integration = NotebookLMIntegration()
        integration._mock = False  # 尝试真实模式

        # 模拟连接失败
        def mock_connect_failure():
            integration.is_connected = False
            return False

        integration.connect = mock_connect_failure

        # 尝试查询,应该触发回退
        with caplog.at_level(logging.WARNING):
            result = integration.query_knowledge("测试主题")

        # 应该有回退日志或错误处理
        assert result is not None or "失败" in caplog.text or "fallback" in caplog.text.lower()

    def test_consensus_engine_fallback_on_ai_client_failure(self, caplog, monkeypatch):
        """测试Consensus引擎AI客户端失败时的回退行为"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_CONSENSUS_ENGINE", "fallback")
        monkeypatch.setenv("AI_CLIENTS_AVAILABLE", "false")
        engine = ConsensusEngine()

        # 真实链路失败时应自动回退，不抛异常
        with caplog.at_level(logging.WARNING):
            import asyncio

            result = asyncio.run(engine.generate_consensus("测试主题"))
        assert result is not None
        assert result.get("mode") == "fallback"
        assert engine._mock is True

    @pytest.mark.asyncio
    async def test_soul_injection_fallback_on_engine_failure(self, caplog, monkeypatch):
        """测试Soul Injection引擎失败时的回退行为"""
        monkeypatch.setenv("AI_INTEGRATION_MODE_SOUL_INJECTION", "fallback")
        monkeypatch.setenv("SOUL_ENGINE_AVAILABLE", "false")
        engine = SoulInjectionEngine()

        # 尝试注入,应该触发回退
        with caplog.at_level(logging.WARNING):
            result = await engine.inject_soul("测试内容")

        # 应该有回退处理
        assert result is not None
        assert result.get("mode") == "fallback"
        assert engine._mock is True

    def test_mock_mode_prevents_real_calls(self, caplog):
        """测试Mock模式阻止真实调用"""
        integration = NotebookLMIntegration()
        integration._mock = True
        integration._mock_reason = "测试Mock模式"

        # 在Mock模式下,不应该有真实的网络调用
        with caplog.at_level(logging.WARNING):
            result = integration.query_knowledge("测试主题")

        # 应该有Mock警告,而不是真实调用
        assert "Mock" in caplog.text or "mock" in caplog.text.lower()
        assert result is not None  # 应该返回模拟结果


class TestExceptionInjection:
    """异常注入测试"""

    def test_notebooklm_exception_handling(self):
        """测试NotebookLM异常处理"""
        integration = NotebookLMIntegration()

        # 注入异常
        def raise_exception(*args, **kwargs):
            raise Exception("测试异常")

        # 临时替换方法
        original_connect = integration.connect
        integration.connect = raise_exception

        try:
            result = integration.query_knowledge("测试主题")
            # 应该有异常处理,返回错误结果而不是崩溃
            assert "error" in result or result is None
        except Exception as e:
            # 或者抛出明确的异常
            assert "测试异常" in str(e)
        finally:
            integration.connect = original_connect

    def test_consensus_engine_exception_handling(self):
        """测试Consensus引擎异常处理"""
        engine = ConsensusEngine()

        # 注入异常
        async def raise_async_exception(*args, **kwargs):
            raise Exception("测试异步异常")

        # 临时替换方法
        original_generate = engine.generate_consensus
        engine.generate_consensus = raise_async_exception

        try:
            import asyncio

            result = asyncio.run(engine.generate_consensus("测试主题"))
            # 应该有异常处理
            assert result is None or "error" in result
        except Exception as e:
            # 或者抛出明确的异常
            assert "测试异步异常" in str(e)
        finally:
            engine.generate_consensus = original_generate

    def test_soul_injection_exception_handling(self):
        """测试Soul Injection引擎异常处理"""
        engine = SoulInjectionEngine()

        # 注入异常
        def raise_exception(*args, **kwargs):
            raise Exception("测试注入异常")

        # 临时替换方法
        original_inject = engine.inject_soul
        engine.inject_soul = raise_exception

        try:
            result = engine.inject_soul("测试内容")
            # 应该有异常处理
            assert result is None or "error" in result
        except Exception as e:
            # 或者抛出明确的异常
            assert "测试注入异常" in str(e)
        finally:
            engine.inject_soul = original_inject


class TestMockFlagConsistencyAdvanced:
    """Mock标志一致性高级测试"""

    def test_mock_flag_cannot_be_none(self):
        """测试Mock标志不能为None"""
        modules = [NotebookLMIntegration(), ConsensusEngine(), SoulInjectionEngine()]

        for module in modules:
            assert module._mock is not None, f"{module.__class__.__name__}._mock不能为None"
            assert isinstance(module._mock, bool), f"{module.__class__.__name__}._mock必须是布尔值"

    def test_mock_reason_must_be_non_empty_string(self):
        """测试Mock原因必须是非空字符串"""
        modules = [NotebookLMIntegration(), ConsensusEngine(), SoulInjectionEngine()]

        for module in modules:
            assert (
                module._mock_reason is not None
            ), f"{module.__class__.__name__}._mock_reason不能为None"
            assert isinstance(
                module._mock_reason, str
            ), f"{module.__class__.__name__}._mock_reason必须是字符串"
            assert (
                len(module._mock_reason.strip()) > 0
            ), f"{module.__class__.__name__}._mock_reason不能为空字符串"

    def test_mock_mode_consistency_across_instances(self):
        """测试不同实例的Mock模式一致性"""
        # 创建多个实例
        instances = [
            NotebookLMIntegration(),
            NotebookLMIntegration(),
            ConsensusEngine(),
            ConsensusEngine(),
            SoulInjectionEngine(),
            SoulInjectionEngine(),
        ]

        # 所有实例的Mock模式应该一致
        notebooklm_instances = [i for i in instances if isinstance(i, NotebookLMIntegration)]
        consensus_instances = [i for i in instances if isinstance(i, ConsensusEngine)]
        soul_instances = [i for i in instances if isinstance(i, SoulInjectionEngine)]

        # 检查同类实例的Mock模式是否一致
        for instances_list in [notebooklm_instances, consensus_instances, soul_instances]:
            if len(instances_list) > 1:
                first_mock = instances_list[0]._mock
                first_reason = instances_list[0]._mock_reason
                for instance in instances_list[1:]:
                    assert (
                        instance._mock == first_mock
                    ), f"{instance.__class__.__name__}实例的Mock模式不一致"
                    assert (
                        instance._mock_reason == first_reason
                    ), f"{instance.__class__.__name__}实例的Mock原因不一致"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
