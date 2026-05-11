# Context Search CLI Module
# Week 3 Day 3: 智能上下文搜索 CLI

"""
上下文搜索 CLI 命令
支持语义搜索、关键词搜索、混合搜索、图谱搜索
"""

import json
import sys
from pathlib import Path

from ai_collab.context.aggregator import ContextAggregator
from ai_collab.context.search import ContextSearchEngine, SearchMethod, SearchScope


class ContextSearchCLI:
    """上下文搜索 CLI"""

    def __init__(self, db_path: str = "data/packs.db"):
        """初始化 CLI

        Args:
            db_path: 数据库路径
        """
        self.aggregator = ContextAggregator()
        self.search_engine = ContextSearchEngine(self.aggregator)

    def search(self, query: str, **kwargs) -> int:
        """执行搜索

        Args:
            query: 搜索查询
            **kwargs: 额外参数

        Returns:
            退出码
        """
        print(f"Searching for: {query}")
        print(f"{'='*60}\n")

        # 解析参数
        method = kwargs.get("method", "semantic")
        scope = kwargs.get("scope", "all")
        limit = int(kwargs.get("limit", 10))
        min_score = float(kwargs.get("min_score", 0.3))

        # 转换为枚举
        try:
            search_method = SearchMethod(method)
        except ValueError:
            print(f"✗ Invalid method: {method}")
            print(f"Valid methods: {[m.value for m in SearchMethod]}")
            return 1

        try:
            search_scope = SearchScope(scope)
        except ValueError:
            print(f"✗ Invalid scope: {scope}")
            print(f"Valid scopes: {[s.value for s in SearchScope]}")
            return 1

        # 执行搜索
        results, stats = self.search_engine.search(
            query, method=search_method, scope=search_scope, limit=limit, min_score=min_score
        )

        # 显示统计信息
        print(f"Method: {stats.method.value}")
        print(f"Scope: {stats.scope.value}")
        print(f"Total results: {stats.total_results}")
        print(f"Filtered out: {stats.filtered_results}")
        print(f"\n{'='*60}\n")

        # 显示结果
        if not results:
            print("No results found.")
            return 0

        for i, result in enumerate(results, 1):
            relevance_emoji = {"very_high": "🔥", "high": "🟢", "medium": "🟡", "low": "🔵"}.get(
                result.relevance, "⚪"
            )

            print(f"{i}. [{result.context_id}] {relevance_emoji} {result.score:.2f}")
            print(f"   {result.content[:100]}{'...' if len(result.content) > 100 else ''}")
            if result.matches:
                print(f"   Matches: {', '.join(result.matches)}")
            print()

        print(f"{'='*60}\n")
        return 0

    def suggest(self, partial: str, limit: int = 5) -> int:
        """建议查询词

        Args:
            partial: 部分查询
            limit: 返回数量

        Returns:
            退出码
        """
        print(f"Suggestions for '{partial}':\n")

        suggestions = self.search_engine.suggest(partial, limit)

        if not suggestions:
            print("No suggestions found.")
            return 0

        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")

        print()
        return 0

    def history(self, count: int = 10) -> int:
        """显示搜索历史

        Args:
            count: 显示数量

        Returns:
            退出码
        """
        search_history = self.search_engine.get_search_history()

        print(f"\nSearch History (Last {min(count, len(search_history))}):\n")
        print(f"{'='*60}\n")

        if not search_history:
            print("No search history available.")
            return 0

        for i, stats in enumerate(search_history[-count:], 1):
            print(f"{i}. Method: {stats.method.value}, Scope: {stats.scope.value}")
            print(f"   Results: {stats.total_results}, Time: {stats.execution_time_ms:.2f}ms")

        print(f"\n{'='*60}\n")
        return 0

    def clear_history(self) -> int:
        """清空搜索历史

        Returns:
            退出码
        """
        self.search_engine.clear_history()
        print("Search history cleared.")
        return 0

    def export_results(self, query: str, output_file: str, **kwargs) -> int:
        """导出搜索结果

        Args:
            query: 搜索查询
            output_file: 输出文件路径
            **kwargs: 额外参数

        Returns:
            退出码
        """
        print(f"Exporting search results for '{query}' to {output_file}...")

        # 执行搜索
        results, stats = self.search_engine.search(query, **kwargs)

        # 准备导出数据
        export_data = {
            "query": query,
            "method": stats.method.value,
            "scope": stats.scope.value,
            "total_results": stats.total_results,
            "results": [
                {
                    "context_id": r.context_id,
                    "content": r.content,
                    "score": r.score,
                    "relevance": r.relevance,
                    "matches": r.matches,
                    "metadata": r.metadata,
                }
                for r in results
            ],
        }

        # 写入文件
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix == ".json":
            output_path.write_text(
                json.dumps(export_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        else:
            # JSON 格式
            output_path = output_path.with_suffix(".json")
            output_path.write_text(
                json.dumps(export_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )

        print(f"✓ Exported {stats.total_results} results to {output_path}")
        return 0

    def interactive(self) -> int:
        """交互式搜索模式

        Returns:
            退出码
        """
        print("Context Search - Interactive Mode")
        print("Type 'help' for commands, 'quit' to exit\n")

        while True:
            try:
                user_input = input("search> ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    return 0

                if user_input.lower() == "help":
                    print("\nCommands:")
                    print("  <query>                    - Search with default settings")
                    print("  /method <semantic|...>      - Set search method")
                    print("  /scope <all|...>           - Set search scope")
                    print("  /limit <number>            - Set result limit")
                    print("  /suggest <partial>         - Get suggestions")
                    print("  /history                   - Show search history")
                    print("  /clear                     - Clear history")
                    print("  /help                      - Show this help")
                    print("  /quit                      - Exit\n")
                    continue

                if user_input.startswith("/"):
                    # 命令处理
                    parts = user_input.split()
                    cmd = parts[0].lower()

                    if cmd == "/method" and len(parts) > 1:
                        method = parts[1]
                        if method in [m.value for m in SearchMethod]:
                            self._current_method = SearchMethod(method)
                            print(f"Method changed to: {method}")
                        else:
                            print(f"Invalid method: {method}")
                    elif cmd == "/scope" and len(parts) > 1:
                        scope = parts[1]
                        if scope in [s.value for s in SearchScope]:
                            self._current_scope = SearchScope(scope)
                            print(f"Scope changed to: {scope}")
                        else:
                            print(f"Invalid scope: {scope}")
                    elif cmd == "/limit" and len(parts) > 1:
                        limit = int(parts[1])
                        self._current_limit = limit
                        print(f"Limit changed to: {limit}")
                    elif cmd == "/suggest" and len(parts) > 1:
                        partial = " ".join(parts[1:])
                        self.suggest(partial)
                    elif cmd == "/history":
                        self.history()
                    elif cmd == "/clear":
                        self.clear_history()
                    else:
                        print(f"Unknown command: {cmd}")
                        print("Type 'help' for commands")
                else:
                    # 搜索查询
                    self.search(
                        user_input,
                        method=getattr(self, "_current_method", SearchMethod.SEMANTIC).value,
                        scope=getattr(self, "_current_scope", SearchScope.ALL).value,
                        limit=getattr(self, "_current_limit", 10),
                    )

            except KeyboardInterrupt:
                print("\nGoodbye!")
                return 0
            except EOFError:
                print("\nGoodbye!")
                return 0
            except Exception as e:
                print(f"Error: {e}")

        return 0


def main():
    """CLI 入口"""
    if len(sys.argv) < 2:
        print("Usage: context_search.py <command> [options]")
        print("Commands:")
        print("  search <query> [--method <m>] [--scope <s>] [--limit <n>] [--min-score <x>]")
        print("  suggest <partial> [--limit <n>]")
        print("  history [--count <n>]")
        print("  clear")
        print("  export <query> <output_file> [search options]")
        print("  interactive")
        return 1

    command = sys.argv[1]
    cli = ContextSearchCLI()

    if command == "search":
        if len(sys.argv) < 3:
            print("Usage: context_search.py search <query> [options]")
            return 1

        query = sys.argv[2]
        kwargs = {}

        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--method" and i + 1 < len(sys.argv):
                kwargs["method"] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--scope" and i + 1 < len(sys.argv):
                kwargs["scope"] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                kwargs["limit"] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--min-score" and i + 1 < len(sys.argv):
                kwargs["min_score"] = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        return cli.search(query, **kwargs)

    elif command == "suggest":
        if len(sys.argv) < 3:
            print("Usage: context_search.py suggest <partial> [--limit <n>]")
            return 1

        partial = sys.argv[2]
        limit = 5
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
                i += 2
            else:
                i += 1

        return cli.suggest(partial, limit)

    elif command == "history":
        count = 10
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--count" and i + 1 < len(sys.argv):
                count = int(sys.argv[i + 1])
                i += 2
            else:
                i += 1

        return cli.history(count)

    elif command == "clear":
        return cli.clear_history()

    elif command == "export":
        if len(sys.argv) < 4:
            print("Usage: context_search.py export <query> <output_file> [search options]")
            return 1

        query = sys.argv[2]
        output_file = sys.argv[3]
        kwargs = {}

        i = 4
        while i < len(sys.argv):
            if sys.argv[i] == "--method" and i + 1 < len(sys.argv):
                kwargs["method"] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--scope" and i + 1 < len(sys.argv):
                kwargs["scope"] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                kwargs["limit"] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--min-score" and i + 1 < len(sys.argv):
                kwargs["min_score"] = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        return cli.export_results(query, output_file, **kwargs)

    elif command == "interactive":
        return cli.interactive()

    else:
        print(f"Unknown command: {command}")
        print("Available commands: search, suggest, history, clear, export, interactive")
        return 1


if __name__ == "__main__":
    sys.exit(main())
