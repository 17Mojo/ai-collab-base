"""角色命令前缀与 ACK 前缀的统一解析。

背景（2026-10-22 Claude Code × CodeArts 共创搭建）：

本仓库长期存在两套命令命名空间：

- **角色命名空间**：`config/agent-orchestration.json` 的 `command_prefixes`，
  例如 `X.RUN → AGENT_EXEC`、`A.RUN → AGENT_ARCH`。
- **provider 命名空间**：`ai_collab/ack_protocol.py` 里硬编码的
  `{"claude_code": "C", "codearts_agent": "A", "codex": "X"}`。

两边都叫 "A"，指代的对象却不同。派发 payload 用 provider 命名空间写
"A.RUN"，角色表却说 A.RUN 是 AGENT_ARCH；结果 CodeArts 收到的执行提示
与角色表对不上，ACK 前缀也跟着错位。

本模块把两套命名空间收敛成一套：

- **角色命名空间是权威**：`command_prefixes` 决定 role → `X.RUN`。
- **provider 前缀由角色派生**：provider 绑定的角色 → 该角色的命令前缀
  → 首字母即 ACK 前缀（`A.RUN` → `A.ACK`）。
- 角色名或编排配置缺失时，退回既有的硬编码兜底表，不改变旧行为。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# provider → ACK 前缀的兜底表（编排配置不可用时使用）。
# 与 ai_collab/ack_protocol.py 的 _ACK_PREFIX 保持一致，
# tests/unit/test_ack_prefix_consistency.py 会强制两者同步。
FALLBACK_ACK_PREFIX: dict[str, str] = {
    "claude_code": "C",
    "codearts_agent": "A",
    "codex": "X",
}

# provider → 默认角色代号（编排配置缺失时使用）
FALLBACK_ROLE_BY_PROVIDER: dict[str, str] = {
    "codearts_agent": "AGENT_EXEC",
    "claude_code": "AGENT_ARCH",
    "codex": "AGENT_TEST",
}


def _load_orchestration(workspace: Path | str | None) -> Any | None:
    try:
        from .orchestration import OrchestrationConfig
    except ImportError:  # pragma: no cover - 编排模块不可用时降级
        return None

    root = str(workspace or "").strip()
    if not root:
        root = os.getcwd()
    try:
        config = OrchestrationConfig(workspace_path=root)
        if not config.load():
            return None
    except OSError:
        return None
    return config


def resolve_role_for_provider(
    provider_id: str,
    *,
    workspace: Path | str | None = None,
) -> str | None:
    """provider → 角色代号（优先编排配置，其次兜底表）。"""
    normalized = str(provider_id or "").strip().lower()
    if not normalized:
        return None
    config = _load_orchestration(workspace)
    if config is not None:
        role_id = config.get_role_for_provider(normalized)
        if role_id:
            return role_id
    return FALLBACK_ROLE_BY_PROVIDER.get(normalized)


def resolve_run_hint(
    provider_id: str,
    *,
    assignee_role: str | None = None,
    workspace: Path | str | None = None,
) -> str:
    """provider → RUN 提示（如 'A.RUN'）。

    与 ACK 提示同源：先按工单声明的角色取角色命令前缀，
    否则取 provider 在 provider_registry 里声明的 fallback_ack_prefix。
    """
    run_hint, _ = resolve_hints(
        provider_id, assignee_role=assignee_role, workspace=workspace
    )
    return run_hint


def resolve_ack_prefix(
    provider_id: str,
    *,
    assignee_role: str | None = None,
    workspace: Path | str | None = None,
) -> str:
    """provider → ACK 前缀（如 'A'）。

    优先用工单声明的角色（PROTOCOL §7.3 的 assignee_role），
    其次用编排配置里 provider 绑定的角色，最后退回兜底表。
    """
    _, ack_hint = resolve_hints(
        provider_id, assignee_role=assignee_role, workspace=workspace
    )
    return ack_hint.split(".", 1)[0]


def resolve_hints(
    provider_id: str,
    *,
    assignee_role: str | None = None,
    workspace: Path | str | None = None,
) -> tuple[str, str]:
    """provider → (RUN 提示, ACK 提示)。

    两条提示必须同源，否则派发 payload 会告诉对方用 "A.RUN" 触发、
    却要求回 "C.ACK"，接收方无法自洽。

    解析顺序：
    1. 工单声明的 `assignee_role` → 该角色的命令前缀（角色命名空间，权威）
    2. `provider_registry[provider].fallback_ack_prefix`（provider 命名空间）
    3. 硬编码兜底表
    """
    normalized = str(provider_id or "").strip().lower()

    prefix = ""
    config = _load_orchestration(workspace)
    if config is not None:
        role_id = str(assignee_role or "").strip()
        if role_id:
            role_prefix = config.get_command_prefix_for_role(role_id)
            if role_prefix:
                prefix = role_prefix.split(".", 1)[0].strip()
        if not prefix and config.providers:
            entry = config.providers.get(normalized)
            if entry is not None:
                prefix = str(
                    getattr(entry, "extra", {}).get("fallback_ack_prefix") or ""
                ).strip()

    if not prefix:
        prefix = FALLBACK_ACK_PREFIX.get(normalized, "")

    if not prefix:
        prefix = "X"

    return f"{prefix}.RUN", f"{prefix}.ACK"


def resolve_ack_hint(
    provider_id: str,
    *,
    assignee_role: str | None = None,
    workspace: Path | str | None = None,
) -> str:
    """provider → ACK 提示（如 'A.ACK'）。"""
    _, ack_hint = resolve_hints(
        provider_id, assignee_role=assignee_role, workspace=workspace
    )
    return ack_hint
