# NotebookLM 上下文增强模块
# src/ai_collab/context/enhanced.py

"""
NotebookLM 集成模块 - 增强上下文理解

利用 NotebookLM 的知识库增强场景识别和上下文分析
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .schema import Context, FileContext, NotebookLMContext, ScenarioType

logger = logging.getLogger(__name__)


class ContextEnhancer:
    """上下文增强器 - 使用 NotebookLM 增强上下文理解"""

    def __init__(self, notebooklm_integration=None):
        """
        初始化上下文增强器

        Args:
            notebooklm_integration: NotebookLM 集成实例
        """
        self._notebooklm = notebooklm_integration
        self._logger = logging.getLogger(__name__)

    def enrich(
        self,
        base_context: Context,
        query: str,
        max_results: int = 5,
    ) -> Context:
        """
        使用 NotebookLM 丰富上下文内容

        Args:
            base_context: 基础上下文
            query: 查询问题
            max_results: 最多返回的结果数

        Returns:
            增强后的上下文
        """
        if not self._notebooklm:
            self._logger.warning("NotebookLM integration not available, returning base context")
            return base_context

        try:
            # 查询 NotebookLM 知识库
            result = self._notebooklm.query_knowledge(topic=query)

            if "error" in result:
                self._logger.error(f"NotebookLM query failed: {result['error']}")
                return base_context

            # 创建 NotebookLM 上下文
            notebooklm_ctx = NotebookLMContext(
                notebook_id=result.get("notebook_id", "ai-collab-system-docs"),
                notebook_name=result.get("notebook_name", "project-docs"),
                query_results=[{"query": query, "answer": result.get("response", "")}],
                sources=result.get("sources", [])[:max_results],
                last_updated=datetime.now(),
            )

            # 更新基础上下文
            base_context.update_notebooklm(notebooklm_ctx)
            base_context.metadata.touch()

            self._logger.info(f"Context enriched with {len(result.get('sources', []))} sources")
            return base_context

        except Exception as e:
            self._logger.error(f"Failed to enrich context: {e}")
            return base_context

    def auto_upload_documents(
        self,
        file_paths: List[str],
        notebook_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        自动上传文档到 NotebookLM

        Args:
            file_paths: 要上传的文件路径列表
            notebook_id: 目标笔记本 ID (默认使用配置的 ID)

        Returns:
            上传结果字典
        """
        if not self._notebooklm:
            self._logger.warning("NotebookLM integration not available")
            return {"uploaded": 0, "errors": ["NotebookLM not available"]}

        results = {"uploaded": 0, "errors": [], "source_ids": []}
        for file_path in file_paths:
            try:
                if hasattr(self._notebooklm, "add_source"):
                    source_result = self._notebooklm.add_source(
                        notebook_id=notebook_id,
                        file_path=file_path,
                    )
                    results["uploaded"] += 1
                    if isinstance(source_result, dict) and "source_id" in source_result:
                        results["source_ids"].append(source_result["source_id"])
                else:
                    results["errors"].append(f"add_source not supported for {file_path}")
            except Exception as e:
                results["errors"].append(f"{file_path}: {str(e)}")

        self._logger.info(f"Auto-uploaded {results['uploaded']}/{len(file_paths)} documents")
        return results

    def enhanced_query(
        self,
        query: str,
        context: Optional[Context] = None,
        max_results: int = 5,
        include_related: bool = True,
    ) -> Dict[str, Any]:
        """
        增强知识检索 - 基于上下文优化查询

        Args:
            query: 查询问题
            context: 当前上下文 (用于优化查询)
            max_results: 最多返回结果数
            include_related: 是否包含相关主题

        Returns:
            增强检索结果
        """
        if not self._notebooklm:
            return {"results": [], "enhanced_query": query, "error": "NotebookLM not available"}

        # 基于上下文优化查询
        enhanced_query_str = query
        if context:
            scenario_hint = f"在{context.scenario.value}场景中"
            enhanced_query_str = f"{scenario_hint} {query}"

        try:
            result = self._notebooklm.query_knowledge(topic=enhanced_query_str)
            if "error" in result:
                return {"results": [], "enhanced_query": enhanced_query_str, "error": result["error"]}

            sources = result.get("sources", [])[:max_results]
            response = result.get("response", "")

            output = {
                "results": sources,
                "answer": response,
                "enhanced_query": enhanced_query_str,
                "source_count": len(sources),
            }

            # 检索相关主题
            if include_related and sources:
                related_topics = set()
                for source in sources:
                    if isinstance(source, dict) and "title" in source:
                        related_topics.add(source["title"])
                output["related_topics"] = list(related_topics)

            return output

        except Exception as e:
            return {"results": [], "enhanced_query": enhanced_query_str, "error": str(e)}

    def suggest_files(
        self,
        context: Context,
        project_files: List[str],
        top_n: int = 10,
    ) -> List[str]:
        """
        基于当前上下文建议相关文件

        Args:
            context: 当前上下文
            project_files: 项目中的所有文件
            top_n: 返回的文件数量

        Returns:
            建议的文件列表
        """
        if not self._notebooklm or not context.notebooklm_context:
            # 没有 NotebookLM 上下文，使用简单规则
            return self._simple_file_suggestion(context, project_files, top_n)

        try:
            # 使用 NotebookLM 查询相关文档
            query = f"与 {context.scenario.value} 场景相关的文件和文档"
            result = self._notebooklm.query_knowledge(topic=query)

            if "error" in result:
                return self._simple_file_suggestion(context, project_files, top_n)

            # 从 NotebookLM 响应中提取文件路径
            sources = result.get("sources", [])
            # 匹配项目文件
            suggested = []
            for source in sources:
                for file_path in project_files:
                    if source.lower() in file_path.lower() or file_path.lower() in source.lower():
                        suggested.append(file_path)
                        if len(suggested) >= top_n:
                            return suggested

            # 如果不足，补充简单规则的结果
            simple_suggestions = self._simple_file_suggestion(
                context,
                [f for f in project_files if f not in suggested],
                top_n - len(suggested),
            )
            suggested.extend(simple_suggestions)

            return suggested[:top_n]

        except Exception as e:
            self._logger.error(f"Failed to suggest files: {e}")
            return self._simple_file_suggestion(context, project_files, top_n)

    def _simple_file_suggestion(
        self,
        context: Context,
        project_files: List[str],
        top_n: int,
    ) -> List[str]:
        """简单的文件建议规则"""
        scenario = context.scenario

        # 场景特定的文件模式
        scenario_patterns = {
            ScenarioType.CODING: ["src/", "app/", "lib/", "*.py", "*.js", "*.ts"],
            ScenarioType.RESEARCH: ["docs/", "research/", "*.md", "*.pdf"],
            ScenarioType.WRITING: ["content/", "posts/", "articles/", "*.md"],
            ScenarioType.DEBUGGING: ["logs/", "tests/", "*test*.py", "debug/"],
            ScenarioType.DESIGN: ["design/", "assets/", "*.css", "*.scss"],
            ScenarioType.PROJECT_PLANNING: ["plans/", "tasks/", "todo*", "*.md"],
            ScenarioType.DOCUMENTATION: ["doc/", "docs/", "README*", "CHANGELOG*"],
        }

        patterns = scenario_patterns.get(scenario, [])

        suggested = []
        for file_path in project_files:
            # 检查是否匹配模式
            if self._matches_patterns(file_path, patterns):
                suggested.append(file_path)
                if len(suggested) >= top_n:
                    break

        # 如果不足，返回任何文件
        if len(suggested) < top_n:
            remaining = [f for f in project_files if f not in suggested]
            suggested.extend(remaining[: top_n - len(suggested)])

        return suggested[:top_n]

    def _matches_patterns(self, file_path: str, patterns: List[str]) -> bool:
        """检查文件路径是否匹配模式"""
        import fnmatch
        import os

        file_name = os.path.basename(file_path)
        file_name_lower = file_name.lower()
        file_path_lower = file_path.lower()

        for pattern in patterns:
            pattern_lower = pattern.lower()
            if ("*" in pattern) and fnmatch.fnmatch(file_name_lower, pattern_lower):
                return True
            if pattern_lower in file_path_lower:
                return True

        return False

    def extract_context_summary(
        self,
        context: Context,
        max_length: int = 500,
    ) -> Dict[str, Any]:
        """
        提取上下文摘要

        Args:
            context: 上下文对象
            max_length: 摘要最大长度

        Returns:
            摘要字典
        """
        summary = {
            "context_id": context.context_id,
            "scenario": context.scenario.value,
            "name": context.name,
            "file_count": len(context.file_contexts),
            "session_count": len(context.ai_sessions),
            "has_notebooklm": context.notebooklm_context is not None,
        }

        # NotebookLM 关键点
        if context.notebooklm_context:
            summary["notebooklm_sources"] = context.notebooklm_context.sources[:3]
            if context.notebooklm_context.query_results:
                answer = context.notebooklm_context.query_results[0].get("answer", "")
                summary["knowledge_summary"] = answer[:max_length] if answer else ""

        # 文件列表
        summary["recent_files"] = [f.path for f in context.file_contexts[:5]]

        # 标签
        if context.metadata.tags:
            summary["tags"] = context.metadata.tags[:5]

        # 时间信息
        summary["last_updated"] = context.metadata.updated_at.isoformat()

        return summary

    def merge_contexts(
        self,
        contexts: List[Context],
        scenario: ScenarioType,
        name: str,
    ) -> Context:
        """
        合并多个上下文

        Args:
            contexts: 上下文列表
            scenario: 新场景类型
            name: 新上下文名称

        Returns:
            合并后的上下文
        """
        import uuid

        merged = Context(
            context_id=str(uuid.uuid4()),
            scenario=scenario,
            name=name,
        )

        # 合并文件上下文（去重）
        seen_files = set()
        for ctx in contexts:
            for file_ctx in ctx.file_contexts:
                if file_ctx.path not in seen_files:
                    merged.add_file(file_ctx)
                    seen_files.add(file_ctx.path)

        # 合并 AI 会话
        for ctx in contexts:
            for session in ctx.ai_sessions:
                merged.add_ai_session(session)

        # 合并 NotebookLM 上下文
        notebooklm_contexts = [ctx.notebooklm_context for ctx in contexts if ctx.notebooklm_context]
        if notebooklm_contexts:
            # 选择信息量最大的
            richest = max(
                notebooklm_contexts,
                key=lambda nb: sum(len(q.get("answer", "")) for q in nb.query_results),
            )
            merged.update_notebooklm(richest)

        # 合并标签
        all_tags = set()
        for ctx in contexts:
            all_tags.update(ctx.metadata.tags)
        merged.metadata.tags = list(all_tags)

        return merged


