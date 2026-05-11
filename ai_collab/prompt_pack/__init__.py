"""
Prompt Pack Research - AI 规则管理系统

这个包实现了 Prompt Pack 研究项目的核心功能。
与 Prompt Pack v2.0 产品不同，这里的 Pack 用于为 AI 工具定义上下文和规则。
"""

from .manager import PackManager
from .schema import (
    AITool,
    PackCategoryType,
    PackCompatibilityError,
    PackDependencyError,
    PackManifest,
    PromptPack,
    RuleFile,
)

__all__ = [
    # Schema
    "PromptPack",
    "PackManifest",
    "RuleFile",
    "PackCategoryType",
    "AITool",
    "PackCompatibilityError",
    "PackDependencyError",
    # Manager
    "PackManager",
]
