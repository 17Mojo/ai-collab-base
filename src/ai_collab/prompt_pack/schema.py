"""
Prompt Pack Research - AI 规则管理系统

这个模块实现了 Prompt Pack 研究项目中的 Pack 管理功能。
与 schema_v2.py（PromptPack v2.0 产品）不同，这里的 Pack 用于：
- 为 AI 工具（Claude Code、Copilot）定义规则和上下文
- 支持根据任务类型动态选择和加载不同的 pack
- 实现规则的版本控制和演进管理
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class PackCategoryType(Enum):
    """Pack 分类类型（用于 AI 工具规则管理）"""

    DOMAIN = "domain"  # 领域特定规则
    PROJECT = "project"  # 项目特定规则
    STAGE = "stage"  # 开发阶段规则
    ROLE = "role"  # 角色特定规则


class AITool(Enum):
    """支持的 AI 工具"""

    CLAUDE_CODE = "claude_code"
    GITHUB_COPILOT = "github_copilot"
    CODEARTS_AGENT = "codearts_agent"
    CODEX_AGENT = "codex_agent"
    UNIVERSAL = "universal"  # 跨工具通用


@dataclass
class RuleFile:
    """规则文件定义"""

    filename: str
    content: str
    priority: int = 100  # 优先级，数字越小优先级越高
    enabled: bool = True


@dataclass
class PackManifest:
    """Pack 配置清单 (manifest.json)"""

    name: str
    version: str
    category: PackCategoryType
    description: str
    author: str
    created_at: datetime
    updated_at: datetime

    # 依赖关系
    dependencies: List[str] = field(default_factory=list)  # 其他 pack 名称

    # AI 工具兼容性
    compatible_tools: List[AITool] = field(default_factory=list)

    # 元数据
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "category": self.category.value,
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "dependencies": self.dependencies,
            "compatible_tools": [tool.value for tool in self.compatible_tools],
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackManifest":
        """从字典创建"""
        return cls(
            name=data["name"],
            version=data["version"],
            category=PackCategoryType(data["category"]),
            description=data["description"],
            author=data["author"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            dependencies=data.get("dependencies", []),
            compatible_tools=[AITool(t) for t in data.get("compatible_tools", [])],
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PromptPack:
    """
    Prompt Pack 完整定义

    一个 Prompt Pack 是一组相关联的 AI 规则、提示词和上下文信息的集合。
    用于为特定的 AI 工具或场景提供定制化的上下文和规则。
    """

    manifest: PackManifest

    # 核心规则文件
    rules: Dict[str, RuleFile] = field(default_factory=dict)  # filename -> RuleFile

    # Pack 根目录
    root_path: Optional[Path] = None

    def add_rule(self, filename: str, content: str, priority: int = 100, enabled: bool = True):
        """添加规则文件"""
        self.rules[filename] = RuleFile(
            filename=filename, content=content, priority=priority, enabled=enabled
        )

    def get_rules_content(self, tool: Optional[AITool] = None) -> List[str]:
        """
        获取规则内容列表（按优先级排序）

        Args:
            tool: 目标 AI 工具，用于过滤兼容的规则

        Returns:
            List[str]: 规则内容列表
        """
        # 检查工具兼容性
        if tool and tool not in self.manifest.compatible_tools:
            if AITool.UNIVERSAL in self.manifest.compatible_tools:
                pass  # Universal pack 对所有工具兼容
            else:
                return []  # 不兼容，返回空列表

        # 按优先级排序并过滤启用的规则
        sorted_rules = sorted(
            [r for r in self.rules.values() if r.enabled], key=lambda r: r.priority
        )

        return [rule.content for rule in sorted_rules]

    def validate(self) -> bool:
        """验证 Pack 结构完整性"""
        if not self.manifest.name:
            return False

        if not self.manifest.version:
            return False

        return True

    def to_context(self, tool: AITool) -> str:
        """
        转换为 AI 工具可用的上下文字符串

        Args:
            tool: 目标 AI 工具

        Returns:
            str: 格式化的上下文字符串
        """
        rules_content = self.get_rules_content(tool)

        if not rules_content:
            return ""

        header = f"# Prompt Pack: {self.manifest.name} (v{self.manifest.version})\n"
        header += f"# Category: {self.manifest.category.value}\n"
        header += f"# Description: {self.manifest.description}\n\n"

        return header + "\n\n".join(rules_content)


class PackCompatibilityError(Exception):
    """Pack 兼容性错误"""

    pass


class PackDependencyError(Exception):
    """Pack 依赖错误"""

    pass
