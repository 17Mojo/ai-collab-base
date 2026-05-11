"""
通识生成 API 路由
"""

import sys
from pathlib import Path

# Add parent directory to sys.path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/consensus", tags=["consensus"])


class ConsensusRequest(BaseModel):
    """通识生成请求"""

    topic: str
    providers: Optional[List[str]] = None
    timeout: Optional[float] = 30.0
    # 新增：Chrome发送的真实响应（混合模式）
    real_responses: Optional[List[Dict[str, Any]]] = None


class RealResponseItem(BaseModel):
    """真实AI响应项（来自Chrome）"""

    platform: str  # 平台ID（如kimi.com, chatgpt.com）
    content: str  # AI响应内容
    confidence: Optional[float] = 0.9


class ConsensusResponse(BaseModel):
    """通识生成响应"""

    topic: str
    consensus: str
    sources: List[Dict[str, Any]]
    timestamp: str
    version: str
    mode: str


class ProvidersResponse(BaseModel):
    """Provider 列表响应"""

    providers: List[str]
    defaults: List[str]


@router.post("/generate", response_model=ConsensusResponse)
async def generate_consensus(request: ConsensusRequest):
    """
    生成通识内容

    从多个 AI Provider 并发查询，提取共识内容

    混合模式支持：
    - 如果提供 real_responses（来自Chrome），直接使用真实响应进行共识提取
    - 否则使用本地 Mock 或调用 API

    Args:
        request: 包含 topic、可选 providers、timeout、可选 real_responses

    Returns:
        包含 consensus、sources、mode 等信息
    """
    from ai_collab.engines.consensus_engine import ConsensusEngine

    try:
        engine = ConsensusEngine()

        # 混合模式：使用Chrome发送的真实响应
        if request.real_responses:
            # 格式化为引擎期望的格式
            formatted_responses = [
                {
                    "ai": resp.get("platform", "unknown"),
                    "response": resp.get("content", ""),
                    "confidence": resp.get("confidence", 0.9),
                }
                for resp in request.real_responses
            ]

            # 直接提取共识
            consensus = engine._extract_consensus(formatted_responses)
            verified = engine._verify_consensus(consensus)

            return ConsensusResponse(
                topic=request.topic,
                consensus=verified,
                sources=formatted_responses,
                timestamp=datetime.now().isoformat(),
                version="2.0",
                mode="real_chrome",  # 标记为真实Chrome响应
            )

        # 本地模式：使用Mock或本地API调用
        if request.providers:
            for provider_name in request.providers:
                if provider_name in engine.providers:
                    engine.providers[provider_name].enabled = True

        result = await engine.generate_consensus(request.topic)
        return ConsensusResponse(**result)

    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"AI providers unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Consensus generation failed: {str(e)}")


@router.get("/providers", response_model=ProvidersResponse)
async def list_providers():
    """
    列出可用的 AI Provider

    Returns:
        providers: 所有已注册的 provider 名称
        defaults: 默认启用的 provider
    """
    from ai_collab.engines.consensus_engine import ConsensusEngine

    engine = ConsensusEngine()
    return ProvidersResponse(
        providers=list(engine.providers.keys()), defaults=["chatgpt", "claude", "kimi", "qianwen"]
    )
