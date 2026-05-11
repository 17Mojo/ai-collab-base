"""
NotebookLM API Router
NotebookLM 知识查询集成
"""

import asyncio
import os
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# NotebookLM 配置
NOTEBOOK_ID = os.getenv("NOTEBOOKLM_NOTEBOOK_ID", "d2b04caa-257a-4aad-82b0-f58c28e0dad5")

# NotebookLM Skill 路径
SKILL_DIR = Path.home() / ".claude" / "skills" / "notebooklm"
SCRIPTS_DIR = SKILL_DIR / "scripts"
RUN_WRAPPER = SCRIPTS_DIR / "run.py"
ASK_QUESTION_SCRIPT = SCRIPTS_DIR / "ask_question.py"

# 默认 Notebook URL
DEFAULT_NOTEBOOK_URL = f"https://notebooklm.google.com/notebook/{NOTEBOOK_ID}"


class QueryRequest(BaseModel):
    """知识查询请求"""

    notebook_id: str = NOTEBOOK_ID
    query: str
    context: str = "创作原则"


class QueryResponse(BaseModel):
    """知识查询响应"""

    response: str
    sources: list[str] = []
    mode: str = "real"
    notebook_id: str
    query: str


class GenerateArtifactRequest(BaseModel):
    """产物生成请求"""

    notebook_id: str = NOTEBOOK_ID
    content_type: str  # audio, video, slides, infographic, mindmap, flashcards, briefing
    style: str = "default"
    orientation: str = "vertical"


class GenerateArtifactResponse(BaseModel):
    """产物生成响应"""

    success: bool
    artifact_id: str = ""
    content_type: str
    mode: str = "real"
    message: str = ""


