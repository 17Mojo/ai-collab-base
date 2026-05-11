# Context Aggregator CLI Module
# Week 4 Day 1: 上下文聚合器 CLI (修复版 v3)

"""
上下文聚合器 CLI 命令
支持添加上下文、聚合、查看状态
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import Optional

from ai_collab.context.aggregator import ContextAggregator


class ContextAggregatorCLI:
    """上下文聚合器 CLI"""

    def __init__(self):
        """初始化 CLI"""
        self.aggregator = ContextAggregator()

    def add_context(self, source: str, content: str, confidence: float = 0.7) -> int:
        """添加上下文

        Args:
            source: 来源类型 (api/file/notebooklm)
            content: 内容
            confidence: 置信度 (0.0-1.0)

        Returns:
            退出码 (0=成功, 1=失败)
        """
        print(f"Adding context from {source}...")

        # 验证置信度
        if not 0.0 <= confidence <= 1.0:
            print(f"✗ Confidence must be between 0 and 1, got {confidence}")
            return 1

        try:
            context_id = self.aggregator.extract_knowledge(
                source_type=source, content=content, confidence=confidence
            )

            print(f"✓ Context added: {context_id.source_id}")
            return 0
        except ValueError as e:
            print(f"✗ Failed to add context: {e}")
            return 1

    def aggregate(
        self, query: str, source_type: Optional[str] = None, strategy: str = "weighted"
    ) -> int:
        """聚合上下文

        Args:
            query: 查询内容
            source_type: 来源类型过滤
            strategy: 聚合策略

        Returns:
            退出码
        """
        print(f"Aggregating context for query: {query}...")

        # 创建上下文
        try:
            self.aggregator.list_contexts()

            # 聚合现有的知识源
            sources = list(self._get_all_sources())

            if not sources:
                print("✗ No sources to aggregate")
                return 1

            # 合并知识
            result = self.aggregator.merge_knowledge(sources=sources, strategy=strategy)

            # 创建上下文记录
            context_id = self.aggregator.create_context(
                query=query, sources=[s.source_id for s in sources]
            )

            print(f"\n{'='*60}")
            print(f"Aggregated Context: {context_id}")
            print(f"{'='*60}\n")
            print(f"Query: {query}")
            print(f"Sources: {len(result.sources)}")
            print(f"Content:\n{result.content}\n")

            return 0
        except Exception as e:
            print(f"✗ Aggregation failed: {e}")
            return 1

    def status(self) -> int:
        """查看状态

        Returns:
            退出码
        """
        sources = list(self._get_all_sources())

        print(f"\n{'='*60}")
        print("Context Aggregator Status")
        print(f"{'='*60}\n")

        print(f"Total Knowledge Items: {len(sources)}")

        # 来源统计
        source_stats = {}
        for source in sources:
            if source.source_type not in source_stats:
                source_stats[source.source_type] = 0
            source_stats[source.source_type] += 1

        print("\nSource Statistics:")
        for source_type, count in source_stats.items():
            high_conf = sum(
                1 for s in sources if s.source_type == source_type and s.confidence >= 0.7
            )
            print(f"  {source_type}:")
            print(f"    Total: {count}")
            print(f"    High Confidence: {high_conf}")

        print(f"\n{'='*60}\n")

        # 显示历史
        history = self.aggregator.get_history()
        if history:
            print(f"Recent Contexts (last {len(history)}):")
            for ctx in history:
                print(f"  - {ctx.context_id}: {ctx.query}")

        print(f"\n{'='*60}\n")

        return 0

    def list_history(self, limit: int = 10) -> int:
        """列出历史记录

        Args:
            limit: 返回数量

        Returns:
            退出码
        """
        history = self.aggregator.get_history(limit)

        print(f"\n{'='*60}")
        print(f"Context History (last {len(history)})")
        print(f"{'='*60}\n")

        if not history:
            print("No history found.")
            return 0

        for i, ctx in enumerate(history, 1):
            print(f"{i}. {ctx.context_id}")
            print(f"   Query: {ctx.query}")
            print(f"   Sources: {len(ctx.sources)}")
            print(f"   Created: {ctx.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print()

        print(f"{'='*60}\n")

        return 0

    def add_from_file(self, file_path: str, source: str = "file", confidence: float = 0.6) -> int:
        """从文件添加上下文

        Args:
            file_path: 文件路径
            source: 来源类型
            confidence: 置信度

        Returns:
            退出码
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            print(f"✗ File not found: {file_path}")
            return 1
        except IOError as e:
            print(f"✗ Failed to read file: {e}")
            return 1

        return self.add_context(source, content, confidence)

    def export_context(self, context_id: Optional[str] = None) -> int:
        """导出上下文

        Args:
            context_id: 上下文 ID，不提供则导出最新

        Returns:
            退出码
        """
        history = self.aggregator.get_history()

        if not history:
            print("✗ No contexts to export")
            return 1

        # 获取目标上下文
        if context_id:
            target = next((ctx for ctx in history if ctx.context_id == context_id), None)
            if not target:
                print(f"✗ Context not found: {context_id}")
                return 1
        else:
            target = history[-1]

        # 导出
        output = {
            "context_id": target.context_id,
            "created_at": target.created_at.isoformat(),
            "query": target.query,
            "sources": len(target.sources),
            "content": target.result.to_dict() if target.result else None,
        }

        output_path = f"exported_{target.context_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        print(f"✓ Context exported to: {output_path}")
        return 0

    def _get_all_sources(self):
        """获取所有源"""
        if hasattr(self.aggregator, "sources"):
            return self.aggregator.sources
        elif hasattr(self.aggregator.aggregator, "sources"):
            return self.aggregator.aggregator.sources
        else:
            return []


