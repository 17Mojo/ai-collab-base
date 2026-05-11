# Pack Rating CLI Module
# Week 2 Day 2: Pack 评价系统 CLI

"""
Pack 评价 CLI 命令
支持添加、查看、删除评价
"""

import sys
from pathlib import Path
from typing import Optional

from ai_collab.pack.market_api import PackMarketAPI


class PackRatingCLI:
    """Pack 评价 CLI"""

    def __init__(self, db_path: str = "data/packs.db"):
        """初始化 CLI

        Args:
            db_path: 数据库路径
        """
        self.api = PackMarketAPI(db_path)
        self._ensure_db_dir()

    def _ensure_db_dir(self) -> None:
        """确保数据库目录存在"""
        Path("data").mkdir(exist_ok=True)

    def add_rating(
        self,
        pack_id: str,
        score: int,
        title: str,
        content: Optional[str] = None,
        user_id: str = "default_user",
    ) -> int:
        """添加评价

        Args:
            pack_id: Pack ID
            score: 评分 (1-5)
            title: 标题
            content: 内容 (可选)
            user_id: 用户 ID

        Returns:
            退出码 (0=成功, 1=失败)
        """
        print(f"Adding rating for pack: {pack_id}")
        print(f"Score: {score}/5")
        print(f"Title: {title}")
        if content:
            print(f"Content: {content[:50]}..." if len(content) > 50 else f"Content: {content}")

        result = self.api.rate_pack(pack_id, user_id, score, title, content or "")

        if result["success"]:
            print(f"✓ Rating added successfully! Rating ID: {result['rating_id']}")
            return 0
        else:
            print(f"✗ Failed to add rating: {result.get('error', 'Unknown error')}")
            return 1

    def get_rating(self, pack_id: str) -> int:
        """获取 Pack 评分信息

        Args:
            pack_id: Pack ID

        Returns:
            退出码
        """
        result = self.api.get_pack(pack_id)

        if not result["success"]:
            print(f"✗ Pack not found: {pack_id}")
            return 1

        pack = result["pack"]

        print(f"\n{'='*60}")
        print(f"Pack: {pack['pack_name']} (v{pack['version']})")
        print(f"{'='*60}")
        print(f"Average Rating: {pack['rating']:.1f}/5.0")
        print(f"Total Ratings: {pack['rating_count']}")
        print(f"Downloads: {pack['downloads']}")
        print(f"Status: {pack['status']}")
        print(f"{'='*60}\n")

        # 获取详细评分分布
        ratings = self.api.list_pack_ratings(pack_id)

        if ratings["success"] and ratings["count"] > 0:
            distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

            for r in ratings["ratings"]:
                distribution[r["rating"]] += 1

            print("Rating Distribution:")
            print("-" * 60)
            for stars in range(5, 0, -1):
                count = distribution[stars]
                bar = "█" * count
                print(f"  {stars} ★: {bar} ({count})")
            print("-" * 60)

        return 0

    def list_reviews(self, pack_id: str, limit: int = 10, detailed: bool = False) -> int:
        """列出 Pack 评价

        Args:
            pack_id: Pack ID
            limit: 限制数量
            detailed: 显示详细信息

        Returns:
            退出码
        """
        result = self.api.list_pack_ratings(pack_id, limit)

        if not result["success"]:
            print(f"✗ Failed to get reviews: {result.get('error', 'Unknown error')}")
            return 1

        reviews = result["ratings"]

        if not reviews:
            print(f"No reviews found for pack: {pack_id}")
            return 0

        print(f"\n{'='*60}")
        print(f"Reviews for Pack: {pack_id}")
        print(f"Showing {len(reviews)} review(s)")
        print(f"{'='*60}\n")

        for i, review in enumerate(reviews, 1):
            stars = "★" * review["rating"]
            print(f"\n[{i}] {review['rating']}/5 {stars}")
            print(f"    User: {review['user_id']}")
            print(f"    Date: {review['created_at'][:10]}")

            if detailed and review.get("title"):
                print(f"    Title: {review['title']}")
            if detailed and review.get("content"):
                content = review["content"]
                if len(content) > 200:
                    content = content[:200] + "..."
                print(f"    Content: {content}")

            if not detailed and (review.get("title") or review.get("content")):
                summary = review.get("title", review.get("content", ""))[:60]
                if summary:
                    print(f"    Summary: {summary}...")

        print(f"\n{'='*60}\n")

        return 0

    def delete_rating(self, rating_id: str, user_id: str = "default_user") -> int:
        """删除评价

        Args:
            rating_id: 评价 ID
            user_id: 用户 ID (用于验证权限)

        Returns:
            退出码
        """
        result = self.api.get_rating(rating_id)

        if not result["success"]:
            print(f"✗ Rating not found: {rating_id}")
            return 1

        rating = result["rating"]

        # 权限检查
        if rating["user_id"] != user_id:
            print("✗ Permission denied: You can only delete your own ratings")
            print(f"  Rating owner: {rating['user_id']}")
            return 1

        print(f"Deleting rating: {rating_id}")
        print(f"Pack: {rating['pack_id']}")
        print(f"Score: {rating['rating']}/5")

        # API 没有 delete_rating 方法，使用 store 直接操作
        from ai_collab.pack.market_store import PackMarketStore

        store = PackMarketStore("data/packs.db")
        success = store.delete_rating(rating_id)

        if success:
            print("✓ Rating deleted successfully")
            return 0
        else:
            print("✗ Failed to delete rating")
            return 1

    def stats(self, pack_id: str = None) -> int:
        """获取评分统计信息

        Args:
            pack_id: 可选，指定 Pack ID

        Returns:
            退出码
        """
        if pack_id:
            return self.get_rating(pack_id)

        # 全局市场统计
        result = self.api.get_market_stats()

        if result["success"]:
            stats = result["stats"]
            print(f"\n{'='*60}")
            print("Pack Market Statistics")
            print(f"{'='*60}")
            print(f"Total Packs: {stats['total_packs']}")
            print(f"Pending Review: {stats['pending_packs']}")
            print(f"Total Downloads: {stats['total_downloads']}")
            print(f"Average Rating: {stats['average_rating']:.1f}/5.0")
            print(f"{'='*60}\n")
            return 0

        return 1