class ScenarioContextBuilder:
    """场景上下文构建器"""

    def __init__(self, enhancer: Optional[ContextEnhancer] = None):
        """
        初始化构建器

        Args:
            enhancer: 上下文增强器
        """
        self._enhancer = enhancer

    def build_for_coding(
        self,
        base_files: List[str],
        notebooklm_query: str = "代码架构和模块关系",
    ) -> Context:
        """构建编码场景上下文"""
        context = Context(
            context_id=None,
            scenario=ScenarioType.CODING,
            name="Coding Context",
        )

        # 添加文件
        from .schema import FileContext

        for file_path in base_files:
            context.add_file(
                FileContext(
                    path=file_path,
                    language=self._detect_language(file_path),
                    size=0,
                )
            )

        # 使用增强器
        if self._enhancer:
            context = self._enhancer.enrich(context, notebooklm_query)

        return context

    def build_for_research(
        self,
        base_files: List[str],
        notebooklm_query: str = "研究背景和相关文献",
    ) -> Context:
        """构建研究场景上下文"""
        context = Context(
            context_id=None,
            scenario=ScenarioType.RESEARCH,
            name="Research Context",
        )

        # 添加文件
        from .schema import FileContext

        for file_path in base_files:
            context.add_file(
                FileContext(
                    path=file_path,
                    language=self._detect_language(file_path),
                    size=0,
                )
            )

        # 使用增强器
        if self._enhancer:
            context = self._enhancer.enrich(context, notebooklm_query)

        return context

    def build_for_writing(
        self,
        base_files: List[str],
        notebooklm_query: str = "写作风格和内容要求",
    ) -> Context:
        """构建写作场景上下文"""
        context = Context(
            context_id=None,
            scenario=ScenarioType.WRITING,
            name="Writing Context",
        )

        # 添加文件
        from .schema import FileContext

        for file_path in base_files:
            context.add_file(
                FileContext(
                    path=file_path,
                    language=self._detect_language(file_path),
                    size=0,
                )
            )

        # 使用增强器
        if self._enhancer:
            context = self._enhancer.enrich(context, notebooklm_query)

        return context

    def _detect_language(self, path: str) -> str:
        """检测文件语言"""
        from .schema import _detect_language as detect_lang

        return detect_lang(path)


# ==================== 示例 ====================

if __name__ == "__main__":
    print("=== NotebookLM 上下文增强示例 ===\n")

    # 创建增强器（不使用实际 NotebookLM）
    enhancer = ContextEnhancer(notebooklm_integration=None)

    # 创建基础上下文
    context = Context(
        context_id="test-ctx",
        scenario=ScenarioType.CODING,
        name="Test Context",
    )

    # 添加文件
    from .schema import FileContext

    context.add_file(FileContext(path="src/main.py", language="python", size=100))
    context.add_file(FileContext(path="README.md", language="markdown", size=50))

    # 提取摘要
    summary = enhancer.extract_context_summary(context)
    print("摘要:", summary)

    # 文件建议
    project_files = [
        "src/main.py",
        "src/utils.py",
        "app.js",
        "docs/api.md",
        "README.md",
        "CHANGELOG.md",
        "test_main.py",
    ]

    suggested = enhancer.suggest_files(context, project_files, top_n=5)
    print(f"\n建议文件: {suggested}")

    print("\n=== 完成 ===")
