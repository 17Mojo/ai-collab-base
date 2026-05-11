# Pack Market Data Model
# Track A Day 1: Pack 市场基础架构

"""
Pack 市场数据模型
支持 Pack 列表、评价、反馈功能
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List


class PackStatus(Enum):
    """Pack 状态"""

    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


@dataclass
class PackListing:
    """市场 Pack 列表项"""

    pack_id: str
    pack_name: str
    version: str
    description: str
    author: str
    category: str
    tags: List[str] = field(default_factory=list)
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    status: PackStatus = PackStatus.PENDING
    dependencies: List[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_tag(self, tag: str) -> None:
        """添加标签"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()

    def increment_downloads(self) -> None:
        """增加下载次数"""
        self.downloads += 1
        self.updated_at = datetime.now()

    def update_rating(self, new_rating: float, rating_count: int) -> None:
        """更新评分"""
        if rating_count > 0:
            self.rating = new_rating
            self.rating_count = rating_count
            self.updated_at = datetime.now()

    def approve(self) -> None:
        """批准 Pack"""
        self.status = PackStatus.APPROVED
        self.updated_at = datetime.now()

    def reject(self) -> None:
        """拒绝 Pack"""
        self.status = PackStatus.REJECTED
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "pack_id": self.pack_id,
            "pack_name": self.pack_name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "category": self.category,
            "tags": self.tags,
            "downloads": self.downloads,
            "rating": self.rating,
            "rating_count": self.rating_count,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PackListing":
        """从字典反序列化"""
        return cls(
            pack_id=data["pack_id"],
            pack_name=data["pack_name"],
            version=data["version"],
            description=data["description"],
            author=data["author"],
            category=data["category"],
            tags=data.get("tags", []),
            downloads=data.get("downloads", 0),
            rating=data.get("rating", 0.0),
            rating_count=data.get("rating_count", 0),
            status=PackStatus(data.get("status", "pending")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class PackRating:
    """Pack 评价"""

    rating_id: str
    pack_id: str
    user_id: str
    rating: int  # 1-5
    title: str = ""
    content: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if not (1 <= self.rating <= 5):
            raise ValueError(f"Rating must be between 1 and 5, got {self.rating}")

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "rating_id": self.rating_id,
            "pack_id": self.pack_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PackRating":
        """从字典反序列化"""
        return cls(
            rating_id=data["rating_id"],
            pack_id=data["pack_id"],
            user_id=data["user_id"],
            rating=data["rating"],
            title=data.get("title", ""),
            content=data.get("content", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class UserFeedback:
    """用户反馈"""

    feedback_id: str
    pack_id: str
    user_id: str
    feedback_type: str  # bug, suggestion, request
    content: str
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        valid_types = ["bug", "suggestion", "request"]
        if self.feedback_type not in valid_types:
            raise ValueError(
                f"Invalid feedback_type: {self.feedback_type}. Must be one of {valid_types}"
            )

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "feedback_id": self.feedback_id,
            "pack_id": self.pack_id,
            "user_id": self.user_id,
            "feedback_type": self.feedback_type,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserFeedback":
        """从字典反序列化"""
        return cls(
            feedback_id=data["feedback_id"],
            pack_id=data["pack_id"],
            user_id=data["user_id"],
            feedback_type=data["feedback_type"],
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )
