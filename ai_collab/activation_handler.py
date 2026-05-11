"""
激活处理器模块 - VSCode 集成版

支持 Claude Code 与 GitHub Copilot 的协作开发
提供 Python 模块、CLI、VSCode 事件监听多种调用方式
集成 Prompt Pack 功能，支持根据任务类型加载相应的 Pack
"""

import json
import os
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, cast


class AIType(Enum):
    """AI类型枚举"""

    CLAUDE_CODE = "claude_code"
    COPILOT = "copilot"
    CODEARTS_AGENT = "codearts_agent"


class ActivationMode(Enum):
    """激活模式枚举"""

    # VSCode 命令触发
    COMMAND = "command"
    # 文件保存触发
    ON_SAVE = "on_save"
    # VSCode 事件监听触发
    EVENT = "event"
    # 手动 CLI 触发
    CLI = "cli"


class VSCodeIntegration:
    """VSCode 集成辅助类"""

    @staticmethod
    def _is_valid_workspace(path: str) -> bool:
        """验证工作区路径，过滤掉无效根路径。"""
        if not path:
            return False

        resolved = os.path.abspath(path)
        if resolved == os.path.abspath(os.sep):
            return False

        return os.path.isdir(resolved)

    @staticmethod
    def get_workspace_path() -> Optional[str]:
        """获取当前 VSCode 工作区路径"""
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
        """获取项目级 AI 协作配置"""
        workspace = VSCodeIntegration.get_workspace_path()
        if not workspace:
            return {}

        config_file = os.path.join(workspace, ".vscode", "ai-collab.json")
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    return cast(Dict[str, Any], loaded)
        return {}

    @staticmethod
    def get_global_config() -> Dict[str, Any]:
        """获取全局 AI 协作配置"""
        global_config_dir = os.path.expanduser("~/.vscode/ai-collab")
        config_file = os.path.join(global_config_dir, "config.json")
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    return cast(Dict[str, Any], loaded)
        return {}

    @staticmethod
    def save_project_config(config: Dict[str, Any]):
        """保存项目级配置"""
        workspace = VSCodeIntegration.get_workspace_path()
        if not workspace:
            raise ValueError("无法获取工作区路径")

        config_dir = os.path.join(workspace, ".vscode")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "ai-collab.json")

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    @staticmethod
    def update_vscode_output(message: str, channel: str = "AI Collab"):
        """更新 VSCode 输出面板"""
        # 尝试调用 node 脚本或写入日志
        try:
            global_config_dir = os.path.expanduser("~/.vscode/ai-collab")
            os.makedirs(global_config_dir, exist_ok=True)
            log_file = os.path.join(
                global_config_dir, f"output_{datetime.now().strftime('%Y%m%d')}.log"
            )
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] [{channel}] {message}\n")
        except Exception:
            pass  # 静默失败

    @staticmethod
    def get_rule_files(ai_type: AIType) -> List[str]:
        """获取规则文件列表"""
        project_config = VSCodeIntegration.get_project_config()
        rules_dir = project_config.get("rulesDir", "./rules")

        rules_map = {
            AIType.CLAUDE_CODE: [
                "claude_code_memory.md",
                "agent_governance_quickstart.md",
                "AI-COLLABORATION-STANDARDS.md",
                "dev-record-template.md",
            ],
            AIType.CODEARTS_AGENT: [
                "codearts_agent_rules.md",
                "agent_governance_quickstart.md",
                "AI-COLLABORATION-STANDARDS.md",
                "dev-record-template.md",
            ],
            AIType.COPILOT: [
                "copilot_rules.md",
                "AI-COLLABORATION-STANDARDS.md",
                "dev-record-template.md",
            ],
        }

        rule_files = rules_map.get(ai_type, [])
        return [os.path.join(rules_dir, f) for f in rule_files]


