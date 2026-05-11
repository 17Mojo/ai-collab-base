# Pack Template CLI Module
# Week 2 Day 4: Pack 模板系统 CLI

"""
Pack 模板 CLI 命令
支持模板列表、查看、创建等操作
"""

import sys
from pathlib import Path
from typing import Optional

from ai_collab.pack.market_api import PackMarketAPI
from ai_collab.pack.template import TemplateCategory, TemplateLibrary


class PackTemplateCLI:
    """Pack 模板 CLI"""

    def __init__(self, template_dir: Optional[str] = None, db_path: str = "data/packs.db"):
        """初始化 CLI

        Args:
            template_dir: 模板目录
            db_path: 数据库路径
        """
        self.library = TemplateLibrary(template_dir)
        self.api = PackMarketAPI(db_path)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """确保必要目录存在"""
        Path("data").mkdir(exist_ok=True)

    def list_templates(self, category: Optional[str] = None) -> int:
        """列出模板

        Args:
            category: 类别过滤（可选）

        Returns:
            退出码
        """
        print(f"\n{'='*60}")
        print("Template Library")
        print(f"{'='*60}\n")

        # 解析类别
        category_enum = None
        if category:
            try:
                category_enum = TemplateCategory(category)
            except ValueError:
                print(f"✗ Invalid category: {category}")
                print(f"  Valid categories: {[c.value for c in TemplateCategory]}")
                return 1

        templates = self.library.list_templates(category_enum)

        if not templates:
            print("No templates found.")
            return 0

        # 按类别分组显示
        grouped = {}
        for template in templates:
            cat = template.category.value
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(template)

        for cat in sorted(grouped.keys()):
            print(f"\n[{cat.upper()}]")

            for template in grouped[cat]:
                print(f"  {template.template_id:25s} | {template.name}")
                print(f"  {'':25s} | {template.description[:40]}...")
                if template.tags:
                    tags_str = ", ".join(template.tags)
                    print(f"  {'':25s} | Tags: {tags_str}")

        print(f"\n{'='*60}")
        print(f"Total: {len(templates)} templates")
        print(f"{'='*60}\n")

        return 0

    def show_template(self, template_id: str) -> int:
        """显示模板详情

        Args:
            template_id: 模板 ID

        Returns:
            退出码
        """
        template = self.library.get_template(template_id)

        if template is None:
            print(f"✗ Template not found: {template_id}")
            return 1

        print(f"\n{'='*60}")
        print("Template Details")
        print(f"{'='*60}\n")

        print(f"ID: {template.template_id}")
        print(f"Name: {template.name}")
        print(f"Category: {template.category.value}")
        print("\nDescription:")
        print(f"  {template.description}")

        if template.tags:
            print("\nTags:")
            for tag in template.tags:
                print(f"  - {tag}")

        print("\nParameters:")
        if template.parameters:
            for param_name, param_config in template.parameters.items():
                default = param_config.get("default", "N/A")
                options = param_config.get("options", [])
                if options:
                    options_str = ", ".join(options)
                    print(f"  {param_name}: {default} (options: {options_str})")
                else:
                    print(f"  {param_name}: {default}")
        else:
            print("  None")

        print(f"\nWorkflow Steps: {len(template.workflow_data.get('steps', []))}")
        for i, step in enumerate(template.workflow_data.get("steps", []), 1):
            print(f"  {i}. {step.get('action', 'unknown')}: {step.get('field', 'N/A')}")

        print(f"\n{'='*60}\n")

        return 0

    def create_pack(
        self,
        template_id: str,
        pack_name: str,
        parameters: Optional[dict] = None,
        author: str = "default_user",
    ) -> int:
        """基于模板创建 Pack

        Args:
            template_id: 模板 ID
            pack_name: Pack 名称
            parameters: 参数（可选）
            author: 作者

        Returns:
            退出码
        """
        instance = self.library.create_instance(template_id, pack_name, parameters)

        if instance is None:
            print(f"✗ Template not found: {template_id}")
            return 1

        print(f"Creating pack '{pack_name}' from template '{template_id}'...")

        # 创建 Pack
        result = self.api.create_pack(
            pack_name=pack_name,
            version="1.0.0",
            description=f"Created from template: {template_id}",
            author=author,
            category=self.library.get_template(template_id).category.value,
        )

        if result["success"]:
            pack_id = result["pack_id"]
            print("✓ Pack created successfully")
            print(f"  Pack ID: {pack_id}")
            print(f"  Instance ID: {instance.instance_id}")

            if instance.parameters:
                print("\nApplied Parameters:")
                for param_name, param_value in instance.parameters.items():
                    print(f"  {param_name}: {param_value}")
        else:
            print(f"✗ Failed to create pack: {result.get('error', 'Unknown error')}")

        return 0 if result["success"] else 1

    def search_templates(self, query: str) -> int:
        """搜索模板

        Args:
            query: 搜索关键词

        Returns:
            退出码
        """
        templates = self.library.search_templates(query)

        print(f"\n{'='*60}")
        print(f"Templates matching: '{query}'")
        print(f"{'='*60}\n")

        if not templates:
            print("No matching templates found.")
            return 0

        for template in templates:
            print(f"\n{template.template_id:25s}")
            print(f"  Name: {template.name}")
            print(f"  Category: {template.category.value}")
            print(f"  Description: {template.description[:50]}...")

        print(f"\n{'='*60}")
        print(f"Total: {len(templates)} matching templates")
        print(f"{'='*60}\n")

        return 0

    def show_categories(self) -> int:
        """显示模板类别

        Returns:
            退出码
        """
        categories = self.library.get_categories()

        print(f"\n{'='*60}")
        print("Template Categories")
        print(f"{'='*60}\n")

        for category in categories:
            templates = self.library.list_templates(category)
            print(f"\n[{category.value.upper()}]")
            print(f"  Count: {len(templates)}")
            if templates:
                print("  Examples:")
                for template in templates[:3]:
                    print(f"    - {template.template_id}")

        print(f"\n{'='*60}\n")

        return 0


def main():
    """CLI 入口"""
    if len(sys.argv) < 2:
        print("Usage: pack_template.py <command> [options]")
        print("Commands:")
        print("  list [category]           - List all templates")
        print("  show <template_id>          - Show template details")
        print("  create <template_id> <name> - Create pack from template")
        print("  search <query>             - Search templates")
        print("  categories                 - List template categories")
        return 1

    command = sys.argv[1]
    cli = PackTemplateCLI()

    if command == "list":
        category = sys.argv[2] if len(sys.argv) > 2 else None
        return cli.list_templates(category)

    elif command == "show":
        if len(sys.argv) < 3:
            print("Usage: pack_template.py show <template_id>")
            return 1
        return cli.show_template(sys.argv[2])

    elif command == "create":
        if len(sys.argv) < 4:
            print("Usage: pack_template.py create <template_id> <pack_name> [--param1 value1]")
            return 1

        template_id = sys.argv[2]
        pack_name = sys.argv[3]

        # 解析参数
        parameters = {}
        i = 4
        while i + 1 < len(sys.argv):
            param_name = sys.argv[i]
            param_value = sys.argv[i + 1]
            parameters[param_name] = param_value
            i += 2

        return cli.create_pack(template_id, pack_name, parameters)

    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: pack_template.py search <query>")
            return 1
        return cli.search_templates(sys.argv[2])

    elif command == "categories":
        return cli.show_categories()

    else:
        print(f"Unknown command: {command}")
        print("Available commands: list, show, create, search, categories")
        return 1


if __name__ == "__main__":
    sys.exit(main())
