# Pack Template System Tests
# Week 2 Day 4: Pack 模板系统测试

"""
Pack 模板系统功能测试
"""

from datetime import datetime

import pytest

from ai_collab.pack.template import (
    PackTemplate,
    TemplateCategory,
    TemplateInstance,
    TemplateLibrary,
)


class TestTemplateCategory:
    """测试 TemplateCategory 枚举"""

    def test_category_values(self):
        """测试类别值"""
        assert TemplateCategory.PRODUCTIVITY.value == "productivity"
        assert TemplateCategory.CREATIVE.value == "creative"
        assert TemplateCategory.RESEARCH.value == "research"

    def test_category_from_string(self):
        """测试从字符串创建类别"""
        cat = TemplateCategory("productivity")
        assert cat == TemplateCategory.PRODUCTIVITY


class TestPackTemplate:
    """测试 PackTemplate 数据类"""

    def test_create_template(self):
        """测试创建模板"""
        template = PackTemplate(
            template_id="test-template",
            name="Test Template",
            description="A test template",
            category=TemplateCategory.PRODUCTIVITY,
            tags=["test"],
        )

        assert template.template_id == "test-template"
        assert template.category == TemplateCategory.PRODUCTIVITY
        assert template.tags == ["test"]

    def test_template_to_dict(self):
        """测试序列化为字典"""
        template = PackTemplate(
            template_id="test-template",
            name="Test Template",
            description="A test template",
            category=TemplateCategory.PRODUCTIVITY,
        )

        data = template.to_dict()

        assert data["template_id"] == "test-template"
        assert data["category"] == "productivity"
        assert data["tags"] == []

    def test_template_from_dict(self):
        """测试从字典反序列化"""
        data = {
            "template_id": "test-template",
            "name": "Test Template",
            "description": "A test template",
            "category": "productivity",
            "tags": [],
            "schema": {},
            "workflow_data": {},
            "parameters": {},
        }

        template = PackTemplate.from_dict(data)

        assert template.template_id == "test-template"
        assert template.category == TemplateCategory.PRODUCTIVITY


class TestTemplateInstance:
    """测试 TemplateInstance 数据类"""

    def test_create_instance(self):
        """测试创建实例"""
        instance = TemplateInstance(
            instance_id="inst_001",
            template_id="template-001",
            pack_name="My Pack",
            parameters={"param1": "value1"},
            created_at=datetime.now().isoformat(),
        )

        assert instance.template_id == "template-001"
        assert instance.parameters == {"param1": "value1"}

    def test_instance_to_dict(self):
        """测试序列化为字典"""
        instance = TemplateInstance(
            instance_id="inst_001",
            template_id="template-001",
            pack_name="My Pack",
            parameters={},
            created_at="2026-04-05T10:00:00",
        )

        data = instance.to_dict()

        assert data["pack_name"] == "My Pack"
        assert data["template_id"] == "template-001"


