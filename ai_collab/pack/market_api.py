# Pack Market API
# Track A Day 1: Pack 市场管理接口

"""
Pack 市场管理接口
提供 RESTful API 风格的管理功能
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .market import PackListing, PackRating, PackStatus, UserFeedback
from .market_store import PackMarketStore


class PackMarketAPI:
    """Pack 市场 API"""

    def __init__(self, db_path: str = "data/packs.db"):
        """初始化 API

        Args:
            db_path: SQLite 数据库路径
        """
        self.store = PackMarketStore(db_path)

    # ========== Pack 列表管理 ==========

    def create_pack(
        self,
        pack_name: str,
        version: str,
        description: str,
        author: str,
        category: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """创建新 Pack

        Args:
            pack_name: Pack 名称
            version: 版本号
            description: 描述
            author: 作者
            category: 类别
            tags: 标签列表

        Returns:
            操作结果
        """
        pack_id = f"pack_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(pack_name) % 10000:04d}"

        listing = PackListing(
            pack_id=pack_id,
            pack_name=pack_name,
            version=version,
            description=description,
            author=author,
            category=category,
            tags=tags or [],
            status=PackStatus.PENDING,
        )

        success = self.store.create_listing(listing)

        return {
            "success": success,
            "pack_id": pack_id if success else None,
            "message": "Pack created successfully" if success else "Failed to create pack",
        }

    def get_pack(self, pack_id: str) -> Dict[str, Any]:
        """获取 Pack 详情

        Args:
            pack_id: Pack ID

        Returns:
            Pack 详情或错误信息
        """
        listing = self.store.get_listing(pack_id)

        if listing is None:
            return {"success": False, "error": f"Pack {pack_id} not found"}

        return {"success": True, "pack": listing.to_dict()}

    def update_pack(
        self,
        pack_id: str,
        pack_name: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """更新 Pack 信息

        Args:
            pack_id: Pack ID
            pack_name: 新名称（可选）
            version: 新版本（可选）
            description: 新描述（可选）
            category: 新类别（可选）
            tags: 新标签列表（可选）

        Returns:
            操作结果
        """
        listing = self.store.get_listing(pack_id)

        if listing is None:
            return {"success": False, "error": f"Pack {pack_id} not found"}

        # 更新字段
        if pack_name is not None:
            listing.pack_name = pack_name
        if version is not None:
            listing.version = version
        if description is not None:
            listing.description = description
        if category is not None:
            listing.category = category
        if tags is not None:
            listing.tags = tags

        listing.updated_at = datetime.now()

        success = self.store.update_listing(listing)

        return {
            "success": success,
            "message": "Pack updated successfully" if success else "Failed to update pack",
        }

    def delete_pack(self, pack_id: str) -> Dict[str, Any]:
        """删除 Pack

        Args:
            pack_id: Pack ID

        Returns:
            操作结果
        """
        success = self.store.delete_listing(pack_id)

        return {
            "success": success,
            "message": "Pack deleted successfully" if success else "Failed to delete pack",
        }

    def list_packs(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        author: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """列出 Pack（支持过滤）

        Args:
            category: 类别过滤
            status: 状态过滤
            author: 作者过滤
            limit: 限制数量
            offset: 偏移量

        Returns:
            Pack 列表
        """
        status_enum = PackStatus(status) if status else None

        listings = self.store.list_listings(
            category=category, status=status_enum, author=author, limit=limit, offset=offset
        )

        return {
            "success": True,
            "packs": [listing.to_dict() for listing in listings],
            "count": len(listings),
        }

    def search_packs(self, query: str, limit: int = 100) -> Dict[str, Any]:
        """搜索 Pack

        Args:
            query: 搜索关键词
            limit: 限制数量

        Returns:
            搜索结果
        """
        listings = self.store.search_listings(query, limit)

        return {
            "success": True,
            "packs": [listing.to_dict() for listing in listings],
            "count": len(listings),
        }

    # ========== Pack 评价管理 ==========

    def rate_pack(
        self, pack_id: str, user_id: str, rating: int, title: str = "", content: str = ""
    ) -> Dict[str, Any]:
        """评价 Pack

        Args:
            pack_id: Pack ID
            user_id: 用户 ID
            rating: 评分（1-5）
            title: 标题
            content: 内容

        Returns:
            操作结果
        """
        # 检查 Pack 是否存在
        listing = self.store.get_listing(pack_id)
        if listing is None:
            return {"success": False, "error": f"Pack {pack_id} not found"}

        rating_id = f"rating_{datetime.now().strftime('%Y%m%d%H%M%S')}_{pack_id}_{user_id}"

        pack_rating = PackRating(
            rating_id=rating_id,
            pack_id=pack_id,
            user_id=user_id,
            rating=rating,
            title=title,
            content=content,
        )

        success = self.store.create_rating(pack_rating)

        return {
            "success": success,
            "rating_id": rating_id if success else None,
            "message": "Rating submitted successfully" if success else "Failed to submit rating",
        }

    def get_rating(self, rating_id: str) -> Dict[str, Any]:
        """获取评价详情

        Args:
            rating_id: 评价 ID

        Returns:
            评价详情或错误信息
        """
        rating = self.store.get_rating(rating_id)

        if rating is None:
            return {"success": False, "error": f"Rating {rating_id} not found"}

        return {"success": True, "rating": rating.to_dict()}

    def list_pack_ratings(self, pack_id: str, limit: int = 100) -> Dict[str, Any]:
        """列出 Pack 评价

        Args:
            pack_id: Pack ID
            limit: 限制数量

        Returns:
            评价列表
        """
        ratings = self.store.list_ratings(pack_id, limit)

        return {
            "success": True,
            "ratings": [rating.to_dict() for rating in ratings],
            "count": len(ratings),
        }

    def delete_rating(self, rating_id: str) -> Dict[str, Any]:
        """删除评价

        Args:
            rating_id: 评价 ID

        Returns:
            操作结果
        """
        success = self.store.delete_rating(rating_id)

        return {
            "success": success,
            "message": "Rating deleted successfully" if success else "Failed to delete rating",
        }

    # ========== 用户反馈管理 ==========

    def submit_feedback(
        self, pack_id: str, user_id: str, feedback_type: str, content: str
    ) -> Dict[str, Any]:
        """提交用户反馈

        Args:
            pack_id: Pack ID
            user_id: 用户 ID
            feedback_type: 反馈类型（bug, suggestion, request）
            content: 反馈内容

        Returns:
            操作结果
        """
        # 检查 Pack 是否存在
        listing = self.store.get_listing(pack_id)
        if listing is None:
            return {"success": False, "error": f"Pack {pack_id} not found"}

        feedback_id = f"feedback_{datetime.now().strftime('%Y%m%d%H%M%S')}_{pack_id}_{user_id}"

        feedback = UserFeedback(
            feedback_id=feedback_id,
            pack_id=pack_id,
            user_id=user_id,
            feedback_type=feedback_type,
            content=content,
        )

        success = self.store.create_feedback(feedback)

        return {
            "success": success,
            "feedback_id": feedback_id if success else None,
            "message": "Feedback submitted successfully"
            if success
            else "Failed to submit feedback",
        }

    def get_feedback(self, feedback_id: str) -> Dict[str, Any]:
        """获取反馈详情

        Args:
            feedback_id: 反馈 ID

        Returns:
            反馈详情或错误信息
        """
        feedback = self.store.get_feedback(feedback_id)

        if feedback is None:
            return {"success": False, "error": f"Feedback {feedback_id} not found"}

        return {"success": True, "feedback": feedback.to_dict()}

    def list_pack_feedback(
        self, pack_id: str, feedback_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """列出 Pack 反馈

        Args:
            pack_id: Pack ID
            feedback_type: 反馈类型过滤

        Returns:
            反馈列表
        """
        feedbacks = self.store.list_feedback(pack_id, feedback_type)

        return {
            "success": True,
            "feedbacks": [feedback.to_dict() for feedback in feedbacks],
            "count": len(feedbacks),
        }

    # ========== 管理员操作 ==========

    def approve_pack(self, pack_id: str) -> Dict[str, Any]:
        """批准 Pack

        Args:
            pack_id: Pack ID

        Returns:
            操作结果
        """
        listing = self.store.get_listing(pack_id)

        if listing is None:
            return {"success": False, "error": f"Pack {pack_id} not found"}

        listing.approve()
        success = self.store.update_listing(listing)

        return {
            "success": success,
            "message": "Pack approved successfully" if success else "Failed to approve pack",
        }

    def reject_pack(self, pack_id: str) -> Dict[str, Any]:
        """拒绝 Pack

        Args:
            pack_id: Pack ID

        Returns:
            操作结果
        """
        listing = self.store.get_listing(pack_id)

        if listing is None:
            return {"success": False, "error": f"Pack {pack_id} not found"}

        listing.reject()
        success = self.store.update_listing(listing)

        return {
            "success": success,
            "message": "Pack rejected successfully" if success else "Failed to reject pack",
        }

    def increment_downloads(self, pack_id: str) -> Dict[str, Any]:
        """增加下载次数

        Args:
            pack_id: Pack ID

        Returns:
            操作结果
        """
        listing = self.store.get_listing(pack_id)

        if listing is None:
            return {"success": False, "error": f"Pack {pack_id} not found"}

        listing.increment_downloads()
        success = self.store.update_listing(listing)

        return {
            "success": success,
            "downloads": listing.downloads,
            "message": "Download count updated" if success else "Failed to update download count",
        }

    # ========== 统计信息 ==========

    def get_market_stats(self) -> Dict[str, Any]:
        """获取市场统计信息

        Returns:
            统计信息
        """
        approved = self.store.list_listings(status=PackStatus.APPROVED)
        pending = self.store.list_listings(status=PackStatus.PENDING)

        total_downloads = sum(p.downloads for p in approved)
        rated_packs = [p for p in approved if p.rating_count > 0]
        avg_rating = sum(p.rating for p in rated_packs) / len(rated_packs) if rated_packs else 0.0

        # 计算星级分布
        rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for pack in approved:
            if pack.rating_count > 0:
                # 估算分布（简化版，实际应从评分表聚合）
                star = int(round(pack.rating))
                rating_distribution[star] += pack.rating_count

        return {
            "success": True,
            "stats": {
                "total_packs": len(approved),
                "pending_packs": len(pending),
                "total_downloads": total_downloads,
                "average_rating": round(avg_rating, 2),
                "rating_distribution": rating_distribution,
            },
        }

    def get_pack_rating_stats(self, pack_id: str) -> Dict[str, Any]:
        """获取 Pack 详细评分统计

        Args:
            pack_id: Pack ID

        Returns:
            评分统计信息
        """
        pack_result = self.get_pack(pack_id)
        if not pack_result["success"]:
            return pack_result

        pack = pack_result["pack"]
        ratings_result = self.list_pack_ratings(pack_id, limit=1000)

        if not ratings_result["success"]:
            ratings_result = {"ratings": [], "count": 0}

        ratings = ratings_result["ratings"]

        # 计算星级分布
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in ratings:
            distribution[r["rating"]] += 1

        # 高质量评价筛选（4+ 星且带内容）
        high_quality = [r for r in ratings if r["rating"] >= 4 and r.get("content")]

        # 计算最近 7 天评价趋势
        from datetime import timedelta

        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_ratings = [
            r for r in ratings if datetime.fromisoformat(r["created_at"]) > seven_days_ago
        ]

        if recent_ratings:
            recent_avg = sum(r["rating"] for r in recent_ratings) / len(recent_ratings)
        else:
            recent_avg = 0.0

        return {
            "success": True,
            "pack_id": pack_id,
            "pack_name": pack["pack_name"],
            "average_rating": pack["rating"],
            "rating_count": pack["rating_count"],
            "rating_distribution": distribution,
            "high_quality_count": len(high_quality),
            "high_quality_percentage": round(len(high_quality) / len(ratings) * 100, 1)
            if ratings
            else 0,
            "recent_ratings_count": len(recent_ratings),
            "recent_average_rating": round(recent_avg, 2),
        }

    def get_high_quality_reviews(
        self, pack_id: str, min_rating: int = 4, limit: int = 10
    ) -> Dict[str, Any]:
        """获取高质量评价

        Args:
            pack_id: Pack ID
            min_rating: 最低评分（默认 4）
            limit: 限制数量

        Returns:
            高质量评价列表
        """
        all_ratings = self.list_pack_ratings(pack_id, limit=1000)

        if not all_ratings["success"]:
            return all_ratings

        # 筛选高质量评价
        high_quality = [
            r for r in all_ratings["ratings"] if r["rating"] >= min_rating and r.get("content")
        ]

        # 按评分降序排序
        high_quality.sort(key=lambda x: x["rating"], reverse=True)

        return {
            "success": True,
            "reviews": high_quality[:limit],
            "count": len(high_quality),
            "min_rating": min_rating,
        }