async def query_notebooklm(notebook_id: str, query: str) -> dict:
    """
    通过 NotebookLM Skill 查询 NotebookLM

    Args:
        notebook_id: Notebook ID
        query: 查询问题

    Returns:
        dict: 查询结果
    """
    try:
        # 构建 Notebook URL
        notebook_url = f"https://notebooklm.google.com/notebook/{notebook_id}"

        # 使用 NotebookLM Skill 的 run.py wrapper
        if RUN_WRAPPER.exists() and ASK_QUESTION_SCRIPT.exists():
            # 构建命令
            cmd = [
                "python",
                str(RUN_WRAPPER),
                str(ASK_QUESTION_SCRIPT.name),
                "--question",
                query,
                "--notebook-url",
                notebook_url,
            ]

            # 执行命令（使用 asyncio）
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(SCRIPTS_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                # 如果认证失败，返回 Mock 数据
                if "Not authenticated" in error_msg or "authentication" in error_msg.lower():
                    return {
                        "response": "",
                        "sources": [],
                        "mode": "auth_required",
                        "error": "NotebookLM authentication required",
                    }
                # 网络错误，返回 Mock fallback
                if "ERR_CONNECTION" in error_msg or "network" in error_msg.lower():
                    return get_mock_knowledge(query)

            # 解析输出
            output = stdout.decode()

            # 移除 Follow-up reminder
            if "EXTREMELY IMPORTANT: Is that ALL" in output:
                output = output.split("EXTREMELY IMPORTANT: Is that ALL")[0].strip()

            # 提取回答和来源
            response_text = output
            sources = []

            # 尝试解析来源（如果输出包含来源信息）
            if "Sources:" in output or "来源:" in output:
                parts = output.split("Sources:") if "Sources:" in output else output.split("来源:")
                response_text = parts[0].strip()
                if len(parts) > 1:
                    sources_text = parts[1].strip()
                    sources = [
                        s.strip()
                        for s in sources_text.split("\n")
                        if s.strip() and s.strip() != "None"
                    ]

            return {"response": response_text, "sources": sources, "mode": "real"}

        else:
            # Skill scripts not found, return mock
            return get_mock_knowledge(query)

    except FileNotFoundError:
        # Return mock data fallback
        return get_mock_knowledge(query)
    except Exception:
        # Network or other errors, return mock fallback
        return get_mock_knowledge(query)


def get_mock_knowledge(query: str) -> dict:
    """
    获取 Mock 知识数据（用于 fallback）

    Args:
        query: 查询问题

    Returns:
        dict: Mock 知识结果
    """
    # 小红书创作规范 Mock 数据
    mock_knowledge = {
        "创作原则": {
            "response": """
## 小红书知识型内容创作原则

1. **先给结论，再解释原因**
   - 开头必须是明确观点或反常识判断
   - 避免铺垫、背景介绍、学术定义

2. **讲人话，不讲术语**
   - 能不用专业名词就不用，必须用时一句话翻译
   - 多用生活类比、工作场景、真实体验

3. **场景化表达**
   - 每条内容包含至少1个具体场景
   - 明确：谁 + 在做什么 + 为什么用到它

4. **小红书友好结构**
   - 一句话结论 / 反直觉观点
   - 2-4个短段落解释（每段只讲1点）
   - 一个真实例子或对比
   - 一个避坑点 / 行内经验

5. **主动标注边界**
   - 允许说"目前还不成熟"
   - 明确什么人适合、什么人不适合
   - 不做"万能工具"叙事

6. **结尾给可带走的东西**
   - 一个判断标准
   - 一个简单框架
   - 一个可立即尝试的小动作
""",
            "sources": ["小红书知识型博主创作指南.md", "小红书内容规范.md"],
        },
        "图片格式": {
            "response": """
## 小红书图片格式规范

1. **基础参数**
   - 比例：3:4 竖版（最佳）
   - 分辨率：1080×1440px
   - 数量：3-6张
   - 格式：PNG/JPG，单张 ≤ 20MB

2. **封面图要求**
   - 超大标题（占画面1/3以上）
   - 字号：80-120px
   - 高对比度（黑底白字/黄底黑字）
   - 一句话核心观点

3. **内容图要求**
   - 每张图只讲1个点
   - 文字占比 ≤ 40%
   - 字号：标题60-80px，正文40-50px
   - 序号提示（如2/5）

4. **配色规范**
   - 主色调：黑白灰 + 1个高亮色
   - 禁止超过4种颜色
   - 禁止低对比度
""",
            "sources": ["小红书图片格式规范.md", "小红书视觉指南.md"],
        },
        "避坑指南": {
            "response": """
## 小红书创作避坑指南

❌ **禁止事项**:
- 标题党但内容空
- 过度乐观或恐吓式表达
- 把复杂问题一句话"神化解决"
- 明显的割韭菜话术
- 虚假宣传或夸大功效

⚠️ **常见错误**:
- 开头铺垫太多，读者3秒内不知道值不值得看
- 使用太多专业术语，普通人看不懂
- 没有具体场景，泛泛而谈
- 没有标注边界，读者不知道适不适合自己
- 结尾没有可带走的东西，看完就忘

✅ **正确做法**:
- 3秒内让读者知道核心观点
- 用生活类比解释复杂概念
- 至少1个具体使用场景
- 明确适用人群和不适用人群
- 结尾给判断标准或小动作
""",
            "sources": ["小红书避坑指南.md", "内容合规规范.md"],
        },
        "旅游攻略": {
            "response": """
## 旅游攻略创作原则

1. **实用优先**
   - 提供具体地址、交通路线、价格信息
   - 标注开放时间、预约方式
   - 给出真实体验评价

2. **场景化推荐**
   - 适合什么人群（亲子/情侣/独行）
   - 最佳游玩时间
   - 天气影响因素

3. **安全提示**
   - 天气注意事项
   - 紧急联系方式
   - 当地风俗禁忌

4. **预算参考**
   - 交通费用明细
   - 住宿推荐档次
   - 餐饮预算范围
""",
            "sources": ["旅游攻略创作指南.md", "北方旅游注意事项.md"],
        },
    }

    # 查找匹配的知识
    for key, knowledge in mock_knowledge.items():
        if key in query or query in key:
            return {
                "response": knowledge["response"],
                "sources": knowledge["sources"],
                "mode": "mock",
            }

    # 默认返回创作原则
    return {
        "response": mock_knowledge["创作原则"]["response"],
        "sources": mock_knowledge["创作原则"]["sources"],
        "mode": "mock",
    }


@router.post("/query", response_model=QueryResponse)
async def query_knowledge(request: QueryRequest):
    """
    查询 NotebookLM 知识

    Args:
        request: 查询请求

    Returns:
        QueryResponse: 查询结果
    """
    result = await query_notebooklm(request.notebook_id, request.query)

    return QueryResponse(
        response=result["response"],
        sources=result["sources"],
        mode=result["mode"],
        notebook_id=request.notebook_id,
        query=request.query,
    )


@router.post("/generate", response_model=GenerateArtifactResponse)
async def generate_artifact(request: GenerateArtifactRequest):
    """
    生成 NotebookLM Studio 产物

    Args:
        request: 生成请求

    Returns:
        GenerateArtifactResponse: 生成结果
    """
    # 验证 content_type
    valid_types = ["audio", "video", "slides", "infographic", "mindmap", "flashcards", "briefing"]
    if request.content_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content_type: {request.content_type}. Valid types: {valid_types}",
        )

    # Mock 模式 - 真实 Studio 生成需要 NotebookLM 浏览器自动化
    artifact_id = f"mock-{request.content_type}-{int(time.time())}"

    return GenerateArtifactResponse(
        success=True,
        artifact_id=artifact_id,
        content_type=request.content_type,
        mode="mock",
        message="Studio artifact generated in mock mode. Real generation requires NotebookLM browser automation.",
    )


