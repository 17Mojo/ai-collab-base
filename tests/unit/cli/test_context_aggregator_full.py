"""
Context Aggregator CLI Test Suite
Comprehensive tests for context_aggregator.py CLI module
Uses modular test framework for consistent patterns
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import framework utilities
sys.path.insert(0, str(Path(__file__).parent))
from base_cli_test import assert_failure, assert_success


class TestContextAggregatorCLIInit:
    """Test ContextAggregatorCLI initialization"""

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_init_default(self, mock_aggregator_class):
        """Test initialization with defaults"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()

        mock_aggregator_class.assert_called_once_with()
        assert cli.aggregator == mock_aggregator


class TestContextAggregatorCLIAddContext:
    """Test add_context method"""

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_add_context_success(self, mock_aggregator_class):
        """Test successfully adding context"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_context_id = MagicMock()
        mock_context_id.source_id = "ctx_123"
        mock_aggregator.extract_knowledge.return_value = mock_context_id
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.add_context(source="file", content="Test content")

        assert_success(result)
        mock_aggregator.extract_knowledge.assert_called_once_with(
            source_type="file", content="Test content", confidence=0.7
        )

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_add_context_with_confidence(self, mock_aggregator_class):
        """Test adding context with custom confidence"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_context_id = MagicMock()
        mock_context_id.source_id = "ctx_123"
        mock_aggregator.extract_knowledge.return_value = mock_context_id
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.add_context(source="api", content="Test content", confidence=0.9)

        assert_success(result)
        mock_aggregator.extract_knowledge.assert_called_once_with(
            source_type="api", content="Test content", confidence=0.9
        )

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_add_context_invalid_confidence_low(self, mock_aggregator_class):
        """Test adding context with confidence below range"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.add_context(source="file", content="Test content", confidence=-0.1)

        assert_failure(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_add_context_invalid_confidence_high(self, mock_aggregator_class):
        """Test adding context with confidence above range"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.add_context(source="file", content="Test content", confidence=1.5)

        assert_failure(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_add_context_aggregator_error(self, mock_aggregator_class):
        """Test handling aggregator error when adding context"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator.extract_knowledge.side_effect = ValueError("Invalid source type")
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.add_context(source="invalid", content="Test content")

        assert_failure(result)


class TestContextAggregatorCLIAddFromFile:
    """Test add_from_file method"""

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_add_from_file_success(self, mock_aggregator_class):
        """Test adding context from file successfully"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_context_id = MagicMock()
        mock_context_id.source_id = "ctx_123"
        mock_aggregator.extract_knowledge.return_value = mock_context_id
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()

        with patch("builtins.open", mock_open(read_data="File content")):
            result = cli.add_from_file(file_path="/path/to/test.txt", confidence=0.8)

        assert_success(result)
        mock_aggregator.extract_knowledge.assert_called_once_with(
            source_type="file", content="File content", confidence=0.8
        )

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_add_from_file_not_found(self, mock_aggregator_class):
        """Test adding context from non-existent file"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()

        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = FileNotFoundError("File not found")
            result = cli.add_from_file(file_path="/nonexistent/file.txt")

        assert_failure(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_add_from_file_io_error(self, mock_aggregator_class):
        """Test adding context when file read fails"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()

        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = IOError("Permission denied")
            result = cli.add_from_file(file_path="/restricted/file.txt")

        assert_failure(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_add_from_file_custom_source(self, mock_aggregator_class):
        """Test adding context from file with custom source type"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_context_id = MagicMock()
        mock_context_id.source_id = "ctx_456"
        mock_aggregator.extract_knowledge.return_value = mock_context_id
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()

        with patch("builtins.open", mock_open(read_data="Notebook content")):
            result = cli.add_from_file(
                file_path="/path/to/notebook.txt", source="notebook", confidence=0.9
            )

        assert_success(result)
        mock_aggregator.extract_knowledge.assert_called_once_with(
            source_type="notebook", content="Notebook content", confidence=0.9
        )


class TestContextAggregatorCLIAggregate:
    """Test aggregate method"""

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_aggregate_success(self, mock_aggregator_class):
        """Test successful context aggregation"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator.list_contexts.return_value = []

        mock_source1 = MagicMock()
        mock_source1.source_id = "source_1"
        mock_source2 = MagicMock()
        mock_source2.source_id = "source_2"

        mock_aggregator.sources = [mock_source1, mock_source2]

        mock_result = MagicMock()
        mock_result.sources = [mock_source1, mock_source2]
        mock_result.content = "Aggregated content"
        mock_aggregator.merge_knowledge.return_value = mock_result

        mock_context_id = MagicMock()
        mock_aggregator.create_context.return_value = mock_context_id
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.aggregate(query="test query")

        assert_success(result)
        mock_aggregator.merge_knowledge.assert_called_once()
        mock_aggregator.create_context.assert_called_once()

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_aggregate_no_sources(self, mock_aggregator_class):
        """Test aggregation when no sources available"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator.list_contexts.return_value = []
        mock_aggregator.sources = []
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.aggregate(query="test query")

        assert_failure(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_aggregate_exception_handling(self, mock_aggregator_class):
        """Test aggregation error handling"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator.list_contexts.return_value = []
        mock_aggregator.sources = [MagicMock()]
        mock_aggregator.merge_knowledge.side_effect = Exception("Merge error")
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.aggregate(query="test query")

        assert_failure(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_aggregate_with_custom_strategy(self, mock_aggregator_class):
        """Test aggregation with custom strategy"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator.list_contexts.return_value = []
        mock_source = MagicMock()
        mock_aggregator.sources = [mock_source]  # Must be a list

        mock_result = MagicMock()
        mock_result.sources = []
        mock_result.content = "Merged content"
        mock_aggregator.merge_knowledge.return_value = mock_result

        mock_context_id = MagicMock()
        mock_aggregator.create_context.return_value = mock_context_id
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.aggregate(query="test query", strategy="weighted")

        assert_success(result)
        mock_aggregator.merge_knowledge.assert_called_once()
        call_args = mock_aggregator.merge_knowledge.call_args
        assert "strategy" in call_args.kwargs
        assert call_args.kwargs["strategy"] == "weighted"


class TestContextAggregatorCLIStatus:
    """Test status method"""

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_status_with_data(self, mock_aggregator_class):
        """Test getting status when data exists"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_source1 = MagicMock()
        mock_source1.source_type = "api"
        mock_source1.confidence = 0.8
        mock_source2 = MagicMock()
        mock_source2.source_type = "file"
        mock_source2.confidence = 0.6

        mock_aggregator.sources = [mock_source1, mock_source2]
        mock_aggregator.get_history.return_value = []
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.status()

        assert_success(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_status_with_history(self, mock_aggregator_class):
        """Test getting status including history"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator.sources = []

        mock_ctx1 = MagicMock()
        mock_ctx1.context_id = "ctx_1"
        mock_ctx1.query = "Query 1"

        mock_aggregator.get_history.return_value = [mock_ctx1]
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.status()

        assert_success(result)


class TestContextAggregatorCLIListHistory:
    """Test list_history method"""

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_list_history_with_data(self, mock_aggregator_class):
        """Test listing history with data"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_ctx1 = MagicMock()
        mock_ctx1.context_id = "ctx_1"
        mock_ctx1.query = "Query 1"
        mock_ctx1.sources = [MagicMock()]

        import datetime

        mock_ctx1.created_at = datetime.datetime.now()

        mock_aggregator.get_history.return_value = [mock_ctx1]
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.list_history(limit=10)

        assert_success(result)
        mock_aggregator.get_history.assert_called_once_with(10)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_list_history_empty(self, mock_aggregator_class):
        """Test listing history when empty"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator.get_history.return_value = []
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.list_history()

        assert_success(result)


class TestContextAggregatorCLIExportContext:
    """Test export_context method"""

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_export_context_default(self, mock_aggregator_class):
        """Test exporting context with default (latest)"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.context_id = "ctx_123"
        mock_ctx.query = "Test query"
        mock_ctx.created_at = MagicMock()
        mock_ctx.created_at.isoformat.return_value = "2026-04-11T00:00:00"
        mock_ctx.sources = [MagicMock()]
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"key": "value"}
        mock_ctx.result = mock_result
        mock_aggregator.get_history.return_value = [mock_ctx]
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()

        with patch("builtins.open", mock_open()):
            result = cli.export_context()

        assert_success(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_export_context_by_id(self, mock_aggregator_class):
        """Test exporting specific context by ID"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_target = MagicMock()
        mock_target.context_id = "target_123"
        mock_target.created_at = MagicMock()
        mock_target.created_at.isoformat.return_value = "2026-04-11T00:00:00"
        mock_target.query = "Target query"
        mock_target.sources = [MagicMock(), MagicMock()]
        mock_target.result = MagicMock()
        mock_target.result.to_dict.return_value = {"key": "value"}

        mock_other = MagicMock()
        mock_other.context_id = "other_456"

        mock_aggregator.get_history.return_value = [mock_target, mock_other]
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.export_context(context_id="target_123")

        assert_success(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_export_context_no_contexts(self, mock_aggregator_class):
        """Test exporting when no contexts exist"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_aggregator.get_history.return_value = []
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.export_context()

        assert_failure(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_export_context_not_found(self, mock_aggregator_class):
        """Test exporting non-existent context ID"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.context_id = "ctx_123"
        mock_aggregator.get_history.return_value = [mock_ctx]
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.export_context(context_id="nonexistent")

        assert_failure(result)


class TestContextAggregatorCLIMain:
    """Test CLI main entry point"""

    @patch("sys.argv", ["context_aggregator.py"])
    def test_main_no_arguments(self):
        """Test main with no arguments"""
        from ai_collab.cli.context_aggregator import main

        result = main()
        assert result == 1

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_main_unknown_command(self, mock_aggregator_class):
        """Test main with unknown command"""
        from ai_collab.cli.context_aggregator import main

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        with patch("sys.argv", ["context_aggregator.py", "invalid"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_main_status_command(self, mock_aggregator_class):
        """Test main with status command"""
        from ai_collab.cli.context_aggregator import main

        mock_aggregator = MagicMock()
        mock_aggregator.sources = []
        mock_aggregator.get_history.return_value = []
        mock_aggregator_class.return_value = mock_aggregator

        with patch("sys.argv", ["context_aggregator.py", "status"]):
            result = main()

        assert result == 0

    def test_main_command_insufficient_args(self):
        """Test main commands with insufficient arguments"""
        from ai_collab.cli.context_aggregator import main

        # Test add command without required args
        with patch("sys.argv", ["context_aggregator.py", "add"]):
            result = main()
            assert result == 1

        # Test add-file command without required args
        with patch("sys.argv", ["context_aggregator.py", "add-file"]):
            result = main()
            assert result == 1

        # Test aggregate command without required args
        with patch("sys.argv", ["context_aggregator.py", "aggregate"]):
            result = main()
            assert result == 1

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_main_add_command_success(self, mock_aggregator_class):
        """Test main with add command success"""
        from ai_collab.cli.context_aggregator import main

        mock_aggregator = MagicMock()
        mock_context_id = MagicMock()
        mock_context_id.source_id = "ctx_123"
        mock_aggregator.extract_knowledge.return_value = mock_context_id
        mock_aggregator_class.return_value = mock_aggregator

        with patch(
            "sys.argv", ["context_aggregator.py", "add", "--source", "file", "--content", "test"]
        ):
            result = main()

        assert result == 0

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_main_history_command_with_limit(self, mock_aggregator_class):
        """Test main with history command and limit"""
        from ai_collab.cli.context_aggregator import main

        mock_aggregator = MagicMock()
        mock_aggregator.get_history.return_value = []
        mock_aggregator_class.return_value = mock_aggregator

        with patch("sys.argv", ["context_aggregator.py", "history", "--limit", "5"]):
            result = main()

        assert result == 0
        mock_aggregator.get_history.assert_called_once_with(5)


class TestContextAggregatorCLIEdgeCases:
    """Additional edge case tests for coverage"""

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_add_confidence_boundary_low(self, mock_aggregator_class):
        """Test adding context with confidence at lower boundary (0.0)"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_context_id = MagicMock()
        mock_aggregator.extract_knowledge.return_value = mock_context_id
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.add_context("file", "test", confidence=0.0)

        assert_success(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_add_confidence_boundary_high(self, mock_aggregator_class):
        """Test adding context with confidence at upper boundary (1.0)"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_context_id = MagicMock()
        mock_aggregator.extract_knowledge.return_value = mock_context_id
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.add_context("file", "test", confidence=1.0)

        assert_success(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_status_multiple_source_types(self, mock_aggregator_class):
        """Test status with multiple different source types"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        sources = []
        for i, (st, conf) in enumerate(
            [
                ("api", 0.9),
                ("file", 0.8),
                ("notebook", 0.75),
                ("api", 0.6),
                ("file", 0.5),
                ("notebook", 0.4),
            ]
        ):
            mock_s = MagicMock()
            mock_s.source_type = st
            mock_s.confidence = conf
            sources.append(mock_s)

        mock_aggregator.sources = sources
        mock_aggregator.get_history.return_value = []
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.status()

        assert_success(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_list_history_with_multiple_items(self, mock_aggregator_class):
        """Test listing history with multiple items"""
        import datetime

        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        contexts = []
        for i in range(5):
            ctx = MagicMock()
            ctx.context_id = f"ctx_{i}"
            ctx.query = f"Query {i}"
            ctx.sources = [MagicMock() for _ in range(i + 1)]
            ctx.created_at = datetime.datetime.now()
            contexts.append(ctx)

        mock_aggregator.get_history.return_value = contexts[:3]
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.list_history(limit=3)

        assert_success(result)
        mock_aggregator.get_history.assert_called_once_with(3)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_export_context_write_file(self, mock_aggregator_class):
        """Test that export actually writes to file"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.context_id = "export_test"
        mock_ctx.query = "Export test"
        mock_ctx.created_at = MagicMock()
        mock_ctx.created_at.isoformat.return_value = "2026-04-12T10:00:00"
        mock_ctx.sources = [MagicMock()]
        mock_ctx.result = MagicMock()
        mock_ctx.result.to_dict.return_value = {"test": "data"}
        mock_aggregator.get_history.return_value = [mock_ctx]
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()

        opened_files = []

        def track_open(path, mode="r", **kwargs):
            opened_files.append(path)
            return mock_open(read_data="test")()

        with patch("builtins.open", side_effect=track_open):
            result = cli.export_context()

        assert_success(result)
        assert len(opened_files) == 1
        assert opened_files[0].endswith("export_test.json")


class TestContextAggregatorCLIMainFull:
    """Test CLI main entry point - full coverage"""

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_main_add_file_command(self, mock_aggregator_class):
        """Test main with add-file command - lines 319-343"""
        from ai_collab.cli.context_aggregator import main

        mock_aggregator = MagicMock()
        mock_context_id = MagicMock()
        mock_aggregator.extract_knowledge.return_value = mock_context_id
        mock_aggregator_class.return_value = mock_aggregator

        with patch(
            "sys.argv", ["context_aggregator.py", "add-file", "--path", "/path/to/file.txt"]
        ):
            with patch("builtins.open", mock_open(read_data="test content")):
                result = main()

        assert result == 0

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_main_add_file_with_options(self, mock_aggregator_class):
        """Test main with add-file command with all options"""
        from ai_collab.cli.context_aggregator import main

        mock_aggregator = MagicMock()
        mock_context_id = MagicMock()
        mock_aggregator.extract_knowledge.return_value = mock_context_id
        mock_aggregator_class.return_value = mock_aggregator

        with patch(
            "sys.argv",
            [
                "context_aggregator.py",
                "add-file",
                "--path",
                "/path/to/file.txt",
                "--source",
                "notebook",
                "--confidence",
                "0.9",
            ],
        ):
            with patch("builtins.open", mock_open(read_data="test content")):
                result = main()

        assert result == 0

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_main_aggregate_command(self, mock_aggregator_class):
        """Test main with aggregate command - lines 345-379"""
        from ai_collab.cli.context_aggregator import main

        mock_aggregator = MagicMock()
        mock_aggregator.sources = [MagicMock()]  # Need sources for aggregation
        mock_result = MagicMock()
        mock_result.context_id = "ctx_agg"
        mock_result.query = "test query"
        mock_result.sources = []
        mock_result.result = MagicMock()
        mock_aggregator.merge_knowledge.return_value = mock_result
        mock_aggregator_class.return_value = mock_aggregator

        with patch("sys.argv", ["context_aggregator.py", "aggregate", "--query", "test query"]):
            result = main()

        assert result == 0

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_main_aggregate_with_strategy(self, mock_aggregator_class):
        """Test main with aggregate command with strategy"""
        from ai_collab.cli.context_aggregator import main

        mock_aggregator = MagicMock()
        mock_aggregator.sources = [MagicMock()]  # Need sources for aggregation
        mock_result = MagicMock()
        mock_result.context_id = "ctx_agg"
        mock_result.query = "test query"
        mock_result.sources = []
        mock_result.result = MagicMock()
        mock_aggregator.merge_knowledge.return_value = mock_result
        mock_aggregator_class.return_value = mock_aggregator

        with patch(
            "sys.argv",
            [
                "context_aggregator.py",
                "aggregate",
                "--query",
                "test query",
                "--strategy",
                "weighted",
            ],
        ):
            result = main()

        assert result == 0

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_main_export_command(self, mock_aggregator_class):
        """Test main with export command - lines 381-393"""
        from ai_collab.cli.context_aggregator import main

        mock_aggregator = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.context_id = "ctx_export"
        mock_ctx.query = "export query"
        mock_ctx.created_at = MagicMock()
        mock_ctx.created_at.isoformat.return_value = "2026-04-12T00:00:00"
        mock_ctx.sources = []
        mock_ctx.result = MagicMock()
        mock_ctx.result.to_dict.return_value = {"key": "value"}
        mock_aggregator.get_history.return_value = [mock_ctx]
        mock_aggregator_class.return_value = mock_aggregator

        with patch("sys.argv", ["context_aggregator.py", "export"]):
            with patch("builtins.open", mock_open()):
                result = main()

        assert result == 0

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_main_export_with_context_id(self, mock_aggregator_class):
        """Test main with export command with context-id"""
        from ai_collab.cli.context_aggregator import main

        mock_aggregator = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.context_id = "target_ctx"
        mock_ctx.query = "export query"
        mock_ctx.created_at = MagicMock()
        mock_ctx.created_at.isoformat.return_value = "2026-04-12T00:00:00"
        mock_ctx.sources = []
        mock_ctx.result = MagicMock()
        mock_ctx.result.to_dict.return_value = {"key": "value"}
        mock_aggregator.get_history.return_value = [mock_ctx]
        mock_aggregator_class.return_value = mock_aggregator

        with patch("sys.argv", ["context_aggregator.py", "export", "--context-id", "target_ctx"]):
            with patch("builtins.open", mock_open()):
                result = main()

        assert result == 0


class TestContextAggregatorCLISourceHandling:
    """Test source handling - lines 265-272"""

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_status_with_nested_aggregator_sources(self, mock_aggregator_class):
        """Test status with nested aggregator sources - line 269-270"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        # Create mock with nested aggregator
        mock_aggregator = MagicMock()

        # Create nested aggregator with sources
        mock_nested = MagicMock()
        mock_source = MagicMock()
        mock_source.source_type = "api"
        mock_source.confidence = 0.9
        mock_nested.sources = [mock_source]

        # Make hasattr return False for direct sources, True for nested
        del mock_aggregator.sources  # Remove direct sources attribute
        mock_aggregator.aggregator = mock_nested

        mock_aggregator.get_history.return_value = []
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.status()

        assert_success(result)

    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_status_with_no_sources_anywhere(self, mock_aggregator_class):
        """Test status with no sources anywhere - line 272"""
        from ai_collab.cli.context_aggregator import ContextAggregatorCLI

        mock_aggregator = MagicMock()
        del mock_aggregator.sources  # No sources attribute
        mock_aggregator.get_history.return_value = []
        mock_aggregator_class.return_value = mock_aggregator

        cli = ContextAggregatorCLI()
        result = cli.status()

        assert_success(result)