def main():
    """CLI 入口"""
    if len(sys.argv) < 2:
        print("Usage: context_aggregator.py <command> [options]")
        print("Commands:")
        print("  add --source <type> --content <text> [--confidence <0.0-1.0>]")
        print("  add-file --path <file> [--source <type>] [--confidence <0.0-1.0>]")
        print("  aggregate --query <text> [--strategy <type>]")
        print("  status")
        print("  history [--limit <num>]")
        print("  export [--context-id <id>]")
        return 1

    command = sys.argv[1]
    cli = ContextAggregatorCLI()

    if command == "add":
        source = None
        content = None
        confidence = 0.7

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--source" and i + 1 < len(sys.argv):
                source = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--content" and i + 1 < len(sys.argv):
                content = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--confidence" and i + 1 < len(sys.argv):
                confidence = float(sys.argv[i + 1])
                i += 2
            else:
                i += 1

        if not source or not content:
            print(
                "Usage: context_aggregator.py add "
                "--source <type> --content <text> [--confidence <value>]"
            )
            return 1

        return cli.add_context(source, content, confidence)

    if command == "add-file":
        file_path = None
        source = "file"
        confidence = 0.6

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--path" and i + 1 < len(sys.argv):
                file_path = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--source" and i + 1 < len(sys.argv):
                source = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--confidence" and i + 1 < len(sys.argv):
                confidence = float(sys.argv[i + 1])
                i += 2
            else:
                i += 1

        if not file_path:
            print(
                "Usage: context_aggregator.py add-file "
                "--path <file> [--source <type>] [--confidence <value>]"
            )
            return 1

        return cli.add_from_file(file_path, source, confidence)

    if command == "aggregate":
        query = None
        strategy = "weighted"

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--query" and i + 1 < len(sys.argv):
                query = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--strategy" and i + 1 < len(sys.argv):
                strategy = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        if not query:
            print("Usage: context_aggregator.py aggregate --query <text>")
            return 1

        return cli.aggregate(query, strategy=strategy)

    if command == "status":
        return cli.status()

    if command == "history":
        limit = 10
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
                i += 2
            else:
                i += 1

        return cli.list_history(limit)

    if command == "export":
        context_id = None
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--context-id" and i + 1 < len(sys.argv):
                context_id = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        return cli.export_context(context_id)

    print(f"Unknown command: {command}")
    print("Available commands: add, add-file, aggregate, status, history, export")
    return 1


if __name__ == "__main__":
    sys.exit(main())
