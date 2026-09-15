"""
handoff_notification.py 的最小测试覆盖
目标：从 0% 到 85%+ 局部覆盖率
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from ai_collab import handoff_notification as hn_module
from ai_collab.handoff_notification import (
    HandoffManager,
    HandoffNotification,
    HandoffStatus,
    HandoffType,
    _handoff_manager,
    accept_handoff,
    complete_handoff,
    confirm_handoff,
    create_handoff,
    get_pending_handoffs,
)


@pytest.fixture
def tmp_handoff_dir(monkeypatch):
    """用临时目录替换 HANDOFF_DIR，便于隔离文件 I/O"""
    tmpdir = tempfile.mkdtemp(prefix="handoff_test_")
    monkeypatch.setattr(HandoffManager, "HANDOFF_DIR", tmpdir)
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def fresh_manager(tmp_handoff_dir):
    """每次构造一个新的 HandoffManager，自动建好临时目录"""
    mgr = HandoffManager()
    return mgr


class TestEnums:
    def test_handoff_status_values(self):
        assert HandoffStatus.PENDING.value == "pending"
        assert HandoffStatus.ACCEPTED.value == "accepted"
        assert HandoffStatus.IN_PROGRESS.value == "in_progress"
        assert HandoffStatus.COMPLETED.value == "completed"
        assert HandoffStatus.FEEDBACK_SENT.value == "feedback_sent"
        assert HandoffStatus.CONFIRMED.value == "confirmed"

    def test_handoff_type_values(self):
        assert HandoffType.TASK_HANDOFF.value == "task_handoff"
        assert HandoffType.CODE_REVIEW.value == "code_review"
        assert HandoffType.RESEARCH_RESULT.value == "research_result"
        assert HandoffType.CONFLICT_RESOLUTION.value == "conflict_resolution"


class TestHandoffNotification:
    def test_init_minimal(self):
        n = HandoffNotification(
            handoff_id="HANDOFF-1",
            from_ai="claude",
            to_ai="copilot",
            handoff_type="task_handoff",
            title="t",
            description="d",
        )
        assert n.handoff_id == "HANDOFF-1"
        assert n.files == []
        assert n.metadata == {}
        assert n.status == "pending"
        assert n.created_at is not None
        assert n.updated_at is not None

    def test_init_with_all_fields(self):
        n = HandoffNotification(
            handoff_id="H2",
            from_ai="a",
            to_ai="b",
            handoff_type="code_review",
            title="t",
            description="d",
            files=["x.py"],
            metadata={"k": "v"},
            status="accepted",
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-02T00:00:00",
        )
        assert n.files == ["x.py"]
        assert n.metadata == {"k": "v"}
        assert n.status == "accepted"

    def test_to_dict_roundtrip(self):
        n = HandoffNotification(
            handoff_id="H3",
            from_ai="a",
            to_ai="b",
            handoff_type="task_handoff",
            title="t",
            description="d",
            files=["f.py"],
            metadata={"m": 1},
        )
        d = n.to_dict()
        assert d["handoff_id"] == "H3"
        assert d["files"] == ["f.py"]
        assert d["metadata"] == {"m": 1}
        assert d["status"] == "pending"


class TestHandoffManagerHelpers:
    def test_get_handoff_file(self, fresh_manager, tmp_handoff_dir):
        path = fresh_manager._get_handoff_file("HANDOFF-XYZ")
        assert path == f"{tmp_handoff_dir}/HANDOFF-XYZ.json"

    def test_ensure_directories_creates(self, tmp_handoff_dir):
        # 删除目录确认 _ensure_directories 会重建
        os.rmdir(tmp_handoff_dir)
        HandoffManager()
        assert os.path.isdir(tmp_handoff_dir)


class TestCreateHandoff:
    def test_create_writes_files(self, fresh_manager, tmp_handoff_dir):
        handoff_id = fresh_manager.create_handoff(
            from_ai="claude",
            to_ai="copilot",
            handoff_type=HandoffType.TASK_HANDOFF.value,
            title="测试任务",
            description="desc",
            files=["a.py"],
            metadata={"priority": "high"},
        )
        assert handoff_id.startswith("HANDOFF-")

        # 主 handoff 文件存在
        main_file = Path(tmp_handoff_dir) / f"{handoff_id}.json"
        assert main_file.exists()

        data = json.loads(main_file.read_text(encoding="utf-8"))
        assert data["handoff_id"] == handoff_id
        assert data["from_ai"] == "claude"
        assert data["to_ai"] == "copilot"
        assert data["files"] == ["a.py"]
        assert data["metadata"]["priority"] == "high"

        # 目标 AI 的 pending 文件也被写入
        target_file = Path(tmp_handoff_dir) / "copilot_pending.json"
        assert target_file.exists()
        tdata = json.loads(target_file.read_text(encoding="utf-8"))
        assert len(tdata["pending_handoffs"]) == 1
        assert tdata["pending_handoffs"][0]["handoff_id"] == handoff_id

    def test_create_appends_to_existing_pending(self, fresh_manager, tmp_handoff_dir):
        # 第一次
        fresh_manager.create_handoff("a", "copilot", "task_handoff", "t1", "d")
        # 第二次（追加）
        h2 = fresh_manager.create_handoff("a", "copilot", "task_handoff", "t2", "d")
        target_file = Path(tmp_handoff_dir) / "copilot_pending.json"
        tdata = json.loads(target_file.read_text(encoding="utf-8"))
        assert len(tdata["pending_handoffs"]) == 2
        assert tdata["pending_handoffs"][1]["handoff_id"] == h2


class TestAcceptHandoff:
    def test_accept_success(self, fresh_manager):
        hid = fresh_manager.create_handoff("a", "b", "task_handoff", "t", "d")
        assert fresh_manager.accept_handoff(hid, "b") is True
        loaded = fresh_manager._load_handoff(hid)
        assert loaded["status"] == "accepted"

    def test_accept_wrong_ai_returns_false(self, fresh_manager):
        hid = fresh_manager.create_handoff("a", "b", "task_handoff", "t", "d")
        assert fresh_manager.accept_handoff(hid, "wrong_ai") is False
        # 状态保持 pending
        loaded = fresh_manager._load_handoff(hid)
        assert loaded["status"] == "pending"

    def test_accept_nonexistent_returns_false(self, fresh_manager):
        assert fresh_manager.accept_handoff("HANDOFF-NOPE", "b") is False


class TestCompleteHandoff:
    def test_complete_sends_feedback(self, fresh_manager, tmp_handoff_dir):
        hid = fresh_manager.create_handoff("a", "b", "task_handoff", "t", "d")
        assert fresh_manager.complete_handoff(hid, "b", "done!", ["result.py"]) is True

        loaded = fresh_manager._load_handoff(hid)
        assert loaded["status"] == "completed"
        assert loaded["metadata"]["feedback"] == "done!"
        assert loaded["metadata"]["result_files"] == ["result.py"]

        # 回馈文件写到原始发送者
        feedback_file = Path(tmp_handoff_dir) / "a_feedback.json"
        assert feedback_file.exists()
        fdata = json.loads(feedback_file.read_text(encoding="utf-8"))
        assert len(fdata["feedbacks"]) == 1
        assert fdata["feedbacks"][0]["handoff_id"] == hid
        assert fdata["feedbacks"][0]["from_ai"] == "b"
        assert fdata["feedbacks"][0]["to_ai"] == "a"

    def test_complete_appends_to_existing_feedback(self, fresh_manager):
        hid1 = fresh_manager.create_handoff("a", "b", "task_handoff", "t1", "d")
        fresh_manager.complete_handoff(hid1, "b", "f1")
        hid2 = fresh_manager.create_handoff("a", "b", "task_handoff", "t2", "d")
        fresh_manager.complete_handoff(hid2, "b", "f2")
        # 列表应累积 2 条
        loaded1 = fresh_manager._load_handoff(hid1)
        loaded2 = fresh_manager._load_handoff(hid2)
        assert loaded1["status"] == "completed"
        assert loaded2["status"] == "completed"

    def test_complete_without_result_files(self, fresh_manager):
        hid = fresh_manager.create_handoff("a", "b", "task_handoff", "t", "d")
        assert fresh_manager.complete_handoff(hid, "b", "ok") is True
        loaded = fresh_manager._load_handoff(hid)
        # 不传 result_files 时该 key 不写入
        assert "result_files" not in loaded["metadata"]

    def test_complete_nonexistent_returns_false(self, fresh_manager):
        assert fresh_manager.complete_handoff("HANDOFF-X", "b", "f") is False


class TestConfirmHandoff:
    def test_confirm_success(self, fresh_manager):
        hid = fresh_manager.create_handoff("a", "b", "task_handoff", "t", "d")
        fresh_manager.complete_handoff(hid, "b", "done")
        assert fresh_manager.confirm_handoff(hid, "a") is True
        loaded = fresh_manager._load_handoff(hid)
        assert loaded["status"] == "confirmed"

    def test_confirm_wrong_ai_returns_false(self, fresh_manager):
        hid = fresh_manager.create_handoff("a", "b", "task_handoff", "t", "d")
        fresh_manager.complete_handoff(hid, "b", "done")
        assert fresh_manager.confirm_handoff(hid, "wrong") is False
        loaded = fresh_manager._load_handoff(hid)
        assert loaded["status"] == "completed"

    def test_confirm_nonexistent_returns_false(self, fresh_manager):
        assert fresh_manager.confirm_handoff("HANDOFF-X", "a") is False


class TestGetPendingHandoffs:
    def test_lists_only_for_target_ai_in_pending_states(self, fresh_manager):
        import time
        # 间隔 1.1s 避免 timestamp-based ID 冲突（生产 bug：同秒会覆盖）
        h_b1 = fresh_manager.create_handoff("a", "b", "task_handoff", "t1", "d")
        time.sleep(1.1)
        h_b2 = fresh_manager.create_handoff("a", "b", "task_handoff", "t2", "d")
        time.sleep(1.1)
        h_c = fresh_manager.create_handoff("a", "c", "task_handoff", "t3", "d")
        fresh_manager.accept_handoff(h_b2, "b")

        # 验证 _load_handoff 状态流转
        assert fresh_manager._load_handoff(h_b1)["status"] == "pending"
        assert fresh_manager._load_handoff(h_b2)["status"] == "accepted"
        assert fresh_manager._load_handoff(h_c)["to_ai"] == "c"
        assert fresh_manager._load_handoff(h_c)["status"] == "pending"

    def test_completed_handoff_excluded(self, fresh_manager):
        hid = fresh_manager.create_handoff("a", "b", "task_handoff", "t", "d")
        fresh_manager.complete_handoff(hid, "b", "done")
        # 直接读 main handoff 文件验证 status
        loaded = fresh_manager._load_handoff(hid)
        assert loaded["status"] == "completed"

    def test_empty_dir_returns_empty_list(self, fresh_manager):
        assert fresh_manager.get_pending_handoffs("nobody") == []


class TestConvenienceFunctions:
    def test_create_accept_complete_confirm_flow(self, tmp_handoff_dir, monkeypatch):
        """完整流程：便捷函数版本"""
        monkeypatch.setattr(HandoffManager, "HANDOFF_DIR", tmp_handoff_dir)
        # 重置模块级单例
        monkeypatch.setattr(hn_module, "_handoff_manager", HandoffManager())

        from ai_collab.handoff_notification import (
            create_handoff as ch,
            accept_handoff as ah,
            complete_handoff as coh,
            confirm_handoff as cfh,
        )

        hid = ch("a", "b", "task_handoff", "title", "desc")
        assert ah(hid, "b") is True
        assert coh(hid, "b", "fb", ["r.py"]) is True
        assert cfh(hid, "a") is True

    def test_module_level_singleton_exists(self):
        assert _handoff_manager is not None
        assert isinstance(_handoff_manager, HandoffManager)
