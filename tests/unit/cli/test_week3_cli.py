"""
CLI Tests for Week 3 Features
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestContextSearchCLI:
    """Context Search CLI Tests"""

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    def test_search_command(self, mock_engine_class):
        """测试 search 命令"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_stats = MagicMock()
        mock_stats.method.value = "semantic"
        mock_stats.total_results = 0
        mock_engine.search.return_value = ([], mock_stats)

        cli = ContextSearchCLI()
        result = cli.search("test query", method="semantic")

        assert result == 0
        mock_engine.search.assert_called_once()

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    def test_suggest_command(self, mock_engine_class):
        """测试 suggest 命令"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.suggest.return_value = ["suggestion1", "suggestion2"]

        cli = ContextSearchCLI()
        result = cli.suggest("test", limit=2)

        assert result == 0
        mock_engine.suggest.assert_called_once_with("test", 2)

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    def test_history_command(self, mock_engine_class):
        """测试 history 命令"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_stats = MagicMock()
        mock_stats.execution_time_ms = 100
        mock_engine.get_search_history.return_value = [mock_stats, mock_stats]

        cli = ContextSearchCLI()
        result = cli.history(count=2)

        assert result == 0
        mock_engine.get_search_history.assert_called_once()

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    def test_clear_history_command(self, mock_engine_class):
        """测试 clear 命令"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.clear_history()

        assert result == 0
        mock_engine.clear_history.assert_called_once()

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    def test_export_results_command(self, mock_engine_class):
        """测试 export 命令"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_stats = MagicMock()
        mock_stats.method.value = "semantic"
        mock_stats.scope.value = "all"
        mock_stats.total_results = 0
        mock_engine.search.return_value = ([], mock_stats)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "test.json"

            cli = ContextSearchCLI()
            result = cli.export_results("test query", str(output_file))

            assert result == 0
            assert output_file.exists()


class TestCLIErrorHandling:
    """CLI 错误处理测试"""

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    def test_context_search_cli_invalid_method(self, mock_engine_class):
        """测试无效搜索方法"""
        from ai_collab.cli.context_search import ContextSearchCLI

        cli = ContextSearchCLI()
        result = cli.search("test", method="invalid")

        # 应该返回错误
        assert result == 1
