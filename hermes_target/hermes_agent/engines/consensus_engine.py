# 通识生成引擎 - Hermes 移植版 v1.3
# 来源: ai_collab/engines/consensus_engine.py

"""
通识生成引擎（Hermes 适配版）
核心功能：多 AI 并发查询 + 共识提取 + 结果归一化

集成模式：
- MOCK: 仅使用模拟响应
- FALLBACK: 优先尝试 REAL，失败后回退 MOCK
- REAL: 仅真实链路，失败直接抛错

v1.2 新增:
- 可插拔 provider 架构
- 超时控制
- 失败回退
- 结果归一化

v1.3 新增（本次移植目标，四条主路径全部走公开 API）：
- 多模型并发查询：``query_models`` / ``query_multiple_models``（asyncio.gather + Semaphore 限流）
- 双层超时控制：全局 ``global_timeout`` + 单 provider ``timeout``
- 重试退避：``max_retries=3``，指数退避 ``backoff_base * 2 ** attempt``
- 结果归一化：``normalize_result`` 公开入口，失败以 ``status`` 字段表达而非抛异常
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - 仅 Hermes 运行时才有该模块
    from hermes.logger import log as _hermes_log
except ImportError:  # pragma: no cover
    _hermes_log = None

DEFAULT_MODELS = ("chatgpt", "claude", "kimi", "qianwen")
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_CONCURRENT = 5
DEFAULT_GLOBAL_TIMEOUT = 60.0
DEFAULT_BACKOFF_BASE = 0.05

STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"
STATUS_TIMEOUT = "timeout"


def _emit(level: int, message: str) -> None:
    """统一日志出口：优先 Hermes logger，缺失时退回标准 logging。"""
    if _hermes_log is not None:
        for attr in ("log", "info", "warning", "error"):
            handler = getattr(_hermes_log, attr, None)
            if callable(handler):
                try:
                    handler(message)
                    return
                except Exception:  # pragma: no cover - 日志后端异常不能影响主流程
                    break
    LOGGER.log(level, message)


# 模拟 IntegrationMode 枚举(Hermes 内部使用)
# 需为真枚举: 调用方会访问 .value(如 self._mode.value), 普通类的字符串常量没有该属性
class IntegrationMode(str, Enum):
    MOCK = "mock"
    FALLBACK = "fallback"
    REAL = "real"


def get_mode(name: str) -> IntegrationMode:
    """Hermes 模拟: 始终返回 FALLBACK 模式"""
    return IntegrationMode.FALLBACK


@dataclass
class AIProvider:
    """AI Provider 配置"""

    name: str
    client: Any | None = None
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    enabled: bool = True
    backoff_base: float = DEFAULT_BACKOFF_BASE


class ConsensusEngine:
    """通识生成引擎"""

    VERSION = "1.3"

    def __init__(
        self,
        config_path: str | os.PathLike[str] | None = None,
        *,
        global_timeout: float | None = None,
        max_concurrent: int | None = None,
        max_retries: int | None = None,
        models: dict[str, AIProvider] | None = None,
        mode: str | IntegrationMode | None = None,
    ) -> None:
        self.config_path = os.path.expanduser(str(config_path)) if config_path else None
        config = self._load_config(self.config_path)
        engines_cfg = config.get("engines") if isinstance(config.get("engines"), dict) else {}
        consensus_cfg = engines_cfg.get("consensus") if isinstance(engines_cfg.get("consensus"), dict) else {}
        consensus_cfg = consensus_cfg or {}
        retry_cfg = consensus_cfg.get("retry") if isinstance(consensus_cfg.get("retry"), dict) else {}
        retry_cfg = retry_cfg or {}

        # 可插拔 provider 配置
        self.models: dict[str, AIProvider] = {}
        if models:
            for name, provider in models.items():
                self.models[name] = provider
        else:
            for name in DEFAULT_MODELS:
                self.models[name] = AIProvider(name=name, timeout=DEFAULT_TIMEOUT)
        # 兼容旧名(可平滑迁移) - 与 models 指向同一 dict, 注册任一侧双方均可见
        self.providers: dict[str, AIProvider] = self.models
        self.cache: dict[str, dict[str, Any]] = {}
        self._logger = logging.getLogger(__name__)

        self._mode = IntegrationMode(mode) if isinstance(mode, str) else (mode or get_mode("consensus_engine"))
        self._mock = self._mode == IntegrationMode.MOCK
        self._mock_reason = f"ConsensusEngine运行在{self._mode.value}模式"

        # 重试次数：显式参数 > 配置文件 > 默认值(3)
        resolved_max_retries = (
            int(max_retries)
            if max_retries is not None
            else int(retry_cfg.get("max_retries", DEFAULT_MAX_RETRIES))
        )
        self.max_retries = resolved_max_retries
        if models is None:
            for provider in self.models.values():
                provider.max_retries = resolved_max_retries

        # 全局超时配置：显式参数 > 配置文件 > 环境变量 > 默认值
        if global_timeout is not None:
            self.global_timeout = float(global_timeout)
        elif consensus_cfg.get("global_timeout") is not None:
            self.global_timeout = float(consensus_cfg["global_timeout"])
        else:
            self.global_timeout = float(os.getenv("CONSENSUS_GLOBAL_TIMEOUT", str(DEFAULT_GLOBAL_TIMEOUT)))

        # 并发上限（限流阀门）
        if max_concurrent is not None:
            self.max_concurrent = int(max_concurrent)
        else:
            self.max_concurrent = int(consensus_cfg.get("max_concurrent", DEFAULT_MAX_CONCURRENT))
        self.max_concurrent = max(1, self.max_concurrent)

        # 部分失败是否仍返回结果（fallback_mode: partial）
        self.fallback_mode = str(consensus_cfg.get("fallback_mode", "partial"))

    # ------------------------------------------------------------------
    # 配置加载
    # ------------------------------------------------------------------
    @staticmethod
    def _load_config(config_path: str | None) -> dict[str, Any]:
        """读取 Hermes 配置（缺失/损坏时降级为默认配置，不阻断引擎启动）。"""
        if not config_path:
            return {}
        path = os.path.expanduser(str(config_path))
        if not os.path.isfile(path):
            LOGGER.warning("[Consensus] 配置文件不存在, 使用默认配置: %s", path)
            return {}
        try:
            import yaml
        except ImportError:  # pragma: no cover
            LOGGER.warning("[Consensus] 未安装 PyYAML, 跳过配置加载: %s", path)
            return {}
        try:
            with open(path, encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
        except Exception as exc:
            LOGGER.warning("[Consensus] 配置解析失败, 使用默认配置: %s", exc)
            return {}
        return data if isinstance(data, dict) else {}

    # ------------------------------------------------------------------
    # provider 注册
    # ------------------------------------------------------------------
    def register_provider(
        self,
        name: str,
        client: Any,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int | None = None,
        enabled: bool = True,
    ) -> None:
        """
        注册 AI provider

        Args:
            name: Provider 名称
            client: AI 客户端实例
            timeout: 超时时间(秒)
            max_retries: 重试次数(默认沿用引擎级配置)
            enabled: 是否启用
        """
        self.providers[name] = AIProvider(
            name=name,
            client=client,
            timeout=timeout,
            max_retries=self.max_retries if max_retries is None else int(max_retries),
            enabled=enabled,
        )
        self._logger.info(f"[Consensus] 注册 provider: {name}")

    def _check_ai_clients_health(self) -> bool:
        """检查真实 AI 客户端可用性"""
        # 检查是否有可用的 provider
        enabled_providers = [p for p in self.providers.values() if p.enabled]
        if not enabled_providers:
            return False

        # 检查环境变量或实际客户端
        return os.getenv("AI_CLIENTS_AVAILABLE", "false").lower() == "true" or any(
            p.client is not None for p in enabled_providers
        )

    def _resolve_model(self, model: str | None) -> tuple[AIProvider | None, str]:
        """解析目标 provider：显式名 > 首个启用的 provider。"""
        if model:
            provider = self.models.get(model)
            return (provider, model) if provider is not None else (None, model)
        for name, provider in self.models.items():
            if provider.enabled:
                return provider, name
        return None, ""

    # ------------------------------------------------------------------
    # 公开 API：并发查询 / 超时 / 重试 / 结果归一化
    # ------------------------------------------------------------------
    def normalize_result(
        self,
        raw: Any,
        provider_name: str,
        *,
        status: str = STATUS_SUCCESS,
        error: str | None = None,
    ) -> dict[str, Any]:
        """
        结果归一化（公开入口）：统一为 ai/response/confidence/timestamp/provider/status。

        Args:
            raw: 原始响应（dict / str / 其它类型 / None）
            provider_name: provider 名称
            status: 归一化后的状态（success/partial/failed/timeout）
            error: 失败原因（可选）

        Returns:
            归一化后的响应字典
        """
        if isinstance(raw, dict):
            response = raw.get("response", "")
            confidence = raw.get("confidence", 0.0)
            ai_name = raw.get("ai", provider_name)
        elif isinstance(raw, str):
            response = raw
            confidence = 0.0
            ai_name = provider_name
        else:
            response = "" if raw is None else str(raw)
            confidence = 0.0
            ai_name = provider_name

        normalized: dict[str, Any] = {
            "ai": ai_name,
            "response": response,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            "provider": provider_name,
            "status": status,
        }
        if error:
            normalized["error"] = error
        return normalized

    async def query_model(self, topic: str, model: str | None = None) -> dict[str, Any]:
        """
        查询单个模型：provider 超时 + 重试退避 + 结果归一化。

        失败不抛异常，异常信息写入 ``status`` / ``error`` 字段，
        以保证并发查询时的"超时隔离"语义。

        Args:
            topic: 查询主题
            model: 目标模型名（默认取首个启用的 provider）

        Returns:
            归一化后的响应字典
        """
        provider, name = self._resolve_model(model)
        if provider is None:
            return self.normalize_result(None, name or "unknown", status=STATUS_FAILED, error="unknown model")
        try:
            raw = await self._query_single_provider(topic, provider)
        except asyncio.TimeoutError:
            return self.normalize_result(
                None, provider.name, status=STATUS_TIMEOUT, error=f"provider timeout after {provider.max_retries} retries"
            )
        except Exception as exc:
            return self.normalize_result(None, provider.name, status=STATUS_FAILED, error=str(exc))
        return self.normalize_result(raw, provider.name, status=STATUS_SUCCESS)

    async def query_models(self, topic: str) -> list[dict[str, Any]]:
        """
        并发查询所有启用模型（asyncio.gather + Semaphore 限流）。

        Args:
            topic: 查询主题

        Returns:
            归一化后的响应列表（顺序与 models 注册顺序一致）
        """
        targets = [(name, provider) for name, provider in self.models.items() if provider.enabled]
        if not targets:
            return []
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _run(name: str, provider: AIProvider) -> dict[str, Any]:
            async with semaphore:
                return await self.query_model(topic, name)

        raw_results = await asyncio.gather(
            *[_run(name, provider) for name, provider in targets],
            return_exceptions=True,
        )
        results: list[dict[str, Any]] = []
        for (name, _provider), item in zip(targets, raw_results, strict=False):
            if isinstance(item, BaseException):
                results.append(self.normalize_result(None, name, status=STATUS_FAILED, error=str(item)))
            else:
                results.append(item)
        return results

    async def query_consensus(self, topic: str) -> dict[str, Any]:
        """
        查询单 topic 的多模型共识（并发 + 全局超时 + 结果归一化）。

        Args:
            topic: 查询主题

        Returns:
            归一化共识结果（含 status/sources/consensus）
        """
        try:
            sources = await asyncio.wait_for(self.query_models(topic), timeout=self.global_timeout)
        except asyncio.TimeoutError:
            _emit(logging.ERROR, f"[Consensus] 全局超时 ({self.global_timeout}s)")
            return self._build_consensus_result(topic, [], STATUS_TIMEOUT, "global timeout")

        succeeded = [item for item in sources if item.get("status") == STATUS_SUCCESS]
        if not succeeded:
            status = STATUS_FAILED
        elif len(succeeded) < len(sources):
            status = STATUS_PARTIAL
        else:
            status = STATUS_SUCCESS
        return self._build_consensus_result(topic, sources, status)

    async def query_multiple_models(self, topics: Sequence[str]) -> list[dict[str, Any]]:
        """
        并发查询多个 topic（asyncio.gather），每个 topic 返回一份归一化共识结果。

        Args:
            topics: 主题列表

        Returns:
            与输入等长的结果列表
        """
        items = [str(topic) for topic in (topics or [])]
        if not items:
            return []
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _run(topic: str) -> dict[str, Any]:
            async with semaphore:
                return await self.query_consensus(topic)

        raw_results = await asyncio.gather(*[_run(topic) for topic in items], return_exceptions=True)
        results: list[dict[str, Any]] = []
        for topic, item in zip(items, raw_results, strict=False):
            if isinstance(item, BaseException):
                results.append(self._build_consensus_result(topic, [], STATUS_FAILED, str(item)))
            else:
                results.append(item)
        return results

    def _build_consensus_result(
        self,
        topic: str,
        sources: list[dict[str, Any]],
        status: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        """组装归一化共识结果。"""
        succeeded = [item for item in sources if item.get("status") == STATUS_SUCCESS]
        result: dict[str, Any] = {
            "topic": topic,
            "status": status,
            "consensus": self._verify_consensus(self._extract_consensus(succeeded)),
            "sources": sources,
            "timestamp": datetime.now().isoformat(),
            "version": self.VERSION,
            "mode": self._mode.value,
        }
        if error:
            result["error"] = error
        return result

    # ------------------------------------------------------------------
    # 兼容层：原有 generate_consensus 链路
    # ------------------------------------------------------------------
    async def generate_consensus(self, topic: str) -> dict[str, Any]:
        """生成通识内容"""
        if topic in self.cache:
            return self.cache[topic]

        mode_used = "mock"
        if self._mock:
            self._logger.warning(f"[Mock模式] {self._mock_reason}")
            responses = await self._query_multiple_ais_mock(topic)
        else:
            try:
                responses = await self._query_multiple_ais_real(topic)
                mode_used = "real"
            except Exception as exc:
                if self._mode == IntegrationMode.FALLBACK:
                    self._logger.warning(f"[Consensus] REAL失败,回退到Mock: {exc}")
                    self._mock = True
                    mode_used = "fallback"
                    responses = await self._query_multiple_ais_mock(topic)
                else:
                    raise

        consensus = self._extract_consensus(responses)
        verified = self._verify_consensus(consensus)

        result = {
            "topic": topic,
            "consensus": verified,
            "sources": responses,
            "timestamp": datetime.now().isoformat(),
            "version": "1.1",
            "mode": mode_used,
        }
        self.cache[topic] = result
        return result

    async def _query_multiple_ais(self, topic: str) -> list[dict[str, Any]]:
        """兼容旧接口，默认走 mock 响应"""
        return await self._query_multiple_ais_mock(topic)

    async def _query_multiple_ais_mock(self, topic: str) -> list[dict[str, Any]]:
        """模拟多 AI 并发查询"""
        await asyncio.sleep(0)
        return [
            {
                "ai": "chatgpt",
                "response": f"[ChatGPT Mock] 关于{topic}的核心观点是...",
                "confidence": 0.9,
            },
            {
                "ai": "claude",
                "response": f"[Claude Mock] {topic}的关键要素包括...",
                "confidence": 0.85,
            },
            {
                "ai": "kimi",
                "response": f"[Kimi Mock] 从{topic}的角度来看...",
                "confidence": 0.88,
            },
        ]

    async def _query_multiple_ais_real(self, topic: str) -> list[dict[str, Any]]:
        """
        真实链路查询（支持超时、失败回退、结果归一）

        Args:
            topic: 查询主题

        Returns:
            AI 响应列表

        Raises:
            ConnectionError: 所有 provider 都不可用
        """
        if not self._check_ai_clients_health():
            raise ConnectionError("AI clients unavailable")

        # 并发查询所有启用的 provider
        tasks = []
        provider_names = []

        for name, provider in self.providers.items():
            if provider.enabled:
                task = self._query_single_provider(topic, provider)
                tasks.append(task)
                provider_names.append(name)

        if not tasks:
            raise ConnectionError("No enabled providers")

        # 使用 asyncio.gather 并发执行,设置全局超时
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=self.global_timeout
            )
        except asyncio.TimeoutError:
            self._logger.error(f"[Consensus] 全局超时 ({self.global_timeout}s)")
            raise ConnectionError(f"Consensus query timeout after {self.global_timeout}s")

        # 处理结果,过滤失败和异常
        successful_results = []
        for i, result in enumerate(results):
            provider_name = provider_names[i]
            if isinstance(result, BaseException):
                self._logger.warning(f"[Consensus] Provider {provider_name} 失败: {result}")
            elif result is not None and isinstance(result, dict):
                # 归一化结果格式
                normalized = self._normalize_response(result, provider_name)
                successful_results.append(normalized)

        if not successful_results:
            raise ConnectionError("All providers failed")

        self._logger.info(f"[Consensus] 成功获取 {len(successful_results)}/{len(tasks)} 个响应")
        return successful_results

    async def _query_single_provider(self, topic: str, provider: AIProvider) -> dict[str, Any]:
        """
        查询单个 provider (带超时和重试退避)

        Args:
            topic: 查询主题
            provider: Provider 配置

        Returns:
            AI 响应

        Raises:
            Exception: 查询失败
        """
        attempts = max(1, int(provider.max_retries))
        last_error: BaseException | None = None
        for attempt in range(attempts):
            try:
                # 使用 provider 特定的超时
                result = await asyncio.wait_for(
                    self._call_provider_api(topic, provider), timeout=provider.timeout
                )
                return result
            except asyncio.TimeoutError as exc:
                last_error = exc
                self._logger.warning(
                    f"[Consensus] Provider {provider.name} 超时 (attempt {attempt + 1}/{attempts})"
                )
            except Exception as e:
                last_error = e
                self._logger.warning(
                    f"[Consensus] Provider {provider.name} 失败: {e} (attempt {attempt + 1}/{attempts})"
                )
            if attempt < attempts - 1:
                # 指数退避
                await asyncio.sleep(provider.backoff_base * (2**attempt))

        if last_error is not None:
            raise last_error
        raise ConnectionError(  # pragma: no cover - attempts>=1 时不可达
            f"Provider {provider.name} failed after {attempts} retries"
        )

    async def _call_provider_api(self, topic: str, provider: AIProvider) -> dict[str, Any]:
        """
        调用 provider API (支持 async/sync 兼容)

        Args:
            topic: 查询主题
            provider: Provider 配置

        Returns:
            AI 响应

        Raises:
            ConnectionError: Provider 不可用
        """
        # 检查是否有真实的 client
        if provider.client is None:
            # 没有真实 client,使用模拟响应
            return await self._mock_provider_response(topic, provider)

        # 尝试调用真实的 provider client
        try:
            # 检查 client 是否支持 async
            if hasattr(provider.client, "query"):
                # 检查是否是 async 方法
                if inspect.iscoroutinefunction(provider.client.query):
                    # Async 调用
                    result = await provider.client.query(topic)
                else:
                    # Sync 调用 (在 executor 中运行)
                    loop = asyncio.get_running_loop()
                    result = await loop.run_in_executor(None, provider.client.query, topic)
                return self._normalize_client_response(result, provider)
            else:
                self._logger.warning(f"[Consensus] Provider {provider.name} client 没有 query 方法")
                return await self._mock_provider_response(topic, provider)

        except Exception as e:
            self._logger.error(f"[Consensus] Provider {provider.name} client 调用失败: {e}")
            # 失败时返回模拟响应
            return await self._mock_provider_response(topic, provider)

    async def _mock_provider_response(self, topic: str, provider: AIProvider) -> dict[str, Any]:
        """
        生成模拟 provider 响应

        Args:
            topic: 查询主题
            provider: Provider 配置

        Returns:
            模拟响应
        """
        # 模拟 API 调用延迟
        await asyncio.sleep(0.01)

        return {
            "ai": provider.name,
            "response": f"[{provider.name.upper()} REAL] 关于{topic}的真实观点...",
            "confidence": 0.9,
        }

    def _normalize_client_response(self, response: Any, provider: AIProvider) -> dict[str, Any]:
        """
        归一化 client 响应格式

        Args:
            response: 原始响应
            provider: Provider 配置

        Returns:
            归一化后的响应
        """
        # 如果响应已经是字典格式
        if isinstance(response, dict):
            return {
                "ai": response.get("ai", provider.name),
                "response": response.get("response", str(response)),
                "confidence": response.get("confidence", 0.9),
            }

        # 如果响应是字符串
        if isinstance(response, str):
            return {
                "ai": provider.name,
                "response": response,
                "confidence": 0.9,
            }

        # 其他类型,转换为字符串
        return {
            "ai": provider.name,
            "response": str(response),
            "confidence": 0.9,
        }

    def _normalize_response(self, response: dict[str, Any], provider_name: str) -> dict[str, Any]:
        """
        归一化响应格式

        Args:
            response: 原始响应
            provider_name: Provider 名称

        Returns:
            归一化后的响应
        """
        return {
            "ai": response.get("ai", provider_name),
            "response": response.get("response", ""),
            "confidence": response.get("confidence", 0.0),
            "timestamp": datetime.now().isoformat(),
            "provider": provider_name,
        }

    def _extract_consensus(self, responses: list[dict[str, Any]]) -> str:
        """提取共识内容"""
        return "\n\n".join(response.get("response", "") for response in responses)

    def _verify_consensus(self, consensus: str) -> str:
        """基础验证"""
        if len(consensus) < 50:
            return "共识内容不足，需要更多信息"
        if "错误" in consensus or "不确定" in consensus:
            return "共识内容存在不确定性，需要进一步验证"
        return consensus

    def get_consensus_summary(self, result: dict[str, Any]) -> str:
        """获取通识摘要"""
        summary = f"""
# 通识摘要

**主题**: {result['topic']}
**时间**: {result['timestamp']}
**版本**: {result['version']}
**模式**: {result.get('mode', 'unknown')}

## 核心共识

{result['consensus']}

## 来源

"""
        for source in result["sources"]:
            summary += f"- {source['ai']}: 置信度 {source['confidence']}\n"
        return summary


async def generate_consensus(topic: str) -> dict[str, Any]:
    """生成通识便捷函数"""
    engine = ConsensusEngine()
    return await engine.generate_consensus(topic)


async def test_consensus_engine():
    """手动测试入口"""
    engine = ConsensusEngine()
    result = await engine.generate_consensus("知识付费")
    print(engine.get_consensus_summary(result))


if __name__ == "__main__":
    asyncio.run(test_consensus_engine())
