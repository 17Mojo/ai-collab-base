"""
notification.py 的最小测试覆盖
"""

from unittest.mock import patch

from ai_collab import notification as notification_module
from ai_collab.notification import (
    Notification,
    NotificationAPI,
    NotificationDetector,
    NotificationMode,
    NotificationQueue,
    broadcast,
    direct,
    mention,
)


class TestNotificationConstants:
    def test_notification_mode_constants(self):
        assert NotificationMode.BROADCAST == "broadcast"
        assert NotificationMode.BROADCAST_MENTION == "broadcast@mention"
        assert NotificationMode.DIRECT == "direct"

    def test_priority_constants(self):
        P = notification_module.Priority
        assert P.LOW == "low"
        assert P.NORMAL == "normal"
        assert P.HIGH == "high"
        assert P.URGENT == "urgent"


class TestNotification:
    def test_init_minimal(self):
        n = Notification(content="hello")
        assert n.content == "hello"
        assert n.sender == "system"
        assert n.priority == "normal"
        assert n.mode == "broadcast"
        assert n.id is not None
        assert n.timestamp is not None

    def test_init_with_all_fields(self):
        n = Notification(
            content="urgent!",
            mode=NotificationMode.DIRECT,
            sender="claude",
            priority="high",
            mentions=["codex"],
            direct_target="codex",
            metadata={"task_id": "T-001"},
        )
        assert n.mode == "direct"
        assert n.sender == "claude"
        assert n.mentions == ["codex"]
        assert n.direct_target == "codex"
        assert n.metadata["task_id"] == "T-001"

    def test_to_dict_roundtrip(self):
        n = Notification(content="test", mode=NotificationMode.BROADCAST_MENTION, mentions=["a", "b"])
        d = n.to_dict()
        assert d["content"] == "test"
        assert d["mode"] == "broadcast@mention"
        assert d["mentions"] == ["a", "b"]


class TestNotificationQueue:
    """使用 tmp_path 隔离目录"""

    def test_init_creates_dir(self, tmp_path):
        with patch.object(NotificationQueue, "NOTIFICATION_DIR", str(tmp_path / "notifications")):
            NotificationQueue()
            assert (tmp_path / "notifications").exists()

    def test_emit_returns_id(self, tmp_path):
        with patch.object(NotificationQueue, "NOTIFICATION_DIR", str(tmp_path / "notifications")):
            q = NotificationQueue()
            n = Notification(content="test")
            msg_id = q.emit(n)
            assert msg_id == n.id

    def test_emit_appends_to_queue(self, tmp_path):
        with patch.object(NotificationQueue, "NOTIFICATION_DIR", str(tmp_path / "notifications")):
            q = NotificationQueue()
            q.emit(Notification(content="m1"))
            q.emit(Notification(content="m2"))
            messages = q._load_queue()
            assert len(messages) == 2
            assert messages[0]["content"] == "m1"
            assert messages[1]["content"] == "m2"

    def test_get_pending_broadcast(self, tmp_path):
        with patch.object(NotificationQueue, "NOTIFICATION_DIR", str(tmp_path / "notifications")):
            q = NotificationQueue()
            q.emit(Notification(content="all"))
            pending = q.get_pending("claude_code")
            assert len(pending) == 1
            assert pending[0].content == "all"

    def test_get_pending_direct_filters(self, tmp_path):
        with patch.object(NotificationQueue, "NOTIFICATION_DIR", str(tmp_path / "notifications")):
            q = NotificationQueue()
            q.emit(Notification(content="for codex", mode=NotificationMode.DIRECT, direct_target="codex"))
            assert len(q.get_pending("claude_code")) == 0
            pending = q.get_pending("codex")
            assert len(pending) == 1
            assert pending[0].direct_target == "codex"

    def test_load_empty_returns_empty_list(self, tmp_path):
        with patch.object(NotificationQueue, "NOTIFICATION_DIR", str(tmp_path / "notifications")):
            q = NotificationQueue()
            assert q._load_queue() == []


class TestNotificationAPI:
    def test_init(self, tmp_path):
        with patch.object(NotificationQueue, "NOTIFICATION_DIR", str(tmp_path / "notifications")):
            api = NotificationAPI()
            assert api.queue is not None


class TestNotificationDetector:
    def test_init(self, tmp_path):
        with patch.object(NotificationQueue, "NOTIFICATION_DIR", str(tmp_path / "notifications")):
            detector = NotificationDetector(ai_name="claude_code")
            assert detector.ai_name == "claude_code"
            assert detector.queue is not None


class TestModuleHelpers:
    """模块级 helper 函数的签名验证（避免触发文件写入副作用）"""

    def test_broadcast_signature(self):
        import inspect
        sig = inspect.signature(broadcast)
        assert "content" in sig.parameters
        assert "priority" in sig.parameters
        assert sig.parameters["priority"].default == "normal"

    def test_mention_signature(self):
        import inspect
        sig = inspect.signature(mention)
        assert "mentions" in sig.parameters
        assert "content" in sig.parameters

    def test_direct_signature(self):
        import inspect
        sig = inspect.signature(direct)
        assert "target" in sig.parameters
        assert sig.parameters["priority"].default == "high"