class TestTemplateLibrary:
    """测试 TemplateLibrary 类"""

    @pytest.fixture
    def library(self):
        """创建模板库实例"""
        return TemplateLibrary()

    def test_predefined_templates_loaded(self, library):
        """测试预定义模板已加载"""
        # 生产力模板
        assert library.get_template("email-helper") is not None
        assert library.get_template("task-manager") is not None
        assert library.get_template("meeting-notes") is not None

        # 创意模板
        assert library.get_template("creative-writing") is not None
        assert library.get_template("brainstorming") is not None

        # 研究模板
        assert library.get_template("literature-summary") is not None
        assert library.get_template("data-analysis") is not None

    def test_list_all_templates(self, library):
        """测试列出所有模板"""
        templates = library.list_templates()

        assert len(templates) >= 7  # 至少 7 个预定义模板

    def test_list_templates_by_category(self, library):
        """测试按类别列出模板"""
        productivity_templates = library.list_templates(TemplateCategory.PRODUCTIVITY)
        creative_templates = library.list_templates(TemplateCategory.CREATIVE)
        research_templates = library.list_templates(TemplateCategory.RESEARCH)

        assert len(productivity_templates) >= 3
        assert len(creative_templates) >= 2
        assert len(research_templates) >= 2

    def test_get_template(self, library):
        """测试获取模板"""
        template = library.get_template("email-helper")

        assert template is not None
        assert template.template_id == "email-helper"
        assert template.category == TemplateCategory.PRODUCTIVITY

    def test_get_nonexistent_template(self, library):
        """测试获取不存在的模板"""
        template = library.get_template("nonexistent")

        assert template is None

    def test_search_templates(self, library):
        """测试搜索模板"""
        # 搜索 "邮件"
        results = library.search_templates("邮件")

        # 应该找到邮件助手
        template_ids = [t.template_id for t in results]
        assert "email-helper" in template_ids

    def test_search_templates_by_tag(self, library):
        """测试按标签搜索"""
        results = library.search_templates("writing")

        # 应该找到创意写作模板
        template_ids = [t.template_id for t in results]
        assert "creative-writing" in template_ids

    def test_create_instance(self, library):
        """测试创建实例"""
        instance = library.create_instance("email-helper", "My Email Pack", {"tone": "casual"})

        assert instance is not None
        assert instance.template_id == "email-helper"
        assert instance.pack_name == "My Email Pack"
        assert "tone" in instance.parameters

    def test_create_instance_not_found(self, library):
        """测试创建不存在的模板实例"""
        instance = library.create_instance("nonexistent", "Test Pack")

        assert instance is None

    def test_get_categories(self, library):
        """测试获取类别"""
        categories = library.get_categories()

        assert len(categories) >= 3
        assert TemplateCategory.PRODUCTIVITY in categories
        assert TemplateCategory.CREATIVE in categories
        assert TemplateCategory.RESEARCH in categories

    def test_add_custom_template(self, library):
        """测试添加自定义模板"""
        custom_template = PackTemplate(
            template_id="custom-001",
            name="Custom Template",
            description="A custom template",
            category=TemplateCategory.PRODUCTIVITY,
            tags=["custom"],
        )

        success = library.add_template(custom_template)

        assert success is True

        # 验证已添加
        retrieved = library.get_template("custom-001")
        assert retrieved is not None
        assert retrieved.name == "Custom Template"

    def test_add_duplicate_template(self, library):
        """测试添加重复模板"""
        custom_template = PackTemplate(
            template_id="duplicate",
            name="Duplicate",
            description="Duplicate template",
            category=TemplateCategory.PRODUCTIVITY,
        )

        success1 = library.add_template(custom_template)
        success2 = library.add_template(custom_template)

        assert success1 is True
        assert success2 is False

    def test_remove_custom_template(self, library):
        """测试移除自定义模板"""
        # 先添加自定义模板
        custom_template = PackTemplate(
            template_id="remove-test",
            name="Remove Test",
            description="To be removed",
            category=TemplateCategory.PRODUCTIVITY,
        )
        library.add_template(custom_template)

        success = library.remove_template("remove-test")

        assert success is True

        # 验证已移除
        assert library.get_template("remove-test") is None

    def test_remove_predefined_template(self, library):
        """测试移除预定义模板（应该失败）"""
        success = library.remove_template("email-helper")

        assert success is False  # 不允许删除预定义模板

        # 预定义模板仍然存在
        assert library.get_template("email-helper") is not None


