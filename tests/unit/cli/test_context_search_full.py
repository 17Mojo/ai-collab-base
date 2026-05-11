"""
Context Search CLI测试套件
全覆盖测试 - 目标将覆盖率从29%提升至60%+
使用模块化测试框架
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import framework utilities
sys.path.insert(0, str(Path(__file__).parent))
from base_cli_test import assert_failure, assert_success


class TestContextSearchCLIInit:
    """测试 ContextSearchCLI 初始化"""

    @patch("ai_collab.cli.context_search.ContextAggregator")
    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    def test_init_default(self, mock_engine_class, mock_aggregator_class):
        """测试默认初始化"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()

        assert cli.aggregator == mock_aggregator
        assert cli.search_engine == mock_engine


class TestContextSearchCLISearch:
    """测试 search 方法"""

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_search_success_semantic(self, mock_aggregator_class, mock_engine_class):
        """测试语义搜索成功"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_result.context_id = "ctx_123"
        mock_result.score = 0.95
        mock_result.relevance = "very_high"
        mock_result.content = "Test content with some length"
        mock_result.matches = ["test", "content"]

        mock_engine.search.return_value = (
            [mock_result],
            MagicMock(
                method=MagicMock(value="semantic"),
                scope=MagicMock(value="all"),
                total_results=1,
                filtered_results=0,
            ),
        )
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.search("test query")

        assert_success(result)
        mock_engine.search.assert_called_once()

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_search_no_results(self, mock_aggregator_class, mock_engine_class):
        """测试无结果搜索"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_engine.search.return_value = (
            [],
            MagicMock(
                total_results=0,
                filtered_results=0,
                method=MagicMock(value="semantic"),
                scope=MagicMock(value="all"),
            ),
        )
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.search("nonexistent query")

        assert_success(result)

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_search_invalid_method(self, mock_aggregator_class, mock_engine_class):
        """测试无效的搜索方法"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.search("query", method="invalid_method")

        assert_failure(result)

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_search_invalid_scope(self, mock_aggregator_class, mock_engine_class):
        """测试无效的搜索范围"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.search("query", scope="invalid_scope")

        assert_failure(result)

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_search_custom_scope(self, mock_aggregator_class, mock_engine_class):
        """测试自定义范围（有效值）"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_engine.search.return_value = ([], MagicMock())
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.search("query", scope="recent")

        assert_success(result)


class TestContextSearchCLISuggest:
    """测试 suggest 方法"""

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_suggest_success(self, mock_aggregator_class, mock_engine_class):
        """测试建议查询词成功"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_engine.suggest.return_value = ["test1", "test2", "test3"]
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.suggest("test")

        assert_success(result)
        mock_engine.suggest.assert_called_once_with("test", 5)

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_suggest_no_results(self, mock_aggregator_class, mock_engine_class):
        """测试无建议结果"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_engine.suggest.return_value = []
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.suggest("xyz")

        assert_success(result)

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_suggest_custom_limit(self, mock_aggregator_class, mock_engine_class):
        """测试自定义建议数量"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_engine.suggest.return_value = ["suggestion"]
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.suggest("test", limit=10)

        assert_success(result)
        mock_engine.suggest.assert_called_once_with("test", 10)


class TestContextSearchCLIHistory:
    """测试 history 方法"""

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_history_with_data(self, mock_aggregator_class, mock_engine_class):
        """测试显示有数据的历史"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_history = []
        for i in range(3):
            stat = MagicMock()
            stat.method = MagicMock(value=f"method_{i}")
            stat.scope = MagicMock(value=f"scope_{i}")
            stat.total_results = i * 10
            stat.execution_time_ms = 50.0 + i * 10
            mock_history.append(stat)

        mock_engine.get_search_history.return_value = mock_history
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.history(count=10)

        assert_success(result)
        mock_engine.get_search_history.assert_called_once()

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_history_empty(self, mock_aggregator_class, mock_engine_class):
        """测试显示空历史"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_engine.get_search_history.return_value = []
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.history()

        assert_success(result)