class ActivationHandler:
    """
    激活处理器 - VSCode 集成版

    支持：
    - Python 模块调用
    - CLI 命令调用
    - VSCode 事件监听
    """

    # 默认配置
    ACTIVATION_KEYWORD = "2X"
    ACTIVATIONS_LOG_DIR = "./logs/activations"
    GIT_AI_COLLAB_DIR = ".git/ai-collab"

    # ACK 响应模板
    ACK_TEMPLATES: Dict[AIType, str] = {
        AIType.CLAUDE_CODE: "Claude Code ACK: 记忆已激活，已读取 {rules}，准备执行。",
        AIType.CODEARTS_AGENT: "CodeArts Agent ACK: 治理规则已激活，进入执行辅助模式。",
        AIType.COPILOT: "Copilot ACK: 记忆已激活，已读取 {rules}，准备执行。",
    }

    def __init__(
        self,
        ai_type: AIType,
        workspace_path: Optional[str] = None,
        on_activated: Optional[Callable[[str, List[str], Dict[str, Any]], None]] = None,
    ):
        """
        初始化激活处理器

        Args:
            ai_type: AI 类型 (CLAUDE_CODE / COPILOT)
            workspace_path: 工作区路径（可选）
            on_activated: 激活回调函数
        """
        self.ai_type = ai_type
        self.workspace_path = workspace_path or VSCodeIntegration.get_workspace_path()
        self.session_id = self._generate_session_id()
        self.activation_time: Optional[datetime] = None
        self.on_activated = on_activated
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        base_dir = self.workspace_path or "."
        os.makedirs(os.path.join(base_dir, self.ACTIVATIONS_LOG_DIR), exist_ok=True)
        os.makedirs(os.path.join(base_dir, self.GIT_AI_COLLAB_DIR, "activations"), exist_ok=True)

    def _generate_session_id(self) -> str:
        """生成会话 ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"{self.ai_type.value}_{timestamp}"

    def check_activation(self, user_input: str, mode: ActivationMode = ActivationMode.CLI) -> bool:
        """
        检查是否应该激活

        Args:
            user_input: 用户输入或触发内容
            mode: 激活模式

        Returns:
            是否应该激活
        """
        if not user_input:
            return False

        if mode == ActivationMode.CLI:
            # CLI 模式：检查激活词
            return self.ACTIVATION_KEYWORD in user_input
        elif mode == ActivationMode.ON_SAVE:
            # 保存触发：检查文件扩展名是否在白名单
            file_ext = os.path.splitext(user_input)[1].lower()
            project_config = VSCodeIntegration.get_project_config()
            watch_extensions = project_config.get(
                "watchExtensions", [".ts", ".js", ".py", ".go", ".rs"]
            )
            return file_ext in watch_extensions
        elif mode == ActivationMode.EVENT or mode == ActivationMode.COMMAND:
            # 事件或命令模式：总是激活
            return True

        return False

    def activate(
        self, mode: ActivationMode = ActivationMode.CLI, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行激活流程

        Args:
            mode: 激活模式
            context: 额外上下文（如文件路径、命令等）

        Returns:
            激活结果字典
        """
        activation_time = datetime.now()
        self.activation_time = activation_time

        # 如果没有传递 context，自动从状态文件中提取
        if not context:
            context = self._extract_context_from_state()
        else:
            context = context or {}

        # 加载规则文件
        rules = self._load_rules()

        # 生成 ACK 消息
        ack_message = self._generate_ack(rules)

        # 记录激活日志
        self._log_activation(rules, ack_message, mode, context)

        # 更新 VSCode 输出面板
        VSCodeIntegration.update_vscode_output(
            f"{self.ai_type.value} ACTIVATED: {ack_message}", "AI Collab"
        )

        # 调用回调函数
        if self.on_activated:
            try:
                self.on_activated(self.session_id, rules, context)
            except Exception as e:
                print(f"激活回调执行失败: {e}")

        return {
            "session_id": self.session_id,
            "ai_type": self.ai_type.value,
            "activation_time": activation_time.isoformat(),
            "mode": mode.value,
            "rules_loaded": rules,
            "ack_message": ack_message,
            "success": True,
            "context": context,
        }

    def _extract_context_from_state(self) -> Dict[str, Any]:
        """
        从任务状态文件中提取 context 信息

        优先选择与当前 AI 类型匹配的活跃任务；如果不存在，再降级到任意活跃任务。

        Returns:
            包含任务信息的上下文字典，如果没有活跃任务则返回空字典
        """
        try:
            state_file = os.path.join(self.workspace_path or ".", "logs/collaboration_state.json")

            if not os.path.exists(state_file):
                return {}

            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            tasks = state.get("tasks", {})
            if not isinstance(tasks, dict):
                return {}

            active_status = {
                "pending",
                "planning",
                "implementing",
                "in_progress",
                "testing",
                "blocked",
            }
            ai_aliases = {self.ai_type.value}
            # 兼容历史任务类型：copilot <-> codearts_agent
            if self.ai_type == AIType.COPILOT:
                ai_aliases.add(AIType.CODEARTS_AGENT.value)
            elif self.ai_type == AIType.CODEARTS_AGENT:
                ai_aliases.add(AIType.COPILOT.value)

            def _build_context(task_data: Dict[str, Any]) -> Dict[str, Any]:
                context = {
                    "task_id": task_data.get("task_id"),
                    "description": task_data.get("description"),
                    "status": task_data.get("status"),
                    "files": task_data.get("files", []),
                    "ai_type": task_data.get("ai_type"),
                    "created_at": task_data.get("created_at"),
                    "updated_at": task_data.get("updated_at"),
                    "notes": task_data.get("notes", []),
                    "progress": task_data.get("progress"),
                    "dependency": task_data.get("dependency"),
                    "vscode_context": task_data.get("vscode_context", {}),
                }
                return {k: v for k, v in context.items() if v is not None}

            def _resolve_task(task_id: Any) -> Optional[Dict[str, Any]]:
                if not isinstance(task_id, str):
                    return None
                task_data = tasks.get(task_id)
                if isinstance(task_data, dict):
                    return task_data
                return None

            def _is_active(task_data: Dict[str, Any]) -> bool:
                return str(task_data.get("status", "")).lower() in active_status

            def _matches_ai(task_data: Dict[str, Any]) -> bool:
                return str(task_data.get("ai_type", "")).lower() in ai_aliases

            # 1) 当前 active_task 且匹配 AI
            active_task_id = state.get("active_task")
            task = _resolve_task(active_task_id)
            if task and _is_active(task) and _matches_ai(task):
                return _build_context(task)

            # 2) active_tasks 中首个匹配 AI 的活跃任务
            active_tasks = state.get("active_tasks", [])
            if isinstance(active_tasks, list):
                for task_id in active_tasks:
                    task = _resolve_task(task_id)
                    if task and _is_active(task) and _matches_ai(task):
                        return _build_context(task)

            # 3) 全量任务中查找该 AI 最新活跃任务
            matched_active_tasks: List[Dict[str, Any]] = []
            for task_data in tasks.values():
                if isinstance(task_data, dict) and _is_active(task_data) and _matches_ai(task_data):
                    matched_active_tasks.append(task_data)

            if matched_active_tasks:
                matched_active_tasks.sort(
                    key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
                    reverse=True,
                )
                return _build_context(matched_active_tasks[0])

            # 4) 兜底：任意活跃任务（保持向后兼容）
            if isinstance(active_tasks, list):
                for task_id in active_tasks:
                    task = _resolve_task(task_id)
                    if task and _is_active(task):
                        return _build_context(task)

            return {}

        except Exception:
            # 静默忽略错误，返回空字典
            return {}

    def _load_rules(self) -> List[str]:
        """加载规则文件"""
        rule_paths = VSCodeIntegration.get_rule_files(self.ai_type)

        loaded_rules = []
        for rule_path in rule_paths:
            # 如果路径不是绝对路径，基于工作区路径解析
            if not os.path.isabs(rule_path):
                full_path = os.path.join(self.workspace_path or ".", rule_path)
            else:
                full_path = rule_path

            if os.path.exists(full_path):
                loaded_rules.append(os.path.basename(rule_path))

        return loaded_rules

    def _generate_ack(self, rules: List[str]) -> str:
        """生成 ACK 消息"""
        template = self.ACK_TEMPLATES.get(self.ai_type)
        if template is None:
            template = "AI ACK: 记忆已激活，已读取 {rules}，准备执行。"
        rules_str = ", ".join(rules) if rules else "无规则文件"
        return template.format(rules=rules_str)

    def _log_activation(
        self, rules: List[str], ack_message: str, mode: ActivationMode, context: Dict[str, Any]
    ):
        """记录激活日志"""
        activation_time = self.activation_time or datetime.now()
        log_entry = {
            "session_id": self.session_id,
            "ai_type": self.ai_type.value,
            "activation_time": activation_time.isoformat(),
            "mode": mode.value,
            "rules_loaded": rules,
            "ack_message": ack_message,
            "context": context,
        }

        base_dir = self.workspace_path or "."
        date_str = activation_time.strftime("%Y-%m-%d")

        # 写入 logs/activations/
        log_file = os.path.join(base_dir, self.ACTIVATIONS_LOG_DIR, f"{date_str}.jsonl")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # 写入 .git/ai-collab/ （Git 追踪）
        git_log_file = os.path.join(
            base_dir, self.GIT_AI_COLLAB_DIR, "activations", f"{date_str}.jsonl"
        )
        with open(git_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def get_rules_content(self) -> Dict[str, str]:
        """获取规则文件内容"""
        contents = {}
        rule_paths = VSCodeIntegration.get_rule_files(self.ai_type)

        for rule_path in rule_paths:
            if not os.path.isabs(rule_path):
                full_path = os.path.join(self.workspace_path or ".", rule_path)
            else:
                full_path = rule_path

            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    contents[os.path.basename(rule_path)] = f.read()

        return contents

    @staticmethod
    def get_active_sessions() -> List[Dict[str, Any]]:
        """获取当前活跃的会话"""
        config = VSCodeIntegration.get_project_config()
        if not config:
            return []

        state_file = config.get("stateFile", "./logs/collaboration_state.json")
        workspace = VSCodeIntegration.get_workspace_path()

        if workspace:
            state_file = os.path.join(workspace, state_file)

        if not os.path.exists(state_file):
            return []

        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)

        if not isinstance(state, dict):
            return []

        active_tasks = state.get("active_tasks", [])
        return [
            state["tasks"].get(task_id, {})
            for task_id in active_tasks
            if task_id in state.get("tasks", {})
        ]