class TestTemplateLibraryIntegration:
    """测试模板库集成场景"""

    @pytest.fixture
    def library(self):
        """创建模板库实例"""
        return TemplateLibrary()

    def test_complete_template_workflow(self, library):
        """测试完整模板工作流"""
        # 1. 列出可用模板
        templates = library.list_templates()
        assert len(templates) >= 1

        # 2. 选择一个模板
        template = templates[0]
        template_id = template.template_id

        # 3. 查看模板详情
        details = library.get_template(template_id)
        assert details is not None

        # 4. 基于模板创建实例
        instance = library.create_instance(template_id, "Test Pack")
        assert instance is not None

    def test_category_based_selection(self, library):
        """测试基于类别的选择"""
        # 获取生产力模板
        productivity = library.list_templates(TemplateCategory.PRODUCTIVITY)

        # 验证都是生产力类别
        for template in productivity:
            assert template.category == TemplateCategory.PRODUCTIVITY

    def test_parameter_merging(self, library):
        """测试参数合并"""
        # 自定义参数
        custom_params = {"custom_param": "custom_value", "tone": "formal"}  # 覆盖默认值

        instance = library.create_instance("email-helper", "Test Pack", custom_params)

        # 检查参数
        assert "custom_param" in instance.parameters
        assert instance.parameters["tone"] == "formal"

    def test_template_has_workflow(self, library):
        """测试模板包含工作流数据"""
        template = library.get_template("email-helper")

        assert template is not None
        assert "workflow_data" in template.__dict__
        assert "steps" in template.workflow_data
        assert len(template.workflow_data["steps"]) > 0

    def test_search_across_categories(self, library):
        """测试跨类别搜索"""
        # 搜索 "邮件" — 应该找到邮件助手
        results = library.search_templates("邮件")

        # 至少邮件助手应该匹配
        template_ids = [t.template_id for t in results]
        assert "email-helper" in template_ids

    def test_template_metadata_completeness(self, library):
        """测试模板元数据完整性"""
        templates = library.list_templates()

        for template in templates:
            # 验证必需字段
            assert template.template_id
            assert template.name
            assert template.description
            assert template.category

            # 验证数据结构
            assert isinstance(template.tags, list)
            assert isinstance(template.schema, dict)
            assert isinstance(template.workflow_data, dict)
            assert isinstance(template.parameters, dict)

    def test_template_workflow_steps_structure(self, library):
        """测试模板工作流步骤结构"""
        template = library.get_template("email-helper")

        steps = template.workflow_data.get("steps", [])

        for step in steps:
            # 每个步骤至少应该有 action 字段
            assert "action" in step


class TestTemplateEdgeCases:
    """测试模板边缘情况"""

    @pytest.fixture
    def library(self):
        """创建模板库实例"""
        return TemplateLibrary()

    def test_empty_search(self, library):
        """测试空搜索"""
        results = library.search_templates("xyz_nonexistent_123")

        assert len(results) == 0

    def test_instance_merging_none_parameters(self, library):
        """测试合并 None 参数"""
        instance = library.create_instance("email-helper", "Test Pack", None)

        assert instance is not None
        # 应该使用模板默认参数
        assert instance.parameters == library.get_template("email-helper").parameters

    def test_list_templates_invalid_category(self, library):
        """测试使用无效类别列出模板"""
        templates = library.list_templates("invalid_category")

        # 应该返回空列表（或抛出异常，取决于实现）
        # 当前实现会返回空列表
        assert len(templates) == 0

    def test_template_with_empty_fields(self):
        """测试字段为空的模板"""
        template = PackTemplate(
            template_id="empty",
            name="Empty",
            description="Template with empty fields",
            category=TemplateCategory.PRODUCTIVITY,
            tags=[],
            schema={},
            workflow_data={},
            parameters={},
        )

        # 应该能正常创建
        assert template.template_id == "empty"

    def test_template_id_uniqueness(self, library):
        """测试模板 ID 唯一性"""
        templates = library.list_templates()

        template_ids = [t.template_id for t in templates]

        # 检查没有重复 ID
        assert len(template_ids) == len(set(template_ids))

    def test_category_independence(self, library):
        """测试类别独立性"""
        # 从不同类别获取模板
        productivity = library.list_templates(TemplateCategory.PRODUCTIVITY)
        creative = library.list_templates(TemplateCategory.CREATIVE)
        research = library.list_templates(TemplateCategory.RESEARCH)

        # 每个类别的模板应该明确属于该类别
        for template in productivity:
            assert template.category == TemplateCategory.PRODUCTIVITY

        for template in creative:
            assert template.category == TemplateCategory.CREATIVE

        for template in research:
            assert template.category == TemplateCategory.RESEARCH