class TestContextSearchCLIClearHistory:
    """测试 clear_history 方法"""

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_clear_history(self, mock_aggregator_class, mock_engine_class):
        """测试清空历史"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.clear_history()

        assert_success(result)
        mock_engine.clear_history.assert_called_once()


class TestContextSearchCLIMain:
    """测试 CLI main 入口点"""

    @patch("sys.argv", ["context_search.py"])
    def test_main_no_arguments(self):
        """测试无参数调用"""
        from ai_collab.cli.context_search import main

        result = main()
        assert result == 1

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_unknown_command(self, mock_cli_class):
        """测试未知命令"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "unknown_cmd"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_search_command(self, mock_cli_class):
        """测试搜索命令"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.search.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "search", "test query"]):
            result = main()

        assert result == 0
        mock_cli.search.assert_called_once_with("test query")

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_search_insufficient_args(self, mock_cli_class):
        """测试搜索命令缺少参数"""
        from ai_collab.cli.context_search import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["context_search.py", "search"]):
            result = main()

        assert result == 1

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_suggest_command(self, mock_cli_class):
        """测试建议命令"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.suggest.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "suggest", "test"]):
            result = main()

        assert result == 0
        mock_cli.suggest.assert_called_once_with("test", 5)

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_history_command(self, mock_cli_class):
        """测试历史命令"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.history.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "history"]):
            result = main()

        assert result == 0
        mock_cli.history.assert_called_once_with(10)

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_clear_command(self, mock_cli_class):
        """测试清空命令"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.clear_history.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "clear"]):
            result = main()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_export_command(self, mock_cli_class):
        """测试导出命令"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.export_results.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "export", "query", "output.json"]):
            result = main()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_suggest_insufficient_args(self, mock_cli_class):
        """测试建议命令缺少参数"""
        from ai_collab.cli.context_search import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["context_search.py", "suggest"]):
            result = main()

        assert result == 1


class TestContextSearchCLIEdgeCases:
    """测试边缘情况"""

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_search_multiple_results(self, mock_aggregator_class, mock_engine_class):
        """测试多个搜索结果"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        results = []
        for i in range(5):
            mock_r = MagicMock()
            mock_r.context_id = f"ctx_{i}"
            mock_r.score = 0.9 - (i * 0.1)
            mock_r.relevance = ["high", "medium", "low"][min(i, 2)]
            mock_r.content = f"Result content {i}"
            mock_r.matches = ["keyword"]
            results.append(mock_r)

        mock_stats = MagicMock()
        mock_stats.method = MagicMock(value="semantic")
        mock_stats.scope = MagicMock(value="all")
        mock_stats.total_results = 5
        mock_stats.filtered_results = 0

        mock_engine.search.return_value = (results, mock_stats)
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.search("multi results query", limit=5)

        assert_success(result)

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_search.ContextAggregator")
    def test_search_filtered_results(self, mock_aggregator_class, mock_engine_class):
        """测试有过滤结果的情况"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_result.context_id = "ctx_filtered"
        mock_result.score = 0.8
        mock_result.relevance = "high"
        mock_result.content = "High score result"
        mock_result.matches = []

        mock_stats = MagicMock()
        mock_stats.total_results = 10
        mock_stats.filtered_results = 5
        mock_stats.method = MagicMock(value="semantic")
        mock_stats.scope = MagicMock(value="all")

        mock_engine.search.return_value = ([mock_result], mock_stats)
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        result = cli.search("test", min_score=0.5)

        assert_success(result)


class TestContextSearchCLIExportResults:
    """测试 export_results 方法"""

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_export_results_json(self, mock_aggregator_class, mock_engine_class, tmp_path):
        """测试导出为 JSON"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_result = MagicMock()
        mock_result.context_id = "ctx_123"
        mock_result.content = "Test content"
        mock_result.score = 0.95
        mock_result.relevance = "high"
        mock_result.matches = ["test"]
        mock_result.metadata = {"source": "test"}

        mock_engine = MagicMock()
        mock_stats = MagicMock()
        mock_stats.method = MagicMock(value="semantic")
        mock_stats.scope = MagicMock(value="all")
        mock_stats.total_results = 1

        mock_engine.search.return_value = ([mock_result], mock_stats)
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        output_file = tmp_path / "output.json"
        result = cli.export_results("test query", str(output_file))

        assert result == 0
        assert output_file.exists()
        mock_engine.search.assert_called_once_with("test query")

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_export_results_non_json(self, mock_aggregator_class, mock_engine_class, tmp_path):
        """测试非 JSON 文件自动转换为 JSON"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        mock_engine = MagicMock()
        mock_engine.search.return_value = (
            [],
            MagicMock(
                method=MagicMock(value="semantic"), scope=MagicMock(value="all"), total_results=0
            ),
        )
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        output_file = tmp_path / "output.txt"
        result = cli.export_results("test query", str(output_file))
        json_file = output_file.with_suffix(".json")

        assert result == 0
        assert json_file.exists()
        assert not output_file.exists()  # Original filename not used

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    def test_export_results_multiple_items(
        self, mock_aggregator_class, mock_engine_class, tmp_path
    ):
        """测试导出多个结果"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator

        results = []
        for i in range(5):
            r = MagicMock()
            r.context_id = f"ctx_{i}"
            r.content = f"Content {i}"
            r.score = 0.9 - (i * 0.1)
            r.relevance = "high"
            r.matches = []
            r.metadata = {}
            results.append(r)

        mock_engine = MagicMock()
        mock_stats = MagicMock()
        mock_stats.method = MagicMock(value="semantic")
        mock_stats.scope = MagicMock(value="all")
        mock_stats.total_results = 5

        mock_engine.search.return_value = (results, mock_stats)
        mock_engine_class.return_value = mock_engine

        cli = ContextSearchCLI()
        output_file = tmp_path / "multi_output.json"
        result = cli.export_results("test query", str(output_file))

        assert result == 0
        assert output_file.exists()


