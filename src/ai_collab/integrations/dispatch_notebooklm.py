"""
NotebookLM 与派单流程集成模块

提供:
- 派单前知识注入 (enrich_task_with_notebooklm)
- 批量派单上下文增强 (enrich_dispatch_payload)
- 任务结果知识归档 (archive_result_to_notebooklm)

支持两种模式:
- MCP 模式: 通过 Claude Code/CodeArts 会话中的 MCP 工具调用
- CLI 模式: 直接调用 nlm CLI（用于独立运行或 REAL 模式）
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .notebooklm import NotebookLMIntegration

# 配置日志
logger = logging.getLogger(__name__)

# nlm CLI 路径（可通过环境变量覆盖）
NLM_CLI_PATH = os.environ.get("NLM_CLI_PATH", "/Users/raymondna/.local/bin/nlm")

# 默认代理
DEFAULT_PROXY = os.environ.get("NLM_PROXY", "http://127.0.0.1:7890")

# 默认 Notebook ID
DEFAULT_NOTEBOOK_ID = "d2b04caa-257a-4aad-82b0-f58c28e0dad5"

# 批量查询配置
BATCH_QUERY_INTERVAL = 2.0  # 查询间隔（秒）
MAX_RETRIES = 2  # 最大重试次数
RETRY_DELAY = 1.0  # 重试延迟（秒）


# 任务类型到查询模板的映射
TASK_TYPE_QUERY_TEMPLATES: dict[str, dict[str, str]] = {
    "implementation": {
        "tech": "如何实现 {description}？请提供技术方案、架构设计和关键代码示例。",
        "history": "历史中是否有类似 {task_id} 的实现任务？请提供解决方案和经验教训。",
    },
    "bugfix": {
        "tech": "{description} 的根因分析和修复方案是什么？请提供调试步骤和常见原因。",
        "history": "历史中是否有类似 {task_id} 的 bug 修复？请提供修复方法和回滚策略。",
    },
    "test": {
        "tech": "如何为 {description} 编写测试？请提供测试策略、覆盖范围和边界条件。",
        "history": "历史中是否有类似 {task_id} 的测试任务？请提供测试模式和工具选择。",
    },
    "docs": {
        "tech": "{description} 的文档应包含哪些内容？请提供文档结构和关键章节建议。",
        "history": "历史中是否有类似 {task_id} 的文档任务？请提供文档模板和最佳实践。",
    },
    "refactor": {
        "tech": "如何重构 {description}？请提供重构策略、风险点和兼容性考虑。",
        "history": "历史中是否有类似 {task_id} 的重构任务？请提供重构步骤和验证方法。",
    },
    "research": {
        "tech": "关于 {description} 的技术调研：请提供现状分析、可选方案和对比评估。",
        "history": "历史中是否有类似 {task_id} 的调研任务？请提供调研结论和决策依据。",
    },
    "default": {
        "tech": "如何实现 {description}？",
        "history": "历史任务 {task_id} 的解决方案",
    },
}


def _infer_task_type(task: dict[str, Any]) -> str:
    """从任务字典推断任务类型。

    Args:
        task: 任务字典

    Returns:
        任务类型键 (implementation/bugfix/test/docs/refactor/research/default)
    """
    task_id = str(task.get("task_id", "")).upper()
    description = str(task.get("description", "")).lower()
    tags = task.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]

    # 基于 task_id 前缀/关键词推断
    if any(kw in task_id for kw in ["FIX", "BUG"]):
        return "bugfix"
    if any(kw in task_id for kw in ["TEST", "INTEGRATION", "VERIFY"]):
        return "test"
    if any(kw in task_id for kw in ["DOC", "API"]):
        return "docs"
    if any(kw in task_id for kw in ["REFACTOR", "CLEANUP", "MIGRATE"]):
        return "refactor"
    if any(kw in task_id for kw in ["RESEARCH", "OPT", "ANALYSIS"]):
        return "research"

    # 基于 description 关键词推断
    if any(kw in description for kw in ["修复", "fix", "bug", "错误"]):
        return "bugfix"
    if any(kw in description for kw in ["测试", "test", "验证", "覆盖"]):
        return "test"
    if any(kw in description for kw in ["文档", "doc", "api"]):
        return "docs"
    if any(kw in description for kw in ["重构", "refactor", "迁移"]):
        return "refactor"
    if any(kw in description for kw in ["调研", "研究", "优化", "research", "opt"]):
        return "research"
    if any(kw in description for kw in ["实现", "implement", "开发", "创建"]):
        return "implementation"

    # 基于 tags 推断
    tag_str = " ".join(str(t).lower() for t in tags)
    if "bugfix" in tag_str:
        return "bugfix"
    if "test" in tag_str:
        return "test"
    if "docs" in tag_str:
        return "docs"

    return "default"


def _build_queries_for_task(task: dict[str, Any]) -> tuple[str, str]:
    """根据任务类型构建定制化的查询 prompt。

    Args:
        task: 任务字典

    Returns:
        (技术查询 prompt, 历史查询 prompt)
    """
    task_type = _infer_task_type(task)
    templates = TASK_TYPE_QUERY_TEMPLATES.get(task_type, TASK_TYPE_QUERY_TEMPLATES["default"])

    task_id = task.get("task_id", "")
    description = task.get("description", "")

    tech_query = templates["tech"].format(description=description, task_id=task_id)
    history_query = templates["history"].format(description=description, task_id=task_id)

    return tech_query, history_query


def _query_notebooklm_via_cli(
    query: str,
    notebook_id: str,
    proxy: str = DEFAULT_PROXY,
    timeout: float = 60.0,
    retries: int = MAX_RETRIES,
) -> dict[str, Any]:
    """通过 nlm CLI 直接查询 NotebookLM。

    Args:
        query: 查询问题
        notebook_id: Notebook ID
        proxy: HTTP 代理地址
        timeout: 查询超时时间（秒）
        retries: 最大重试次数

    Returns:
        查询结果字典

    Raises:
        RuntimeError: CLI 调用失败
    """
    env = os.environ.copy()
    env["HTTP_PROXY"] = proxy
    env["HTTPS_PROXY"] = proxy

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                [NLM_CLI_PATH, "notebook", "query", notebook_id, query],
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or f"exit code {result.returncode}"
                raise RuntimeError(f"nlm CLI failed: {error_msg}")

            try:
                parsed = json.loads(result.stdout)
                value = parsed.get("value", parsed)
                return {
                    "answer": value.get("answer", ""),
                    "sources_used": value.get("sources_used", []),
                    "conversation_id": value.get("conversation_id", ""),
                    "mode": "real",
                }
            except json.JSONDecodeError:
                return {
                    "answer": result.stdout,
                    "mode": "real",
                    "parse_error": True,
                }

        except subprocess.TimeoutExpired as e:
            last_error = RuntimeError(f"nlm CLI timeout after {timeout}s: {e}")
            logger.warning(f"Query timeout (attempt {attempt + 1}/{retries + 1}): {query[:50]}...")
        except RuntimeError as e:
            last_error = e
            logger.warning(f"Query failed (attempt {attempt + 1}/{retries + 1}): {e}")
        except Exception as e:
            last_error = RuntimeError(f"Unexpected error: {e}")
            logger.warning(f"Unexpected error (attempt {attempt + 1}/{retries + 1}): {e}")

        # 重试前等待
        if attempt < retries:
            time.sleep(RETRY_DELAY)

    raise last_error or RuntimeError("Unknown error")


def enrich_task_with_notebooklm(
    task: dict[str, Any],
    *,
    notebook_id: str = DEFAULT_NOTEBOOK_ID,
    mode: str = "FALLBACK",
    use_cli: bool = False,
    proxy: str = DEFAULT_PROXY,
) -> dict[str, Any]:
    """使用 NotebookLM 知识库增强任务上下文。

    Args:
        task: 任务字典，必须包含 task_id 和 description
        notebook_id: NotebookLM notebook ID
        mode: NotebookLM 运行模式 (MOCK/FALLBACK/REAL)
        use_cli: 是否使用 CLI 模式（绕过 MCP）
        proxy: HTTP 代理地址（CLI 模式使用）

    Returns:
        增强后的任务字典，包含 notebooklm_context 字段
    """
    task_id = task.get("task_id", "")
    task.get("description", "")

    # 根据任务类型构建定制化查询
    query, history_query = _build_queries_for_task(task)

    # REAL 模式 + CLI 模式：直接调用 nlm CLI
    if mode == "REAL" and use_cli:
        try:
            tech_result = _query_notebooklm_via_cli(query, notebook_id, proxy)
            tech_context = tech_result.get("answer", "")
            tech_sources = tech_result.get("sources_used", [])
        except Exception as e:
            # REAL 模式失败，抛出异常（不允许回退）
            raise RuntimeError(f"NotebookLM REAL 模式查询失败: {e}")

        # 查询历史类似任务
        history_query = f"历史任务 {task_id} 的解决方案"
        try:
            history_result = _query_notebooklm_via_cli(history_query, notebook_id, proxy)
            history_context = history_result.get("answer", "")
        except Exception:
            history_context = ""

        task["notebooklm_context"] = {
            "technical_docs": tech_context,
            "historical_solutions": history_context,
            "queried_at": datetime.now().isoformat(),
            "notebook_id": notebook_id,
            "mode": "real",
            "sources_used": tech_sources,
        }
        return task

    # 其他模式：使用 NotebookLMIntegration（MCP 模式）
    nlm = NotebookLMIntegration(notebook_id=notebook_id)

    # 查询技术文档
    tech_context = nlm.query_knowledge(query)

    # 查询历史类似任务（使用定制化 history_query）
    history_context = nlm.query_knowledge(history_query)

    # 注入上下文
    task["notebooklm_context"] = {
        "technical_docs": tech_context.get("response", ""),
        "historical_solutions": history_context.get("response", ""),
        "queried_at": datetime.now().isoformat(),
        "notebook_id": notebook_id,
        "mode": tech_context.get("mode", "mcp"),
    }

    return task


def enrich_dispatch_payload(
    candidates: list[dict[str, Any]],
    *,
    notebook_id: str = DEFAULT_NOTEBOOK_ID,
    mode: str = "FALLBACK",
    use_cli: bool = False,
    proxy: str = DEFAULT_PROXY,
    query_interval: float = BATCH_QUERY_INTERVAL,
    allow_partial_failure: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """批量增强派单候选任务的上下文。

    Args:
        candidates: 派单候选任务列表
        notebook_id: NotebookLM notebook ID
        mode: NotebookLM 运行模式
        use_cli: 是否使用 CLI 模式（绕过 MCP）
        proxy: HTTP 代理地址（CLI 模式使用）
        query_interval: 查询间隔（秒），避免 API 过载
        allow_partial_failure: 是否允许部分任务增强失败

    Returns:
        (增强后的任务列表, 增强统计信息)
    """
    enriched_tasks: list[dict[str, Any]] = []
    stats = {
        "total": len(candidates),
        "enriched": 0,
        "failed": 0,
        "skipped": 0,
        "errors": [],
    }

    for i, task in enumerate(candidates):
        task_id = task.get("task_id", f"unknown-{i}")

        # 查询间隔（第一个任务不等待）
        if i > 0 and query_interval > 0:
            time.sleep(query_interval)

        try:
            enriched_task = enrich_task_with_notebooklm(
                task,
                notebook_id=notebook_id,
                mode=mode,
                use_cli=use_cli,
                proxy=proxy,
            )
            enriched_tasks.append(enriched_task)
            stats["enriched"] += 1
            logger.debug(f"Enriched task: {task_id}")

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Failed to enrich task {task_id}: {error_msg}")

            if allow_partial_failure:
                # 部分失败模式：记录错误，返回原始任务
                stats["failed"] += 1
                stats["errors"].append({"task_id": task_id, "error": error_msg})
                # 添加错误上下文
                task["notebooklm_context"] = {
                    "error": error_msg,
                    "mode": "error",
                    "queried_at": datetime.now().isoformat(),
                }
                enriched_tasks.append(task)
            else:
                # 严格模式：抛出异常
                raise RuntimeError(f"Failed to enrich task {task_id}: {error_msg}")

    return enriched_tasks, stats


def extract_key_sections(result_content: str) -> str:
    """从结果文件提取关键章节。

    Args:
        result_content: 结果文件内容

    Returns:
        提取的关键内容摘要
    """
    sections = []

    # 提取执行命令章节
    cmd_match = re.search(
        r"## 执行命令\s*\n([\s\S]*?)(?=\n## |$)",
        result_content,
        re.MULTILINE,
    )
    if cmd_match:
        sections.append(f"### 执行命令\n{cmd_match.group(1).strip()}")

    # 提取测试结论章节
    test_match = re.search(
        r"## 测试结论\s*\n([\s\S]*?)(?=\n## |$)",
        result_content,
        re.MULTILINE,
    )
    if test_match:
        sections.append(f"### 测试结论\n{test_match.group(1).strip()}")

    # 提取风险/回滚章节
    risk_match = re.search(
        r"## 风险/回滚\s*\n([\s\S]*?)(?=\n## |$)",
        result_content,
        re.MULTILINE,
    )
    if risk_match:
        sections.append(f"### 风险/回滚\n{risk_match.group(1).strip()}")

    return "\n\n".join(sections) if sections else result_content[:500]


def archive_result_to_notebooklm(
    task_id: str,
    result_file: str,
    *,
    notebook_id: str = "ai-collab-system-docs",
    mode: str = "FALLBACK",
) -> dict[str, Any]:
    """将任务结果归档到 NotebookLM 知识库。

    Args:
        task_id: 任务 ID
        result_file: 结果文件路径
        notebook_id: NotebookLM notebook ID
        mode: NotebookLM 运行模式

    Returns:
        归档结果
    """
    result_path = Path(result_file)
    if not result_path.exists():
        return {"status": "skipped", "reason": "result_file_not_found"}

    result_content = result_path.read_text(encoding="utf-8")
    summary = extract_key_sections(result_content)

    nlm = NotebookLMIntegration(notebook_id=notebook_id)

    # 添加为知识源
    add_result = nlm.add_source(
        notebook_id=notebook_id,
        source_type="text",
        content=f"## {task_id} 解决方案\n\n{summary}",
    )

    return {
        "status": "archived",
        "task_id": task_id,
        "notebook_id": notebook_id,
        "source_id": add_result.get("source_id"),
        "archived_at": datetime.now().isoformat(),
    }
