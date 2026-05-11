"""
Unit tests for Prompt Pack Schema

Tests for:
- PackManifest
- PromptPack
- RuleFile
- PackCategoryType
- AITool
"""

from datetime import datetime

from ai_collab.prompt_pack.schema import (
    AITool,
    PackCategoryType,
    PackManifest,
    PromptPack,
    RuleFile,
)


class TestPackManifest:
    """Test PackManifest functionality"""

    def test_create_basic_manifest(self):
        """Test creating a basic manifest"""
        manifest = PackManifest(
            name="test-pack",
            version="1.0.0",
            category=PackCategoryType.DOMAIN,
            description="Test description",
            author="Test Author",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert manifest.name == "test-pack"
        assert manifest.version == "1.0.0"
        assert manifest.category == PackCategoryType.DOMAIN

    def test_manifest_to_dict(self):
        """Test manifest serialization"""
        dt = datetime.now()
        manifest = PackManifest(
            name="test-pack",
            version="1.0.0",
            category=PackCategoryType.DOMAIN,
            description="Test description",
            author="Test Author",
            created_at=dt,
            updated_at=dt,
            dependencies=["dep1"],
        )

        data = manifest.to_dict()

        assert data["name"] == "test-pack"
        assert data["version"] == "1.0.0"
        assert data["category"] == "domain"
        assert "dependencies" in data
        assert data["dependencies"] == ["dep1"]

    def test_manifest_from_dict(self):
        """Test manifest deserialization"""
        dt = datetime.now()
        data = {
            "name": "test-pack",
            "version": "1.0.0",
            "category": "domain",
            "description": "Test description",
            "author": "Test Author",
            "created_at": dt.isoformat(),
            "updated_at": dt.isoformat(),
        }

        manifest = PackManifest.from_dict(data)

        assert manifest.name == "test-pack"
        assert manifest.version == "1.0.0"
        assert manifest.category == PackCategoryType.DOMAIN


class TestPromptPack:
    """Test PromptPack functionality"""

    def test_create_empty_pack(self):
        """Test creating an empty pack"""
        manifest = PackManifest(
            name="test-pack",
            version="1.0.0",
            category=PackCategoryType.DOMAIN,
            description="Test description",
            author="Test Author",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        pack = PromptPack(manifest=manifest)

        assert len(pack.rules) == 0
        assert pack.validate() is True

    def test_pack_add_rule(self):
        """Test adding a rule to pack"""
        manifest = PackManifest(
            name="test-pack",
            version="1.0.0",
            category=PackCategoryType.DOMAIN,
            description="Test description",
            author="Test Author",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            compatible_tools=[AITool.UNIVERSAL, AITool.CLAUDE_CODE],
        )

        pack = PromptPack(manifest=manifest)
        pack.add_rule(
            filename="core.md",
            content="# Core Rules\n\nThis is a test rule.",
            priority=100,
            enabled=True,
        )

        assert len(pack.rules) == 1
        assert "core.md" in pack.rules
        assert pack.rules["core.md"].content == "# Core Rules\n\nThis is a test rule."

    def test_pack_get_rules_content(self):
        """Test getting rules content"""
        manifest = PackManifest(
            name="test-pack",
            version="1.0.0",
            category=PackCategoryType.DOMAIN,
            description="Test description",
            author="Test Author",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            compatible_tools=[AITool.CLAUDE_CODE],
        )

        pack = PromptPack(manifest=manifest)
        pack.add_rule("core.md", "# Core Rules", priority=100)
        pack.add_rule("conventions.md", "# Conventions", priority=50)

        # Test with compatible tool
        content = pack.get_rules_content(AITool.CLAUDE_CODE)
        assert len(content) == 2
        assert "# Conventions" in content[0]  # Lower priority first
        assert "# Core Rules" in content[1]

        # Test with incompatible tool
        content_incompatible = pack.get_rules_content(AITool.GITHUB_COPILOT)
        assert len(content_incompatible) == 0

    def test_pack_to_context(self):
        """Test converting pack to context string"""
        manifest = PackManifest(
            name="test-pack",
            version="1.0.0",
            category=PackCategoryType.DOMAIN,
            description="Test description",
            author="Test Author",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            compatible_tools=[AITool.UNIVERSAL, AITool.CLAUDE_CODE],
        )

        pack = PromptPack(manifest=manifest)
        pack.add_rule("core.md", "# Core Rules\n\nTest rule content.", priority=100)

        context = pack.to_context(AITool.CLAUDE_CODE)

        assert "test-pack" in context
        assert "v1.0.0" in context
        assert "# Core Rules" in context
        assert "Test rule content" in context

    def test_pack_validation(self):
        """Test pack validation"""
        # Valid pack
        valid_manifest = PackManifest(
            name="valid-pack",
            version="1.0.0",
            category=PackCategoryType.DOMAIN,
            description="Test description",
            author="Test Author",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        valid_pack = PromptPack(manifest=valid_manifest)
        assert valid_pack.validate() is True

        # Invalid pack (no name)
        invalid_manifest = PackManifest(
            name="",
            version="1.0.0",
            category=PackCategoryType.DOMAIN,
            description="Test description",
            author="Test Author",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        invalid_pack = PromptPack(manifest=invalid_manifest)
        assert invalid_pack.validate() is False


class TestRuleFile:
    """Test RuleFile functionality"""

    def test_rule_file_creation(self):
        """Test creating a rule file"""
        rule = RuleFile(filename="test.md", content="# Test Content", priority=50, enabled=True)

        assert rule.filename == "test.md"
        assert rule.content == "# Test Content"
        assert rule.priority == 50
        assert rule.enabled is True


class TestEnums:
    """Test enum types"""

    def test_pack_category_type(self):
        """Test PackCategoryType enum"""
        assert PackCategoryType.DOMAIN.value == "domain"
        assert PackCategoryType.PROJECT.value == "project"
        assert PackCategoryType.STAGE.value == "stage"
        assert PackCategoryType.ROLE.value == "role"

    def test_ai_tool(self):
        """Test AITool enum"""
        assert AITool.CLAUDE_CODE.value == "claude_code"
        assert AITool.GITHUB_COPILOT.value == "github_copilot"
        assert AITool.CODEARTS_AGENT.value == "codearts_agent"
        assert AITool.CODEX_AGENT.value == "codex_agent"
        assert AITool.UNIVERSAL.value == "universal"