class TestContextSearchCLIMainWithOptions:
    """测试 main() 选项解析"""

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_search_with_method_option(self, mock_cli_class):
        """测试搜索命令带 --method 选项"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.search.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "search", "query", "--method", "keyword"]):
            result = main()

        assert result == 0
        mock_cli.search.assert_called_once_with("query", method="keyword")

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_search_with_scope_option(self, mock_cli_class):
        """测试搜索命令带 --scope 选项"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.search.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "search", "query", "--scope", "recent"]):
            result = main()

        assert result == 0
        mock_cli.search.assert_called_once_with("query", scope="recent")

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_search_with_limit_option(self, mock_cli_class):
        """测试搜索命令带 --limit 选项"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.search.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "search", "query", "--limit", "20"]):
            result = main()

        assert result == 0
        mock_cli.search.assert_called_once_with("query", limit="20")

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_search_with_min_score_option(self, mock_cli_class):
        """测试搜索命令带 --min-score 选项"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.search.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "search", "query", "--min-score", "0.8"]):
            result = main()

        assert result == 0
        mock_cli.search.assert_called_once_with("query", min_score="0.8")

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_search_with_multiple_options(self, mock_cli_class):
        """测试搜索命令带多个选项"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.search.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch(
            "sys.argv",
            [
                "context_search.py",
                "search",
                "query",
                "--method",
                "semantic",
                "--scope",
                "all",
                "--limit",
                "10",
            ],
        ):
            result = main()

        assert result == 0
        mock_cli.search.assert_called_once_with("query", method="semantic", scope="all", limit="10")

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_suggest_with_limit_option(self, mock_cli_class):
        """测试建议命令带 --limit 选项"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.suggest.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "suggest", "test", "--limit", "10"]):
            result = main()

        assert result == 0
        mock_cli.suggest.assert_called_once_with("test", 10)

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_history_with_count_option(self, mock_cli_class):
        """测试历史命令带 --count 选项"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.history.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "history", "--count", "20"]):
            result = main()

        assert result == 0
        mock_cli.history.assert_called_once_with(20)

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_export_with_options(self, mock_cli_class):
        """测试导出命令带选项"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.export_results.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch(
            "sys.argv",
            ["context_search.py", "export", "query", "output.json", "--method", "semantic"],
        ):
            result = main()

        assert result == 0
        mock_cli.export_results.assert_called_once_with("query", "output.json", method="semantic")

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_export_insufficient_args(self, mock_cli_class):
        """测试导出命令缺少参数"""
        from ai_collab.cli.context_search import main

        mock_cli_class.return_value = MagicMock()

        with patch("sys.argv", ["context_search.py", "export", "query"]):
            result = main()

        assert result == 1


