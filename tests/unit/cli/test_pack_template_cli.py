"""
Pack Template CLI Tests
"""

from unittest.mock import MagicMock, patch


class TestPackTemplateCLI:
    """Pack Template CLI Tests"""

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    @patch("ai_collab.cli.pack_template.PackMarketAPI")
    def test_init(self, mock_api_class, mock_library_class):
        """测试 CLI 初始化"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_path_instance = MagicMock()

        with patch("ai_collab.cli.pack_template.Path") as mock_path_class:
            mock_path_class.return_value = mock_path_instance

            mock_api = MagicMock()
            mock_api_class.return_value = mock_api

            mock_library = MagicMock()
            mock_library_class.return_value = mock_library

            cli = PackTemplateCLI()

            assert cli.library == mock_library
            assert cli.api == mock_api
            mock_path_instance.mkdir.assert_called_once_with(exist_ok=True)

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_list_templates_all(self, mock_library_class):
        """测试列出所有模板"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.list_templates.return_value = []

        cli = PackTemplateCLI()
        result = cli.list_templates()

        assert result == 0
        mock_library.list_templates.assert_called_once_with(None)

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_list_templates_with_category(self, mock_library_class):
        """测试按类别列出模板"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.list_templates.return_value = []

        cli = PackTemplateCLI()
        result = cli.list_templates(category="productivity")

        assert result == 0

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_list_templates_invalid_category(self, mock_library_class):
        """测试列出模板（无效类别）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library

        cli = PackTemplateCLI()
        result = cli.list_templates(category="invalid")

        assert result == 1
        mock_library.list_templates.assert_not_called()

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_show_template_success(self, mock_library_class):
        """测试显示模板详情（成功）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_template = MagicMock()
        mock_template.template_id = "test_template"
        mock_template.category.value = "productivity"
        mock_template.name = "Test Template"
        mock_template.description = "Test description"
        mock_template.tags = ["test"]
        mock_template.parameters = {}  # 无参数
        mock_template.workflow_data = {"steps": []}  # 无步骤

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_template.return_value = mock_template

        cli = PackTemplateCLI()
        result = cli.show_template("test_template")

        assert result == 0
        mock_library.get_template.assert_called_once_with("test_template")

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_show_template_not_found(self, mock_library_class):
        """测试显示模板详情（不存在）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_template.return_value = None

        cli = PackTemplateCLI()
        result = cli.show_template("nonexistent")

        assert result == 1

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    @patch("ai_collab.cli.pack_template.PackMarketAPI")
    def test_create_pack_success(self, mock_api_class, mock_library_class):
        """测试基于模板创建 Pack（成功）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_template = MagicMock()
        mock_template.category.value = "productivity"
        mock_template.template_id = "test_template"

        mock_instance = MagicMock()
        mock_instance.instance_id = "instance_123"
        mock_instance.parameters = {}

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_template.return_value = mock_template
        mock_library.create_instance.return_value = mock_instance

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.create_pack.return_value = {"success": True, "pack_id": "pack_123"}

        cli = PackTemplateCLI()
        result = cli.create_pack("test_template", "Test Pack")

        assert result == 0
        mock_library.create_instance.assert_called_once()

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_create_pack_template_not_found(self, mock_library_class):
        """测试基于模板创建 Pack（模板不存在）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.create_instance.return_value = None

        cli = PackTemplateCLI()
        result = cli.create_pack("nonexistent", "Test Pack")

        assert result == 1

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_search_templates_with_results(self, mock_library_class):
        """测试搜索模板（有结果）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_template = MagicMock()
        mock_template.template_id = "test_template"
        mock_template.name = "Test Template"
        mock_template.category.value = "productivity"

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.search_templates.return_value = [mock_template]

        cli = PackTemplateCLI()
        result = cli.search_templates("test")

        assert result == 0
        mock_library.search_templates.assert_called_once_with("test")

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_search_templates_no_results(self, mock_library_class):
        """测试搜索模板（无结果）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.search_templates.return_value = []

        cli = PackTemplateCLI()
        result = cli.search_templates("nonexistent")

        assert result == 0

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_categories(self, mock_library_class):
        """测试显示模板类别"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_categories.return_value = []
        mock_library.list_templates.return_value = []

        cli = PackTemplateCLI()
        result = cli.show_categories()

        assert result == 0
        mock_library.get_categories.assert_called_once()


class TestPackTemplateCLIErrorHandling:
    """Pack Template CLI 错误处理测试"""

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_list_templates_empty(self, mock_library_class):
        """测试列出模板（空列表）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.list_templates.return_value = []

        cli = PackTemplateCLI()
        result = cli.list_templates()

        assert result == 0

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_list_templates_multiple(self, mock_library_class):
        """测试列出模板（多个模板）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_template1 = MagicMock()
        mock_template1.template_id = "template_1"
        mock_template1.category.value = "productivity"
        mock_template1.name = "Template 1"
        mock_template1.description = "First"
        mock_template1.tags = []

        mock_template2 = MagicMock()
        mock_template2.template_id = "template_2"
        mock_template2.category.value = "productivity"
        mock_template2.name = "Template 2"
        mock_template2.description = "Second"
        mock_template2.tags = ["test"]

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.list_templates.return_value = [mock_template1, mock_template2]

        cli = PackTemplateCLI()
        result = cli.list_templates()

        assert result == 0
        assert mock_library.list_templates.called

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_show_template_with_params(self, mock_library_class):
        """测试显示模板（有参数）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_template = MagicMock()
        mock_template.template_id = "test_template"
        mock_template.name = "Test"
        mock_template.description = "Test"
        mock_template.tags = []
        mock_template.parameters = {
            "param1": {"default": "default1", "options": ["opt1", "opt2"]},
            "param2": {"default": "default2"},
        }
        mock_template.workflow_data = {"steps": []}

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_template.return_value = mock_template

        cli = PackTemplateCLI()
        result = cli.show_template("test_template")

        assert result == 0

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    @patch("ai_collab.cli.pack_template.PackMarketAPI")
    def test_create_pack_with_parameters(self, mock_api_class, mock_library_class):
        """测试基于模板创建 Pack（带参数）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_template = MagicMock()
        mock_template.category.value = "productivity"

        mock_instance = MagicMock()
        mock_instance.instance_id = "instance_123"
        mock_instance.parameters = {"param1": "value1"}

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_template.return_value = mock_template
        mock_library.create_instance.return_value = mock_instance

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.create_pack.return_value = {"success": True, "pack_id": "pack_123"}

        cli = PackTemplateCLI()
        result = cli.create_pack("test_template", "Test Pack", parameters={"param1": "value1"})

        assert result == 0
        mock_library.create_instance.assert_called_once_with(
            "test_template", "Test Pack", {"param1": "value1"}
        )

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    @patch("ai_collab.cli.pack_template.PackMarketAPI")
    def test_create_pack_api_failure(self, mock_api_class, mock_library_class):
        """测试基于模板创建 Pack（API 失败）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_template = MagicMock()
        mock_template.category.value = "productivity"

        mock_instance = MagicMock()
        mock_instance.instance_id = "instance_123"
        mock_instance.parameters = {}

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_template.return_value = mock_template
        mock_library.create_instance.return_value = mock_instance

        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        mock_api.create_pack.return_value = {"success": False, "error": "API error"}

        cli = PackTemplateCLI()
        result = cli.create_pack("test_template", "Test Pack")

        assert result == 1

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_categories_multiple(self, mock_library_class):
        """测试显示模板类别（多个类别）"""
        from ai_collab.cli.pack_template import PackTemplateCLI
        from ai_collab.pack.template import TemplateCategory

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_categories.return_value = [TemplateCategory.PRODUCTIVITY]
        mock_library.list_templates.return_value = []

        cli = PackTemplateCLI()
        result = cli.show_categories()

        assert result == 0
        mock_library.get_categories.assert_called_once()


