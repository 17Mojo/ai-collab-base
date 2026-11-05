"""N17 收口测试：市场表 dependencies 持久化 + pack_versions 版本历史（真 sqlite）

覆盖：
- 旧库迁移：无 dependencies 列的 pack_listings 就地补列、存量行零丢失；
- dependencies 随 create/update 持久化、get/list/search 回读；
- pack_versions 追加式归档语义（每版本一条首次快照、update 覆盖前归档旧行、
  删除当前行后历史仍可查）；
- market_api.create_pack/update_pack 传参 + list_pack_versions 暴露。
"""

import json
import sqlite3
from contextlib import closing
from datetime import datetime

from ai_collab.pack.market import PackListing, PackStatus
from ai_collab.pack.market_api import PackMarketAPI
from ai_collab.pack.market_store import PackMarketStore

# N17 之前的旧库 DDL（无 dependencies 列）——迁移测试的起点
_OLD_SCHEMA_DDL = """
    CREATE TABLE pack_listings (
        pack_id TEXT PRIMARY KEY,
        pack_name TEXT NOT NULL,
        version TEXT NOT NULL,
        description TEXT NOT NULL,
        author TEXT NOT NULL,
        category TEXT NOT NULL,
        tags TEXT NOT NULL,
        downloads INTEGER DEFAULT 0,
        rating REAL DEFAULT 0.0,
        rating_count INTEGER DEFAULT 0,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
"""


