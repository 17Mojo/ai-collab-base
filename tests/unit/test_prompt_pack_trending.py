"""
TASK-P1-PROMPT-TRENDING-001 的不变量测试

守护「热门 Pack (7天内)」名副其实这条契约：
下载事件时间序列可持久化、refresh_index 不清零统计、窗口排序语义正确、
推荐 fallback 不被窗口误伤。

对应契约：collaboration/tasks/TASK-P1-PROMPT-TRENDING-001.md §三 R1~R8
"""

import json
import shutil
from datetime import datetime, timedelta

import pytest

from ai_collab.prompt_pack.schema import PackCategoryType
from ai_collab.prompt_pack.store import (
    DOWNLOAD_EVENT_RETENTION_DAYS,
    PackIndexEntry,
    PackRegistry,
    PackSearchEngine,
)


def days_ago(days: float) -> str:
    return (datetime.now() - timedelta(days=days)).isoformat()


def make_entry(name: str, **kwargs) -> PackIndexEntry:
    stamp = datetime.now()
    defaults = {
        "name": name,
        "version": "1.0.0",
        "category": PackCategoryType.DOMAIN,
        "description": f"{name} description",
        "author": "Author",
        "created_at": stamp,
        "updated_at": stamp,
    }
    defaults.update(kwargs)
    return PackIndexEntry(**defaults)


