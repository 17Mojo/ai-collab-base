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
        result_file="external_target/RESULT-P0-CONSENSUS-ENGINE-001.md",
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


# ---------------------------------------------------------------------------
# 角色前缀映射的四处副本必须一致（2026-10-23）
#
# 229062d 把 A/X 对调成 A.RUN→AGENT_EXEC / X.RUN→AGENT_ARCH 时，
# 只改了 config/agent-orchestration.json 这一份，漏掉了：
#   1. ai_collab/orchestration.py 的 DEFAULT_COMMAND_PREFIXES（内置兜底）
#   2. config/agent-orchestration.template.json（新工作区的冷启动模板）
#   3. config/agent-orchestration.json 三个快照里的 config_copy（回滚目标）
# 结果：任何新工作区冷启动都会拿回倒挂映射，把 229062d 想修掉的语义又装回去。
#
# 不变量：**角色 → 前缀的映射，四处副本必须逐字相同**。
# ---------------------------------------------------------------------------

STANDARD_PREFIX_KEYS = ("A.RUN", "X.RUN", "C.RUN")
TEMPLATE_CONFIG = REPO_ROOT / "config" / "agent-orchestration.template.json"


def _standard_prefixes(mapping: dict) -> dict[str, str]:
    return {key: str(mapping.get(key)) for key in STANDARD_PREFIX_KEYS}


def _live_prefixes() -> dict[str, str]:
    payload = json.loads(ORCHESTRATION_CONFIG.read_text(encoding="utf-8"))
    return _standard_prefixes(payload.get("command_prefixes", {}))


def test_builtin_default_prefixes_match_live_config():
    """内置兜底默认值不得与仓库配置脱节。"""
    assert _standard_prefixes(OrchestrationConfig.DEFAULT_COMMAND_PREFIXES) == _live_prefixes()


def test_template_prefixes_match_live_config():
    """新工作区的冷启动模板不得与仓库配置脱节。"""
    payload = json.loads(TEMPLATE_CONFIG.read_text(encoding="utf-8"))
    assert _standard_prefixes(payload.get("command_prefixes", {})) == _live_prefixes()


def test_snapshot_rollback_targets_match_live_config():
    """快照是回滚目标，回滚到倒挂映射等于把 bug 装回去。"""
    payload = json.loads(ORCHESTRATION_CONFIG.read_text(encoding="utf-8"))
    snapshots = payload.get("snapshots") or []
    assert snapshots, "配置里应当存在快照"
    for snapshot in snapshots:
        config_copy = snapshot.get("config_copy") or {}
        assert _standard_prefixes(config_copy.get("command_prefixes", {})) == _live_prefixes(), (
            f"快照 {snapshot.get('snapshot_id')} 的回滚目标前缀映射与仓库配置不一致"
        )


def test_workspace_bootstrapped_from_template_matches_live_config(tmp_path):
    """行为级：从模板冷启动一个空工作区，得到的映射必须与仓库配置一致。"""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "agent-orchestration.template.json").write_text(
        TEMPLATE_CONFIG.read_text(encoding="utf-8"), encoding="utf-8"
    )

    config = OrchestrationConfig(workspace_path=str(tmp_path))
    assert config.load() is True
    assert _standard_prefixes(config.config.get("command_prefixes", {})) == _live_prefixes()


# ---------------------------------------------------------------------------
# 角色派生层（2026-10-23）
#
# 工单未显式声明 assignee_role 时，state_manager._default_assignee_role
# 按编排配置的 provider→role 绑定反查；provider 没有绑定时退到静态兜底表。
#
# 已知语义边界（codex）：codex 在编排配置里没有绑定任何角色，
# 静态兜底表把它派到 AGENT_TEST —— 而 AGENT_TEST 的在位者是 claude_code。
# 于是 codex 的工单派生出角色字母 C，与 claude_code 的 AGENT_TEST 席位同字母。
#
# 这**不是**字母池不重叠的违规：角色字母标识的是「席位」而不是「厂商」，
# 同一个席位换人坐，前缀当然不变。归属靠 task_id 判定
# （scripts/agent_receipt_bridge.py 的 has_explicit_ack 按 task_id 匹配），
# 仓库里不存在「前缀 → provider」的反向查找，所以不产生误路由。
# 唯一的隐患是：codex 目前 connection_status=unavailable，
# 一旦启用，它 payload 里的 C.RUN 会指向 claude_code 占的席位。
#
# 这里把语义钉死，让以后要改它的人是有意为之，而不是误改。
# ---------------------------------------------------------------------------


def _derived_role(assignee: str) -> str | None:
    from ai_collab.state_manager import StateManager

    return StateManager(workspace_path=str(REPO_ROOT))._default_assignee_role(assignee)


def test_derived_role_follows_orchestration_bindings():
    """provider 在编排配置里有绑定时，派生的角色必须是它占的席位之一。"""
    bindings = _role_bindings()
    for provider, roles in bindings.items():
        derived = _derived_role(provider)
        assert derived in roles, (
            f"{provider} 在编排配置里占 {roles}，派生角色却是 {derived}"
        )


def test_unbound_provider_derives_the_static_fallback_seat():
    """没有绑定的 provider 退到静态兜底表（codex → AGENT_TEST）。"""
    assert "codex" not in _role_bindings()
    assert _derived_role("codex") == "AGENT_TEST"


def test_role_letter_identifies_the_seat_not_the_vendor():
    """角色字母标识席位：codex 坐 AGENT_TEST 与 claude_code 同字母，且是刻意的。"""
    from ai_collab.role_prefix import resolve_hints

    codex = resolve_hints("codex", assignee_role="AGENT_TEST", workspace=REPO_ROOT)
    claude = resolve_hints("claude_code", assignee_role="AGENT_TEST", workspace=REPO_ROOT)
    assert codex == claude == ("C.RUN", "C.ACK")

    # 但没有角色声明时，codex 走自己的 provider 前缀，与任何角色都不撞。
    assert resolve_hints("codex", assignee_role=None, workspace=REPO_ROOT) == ("O.RUN", "O.ACK")


if __name__ == "__main__":
    pytest.main([__file__])