@router.get("/notebook/{notebook_id}/status")
async def get_notebook_status(notebook_id: str):
    """
    获取 Notebook 状态

    Args:
        notebook_id: Notebook ID

    Returns:
        dict: Notebook 状态
    """
    # Mock 模式 - 返回预设状态
    return {"notebook_id": notebook_id, "source_count": 17, "status": "ready"}


@router.get("/download/{artifact_id}")
async def download_artifact(artifact_id: str):
    """
    下载 NotebookLM Studio 产物

    Args:
        artifact_id: 产物 ID

    Returns:
        FileResponse: 产物文件
    """
    # Mock 模式：返回模拟文件信息
    # 真实实现需要调用 nlm CLI download 命令

    content_type_map = {
        "audio": {"mime": "audio/mpeg", "ext": ".mp3"},
        "video": {"mime": "video/mp4", "ext": ".mp4"},
        "slides": {"mime": "application/pdf", "ext": ".pdf"},
        "infographic": {"mime": "image/png", "ext": ".png"},
        "mindmap": {"mime": "image/png", "ext": ".png"},
        "flashcards": {"mime": "application/json", "ext": ".json"},
        "briefing": {"mime": "text/plain", "ext": ".txt"},
    }

    # 从 artifact_id 提取类型
    for content_type, info in content_type_map.items():
        if content_type in artifact_id:
            return {
                "success": True,
                "artifact_id": artifact_id,
                "content_type": content_type,
                "mime_type": info["mime"],
                "extension": info["ext"],
                "mode": "mock",
                "message": "Mock download - real download requires nlm CLI integration",
            }

    return {"success": True, "artifact_id": artifact_id, "mode": "mock", "message": "Mock download"}


@router.post("/batch-query")
async def batch_query_knowledge(requests: list[QueryRequest]):
    """
    批量查询 NotebookLM 知识

    Args:
        requests: 查询请求列表

    Returns:
        list: 查询结果列表
    """
    results = []
    for req in requests:
        result = await query_notebooklm(req.notebook_id, req.query)
        results.append(
            QueryResponse(
                response=result["response"],
                sources=result["sources"],
                mode=result["mode"],
                notebook_id=req.notebook_id,
                query=req.query,
            )
        )
    return results
