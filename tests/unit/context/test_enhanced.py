"""
Enhanced context tests.
"""

from __future__ import annotations

from ai_collab.context.enhanced import ContextEnhancer, ScenarioContextBuilder
from ai_collab.context.schema import Context, FileContext, NotebookLMContext, ScenarioType


class MockNotebookLMIntegration:
    """Mock NotebookLM integration for testing."""

    def query_knowledge(self, topic: str):
        """Mock query_knowledge method."""
        if "error" in topic.lower():
            return {"error": "Mock error"}
        return {
            "notebook_id": "test-notebook",
            "notebook_name": "Test Notebook",
            "response": f"Response for: {topic}",
            "sources": ["doc1.md", "doc2.md", "doc3.md"],
        }


class TestContextEnhancer:
    """Test ContextEnhancer class."""

    def test_enhancer_initialization_without_notebooklm(self):
        """Test enhancer initialization without NotebookLM."""
        enhancer = ContextEnhancer()
        assert enhancer._notebooklm is None

    def test_enhancer_initialization_with_notebooklm(self):
        """Test enhancer initialization with NotebookLM."""
        mock_nb = MockNotebookLMIntegration()
        enhancer = ContextEnhancer(notebooklm_integration=mock_nb)
        assert enhancer._notebooklm is not None

    def test_enrich_without_notebooklm(self):
        """Test enrich without NotebookLM integration."""
        enhancer = ContextEnhancer()
        context = Context(
            context_id="test-ctx",
            scenario=ScenarioType.CODING,
            name="Test",
        )

        result = enhancer.enrich(context, "test query")
        # Should return base context unchanged
        assert result.context_id == context.context_id
        assert result.notebooklm_context is None

    def test_enrich_with_notebooklm(self):
        """Test enrich with NotebookLM integration."""
        mock_nb = MockNotebookLMIntegration()
        enhancer = ContextEnhancer(notebooklm_integration=mock_nb)
        context = Context(
            context_id="test-ctx",
            scenario=ScenarioType.CODING,
            name="Test",
        )

        result = enhancer.enrich(context, "test query")
        # Should have NotebookLM context
        assert result.notebooklm_context is not None
        assert result.notebooklm_context.notebook_id == "test-notebook"
        assert len(result.notebooklm_context.query_results) == 1

    def test_enrich_with_error(self):
        """Test enrich when NotebookLM returns error."""
        mock_nb = MockNotebookLMIntegration()
        enhancer = ContextEnhancer(notebooklm_integration=mock_nb)
        context = Context(
            context_id="test-ctx",
            scenario=ScenarioType.CODING,
            name="Test",
        )

        result = enhancer.enrich(context, "error query")
        # Should return base context on error
        assert result.context_id == context.context_id
        assert result.notebooklm_context is None

    def test_suggest_files_without_notebooklm(self):
        """Test file suggestion without NotebookLM."""
        enhancer = ContextEnhancer()
        context = Context(
            context_id="test-ctx",
            scenario=ScenarioType.CODING,
            name="Test",
        )

        project_files = [
            "src/main.py",
            "src/utils.py",
            "docs/README.md",
            "test_main.py",
        ]

        suggested = enhancer.suggest_files(context, project_files, top_n=3)
        assert len(suggested) <= 3
        assert all(f in project_files for f in suggested)

    def test_suggest_files_for_coding_scenario(self):
        """Test file suggestion for coding scenario."""
        enhancer = ContextEnhancer()
        context = Context(
            context_id="test-ctx",
            scenario=ScenarioType.CODING,
            name="Test",
        )

        project_files = [
            "src/main.py",
            "src/utils.py",
            "docs/README.md",
            "app.js",
            "test_main.py",
        ]

        suggested = enhancer.suggest_files(context, project_files, top_n=5)
        # Should prefer coding-related files
        assert len(suggested) > 0
        # src/ files should be prioritized
        assert any("src/" in f for f in suggested)

    def test_suggest_files_for_research_scenario(self):
        """Test file suggestion for research scenario."""
        enhancer = ContextEnhancer()
        context = Context(
            context_id="test-ctx",
            scenario=ScenarioType.RESEARCH,
            name="Test",
        )

        project_files = [
            "src/main.py",
            "docs/paper.md",
            "research/notes.md",
            "README.md",
        ]

        suggested = enhancer.suggest_files(context, project_files, top_n=3)
        # Should prefer research-related files
        assert len(suggested) > 0

    def test_suggest_files_for_debugging_scenario(self):
        """Test file suggestion for debugging scenario."""
        enhancer = ContextEnhancer()
        context = Context(
            context_id="test-ctx",
            scenario=ScenarioType.DEBUGGING,
            name="Test",
        )

        project_files = [
            "src/main.py",
            "logs/error.log",
            "test_main.py",
            "debug/info.txt",
        ]

        suggested = enhancer.suggest_files(context, project_files, top_n=3)
        # Should prefer debugging-related files
        assert len(suggested) > 0

    def test_extract_context_summary(self):
        """Test context summary extraction."""
        enhancer = ContextEnhancer()
        context = Context(
            context_id="test-ctx",
            scenario=ScenarioType.CODING,
            name="Test Context",
        )
        context.add_file(FileContext(path="main.py", language="python", size=100))
        context.add_file(FileContext(path="utils.py", language="python", size=50))
        context.metadata.tags = ["python", "test"]

        summary = enhancer.extract_context_summary(context)
        assert summary["context_id"] == "test-ctx"
        assert summary["scenario"] == "coding"
        assert summary["name"] == "Test Context"
        assert summary["file_count"] == 2
        assert summary["session_count"] == 0
        assert summary["has_notebooklm"] is False
        assert len(summary["recent_files"]) == 2
        assert summary["tags"] == ["python", "test"]

    def test_extract_context_summary_with_notebooklm(self):
        """Test context summary extraction with NotebookLM."""
        enhancer = ContextEnhancer()
        context = Context(
            context_id="test-ctx",
            scenario=ScenarioType.RESEARCH,
            name="Research Context",
        )
        nb_ctx = NotebookLMContext(
            notebook_id="nb-1",
            notebook_name="Research",
            query_results=[{"query": "test", "answer": "This is a long answer about research"}],
            sources=["doc1.md", "doc2.md"],
        )
        context.update_notebooklm(nb_ctx)

        summary = enhancer.extract_context_summary(context)
        assert summary["has_notebooklm"] is True
        assert "notebooklm_sources" in summary
        assert "knowledge_summary" in summary

    def test_merge_contexts(self):
        """Test merging multiple contexts."""
        enhancer = ContextEnhancer()

        # Create first context
        ctx1 = Context(
            context_id="ctx-1",
            scenario=ScenarioType.CODING,
            name="Context 1",
        )
        ctx1.add_file(FileContext(path="main.py", language="python", size=100))
        ctx1.metadata.tags = ["python"]

        # Create second context
        ctx2 = Context(
            context_id="ctx-2",
            scenario=ScenarioType.CODING,
            name="Context 2",
        )
        ctx2.add_file(FileContext(path="utils.py", language="python", size=50))
        ctx2.add_file(FileContext(path="main.py", language="python", size=100))  # Duplicate
        ctx2.metadata.tags = ["utils"]

        merged = enhancer.merge_contexts(
            [ctx1, ctx2],
            scenario=ScenarioType.CODING,
            name="Merged Context",
        )

        assert merged.scenario == ScenarioType.CODING
        assert merged.name == "Merged Context"
        # Should deduplicate files
        assert len(merged.file_contexts) == 2
        # Should merge tags
        assert set(merged.metadata.tags) == {"python", "utils"}

    def test_merge_contexts_with_notebooklm(self):
        """Test merging contexts with NotebookLM."""
        enhancer = ContextEnhancer()

        ctx1 = Context(
            context_id="ctx-1",
            scenario=ScenarioType.RESEARCH,
            name="Context 1",
        )
        nb_ctx1 = NotebookLMContext(
            notebook_id="nb-1",
            notebook_name="Research 1",
            query_results=[{"query": "q1", "answer": "short"}],
        )
        ctx1.update_notebooklm(nb_ctx1)

        ctx2 = Context(
            context_id="ctx-2",
            scenario=ScenarioType.RESEARCH,
            name="Context 2",
        )
        nb_ctx2 = NotebookLMContext(
            notebook_id="nb-2",
            notebook_name="Research 2",
            query_results=[{"query": "q2", "answer": "much longer answer with more content"}],
        )
        ctx2.update_notebooklm(nb_ctx2)

        merged = enhancer.merge_contexts(
            [ctx1, ctx2],
            scenario=ScenarioType.RESEARCH,
            name="Merged",
        )

        # Should choose the richest NotebookLM context
        assert merged.notebooklm_context is not None
        assert merged.notebooklm_context.notebook_id == "nb-2"


