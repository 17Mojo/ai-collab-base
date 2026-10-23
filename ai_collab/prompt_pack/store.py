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
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from .schema import PackCategoryType

#: 下载事件在索引里的保留天数。契约 TASK-P1-PROMPT-TRENDING-001 R2 指定 90 天，
#: 目的是防止 .packs-index.json 随下载次数无限膨胀。
DOWNLOAD_EVENT_RETENTION_DAYS = 90


def _parse_event_timestamp(raw: object) -> datetime | None:
    """把下载事件的时间戳解析为 naive datetime，无法解析时返回 None"""
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed


def _normalize_download_events(raw: object) -> list[str]:
    """把索引里的 download_events 原始值规整为 list[str]

    旧索引文件没有该字段，或该字段被手工改坏成非 list 值时，统一按 [] 处理。
    这里绝不能让异常冒泡到 _load_index 的 except 分支 —— 那会触发
    _build_index() 重建索引并清空全部统计，丢掉下载历史，比原缺陷更严重。
    """
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, str)]


def _prune_download_events(
    events: list[str], now: datetime | None = None
) -> list[str]:
    """裁剪下载事件，只保留最近 DOWNLOAD_EVENT_RETENTION_DAYS 天内的记录"""
    reference = now or datetime.now()
    if reference.tzinfo is not None:
        reference = reference.replace(tzinfo=None)
    cutoff = reference - timedelta(days=DOWNLOAD_EVENT_RETENTION_DAYS)
    kept = []
    for raw in events:
        parsed = _parse_event_timestamp(raw)
        if parsed is None:
            continue
        if parsed >= cutoff:
            kept.append(raw)
    return kept


def _count_events_in_window(
    events: list[str], window_start: datetime, window_end: datetime
) -> int:
    """统计落在闭区间窗口 [window_start, window_end] 内的下载事件数"""
    count = 0
    for raw in events or []:
        parsed = _parse_event_timestamp(raw)
        if parsed is None:
            continue
        if window_start <= parsed <= window_end:
            count += 1
    return count


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
    tags: list[str] | None = None
    download_events: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> dict[str, Any]:
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
            "download_events": self.download_events,
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
        self.index: dict[str, PackIndexEntry] = {}
        self._load_index()

    def _load_index(self):
        """加载 Pack 索引"""
        if not self.index_file.exists():
            self._build_index()
        else:
            try:
                with open(self.index_file, encoding="utf-8") as f:
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
                        download_events=_normalize_download_events(
                            entry_data.get("download_events")
                        ),
                    )
            except (json.JSONDecodeError, KeyError, ValueError):
                # 索引文件损坏，重新构建
                self._build_index()

    def _build_index(self):
        """构建 Pack 索引

        对同名包保留已积累的统计（downloads / rating / review_count）与下载事件
        （download_events）。refresh_index() 走的就是这条路径，若用全新条目覆盖旧条目，
        一次刷新就会把热度数据全部清零 —— 热度功能活不过一次刷新。
        描述性字段（version / description / author / category / 时间戳 / tags）
        仍以文件系统的 manifest.json 为准。
        """
        previous_by_name = {e.name: e for e in (getattr(self, "index", None) or {}).values()}
        self.index = {}

        for pack_dir in self.packs_root.iterdir():
            if not pack_dir.is_dir():
                continue

            manifest_file = pack_dir / "manifest.json"
            if not manifest_file.exists():
                continue

            try:
                with open(manifest_file, encoding="utf-8") as f:
                    manifest = json.load(f)

                carried = previous_by_name.get(manifest["name"])

                entry = PackIndexEntry(
                    name=manifest["name"],
                    version=manifest["version"],
                    category=PackCategoryType(manifest["category"]),
                    description=manifest["description"],
                    author=manifest["author"],
                    created_at=datetime.fromisoformat(manifest["created_at"]),
                    updated_at=datetime.fromisoformat(manifest["updated_at"]),
                    downloads=carried.downloads if carried else 0,
                    rating=carried.rating if carried else 0.0,
                    review_count=carried.review_count if carried else 0,
                    tags=manifest.get("tags", []),
                    download_events=(
                        _prune_download_events(list(carried.download_events))
                        if carried
                        else []
                    ),
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
        downloads: int | None = None,
        rating: float | None = None,
        review_count: int | None = None,
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
            if downloads > 0:
                # 记下每一次下载发生的时间，热度窗口才有数据可算
                stamp = datetime.now().isoformat()
                entry.download_events.extend([stamp] * downloads)
                entry.download_events = _prune_download_events(entry.download_events)

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

    def get_all_packs(self) -> list[PackIndexEntry]:
        """获取所有 Pack"""
        return list(self.index.values())

    def get_packs_by_category(self, category: PackCategoryType) -> list[PackIndexEntry]:
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
    ) -> list[PackIndexEntry]:
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
            if entry.tags and any(query_lower in tag.lower() for tag in entry.tags):
                results.append(entry)
                continue

        # 排序
        results = self._sort_results(results, sort_by)

        # 限制数量
        return results[:limit]

    def _sort_results(
        self, results: list[PackIndexEntry], sort_by: PackSortType
    ) -> list[PackIndexEntry]:
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

    def get_trending_packs(self, days: int = 7, limit: int = 10) -> list[PackIndexEntry]:
        """
        获取热门 Pack（按时间窗口内的下载热度）

        Args:
            days: 日期范围（天），闭区间 [now - days, now]，必须为正
            limit: 结果数量限制，非正数返回空列表

        Returns:
            热门 Pack 列表

        Raises:
            ValueError: days <= 0
        """
        if days <= 0:
            raise ValueError(f"days must be a positive window in days, got {days}")
        if limit <= 0:
            return []

        now = datetime.now()
        window_start = now - timedelta(days=days)

        windowed: list[tuple[int, PackIndexEntry]] = []
        for entry in self.registry.get_all_packs():
            hits = _count_events_in_window(entry.download_events, window_start, now)
            if hits > 0:
                windowed.append((hits, entry))

        if windowed:
            # 排序键：窗口内下载次数 desc → 总下载数 desc → name asc（稳定 tie-break）
            windowed.sort(key=lambda pair: (-pair[0], -pair[1].downloads, pair[1].name))
            return [entry for _, entry in windowed[:limit]]

        # 降级路径（有意为之，不是 bug）：旧索引文件根本没有下载事件数据，
        # 或窗口内确实无人下载。此时退回按累计下载数排序 —— 与本工单改动前的
        # 行为一致，保证 CLI 的「热门 Pack」不会因历史数据缺失而空屏。
        return sorted(
            self.registry.get_all_packs(),
            key=lambda x: (-x.downloads, x.name),
        )[:limit]

    def get_recommended_packs(self, pack_name: str, limit: int = 5) -> list[PackIndexEntry]:
        """
        获取推荐 Pack

        Args:
            pack_name: Pack 名称
            limit: 结果数量限制

        Returns:
            推荐 Pack 列表
        """
        if pack_name not in self.registry.index:
            # 「推荐」的语义是「全部 Pack 里最热门的」，不该被 7 天窗口绑架，
            # 因此这里走不依赖窗口的排序（downloads desc → name asc）。
            return sorted(
                self.registry.get_all_packs(),
                key=lambda x: (-x.downloads, x.name),
            )[:limit]

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
    ) -> list[PackIndexEntry]:
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

    def get_pack_details(self, pack_name: str) -> PackIndexEntry | None:
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
