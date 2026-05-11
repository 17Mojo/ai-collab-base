"""
Context schema tests.
"""

from __future__ import annotations

from datetime import datetime

from ai_collab.context.schema import (
    AISessionContext,
    Context,
    ContextChangeLog,
    ContextMetadata,
    ContextSource,
    FileContext,
    NotebookLMContext,
    ScenarioType,
    create_context,
)


class TestScenarioType:
    """Test ScenarioType enum."""

    def test_scenario_types(self):
        assert ScenarioType.CODING.value == "coding"
        assert ScenarioType.RESEARCH.value == "research"
        assert ScenarioType.WRITING.value == "writing"
        assert ScenarioType.DEBUGGING.value == "debugging"
        assert ScenarioType.DESIGN.value == "design"
        assert ScenarioType.PROJECT_PLANNING.value == "project_planning"
        assert ScenarioType.DOCUMENTATION.value == "documentation"
        assert ScenarioType.UNKNOWN.value == "unknown"


class TestContextSource:
    """Test ContextSource enum."""

    def test_context_sources(self):
        assert ContextSource.FILE_SYSTEM.value == "file_system"
        assert ContextSource.AI_SESSION.value == "ai_session"
        assert ContextSource.NOTEBOOKLM.value == "notebooklm"
        assert ContextSource.USER_INPUT.value == "user_input"
        assert ContextSource.EXTERNAL_API.value == "external_api"
        assert ContextSource.PACK_RESULT.value == "pack_result"


class TestFileContext:
    """Test FileContext dataclass."""

    def test_file_context_creation(self):
        file_ctx = FileContext(
            path="src/ai_collab/context/schema.py",
            content="print('hello')",
            language="python",
            size=100,
        )
        assert file_ctx.path == "src/ai_collab/context/schema.py"
        assert file_ctx.content == "print('hello')"
        assert file_ctx.language == "python"
        assert file_ctx.size == 100

    def test_file_context_to_dict(self):
        file_ctx = FileContext(
            path="test.py",
            content="# test",
            language="python",
            size=50,
            modified_at=datetime(2026, 4, 3, 12, 0),
            hash="abc123",
        )
        result = file_ctx.to_dict()
        assert result["path"] == "test.py"
        assert result["content"] == "# test"
        assert result["language"] == "python"
        assert result["size"] == 50
        assert result["modified_at"] == "2026-04-03T12:00:00"
        assert result["hash"] == "abc123"


class TestAISessionContext:
    """Test AISessionContext dataclass."""

    def test_ai_session_creation(self):
        session = AISessionContext(
            session_id="sess-1",
            ai_type="claude",
            started_at=datetime(2026, 4, 3, 10, 0),
            messages=[{"role": "user", "content": "test"}],
        )
        assert session.session_id == "sess-1"
        assert session.ai_type == "claude"
        assert len(session.messages) == 1

    def test_ai_session_to_dict(self):
        session = AISessionContext(
            session_id="sess-2",
            ai_type="codex",
            started_at=datetime(2026, 4, 3, 11, 0),
        )
        result = session.to_dict()
        assert result["session_id"] == "sess-2"
        assert result["ai_type"] == "codex"
        assert result["started_at"] == "2026-04-03T11:00:00"


class TestNotebookLMContext:
    """Test NotebookLMContext dataclass."""

    def test_notebooklm_creation(self):
        nb_ctx = NotebookLMContext(
            notebook_id="nb-1",
            notebook_name="test notebook",
            query_results=[{"query": "test", "answer": "result"}],
            sources=["doc1.pdf", "doc2.pdf"],
        )
        assert nb_ctx.notebook_id == "nb-1"
        assert nb_ctx.notebook_name == "test notebook"
        assert len(nb_ctx.query_results) == 1
        assert len(nb_ctx.sources) == 2

    def test_notebooklm_to_dict(self):
        nb_ctx = NotebookLMContext(
            notebook_id="nb-2",
            notebook_name="demo",
        )
        result = nb_ctx.to_dict()
        assert result["notebook_id"] == "nb-2"
        assert result["notebook_name"] == "demo"
        assert result["query_results"] == []
        assert result["sources"] == []


class TestContextMetadata:
    """Test ContextMetadata dataclass."""

    def test_metadata_creation(self):
        meta = ContextMetadata(
            tags=["coding", "python"],
            owner="user",
            version=2,
        )
        assert len(meta.tags) == 2
        assert meta.owner == "user"
        assert meta.version == 2

    def test_metadata_touch(self):
        meta = ContextMetadata()
        original_time = meta.updated_at
        meta.touch()
        assert meta.updated_at > original_time


