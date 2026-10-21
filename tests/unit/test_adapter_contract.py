import json
from pathlib import Path

from ai_collab.adapters.claude_adapter import get_claude_adapter_contract
from ai_collab.adapters.codearts_adapter import get_codearts_adapter_contract
from ai_collab.intervention_queue import enqueue_intervention


def _write_workspace_config(workspace: Path) -> None:
    config = {
        "version": "1.0.0",
        "sessionOrchestration": {
            "claudeAdapter": {
                "enabled": True,
                "channel": "claude-main",
                "bridgeCommand": "",
                "deliveryStatusOnSuccess": "queued_for_delivery",
                "report": "logs/claude_adapter_report.json",
                "history": "logs/claude_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CLAUDE_ADAPTER_SUMMARY_latest.md",
                "eventDir": "collaboration/monitoring/claude_push_events",
            },
            "codeartsAdapter": {
                "enabled": False,
                "bridgeCommand": "",
                "deliveryStatusOnSuccess": "queued_for_delivery",
                "report": "logs/codearts_adapter_report.json",
                "history": "logs/codearts_adapter_history.jsonl",
                "summary": "collaboration/monitoring/CODEARTS_ADAPTER_SUMMARY_latest.md",
                "eventDir": "collaboration/monitoring/codearts_pull_events",
            },
            "registryState": "logs/session_registry_state.json",
            "registryHistory": "logs/session_registry_history.jsonl",
            "registrySummary": "collaboration/monitoring/SESSION_REGISTRY_SUMMARY_latest.md",
            "interventionState": "logs/session_intervention_state.json",
            "interventionHistory": "logs/session_intervention_history.jsonl",
            "interventionSummary": "collaboration/monitoring/SESSION_INTERVENTION_SUMMARY_latest.md",
        },
    }
    vscode_dir = workspace / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    (vscode_dir / "ai-collab.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_claude_adapter_contract_exposes_push_and_heartbeat(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)

    contract = get_claude_adapter_contract()
    contract.register_session(workspace=workspace, session_id="claude-main")
    enqueue_intervention(
        workspace=workspace,
        session_id="claude-main",
        assignee="claude_code",
        reason_code="missing_explicit_ack",
        severity="high",
        message_artifact="collaboration/monitoring/session_interventions/claude.md",
        intervention_id="contract-claude-001",
    )

    heartbeat = contract.heartbeat(workspace=workspace)

    assert contract.capability == "push"
    assert contract.push_interventions is not None
    assert contract.pull_interventions is None
    assert heartbeat["session_registered"] is True
    assert heartbeat["session_id"] == "claude-main"
    assert heartbeat["open_intervention_count"] == 1


def test_codearts_adapter_contract_exposes_pull_and_heartbeat(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_workspace_config(workspace)

    contract = get_codearts_adapter_contract()
    contract.register_session(workspace=workspace, session_id="codearts-main")
    enqueue_intervention(
        workspace=workspace,
        session_id="codearts-main",
        assignee="codearts_agent",
        reason_code="unregistered_session",
        severity="medium",
        message_artifact="collaboration/monitoring/session_interventions/codearts.md",
        intervention_id="contract-codearts-001",
    )

    heartbeat = contract.heartbeat(workspace=workspace)

    assert contract.capability == "pull"
    assert contract.push_interventions is None
    assert contract.pull_interventions is not None
    assert heartbeat["session_registered"] is True
    assert heartbeat["session_id"] == "codearts-main"
    assert heartbeat["open_intervention_count"] == 1



class TestBaseAIAdapterContract:
    """BaseAIAdapter 接口契约测试 - 覆盖 base_adapter.py (11-50)"""

    def test_subclass_must_implement_abstract_methods(self):
        """子类必须实现所有 abstractmethod"""
        from abc import ABC
        from ai_collab.adapters.base_adapter import BaseAIAdapter
        # 尝试实例化直接失败
        try:
            BaseAIAdapter("test")
            assert False, "Should not instantiate abstract class"
        except TypeError:
            pass  # expected

    def test_concrete_subclass_minimal(self):
        """最小具体子类可实例化"""
        from ai_collab.adapters.base_adapter import BaseAIAdapter

        class MinimalAdapter(BaseAIAdapter):
            def connect(self) -> bool:
                self.is_connected = True
                return True
            def send_message(self, message, context=None):
                return {"sent": True, "msg": message}
            def receive_message(self, timeout=30):
                return {"received": True}
            def disconnect(self) -> bool:
                self.is_connected = False
                return True

        adapter = MinimalAdapter("test_platform")
        assert adapter.platform_name == "test_platform"
        assert adapter.is_connected is False
        assert adapter.session_id is None
        assert adapter.config == {}

    def test_get_platform_info(self):
        """get_platform_info 返回完整信息"""
        from ai_collab.adapters.base_adapter import BaseAIAdapter

        class TestAdapter(BaseAIAdapter):
            def connect(self): return True
            def send_message(self, message, context=None): return {}
            def receive_message(self, timeout=30): return None
            def disconnect(self): return True

        adapter = TestAdapter("chatgpt", {"api_key": "sk-123"})
        info = adapter.get_platform_info()
        assert info["platform_name"] == "chatgpt"
        assert info["is_connected"] is False
        assert info["config"] == {"api_key": "sk-123"}

    def test_log_action(self, capsys):
        """log_action 打印 action + details"""
        from ai_collab.adapters.base_adapter import BaseAIAdapter

        class TestAdapter(BaseAIAdapter):
            def connect(self): return True
            def send_message(self, message, context=None): return {}
            def receive_message(self, timeout=30): return None
            def disconnect(self): return True

        adapter = TestAdapter("claude")
        adapter.log_action("send", {"to": "user"})
        captured = capsys.readouterr()
        assert "[claude]" in captured.out
        assert "send" in captured.out
        assert "user" in captured.out

    def test_context_manager_protocol(self):
        """__enter__/__exit__ 实现 context manager"""
        from ai_collab.adapters.base_adapter import BaseAIAdapter

        class TestAdapter(BaseAIAdapter):
            def __init__(self, name):
                super().__init__(name)
                self.connected_count = 0
                self.disconnected_count = 0
            def connect(self):
                self.connected_count += 1
                self.is_connected = True
                return True
            def send_message(self, message, context=None): return {}
            def receive_message(self, timeout=30): return None
            def disconnect(self):
                self.disconnected_count += 1
                self.is_connected = False
                return True

        with TestAdapter("test") as adapter:
            assert adapter.connected_count == 1
            assert adapter.is_connected is True
        assert adapter.disconnected_count == 1
        assert adapter.is_connected is False

    def test_exception_classes(self):
        """异常类层次结构"""
        from ai_collab.adapters.base_adapter import (
            AIAdapterError, ConnectionError, MessageError, TimeoutError
        )
        # AIAdapterError 是基类
        assert issubclass(ConnectionError, AIAdapterError)
        assert issubclass(MessageError, AIAdapterError)
        assert issubclass(TimeoutError, AIAdapterError)
        # 可实例化
        assert isinstance(ConnectionError("test"), AIAdapterError)
        assert isinstance(MessageError("test"), AIAdapterError)
        assert isinstance(TimeoutError("test"), AIAdapterError)
