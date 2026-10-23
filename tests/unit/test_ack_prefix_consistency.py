"""ACK 前缀 / 状态映射的一致性守卫。

provider → ACK 前缀的映射历史上被硬编码在三处
（ai_collab/ack_protocol.py、scripts/agent_receipt_bridge.py、
ai_collab/orchestration.py），加上 config/agent-orchestration.json 的
provider_registry 一共四处。任一处漂移都会让 ACK 行无法被识别，
这里用测试强制它们保持一致。
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ai_collab.ack_protocol import (
    _ACK_PREFIX,
    _DEFAULT_ACK_STATUS,
    SUPPORTED_ASSIGNEES,
    build_ack_line,
)
from ai_collab.orchestration import OrchestrationConfig

REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPT_SCRIPT = REPO_ROOT / "scripts" / "agent_receipt_bridge.py"
ORCHESTRATION_CONFIG = REPO_ROOT / "config" / "agent-orchestration.json"

# PROTOCOL.md：<PREFIX>.ACK|task=<ids>|status=<ok/blocked/noop>|result=<paths>
PROTOCOL_ACK_STATUSES = {"ok", "blocked", "noop"}


def _load_receipt_bridge_module():
    """按路径加载 standalone 脚本（它刻意不依赖 ai_collab 包）。"""
    source = RECEIPT_SCRIPT.read_text(encoding="utf-8")
    namespace: dict = {"__name__": "agent_receipt_bridge_under_test", "__file__": str(RECEIPT_SCRIPT)}
    exec(compile(source, str(RECEIPT_SCRIPT), "exec"), namespace)  # noqa: S102
    return namespace


def test_receipt_bridge_prefix_map_matches_ack_protocol():
    namespace = _load_receipt_bridge_module()
    for assignee in SUPPORTED_ASSIGNEES:
        assert namespace["ack_prefix_for"](assignee) == _ACK_PREFIX[assignee]


def test_orchestration_fallback_prefix_map_matches_ack_protocol():
    for assignee, prefix in _ACK_PREFIX.items():
        assert OrchestrationConfig.DEFAULT_FALLBACK_ACK_PREFIX[assignee] == prefix


def test_config_provider_registry_matches_ack_protocol():
    payload = json.loads(ORCHESTRATION_CONFIG.read_text(encoding="utf-8"))
    registry = payload.get("provider_registry", {})
    for assignee, prefix in _ACK_PREFIX.items():
        entry = registry.get(assignee)
        assert entry is not None, f"provider_registry 缺少 {assignee}"
        assert entry.get("fallback_ack_prefix") == prefix


def test_default_ack_status_stays_inside_protocol_enum():
    for assignee, status in _DEFAULT_ACK_STATUS.items():
        assert status in PROTOCOL_ACK_STATUSES, f"{assignee} 的默认 ACK 状态 {status} 违反协议枚举"


def test_receipt_bridge_status_stays_inside_protocol_enum():
    namespace = _load_receipt_bridge_module()
    for assignee in SUPPORTED_ASSIGNEES:
        assert namespace["ack_status_for"](assignee) in PROTOCOL_ACK_STATUSES


def test_codearts_ack_line_is_protocol_conformant():
    line = build_ack_line(
        assignee="codearts_agent",
        task_id="TASK-P0-CONSENSUS-ENGINE-001",
        result_file="hermes_target/RESULT-P0-CONSENSUS-ENGINE-001.md",
    )
    assert line.startswith("A.ACK|task=")
    assert "|status=ok|" in line


def test_receipt_bridge_script_still_runs_help():
    result = subprocess.run(
        [sys.executable, str(RECEIPT_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "workspace" in result.stdout


# ---------------------------------------------------------------------------
# 字母池不重叠（2026-10-23）
#
# 角色命名空间与 provider 命名空间都用单字母，字母池却是同一批，
# 于是历史上出现过 "X" 同时指代 AGENT_ARCH（角色）和 codex（provider）：
# codex 的兜底前缀是初版遗留（那时 X 是 AGENT_EXEC 的角色前缀），
# 而 229062d 把角色侧的 X 让给了 AGENT_ARCH，两边就此撞车。
#
# 不变量：**provider 兜底前缀只能与"该 provider 实际绑定的那个角色"
# 共用字母**；否则必须另取角色池之外的字母。
# ---------------------------------------------------------------------------


def _role_prefixes() -> dict[str, str]:
    payload = json.loads(ORCHESTRATION_CONFIG.read_text(encoding="utf-8"))
    prefixes = payload.get("command_prefixes", {})
    return {
        str(role): str(prefix).split(".", 1)[0].strip()
        for prefix, role in prefixes.items()
        if isinstance(prefix, str) and "." in prefix
    }


def _role_bindings() -> dict[str, set[str]]:
    payload = json.loads(ORCHESTRATION_CONFIG.read_text(encoding="utf-8"))
    bindings: dict[str, set[str]] = {}
    for role, entry in (payload.get("roles") or {}).items():
        provider = str((entry.get("binding") or {}).get("provider") or "").strip()
        if provider:
            bindings.setdefault(provider, set()).add(role)
    return bindings


def test_provider_prefix_never_collides_with_unbound_role_prefix():
    """provider 兜底前缀不得撞上"它并没有扮演"的角色前缀。"""
    role_prefixes = _role_prefixes()
    bindings = _role_bindings()
    for provider, prefix in _ACK_PREFIX.items():
        for role, role_prefix in role_prefixes.items():
            if role_prefix != prefix:
                continue
            assert role in bindings.get(provider, set()), (
                f"provider {provider} 的兜底前缀 {prefix} 与角色 {role} 撞车，"
                f"但它并未绑定该角色；ACK 行无法区分发送方"
            )


def test_codex_prefix_is_outside_role_letter_pool():
    """codex 未绑定任何角色，其前缀必须避开角色字母池。"""
    role_prefixes = set(_role_prefixes().values())
    assert _ACK_PREFIX["codex"] not in role_prefixes
    assert _ACK_PREFIX["codex"] == "O"


def test_unknown_provider_fallback_is_not_a_role_letter():
    """解析不出 provider 时的兜底前缀不能是任何角色前缀。"""
    from ai_collab.role_prefix import UNKNOWN_PROVIDER_PREFIX

    role_prefixes = set(_role_prefixes().values())
    assert UNKNOWN_PROVIDER_PREFIX not in role_prefixes
    assert UNKNOWN_PROVIDER_PREFIX == "Z"


def test_no_two_providers_share_the_same_prefix():
    prefixes = list(_ACK_PREFIX.values())
    assert len(prefixes) == len(set(prefixes))


if __name__ == "__main__":
    pytest.main([__file__])
