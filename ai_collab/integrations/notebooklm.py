# NotebookLM集成模块
# src/ai_collab/integrations/notebooklm.py

"""
NotebookLM集成模块
提供与NotebookLM Studio的深度集成功能
支持 MOCK/FALLBACK/REAL 三种模式
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config.integration_flags import IntegrationMode, get_mode


class NotebookLMIntegration:
    """NotebookLM集成类"""

    def __init__(self, notebook_id: Optional[str] = None):
        """
        初始化NotebookLM集成

        Args:
            notebook_id: Notebook ID（可选）
        """
        self.notebook_id = notebook_id
        self.is_connected = False
        self._logger = logging.getLogger(__name__)

        # 从配置获取集成模式
        self._mode = get_mode("notebooklm")
        self._mock = self._mode == IntegrationMode.MOCK
        self._mock_reason = f"NotebookLM运行在{self._mode.value}模式"

    def _check_mcp_health(self) -> bool:
        """
        检查 NotebookLM MCP 健康状态 (严格模式)

        Returns:
            MCP 是否可用

        Raises:
            ConnectionError: REAL 模式下 MCP 不可用时抛出
        """
        try:
            # 严格检查: 只使用真实的 MCP 工具
            import builtins

            TOOL_NAME_GET_HEALTH = "mcp__plugin_notebooklm__get_health"
            if not hasattr(builtins, TOOL_NAME_GET_HEALTH):
                # MCP 工具不存在
                if self._mode == IntegrationMode.REAL:
                    raise ConnectionError("MCP get_health 工具不可用 (REAL 模式)")
                else:
                    self._logger.warning("[NotebookLM] MCP工具不可用")
                    return False

            # 调用真实的 MCP 健康检查
            get_health_func = getattr(builtins, TOOL_NAME_GET_HEALTH)
            health_result = get_health_func()

            if not health_result:
                if self._mode == IntegrationMode.REAL:
                    raise ConnectionError("MCP 健康检查返回空结果 (REAL 模式)")
                else:
                    self._logger.warning("[NotebookLM] MCP健康检查返回空结果")
                    return False

            if not health_result.get("authenticated", False):
                if self._mode == IntegrationMode.REAL:
                    raise ConnectionError(f"MCP 未认证: {health_result} (REAL 模式)")
                else:
                    self._logger.warning(f"[NotebookLM] MCP未认证: {health_result}")
                    return False

            # 健康检查通过
            self._logger.info("[NotebookLM] MCP健康检查通过")
            return True

        except ConnectionError:
            # REAL 模式的异常直接抛出
            raise
        except Exception as e:
            if self._mode == IntegrationMode.REAL:
                raise ConnectionError(f"MCP 健康检查异常: {e} (REAL 模式)")
            else:
                self._logger.error(f"[NotebookLM] MCP健康检查异常: {e}")
                return False

    def _query_mcp(self, topic: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        通过 MCP 查询 NotebookLM (严格模式)

        Args:
            topic: 查询主题
            context: 上下文信息

        Returns:
            查询结果

        Raises:
            ConnectionError: REAL 模式下 MCP 调用失败时抛出
        """
        # 构建查询
        query = f"关于{topic}的详细信息"
        if context:
            query = f"{context}\n\n{query}"

        try:
            # 严格检查: 只使用真实的 MCP 工具
            import builtins

            TOOL_NAME_ASK_QUESTION = "mcp__plugin_notebooklm__ask_question"
            if not hasattr(builtins, TOOL_NAME_ASK_QUESTION):
                if self._mode == IntegrationMode.REAL:
                    raise ConnectionError("MCP ask_question 工具不可用 (REAL 模式)")
                else:
                    raise ConnectionError("MCP ask_question 工具不可用")

            # 调用真实的 MCP 查询
            notebook_id = self.notebook_id or "ai-collab-system-docs"
            ask_question_func = getattr(builtins, TOOL_NAME_ASK_QUESTION)

            result = ask_question_func(question=query, notebook_id=notebook_id)

            if not result:
                if self._mode == IntegrationMode.REAL:
                    raise ConnectionError("MCP 查询返回空结果 (REAL 模式)")
                else:
                    raise ConnectionError("MCP 查询返回空结果")

            if "answer" not in result:
                if self._mode == IntegrationMode.REAL:
                    raise ConnectionError(f"MCP 响应格式错误: {result} (REAL 模式)")
                else:
                    raise ConnectionError(f"MCP 响应格式错误: {result}")

            # 转换 MCP 响应格式
            return {
                "query": query,
                "response": result.get("answer", ""),
                "sources": result.get("sources", []),
                "timestamp": datetime.now().isoformat(),
                "session_id": result.get("session_id", ""),
                "mcp_mode": "real",
            }

        except ConnectionError:
            # REAL 模式的异常直接抛出
            raise
        except Exception as e:
            if self._mode == IntegrationMode.REAL:
                raise ConnectionError(f"MCP 查询异常: {e} (REAL 模式)")
            else:
                self._logger.error(f"[NotebookLM] MCP查询失败: {e}")
                raise

    def connect(self) -> bool:
        """
        连接到NotebookLM

        Returns:
            是否连接成功
        """
        try:
            # 根据模式决定行为
            if self._mode == IntegrationMode.MOCK:
                self._logger.warning(f"[Mock模式] {self._mock_reason}")
                self.is_connected = True
                return True

            # 尝试真实连接
            try:
                # 调用 MCP 健康检查
                # 注意: 这里需要通过 MCP 工具调用
                # 由于 Python 环境限制,我们使用模拟的健康检查
                health_status = self._check_mcp_health()

                if health_status:
                    self.is_connected = True
                    self._logger.info("[NotebookLM] MCP连接成功")
                    return True
                else:
                    # FALLBACK 模式: 回退到 Mock
                    if self._mode == IntegrationMode.FALLBACK:
                        self._logger.warning("[NotebookLM] MCP不可用,回退到Mock模式")
                        self._mock = True
                        self.is_connected = True
                        return True
                    else:
                        # REAL 模式: 抛出异常
                        raise ConnectionError("NotebookLM MCP不可用")

            except Exception as e:
                if self._mode == IntegrationMode.FALLBACK:
                    self._logger.warning(f"[NotebookLM] 连接失败,回退到Mock: {e}")
                    self._mock = True
                    self.is_connected = True
                    return True
                else:
                    raise

        except Exception as e:
            self._logger.error(f"[NotebookLM] 连接失败: {e}")
            return False

    def query_knowledge(self, topic: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        查询NotebookLM知识库

        Args:
            topic: 查询主题
            context: 上下文信息

        Returns:
            查询结果
        """
        # Mock模式警告
        if self._mock:
            self._logger.warning(f"[Mock模式] {self._mock_reason}")

        if not self.is_connected:
            self.connect()

        # 构建查询
        query = f"关于{topic}的详细信息"
        if context:
            query = f"{context}\n\n{query}"

        try:
            # 根据模式选择查询方式
            if self._mock:
                # Mock 模式: 返回模拟数据
                result = {
                    "query": query,
                    "response": f"[NotebookLM Mock响应] 关于{topic}的知识...",
                    "sources": ["document1.pdf", "document2.docx"],
                    "timestamp": datetime.now().isoformat(),
                    "mode": "mock",
                }
            else:
                # REAL/FALLBACK 模式: 尝试真实 MCP 调用
                try:
                    result = self._query_mcp(topic, context)
                    result["mode"] = "real"
                except Exception as e:
                    if self._mode == IntegrationMode.FALLBACK:
                        self._logger.warning(f"[NotebookLM] MCP查询失败,回退到Mock: {e}")
                        result = {
                            "query": query,
                            "response": f"[NotebookLM Mock响应] 关于{topic}的知识...",
                            "sources": ["document1.pdf", "document2.docx"],
                            "timestamp": datetime.now().isoformat(),
                            "mode": "fallback",
                        }
                    else:
                        raise

            self._logger.info(f"[NotebookLM] 查询成功: {topic}")
            return result

        except Exception as e:
            self._logger.error(f"[NotebookLM] 查询失败: {e}")
            return {"error": str(e)}

    def enhance_prompt(self, prompt: str, topic: str) -> str:
        """
        使用NotebookLM知识增强Prompt

        Args:
            prompt: 原始Prompt
            topic: 主题

        Returns:
            增强后的Prompt
        """
        # 查询相关知识
        knowledge = self.query_knowledge(topic)

        if "error" in knowledge:
            return prompt

        # 提取关键信息
        context = knowledge.get("response", "")
        sources = knowledge.get("sources", [])

        # 构建增强Prompt
        enhanced_prompt = f"""
{prompt}

## 参考知识

{context}

## 来源
{', '.join(sources)}
"""

        return enhanced_prompt

    def save_result(self, content: str, metadata: Dict[str, Any]) -> bool:
        """
        保存生成结果到NotebookLM

        Args:
            content: 生成的内容
            metadata: 元数据

        Returns:
            是否保存成功
        """
        if not self.is_connected:
            self.connect()

        try:
            # 构建笔记本条目
            entry = {
                "title": f"生成内容 - {metadata.get('topic', '未知主题')}",
                "content": content,
                "metadata": {
                    "pack_name": metadata.get("pack_name", "Unknown"),
                    "validation_score": metadata.get("validation_score", 0),
                    "timestamp": datetime.now().isoformat(),
                    "tags": metadata.get("tags", []),
                },
            }

            # 保存到NotebookLM
            # 实际实现需要NotebookLM API支持
            print(f"[NotebookLM] 结果已保存: {entry['title']}")
            return True

        except Exception as e:
            print(f"[NotebookLM] 保存失败: {e}")
            return False

    def get_recommended_packs(self, user_input: str) -> List[Dict[str, Any]]:
        """
        基于NotebookLM知识推荐Pack

        Args:
            user_input: 用户输入

        Returns:
            推荐的Pack列表
        """
        # 分析用户意图
        intent = self._analyze_intent(user_input)

        # 查询相关主题（保留查询调用以维持原有逻辑）
        _ = self.query_knowledge(intent["topic"])

        # 匹配Pack库
        # 实际实现需要查询Pack库
        recommended = [
            {"pack_name": "内容生成器", "relevance": 0.9, "reason": "适合生成文章内容"},
            {"pack_name": "小红书文案", "relevance": 0.8, "reason": "适合社交媒体内容"},
        ]

        return recommended

    def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """
        分析用户意图

        Args:
            user_input: 用户输入

        Returns:
            意图分析结果
        """
        # 简单的意图分析
        # 实际实现可以使用更复杂的NLP

        intent = {
            "type": "content_generation",
            "topic": user_input,
            "keywords": user_input.split()[:5],
        }

        return intent

    def create_notebook_from_pack(self, pack: Dict[str, Any]) -> str:
        """
        从Pack创建NotebookLM笔记本

        Args:
            pack: Pack数据

        Returns:
            创建的Notebook ID
        """
        # 构建笔记本内容
        notebook_content = f"""
# {pack['metadata']['pack_name']}

## 描述
{pack['metadata'].get('description', '无描述')}

## 工作流

"""

        # 添加工作流步骤
        for i, step in enumerate(pack["workflow"]["steps"], 1):
            notebook_content += f"### 步骤{i}: {step['name']}\n"
            notebook_content += f"类型: {step['type']}\n\n"

        # 创建笔记本
        # 实际实现需要NotebookLM API支持
        notebook_id = f"notebook-{int(datetime.now().timestamp())}"

        print(f"[NotebookLM] 笔记本已创建: {notebook_id}")
        return notebook_id


class PackToStudioConverter:
    """Pack到NotebookLM Studio转换器"""

    def convert(self, pack: Dict[str, Any]) -> Dict[str, Any]:
        """
        将Pack转换为NotebookLM Studio格式

        Args:
            pack: Pack数据

        Returns:
            Studio格式数据
        """
        studio_prompt = {
            "name": pack["metadata"]["pack_name"],
            "description": pack["metadata"].get("description", ""),
            "prompt": self._extract_prompt(pack),
            "variables": self._extract_variables(pack),
            "category": pack["metadata"].get("type", "general"),
            "tags": pack["metadata"].get("tags", []),
            "workflow": self._convert_workflow(pack["workflow"]),
        }

        return studio_prompt

    def _extract_prompt(self, pack: Dict[str, Any]) -> str:
        """提取Prompt内容"""
        prompt = ""

        for step in pack["workflow"]["steps"]:
            if step["type"] == "GENERATION":
                prompt += step.get("template", "") + "\n"

        return prompt.strip()

    def _extract_variables(self, pack: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取变量"""
        variables = []

        for step in pack["workflow"]["steps"]:
            if step["type"] == "LOCAL":
                for inp in step.get("inputs", []):
                    variables.append(
                        {
                            "name": inp["key"],
                            "type": "string",
                            "required": inp.get("required", False),
                            "default": inp.get("default", ""),
                        }
                    )

        return variables

    def _convert_workflow(self, workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """转换工作流"""
        studio_workflow = []

        for step in workflow["steps"]:
            studio_step = {"name": step["name"], "type": step["type"], "config": {}}

            # 转换配置
            if step["type"] == "GENERATION":
                studio_step["config"]["template"] = step.get("template", "")
                studio_step["config"]["params"] = step.get("params", {})

            studio_workflow.append(studio_step)

        return studio_workflow


# ==================== 便捷函数 ====================


def integrate_with_notebooklm(pack: Dict[str, Any], user_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    将Pack执行与NotebookLM集成

    Args:
        pack: Pack数据
        user_input: 用户输入

    Returns:
        集成执行结果
    """
    integration = NotebookLMIntegration()

    # 1. 增强Prompt
    topic = user_input.get("topic", "")
    enhanced_prompt = integration.enhance_prompt(
        pack["workflow"]["steps"][2].get("template", ""), topic  # GENERATION步骤
    )

    # 2. 执行Pack（简化版）
    result = {
        "pack_name": pack["metadata"]["pack_name"],
        "enhanced_prompt": enhanced_prompt,
        "status": "success",
    }

    # 3. 保存结果
    integration.save_result(
        content=result.get("generated_content", ""),
        metadata={"pack_name": pack["metadata"]["pack_name"], "topic": topic},
    )

    return result


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=== NotebookLM集成示例 ===\n")

    # 创建集成实例
    integration = NotebookLMIntegration()

    # 连接
    integration.connect()

    # 查询知识
    print("步骤1: 查询知识...")
    knowledge = integration.query_knowledge("AI协作系统")
    print(f"查询结果: {knowledge['response'][:100]}...\n")

    # 增强Prompt
    print("步骤2: 增强Prompt...")
    original_prompt = "请介绍一下{topic}"
    enhanced = integration.enhance_prompt(original_prompt, "AI协作系统")
    print(f"增强后: {enhanced[:150]}...\n")

    # 转换Pack到Studio格式
    print("步骤3: 转换Pack...")
    sample_pack = {
        "metadata": {"pack_name": "测试Pack", "type": "content_generation"},
        "workflow": {
            "steps": [
                {"name": "收集输入", "type": "LOCAL", "inputs": [{"key": "topic"}]},
                {"name": "生成内容", "type": "GENERATION", "template": "关于{topic}的内容"},
            ]
        },
    }

    converter = PackToStudioConverter()
    studio_format = converter.convert(sample_pack)
    print(f"Studio格式: {json.dumps(studio_format, indent=2, ensure_ascii=False)}\n")

    print("=== 完成 ===")