class TestContextSearchCLIInteractive:
    """测试 interactive() 方法"""

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_quit(self, mock_input, mock_aggregator_class, mock_engine_class):
        """测试交互模式退出 - lines 225-237"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        # Simulate user typing 'quit'
        mock_input.return_value = "quit"

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_exit(self, mock_input, mock_aggregator_class, mock_engine_class):
        """测试交互模式 exit 命令"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_input.return_value = "exit"

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_help(self, mock_input, mock_aggregator_class, mock_engine_class):
        """测试交互模式 help 命令 - lines 239-250"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        # help then quit
        mock_input.side_effect = ["help", "quit"]

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_empty_input(self, mock_input, mock_aggregator_class, mock_engine_class):
        """测试交互模式空输入 - lines 232-233"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        # empty then quit
        mock_input.side_effect = ["", "quit"]

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_method_command(self, mock_input, mock_aggregator_class, mock_engine_class):
        """测试 /method 命令 - lines 257-263"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_input.side_effect = ["/method semantic", "quit"]

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_invalid_method(self, mock_input, mock_aggregator_class, mock_engine_class):
        """测试无效 method - line 263"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_input.side_effect = ["/method invalid_method", "quit"]

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_scope_command(self, mock_input, mock_aggregator_class, mock_engine_class):
        """测试 /scope 命令 - lines 264-270"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_input.side_effect = ["/scope recent", "quit"]

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_invalid_scope(self, mock_input, mock_aggregator_class, mock_engine_class):
        """测试无效 scope - line 270"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_input.side_effect = ["/scope invalid_scope", "quit"]

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_limit_command(self, mock_input, mock_aggregator_class, mock_engine_class):
        """测试 /limit 命令 - lines 271-274"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_input.side_effect = ["/limit 20", "quit"]

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_suggest_command(
        self, mock_input, mock_aggregator_class, mock_engine_class
    ):
        """测试 /suggest 命令 - lines 275-277"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine.suggest.return_value = ["suggestion1", "suggestion2"]
        mock_engine_class.return_value = mock_engine

        mock_input.side_effect = ["/suggest test", "quit"]

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_history_command(
        self, mock_input, mock_aggregator_class, mock_engine_class
    ):
        """测试 /history 命令 - lines 278-279"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine.get_search_history.return_value = []
        mock_engine_class.return_value = mock_engine

        mock_input.side_effect = ["/history", "quit"]

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_clear_command(self, mock_input, mock_aggregator_class, mock_engine_class):
        """测试 /clear 命令 - lines 280-281"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_input.side_effect = ["/clear", "quit"]

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_unknown_command(
        self, mock_input, mock_aggregator_class, mock_engine_class
    ):
        """测试未知命令 - lines 282-284"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_input.side_effect = ["/unknown", "quit"]

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_search_query(self, mock_input, mock_aggregator_class, mock_engine_class):
        """测试搜索查询 - lines 285-292"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_result = MagicMock()
        mock_result.context_id = "ctx_123"
        mock_result.score = 0.95
        mock_result.relevance = "high"
        mock_result.content = "Test content"
        mock_result.matches = ["test"]
        mock_engine.search.return_value = (
            [mock_result],
            MagicMock(
                method=MagicMock(value="semantic"),
                scope=MagicMock(value="all"),
                total_results=1,
                filtered_results=0,
            ),
        )
        mock_engine_class.return_value = mock_engine

        mock_input.side_effect = ["test query", "quit"]

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_keyboard_interrupt(
        self, mock_input, mock_aggregator_class, mock_engine_class
    ):
        """测试 KeyboardInterrupt - lines 294-296"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_input.side_effect = KeyboardInterrupt()

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0

    @patch("ai_collab.cli.context_search.ContextSearchEngine")
    @patch("ai_collab.cli.context_aggregator.ContextAggregator")
    @patch("builtins.input")
    def test_interactive_eof_error(self, mock_input, mock_aggregator_class, mock_engine_class):
        """测试 EOFError - lines 297-299"""
        from ai_collab.cli.context_search import ContextSearchCLI

        mock_aggregator = MagicMock()
        mock_aggregator_class.return_value = mock_aggregator
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine

        mock_input.side_effect = EOFError()

        cli = ContextSearchCLI()
        result = cli.interactive()

        assert result == 0


class TestContextSearchCLIMainInteractive:
    """测试 main() interactive 命令"""

    @patch("ai_collab.cli.context_search.ContextSearchCLI")
    def test_main_interactive_command(self, mock_cli_class):
        """测试 interactive 命令 - line 410"""
        from ai_collab.cli.context_search import main

        mock_cli = MagicMock()
        mock_cli.interactive.return_value = 0
        mock_cli_class.return_value = mock_cli

        with patch("sys.argv", ["context_search.py", "interactive"]):
            result = main()

        assert result == 0
        mock_cli.interactive.assert_called_once()
