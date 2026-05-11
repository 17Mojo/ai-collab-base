"""
Pack 注册表和发现机制

实现 Pack 商店功能：
- Pack 索引和注册
- Pack 搜索和发现
- Pack 分类浏览
- Pack 热门度排序
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schema import PackCategoryType


class PackSortType(Enum):
    """Pack 排序类型"""

    POPULARITY = "popularity"  # 按热度排序
    RATING = "rating"  # 按评分排序
    NEWEST = "newest"  # 按最新创建时间排序
    NAME = "name"  # 按名称排序
    DOWNLOADS = "downloads"  # 按下载次数排序


@dataclass
class PackIndexEntry:
    """Pack 索引条目"""

    name: str
    version: str
    category: PackCategoryType
    description: str
    author: str
    created_at: datetime
    updated_at: datetime
    downloads: int = 0
    rating: float = 0.0
    review_count: int = 0
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "category": self.category.value,
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "downloads": self.downloads,
            "rating": self.rating,
            "review_count": self.review_count,
            "tags": self.tags,
        }


class PackRegistry:
    """Pack 注册表"""

    def __init__(self, packs_root: Path):
        """
        初始化 Pack 注册表

        Args:
            packs_root: Packs 根目录
        """
        self.packs_root = Path(packs_root)
        self.index_file = self.packs_root / ".packs-index.json"
        self.index: Dict[str, PackIndexEntry] = {}
        self._load_index()

    def _load_index(self):
        """加载 Pack 索引"""
        if not self.index_file.exists():
            self._build_index()
        else:
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    index_data = json.load(f)

                self.index = {}
                for name, entry_data in index_data.items():
                    self.index[name] = PackIndexEntry(
                        name=entry_data["name"],
                        version=entry_data["version"],
                        category=PackCategoryType(entry_data["category"]),
                        description=entry_data["description"],
                        author=entry_data["author"],
                        created_at=datetime.fromisoformat(entry_data["created_at"]),
                        updated_at=datetime.fromisoformat(entry_data["updated_at"]),
                        downloads=entry_data.get("downloads", 0),
                        rating=entry_data.get("rating", 0.0),
                        review_count=entry_data.get("review_count", 0),
                        tags=entry_data.get("tags", []),
                    )
            except (json.JSONDecodeError, KeyError, ValueError):
                # 索引文件损坏，重新构建
                self._build_index()

    def _build_index(self):
        """构建 Pack 索引"""
        self.index = {}

        for pack_dir in self.packs_root.iterdir():
            if not pack_dir.is_dir():
                continue

            manifest_file = pack_dir / "manifest.json"
            if not manifest_file.exists():
                continue

            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)

                entry = PackIndexEntry(
                    name=manifest["name"],
                    version=manifest["version"],
                    category=PackCategoryType(manifest["category"]),
                    description=manifest["description"],
                    author=manifest["author"],
                    created_at=datetime.fromisoformat(manifest["created_at"]),
                    updated_at=datetime.fromisoformat(manifest["updated_at"]),
                    tags=manifest.get("tags", []),
                )

                self.index[entry.name] = entry
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        self._save_index()

    def _save_index(self):
        """保存 Pack 索引"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            index_data = {name: entry.to_dict() for name, entry in self.index.items()}
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    def register_pack(self, pack_name: str, entry: PackIndexEntry) -> None:
        """
        注册 Pack

        Args:
            pack_name: Pack 名称
            entry: Pack 索引条目
        """
        self.index[pack_name] = entry
        self._save_index()

    def unregister_pack(self, pack_name: str) -> None:
        """
        注销 Pack

        Args:
            pack_name: Pack 名称
        """
        if pack_name in self.index:
            del self.index[pack_name]
            self._save_index()

    def update_pack_stats(
        self,
        pack_name: str,
        downloads: Optional[int] = None,
        rating: Optional[float] = None,
        review_count: Optional[int] = None,
    ) -> None:
        """
        更新 Pack 统计信息

        Args:
            pack_name: Pack 名称
            downloads: 下载次数增量
            rating: 新评分
            review_count: 评论数量
        """
        if pack_name not in self.index:
            return

        entry = self.index[pack_name]

        if downloads is not None:
            entry.downloads += downloads

        if rating is not None:
            # 计算新的平均评分
            if entry.review_count > 0:
                entry.rating = ((entry.rating * entry.review_count) + rating) / (
                    entry.review_count + 1
                )
            else:
                entry.rating = rating

        if review_count is not None:
            entry.review_count += review_count

        self._save_index()

    def refresh_index(self) -> None:
        """刷新 Pack 索引"""
        self._build_index()

    def get_all_packs(self) -> List[PackIndexEntry]:
        """获取所有 Pack"""
        return list(self.index.values())

    def get_packs_by_category(self, category: PackCategoryType) -> List[PackIndexEntry]:
        """获取指定类别的 Pack"""
        return [entry for entry in self.index.values() if entry.category == category]