@pytest.fixture
def registry_factory(tmp_path):
    """返回一个用 tmp_path 建 registry 的工厂，并负责写 manifest"""
    created = []

    def build(names=("alpha", "beta", "gamma")):
        packs_dir = tmp_path / f"packs{len(created)}"
        packs_dir.mkdir()
        created.append(packs_dir)
        for name in names:
            pack_dir = packs_dir / name
            pack_dir.mkdir()
            stamp = datetime.now().isoformat()
            manifest = {
                "name": name,
                "version": "1.0.0",
                "category": "domain",
                "description": f"{name} description",
                "author": "Author",
                "created_at": stamp,
                "updated_at": stamp,
                "dependencies": [],
                "compatible_tools": ["universal"],
                "tags": [],
                "metadata": {},
            }
            with open(pack_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        return PackRegistry(packs_dir)

    yield build
    for path in created:
        shutil.rmtree(path, ignore_errors=True)


class TestDownloadEventsDataModel:
    """R1: download_events 字段的序列化 / 反序列化 / 向后兼容"""

    def test_to_dict_includes_download_events(self):
        entry = make_entry("alpha", download_events=[days_ago(1), days_ago(2)])

        data = entry.to_dict()

        assert data["download_events"] == entry.download_events

    def test_to_dict_defaults_to_empty_list(self):
        data = make_entry("alpha").to_dict()

        assert data["download_events"] == []

    def test_load_index_reads_download_events(self, registry_factory):
        registry = registry_factory(names=("alpha",))
        registry.index["alpha"].download_events = [days_ago(1)]
        registry._save_index()

        reloaded = PackRegistry(registry.packs_root)

        assert reloaded.index["alpha"].download_events == registry.index[
            "alpha"
        ].download_events

    def test_legacy_index_without_download_events_loads(self, registry_factory):
        """旧索引文件没有 download_events 字段时按 [] 处理，不报错、统计不丢"""
        registry = registry_factory(names=("alpha",))
        registry.index["alpha"].downloads = 42
        registry.index["alpha"].rating = 4.5
        registry.index["alpha"].review_count = 7
        registry._save_index()

        raw = json.loads(registry.index_file.read_text(encoding="utf-8"))
        del raw["alpha"]["download_events"]
        registry.index_file.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        reloaded = PackRegistry(registry.packs_root)

        assert reloaded.index["alpha"].download_events == []
        assert reloaded.index["alpha"].downloads == 42
        assert reloaded.index["alpha"].rating == 4.5
        assert reloaded.index["alpha"].review_count == 7

    def test_malformed_download_events_does_not_wipe_stats(self, registry_factory):
        """download_events 被改坏成非 list 时不得触发索引重建（那会清空统计）"""
        registry = registry_factory(names=("alpha",))
        registry.index["alpha"].downloads = 11
        registry._save_index()

        raw = json.loads(registry.index_file.read_text(encoding="utf-8"))
        raw["alpha"]["download_events"] = "not-a-list"
        registry.index_file.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        reloaded = PackRegistry(registry.packs_root)

        assert reloaded.index["alpha"].download_events == []
        assert reloaded.index["alpha"].downloads == 11


class TestEventRecording:
    """R2: update_pack_stats 的事件写入与裁剪"""

    def test_update_downloads_appends_n_events(self, registry_factory):
        registry = registry_factory(names=("alpha",))

        registry.update_pack_stats("alpha", downloads=3)

        assert len(registry.index["alpha"].download_events) == 3
        assert registry.index["alpha"].downloads == 3

    def test_zero_or_none_downloads_append_nothing(self, registry_factory):
        registry = registry_factory(names=("alpha",))

        registry.update_pack_stats("alpha", downloads=0)
        registry.update_pack_stats("alpha", downloads=None)
        registry.update_pack_stats("alpha", rating=4.0, review_count=1)

        assert registry.index["alpha"].download_events == []

    def test_rating_only_update_appends_nothing(self, registry_factory):
        """R7: rating.py 的调用路径不传 downloads，不得产生下载事件"""
        registry = registry_factory(names=("alpha",))

        registry.update_pack_stats("alpha", rating=4.8, review_count=2)

        assert registry.index["alpha"].download_events == []

    def test_events_are_pruned_to_retention_window(self, registry_factory):
        registry = registry_factory(names=("alpha",))
        entry = registry.index["alpha"]
        stale = (datetime.now() - timedelta(days=DOWNLOAD_EVENT_RETENTION_DAYS + 5)).isoformat()
        entry.download_events = [stale, days_ago(1)]

        registry.update_pack_stats("alpha", downloads=1)

        assert len(entry.download_events) == 2
        assert stale not in entry.download_events


class TestStatsSurviveRefresh:
    """R3: refresh_index 不得清零统计与下载事件"""

    def test_refresh_index_preserves_stats_and_events(self, registry_factory):
        registry = registry_factory(names=("alpha",))
        registry.update_pack_stats("alpha", downloads=5)
        registry.update_pack_stats("alpha", rating=4.5, review_count=2)

        registry.refresh_index()

        entry = registry.index["alpha"]
        assert entry.downloads == 5
        assert entry.rating == 4.5
        assert entry.review_count == 2
        assert len(entry.download_events) == 5

    def test_refresh_index_still_reads_manifest_fields(self, registry_factory):
        registry = registry_factory(names=("alpha",))

        registry.refresh_index()

        assert registry.index["alpha"].version == "1.0.0"
        assert registry.index["alpha"].author == "Author"

    def test_refresh_index_drops_packs_missing_from_filesystem(self, registry_factory):
        registry = registry_factory(names=("alpha", "beta"))
        registry.index["ghost"] = make_entry("ghost")

        registry.refresh_index()

        assert "ghost" not in registry.index
        assert "alpha" in registry.index


class TestTrendingWindow:
    """R4: 窗口热度排序语义"""

    def test_only_in_window_events_are_candidates(self, registry_factory):
        registry = registry_factory(names=("alpha", "beta"))
        registry.index["alpha"].download_events = [days_ago(1), days_ago(2)]
        registry.index["alpha"].downloads = 2
        registry.index["beta"].download_events = [days_ago(30)]
        registry.index["beta"].downloads = 1
        engine = PackSearchEngine(registry)

        trending = engine.get_trending_packs(days=7, limit=10)

        assert [p.name for p in trending] == ["alpha"]

    def test_window_hits_outrank_total_downloads(self, registry_factory):
        registry = registry_factory(names=("alpha", "beta"))
        registry.index["alpha"].download_events = [days_ago(1)]
        registry.index["alpha"].downloads = 999
        registry.index["beta"].download_events = [days_ago(1), days_ago(2), days_ago(3)]
        registry.index["beta"].downloads = 3
        engine = PackSearchEngine(registry)

        trending = engine.get_trending_packs(days=7, limit=10)

        assert [p.name for p in trending] == ["beta", "alpha"]

    def test_tie_break_is_name_ascending_and_reproducible(self, registry_factory):
        registry = registry_factory(names=("charlie", "alpha", "bravo"))
        for name in ("charlie", "alpha", "bravo"):
            registry.index[name].download_events = [days_ago(1)]
            registry.index[name].downloads = 5
        engine = PackSearchEngine(registry)

        first = [p.name for p in engine.get_trending_packs(days=7, limit=10)]
        second = [p.name for p in engine.get_trending_packs(days=7, limit=10)]

        assert first == ["alpha", "bravo", "charlie"]
        assert first == second

    def test_non_positive_days_raises_value_error(self, registry_factory):
        engine = PackSearchEngine(registry_factory())

        for bad_days in (0, -1):
            with pytest.raises(ValueError, match="days"):
                engine.get_trending_packs(days=bad_days)

    def test_non_positive_limit_returns_empty(self, registry_factory):
        registry = registry_factory(names=("alpha",))
        registry.index["alpha"].download_events = [days_ago(1)]
        engine = PackSearchEngine(registry)

        assert engine.get_trending_packs(days=7, limit=0) == []
        assert engine.get_trending_packs(days=7, limit=-3) == []

    def test_fallback_when_no_events_in_window(self, registry_factory):
        """降级路径：无任何窗口内事件时退回按累计下载数排序，不空屏"""
        registry = registry_factory(names=("alpha", "beta", "gamma"))
        registry.index["alpha"].downloads = 10
        registry.index["beta"].downloads = 50
        registry.index["gamma"].downloads = 30
        engine = PackSearchEngine(registry)

        trending = engine.get_trending_packs(days=7, limit=3)

        assert [p.name for p in trending] == ["beta", "gamma", "alpha"]

    def test_limit_truncates_window_results(self, registry_factory):
        registry = registry_factory(names=("alpha", "beta", "gamma"))
        for name in ("alpha", "beta", "gamma"):
            registry.index[name].download_events = [days_ago(1)]
        engine = PackSearchEngine(registry)

        assert len(engine.get_trending_packs(days=7, limit=2)) == 2


class TestRecommendedNotWindowBound:
    """R5: 推荐 fallback 不被 7 天窗口绑架"""

    def test_recommend_fallback_ignores_window(self, registry_factory):
        registry = registry_factory(names=("alpha", "beta"))
        registry.index["alpha"].downloads = 100
        registry.index["beta"].download_events = [days_ago(1)]
        registry.index["beta"].downloads = 1
        engine = PackSearchEngine(registry)

        recommendations = engine.get_recommended_packs("nonexistent", limit=5)

        assert [p.name for p in recommendations] == ["alpha", "beta"]

    def test_recommend_fallback_respects_limit(self, registry_factory):
        registry = registry_factory(names=("alpha", "beta", "gamma"))
        for name in ("alpha", "beta", "gamma"):
            registry.index[name].downloads = 5
        engine = PackSearchEngine(registry)

        assert len(engine.get_recommended_packs("nonexistent", limit=2)) == 2

    def test_same_category_branch_unchanged(self, registry_factory):
        registry = registry_factory(names=("alpha", "beta", "gamma"))
        registry.index["alpha"].rating = 4.0
        registry.index["alpha"].downloads = 1
        registry.index["beta"].rating = 5.0
        registry.index["beta"].downloads = 1
        # 排序键 rating * 10 + downloads * 0.1 → beta=50.1 > gamma=30.9
        registry.index["gamma"].rating = 3.0
        registry.index["gamma"].downloads = 9
        engine = PackSearchEngine(registry)

        recommendations = engine.get_recommended_packs("alpha", limit=5)

        assert [p.name for p in recommendations] == ["beta", "gamma"]
