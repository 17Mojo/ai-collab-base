"""
VSCode 集成辅助模块

提供 VSCode 环境下的常用功能，支持多模块共享
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class VSCodeIntegration:
    """VSCode 集成辅助类"""

    @staticmethod
    def _is_valid_workspace(path: str) -> bool:
        """
        验证工作区路径，过滤掉无效根路径

        Args:
            path: 待验证的路径

        Returns:
            是否为有效工作区
        """
        if not path:
            return False

        resolved = os.path.abspath(path)
        if resolved == os.path.abspath(os.sep):
            return False

        return os.path.isdir(resolved)

    @staticmethod
    def get_workspace_path() -> Optional[str]:
        """
        获取当前 VSCode 工作区路径

        Returns:
            工作区路径，如果找不到则返回 None
        """
        # 通过环境变量获取工作区路径
        workspace = os.environ.get("VSCODE_CWD")
        if workspace and VSCodeIntegration._is_valid_workspace(workspace):
            return os.path.abspath(workspace)

        # 尝试从 .vscode 目录定位
        cwd = os.path.abspath(os.getcwd())
        if cwd:
            # 向上查找包含 .vscode 或 package.json 的目录
            path = cwd
            while path and path != os.path.dirname(path):
                if os.path.exists(os.path.join(path, ".vscode")) or os.path.exists(
                    os.path.join(path, "package.json")
                ):
                    return path
                path = os.path.dirname(path)

        return cwd

    @staticmethod
    def get_project_config() -> Dict[str, Any]:
        """
        获取项目级 AI 协作配置

        Returns:
            配置字典，如果没找到则返回空字典
        """
        workspace = VSCodeIntegration.get_workspace_path()
        if not workspace:
            return {}

        config_file = os.path.join(workspace, ".vscode", "ai-collab.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    @staticmethod
    def get_global_config() -> Dict[str, Any]:
        """
        获取全局 AI 协作配置

        Returns:
            全局配置字典
        """
        global_config_dir = os.path.expanduser("~/.vscode/ai-collab")
        config_file = os.path.join(global_config_dir, "config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    @staticmethod
    def save_project_config(config: Dict[str, Any]):
        """
        保存项目级配置

        Args:
            config: 配置字典

        Raises:
            ValueError: 如果无法获取工作区路径
        """
        workspace = VSCodeIntegration.get_workspace_path()
        if not workspace:
            raise ValueError("无法获取工作区路径")

        config_dir = os.path.join(workspace, ".vscode")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "ai-collab.json")

        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except IOError as e:
            raise ValueError(f"无法保存配置文件: {e}")

    @staticmethod
    def update_vscode_output(message: str, channel: str = "AI Collab"):
        """
        更新 VSCode 输出面板

        Args:
            message: 输出消息
            channel: 输出频道名称
        """
        try:
            global_config_dir = os.path.expanduser("~/.vscode/ai-collab")
            os.makedirs(global_config_dir, exist_ok=True)
            log_file = os.path.join(
                global_config_dir, f"output_{datetime.now().strftime('%Y%m%d')}.log"
            )
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] [{channel}] {message}\n")
        except Exception:
            # 静默失败，避免影响主流程
            pass

    @staticmethod
    def get_rule_files(ai_type: str, rules_dir: str = "./rules") -> List[str]:
        """
        获取规则文件列表

        Args:
            ai_type: AI 类型 (CLAUDE_CODE / COPILOT)
            rules_dir: 规则文件目录

        Returns:
            规则文件路径列表
        """
        project_config = VSCodeIntegration.get_project_config()
        rules_dir = project_config.get("rulesDir", rules_dir)

        rules_map = {
            "claude_code": [
                "claude_code_memory.md",
                "agent_governance_quickstart.md",
                "AI-COLLABORATION-STANDARDS.md",
                "dev-record-template.md",
            ],
            "codearts_agent": [
                "codearts_agent_rules.md",
                "agent_governance_quickstart.md",
                "AI-COLLABORATION-STANDARDS.md",
                "dev-record-template.md",
            ],
            "copilot": [
                "copilot_rules.md",
                "AI-COLLABORATION-STANDARDS.md",
                "dev-record-template.md",
            ],
        }

        rule_files = rules_map.get(ai_type.lower(), [])
        return [os.path.join(rules_dir, f) for f in rule_files]


if __name__ == "__main__":
    # 测试 VSCode 集成功能
    print("🔧 测试 VSCode 集成功能")

    workspace = VSCodeIntegration.get_workspace_path()
    print(f"工作区路径: {workspace}")

    project_config = VSCodeIntegration.get_project_config()
    print(f"项目配置: {project_config}")

    global_config = VSCodeIntegration.get_global_config()
    print(f"全局配置: {global_config}")

    # 测试输出更新
    VSCodeIntegration.update_vscode_output("测试消息", "测试频道")
    print("✅ VSCode 输出面板更新测试成功")
