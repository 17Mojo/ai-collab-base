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
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


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


RETRYABLE_CATEGORIES = frozenset({
    ReceiptErrorCategory.RESULT_FILE_NOT_FOUND,
    ReceiptErrorCategory.RESULT_FILE_MISSING_SECTIONS,
    ReceiptErrorCategory.STATE_MANAGER_REJECTED,
    ReceiptErrorCategory.VALIDATION_FAILED,
})


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


def get_error_suggestion(category: ReceiptErrorCategory) -> Optional[str]:
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

REQUIRED_SECTIONS = ("## 执行命令", "## 测试结论", "## 风险")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------- 门禁 ----------------

def check_result_file(workspace: Path, task: Dict[str, Any]) -> Optional[str]:
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
    missing = [s for s in REQUIRED_SECTIONS if s not in text]
    if missing:
        return f"result_file missing sections: {missing}"
    return None


def check_acceptance_mismatch(workspace: Path, task: Dict[str, Any]) -> Optional[str]:
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


def check_open_patch(state: Dict[str, Any], task_id: str) -> bool:
    """是否存在 open patch。"""
    for p in state.get("patches", {}).values():
        if p.get("task_id") == task_id and p.get("status") not in {"completed", "merged", "cancelled"}:
            return True
    return False


def has_explicit_ack(ack_state: Dict[str, Any], task_id: str) -> bool:
    item = ack_state.get("items", {}).get(task_id)
    if not item:
        return False
    return item.get("source") == "cli-ack"


def ack_prefix_for(assignee: str) -> str:
    return {"claude_code": "C", "codearts_agent": "A", "codex": "X"}.get(assignee, "A")


def ack_status_for(assignee: str) -> str:
    return "completed" if assignee == "codearts_agent" else "ok"


# ---------------- 主流程 ----------------

def run_receipt(args) -> int:
    workspace = Path(args.workspace)
    state = read_json(workspace / "logs" / "collaboration_state.json", {"tasks": {}, "patches": {}})
    ack_state = read_json(workspace / "logs" / "agent_ack_bridge_state.json", {"items": {}})

    tasks = state.get("tasks", {})
    candidate_count = 0
    completed: List[str] = []
    skipped: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

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
            errors.append({
                "task_id": tid,
                "error": gate_error,
                "category": classify_receipt_error(ValueError(gate_error)).value,
            })
            continue

        # 4. acceptance_commands 一致性检查
        mismatch = check_acceptance_mismatch(workspace, task)
        if mismatch:
            errors.append({
                "task_id": tid,
                "error": mismatch,
                "category": ReceiptErrorCategory.MISSING_ACCEPTANCE_COMMANDS.value,
            })
            continue

        # 5. 收口
        completed.append(tid)
        if not args.dry_run:
            task["status"] = "completed"
            task["completed_at"] = task.get("updated_at")
            # 更新 ACK bridge 状态
            rel = task.get("result_file", "")
            ack_state.setdefault("items", {})[tid] = {
                "task_id": tid,
                "assignee": assignee,
                "result_file": rel,
                "ack_line": f"{ack_prefix_for(assignee)}.ACK|task={tid}|status={ack_status_for(assignee)}|result={rel}",
                "receipt_completed_at": task.get("updated_at"),
                "bridged_at": task.get("updated_at"),
                "bridge_count": 1,
                "source": "cli-ack",
            }

    state_updated = False
    if not args.dry_run and completed:
        write_json(workspace / "logs" / "collaboration_state.json", state)
        write_json(workspace / "logs" / "agent_ack_bridge_state.json", ack_state)
        receipt_state = read_json(workspace / args.state, {"version": "1.0.0", "items": {}})
        for tid in completed:
            receipt_state.setdefault("items", {})[tid] = {
                "task_id": tid,
                "completed_at": tasks[tid].get("completed_at"),
            }
        write_json(workspace / args.state, receipt_state)
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
