"""
Unit tests for Prompt Pack Token Budget Management

Tests for:
- Token budget calculation and enforcement
- Pack token cost estimation
- Budget-aware pack selection
- Token optimization strategies
"""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ai_collab.prompt_pack.manager import PackManager
from ai_collab.prompt_pack.schema import AITool


@pytest.fixture
def temp_packs_dir():
    """Create a temporary directory for test packs"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def base_pack(temp_packs_dir):
    """Create a base pack for testing"""
    pack_dir = temp_packs_dir / "base-pack"
    pack_dir.mkdir()

    manifest = {
        "name": "base-pack",
        "version": "1.0.0",
        "category": "domain",
        "description": "Base pack for token budget testing",
        "author": "Test Author",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "dependencies": [],
        "compatible_tools": ["claude_code", "universal"],
        "tags": ["test", "base"],
        "metadata": {},
    }

    # Create files with known token content
    with open(pack_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)

    with open(pack_dir / "core.md", "w") as f:
        f.write("# Core Rules\n\nThis is core rule content with about 50 tokens.")

    with open(pack_dir / "conventions.md", "w") as f:
        f.write("# Conventions\n\nThis is conventions content with about 60 tokens.")

    return pack_dir


@pytest.fixture
def expensive_pack(temp_packs_dir):
    """Create a pack with high token cost"""
    pack_dir = temp_packs_dir / "expensive-pack"
    pack_dir.mkdir()

    manifest = {
        "name": "expensive-pack",
        "version": "1.0.0",
        "category": "role",
        "description": "Expensive pack with lots of content",
        "author": "Test Author",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "dependencies": [],
        "compatible_tools": ["claude_code", "universal"],
        "tags": ["test", "expensive", "advanced"],
        "metadata": {},
    }

    with open(pack_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)

    # Create large content file
    large_content = "# Advanced Rules\n\n" + "\n\n".join(
        [f"This is advanced rule line {i} with more content." for i in range(100)]
    )
    with open(pack_dir / "advanced.md", "w") as f:
        f.write(large_content)

    return pack_dir


@pytest.fixture
def medium_pack(temp_packs_dir):
    """Create a pack with medium token cost"""
    pack_dir = temp_packs_dir / "medium-pack"
    pack_dir.mkdir()

    manifest = {
        "name": "medium-pack",
        "version": "1.0.0",
        "category": "domain",
        "description": "Medium pack with moderate content",
        "author": "Test Author",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "dependencies": [],
        "compatible_tools": ["claude_code", "universal"],
        "tags": ["test", "medium"],
        "metadata": {},
    }

    with open(pack_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)

    with open(pack_dir / "rules.md", "w") as f:
        f.write("# Medium Rules\n\n" + "\n".join([f"Medium rule {i}" for i in range(20)]))

    return pack_dir


class TestTokenBudgetCalculation:
    """Test token budget calculation and estimation"""

    def test_estimate_pack_tokens(self, temp_packs_dir, base_pack):
        """Test estimating tokens for a pack"""
        manager = PackManager(temp_packs_dir)
        pack = manager.load_pack("base-pack")

        # Estimate tokens (simple word-based approximation)
        tokens = manager.estimate_pack_tokens(pack)

        # Should estimate approximately the content size
        assert tokens > 0
        assert tokens < 500  # Base pack shouldn't be too large

    def test_estimate_expensive_pack_tokens(self, temp_packs_dir, expensive_pack):
        """Test estimating tokens for large pack"""
        manager = PackManager(temp_packs_dir)
        pack = manager.load_pack("expensive-pack")

        tokens = manager.estimate_pack_tokens(pack)

        # Expensive pack should have significantly more tokens
        assert tokens > 100
        assert tokens < 5000  # Reasonable upper bound

    def test_estimate_dependency_tokens(self, temp_packs_dir):
        """Test estimating tokens including dependencies"""
        # Create dependency chain
        dep_pack_dir = temp_packs_dir / "dependency"
        dep_pack_dir.mkdir()

        manifest = {
            "name": "dependency",
            "version": "1.0.0",
            "category": "domain",
            "description": "Dependency pack",
            "author": "Test Author",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "dependencies": [],
            "compatible_tools": ["universal"],
            "tags": [],
            "metadata": {},
        }

        with open(dep_pack_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        with open(dep_pack_dir / "dep.md", "w") as f:
            f.write("# Dependency Content\n\nAbout 40 tokens here.")

        # Create pack with dependency
        main_pack_dir = temp_packs_dir / "main"
        main_pack_dir.mkdir()

        main_manifest = {
            "name": "main",
            "version": "1.0.0",
            "category": "domain",
            "description": "Main pack with dependency",
            "author": "Test Author",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "dependencies": ["dependency"],
            "compatible_tools": ["universal"],
            "tags": [],
            "metadata": {},
        }

        with open(main_pack_dir / "manifest.json", "w") as f:
            json.dump(main_manifest, f)

        with open(main_pack_dir / "main.md", "w") as f:
            f.write("# Main Content\n\nAbout 35 tokens here.")

        manager = PackManager(temp_packs_dir)
        pack = manager.load_pack("main")

        # Estimate with dependencies
        tokens = manager.estimate_pack_tokens(pack, include_dependencies=True)

        # Should be more than just main pack
        single_pack_tokens = manager.estimate_pack_tokens(pack, include_dependencies=False)
        assert tokens > single_pack_tokens


class TestBudgetEnforcement:
    """Test budget enforcement and validation"""

    def test_validate_token_budget_under_limit(self, temp_packs_dir, base_pack, expensive_pack):
        """Test budget validation when under limit"""
        manager = PackManager(temp_packs_dir)

        # Load both packs
        base = manager.load_pack("base-pack")
        expensive = manager.load_pack("expensive-pack")

        # Test under budget
        is_valid = manager.validate_token_budget([base, expensive], budget_limit=10000)
        assert is_valid is True

    def test_validate_token_budget_over_limit(self, temp_packs_dir, expensive_pack):
        """Test budget validation when over limit"""
        manager = PackManager(temp_packs_dir)

        # Load expensive pack multiple times
        expensive = manager.load_pack("expensive-pack")

        # Test over budget
        is_valid = manager.validate_token_budget(
            [expensive, expensive, expensive], budget_limit=100
        )
        assert is_valid is False

    def test_get_remaining_budget(self, temp_packs_dir, base_pack, medium_pack):
        """Test calculating remaining budget"""
        manager = PackManager(temp_packs_dir)

        base = manager.load_pack("base-pack")
        medium = manager.load_pack("medium-pack")

        remaining = manager.get_remaining_budget([base, medium], total_budget=5000)

        # Should have positive remaining budget
        assert remaining > 0
        assert remaining < 5000


class TestBudgetAwareSelection:
    """Test budget-aware pack selection strategies"""

    def test_select_packs_within_budget(
        self, temp_packs_dir, base_pack, medium_pack, expensive_pack
    ):
        """Test selecting packs that fit within budget"""
        manager = PackManager(temp_packs_dir)

        all_packs = [
            manager.load_pack("base-pack"),
            manager.load_pack("medium-pack"),
            manager.load_pack("expensive-pack"),
        ]

        # Select packs within budget
        selected = manager.select_packs_within_budget(all_packs, budget_limit=5000)

        # Should include most packs
        assert len(selected) >= 1  # At least one pack should fit

    def test_optimize_pack_selection_for_budget(self, temp_packs_dir, base_pack, medium_pack):
        """Test optimizing pack selection for maximum coverage"""
        manager = PackManager(temp_packs_dir)

        packs = [manager.load_pack("base-pack"), manager.load_pack("medium-pack")]

        # Optimize selection
        selected = manager.optimize_pack_selection(packs, budget_limit=5000, target_tags=["test"])

        # Should select packs matching target tags
        assert len(selected) >= 1


class TestTokenEfficiency:
    """Test token efficiency and optimization"""

    def test_calculate_token_efficiency(self, temp_packs_dir, base_pack, expensive_pack):
        """Test calculating token efficiency metrics"""
        manager = PackManager(temp_packs_dir)

        base = manager.load_pack("base-pack")
        expensive = manager.load_pack("expensive-pack")

        # Base pack should be more efficient (smaller, useful content)
        base_efficiency = manager.calculate_token_efficiency(base)
        expensive_efficiency = manager.calculate_token_efficiency(expensive)

        # Both should have positive efficiency scores
        assert base_efficiency > 0
        assert expensive_efficiency > 0

    def test_compress_pack_tokens(self, temp_packs_dir, base_pack):
        """Test pack token compression"""
        manager = PackManager(temp_packs_dir)

        base = manager.load_pack("base-pack")

        original_tokens = manager.estimate_pack_tokens(base)

        # Compress the pack
        compressed_pack = manager.compress_pack_tokens(base, compression_ratio=0.5)

        # Should have fewer tokens
        compressed_tokens = manager.estimate_pack_tokens(compressed_pack)
        assert compressed_tokens < original_tokens


class TestTokenBudgetIntegration:
    """Test token budget integration with Pack Manager"""

    def test_get_packed_context_with_budget(self, temp_packs_dir, base_pack, expensive_pack):
        """Test getting packed context respecting budget"""
        manager = PackManager(temp_packs_dir)

        # Get context with budget limit
        context = manager.get_packed_context(
            "expensive-pack", AITool.CLAUDE_CODE, include_dependencies=True, token_budget=5000
        )

        # Should still work even with budget constraint
        assert len(context) > 0

    def test_inject_with_budget_validation(self, temp_packs_dir, base_pack, medium_pack):
        """Test injection with budget validation"""
        manager = PackManager(temp_packs_dir)

        current_context = "Current context content."

        # Inject with budget
        new_context, is_valid = manager.inject_with_budget_validation(
            "base-pack", current_context, AITool.CLAUDE_CODE, budget_limit=10000
        )

        assert is_valid is True
        assert len(new_context) > len(current_context)