class TestPackTemplateCLIMain:
    """测试 CLI main() 入口点"""

    @patch("ai_collab.cli.pack_template.PackTemplateCLI")
    def test_main_no_arguments(self, mock_cli_class):
        """测试无参数调用"""
        from ai_collab.cli.pack_template import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_template.py"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_template.PackTemplateCLI")
    def test_main_unknown_command(self, mock_cli_class):
        """测试未知命令"""
        from ai_collab.cli.pack_template import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_template.py", "unknown_cmd"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_template.PackTemplateCLI")
    def test_main_list_command(self, mock_cli_class):
        """测试 list 命令"""
        from ai_collab.cli.pack_template import main

        mock_cli = MagicMock()
        mock_cli.list_templates.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_template.py", "list"]):
            result = main()

        assert result == 0
        mock_cli.list_templates.assert_called_once_with(None)

    @patch("ai_collab.cli.pack_template.PackTemplateCLI")
    def test_main_list_with_category(self, mock_cli_class):
        """测试 list 命令带类别"""
        from ai_collab.cli.pack_template import main

        mock_cli = MagicMock()
        mock_cli.list_templates.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_template.py", "list", "productivity"]):
            result = main()

        assert result == 0
        mock_cli.list_templates.assert_called_once_with("productivity")

    @patch("ai_collab.cli.pack_template.PackTemplateCLI")
    def test_main_show_command(self, mock_cli_class):
        """测试 show 命令"""
        from ai_collab.cli.pack_template import main

        mock_cli = MagicMock()
        mock_cli.show_template.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_template.py", "show", "template_123"]):
            result = main()

        assert result == 0
        mock_cli.show_template.assert_called_once_with("template_123")

    @patch("ai_collab.cli.pack_template.PackTemplateCLI")
    def test_main_show_missing_arg(self, mock_cli_class):
        """测试 show 命令缺少参数"""
        from ai_collab.cli.pack_template import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_template.py", "show"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_template.PackTemplateCLI")
    def test_main_create_command(self, mock_cli_class):
        """测试 create 命令"""
        from ai_collab.cli.pack_template import main

        mock_cli = MagicMock()
        mock_cli.create_pack.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_template.py", "create", "template_123", "MyPack"]):
            result = main()

        assert result == 0
        mock_cli.create_pack.assert_called_once_with("template_123", "MyPack", {})

    @patch("ai_collab.cli.pack_template.PackTemplateCLI")
    def test_main_create_with_parameters(self, mock_cli_class):
        """测试 create 命令带参数"""
        from ai_collab.cli.pack_template import main

        mock_cli = MagicMock()
        mock_cli.create_pack.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch(
            "sys.argv",
            [
                "pack_template.py",
                "create",
                "template_123",
                "MyPack",
                "--param1",
                "value1",
                "--param2",
                "value2",
            ],
        ):
            result = main()

        assert result == 0
        mock_cli.create_pack.assert_called_once_with(
            "template_123", "MyPack", {"--param1": "value1", "--param2": "value2"}
        )

    @patch("ai_collab.cli.pack_template.PackTemplateCLI")
    def test_main_create_missing_args(self, mock_cli_class):
        """测试 create 命令缺少参数"""
        from ai_collab.cli.pack_template import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_template.py", "create", "template_123"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_template.PackTemplateCLI")
    def test_main_search_command(self, mock_cli_class):
        """测试 search 命令"""
        from ai_collab.cli.pack_template import main

        mock_cli = MagicMock()
        mock_cli.search_templates.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_template.py", "search", "productivity"]):
            result = main()

        assert result == 0
        mock_cli.search_templates.assert_called_once_with("productivity")

    @patch("ai_collab.cli.pack_template.PackTemplateCLI")
    def test_main_search_missing_arg(self, mock_cli_class):
        """测试 search 命令缺少参数"""
        from ai_collab.cli.pack_template import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["pack_template.py", "search"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.pack_template.PackTemplateCLI")
    def test_main_categories_command(self, mock_cli_class):
        """测试 categories 命令"""
        from ai_collab.cli.pack_template import main

        mock_cli = MagicMock()
        mock_cli.show_categories.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["pack_template.py", "categories"]):
            result = main()

        assert result == 0
        mock_cli.show_categories.assert_called_once()


