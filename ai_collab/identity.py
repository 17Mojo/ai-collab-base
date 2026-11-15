"""执行主体身份：session_id + model_id。

设计契约见 openspec/changes/migrate-session-identity/design 意图（proposal.md 与
specs/task-contract/spec.md）。

为什么需要这一层：工单契约长期用 `assignee_provider`（厂商标签）承担「谁做的」，
但厂商标签回答不了「哪个会话、哪个模型」。多会话并行时同一个厂商名会同时对应多个
执行主体，工单因此无法定位到责任人。身份与路由分离后：
- 身份（session_id / model_id）是契约层事实，必须可核验；
- 路由（assignee）是运行时投递键，允许由注册表反查得到。

本模块只做规范化与判定，不写盘、不读时间以外的外部状态。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# 身份成为必填项的时间切点。此日期（含）之后创建的工单必须声明身份；
# 之前的工单按 historical 处理，缺失不判错，但会被计数。
IDENTITY_REQUIRED_SINCE = "2026-11-16"

# session_id：字母数字开头，允许 . _ : - ，长度 3–96。刻意不接受空白与斜杠，
# 避免和路径、命令行拼接混淆。
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,95}$")
# model_id：允许厂商前缀与版本号里的 . _ : + - /（如 vendor/model-1.2+flash）。
MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+-]{0,63}(?:/[A-Za-z0-9._:+-]{1,63})?$")

DECLARED = "declared"
LEGACY = "legacy"
MISSING = "missing"
INVALID = "invalid"


def normalize_session_id(value: Any) -> str | None:
    """返回规范化后的 session_id；不合法返回 None（不抛异常，由调用方决定严重级别）。"""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not SESSION_ID_PATTERN.fullmatch(normalized):
        return None
    return normalized


def normalize_model_id(value: Any) -> str | None:
    """返回规范化后的 model_id；不合法返回 None。"""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not MODEL_ID_PATTERN.fullmatch(normalized):
        return None
    return normalized


def created_on_or_after(created_at: Any, cutoff: str = IDENTITY_REQUIRED_SINCE) -> bool:
    """工单是否落在「身份必填」的时间范围内。created_at 缺失时按必填处理（fail-closed）。"""
    text = str(created_at or "").strip()
    if not text:
        return True
    return text[:10] >= cutoff


def resolve_identity(task: dict[str, Any]) -> dict[str, Any]:
    """判定单个工单的身份状态。

    返回 state ∈ {declared, legacy, missing, invalid}：
    - declared：两个字段都在且格式合法
    - legacy：切点之前创建且未声明身份（允许，需计数）
    - missing：切点之后创建但缺字段（契约不合法）
    - invalid：字段存在但格式非法（与 missing 区分，便于定位是漏填还是填错）
    """
    raw_session = task.get("session_id")
    raw_model = task.get("model_id")
    has_any = bool(str(raw_session or "").strip() or str(raw_model or "").strip())

    session_id = normalize_session_id(raw_session)
    model_id = normalize_model_id(raw_model)

    if session_id and model_id:
        return {"state": DECLARED, "session_id": session_id, "model_id": model_id, "reason": ""}

    if has_any:
        invalid = []
        if raw_session and not session_id:
            invalid.append("session_id")
        if raw_model and not model_id:
            invalid.append("model_id")
        if invalid:
            return {
                "state": INVALID,
                "session_id": session_id,
                "model_id": model_id,
                "reason": f"格式非法: {invalid}",
            }

    if not created_on_or_after(task.get("created_at")):
        return {"state": LEGACY, "session_id": session_id, "model_id": model_id, "reason": "历史工单未声明身份"}

    return {
        "state": MISSING,
        "session_id": None,
        "model_id": None,
        "reason": f"切点 {IDENTITY_REQUIRED_SINCE} 之后的工单必须声明 session_id 与 model_id",
    }


def derive_assignee_from_session(workspace: Path, session_id: str) -> str | None:
    """按会话注册表反查路由键（assignee）。查不到返回 None —— 不猜。

    这是「身份 → 路由」的桥：让新工单可以只声明身份，路由由注册表事实提供。
    注册表本身不可读时同样返回 None，由调用方拒绝创建工单。
    """
    normalized = normalize_session_id(session_id)
    if not normalized:
        return None
    try:
        from .session_registry import read_session_registry

        entries = read_session_registry(workspace=workspace)
    except (OSError, ValueError, KeyError):
        return None
    for entry in entries:
        if str(entry.get("session_id") or "").strip() != normalized:
            continue
        assignee = str(entry.get("assignee") or "").strip()
        return assignee or None
    return None