def _make_old_db(path, rows):
    """构造 N17 之前的旧库（无 dependencies 列），写入给定行"""
    with closing(sqlite3.connect(str(path))) as conn, conn:
        conn.execute(_OLD_SCHEMA_DDL)
        for r in rows:
            conn.execute(
                """
                INSERT INTO pack_listings (
                    pack_id, pack_name, version, description, author, category,
                    tags, downloads, rating, rating_count, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                r,
            )


def _listing(pack_id="p1", version="1.0.0", deps=None, description="desc"):
    return PackListing(
        pack_id=pack_id,
        pack_name="P One",
        version=version,
        description=description,
        author="tester",
        category="general",
        tags=["t"],
        status=PackStatus.PENDING,
        dependencies=deps if deps is not None else [],
        created_at=datetime(2026, 11, 5, 10, 0, 0),
        updated_at=datetime(2026, 11, 5, 10, 0, 0),
    )


class TestMigration:
    """旧库 → 新 schema 迁移"""

    def test_old_db_gains_dependencies_column_and_keeps_rows(self, tmp_path):
        db = tmp_path / "packs.db"
        _make_old_db(
            db,
            [
                (
                    "p1", "P One", "1.0.0", "desc", "tester", "general",
                    json.dumps(["t"]), 3, 4.5, 2, "approved",
                    "2026-11-01T00:00:00", "2026-11-02T00:00:00",
                )
            ],
        )

        store = PackMarketStore(str(db))

        with closing(sqlite3.connect(str(db))) as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(pack_listings)")}
        assert "dependencies" in cols

        listing = store.get_listing("p1")
        assert listing is not None
        assert listing.version == "1.0.0"
        assert listing.downloads == 3
        assert listing.rating == 4.5
        assert listing.status == PackStatus.APPROVED
        assert listing.dependencies == []  # 迁移默认值

    def test_migration_idempotent(self, tmp_path):
        db = tmp_path / "packs.db"
        _make_old_db(
            db,
            [("p1", "P", "1.0.0", "d", "a", "c", "[]", 0, 0.0, 0, "pending",
              "2026-11-01T00:00:00", "2026-11-01T00:00:00")],
        )
        PackMarketStore(str(db))
        store2 = PackMarketStore(str(db))  # 二次打开不再 ALTER
        assert store2.get_listing("p1") is not None

    def test_new_db_has_dependencies_column(self, tmp_path):
        db = tmp_path / "packs.db"
        PackMarketStore(str(db))
        with closing(sqlite3.connect(str(db))) as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(pack_listings)")}
        assert "dependencies" in cols


class TestDependenciesPersistence:
    """dependencies 列持久化回读"""

    def test_create_and_get_roundtrip(self, tmp_path):
        store = PackMarketStore(str(tmp_path / "packs.db"))
        deps = [{"name": "base", "version": "^1.0.0", "optional": False}]
        assert store.create_listing(_listing(deps=deps)) is True

        listing = store.get_listing("p1")
        assert listing is not None
        assert listing.dependencies == deps

    def test_update_persists_dependencies(self, tmp_path):
        store = PackMarketStore(str(tmp_path / "packs.db"))
        store.create_listing(_listing(deps=[]))

        updated = _listing(deps=[{"name": "x", "version": "*", "optional": True}])
        assert store.update_listing(updated) is True
        listing = store.get_listing("p1")
        assert listing.dependencies == [{"name": "x", "version": "*", "optional": True}]

    def test_list_and_search_return_dependencies(self, tmp_path):
        store = PackMarketStore(str(tmp_path / "packs.db"))
        deps = [{"name": "base", "version": ">=1.0.0", "optional": False}]
        store.create_listing(_listing(deps=deps))

        listed = store.list_listings()
        assert listed[0].dependencies == deps
        found = store.search_listings("P One")
        assert found[0].dependencies == deps


class TestVersionHistory:
    """pack_versions 追加式版本历史"""

    def test_create_archives_snapshot(self, tmp_path):
        store = PackMarketStore(str(tmp_path / "packs.db"))
        deps = [{"name": "base", "version": "^1.0.0", "optional": False}]
        store.create_listing(_listing(version="1.0.0", deps=deps))

        versions = store.list_versions("p1")
        assert len(versions) == 1
        assert versions[0]["version"] == "1.0.0"
        assert versions[0]["dependencies"] == deps
        assert versions[0]["status"] == "pending"
        assert "archived_at" in versions[0]

    def test_update_archives_old_and_new(self, tmp_path):
        store = PackMarketStore(str(tmp_path / "packs.db"))
        store.create_listing(_listing(version="1.0.0", description="first"))
        store.update_listing(_listing(version="2.0.0", description="second"))

        versions = store.list_versions("p1")
        assert [v["version"] for v in versions] == ["1.0.0", "2.0.0"]
        by_ver = {v["version"]: v for v in versions}
        assert by_ver["1.0.0"]["description"] == "first"
        assert by_ver["2.0.0"]["description"] == "second"

    def test_same_version_keeps_first_snapshot(self, tmp_path):
        """同版本元数据改动不重写历史（INSERT OR IGNORE 语义）"""
        store = PackMarketStore(str(tmp_path / "packs.db"))
        store.create_listing(_listing(version="1.0.0", description="first"))
        store.update_listing(_listing(version="1.0.0", description="second"))

        versions = store.list_versions("p1")
        assert len(versions) == 1
        assert versions[0]["description"] == "first"
        # 当前真值仍是 pack_listings
        assert store.get_listing("p1").description == "second"

    def test_history_survives_delete(self, tmp_path):
        store = PackMarketStore(str(tmp_path / "packs.db"))
        store.create_listing(_listing(version="1.0.0"))
        store.delete_listing("p1")

        assert store.get_listing("p1") is None
        assert len(store.list_versions("p1")) == 1

    def test_migrated_db_update_archives_preexisting_row(self, tmp_path):
        """迁移前存量行在首次 update_listing 时补进历史（覆盖前归档旧行）"""
        db = tmp_path / "packs.db"
        _make_old_db(
            db,
            [("p1", "P One", "1.0.0", "legacy", "tester", "general",
              json.dumps(["t"]), 0, 0.0, 0, "pending",
              "2026-11-01T00:00:00", "2026-11-01T00:00:00")],
        )
        store = PackMarketStore(str(db))

        store.update_listing(_listing(version="2.0.0", description="new"))
        versions = store.list_versions("p1")
        assert [v["version"] for v in versions] == ["1.0.0", "2.0.0"]
        assert versions[0]["description"] == "legacy"
        assert versions[0]["dependencies"] == []

    def test_list_versions_unknown_pack_empty(self, tmp_path):
        store = PackMarketStore(str(tmp_path / "packs.db"))
        assert store.list_versions("nope") == []


class TestMarketAPIWiring:
    """market_api 传参与暴露"""

    def test_create_pack_with_dependencies(self, tmp_path):
        api = PackMarketAPI(str(tmp_path / "packs.db"))
        deps = [{"name": "base", "version": "^1.0.0", "optional": False}]
        result = api.create_pack(
            "Demo", "1.0.0", "d", "tester", "general", dependencies=deps
        )
        assert result["success"] is True

        got = api.get_pack(result["pack_id"])
        assert got["pack"]["dependencies"] == deps

    def test_update_pack_with_dependencies(self, tmp_path):
        api = PackMarketAPI(str(tmp_path / "packs.db"))
        created = api.create_pack("Demo", "1.0.0", "d", "tester", "general")
        deps = [{"name": "x", "version": "*", "optional": False}]
        result = api.update_pack(created["pack_id"], dependencies=deps)
        assert result["success"] is True

        got = api.get_pack(created["pack_id"])
        assert got["pack"]["dependencies"] == deps

    def test_list_pack_versions(self, tmp_path):
        api = PackMarketAPI(str(tmp_path / "packs.db"))
        created = api.create_pack("Demo", "1.0.0", "d", "tester", "general")
        pid = created["pack_id"]

        result = api.list_pack_versions(pid)
        assert result["success"] is True
        assert result["count"] == 1
        assert result["versions"][0]["version"] == "1.0.0"

    def test_list_pack_versions_unknown_pack_errors(self, tmp_path):
        api = PackMarketAPI(str(tmp_path / "packs.db"))
        result = api.list_pack_versions("nope")
        assert result["success"] is False
        assert "not found" in result["error"]


class TestFromDictRoundtrip:
    """PackListing.from_dict 不再丢 dependencies（to_dict/from_dict 对称）"""

    def test_from_dict_keeps_dependencies(self):
        deps = [{"name": "base", "version": "^1.0.0", "optional": False}]
        listing = _listing(deps=deps)
        restored = PackListing.from_dict(listing.to_dict())
        assert restored.dependencies == deps