class TestScenarioContextBuilder:
    """Test ScenarioContextBuilder class."""

    def test_builder_initialization_without_enhancer(self):
        """Test builder initialization without enhancer."""
        builder = ScenarioContextBuilder()
        assert builder._enhancer is None

    def test_builder_initialization_with_enhancer(self):
        """Test builder initialization with enhancer."""
        enhancer = ContextEnhancer()
        builder = ScenarioContextBuilder(enhancer=enhancer)
        assert builder._enhancer is not None

    def test_build_for_coding(self):
        """Test building coding context."""
        builder = ScenarioContextBuilder()
        context = builder.build_for_coding(
            base_files=["main.py", "utils.py"],
        )

        assert context.scenario == ScenarioType.CODING
        assert context.name == "Coding Context"
        assert len(context.file_contexts) == 2
        assert context.file_contexts[0].path == "main.py"

    def test_build_for_research(self):
        """Test building research context."""
        builder = ScenarioContextBuilder()
        context = builder.build_for_research(
            base_files=["paper.md", "notes.md"],
        )

        assert context.scenario == ScenarioType.RESEARCH
        assert context.name == "Research Context"
        assert len(context.file_contexts) == 2

    def test_build_for_writing(self):
        """Test building writing context."""
        builder = ScenarioContextBuilder()
        context = builder.build_for_writing(
            base_files=["article1.md", "article2.md"],
        )

        assert context.scenario == ScenarioType.WRITING
        assert context.name == "Writing Context"
        assert len(context.file_contexts) == 2

    def test_build_with_enhancer(self):
        """Test building context with enhancer."""
        mock_nb = MockNotebookLMIntegration()
        enhancer = ContextEnhancer(notebooklm_integration=mock_nb)
        builder = ScenarioContextBuilder(enhancer=enhancer)

        context = builder.build_for_coding(
            base_files=["main.py"],
            notebooklm_query="architecture",
        )

        # Should have NotebookLM context from enhancer
        assert context.notebooklm_context is not None

    def test_language_detection(self):
        """Test language detection in builder."""
        builder = ScenarioContextBuilder()
        context = builder.build_for_coding(
            base_files=["main.py", "app.js", "style.css", "config.json"],
        )

        languages = {f.language for f in context.file_contexts}
        assert "python" in languages
        assert "javascript" in languages
        assert "css" in languages
        assert "json" in languages


