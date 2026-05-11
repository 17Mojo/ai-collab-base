# Pack Template System
# Week 2 Day 4: Pack 模板系统

"""
Pack 模板系统
支持预定义模板和自定义模板
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class TemplateCategory(Enum):
    """模板类别"""

    PRODUCTIVITY = "productivity"
    CREATIVE = "creative"
    RESEARCH = "research"


@dataclass
class PackTemplate:
    """Pack 模板"""

    template_id: str
    name: str
    description: str
    category: TemplateCategory
    tags: List[str] = field(default_factory=list)
    schema: Dict[str, Any] = field(default_factory=dict)
    workflow_data: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "tags": self.tags,
            "schema": self.schema,
            "workflow_data": self.workflow_data,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackTemplate":
        """从字典反序列化"""
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            description=data["description"],
            category=TemplateCategory(data["category"]),
            tags=data.get("tags", []),
            schema=data.get("schema", {}),
            workflow_data=data.get("workflow_data", {}),
            parameters=data.get("parameters", {}),
        )


@dataclass
class TemplateInstance:
    """模板实例（基于模板创建的 Pack）"""

    instance_id: str
    template_id: str
    pack_name: str
    parameters: Dict[str, Any]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "instance_id": self.instance_id,
            "template_id": self.template_id,
            "pack_name": self.pack_name,
            "parameters": self.parameters,
            "created_at": self.created_at,
        }


class TemplateLibrary:
    """模板库"""

    def __init__(self, template_dir: Optional[str] = None):
        """初始化模板库

        Args:
            template_dir: 模板目录（默认 templates/）
        """
        self.template_dir = template_dir or "templates"
        self._templates: Dict[str, PackTemplate] = {}
        self._ensure_template_dir()
        self._load_predefined_templates()

    def _ensure_template_dir(self) -> None:
        """确保模板目录存在"""
        Path(self.template_dir).mkdir(parents=True, exist_ok=True)

    def _load_predefined_templates(self) -> None:
        """加载预定义模板"""
        # 生产力模板
        self._templates["email-helper"] = PackTemplate(
            template_id="email-helper",
            name="邮件助手",
            description="帮助撰写和管理邮件",
            category=TemplateCategory.PRODUCTIVITY,
            tags=["email", "communication"],
            schema={
                "name": {"type": "string", "description": "Pack 名称"},
                "version": {"type": "string", "description": "版本号"},
                "description": {"type": "string", "description": "描述"},
            },
            workflow_data={
                "steps": [
                    {"action": "input", "field": "recipient"},
                    {"action": "input", "field": "subject"},
                    {"action": "validate", "rule": "email_format"},
                    {"action": "output", "field": "email_body"},
                ]
            },
            parameters={
                "tone": {
                    "default": "professional",
                    "options": ["professional", "casual", "formal"],
                },
                "language": {"default": "English", "options": ["English", "Chinese"]},
            },
        )

        self._templates["task-manager"] = PackTemplate(
            template_id="task-manager",
            name="任务管理",
            description="规划和跟踪任务",
            category=TemplateCategory.PRODUCTIVITY,
            tags=["productivity", "planning"],
            schema={
                "name": {"type": "string", "description": "Pack 名称"},
                "version": {"type": "string", "description": "版本号"},
            },
            workflow_data={
                "steps": [
                    {"action": "input", "field": "task_list"},
                    {"action": "validate", "rule": "task_format"},
                    {"action": "organize", "by": "priority"},
                    {"action": "output", "field": "organized_tasks"},
                ]
            },
            parameters={
                "priority_system": {
                    "default": "high_medium_low",
                    "options": ["high_medium_low", "eisenhower"],
                }
            },
        )

        self._templates["meeting-notes"] = PackTemplate(
            template_id="meeting-notes",
            name="会议记录",
            description="记录和整理会议内容",
            category=TemplateCategory.PRODUCTIVITY,
            tags=["meeting", "documentation"],
            schema={"name": {"type": "string", "description": "Pack 名称"}},
            workflow_data={
                "steps": [
                    {"action": "input", "field": "attendees"},
                    {"action": "input", "field": "agenda"},
                    {"action": "record", "field": "notes"},
                    {"action": "summarize", "field": "action_items"},
                    {"action": "output", "field": "meeting_summary"},
                ]
            },
            parameters={"format": {"default": "markdown", "options": ["markdown", "text"]}},
        )

        # 创意模板
        self._templates["creative-writing"] = PackTemplate(
            template_id="creative-writing",
            name="创意写作",
            description="激发创意和灵感",
            category=TemplateCategory.CREATIVE,
            tags=["writing", "creativity"],
            schema={"name": {"type": "string", "description": "Pack 名称"}},
            workflow_data={
                "steps": [
                    {"action": "input", "field": "topic"},
                    {"action": "brainstorm", "method": "random_words"},
                    {"action": "organize", "structure": "story_arc"},
                    {"action": "output", "field": "creative_content"},
                ]
            },
            parameters={
                "genre": {
                    "default": "general",
                    "options": ["general", "fiction", "poetry", "dialogue"],
                }
            },
        )

        self._templates["brainstorming"] = PackTemplate(
            template_id="brainstorming",
            name="头脑风暴",
            description="产生创意想法",
            category=TemplateCategory.CREATIVE,
            tags=["brainstorming", "ideas"],
            schema={"name": {"type": "string", "description": "Pack 名称"}},
            workflow_data={
                "steps": [
                    {"action": "input", "field": "prompt"},
                    {"action": "brainstorm", "quantity": 10},
                    {"action": "evaluate", "criteria": "feasibility"},
                    {"action": "output", "field": "top_ideas"},
                ]
            },
        )

        # 研究模板
        self._templates["literature-summary"] = PackTemplate(
            template_id="literature-summary",
            name="文献总结",
            description="总结和分析文献",
            category=TemplateCategory.RESEARCH,
            tags=["research", "literature"],
            schema={"name": {"type": "string", "description": "Pack 名称"}},
            workflow_data={
                "steps": [
                    {"action": "input", "field": "paper_urls"},
                    {"action": "extract", "field": "key_points"},
                    {"action": "compare", "across": "papers"},
                    {"action": "output", "field": "summary_report"},
                ]
            },
        )

        self._templates["data-analysis"] = PackTemplate(
            template_id="data-analysis",
            name="数据分析",
            description="分析和可视化数据",
            category=TemplateCategory.RESEARCH,
            tags=["analysis", "data"],
            schema={"name": {"type": "string", "description": "Pack 名称"}},
            workflow_data={
                "steps": [
                    {"action": "input", "field": "data_source"},
                    {"action": "validate", "rule": "data_format"},
                    {"action": "analyze", "method": "statistics"},
                    {"action": "visualize", "type": "charts"},
                    {"action": "output", "field": "analysis_report"},
                ]
            },
        )

    def list_templates(self, category: Optional[TemplateCategory] = None) -> List[PackTemplate]:
        """列出模板

        Args:
            category: 类别过滤（可选）

        Returns:
            模板列表
        """
        templates = list(self._templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        return templates

    def get_template(self, template_id: str) -> Optional[PackTemplate]:
        """获取模板

        Args:
            template_id: 模板 ID

        Returns:
            模板，不存在返回 None
        """
        return self._templates.get(template_id)

    def search_templates(self, query: str) -> List[PackTemplate]:
        """搜索模板

        Args:
            query: 搜索关键词

        Returns:
            匹配的模板列表
        """
        query_lower = query.lower()

        results = []
        for template in self._templates.values():
            # 搜索名称、描述、标签
            if (
                query_lower in template.name.lower()
                or query_lower in template.description.lower()
                or any(query_lower in tag.lower() for tag in template.tags)
            ):
                results.append(template)

        return results

    def create_instance(
        self, template_id: str, pack_name: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[TemplateInstance]:
        """基于模板创建 Pack 实例

        Args:
            template_id: 模板 ID
            pack_name: Pack 名称
            parameters: 参数（可选）

        Returns:
            模板实例
        """
        template = self.get_template(template_id)

        if template is None:
            return None

        # 合并参数
        pack_parameters = template.parameters.copy()
        if parameters:
            pack_parameters.update(parameters)

        import datetime

        instance = TemplateInstance(
            instance_id=f"inst_{template_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            template_id=template_id,
            pack_name=pack_name,
            parameters=pack_parameters,
            created_at=datetime.datetime.now().isoformat(),
        )

        return instance

    def add_template(self, template: PackTemplate) -> bool:
        """添加自定义模板

        Args:
            template: 模板

        Returns:
            是否添加成功
        """
        if template.template_id in self._templates:
            return False

        self._templates[template.template_id] = template

        # 保存到文件
        template_file = Path(self.template_dir) / f"{template.template_id}.json"
        with open(template_file, "w") as f:
            json.dump(template.to_dict(), f, indent=2)

        return True

    def remove_template(self, template_id: str) -> bool:
        """移除自定义模板

        Args:
            template_id: 模板 ID

        Returns:
            是否移除成功
        """
        if template_id not in self._templates:
            return False

        # 不允许删除预定义模板
        predefined_ids = [
            "email-helper",
            "task-manager",
            "meeting-notes",
            "creative-writing",
            "brainstorming",
            "literature-summary",
            "data-analysis",
        ]

        if template_id in predefined_ids:
            return False

        del self._templates[template_id]

        # 删除文件
        template_file = Path(self.template_dir) / f"{template_id}.json"
        if template_file.exists():
            template_file.unlink()

        return True

    def get_categories(self) -> List[TemplateCategory]:
        """获取所有模板类别

        Returns:
            类别列表
        """
        categories = set()

        for template in self._templates.values():
            categories.add(template.category)

        return sorted(list(categories), key=lambda x: x.value)
