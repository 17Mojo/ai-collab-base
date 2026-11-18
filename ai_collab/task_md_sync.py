"""从 `collaboration/tasks/TASK-*.md` 读取工单事实的纯函数。

这里只做「读」：解析 frontmatter、挑文件。写账本的逻辑在
`StateManager.sync_tasks_from_md()`，让状态变更留在状态模块内，
并保持 `scripts/verify_task_file_contracts.py` 与本模块共用同一套解析约定。

为什么不直接用 `TASK_*.md`：本仓工单名是 `TASK-P1-<名字>-001.md`（连字符），
下划线写法一个都匹配不到。2026-10-27 踩过这个坑，两种写法都收，避免再次漏检。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

IDENTITY_FIELDS = ("session_id", "model_id")


def parse_frontmatter(path: Path) -> dict[str, Any]:
    """读 `---` 包裹的 YAML frontmatter；没有就返回空字典，不抛异常。"""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    _, frontmatter, _body = text.split("---", 2)
    parsed = yaml.safe_load(frontmatter) or {}
    return parsed if isinstance(parsed, dict) else {}


def collect_task_files(tasks_dir: Path, only: list[str] | None = None) -> list[Path]:
    """挑出工单文件，按文件名排序以保证同步结果可复现。"""
    if only:
        return [tasks_dir / f"{task_id}.md" for task_id in only]
    found = {p for pattern in ("TASK-*.md", "TASK_*.md") for p in tasks_dir.glob(pattern) if p.is_file()}
    return sorted(found)


def declared_identity(frontmatter: dict[str, Any]) -> dict[str, str]:
    """只返回 md 中**已声明**的身份字段。

    空字符串与缺字段等同对待。刻意不在这里做补全或推导——历史工单的会话多数已结束，
    注册表没有事实可依，任何填充都是编造。判定 legacy / partial 是 `resolve_identity` 的职责。
    """
    result: dict[str, str] = {}
    for field in IDENTITY_FIELDS:
        value = frontmatter.get(field)
        if isinstance(value, str) and value.strip():
            result[field] = value.strip()
    return result