class TestNotificationQueueGetPending:
    def test_get_pending_broadcast(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import Notification, NotificationMode, NotificationQueue
        q = NotificationQueue()
        q.emit(Notification(content="hello", mode=NotificationMode.BROADCAST))
        pending = q.get_pending("claude_code")
        assert len(pending) == 1
        assert pending[0].content == "hello"

    def test_get_pending_broadcast_unknown_ai_excluded(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import Notification, NotificationMode, NotificationQueue
        q = NotificationQueue()
        q.emit(Notification(content="hello", mode=NotificationMode.BROADCAST))
        # Unknown AI is not in BROADCAST_TARGETS, should get nothing
        pending = q.get_pending("unknown_ai")
        assert len(pending) == 0

    def test_get_pending_broadcast_mention(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import Notification, NotificationMode, NotificationQueue
        q = NotificationQueue()
        q.emit(Notification(
            content="hello @team",
            mode=NotificationMode.BROADCAST_MENTION,
            mentions=["claude_code"]
        ))
        pending = q.get_pending("claude_code")
        assert len(pending) == 1

    def test_get_pending_direct_target_match(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import Notification, NotificationMode, NotificationQueue
        q = NotificationQueue()
        q.emit(Notification(
            content="secret",
            mode=NotificationMode.DIRECT,
            direct_target="claude_code"
        ))
        pending = q.get_pending("claude_code")
        assert len(pending) == 1
        # Other AI should not see direct message
        pending_other = q.get_pending("codex")
        assert len(pending_other) == 0

    def test_get_pending_direct_empty_target_excluded(self, tmp_path, monkeypatch):
        """DIRECT 但目标不在 BROADCAST_TARGETS 中,不被 claude_code 看到"""
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import Notification, NotificationMode, NotificationQueue
        q = NotificationQueue()
        q.emit(Notification(
            content="direct",
            mode=NotificationMode.DIRECT,
            direct_target="some_other_ai"
        ))
        # claude_code is not the target
        assert len(q.get_pending("claude_code")) == 0


class TestNotificationQueueMarkRead:
    def test_mark_read_moves_to_history(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import Notification, NotificationMode, NotificationQueue
        q = NotificationQueue()
        msg_id = q.emit(Notification(content="hello", mode=NotificationMode.BROADCAST))
        # Mark read by all broadcast targets
        for ai in q.BROADCAST_TARGETS:
            q.mark_read(msg_id, ai)
        # Now pending should be empty
        assert len(q.get_pending("claude_code")) == 0

    def test_mark_read_partial(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import Notification, NotificationMode, NotificationQueue
        q = NotificationQueue()
        msg_id = q.emit(Notification(content="hello", mode=NotificationMode.BROADCAST))
        # Only mark by claude_code
        q.mark_read(msg_id, "claude_code")
        # Still pending for others
        pending = q.get_pending("codex")
        assert len(pending) == 1

    def test_mark_read_nonexistent_message(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import NotificationQueue
        q = NotificationQueue()
        # Should not raise
        q.mark_read("MSG-NONEXISTENT", "claude_code")


class TestNotificationQueueGetUnreadCount:
    def test_get_unread_count_initial(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import NotificationQueue
        q = NotificationQueue()
        assert q.get_unread_count("claude_code") == 0

    def test_get_unread_count_after_emit(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import Notification, NotificationMode, NotificationQueue
        q = NotificationQueue()
        q.emit(Notification(content="hi", mode=NotificationMode.BROADCAST))
        q.emit(Notification(content="hi2", mode=NotificationMode.BROADCAST))
        count = q.get_unread_count("claude_code")
        assert count == 2

    def test_get_unread_count_after_read(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import Notification, NotificationMode, NotificationQueue
        q = NotificationQueue()
        msg_id = q.emit(Notification(content="hi", mode=NotificationMode.BROADCAST))
        # claude_code 标记已读
        q.mark_read(msg_id, "claude_code")
        # claude_code 看到 0,但队列中还有给其他 AI 的
        assert q.get_unread_count("claude_code") == 0


class TestNotificationAPIDirect:
    def test_direct_creates_notification(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import NotificationAPI, Priority
        api = NotificationAPI()
        msg_id = api.direct("claude_code", "秘密消息", priority=Priority.HIGH)
        assert msg_id.startswith("MSG-")

    def test_direct_writes_to_target_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import NotificationAPI, Priority
        api = NotificationAPI()
        api.direct("claude_code", "秘密消息")
        # Check notification file was written
        target_file = tmp_path / "notifications" / "claude_code_notification.json"
        assert target_file.exists()


class TestNotificationAPIMention:
    def test_mention_writes_to_all_targets(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import NotificationAPI, Priority
        api = NotificationAPI()
        msg_id = api.mention(["claude_code"], "重要通知", priority=Priority.HIGH)
        assert msg_id.startswith("MSG-")
        # Check all broadcast targets have a file
        for ai in api.queue.BROADCAST_TARGETS:
            target_file = tmp_path / "notifications" / f"{ai}_notification.json"
            assert target_file.exists()


class TestNotificationAPIWriteTarget:
    def test_write_to_target_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from ai_collab.notification import NotificationAPI, Notification, Priority
        api = NotificationAPI()
        notification = Notification(
            content="test",
            mode="direct",
            direct_target="claude_code",
            priority=Priority.HIGH
        )
        api._write_to_target("claude_code", notification, "MSG-test-1")
        target_file = tmp_path / "notifications" / "claude_code_notification.json"
        assert target_file.exists()
        import json
        data = json.loads(target_file.read_text())
        assert data["message_id"] == "MSG-test-1"
        assert data["read"] is False


class TestNotificationEnumStrings:
    def test_priority_values(self):
        from ai_collab.notification import Priority
        assert Priority.LOW == "low"
        assert Priority.NORMAL == "normal"
        assert Priority.HIGH == "high"
        assert Priority.URGENT == "urgent"

    def test_notification_mode_values(self):
        from ai_collab.notification import NotificationMode
        assert NotificationMode.BROADCAST == "broadcast"
        assert NotificationMode.BROADCAST_MENTION == "broadcast@mention"
        assert NotificationMode.DIRECT == "direct"