class TestContext:
    """Test Context dataclass."""

    def test_context_creation(self):
        ctx = Context(
            context_id="ctx-1",
            scenario=ScenarioType.CODING,
            name="Coding session",
        )
        assert ctx.context_id == "ctx-1"
        assert ctx.scenario == ScenarioType.CODING
        assert ctx.name == "Coding session"
        assert len(ctx.file_contexts) == 0
        assert len(ctx.ai_sessions) == 0

    def test_add_file(self):
        ctx = Context(
            context_id="ctx-2",
            scenario=ScenarioType.CODING,
            name="Test",
        )
        file_ctx = FileContext(path="test.py", language="python", size=100)
        ctx.add_file(file_ctx)
        assert len(ctx.file_contexts) == 1
        assert ctx.file_contexts[0].path == "test.py"
        assert ctx.metadata.updated_at > ctx.metadata.created_at

    def test_add_ai_session(self):
        ctx = Context(
            context_id="ctx-3",
            scenario=ScenarioType.CODING,
            name="Test",
        )
        session = AISessionContext(
            session_id="sess-1",
            ai_type="claude",
            started_at=datetime(2026, 4, 3, 10, 0),
        )
        ctx.add_ai_session(session)
        assert len(ctx.ai_sessions) == 1

    def test_update_notebooklm(self):
        ctx = Context(
            context_id="ctx-4",
            scenario=ScenarioType.RESEARCH,
            name="Test",
        )
        nb_ctx = NotebookLMContext(
            notebook_id="nb-1",
            notebook_name="research",
        )
        ctx.update_notebooklm(nb_ctx)
        assert ctx.notebooklm_context is not None
        assert ctx.notebooklm_context.notebook_id == "nb-1"

    def test_get_file_by_path(self):
        ctx = Context(
            context_id="ctx-5",
            scenario=ScenarioType.CODING,
            name="Test",
        )
        file_ctx1 = FileContext(path="file1.py", language="python", size=100)
        file_ctx2 = FileContext(path="file2.py", language="python", size=150)
        ctx.add_file(file_ctx1)
        ctx.add_file(file_ctx2)

        found = ctx.get_file_by_path("file1.py")
        assert found is not None
        assert found.path == "file1.py"

        not_found = ctx.get_file_by_path("file3.py")
        assert not_found is None

    def test_get_latest_session(self):
        ctx = Context(
            context_id="ctx-6",
            scenario=ScenarioType.CODING,
            name="Test",
        )
        session1 = AISessionContext(
            session_id="sess-1",
            ai_type="claude",
            started_at=datetime(2026, 4, 3, 10, 0),
        )
        session2 = AISessionContext(
            session_id="sess-2",
            ai_type="claude",
            started_at=datetime(2026, 4, 3, 11, 0),
        )
        ctx.add_ai_session(session1)
        ctx.add_ai_session(session2)

        latest = ctx.get_latest_session()
        assert latest is not None
        assert latest.session_id == "sess-2"

    def test_get_latest_session_filtered(self):
        ctx = Context(
            context_id="ctx-7",
            scenario=ScenarioType.CODING,
            name="Test",
        )
        claude_session = AISessionContext(
            session_id="claude-1",
            ai_type="claude",
            started_at=datetime(2026, 4, 3, 10, 0),
        )
        codex_session = AISessionContext(
            session_id="codex-1",
            ai_type="codex",
            started_at=datetime(2026, 4, 3, 12, 0),
        )
        ctx.add_ai_session(claude_session)
        ctx.add_ai_session(codex_session)

        claude_latest = ctx.get_latest_session(ai_type="claude")
        assert claude_latest is not None
        assert claude_latest.ai_type == "claude"

    def test_get_summary(self):
        ctx = Context(
            context_id="ctx-8",
            scenario=ScenarioType.CODING,
            name="Test context",
        )
        ctx.add_file(FileContext(path="test.py", language="python", size=100))
        ctx.add_file(FileContext(path="test2.py", language="python", size=150))

        summary = ctx.get_summary()
        assert summary["context_id"] == "ctx-8"
        assert summary["scenario"] == "coding"
        assert summary["name"] == "Test context"
        assert summary["file_count"] == 2
        assert summary["session_count"] == 0
        assert summary["has_notebooklm"] is False

    def test_to_dict(self):
        ctx = Context(
            context_id="ctx-9",
            scenario=ScenarioType.CODING,
            name="Test",
        )
        ctx.add_file(FileContext(path="test.py", language="python", size=100))
        ctx.add_ai_session(
            AISessionContext(
                session_id="sess-1",
                ai_type="claude",
                started_at=datetime(2026, 4, 3, 10, 0),
            )
        )

        result = ctx.to_dict()
        assert result["context_id"] == "ctx-9"
        assert result["scenario"] == "coding"
        assert len(result["file_contexts"]) == 1
        assert len(result["ai_sessions"]) == 1

    def test_from_dict(self):
        data = {
            "context_id": "ctx-10",
            "scenario": "coding",
            "name": "Test",
            "file_contexts": [
                {
                    "path": "test.py",
                    "content": None,
                    "language": "python",
                    "size": 100,
                    "modified_at": None,
                    "hash": None,
                }
            ],
            "ai_sessions": [],
            "notebooklm_context": None,
            "user_context": {},
            "metadata": {
                "created_at": "2026-04-03T10:00:00",
                "updated_at": "2026-04-03T10:00:00",
                "tags": [],
                "owner": "system",
                "version": 1,
            },
            "parent_id": None,
            "children_ids": [],
            "size": 100,
        }

        ctx = Context.from_dict(data)
        assert ctx.context_id == "ctx-10"
        assert ctx.scenario == ScenarioType.CODING
        assert len(ctx.file_contexts) == 1
        assert ctx.file_contexts[0].path == "test.py"

    def test_serialize_deserialize_roundtrip(self):
        original = Context(
            context_id="ctx-11",
            scenario=ScenarioType.RESEARCH,
            name="Research context",
        )
        original.add_file(FileContext(path="doc.md", language="markdown", size=200))
        original.add_ai_session(
            AISessionContext(
                session_id="sess-1",
                ai_type="claude",
                started_at=datetime(2026, 4, 3, 10, 0),
                messages=[{"role": "user", "content": "test"}],
            )
        )

        data = original.to_dict()
        restored = Context.from_dict(data)

        assert restored.context_id == original.context_id
        assert restored.scenario == original.scenario
        assert restored.name == original.name
        assert len(restored.file_contexts) == len(original.file_contexts)
        assert len(restored.ai_sessions) == len(original.ai_sessions)


