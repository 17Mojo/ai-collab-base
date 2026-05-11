"""
AI Collab CLI 模块

提供命令行接口用于 AI 协作系统
"""

from ._cli_main import *  # noqa: F401,F403
from ._cli_main import (  # noqa: F401
    _append_jsonl,
    _as_int,
    _auto_enable_dispatch_flags,
    _cmd_stage_domain,
    _compact_stage_report,
    _count_pending_tasks_for_target,
    _count_reopened_redispatch_tasks_for_target,
    _emit_plan_patches,
    _emit_plan_tasks,
    _execute_hygiene_once,
    _generate_reports_and_summaries,
    _generate_trigger_payload_files,
    _handle_compat_check,
    _handle_export_command,
    _handle_import_command,
    _handle_rating_command,
    _handle_sharing_command,
    _handle_store_command,
    _handle_template_command,
    _handle_validate_command,
    _handle_version_command,
    _load_json_file,
    _load_steps_from_file,
    _normalize_hygiene_domain_order,
    _normalize_trigger_assignee,
    _parse_iso_datetime,
    _print_hygiene_report,
    _print_stage_report,
    _read_json_if_exists,
    _report_health_line,
    _resolve_trigger_assignees,
    _resolve_workspace_hygiene_config,
    _run_spawn_agent_guard_gate,
    _run_workspace_guard_gate,
    _set_workspace_env,
    _write_json,
    main,
)

__all__ = ["main"]
