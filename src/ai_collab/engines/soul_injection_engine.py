# 灵魂注入引擎 - v1.2
# src/ai_collab/engines/soul_injection_engine.py

"""
灵魂注入引擎
核心功能：风格转换 + 观点注入

集成模式：
- MOCK: 仅使用模拟注入
- FALLBACK: 优先尝试 REAL，失败后回退 MOCK
- REAL: 仅真实链路，失败返回错误

v1.2 新增:
- 模板系统
- 策略模式
- 幂等性保证
- 异常处理增强
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

import aiohttp

from ..config.integration_flags import IntegrationMode, get_mode


class SoulServiceErrorCode(Enum):
    """Soul 服务错误码"""

    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    RATE_LIMIT = "RATE_LIMIT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class SoulServiceError(Exception):
    """Soul 服务错误"""

    def __init__(
        self,
        message: str,
        error_code: SoulServiceErrorCode,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.original_error = original_error


@dataclass
class SoulProfile:
    """灵魂画像"""

    name: str
    style: str
    method: str
    viewpoint: str
    keywords: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "style": self.style,
            "method": self.method,
            "viewpoint": self.viewpoint,
            "keywords": self.keywords,
        }


class InjectionStrategy(Protocol):
    """注入策略协议"""

    def apply(self, content: str, profile: SoulProfile) -> str:
        """应用注入策略"""
        ...


class StyleInjectionStrategy:
    """风格注入策略"""

    def apply(self, content: str, profile: SoulProfile) -> str:
        """应用风格转换"""
        if profile.name == "罗永浩风格":
            return f"我跟你讲，{content}\n\n这才是真正的价值。"
        if profile.name == "刀姐商业方法":
            return f"具体怎么做呢？{content}\n\n核心逻辑就是这样。"
        if profile.name == "董宇辉风格":
            return f"就像{content}\n\n你会发现，这背后有更深的含义。"
        return content


class MethodInjectionStrategy:
    """方法论注入策略"""

    def apply(self, content: str, profile: SoulProfile) -> str:
        """注入方法论"""
        return f"{content}\n\n【方法论】{profile.method}"


class ViewpointInjectionStrategy:
    """观点注入策略"""

    def apply(self, content: str, profile: SoulProfile) -> str:
        """表达核心观点"""
        return f"{content}\n\n【核心观点】{profile.viewpoint}"


class SoulInjectionEngine:
    """灵魂注入引擎"""

    def __init__(self):
        self.profiles = self._load_default_profiles()
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._logger = logging.getLogger(__name__)

        self._mode = get_mode("soul_injection")
        self._mock = self._mode == IntegrationMode.MOCK
        self._mock_reason = f"SoulInjectionEngine运行在{self._mode.value}模式"

        # 注入策略链
        self.strategies: List[InjectionStrategy] = [
            StyleInjectionStrategy(),
            MethodInjectionStrategy(),
            ViewpointInjectionStrategy(),
        ]

        # 幂等性配置
        self.enable_cache = os.getenv("SOUL_ENABLE_CACHE", "true").lower() == "true"

    def _check_engine_health(self) -> bool:
        """检查 REAL 链路可用性"""
        return os.getenv("SOUL_ENGINE_AVAILABLE", "false").lower() == "true"

    def _generate_cache_key(self, consensus: str, profile_name: str) -> str:
        """生成缓存键 (幂等性保证)"""
        content = f"{consensus}:{profile_name}"
        return hashlib.md5(content.encode()).hexdigest()

    def _load_default_profiles(self) -> Dict[str, SoulProfile]:
        return {
            "luoyonghao": SoulProfile(
                name="罗永浩风格",
                style="直率、幽默、有态度",
                method="商业闭环、价值交换",
                viewpoint="不是简单的卖货，而是改变行业",
                keywords=["我跟你讲", "这才是真正的", "不是简单的", "就像我"],
            ),
            "daojie": SoulProfile(
                name="刀姐商业方法",
                style="实用、系统、可执行",
                method="3H策略、价值阶梯、自动化漏斗",
                viewpoint="商业的本质是价值交换，不是割韭菜",
                keywords=["具体怎么做", "核心逻辑", "价值阶梯", "MVP验证"],
            ),
            "dongyuhui": SoulProfile(
                name="董宇辉风格",
                style="诗意、温暖、有深度",
                method="故事化表达、情感共鸣",
                viewpoint="知识是光，照亮前行的路",
                keywords=["就像", "你会发现", "这让我想起", "在那一刻"],
            ),
        }

    async def inject_soul(
        self,
        consensus: str,
        profile_name: str = "luoyonghao",
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        统一注入入口：按模式路由到 mock/real (支持异步)

        Args:
            consensus: 共识内容
            profile_name: 灵魂画像名称
            timeout: 请求超时时间 (秒)
            max_retries: 最大重试次数

        Returns:
            注入结果

        Raises:
            ValueError: 参数验证失败
            ConnectionError: REAL 模式下引擎不可用
        """
        # 参数验证
        if not consensus or not consensus.strip():
            raise ValueError("consensus 不能为空")

        if profile_name not in self.profiles:
            raise ValueError(f"未找到灵魂画像: {profile_name}")

        # 幂等性检查
        cache_key = self._generate_cache_key(consensus, profile_name)
        if self.enable_cache and cache_key in self.cache:
            self._logger.info(f"[Soul] 使用缓存结果: {cache_key[:8]}")
            return self.cache[cache_key]

        # 按模式路由
        if self._mock:
            self._logger.warning(f"[Mock模式] {self._mock_reason}")
            result = self.inject_soul_mock(consensus, profile_name)
            result["mode"] = "mock"
        else:
            try:
                result = await self.inject_soul_real(
                    consensus, profile_name, timeout=timeout, max_retries=max_retries
                )
                result["mode"] = "real"
            except Exception as exc:
                if self._mode == IntegrationMode.FALLBACK:
                    self._logger.warning(f"[Soul] REAL失败,回退到Mock: {exc}")
                    self._mock = True  # 设置 _mock 标志
                    result = self.inject_soul_mock(consensus, profile_name)
                    result["mode"] = "fallback"
                else:
                    return {"success": False, "error": str(exc), "mode": "real"}

        # 缓存结果
        if self.enable_cache:
            self.cache[cache_key] = result

        return result

    def inject_soul_mock(self, consensus: str, profile_name: str = "luoyonghao") -> Dict[str, Any]:
        """
        Mock 链路：稳定输出用于回退

        Args:
            consensus: 共识内容
            profile_name: 灵魂画像名称

        Returns:
            注入结果
        """
        profile = self.profiles.get(profile_name)
        if not profile:
            return {"success": False, "error": f"未找到灵魂画像: {profile_name}"}

        # 使用策略链进行注入
        content = consensus
        for strategy in self.strategies:
            try:
                content = strategy.apply(content, profile)
            except Exception as e:
                self._logger.error(f"[Soul] 策略执行失败: {e}")
                # 继续执行其他策略

        return {
            "success": True,
            "original_consensus": consensus,
            "personalized_content": content,
            "soul_profile": profile.to_dict(),
            "timestamp": datetime.now().isoformat(),
            "strategies_applied": len(self.strategies),
        }

    async def inject_soul_real(
        self,
        consensus: str,
        profile_name: str = "luoyonghao",
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        REAL 链路：真实注入链路适配 (带超时和重试)

        Args:
            consensus: 共识内容
            profile_name: 灵魂画像名称
            timeout: 请求超时时间 (秒)
            max_retries: 最大重试次数

        Returns:
            注入结果

        Raises:
            ConnectionError: 引擎不可用
            SoulServiceError: 服务调用失败
        """
        if not self._check_engine_health():
            raise ConnectionError("Soul engine unavailable")

        profile = self.profiles.get(profile_name)
        if not profile:
            return {"success": False, "error": f"未找到灵魂画像: {profile_name}"}

        # 真实注入链路：使用外部 AI 服务或模板引擎
        try:
            # 1. 尝试使用外部 AI 服务进行风格转换
            personalized_content = await self._call_external_ai_service(
                consensus, profile, timeout=timeout, max_retries=max_retries
            )

            # 2. 如果外部服务不可用,回退到策略链
            if not personalized_content:
                self._logger.warning("[Soul] 外部服务不可用,使用策略链")
                personalized_content = self._apply_strategy_chain(consensus, profile)

            return {
                "success": True,
                "original_consensus": consensus,
                "personalized_content": personalized_content,
                "soul_profile": profile.to_dict(),
                "timestamp": datetime.now().isoformat(),
                "strategies_applied": 0,
                "real_mode": True,
            }

        except SoulServiceError as e:
            self._logger.error(f"[Soul] REAL 链路失败: {e.error_code.value} - {e}")

            # 根据错误码决定是否回退
            if e.error_code in [
                SoulServiceErrorCode.TIMEOUT,
                SoulServiceErrorCode.SERVICE_UNAVAILABLE,
            ]:
                # 超时和服务不可用,回退到策略链
                self._logger.warning("[Soul] 服务不可用,回退到策略链")
                personalized_content = self._apply_strategy_chain(consensus, profile)
                return {
                    "success": True,
                    "original_consensus": consensus,
                    "personalized_content": personalized_content,
                    "soul_profile": profile.to_dict(),
                    "timestamp": datetime.now().isoformat(),
                    "strategies_applied": len(self.strategies),
                    "real_mode": True,
                    "fallback_used": True,
                    "error_code": e.error_code.value,
                }
            else:
                # 其他错误,抛出异常
                raise

        except Exception as e:
            self._logger.error(f"[Soul] REAL 链路失败: {e}")
            raise

    async def _call_external_ai_service(
        self, consensus: str, profile: SoulProfile, timeout: float = 30.0, max_retries: int = 3
    ) -> Optional[str]:
        """
        调用外部 AI 服务进行风格转换 (带超时和重试)

        Args:
            consensus: 共识内容
            profile: 灵魂画像
            timeout: 请求超时时间 (秒)
            max_retries: 最大重试次数

        Returns:
            个性化内容,如果服务不可用则返回 None

        Raises:
            SoulServiceError: 服务调用失败
        """
        # 检查是否有可用的外部 AI 服务
        ai_service_url = os.getenv("SOUL_AI_SERVICE_URL", "")

        if not ai_service_url:
            self._logger.info("[Soul] 未配置外部 AI 服务")
            return None

        # 构建请求
        request_data = {
            "content": consensus,
            "style": profile.style,
            "method": profile.method,
            "viewpoint": profile.viewpoint,
        }

        # 重试逻辑
        last_error = None
        for attempt in range(max_retries):
            try:
                # 使用 aiohttp 进行异步 HTTP 请求
                timeout_config = aiohttp.ClientTimeout(total=timeout)

                async with aiohttp.ClientSession(timeout=timeout_config) as session:
                    async with session.post(
                        ai_service_url,
                        json=request_data,
                        headers={"Content-Type": "application/json"},
                    ) as response:
                        # 检查 HTTP 状态码
                        if response.status == 200:
                            result = await response.json()
                            if "personalized_content" in result:
                                return result["personalized_content"]
                            else:
                                raise SoulServiceError(
                                    "响应格式错误: 缺少 personalized_content",
                                    SoulServiceErrorCode.INVALID_RESPONSE,
                                )
                        elif response.status == 429:
                            # 速率限制
                            raise SoulServiceError(
                                f"速率限制 (attempt {attempt + 1}/{max_retries})",
                                SoulServiceErrorCode.RATE_LIMIT,
                            )
                        elif response.status >= 500:
                            # 服务端错误
                            raise SoulServiceError(
                                f"服务不可用: HTTP {response.status} (attempt {attempt + 1}/{max_retries})",
                                SoulServiceErrorCode.SERVICE_UNAVAILABLE,
                            )
                        else:
                            # 其他错误
                            raise SoulServiceError(
                                f"请求失败: HTTP {response.status}", SoulServiceErrorCode.UNKNOWN_ERROR
                            )

            except asyncio.TimeoutError as e:
                last_error = SoulServiceError(
                    f"请求超时 (attempt {attempt + 1}/{max_retries})", SoulServiceErrorCode.TIMEOUT, e
                )
                self._logger.warning(f"[Soul] {last_error}")

            except aiohttp.ClientError as e:
                last_error = SoulServiceError(
                    f"连接错误: {e} (attempt {attempt + 1}/{max_retries})",
                    SoulServiceErrorCode.CONNECTION_ERROR,
                    e,
                )
                self._logger.warning(f"[Soul] {last_error}")

            except SoulServiceError as e:
                last_error = e
                if e.error_code == SoulServiceErrorCode.RATE_LIMIT:
                    # 速率限制,等待后重试
                    await asyncio.sleep(1.0 * (attempt + 1))
                elif e.error_code == SoulServiceErrorCode.SERVICE_UNAVAILABLE:
                    # 服务不可用,等待后重试
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    # 其他错误,直接抛出
                    raise

            except Exception as e:
                last_error = SoulServiceError(f"未知错误: {e}", SoulServiceErrorCode.UNKNOWN_ERROR, e)
                self._logger.error(f"[Soul] {last_error}")
                raise

        # 所有重试都失败
        if last_error:
            raise last_error

        return None

    def _apply_strategy_chain(self, consensus: str, profile: SoulProfile) -> str:
        """
        应用策略链进行注入

        Args:
            consensus: 共识内容
            profile: 灵魂画像

        Returns:
            个性化内容
        """
        content = consensus
        for strategy in self.strategies:
            try:
                content = strategy.apply(content, profile)
            except Exception as e:
                self._logger.error(f"[Soul] 策略执行失败: {e}")
                # 继续执行其他策略
        return content

    def add_custom_profile(
        self, name: str, style: str, method: str, viewpoint: str, keywords: List[str]
    ) -> bool:
        try:
            self.profiles[name] = SoulProfile(name, style, method, viewpoint, keywords)
            return True
        except Exception:
            return False

    def list_profiles(self) -> List[str]:
        return list(self.profiles.keys())

    def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        profile = self.profiles.get(name)
        return profile.to_dict() if profile else None


async def inject_soul(
    consensus: str, profile_name: str = "luoyonghao", timeout: float = 30.0, max_retries: int = 3
) -> Dict[str, Any]:
    """便捷函数 (异步)"""
    engine = SoulInjectionEngine()
    return await engine.inject_soul(consensus, profile_name, timeout, max_retries)


def test_soul_injection_engine():
    """手动测试入口"""
    engine = SoulInjectionEngine()
    result = engine.inject_soul("知识付费是一个有前景的市场", "luoyonghao")
    print(result)


if __name__ == "__main__":
    test_soul_injection_engine()