class TestContextChangeLog:
    """Test ContextChangeLog dataclass."""

    def test_change_log_creation(self):
        log = ContextChangeLog(
            log_id="log-1",
            context_id="ctx-1",
            change_type="file_add",
            timestamp=datetime(2026, 4, 3, 12, 0),
            details={"file": "test.py"},
            source=ContextSource.FILE_SYSTEM,
        )
        assert log.log_id == "log-1"
        assert log.context_id == "ctx-1"
        assert log.change_type == "file_add"
        assert log.source == ContextSource.FILE_SYSTEM

    def test_change_log_to_dict(self):
        log = ContextChangeLog(
            log_id="log-2",
            context_id="ctx-2",
            change_type="update",
            timestamp=datetime(2026, 4, 3, 13, 0),
            details={"field": "value"},
            source=ContextSource.USER_INPUT,
        )
        result = log.to_dict()
        assert result["log_id"] == "log-2"
        assert result["context_id"] == "ctx-2"
        assert result["change_type"] == "update"
        assert result["source"] == "user_input"


class TestCreateContext:
    """Test create_context factory function."""

    def test_create_context_without_files(self):
        ctx = create_context(
            scenario=ScenarioType.CODING,
            name="Test context",
        )
        assert ctx.scenario == ScenarioType.CODING
        assert ctx.name == "Test context"
        assert len(ctx.file_contexts) == 0
        assert ctx.context_id is not None

    def test_create_context_with_files(self):
        ctx = create_context(
            scenario=ScenarioType.WRITING,
            name="Writing context",
            files=["article1.md", "article2.md"],
        )
        assert len(ctx.file_contexts) == 2
        assert ctx.file_contexts[0].path == "article1.md"
        assert ctx.file_contexts[1].path == "article2.md"
        assert ctx.file_contexts[0].language == "markdown"

    def test_create_context_with_custom_id(self):
        custom_id = "my-custom-id"
        ctx = create_context(
            scenario=ScenarioType.DEBUGGING,
            name="Debug context",
            context_id=custom_id,
        )
        assert ctx.context_id == custom_id

    def test_language_detection(self):
        ctx = create_context(
            scenario=ScenarioType.CODING,
            name="Test",
            files=[
                "app.py",
                "style.css",
                "index.html",
                "config.json",
                "README.md",
            ],
        )

        languages = {f.language for f in ctx.file_contexts}
        assert "python" in languages
        assert "css" in languages
        assert "html" in languages
        assert "json" in languages
        assert "markdown" in languages