class TestPackTemplateCLIWorkflowSteps:
    """测试工作流步骤输出路径"""

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_show_template_with_workflow_steps(self, mock_library_class):
        """测试显示模板（带工作流步骤）- 覆盖 line 135"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_template = MagicMock()
        mock_template.template_id = "test_template"
        mock_template.name = "Test"
        mock_template.description = "Test template"
        mock_template.tags = ["test"]
        mock_template.parameters = {}
        mock_template.workflow_data = {
            "steps": [
                {"action": "input", "field": "name"},
                {"action": "validate", "field": "email"},
                {"action": "output", "field": "result"},
            ]
        }

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_template.return_value = mock_template

        cli = PackTemplateCLI()
        result = cli.show_template("test_template")

        # This triggers the workflow steps printing on line 135
        assert result == 0

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_show_template_with_empty_workflow(self, mock_library_class):
        """测试显示模板（空工作流）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_template = MagicMock()
        mock_template.template_id = "test_template"
        mock_template.name = "Test"
        mock_template.description = "Test"
        mock_template.tags = []
        mock_template.parameters = {}
        mock_template.workflow_data = {"steps": []}

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_template.return_value = mock_template

        cli = PackTemplateCLI()
        result = cli.show_template("test_template")

        assert result == 0

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_show_template_with_no_workflow_data(self, mock_library_class):
        """测试显示模板（无工作流数据）"""
        from ai_collab.cli.pack_template import PackTemplateCLI

        mock_template = MagicMock()
        mock_template.template_id = "test_template"
        mock_template.name = "Test"
        mock_template.description = "Test"
        mock_template.tags = []
        mock_template.parameters = {}
        mock_template.workflow_data = {}  # Empty dict

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_template.return_value = mock_template

        cli = PackTemplateCLI()
        result = cli.show_template("test_template")

        assert result == 0


