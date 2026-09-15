"""
notification.py 的最小测试覆盖
"""

import os
import json
import pytest
from unittest.mock import patch
from ai_collab import notification as notification_module
from ai_collab.notification import (
    Notification,
    NotificationMode,
    NotificationQueue,
    NotificationAPI,
    NotificationDetector,
    broadcast,
    mention,
    direct,
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
            q = NotificationQueue()
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