class TestContextIntegration:
    """Integration tests for Context."""

    def test_complete_context_workflow(self):
        """Test complete context creation and modification workflow."""
        # Create context
        ctx = create_context(
            scenario=ScenarioType.CODING,
            name="Full workflow test",
            files=["main.py", "utils.py"],
        )

        # Add AI session
        session = AISessionContext(
            session_id="sess-1",
            ai_type="claude",
            started_at=datetime(2026, 4, 3, 10, 0),
            messages=[
                {"role": "user", "content": "Help me code"},
                {"role": "assistant", "content": "I'll help"},
            ],
        )
        ctx.add_ai_session(session)

        # Add NotebookLM context
        nb_ctx = NotebookLMContext(
            notebook_id="nb-1",
            notebook_name="project-docs",
            query_results=[{"query": "architecture", "answer": "..."}],
            sources=["arch.md", "design.md"],
        )
        ctx.update_notebooklm(nb_ctx)

        # Verify
        assert len(ctx.file_contexts) == 2
        assert len(ctx.ai_sessions) == 1
        assert ctx.notebooklm_context is not None
        assert ctx.notebooklm_context.notebook_id == "nb-1"

        # Serialize and restore
        data = ctx.to_dict()
        restored = Context.from_dict(data)

        assert restored.context_id == ctx.context_id
        assert restored.scenario == ctx.scenario
        assert restored.name == ctx.name
        assert len(restored.file_contexts) == len(ctx.file_contexts)
        assert len(restored.ai_sessions) == len(ctx.ai_sessions)
        assert restored.notebooklm_context is not None
        assert restored.notebooklm_context.notebook_id == nb_ctx.notebook_id