def main():
    """CLI 入口"""
    if len(sys.argv) < 2:
        print("Usage: pack_rating.py <command> [options]")
        print("Commands: add, get, list, delete, stats")
        return 1

    command = sys.argv[1]
    cli = PackRatingCLI()

    if command == "add":
        if len(sys.argv) < 5:
            print("Usage: pack_rating.py add <pack_id> <score> <title> [content]")
            return 1

        pack_id = sys.argv[2]
        score = int(sys.argv[3])
        title = sys.argv[4]
        content = sys.argv[5] if len(sys.argv) > 5 else None

        return cli.add_rating(pack_id, score, title, content)

    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: pack_rating.py get <pack_id>")
            return 1

        pack_id = sys.argv[2]
        return cli.get_rating(pack_id)

    elif command == "list":
        if len(sys.argv) < 3:
            print("Usage: pack_rating.py list <pack_id> [--limit N] [--detailed]")
            return 1

        pack_id = sys.argv[2]
        limit = 10
        detailed = False

        for i, arg in enumerate(sys.argv[3:], 3):
            if arg == "--limit" and i + 1 < len(sys.argv):
                limit = int(sys.argv[i + 1])
            elif arg == "--detailed":
                detailed = True

        return cli.list_reviews(pack_id, limit, detailed)

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: pack_rating.py delete <rating_id>")
            return 1

        rating_id = sys.argv[2]
        return cli.delete_rating(rating_id)

    elif command == "stats":
        pack_id = sys.argv[2] if len(sys.argv) > 2 else None
        return cli.stats(pack_id)

    else:
        print(f"Unknown command: {command}")
        print("Available commands: add, get, list, delete, stats")
        return 1


if __name__ == "__main__":
    sys.exit(main())