class PackSearchEngine:
    """Pack 搜索引擎"""

    def __init__(self, registry: PackRegistry):
        """
        初始化搜索引擎

        Args:
            registry: Pack 注册表
        """
        self.registry = registry

    def search(
        self, query: str, sort_by: PackSortType = PackSortType.POPULARITY, limit: int = 20
    ) -> List[PackIndexEntry]:
        """
        搜索 Pack

        Args:
            query: 搜索查询
            sort_by: 排序方式
            limit: 结果数量限制

        Returns:
            搜索结果
        """
        query_lower = query.lower()

        # 搜索所有匹配的 Pack
        results = []
        for entry in self.registry.get_all_packs():
            # 匹配名称
            if query_lower in entry.name.lower():
                results.append(entry)
                continue

            # 匹配描述
            if query_lower in entry.description.lower():
                results.append(entry)
                continue

            # 匹配标签
            if any(query_lower in tag.lower() for tag in entry.tags):
                results.append(entry)
                continue

        # 排序
        results = self._sort_results(results, sort_by)

        # 限制数量
        return results[:limit]

    def _sort_results(
        self, results: List[PackIndexEntry], sort_by: PackSortType
    ) -> List[PackIndexEntry]:
        """排序搜索结果"""
        if sort_by == PackSortType.POPULARITY:
            # 热度 = (下载次数 * 0.5 + 评分 * 10 * 0.3 + 评论数 * 0.2)
            return sorted(
                results,
                key=lambda x: x.downloads * 0.5 + x.rating * 10 * 0.3 + x.review_count * 0.2,
                reverse=True,
            )
        elif sort_by == PackSortType.RATING:
            return sorted(results, key=lambda x: x.rating, reverse=True)
        elif sort_by == PackSortType.NEWEST:
            return sorted(results, key=lambda x: x.updated_at, reverse=True)
        elif sort_by == PackSortType.NAME:
            return sorted(results, key=lambda x: x.name)
        elif sort_by == PackSortType.DOWNLOADS:
            return sorted(results, key=lambda x: x.downloads, reverse=True)
        else:
            return results

    def get_trending_packs(self, days: int = 7, limit: int = 10) -> List[PackIndexEntry]:
        """
        获取热门 Pack

        Args:
            days: 日期范围（天）
            limit: 结果数量限制

        Returns:
            热门 Pack 列表
        """
        # TODO: 实现基于时间的热度计算
        # 当前简单按下载次数排序
        all_packs = self.registry.get_all_packs()
        return sorted(all_packs, key=lambda x: x.downloads, reverse=True)[:limit]

    def get_recommended_packs(self, pack_name: str, limit: int = 5) -> List[PackIndexEntry]:
        """
        获取推荐 Pack

        Args:
            pack_name: Pack 名称
            limit: 结果数量限制

        Returns:
            推荐 Pack 列表
        """
        if pack_name not in self.registry.index:
            return self.get_trending_packs(limit=limit)

        # 获取当前 Pack
        current = self.registry.index[pack_name]

        # 推荐同类别的 Pack
        same_category = [
            entry
            for entry in self.registry.get_all_packs()
            if entry.category == current.category and entry.name != pack_name
        ]

        # 推荐
        return sorted(same_category, key=lambda x: x.rating * 10 + x.downloads * 0.1, reverse=True)[
            :limit
        ]

    def browse_by_category(
        self, category: PackCategoryType, sort_by: PackSortType = PackSortType.POPULARITY
    ) -> List[PackIndexEntry]:
        """
        按类别浏览

        Args:
            category: Pack 类别
            sort_by: 排序方式

        Returns:
            Pack 列表
        """
        packs = self.registry.get_packs_by_category(category)
        return self._sort_results(packs, sort_by)

    def get_pack_details(self, pack_name: str) -> Optional[PackIndexEntry]:
        """
        获取 Pack 详情

        Args:
            pack_name: Pack 名称

        Returns:
            Pack 索引条目，如果不存在则返回 None
        """
        return self.registry.index.get(pack_name)


def create_pack_store(packs_root: str = ".", workspace: str = ".") -> PackSearchEngine:
    """
    创建 Pack 商店搜索引擎

    Args:
        packs_root: Packs 根目录
        workspace: 工作区路径

    Returns:
        PackSearchEngine 实例
    """
    packs_path = Path(workspace) / packs_root
    registry = PackRegistry(packs_path)
    return PackSearchEngine(registry)