class TestContextEdgeCases:
    """Edge case tests for Context that improve coverage."""

    def test_get_file_by_path_returns_none_when_empty(self):
        """test_get_file_by_path returns None when file_contexts is empty."""
        ctx = Context(
            context_id="ctx-edge-1",
            scenario=ScenarioType.CODING,
            name="Test",
        )
        result = ctx.get_file_by_path("any.py")
        assert result is None

    def test_get_latest_session_returns_none_when_empty(self):
        """test_get_latest_session returns None when ai_sessions is empty."""
        ctx = Context(
            context_id="ctx-edge-2",
            scenario=ScenarioType.CODING,
            name="Test",
        )
        result = ctx.get_latest_session()
        assert result is None

    def test_get_latest_session_filter_returns_none_when_no_match(self):
        """test_get_latest_session with ai_type filter returns None when no match."""
        ctx = Context(
            context_id="ctx-edge-3",
            scenario=ScenarioType.CODING,
            name="Test",
        )
        session = AISessionContext(
            session_id="sess-1",
            ai_type="claude",
            started_at=datetime(2026, 4, 3, 10, 0),
        )
        ctx.add_ai_session(session)
        result = ctx.get_latest_session(ai_type="codex")
        assert result is None

    def test_to_dict_with_notebooklm_null(self):
        """test_to_dict when notebooklm_context is None."""
        ctx = Context(
            context_id="ctx-edge-4",
            scenario=ScenarioType.CODING,
            name="Test",
        )
        result = ctx.to_dict()
        assert result["notebooklm_context"] is None

    def test_from_dict_with_notebooklm(self):
        """test_from_dict with notebooklm_context."""
        data = {
            "context_id": "ctx-edge-5",
            "scenario": "research",
            "name": "Test",
            "file_contexts": [],
            "ai_sessions": [],
            "notebooklm_context": {
                "notebook_id": "nb-1",
                "notebook_name": "Test Notebook",
                "query_results": [],
                "sources": [],
                "last_updated": None,
            },
            "user_context": {},
            "metadata": {
                "created_at": "2026-04-03T10:00:00",
                "updated_at": "2026-04-03T10:00:00",
                "tags": [],
                "owner": "system",
                "version": 1,
            },
            "parent_id": None,
            "children_ids": [],
            "size": 0,
        }
        ctx = Context.from_dict(data)
        assert ctx.notebooklm_context is not None
        assert ctx.notebooklm_context.notebook_id == "nb-1"

    def test_recalculate_size_with_user_context(self):
        """test__recalculate_size includes user_context."""
        ctx = Context(
            context_id="ctx-edge-6",
            scenario=ScenarioType.CODING,
            name="Test",
            user_context={"key": "value" * 100},
        )
        assert ctx.size > 0

    def test_recalculate_size_with_notebooklm(self):
        """test__recalculate_size includes notebooklm_context."""
        ctx = Context(
            context_id="ctx-edge-7",
            scenario=ScenarioType.CODING,
            name="Test",
        )
        notebooklm = NotebookLMContext(
            notebook_id="nb-1",
            notebook_name="Test",
            query_results=[{"data": "x" * 100}],
        )
        ctx.update_notebooklm(notebooklm)
        size_before = ctx.size
        assert size_before > 0

    def test_file_context_to_dict_with_none_modified_at(self):
        """test FileContext.to_dict when modified_at is None."""
        file_ctx = FileContext(path="test.py")
        result = file_ctx.to_dict()
        assert result["modified_at"] is None

    def test_file_context_to_dict_with_none_hash(self):
        """test FileContext.to_dict when hash is None."""
        file_ctx = FileContext(path="test.py", modified_at=datetime.now())
        result = file_ctx.to_dict()
        assert result["hash"] is None

    def test_notebooklm_context_to_dict_with_none_last_updated(self):
        """test NotebookLMContext.to_dict when last_updated is None."""
        nb_ctx = NotebookLMContext(notebook_id="nb-1", notebook_name="Test")
        result = nb_ctx.to_dict()
        assert result["last_updated"] is None

    def test_notebooklm_context_to_dict_with_last_updated_set(self):
        """test NotebookLMContext.to_dict when last_updated is set."""
        nb_ctx = NotebookLMContext(
            notebook_id="nb-1",
            notebook_name="Test",
            last_updated=datetime(2026, 4, 3, 10, 0),
        )
        result = nb_ctx.to_dict()
        assert result["last_updated"] == "2026-04-03T10:00:00"

    def test_context_change_log_to_dict(self):
        """test ContextChangeLog.to_dict."""
        log = ContextChangeLog(
            log_id="log-3",
            context_id="ctx-1",
            change_type="create",
            timestamp=datetime(2026, 4, 3, 10, 0),
            details={"message": "test"},
            source=ContextSource.USER_INPUT,
        )
        result = log.to_dict()
        assert result["log_id"] == "log-3"
        assert result["source"] == "user_input"
        assert result["timestamp"] == "2026-04-03T10:00:00"

    def test_create_context_without_files_has_no_file_contexts(self):
        """test create_context without files has no file_contexts."""
        ctx = create_context(
            scenario=ScenarioType.CODING,
            name="Test",
        )
        assert len(ctx.file_contexts) == 0

    def test_create_context_auto_generates_context_id(self):
        """test create_context auto-generates context_id when not provided."""
        ctx = create_context(
            scenario=ScenarioType.CODING,
            name="Test",
        )
        assert ctx.context_id is not None
        assert len(ctx.context_id) > 0

    def test_create_context_with_empty_files_list(self):
        """test create_context with empty files list."""
        ctx = create_context(
            scenario=ScenarioType.CODING,
            name="Test",
            files=[],
        )
        assert len(ctx.file_contexts) == 0

    def test_create_context_language_detection_unknown_extension(self):
        """test create_context language detection for unknown extensions."""
        ctx = create_context(
            scenario=ScenarioType.CODING,
            name="Test",
            files=["file.unknown", "file.xyz"],
        )
        assert ctx.file_contexts[0].language == "text"
        assert ctx.file_contexts[1].language == "text"

    def test_create_context_with_parent_and_children(self):
        """test create_context can later accept parent_id and children_ids."""
        ctx = create_context(
            scenario=ScenarioType.CODING,
            name="Test",
        )
        ctx.parent_id = "parent-001"
        ctx.children_ids = ["child-001", "child-002"]
        assert ctx.parent_id == "parent-001"
        assert len(ctx.children_ids) == 2

    def test_context_size_recalculation_on_add_file(self):
        """test context size is recalculated when adding file."""
        ctx = create_context(
            scenario=ScenarioType.CODING,
            name="Test",
        )
        initial_size = ctx.size
        file_ctx = FileContext(path="test.py", size=500)
        ctx.add_file(file_ctx)
        assert ctx.size > initial_size
        assert ctx.size >= 500
