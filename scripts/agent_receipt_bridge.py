#!/usr/bin/env python3
"""Agent Receipt Bridge - 自动回执桥接脚本"""
import argparse
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class ReceiptErrorCategory(Enum):
    """Receipt error categories."""
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
    UNKNOWN = "unknown"


RETRYABLE_CATEGORIES = frozenset({
    ReceiptErrorCategory.RESULT_FILE_NOT_FOUND,
    ReceiptErrorCategory.RESULT_FILE_MISSING_SECTIONS,
    ReceiptErrorCategory.STATE_MANAGER_REJECTED,
    ReceiptErrorCategory.VALIDATION_FAILED,
})


@dataclass
class ReceiptRetryConfig:
    """Receipt retry configuration."""
    retryable_categories: frozenset = field(default_factory=lambda: RETRYABLE_CATEGORIES)
    max_attempts: int = 3
    backoff_seconds: float = 1.0


def classify_receipt_error(exc: Exception) -> ReceiptErrorCategory:
    """Classify a receipt error into a category."""
    msg = str(exc).lower()
    if "result_file not found" in msg:
        return ReceiptErrorCategory.RESULT_FILE_NOT_FOUND
    if "result_file is empty" in msg or "result_file_empty" in msg:
        return ReceiptErrorCategory.RESULT_FILE_EMPTY
    if "result_file" in msg and ("missing sections" in msg or "invalid" in msg):
        return ReceiptErrorCategory.RESULT_FILE_INVALID
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
    """Determine whether a receipt error should be retried."""
    if category not in config.retryable_categories:
        return False
    return attempt < config.max_attempts


def get_error_suggestion(category: ReceiptErrorCategory) -> Optional[str]:
    """Get a suggestion for a given error category."""
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
    }
    return suggestions.get(category)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--reclose", action="store_true")
    p.add_argument("--force-workspace", action="store_true")
    p.add_argument("--report")
    p.add_argument("--history")
    p.add_argument("--state")
    p.add_argument("--summary")
    p.add_argument("--max-attempts", type=int, default=3)
    args = p.parse_args()

    out = {"received": [], "total": 0, "errors": []}
    if args.report:
        Path(args.report).write_text(json.dumps(out, indent=2))
    if args.history:
        Path(args.history).parent.mkdir(parents=True, exist_ok=True)
        Path(args.history).write_text("")
    if args.summary:
        Path(args.summary).write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
