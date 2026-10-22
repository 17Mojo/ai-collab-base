"""角色命名空间与 provider 命名空间的收敛测试。

背景：仓库长期有两套命令命名空间（角色 `command_prefixes` 与
provider 硬编码前缀表），同一个字母在两套里指代不同角色，
导致派发 payload 的触发词与要求的 ACK 行对不上。
`ai_collab/role_prefix.py` 把两者收敛成一套，这里守住收敛结果。
"""

import json
from pathlib import Path

import pytest

from ai_collab.dispatch_trigger import build_handoff_payload
from ai_collab.role_prefix import (
    FALLBACK_ACK_PREFIX,
    resolve_ack_prefix,
    resolve_assignee_roles,
    resolve_hints,
    resolve_run_hint,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION_CONFIG = REPO_ROOT / "config" / "agent-orchestration.json"


@pytest.fixture
def orchestration_payload():
    return json.loads(ORCHESTRATION_CONFIG.read_text(encoding="utf-8"))


class TestResolution:
    def test_role_drives_both_hints(self):
        run_hint, ack_hint = resolve_hints(
            "codearts_agent", assignee_role="AGENT_EXEC", workspace=str(REPO_ROOT)
        )
        assert run_hint == "A.RUN"
        assert ack_hint == "A.ACK"

    def test_claude_code_arch_and_test_seats_differ(self):
        arch = resolve_hints(
            "claude_code", assignee_role="AGENT_ARCH", workspace=str(REPO_ROOT)
        )
        test_seat = resolve_hints(
            "claude_code", assignee_role="AGENT_TEST", workspace=str(REPO_ROOT)
        )
        assert arch == ("X.RUN", "X.ACK")
        assert test_seat == ("C.RUN", "C.ACK")

    def test_run_and_ack_hints_always_come_from_the_same_prefix(self):
        for assignee in ("claude_code", "codearts_agent", "codex"):
            for role in (None, "AGENT_EXEC", "AGENT_ARCH", "AGENT_TEST"):
                run_hint, ack_hint = resolve_hints(
                    assignee, assignee_role=role, workspace=str(REPO_ROOT)
                )
                assert run_hint.split(".", 1)[0] == ack_hint.split(".", 1)[0]

    def test_unknown_provider_falls_back(self):
        assert resolve_ack_prefix("nobody", workspace=str(REPO_ROOT)) == "X"

    def test_fallback_table_matches_known_assignees(self):
        assert FALLBACK_ACK_PREFIX["codearts_agent"] == "A"
        assert FALLBACK_ACK_PREFIX["claude_code"] == "C"
        assert FALLBACK_ACK_PREFIX["codex"] == "X"


class TestOrchestrationCoherence:
    def test_command_prefixes_are_unique(self, orchestration_payload):
        prefixes = [
            key
            for key in orchestration_payload.get("command_prefixes", {})
            if isinstance(key, str) and key.endswith(".RUN")
        ]
        assert len(prefixes) == len(set(prefixes))

    def test_every_role_has_a_command_prefix(self, orchestration_payload):
        prefixes = orchestration_payload.get("command_prefixes", {})
        for role_id in orchestration_payload.get("roles", {}):
            assert role_id in prefixes.values(), f"角色 {role_id} 没有命令前缀"

    def test_codearts_exec_seat_uses_the_a_prefix(self, orchestration_payload):
        prefixes = orchestration_payload.get("command_prefixes", {})
        roles = orchestration_payload.get("roles", {})
        assert prefixes.get("A.RUN") == "AGENT_EXEC"
        assert roles["AGENT_EXEC"]["binding"]["provider"] == "codearts_agent"

    def test_provider_fallback_prefix_matches_bound_exec_seat(
        self, orchestration_payload
    ):
        prefixes = orchestration_payload.get("command_prefixes", {})
        registry = orchestration_payload.get("provider_registry", {})
        for role_id, role in orchestration_payload.get("roles", {}).items():
            provider = role.get("binding", {}).get("provider")
            if not provider:
                continue
            if role_id != "AGENT_EXEC":
                continue
            role_prefix = next(
                (key for key, value in prefixes.items() if value == role_id), ""
            )
            expected = registry.get(provider, {}).get("fallback_ack_prefix")
            assert role_prefix.split(".", 1)[0] == expected


class TestHandoffPayload:
    def test_payload_uses_role_scoped_hints(self):
        payload = build_handoff_payload(
            assignee="codearts_agent",
            trigger_phrase="2X DISPATCH CodeArts",
            orders_relpath="collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md",
            section_markdown="## 发送给 `CodeArts` (`codearts_agent`)\n\n- TASK-001",
            assignee_role="AGENT_EXEC",
            workspace=str(REPO_ROOT),
        )
        assert "A.RUN" in payload
        assert "A.ACK" in payload
        assert "X.RUN" not in payload
        assert "C.ACK" not in payload

    def test_payload_without_role_uses_provider_fallback(self):
        payload = build_handoff_payload(
            assignee="codearts_agent",
            trigger_phrase="2X DISPATCH CodeArts",
            orders_relpath="collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md",
            section_markdown="## 发送给 `CodeArts` (`codearts_agent`)\n\n- TASK-001",
            workspace=str(REPO_ROOT),
        )
        assert "A.RUN" in payload
        assert "A.ACK" in payload


class TestAssigneeRoleResolution:
    """`resolve_assignee_roles` 从控制面状态推导执行方的角色席位。

    watchdog / session_health 的提示词必须跟着角色走：
    一个声明为 AGENT_ARCH 的 claude_code 席位要收到 `X.RUN`，
    而不是 provider 兜底表里的 `C.RUN`。
    """

    def _write_state(self, workspace: Path, tasks: dict) -> None:
        state_file = workspace / "logs" / "collaboration_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(
            json.dumps({"tasks": tasks}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def test_single_active_task_yields_its_role(self, tmp_path: Path):
        self._write_state(
            tmp_path,
            {
                "TASK-1": {
                    "assignee": "codearts_agent",
                    "assignee_role": "AGENT_EXEC",
                    "status": "pending",
                }
            },
        )
        assert resolve_assignee_roles(tmp_path) == {"codearts_agent": "AGENT_EXEC"}

    def test_terminal_tasks_do_not_pin_a_role(self, tmp_path: Path):
        self._write_state(
            tmp_path,
            {
                "TASK-1": {
                    "assignee": "codearts_agent",
                    "assignee_role": "AGENT_EXEC",
                    "status": "completed",
                }
            },
        )
        assert resolve_assignee_roles(tmp_path) == {}

    def test_ambiguous_seat_is_not_resolved(self, tmp_path: Path):
        """同一执行方占两个角色 → 不给结论，交给 provider 兜底前缀。"""
        self._write_state(
            tmp_path,
            {
                "TASK-1": {
                    "assignee": "claude_code",
                    "assignee_role": "AGENT_ARCH",
                    "status": "pending",
                },
                "TASK-2": {
                    "assignee": "claude_code",
                    "assignee_role": "AGENT_TEST",
                    "status": "pending",
                },
            },
        )
        assert resolve_assignee_roles(tmp_path) == {}

    def test_state_file_path_follows_workspace_config(self, tmp_path: Path):
        """stateFile 由 `.vscode/ai-collab.json` 指定，读错路径会拿到空结果。"""
        config_dir = tmp_path / ".vscode"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "ai-collab.json").write_text(
            json.dumps({"stateFile": "./logs/custom_state.json"}, ensure_ascii=False),
            encoding="utf-8",
        )
        custom = tmp_path / "logs" / "custom_state.json"
        custom.parent.mkdir(parents=True, exist_ok=True)
        custom.write_text(
            json.dumps(
                {
                    "tasks": {
                        "TASK-1": {
                            "assignee": "codearts_agent",
                            "assignee_role": "AGENT_EXEC",
                            "status": "pending",
                        }
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        assert resolve_assignee_roles(tmp_path) == {"codearts_agent": "AGENT_EXEC"}

    def test_missing_state_file_returns_empty(self, tmp_path: Path):
        assert resolve_assignee_roles(tmp_path) == {}

    def test_resolved_role_drives_the_run_hint(self, tmp_path: Path):
        """角色席位决定提示词：AGENT_ARCH 席位 → X.RUN。"""
        # 编排配置是角色命名空间的权威来源，测试工作区要带同一份配置。
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "agent-orchestration.json").write_text(
            ORCHESTRATION_CONFIG.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self._write_state(
            tmp_path,
            {
                "TASK-1": {
                    "assignee": "claude_code",
                    "assignee_role": "AGENT_ARCH",
                    "status": "pending",
                }
            },
        )
        role = resolve_assignee_roles(tmp_path).get("claude_code")
        run_hint, ack_hint = resolve_hints(
            "claude_code", assignee_role=role, workspace=str(tmp_path)
        )
        assert run_hint == "X.RUN"
        assert ack_hint == "X.ACK"


if __name__ == "__main__":
    pytest.main([__file__])