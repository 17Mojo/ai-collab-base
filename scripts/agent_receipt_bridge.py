#!/usr/bin/env python3
"""Agent Receipt Bridge - 自动回执桥接.

职责:
- 检测 testing 状态候选任务
- 复用完成态门禁（结果文件存在且章节完整）
- 显式 ACK 校验（cli-ack 来源）
- 自动执行 testing -> completed（支持 dry-run）
- 写入回执报告、历史、回执状态与摘要
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# 本脚本刻意不依赖 ai_collab 包（可以被单独拷走执行），
# 但 ACK 前缀的**解析规则**必须与 ai_collab.role_prefix 同源 ——
# 否则同一个工单，CLI ACK 路径给 X.ACK、桥接路径给 C.ACK，两处记录自相矛盾。
# 折中：把仓库根加进 sys.path，import 失败时再退回本地兜底表。
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


class ReceiptErrorCategory(Enum):
    """回执错误分类。"""

    RESULT_FILE_NOT_FOUND = "result_file_not_found"
    RESULT_FILE_EMPTY = "result_file_empty"
    RESULT_FILE_INVALID = "result_file_invalid"
    RESULT_FILE_MISSING_SECTIONS = "result_file_missing_sections"
    VALIDATION_FAILED = "validation_failed"
    STATE_MANAGER_REJECTED = "state_manager_rejected"
    TASK_NOT_FOUND = "task_not_found"
    TASK_NOT_IN_TESTING = "task_not_in_testing"
    OPEN_PATCH_EXISTS = "open_patch_exists"
    ACTION_REQUIRED = "action_required"
    MISSING_ACCEPTANCE_COMMANDS = "missing_acceptance_commands"
    UNKNOWN = "unknown"


RETRYABLE_CATEGORIES = frozenset(
    {
        ReceiptErrorCategory.RESULT_FILE_NOT_FOUND,
        ReceiptErrorCategory.RESULT_FILE_MISSING_SECTIONS,
        ReceiptErrorCategory.STATE_MANAGER_REJECTED,
        ReceiptErrorCategory.VALIDATION_FAILED,
    }
)


@dataclass
class ReceiptRetryConfig:
    """回执重试配置。"""

    retryable_categories: frozenset = field(default_factory=lambda: RETRYABLE_CATEGORIES)
    max_attempts: int = 3
    backoff_seconds: float = 1.0


def classify_receipt_error(exc: Exception) -> ReceiptErrorCategory:
    """将异常分类到回执错误类别。"""
    msg = str(exc).lower()
    if "result_file not found" in msg:
        return ReceiptErrorCategory.RESULT_FILE_NOT_FOUND
    if "result_file is empty" in msg or "result_file_empty" in msg:
        return ReceiptErrorCategory.RESULT_FILE_EMPTY
    if "result_file" in msg and ("missing sections" in msg or "invalid" in msg):
        return ReceiptErrorCategory.RESULT_FILE_INVALID
    if "missing acceptance_commands" in msg:
        return ReceiptErrorCategory.MISSING_ACCEPTANCE_COMMANDS
    if "validation" in msg and "fail" in msg:
        return ReceiptErrorCategory.VALIDATION_FAILED
    if "state_manager" in msg and "reject" in msg:
        return ReceiptErrorCategory.STATE_MANAGER_REJECTED
    if "task" in msg and "not found" in msg:
        return ReceiptErrorCategory.TASK_NOT_FOUND
    if "not in testing" in msg or "task_not_in_testing" in msg:
        return ReceiptErrorCategory.TASK_NOT_IN_TESTING
    if "open patch" in msg or "open_patch" in msg:
        return ReceiptErrorCategory.OPEN_PATCH_EXISTS
    if "action_required" in msg:
        return ReceiptErrorCategory.ACTION_REQUIRED
    return ReceiptErrorCategory.UNKNOWN


def should_retry_receipt_error(
    category: ReceiptErrorCategory,
    attempt: int,
    config: ReceiptRetryConfig,
) -> bool:
    """判断是否应重试。"""
    if category not in config.retryable_categories:
        return False
    return attempt < config.max_attempts


def get_error_suggestion(category: ReceiptErrorCategory) -> str | None:
    """获取错误处理建议。"""
    suggestions = {
        ReceiptErrorCategory.RESULT_FILE_NOT_FOUND: "请确认 result_file 路径存在并可访问",
        ReceiptErrorCategory.RESULT_FILE_EMPTY: "结果文件内容为空，请重新执行任务生成内容",
        ReceiptErrorCategory.RESULT_FILE_INVALID: "请检查结果文件格式是否符合 Schema",
        ReceiptErrorCategory.RESULT_FILE_MISSING_SECTIONS: "请补充缺失章节后重试",
        ReceiptErrorCategory.VALIDATION_FAILED: "请检查结果文件是否符合验收要求",
        ReceiptErrorCategory.STATE_MANAGER_REJECTED: "请检查状态文件权限",
        ReceiptErrorCategory.TASK_NOT_FOUND: "任务 ID 不存在，请确认 ID 正确",
        ReceiptErrorCategory.TASK_NOT_IN_TESTING: "请将任务先移至 testing 状态",
        ReceiptErrorCategory.OPEN_PATCH_EXISTS: "请先关闭 open patch",
        ReceiptErrorCategory.ACTION_REQUIRED: "请人工介入处理",
        ReceiptErrorCategory.MISSING_ACCEPTANCE_COMMANDS: "请补充 acceptance_commands 字段",
    }
    return suggestions.get(category)


# ---------------- IO ----------------

# 结果文件章节契约（PROTOCOL §7.4，台账 N41）。
#
# 本脚本可被单独拷走执行，所以**刻意不 import ai_collab**，保留本地副本；
# 权威定义在 ai_collab/result_file_contract.py。两侧由
# tests/unit/test_result_file_contract.py 强制逐字一致 + 行为等价，
# 沿用 _MANAGED_LEDGER_FILENAMES 的既有模式。改这里必须同步改那边。
#
# 旧实现是 `REQUIRED_SECTIONS = ("## 执行命令", "## 测试结论", "## 风险")`，
# 即字面 H2 子串匹配，与 state_manager 的三组替代词判据矛盾：
# ① 按 PROTOCOL §7.4 写的合规文件（「测试结论」是 `## 验证结果` 下的小节）被判 invalid；
# ② 缺强制段 `## 回滚` 的文件被放行；
# ③ `## 4. 执行命令` 这种编号标题反而匹配不上。
SECTION_GROUPS = (
    ("执行命令", ("执行命令", "命令清单", "acceptance_commands", "verification commands", "commands")),
    ("验证结果", ("验证结果", "测试结论", "验证", "test result", "test conclusion", "verification")),
    ("风险", ("风险", "risk")),
    ("回滚", ("回滚", "rollback")),
)

# `(?!#)` 必不可少：没有它，`##### H5` 会被贪婪的 `#{2,4}` 吃掉四个 `#`，
# 剩下的 `# H5` 当成标题文字，于是 5 级标题被误判成 4 级（与权威实现保持一致）。
_HEADING_RE = re.compile(r"^(#{2,4})(?!#)[ \t]*(.+?)[ \t]*$", re.MULTILINE)
_NUMBERING_RE = re.compile(
    r"^[ \t]*(?:"
    r"第?[0-9０-９一二三四五六七八九十百]+(?:[.．、)）]|[ \t])"
    r"|[（(][0-9０-９一二三四五六七八九十百]+[）)]"
    r"|[0-9０-９]+(?:[.．][0-9０-９]+)+[.．、]?"
    r")[ \t]*"
)
_COMPOUND_SEP_RE = re.compile(r"[与和及、/／,，;；]+")


def _heading_matches(heading_normalized: str, keywords: tuple[str, ...]) -> bool:
    """标题**作为章节名**表达该概念：某一段以关键词开头。

    只认「以关键词开头」，不认「标题里提到」——否则
    `### F7 关于回滚的说明` 这种描述性小节会顶替真正的 `## 回滚` 段。
    """
    parts = [p.strip() for p in _COMPOUND_SEP_RE.split(heading_normalized) if p.strip()]
    for part in parts:
        low = part.lower()
        for kw in keywords:
            if low.startswith(str(kw).lower()):
                return True
    return False


def missing_result_sections(text: str) -> list[str]:
    """返回缺失的章节组名；空列表表示齐备。"""
    headings = []
    for m in _HEADING_RE.finditer(text or ""):
        headings.append(_NUMBERING_RE.sub("", m.group(2).strip()).strip())
    missing = []
    for label, keywords in SECTION_GROUPS:
        if not any(_heading_matches(h, keywords) for h in headings):
            missing.append(label)
    return missing


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


# 与 ai_collab/governance.py 的 LEDGER_FILENAMES 同源；
# tests/unit/test_governance_ledger.py 强制两者一致（沿用 ack_prefix 的一致性测试模式）。
# 本脚本可被单独拷走执行，所以运行时守卫用本地表而不硬依赖 ai_collab 包。
_MANAGED_LEDGER_FILENAMES = (
    "collaboration_state.json",
    "agent_ack_bridge_state.json",
    "agent_receipt_state.json",
)


def write_json(path: Path, data: Any) -> None:
    """只写报告类文件；受管账本必须走 locked_json_update，禁止直接覆写。"""
    if path.name in _MANAGED_LEDGER_FILENAMES:
        raise RuntimeError(f"受管账本禁止直接覆写，请走 locked_json_update: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------- 门禁 ----------------


def check_result_file(workspace: Path, task: dict[str, Any]) -> str | None:
    """检查结果文件；返回错误消息（None 表示通过）。"""
    rel = task.get("result_file")
    if not rel:
        return f"result_file not found: (empty for {task.get('task_id')})"
    path = workspace / rel
    if not path.exists():
        return f"result_file not found: {rel}"
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        return f"result_file is empty: {rel}"
    missing = missing_result_sections(text)
    if missing:
        return f"result_file missing sections: {missing}"
    return None


def check_acceptance_mismatch(workspace: Path, task: dict[str, Any]) -> str | None:
    """检查结果文件中的执行命令与 acceptance_commands 是否一致。

    返回错误消息（None 表示一致或无 acceptance_commands 约定）。
    """
    rel = task.get("result_file")
    commands = task.get("acceptance_commands")
    if not rel or not commands:
        return None
    path = workspace / rel
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")

    # 提取 "## 执行命令" 段落
    marker = "## 执行命令"
    if marker not in text:
        return None
    section = text.split(marker, 1)[1]
    # 截断到下一个 "## " 标题
    next_header = section.find("\n## ")
    if next_header != -1:
        section = section[:next_header]

    for cmd in commands:
        if cmd.strip() and cmd.strip() not in section:
            return f"missing acceptance_commands in result_file: {cmd.strip()}"
    return None


def check_open_patch(state: dict[str, Any], task_id: str) -> bool:
    """是否存在 open patch。"""
    for p in state.get("patches", {}).values():
        if p.get("task_id") == task_id and p.get("status") not in {"completed", "merged", "cancelled"}:
            return True
    return False


def has_explicit_ack(ack_state: dict[str, Any], task_id: str) -> bool:
    item = ack_state.get("items", {}).get(task_id)
    if not item:
        return False
    return item.get("source") == "cli-ack"


def _prefix_workspace(workspace: Path | None) -> Path:
    """选一个**已经存在编排配置**的目录作为前缀解析的输入。

    `OrchestrationConfig.load()` 在找不到配置时会把模板 copy 进目标目录 ——
    回执桥接只想「读前缀」，不该在别人的工作区里落文件。
    """
    candidate = Path(workspace) if workspace else _REPO_ROOT
    if (candidate / "config" / "agent-orchestration.json").exists():
        return candidate
    return _REPO_ROOT


def ack_prefix_for(
    assignee: str,
    *,
    assignee_role: str | None = None,
    workspace: Path | None = None,
) -> str:
    """执行方 → ACK 前缀。

    **角色优先**（PROTOCOL §7.3）：工单声明了 `assignee_role` 就取该角色的
    命令前缀（AGENT_ARCH → X），否则才退回 provider 兜底表。
    解析器是 `ai_collab.role_prefix` —— 前缀映射的单一事实源；
    本脚本不依赖 ai_collab 包，import 失败时退回下面的硬编码表
    （与 ai_collab/ack_protocol.py 的 _ACK_PREFIX 保持一致，
    tests/unit/test_ack_prefix_consistency.py 会强制两者同步）。
    兜底用角色字母池之外的保留字母 "Z"：历史上的 "A" 正好是
    AGENT_EXEC 的角色前缀，会把"未解析"伪装成真实角色。
    """
    try:
        from ai_collab.role_prefix import resolve_ack_prefix

        return resolve_ack_prefix(
            assignee,
            assignee_role=assignee_role,
            workspace=_prefix_workspace(workspace),
        )
    except Exception:  # pragma: no cover - ai_collab 不可用时退回兜底表
        return {"claude_code": "C", "codearts_agent": "A", "codex": "O"}.get(assignee, "Z")


def ack_status_for(assignee: str) -> str:
    # PROTOCOL.md：ACK 行 status 只能是 ok / blocked / noop
    return "ok"


# ---------------- 主流程 ----------------


def run_receipt(args) -> int:
    workspace = Path(args.workspace)
    state = read_json(workspace / "logs" / "collaboration_state.json", {"tasks": {}, "patches": {}})
    ack_state = read_json(workspace / "logs" / "agent_ack_bridge_state.json", {"items": {}})

    tasks = state.get("tasks", {})
    candidate_count = 0
    completed: list[str] = []
    completed_meta: dict[str, dict[str, Any]] = {}
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for tid, task in tasks.items():
        if task.get("status") != "testing":
            continue

        assignee = task.get("assignee") or task.get("ai_type") or "codearts_agent"

        # 1. open patch 检查（跳过，不计入 candidate）
        if check_open_patch(state, tid):
            skipped.append({"task_id": tid, "reason": "open patch exists"})
            continue

        # 2. 显式 ACK 检查（claude_code 必须有 cli-ack；跳过，不计入 candidate）
        ai_type = (task.get("ai_type") or "").lower()
        needs_ack = "claude" in ai_type or assignee == "claude_code"
        if needs_ack and not has_explicit_ack(ack_state, tid):
            skipped.append({"task_id": tid, "reason": "explicit ACK required before receipt close"})
            continue

        # 通过前置检查，计为候选
        candidate_count += 1

        # 3. 结果文件门禁
        gate_error = check_result_file(workspace, task)
        if gate_error:
            errors.append(
                {
                    "task_id": tid,
                    "error": gate_error,
                    "category": classify_receipt_error(ValueError(gate_error)).value,
                }
            )
            continue

        # 4. acceptance_commands 一致性检查
        mismatch = check_acceptance_mismatch(workspace, task)
        if mismatch:
            errors.append(
                {
                    "task_id": tid,
                    "error": mismatch,
                    "category": ReceiptErrorCategory.MISSING_ACCEPTANCE_COMMANDS.value,
                }
            )
            continue

        # 5. 收口：只收集本轮变更，不在此处改内存里的整份状态。
        # 真正写回在最后的统一入口里，基于锁内重读的最新内容合并。
        completed.append(tid)
        if not args.dry_run:
            rel = task.get("result_file", "")
            # 角色决定 ACK 前缀：同一个 provider 可以占多个席位
            # （claude_code 同时是 AGENT_ARCH 与 AGENT_TEST），
            # 不带角色就只能落到 provider 兜底字母上。
            assignee_role = str(task.get("assignee_role") or "").strip()
            prefix = ack_prefix_for(assignee, assignee_role=assignee_role or None, workspace=workspace)
            completed_meta[tid] = {
                "completed_at": task.get("updated_at"),
                "ack_item": {
                    "task_id": tid,
                    "assignee": assignee,
                    "assignee_role": assignee_role or None,
                    "result_file": rel,
                    "ack_line": f"{prefix}.ACK|task={tid}|status={ack_status_for(assignee)}|result={rel}",
                    "receipt_completed_at": task.get("updated_at"),
                    "bridged_at": task.get("updated_at"),
                    "bridge_count": 1,
                    "source": "cli-ack",
                },
            }

    state_updated = False
    if not args.dry_run and completed:
        from ai_collab.governance import locked_json_update

        def _mutate_state(latest: Any) -> None:
            if not isinstance(latest, dict):
                return
            latest_tasks = latest.get("tasks")
            if not isinstance(latest_tasks, dict):
                return
            for tid in completed:
                task = latest_tasks.get(tid)
                if isinstance(task, dict):
                    task["status"] = "completed"
                    task["completed_at"] = completed_meta[tid]["completed_at"]

        def _mutate_ack(latest: Any) -> None:
            if not isinstance(latest, dict):
                return
            items = latest.get("items")
            if not isinstance(items, dict):
                items = {}
                latest["items"] = items
            for tid in completed:
                items[tid] = completed_meta[tid]["ack_item"]

        def _mutate_receipt(latest: Any) -> None:
            if not isinstance(latest, dict):
                return
            items = latest.get("items")
            if not isinstance(items, dict):
                items = {}
                latest["items"] = items
            for tid in completed:
                items[tid] = {
                    "task_id": tid,
                    "completed_at": completed_meta[tid]["completed_at"],
                }

        locked_json_update(
            workspace / "logs" / "collaboration_state.json",
            {"tasks": {}, "patches": {}},
            _mutate_state,
        )
        locked_json_update(
            workspace / "logs" / "agent_ack_bridge_state.json",
            {"items": {}},
            _mutate_ack,
        )
        locked_json_update(
            workspace / args.state,
            {"version": "1.0.0", "items": {}},
            _mutate_receipt,
        )
        state_updated = True

    report = {
        "mode": "dry-run" if args.dry_run else "apply",
        "candidate_count": candidate_count,
        "completed_count": len(completed),
        "skipped_count": len(skipped),
        "skipped_tasks": skipped,
        "error_count": len(errors),
        "errors": errors,
        "completed_tasks": completed,
        "state_updated": state_updated,
    }

    if args.report:
        write_json(workspace / args.report, report)
    if args.history and not args.dry_run:
        hp = workspace / args.history
        hp.parent.mkdir(parents=True, exist_ok=True)
        with hp.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"event": "receipt", "completed": len(completed)}, ensure_ascii=False) + "\n")
    if args.summary:
        sp = workspace / args.summary
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(
            f"# Agent Receipt Summary\n\n- candidate: {candidate_count}\n"
            f"- completed: {len(completed)}\n- skipped: {len(skipped)}\n- errors: {len(errors)}\n",
            encoding="utf-8",
        )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--reclose", action="store_true")
    p.add_argument("--force-workspace", action="store_true")
    p.add_argument("--report")
    p.add_argument("--history")
    p.add_argument("--state", default="logs/agent_receipt_state.json")
    p.add_argument("--summary")
    p.add_argument("--max-attempts", type=int, default=3)
    args = p.parse_args()
    return run_receipt(args)


if __name__ == "__main__":
    sys.exit(main())
