"""
Pack 评分和评价系统

实现 Pack 评分和评价功能：
- 提交评分
- 记录评价
- 评分统计
- 评论管理
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Review:
    """评价"""

    id: str
    pack_name: str
    user: str
    rating: int  # 1-5 星
    title: str
    content: str
    created_at: datetime
    helpful_count: int = 0

    def __post_init__(self):
        if not 1 <= self.rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "pack_name": self.pack_name,
            "user": self.user,
            "rating": self.rating,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "helpful_count": self.helpful_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Review":
        """从字典创建"""
        return cls(
            id=data["id"],
            pack_name=data["pack_name"],
            user=data["user"],
            rating=data["rating"],
            title=data["title"],
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
            helpful_count=data.get("helpful_count", 0),
        )


@dataclass
class RatingSummary:
    """评分摘要"""

    pack_name: str
    average_rating: float
    total_reviews: int
    rating_distribution: Dict[int, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "pack_name": self.pack_name,
            "average_rating": round(self.average_rating, 2),
            "total_reviews": self.total_reviews,
            "rating_distribution": self.rating_distribution,
        }


class RatingSystem:
    """评分系统"""

    def __init__(self, packs_root: str = ".", workspace: str = "."):
        """
        初始化评分系统

        Args:
            packs_root: Packs 根目录
            workspace: 工作区路径
        """
        from pathlib import Path

        self.packs_root = Path(workspace) / packs_root
        self.reviews_dir = self.packs_root / ".reviews"
        self.reviews_dir.mkdir(exist_ok=True)

    def _get_reviews_file(self, pack_name: str) -> Path:
        """获取 Pack 评价文件路径"""
        return self.reviews_dir / f"{pack_name}.json"

    def _load_reviews(self, pack_name: str) -> Dict[str, Review]:
        """加载 Pack 的所有评价"""
        reviews_file = self._get_reviews_file(pack_name)
        if not reviews_file.exists():
            return {}

        with open(reviews_file, "r", encoding="utf-8") as f:
            reviews_data = json.load(f)

        return {review_id: Review.from_dict(data) for review_id, data in reviews_data.items()}

    def _save_reviews(self, pack_name: str, reviews: Dict[str, Review]) -> None:
        """保存 Pack 的所有评价"""
        reviews_file = self._get_reviews_file(pack_name)

        with open(reviews_file, "w", encoding="utf-8") as f:
            reviews_data = {review_id: review.to_dict() for review_id, review in reviews.items()}
            json.dump(reviews_data, f, ensure_ascii=False, indent=2)

    def add_review(
        self, pack_name: str, user: str, rating: int, title: str, content: str
    ) -> Review:
        """
        添加评价

        Args:
            pack_name: Pack 名称
            user: 用户名
            rating: 评分（1-5）
            title: 评价标题
            content: 评价内容

        Returns:
            新创建的评价
        """
        # 检查用户是否已经评价过
        reviews = self._load_reviews(pack_name)
        for review in list(reviews.values()):
            if review.user == user:
                raise ValueError(f"User {user} has already reviewed {pack_name}")

        # 创建新评价
        timestamp = datetime.now()
        review_id = f"{pack_name}-{user}-{int(timestamp.timestamp())}"
        review = Review(
            id=review_id,
            pack_name=pack_name,
            user=user,
            rating=rating,
            title=title,
            content=content,
            created_at=timestamp,
        )

        # 保存评价
        reviews[review_id] = review
        self._save_reviews(pack_name, reviews)

        # 更新 Pack 索引中的评分（如果商店可用）
        if user == "default":
            try:
                from .store import PackRegistry

                registry = PackRegistry(self.packs_root)
                summary = self.get_rating_summary(pack_name)
                if summary.total_reviews > 0:
                    registry.update_pack_stats(
                        pack_name, rating=summary.average_rating, review_count=summary.total_reviews
                    )
            except Exception:
                # 忽略错误（商店可能不可用）
                pass

        return review

    def delete_review(self, pack_name: str, review_id: str, user: str) -> bool:
        """
        删除评价

        Args:
            pack_name: Pack 名称
            review_id: 评价 ID
            user: 用户名（用于权限验证）

        Returns:
            是否成功删除
        """
        reviews = self._load_reviews(pack_name)

        if review_id not in reviews:
            return False

        # 验证权限
        if reviews[review_id].user != user:
            return False

        # 删除评价
        del reviews[review_id]
        self._save_reviews(pack_name, reviews)

        # 更新 Pack 索引中的评分
        self._update_pack_rating(pack_name)

        return True

    def get_reviews(self, pack_name: str) -> List[Review]:
        """
        获取 Pack 的所有评价

        Args:
            pack_name: Pack 名称

        Returns:
            评价列表（按时间倒序）
        """
        reviews = self._load_reviews(pack_name)
        return sorted(reviews.values(), key=lambda r: r.created_at, reverse=True)

    def get_user_reviews(self, user: str) -> List[Review]:
        """
        获取用户的所有评价

        Args:
            user: 用户名

        Returns:
            评价列表（按时间倒序）
        """
        user_reviews = []

        for reviews_file in self.reviews_dir.glob("*.json"):
            pack_name = reviews_file.stem
            reviews = self._load_reviews(pack_name)

            for review in list(reviews.values()):
                if review.user == user:
                    user_reviews.append(review)

        return sorted(user_reviews, key=lambda r: r.created_at, reverse=True)

    def get_rating_summary(self, pack_name: str) -> RatingSummary:
        """
        获取 Pack 评分摘要

        Args:
            pack_name: Pack 名称

        Returns:
            评分摘要
        """
        reviews = self._load_reviews(pack_name)

        if not reviews:
            return RatingSummary(
                pack_name=pack_name, average_rating=0.0, total_reviews=0, rating_distribution={}
            )

        # 计算平均评分
        total_rating = sum(review.rating for review in reviews.values())
        average_rating = total_rating / len(reviews)

        # 计算评分分布
        rating_distribution = {}
        for review in reviews.values():
            rating_value = review.rating
            if rating_value not in rating_distribution:
                rating_distribution[rating_value] = 0
            rating_distribution[rating_value] += 1

        # 填充缺失的评分
        for i in range(1, 6):
            if i not in rating_distribution:
                rating_distribution[i] = 0

        return RatingSummary(
            pack_name=pack_name,
            average_rating=average_rating,
            total_reviews=len(reviews),
            rating_distribution=rating_distribution,
        )

    def mark_review_helpful(self, pack_name: str, review_id: str) -> bool:
        """
        标记评价为有帮助

        Args:
            pack_name: Pack 名称
            review_id: 评价 ID

        Returns:
            是否成功标记
        """
        reviews = self._load_reviews(pack_name)

        if review_id not in reviews:
            return False

        review = reviews[review_id]
        review.helpful_count += 1

        self._save_reviews(pack_name, reviews)
        return True

    def get_top_reviews(self, pack_name: str, limit: int = 10) -> List[Review]:
        """
        获取热门评价（按有用性排序）

        Args:
            pack_name: Pack 名称
            limit: 结果数量限制

        Returns:
            评价列表
        """
        reviews = self._load_reviews(pack_name)

        return sorted(reviews.values(), key=lambda r: (r.helpful_count, r.rating), reverse=True)[
            :limit
        ]

    def _update_pack_rating(self, pack_name: str) -> None:
        """
        更新 Pack 索引中的评分信息

        Args:
            pack_name: Pack 名称
        """
        try:
            from .store import PackRegistry

            registry = PackRegistry(self.packs_root)
            summary = self.get_rating_summary(pack_name)
            if summary.total_reviews > 0:
                registry.update_pack_stats(
                    pack_name, rating=summary.average_rating, review_count=summary.total_reviews
                )
        except Exception:
            # 忽略错误（商店可能不可用）
            pass

    def export_reviews(self, pack_name: str) -> Dict[str, Any]:
        """
        导出 Pack 评价数据

        Args:
            pack_name: Pack 名称

        Returns:
            评价数据字典
        """
        reviews = self._load_reviews(pack_name)
        summary = self.get_rating_summary(pack_name)

        return {
            "pack_name": pack_name,
            "summary": summary.to_dict(),
            "reviews": [review.to_dict() for review in reviews.values()],
        }

    def import_reviews(self, data: Dict[str, Any]) -> int:
        """
        导入 Pack 评价数据

        Args:
            data: 评价数据字典

        Returns:
            导入的评价数量
        """
        pack_name = data["pack_name"]
        imported_count = 0

        reviews = self._load_reviews(pack_name)

        for review_data in data.get("reviews", []):
            try:
                review = Review.from_dict(review_data)
                reviews[review.id] = review
                imported_count += 1
            except (KeyError, ValueError):
                continue

        self._save_reviews(pack_name, reviews)
        self._update_pack_rating(pack_name)

        return imported_count


def create_rating_system(packs_root: str = ".", workspace: str = ".") -> RatingSystem:
    """
    创建评分系统

    Args:
        packs_root: Packs 根目录
        workspace: 工作区路径

    Returns:
        RatingSystem 实例
    """
    return RatingSystem(packs_root, workspace)
