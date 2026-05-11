"""
AI 协作开发系统 - VSCode 集成版

协调 Claude Code 与 GitHub Copilot 的协作开发
"""

__version__ = "2.0.0"

from .activation_handler import ActivationHandler, ActivationMode, AIType, VSCodeIntegration
from .agent_orchestrator import AgentOrchestrator
from .codex_integration import CodexIntegration
from .dev_logger import DevLogger, VSCodeOutputLogger
from .state_manager import Conflict, FileStatus, StateManager, Task, TaskStatus, VSCodeStateManager

__all__ = [
    "AIType",
    "ActivationHandler",
    "ActivationMode",
    "VSCodeIntegration",
    "TaskStatus",
    "FileStatus",
    "Task",
    "Conflict",
    "StateManager",
    "VSCodeStateManager",
    "DevLogger",
    "VSCodeOutputLogger",
    "CodexIntegration",
    "AgentOrchestrator",
]