class TestPackTemplateCLICategoriesExamples:
    """测试类别示例输出 - 覆盖 lines 239-241"""

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_categories_with_examples(self, mock_library_class):
        """测试显示类别（带示例）- 覆盖 lines 239-241"""
        from ai_collab.cli.pack_template import PackTemplateCLI
        from ai_collab.pack.template import TemplateCategory

        mock_template1 = MagicMock()
        mock_template1.template_id = "workflow_automation"

        mock_template2 = MagicMock()
        mock_template2.template_id = "data_inclusion"

        mock_template3 = MagicMock()
        mock_template3.template_id = "productivity_booster"

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_categories.return_value = [
            TemplateCategory.PRODUCTIVITY,
            TemplateCategory.CREATIVE,
        ]

        # Return 3 templates for productivity to trigger the [:3] slice
        mock_library.list_templates.side_effect = [
            [mock_template1, mock_template2, mock_template3],  # productivity
            [],  # creative
        ]

        cli = PackTemplateCLI()
        result = cli.show_categories()

        assert result == 0
        # Should have called list_templates for each category
        assert mock_library.list_templates.call_count >= 1

    @patch("ai_collab.cli.pack_template.TemplateLibrary")
    def test_categories_single_template(self, mock_library_class):
        """测试显示类别（单个模板）"""
        from ai_collab.cli.pack_template import PackTemplateCLI
        from ai_collab.pack.template import TemplateCategory

        mock_template = MagicMock()
        mock_template.template_id = "single_template"

        mock_library = MagicMock()
        mock_library_class.return_value = mock_library
        mock_library.get_categories.return_value = [TemplateCategory.PRODUCTIVITY]
        mock_library.list_templates.return_value = [mock_template]

        cli = PackTemplateCLI()
        result = cli.show_categories()

        assert result == 0
