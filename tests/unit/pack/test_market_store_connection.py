# Pack Market Store 连接生命周期测试
# Track A Day 1: 守护 sqlite3 连接不泄漏 + 事务语义不丢失

"""
PackMarketStore 连接生命周期回归测试

背景
----
``sqlite3`` 的 ``with conn:`` 只管理**事务**（成功提交 / 异常回滚），**不关闭连接**。
历史实现写成 ``with sqlite3.connect(path) as conn:``，每次调用都会泄漏一个连接，
表现为 ``ResourceWarning: unclosed database``。

修复引入了 ``_connect()`` 辅助上下文管理器，在事务上下文外层补上关闭语义。
这里守护两个方向：

1. 连接**必须被关闭**（防泄漏回归）
2. 写入**必须落盘**（防"只包 closing 丢掉事务上下文"导致的数据丢失）
"""

import gc
import os
import sqlite3
import tempfile
import warnings
from contextlib import closing

import pytest

from ai_collab.pack.market import PackListing
from ai_collab.pack.market_store import PackMarketStore, _connect


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def sample_listing():
    """创建示例 Pack 列表项"""
    return PackListing(
        pack_id="conn_test_001",
        pack_name="Connection Test Pack",
        version="1.0.0",
        description="用于守护连接生命周期的 Pack",
        author="test_user",
        category="productivity",
        tags=["test", "connection"],
    )


@pytest.fixture
def tracked_connections(monkeypatch):
    """捕获 market_store 打开的所有 SQLite 连接。

    ``market_store`` 用 ``import sqlite3`` 后调用 ``sqlite3.connect``，
    因此补丁打在 ``sqlite3`` 模块上；monkeypatch 会在用例结束后自动还原。
    """
    created: list[sqlite3.Connection] = []
    real_connect = sqlite3.connect

    def tracking_connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        created.append(conn)
        return conn

    monkeypatch.setattr(sqlite3, "connect", tracking_connect)
    return created


class TestConnectionIsClosed:
    """连接必须在操作结束后关闭"""

    def test_all_connections_closed_after_store_use(self, temp_db, tracked_connections):
        """store 的所有连接在操作返回后都应处于关闭状态"""
        store = PackMarketStore(temp_db)
        store.list_listings()

        assert tracked_connections, "预期至少打开一个连接，实际一个都没有"

        for conn in tracked_connections:
            with pytest.raises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")

    def test_connections_closed_after_write(self, temp_db, tracked_connections, sample_listing):
        """写入路径的连接同样必须关闭"""
        store = PackMarketStore(temp_db)
        store.create_listing(sample_listing)

        assert tracked_connections
        for conn in tracked_connections:
            with pytest.raises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")

    def test_connection_closed_even_when_body_raises(self, temp_db, tracked_connections):
        """上下文块内抛异常时连接也必须关闭（不能因异常路径泄漏）"""
        with pytest.raises(RuntimeError, match="boom"):
            with _connect(temp_db) as conn:
                conn.execute("CREATE TABLE t (x INT)")
                raise RuntimeError("boom")

        assert tracked_connections
        for conn in tracked_connections:
            with pytest.raises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")

    def test_transaction_rolled_back_when_body_raises(self, temp_db):
        """异常时 DML 必须回滚——不能留下半截写入

        注意 SQLite 语义：DDL（CREATE TABLE）在 legacy transaction 模式下是自动提交的，
        只有 DML（INSERT/UPDATE/DELETE）受事务回滚保护。
        因此这里断言「表存在但没有数据」，而不是「表不存在」。
        """
        with pytest.raises(RuntimeError):
            with _connect(temp_db) as conn:
                conn.execute("CREATE TABLE t (x INT)")
                conn.execute("INSERT INTO t VALUES (1)")
                raise RuntimeError("boom")

        with closing(sqlite3.connect(temp_db)) as probe:
            rows = probe.execute("SELECT * FROM t").fetchall()
        assert rows == [], f"异常路径下 INSERT 未被回滚: {rows}"

    def test_no_unclosed_database_resource_warning(self, temp_db):
        """不产生 ResourceWarning: unclosed database"""
        # 先回收上一轮遗留的垃圾对象，避免跨用例污染本用例的告警窗口
        gc.collect()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")

            store = PackMarketStore(temp_db)
            store.list_listings()
            gc.collect()

        leaks = [str(w.message) for w in caught if "unclosed database" in str(w.message)]
        assert not leaks, f"检测到未关闭的 SQLite 连接: {leaks}"


class TestTransactionSemantics:
    """事务语义必须保留——修连接泄漏不能以丢数据为代价"""

    def test_write_is_persisted(self, temp_db, sample_listing):
        """写入后能读回，说明事务确实提交了"""
        store = PackMarketStore(temp_db)

        assert store.create_listing(sample_listing) is True

        loaded = store.get_listing(sample_listing.pack_id)
        assert loaded is not None
        assert loaded.pack_name == sample_listing.pack_name
        assert loaded.version == sample_listing.version

    def test_write_visible_from_a_fresh_connection(self, temp_db, sample_listing):
        """独立连接能读到数据，证明数据真正落盘而非仅在内存事务里"""
        store = PackMarketStore(temp_db)
        store.create_listing(sample_listing)

        # 用完全独立的连接读取，绕开 store 自身的连接
        with closing(sqlite3.connect(temp_db)) as conn:
            rows = conn.execute("SELECT pack_name FROM pack_listings WHERE pack_id = ?", (sample_listing.pack_id,)).fetchall()

        assert rows, "数据未落盘：独立连接读不到刚写入的记录"
        assert rows[0][0] == sample_listing.pack_name

    def test_delete_is_persisted(self, temp_db, sample_listing):
        """删除同样需要真正落盘"""
        store = PackMarketStore(temp_db)
        store.create_listing(sample_listing)

        assert store.delete_listing(sample_listing.pack_id) is True
        assert store.get_listing(sample_listing.pack_id) is None
