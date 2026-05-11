"""
灵魂注入 API 路由
支持预设风格 + 自定义风格 CRUD
"""

import sys
from pathlib import Path

# Add parent directory to sys.path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/soul", tags=["soul"])


# ========== Request/Response Models ==========


class SoulInjectRequest(BaseModel):
    """灵魂注入请求"""

    consensus: str
    profile_name: str = "luoyonghao"
    timeout: Optional[float] = 30.0


class StylePromptRequest(BaseModel):
    """风格化提示词请求"""

    original_prompt: str
    profile_name: str = "luoyonghao"


class StylePromptResponse(BaseModel):
    """风格化提示词响应"""

    success: bool
    original_prompt: str
    styled_prompt: str
    profile_name: str
    style_characteristics: Dict[str, Any]


class SoulInjectResponse(BaseModel):
    """灵魂注入响应"""

    success: bool
    original_consensus: str
    personalized_content: str
    soul_profile: Dict[str, Any]
    timestamp: str
    mode: str
    strategies_applied: Optional[int] = None


class ProfilesResponse(BaseModel):
    """灵魂画像列表响应"""

    profiles: List[str]
    defaults: Dict[str, str]


class StyleCreateRequest(BaseModel):
    """创建自定义风格请求"""

    name: str
    display_name: Optional[str] = None
    prefix: Optional[str] = ""
    suffix: Optional[str] = ""
    tone: Optional[str] = ""
    keywords: Optional[List[str]] = []


class StyleUpdateRequest(BaseModel):
    """更新自定义风格请求"""

    display_name: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    tone: Optional[str] = None
    keywords: Optional[List[str]] = None


class StyleResponse(BaseModel):
    """风格响应"""

    name: str
    display_name: str
    prefix: str
    suffix: str
    tone: str
    keywords: List[str]
    is_preset: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class StylesListResponse(BaseModel):
    """风格列表响应"""

    styles: List[StyleResponse]
    total: int


# ========== Helper Functions ==========


def get_style_db():
    """获取风格数据库实例"""
    from app.db.style_db import style_db

    return style_db


# ========== Style CRUD API ==========


@router.get("/styles", response_model=StylesListResponse)
async def list_all_styles():
    """
    列出所有风格（预设 + 自定义）
    """
    db = get_style_db()
    styles = db.get_all_styles()

    return StylesListResponse(styles=[StyleResponse(**s) for s in styles], total=len(styles))


@router.get("/styles/{name}", response_model=StyleResponse)
async def get_style_detail(name: str):
    """
    获取单个风格详情
    """
    db = get_style_db()
    style = db.get_style(name)

    if not style:
        raise HTTPException(status_code=404, detail=f"Style not found: {name}")

    return StyleResponse(**style)


@router.post("/styles", response_model=StyleResponse)
async def create_custom_style(request: StyleCreateRequest):
    """
    创建自定义风格
    """
    db = get_style_db()

    try:
        style = db.create_style(
            {
                "name": request.name,
                "display_name": request.display_name or request.name,
                "prefix": request.prefix or "",
                "suffix": request.suffix or "",
                "tone": request.tone or "",
                "keywords": request.keywords or [],
            }
        )
        return StyleResponse(**style)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/styles/{name}", response_model=StyleResponse)
async def update_custom_style(name: str, request: StyleUpdateRequest):
    """
    更新自定义风格
    """
    db = get_style_db()

    try:
        style = db.update_style(
            name,
            {
                "display_name": request.display_name,
                "prefix": request.prefix,
                "suffix": request.suffix,
                "tone": request.tone,
                "keywords": request.keywords,
            },
        )

        if not style:
            raise HTTPException(status_code=404, detail=f"Style not found: {name}")

        return StyleResponse(**style)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/styles/{name}")
async def delete_custom_style(name: str):
    """
    删除自定义风格（不能删除预设）
    """
    db = get_style_db()

    deleted = db.delete_style(name)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Style not found or is preset: {name}")

    return {"success": True, "message": f"Style {name} deleted"}


# ========== Legacy API (保持兼容) ==========


@router.post("/inject", response_model=SoulInjectResponse)
async def inject_soul(request: SoulInjectRequest):
    """
    注入灵魂/个性化风格

    将共识内容注入指定的灵魂画像风格

    Args:
        request: 包含 consensus、profile_name、timeout

    Returns:
        包含 personalized_content、soul_profile、mode 等信息
    """
    from ai_collab.engines.soul_injection_engine import SoulInjectionEngine

    try:
        engine = SoulInjectionEngine()
        result = await engine.inject_soul(
            consensus=request.consensus, profile_name=request.profile_name, timeout=request.timeout
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500, detail=result.get("error", "Soul injection failed")
            )

        return SoulInjectResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"Soul engine unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Soul injection failed: {str(e)}")


@router.post("/style_prompt", response_model=StylePromptResponse)
async def style_prompt(request: StylePromptRequest):
    """
    生成风格化提问提示词

    将用户原始提问转换为特定风格的提问方式

    Args:
        request: 包含 original_prompt、profile_name

    Returns:
        包含 styled_prompt（风格化后的提问）
    """
    db = get_style_db()

    # 从数据库获取风格
    style = db.get_style(request.profile_name)

    # 如果找不到，使用默认罗永浩风格
    if not style:
        style = db.get_style("luoyonghao")

    # 生成风格化提问
    styled_prompt = f"{style['prefix']}{request.original_prompt}{style['suffix']}"

    return StylePromptResponse(
        success=True,
        original_prompt=request.original_prompt,
        styled_prompt=styled_prompt,
        profile_name=request.profile_name,
        style_characteristics={
            "name": style["name"],
            "display_name": style["display_name"],
            "prefix": style["prefix"],
            "suffix": style["suffix"],
            "tone": style["tone"],
            "keywords": style["keywords"],
            "is_preset": style["is_preset"],
        },
    )


@router.get("/profiles", response_model=ProfilesResponse)
async def list_profiles():
    """
    列出可用的灵魂画像

    Returns:
        profiles: 所有已注册的灵魂画像名称
        defaults: 默认画像及其描述
    """
    db = get_style_db()
    styles = db.get_all_styles()

    profiles = [s["name"] for s in styles]
    defaults = {s["name"]: f"{s['display_name']} - {s['tone']}" for s in styles if s["is_preset"]}

    return ProfilesResponse(profiles=profiles, defaults=defaults)


@router.get("/profiles/{profile_name}")
async def get_profile(profile_name: str):
    """
    获取指定灵魂画像详情

    Args:
        profile_name: 灵魂画像名称

    Returns:
        灵魂画像详情
    """
    db = get_style_db()
    style = db.get_style(profile_name)

    if not style:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_name}")

    return style
