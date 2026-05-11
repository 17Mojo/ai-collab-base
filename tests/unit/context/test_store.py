"""
Context 持久化存储测试
"""


import pytest

from ai_collab.context.store import ContextStore


@pytest.fixture
def store(tmp_path):
    """创建临时存储"""
    db_path = str(tmp_path / "test_contexts.db")
    s = ContextStore(db_path)
    yield s
    s.close()


@pytest.fixture
def sample_context():
    """示例 Context 数据"""
    return {
        "name": "Test Context",
        "scenario": "coding",
        "metadata": {"priority": "high"},
        "file_contexts": [
            {"path": "src/main.py", "language": "python", "size": 100},
            {"path": "src/utils.py", "language": "python", "size": 50},
        ],
        "notebooklm": {"notebook_id": "nb-123", "sources": ["doc1"]},
        "tags": ["python", "backend"],
    }


class TestContextStore:
    """Context 持久化存储测试"""

    def test_save_and_get(self, store, sample_context):
        """保存和获取"""
        context_id = store.save(sample_context)
        assert context_id

        result = store.get(context_id)
        assert result is not None
        assert result["name"] == "Test Context"
        assert result["scenario"] == "coding"

    def test_save_with_custom_id(self, store, sample_context):
        """使用自定义 ID 保存"""
        sample_context["context_id"] = "custom-id-123"
        context_id = store.save(sample_context)
        assert context_id == "custom-id-123"

    def test_update_existing(self, store, sample_context):
        """更新已存在的 Context"""
        context_id = store.save(sample_context)
        sample_context["context_id"] = context_id
        sample_context["name"] = "Updated Name"
        store.save(sample_context)

        result = store.get(context_id)
        assert result["name"] == "Updated Name"

    def test_get_nonexistent(self, store):
        """获取不存在的 Context"""
        result = store.get("nonexistent-id")
        assert result is None

    def test_list_contexts(self, store):
        """列出 Context"""
        for i in range(5):
            store.save({"name": f"Context {i}", "scenario": "coding"})

        contexts = store.list_contexts(limit=3)
        assert len(contexts) == 3

    def test_list_by_scenario(self, store):
        """按场景列出"""
        store.save({"name": "Coding", "scenario": "coding"})
        store.save({"name": "Research", "scenario": "research"})
        store.save({"name": "Writing", "scenario": "writing"})

        coding = store.list_contexts(scenario="coding")
        assert len(coding) == 1
        assert coding[0]["scenario"] == "coding"

    def test_delete(self, store, sample_context):
        """删除 Context"""
        context_id = store.save(sample_context)
        assert store.delete(context_id) is True
        assert store.get(context_id) is None

    def test_delete_nonexistent(self, store):
        """删除不存在的 Context"""
        assert store.delete("nonexistent") is False

    def test_search_by_name(self, store):
        """按名称搜索"""
        store.save({"name": "Python Backend", "scenario": "coding"})
        store.save({"name": "React Frontend", "scenario": "coding"})

        results = store.search("Python")
        assert len(results) == 1
        assert results[0]["name"] == "Python Backend"

    def test_search_by_tags(self, store):
        """按标签搜索"""
        store.save({"name": "Ctx1", "scenario": "coding", "tags": ["python", "ml"]})
        store.save({"name": "Ctx2", "scenario": "coding", "tags": ["javascript"]})

        results = store.search("python")
        assert len(results) >= 1

    def test_count(self, store):
        """统计数量"""
        store.save({"name": "Ctx1", "scenario": "coding"})
        store.save({"name": "Ctx2", "scenario": "research"})
        store.save({"name": "Ctx3", "scenario": "coding"})

        assert store.count() == 3
        assert store.count(scenario="coding") == 2
        assert store.count(scenario="research") == 1

    def test_persistence(self, tmp_path, sample_context):
        """数据持久化 - 重启后数据保持"""
        db_path = str(tmp_path / "persist_test.db")

        # 写入
        store1 = ContextStore(db_path)
        context_id = store1.save(sample_context)
        store1.close()

        # 重新打开读取
        store2 = ContextStore(db_path)
        result = store2.get(context_id)
        store2.close()

        assert result is not None
        assert result["name"] == "Test Context"

    def test_file_contexts_stored(self, store, sample_context):
        """文件上下文存储"""
        context_id = store.save(sample_context)
        result = store.get(context_id)
        assert len(result["file_contexts"]) == 2
        assert result["file_contexts"][0]["path"] == "src/main.py"

    def test_notebooklm_stored(self, store, sample_context):
        """NotebookLM 上下文存储"""
        context_id = store.save(sample_context)
        result = store.get(context_id)
        assert result["notebooklm"] is not None
        assert result["notebooklm"]["notebook_id"] == "nb-123"

    def test_context_manager(self, tmp_path):
        """上下文管理器"""
        db_path = str(tmp_path / "cm_test.db")
        with ContextStore(db_path) as store:
            store.save({"name": "Test", "scenario": "coding"})
            assert store.count() == 1

    def test_offset_pagination(self, store):
        """分页偏移"""
        for i in range(10):
            store.save({"name": f"Ctx {i}", "scenario": "coding"})

        page1 = store.list_contexts(limit=5, offset=0)
        page2 = store.list_contexts(limit=5, offset=5)
        assert len(page1) == 5
        assert len(page2) == 5
        # 确保不重叠
        ids1 = {c["context_id"] for c in page1}
        ids2 = {c["context_id"] for c in page2}
        assert ids1.isdisjoint(ids2)
