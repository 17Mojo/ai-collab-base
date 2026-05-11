"""
Pack 集成助手 - 为 AI 激活流程提供 Pack 支持

这个模块提供 Pack 集成功能，可以在 AI 激活时自动加载相关的 Pack 上下文。
"""

from pathlib import Path
from typing import Any, Dict, Optional

from ai_collab.prompt_pack import AITool, PackManager


class PackIntegrationHelper:
    """Pack 集成助手类"""

    def __init__(self, workspace_path: Optional[str] = None):
        """
        初始化 Pack 集成助手

        Args:
            workspace_path: 工作区路径
        """
        workspace = Path(workspace_path or Path.cwd())
        packs_root = workspace / "packs"
        self.manager = PackManager(packs_root)
        self.active_pack: Optional[str] = None
        self.pack_context: str = ""

    def recommend_pack_for_task(self, task_description: str, ai_type_str: str) -> Optional[str]:
        """
        根据任务描述推荐 Pack

        Args:
            task_description: 任务描述
            ai_type_str: AI 类型字符串

        Returns:
            推荐的 Pack 名称，如果没有匹配则返回 None
        """
        # 映射 AI 类型
        ai_type_map = {
            "claude_code": AITool.CLAUDE_CODE,
            "github_copilot": AITool.GITHUB_COPILOT,
            "codex_agent": AITool.CODEX_AGENT,
            "codearts_agent": AITool.CODEARTS_AGENT,
        }
        tool = ai_type_map.get(ai_type_str, AITool.UNIVERSAL)

        # 获取最佳 Pack
        recommended = self.manager.get_best_pack(task_description, tool)
        return recommended.manifest.name if recommended else None

    def load_pack(self, pack_name: str, ai_type_str: str) -> str:
        """
        加载 Pack 并返回上下文

        Args:
            pack_name: Pack 名称
            ai_type_str: AI 类型字符串

        Returns:
            Pack 上下文字符串
        """
        # 映射 AI 类型
        ai_type_map = {
            "claude_code": AITool.CLAUDE_CODE,
            "github_copilot": AITool.GITHUB_COPILOT,
            "codex_agent": AITool.CODEX_AGENT,
            "codearts_agent": AITool.CODEARTS_AGENT,
        }
        tool = ai_type_map.get(ai_type_str, AITool.UNIVERSAL)

        # 获取 Pack 上下文（包含依赖）
        context = self.manager.get_packed_context(pack_name, tool, include_dependencies=True)

        self.active_pack = pack_name
        self.pack_context = context

        return context

    def activate_pack_for_task(self, task_description: str, ai_type_str: str) -> Dict[str, Any]:
        """
        为任务推荐并激活 Pack

        Args:
            task_description: 任务描述
            ai_type_str: AI 类型字符串

        Returns:
            激活结果字典
        """
        # 推荐 Pack
        pack_name = self.recommend_pack_for_task(task_description, ai_type_str)

        if not pack_name:
            return {"success": False, "message": "未找到匹配的 Pack", "pack_name": None}

        # 加载 Pack
        context = self.load_pack(pack_name, ai_type_str)

        return {
            "success": True,
            "message": f"已激活 Pack: {pack_name}",
            "pack_name": pack_name,
            "context": context,
        }

    def get_available_packs(self) -> list:
        """获取所有可用的 Pack"""
        return self.manager.list_available_packs()

    def inject_into_activation_context(
        self, activation_result: Dict[str, Any], task_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        将 Pack 上下文注入到激活结果中

        Args:
            activation_result: 原始激活结果
            task_description: 可选的任务描述，用于推荐 Pack

        Returns:
            注入 Pack 上下文后的激活结果
        """
        ai_type_str = activation_result.get("ai_type", "")

        # 如果有任务描述，尝试自动推荐 Pack
        if task_description and self.manager:
            pack_result = self.activate_pack_for_task(task_description, ai_type_str)
            if pack_result["success"]:
                activation_result["pack_name"] = pack_result["pack_name"]
                activation_result["pack_context"] = pack_result["context"]
                activation_result["ack_message"] += f" | Pack: {pack_result['pack_name']}"

        return activation_result


def create_pack_integration(workspace_path: Optional[str] = None) -> PackIntegrationHelper:
    """
    创建 Pack 集成助手实例

    Args:
        workspace_path: 工作区路径

    Returns:
        PackIntegrationHelper 实例
    """
    return PackIntegrationHelper(workspace_path)
