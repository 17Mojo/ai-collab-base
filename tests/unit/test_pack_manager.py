"""
Unit tests for Pack Manager

Tests for:
- PackManager
- Pack loading
- Dependency resolution
- Context injection
- Smart recommendation
"""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ai_collab.prompt_pack.manager import PackManager
from ai_collab.prompt_pack.schema import AITool, PackCategoryType, PackDependencyError


@pytest.fixture
def temp_packs_dir():
    """Create a temporary directory for test packs"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_pack(temp_packs_dir):
    """Create a sample pack for testing"""
    pack_dir = temp_packs_dir / "sample-pack"
    pack_dir.mkdir()

    manifest = {
        "name": "sample-pack",
        "version": "1.0.0",
        "category": "domain",
        "description": "Sample pack for testing",
        "author": "Test Author",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "dependencies": [],
        "compatible_tools": ["claude_code", "github_copilot", "universal"],
        "tags": ["test", "sample"],
        "metadata": {},
    }

    with open(pack_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)

    with open(pack_dir / "core.md", "w") as f:
        f.write("# Core Rules\n\nThis is core rule content.")

    with open(pack_dir / "conventions.md", "w") as f:
        f.write("# Conventions\n\nThis is conventions content.")

    return pack_dir


@pytest.fixture
def pack_with_dependency(temp_packs_dir):
    """Create a pack with dependencies"""
    # Create dependency pack
    dep_pack_dir = temp_packs_dir / "dependency-pack"
    dep_pack_dir.mkdir()

    dep_manifest = {
        "name": "dependency-pack",
        "version": "1.0.0",
        "category": "domain",
        "description": "Dependency pack",
        "author": "Test Author",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "dependencies": [],
        "compatible_tools": ["universal"],
        "tags": ["dependency"],
        "metadata": {},
    }

    with open(dep_pack_dir / "manifest.json", "w") as f:
        json.dump(dep_manifest, f)

    with open(dep_pack_dir / "dep.md", "w") as f:
        f.write("# Dependency Rules\n\nThis is dependency content.")

    # Create main pack with dependency
    main_pack_dir = temp_packs_dir / "main-pack"
    main_pack_dir.mkdir()

    main_manifest = {
        "name": "main-pack",
        "version": "1.0.0",
        "category": "domain",
        "description": "Main pack with dependencies",
        "author": "Test Author",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "dependencies": ["dependency-pack"],
        "compatible_tools": ["universal"],
        "tags": ["main"],
        "metadata": {},
    }

    with open(main_pack_dir / "manifest.json", "w") as f:
        json.dump(main_manifest, f)

    with open(main_pack_dir / "main.md", "w") as f:
        f.write("# Main Rules\n\nThis is main content.")

    return main_pack_dir


class TestPackManager:
    """Test PackManager functionality"""

    def test_manager_initialization(self, temp_packs_dir):
        """Test manager initialization"""
        manager = PackManager(temp_packs_dir)
        assert manager.packs_root == temp_packs_dir
        assert len(manager._packs_cache) == 0

    def test_load_pack(self, temp_packs_dir, sample_pack):
        """Test loading a pack"""
        manager = PackManager(temp_packs_dir)
        pack = manager.load_pack("sample-pack")

        assert pack.manifest.name == "sample-pack"
        assert pack.manifest.version == "1.0.0"
        assert len(pack.rules) == 2
        assert "core.md" in pack.rules
        assert "conventions.md" in pack.rules

    def test_load_pack_caching(self, temp_packs_dir, sample_pack):
        """Test pack caching"""
        manager = PackManager(temp_packs_dir)
        pack1 = manager.load_pack("sample-pack")
        pack2 = manager.load_pack("sample-pack")

        assert pack1 is pack2  # Should be same object (cached)
        assert len(manager._packs_cache) == 1

    def test_load_nonexistent_pack(self, temp_packs_dir):
        """Test loading a non-existent pack"""
        manager = PackManager(temp_packs_dir)

        with pytest.raises(FileNotFoundError):
            manager.load_pack("nonexistent-pack")

    def test_resolve_dependencies(self, temp_packs_dir, pack_with_dependency):
        """Test dependency resolution"""
        manager = PackManager(temp_packs_dir)
        pack = manager.load_pack("main-pack")

        dependencies = manager.resolve_dependencies(pack)

        assert len(dependencies) == 1
        assert dependencies[0].manifest.name == "dependency-pack"

    def test_circular_dependency_detection(self, temp_packs_dir):
        """Test circular dependency detection"""
        # Create circular dependency
        pack_a_dir = temp_packs_dir / "pack-a"
        pack_b_dir = temp_packs_dir / "pack-b"

        for pack_dir, name, dep in [
            (pack_a_dir, "pack-a", "pack-b"),
            (pack_b_dir, "pack-b", "pack-a"),
        ]:
            pack_dir.mkdir()
            manifest = {
                "name": name,
                "version": "1.0.0",
                "category": "domain",
                "description": f"{name} description",
                "author": "Test Author",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "dependencies": [dep],
                "compatible_tools": ["universal"],
                "tags": [],
                "metadata": {},
            }
            with open(pack_dir / "manifest.json", "w") as f:
                json.dump(manifest, f)

        manager = PackManager(temp_packs_dir)
        pack_a = manager.load_pack("pack-a")

        with pytest.raises(PackDependencyError) as exc_info:
            manager.resolve_dependencies(pack_a)

        assert "Circular dependency" in str(exc_info.value)

    def test_get_packed_context(self, temp_packs_dir, pack_with_dependency):
        """Test getting packed context with dependencies"""
        manager = PackManager(temp_packs_dir)
        context = manager.get_packed_context(
            "main-pack", AITool.CLAUDE_CODE, include_dependencies=True
        )

        assert "main-pack" in context
        assert "# Main Rules" in context
        assert "dependency-pack" in context
        assert "# Dependency Rules" in context

    def test_list_available_packs(self, temp_packs_dir, sample_pack):
        """Test listing available packs"""
        manager = PackManager(temp_packs_dir)
        packs = manager.list_available_packs()

        assert len(packs) == 1
        assert "sample-pack" in packs

    def test_list_available_packs_filter(self, temp_packs_dir, sample_pack):
        """Test listing packs with category filter"""
        manager = PackManager(temp_packs_dir)
        domain_packs = manager.list_available_packs(PackCategoryType.DOMAIN)
        role_packs = manager.list_available_packs(PackCategoryType.ROLE)

        assert len(domain_packs) == 1
        assert len(role_packs) == 0

    def test_get_best_pack(self, temp_packs_dir, sample_pack):
        """Test smart pack recommendation"""
        manager = PackManager(temp_packs_dir)

        # Test name matching
        recommended = manager.get_best_pack("Use sample-pack for this task", AITool.CLAUDE_CODE)
        assert recommended is not None
        assert recommended.manifest.name == "sample-pack"

        # Test description matching
        recommended = manager.get_best_pack("I need Sample pack for testing", AITool.CLAUDE_CODE)
        assert recommended is not None
        assert recommended.manifest.name == "sample-pack"

        # Test tag matching
        recommended = manager.get_best_pack("I need something for test", AITool.CLAUDE_CODE)
        # Should match the "test" tag
        assert recommended is not None

        # Test no match
        recommended = manager.get_best_pack("completely unrelated request", AITool.CLAUDE_CODE)
        assert recommended is None

    def test_inject_into_ai_context(self, temp_packs_dir, sample_pack):
        """Test injecting pack context into existing context"""
        manager = PackManager(temp_packs_dir)

        current_context = "This is the existing context."
        new_context = manager.inject_into_ai_context(
            "sample-pack", current_context, AITool.CLAUDE_CODE
        )

        assert "This is the existing context." in new_context
        assert "sample-pack" in new_context
        assert "# Core Rules" in new_context

    def test_clear_cache(self, temp_packs_dir, sample_pack):
        """Test clearing pack cache"""
        manager = PackManager(temp_packs_dir)
        manager.load_pack("sample-pack")
        assert len(manager._packs_cache) == 1

        manager.clear_cache()
        assert len(manager._packs_cache) == 0