class TestContextEnhancerIntegration:
    """Integration tests for ContextEnhancer."""

    def test_complete_workflow(self):
        """Test complete enhancement workflow."""
        # Create enhancer with mock NotebookLM
        mock_nb = MockNotebookLMIntegration()
        enhancer = ContextEnhancer(notebooklm_integration=mock_nb)

        # Create builder with enhancer
        builder = ScenarioContextBuilder(enhancer=enhancer)

        # Build coding context
        context = builder.build_for_coding(
            base_files=["src/main.py", "src/utils.py"],
            notebooklm_query="project architecture",
        )

        # Verify context
        assert context.scenario == ScenarioType.CODING
        assert len(context.file_contexts) == 2
        assert context.notebooklm_context is not None

        # Extract summary
        summary = enhancer.extract_context_summary(context)
        assert summary["scenario"] == "coding"
        assert summary["file_count"] == 2
        assert summary["has_notebooklm"] is True

        # Suggest files
        project_files = [
            "src/main.py",
            "src/utils.py",
            "src/models.py",
            "docs/README.md",
            "test_main.py",
        ]
        suggested = enhancer.suggest_files(context, project_files, top_n=3)
        assert len(suggested) > 0

    def test_merge_and_enhance_workflow(self):
        """Test merging and enhancing contexts."""
        enhancer = ContextEnhancer()

        # Create multiple contexts
        ctx1 = Context(
            context_id="ctx-1",
            scenario=ScenarioType.CODING,
            name="Frontend",
        )
        ctx1.add_file(FileContext(path="app.js", language="javascript", size=100))

        ctx2 = Context(
            context_id="ctx-2",
            scenario=ScenarioType.CODING,
            name="Backend",
        )
        ctx2.add_file(FileContext(path="server.py", language="python", size=150))

        # Merge
        merged = enhancer.merge_contexts(
            [ctx1, ctx2],
            scenario=ScenarioType.CODING,
            name="Full Stack",
        )

        assert len(merged.file_contexts) == 2
        assert merged.name == "Full Stack"

        # Extract summary
        summary = enhancer.extract_context_summary(merged)
        assert summary["file_count"] == 2
