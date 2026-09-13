"""
AI 协作开发系统 - CLI 工具 (扩展版)

包含原有命令 + orchestration 冷启动与配置管理命令
"""

import argparse
import json
import os
import sys
from datetime import datetime

# 原有模块导入
from .activation_handler import ActivationHandler, ActivationMode, AIType, VSCodeIntegration
from .state_manager import PatchStatus, StateManager, TaskStatus

# 新增 orchestration 模块导入
from ai_collab.orchestration import (
    BindingStatus,
    ColdStartWizard,
    OrchestrationConfig,
    StartupMode,
    check_cold_start,
    get_orchestration_config
)


# ============== 原有命令 ==============

def cmd_activate(args):
    """激活 AI 协作系统"""
    ai_type_map = {
        "claude": AIType.CLAUDE_CODE,
        "claude_code": AIType.CLAUDE_CODE,
        "copilot": AIType.COPILOT,
        "codearts": AIType.CODEARTS_AGENT,
        "codearts_agent": AIType.CODEARTS_AGENT,
        "codex": AIType.CLAUDE_CODE,
    }

    ai_type = ai_type_map.get(args.ai.lower())
    if not ai_type:
        print(f"错误: 未知的 AI 类型 '{args.ai}'")
        print("支持的类型: claude, claude_code, copilot, codearts_agent, codex")
        return 1

    mode_map = {
        "cli": ActivationMode.CLI,
        "command": ActivationMode.COMMAND,
        "event": ActivationMode.EVENT,
        "on_save": ActivationMode.ON_SAVE,
    }
    mode = mode_map.get(args.mode, ActivationMode.CLI)

    if args.workspace:
        os.environ["VSCODE_CWD"] = args.workspace

    def on_activated(session_id, rules, context):
        print("\n[激活回调]")
        print(f"  会话ID: {session_id}")
        print(f"  加载规则: {', '.join(rules)}")
        if context:
            print(f"  上下文: {json.dumps(context, ensure_ascii=False, indent=2)}")

    handler = ActivationHandler(
        ai_type=ai_type, workspace_path=args.workspace, on_activated=on_activated
    )

    print("=" * 60)
    print(f"AI 协作系统 - 激活 ({args.ai.upper()})")
    print("=" * 60)

    if args.input:
        user_input = args.input
    else:
        user_input = f"开始任务 {ActivationHandler.ACTIVATION_KEYWORD}"

    if handler.check_activation(user_input, mode):
        result = handler.activate(mode)

        print("\n激活成功!")
        print(f"  AI类型: {result['ai_type']}")
        print(f"  会话ID: {result['session_id']}")
        print(f"  激活时间: {result['activation_time']}")
        print(f"  模式: {result['mode']}")
        print(f"  加载规则: {', '.join(result['rules_loaded'])}")
        print(f"\n  响应: {result['ack_message']}")

        if args.show_rules:
            print("\n[规则内容]")
            rules_content = handler.get_rules_content()
            for rule_file, content in rules_content.items():
                print(f"\n--- {rule_file} ---")
                print(content[:500] + "..." if len(content) > 500 else content)

        return 0
    else:
        print("\n激活失败: 未检测到激活词")
        return 1


def cmd_check(args):
    """检查文件冲突"""
    ai_type = args.ai.lower() if args.ai else "claude"

    state = StateManager(workspace_path=args.workspace)

    print("=" * 60)
    print(f"AI 协作系统 - 冲突检查 ({ai_type.upper()})")
    print("=" * 60)

    files_to_check = args.files or []
    if not files_to_check:
        print("\n警告: 未指定检查文件，将从当前工作目录查找")
        workspace = args.workspace or VSCodeIntegration.get_workspace_path()
        if workspace:
            for root, dirs, files in os.walk(workspace):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for file in files:
                    if file.endswith((".ts", ".tsx", ".js", ".py", ".go")):
                        rel_path = os.path.relpath(os.path.join(root, file), workspace)
                        files_to_check.append(rel_path)
                        if len(files_to_check) >= 10:
                            break
                if len(files_to_check) >= 10:
                    break

    if files_to_check:
        print(f"\n检查文件 ({len(files_to_check)} 个):")
        for f in files_to_check:
            print(f"  - {f}")

    check_mode = "both" if args.mode == "both" else "command"
    conflicts = state.check_conflicts(ai_type, files_to_check, check_mode)

    if conflicts:
        print(f"\n检测到 {len(conflicts)} 个冲突:")
        for i, c in enumerate(conflicts, 1):
            print(f"\n  冲突 {i}:")
            print(f"    任务ID: {c['task_id']}")
            print(f"    AI类型: {c['ai_type']}")
            print(f"    描述: {c['description']}")
            print(f"    状态: {c['status']}")
            print(f"    重叠文件: {c['overlapping_files']}")
            print(f"    检测时间: {c['detected_at']}")

            if args.resolve:
                conflict_id = c.get("conflict_id", f"conflict-{datetime.now().timestamp()}")
                if state.resolve_conflict(conflict_id, "待用户决策"):
                    print("    → 冲突已标记为待解决")
        return 1
    else:
        print("\n无冲突，可以安全开发")
        return 0


def cmd_tasks(args):
    """任务管理"""
    state = StateManager(workspace_path=args.workspace)

    print("=" * 60)
    print("AI 协作系统 - 任务管理")
    print("=" * 60)

    cmd = args.subcommand
    if cmd == "list":
        if args.status == "all":
            tasks = state.get_all_tasks()
        elif args.status == "active":
            tasks = state.get_active_tasks()
        elif args.status == "completed":
            tasks = [t for t in state.get_all_tasks() if t.get("status") == "completed"]
        else:
            tasks = [t for t in state.get_all_tasks() if t.get("status") == args.status]

        print(f"\n任务列表 ({args.status}, {len(tasks)} 个):")
        if tasks:
            for task in tasks:
                print(f"\n  {task['task_id']}")
                print(f"    AI: {task['ai_type']}")
                print(f"    描述: {task['description']}")
                print(f"    状态: {task['status']}")
                print(f"    创建时间: {task.get('created_at', 'N/A')}")
                if task.get("files"):
                    print(
                        f"    文件: {', '.join(task['files'][:3])}"
                        + ("..." if len(task["files"]) > 3 else "")
                    )
        else:
            print("  无任务")

    elif cmd == "register":
        task_id = args.task_id or f"TASK-{int(datetime.now().timestamp())}"
        task = state.register_task(
            task_id=task_id,
            ai_type=args.ai,
            description=args.description or "新任务",
            files=args.files or [],
            vscode_context={"source": "cli"},
        )
        print(f"\n任务已注册: {task_id}")
        print(f"  AI: {task['ai_type']}")
        print(f"  描述: {task['description']}")

    elif cmd == "update":
        if not args.task_id:
            print("\n错误: 需要指定 task_id")
            return 1

        status_map = {
            "pending": TaskStatus.PENDING,
            "planning": TaskStatus.PLANNING,
            "implementing": TaskStatus.IMPLEMENTING,
            "testing": TaskStatus.TESTING,
            "completed": TaskStatus.COMPLETED,
            "failed": TaskStatus.FAILED,
            "cancelled": TaskStatus.CANCELLED,
        }
        new_status = status_map.get(args.status, TaskStatus.PENDING)

        state.update_task_status(args.task_id, new_status, args.note)
        print(f"\n任务状态已更新: {args.task_id} -> {new_status.value}")

    return 0


def cmd_status(args):
    """显示系统状态"""
    state = StateManager(workspace_path=args.workspace)
    workspace = args.workspace or VSCodeIntegration.get_workspace_path()

    print("=" * 60)
    print("AI 协作系统 - 系统状态")
    print("=" * 60)

    print("\n[工作区]")
    print(f"  路径: {workspace or '未设置'}")

    config = VSCodeIntegration.get_project_config()
    print("\n[项目配置]")
    print(f"  版本: {config.get('version', 'N/A')}")
    print(f"  规则目录: {config.get('rulesDir', './rules')}")
    print(f"  日志目录: {config.get('logsDir', './logs')}")
    print(f"  激活词: {config.get('activationKeyword', '2X')}")
    print(f"  启用AI: {', '.join(config.get('enabledAIs', []))}")

    print("\n[任务统计]")
    active_tasks = state.get_active_tasks()
    all_tasks = state.get_all_tasks()
    completed = [t for t in all_tasks if t.get("status") == "completed"]

    print(f"  总任务数: {len(all_tasks)}")
    print(f"  活跃任务: {len(active_tasks)}")
    print(f"  已完成任务: {len(completed)}")

    conflicts = state.get_conflicts("open")
    print("\n[冲突状态]")
    print(f"  未解决冲突: {len(conflicts)}")

    # 显示 orchestration 状态
    orch_config = get_orchestration_config(workspace)
    print("\n[Orchestration 配置]")
    print(f"  绑定状态: {orch_config.get_binding_status().value}")
    print(f"  启动模式: {orch_config.config.get('startup_mode', '未设置')}")

    active_roles = [r for r in orch_config.roles.values() if r.is_active()]
    print(f"  活跃角色: {len(active_roles)}/{len(orch_config.roles)}")

    if active_roles and args.verbose:
        print("\n  角色绑定详情:")
        for role in active_roles:
            provider = role.binding.get("provider", "")
            variant = role.binding.get("model_variant", "")
            variant_display = f" ({variant})" if variant else ""
            print(f"    {role.role_id} ({role.display_name}) → {provider}{variant_display}")

    return 0


# ============== 新增 Orchestration 命令 ==============

def cmd_orchestration(args):
    """Orchestration 配置管理"""
    workspace = args.workspace or os.getcwd()

    print("=" * 60)
    print("AI Collab Base - Orchestration 配置管理")
    print("=" * 60)

    cmd = args.subcommand

    if cmd == "status":
        config = get_orchestration_config(workspace)
        print(f"\n绑定状态: {config.get_binding_status().value}")
        print(f"启动模式: {config.config.get('startup_mode', '未设置')}")

        print("\n角色列表:")
        for role in config.roles.values():
            status_icon = "✓" if role.is_active() else "○"
            provider = role.binding.get("provider", "未绑定")
            variant = role.binding.get("model_variant", "")
            variant_display = f" ({variant})" if variant else ""
            print(f"  {status_icon} {role.role_id} ({role.display_name}) → {provider}{variant_display}")

        print("\n命令映射:")
        prefixes = config.config.get("command_prefixes", {})
        for prefix in ["A.RUN", "X.RUN", "C.RUN"]:
            role_id = prefixes.get(prefix, "")
            role = config.roles.get(role_id)
            role_name = role.display_name if role else role_id
            print(f"  {prefix} → {role_name}")

        custom = prefixes.get("custom_prefixes", {})
        if custom:
            print("\n自定义命令:")
            for prefix, role_id in custom.items():
                role = config.roles.get(role_id)
                role_name = role.display_name if role else role_id
                print(f"  {prefix} → {role_name}")

    elif cmd == "cold-start":
        config = get_orchestration_config(workspace)

        if not config.is_cold_start_needed():
            print("\n冷启动已完成，无需重新执行")
            print("如需重新配置，请先运行: orchestration reset")
            return 1

        wizard = ColdStartWizard(config)
        wizard.run()
        return 0

    elif cmd == "detect":
        config = get_orchestration_config(workspace)
        print("\n检测可用 Agent 服务商...")

        providers = config.detect_providers()
        print("\n检测结果:")
        for provider in providers.values():
            status_icon = "✓" if provider.connection_status.value in ["connected", "detected"] else "✗"
            status_text = provider.connection_status.value
            sub_agent = " (支持 SubAgent)" if provider.supports_sub_agent else ""
            print(f"  {status_icon} {provider.name} [{status_text}]{sub_agent}")

        config.save()
        print("\n检测结果已保存到配置")

    elif cmd == "roles":
        config = get_orchestration_config(workspace)

        if args.role_action == "list":
            print("\n角色列表:")
            for role in config.roles.values():
                status = role.binding.get("status", "dormant")
                status_icon = "✓" if status == "active" else "○"
                print(f"  {status_icon} {role.role_id}")
                print(f"      名称: {role.display_name}")
                print(f"      职责: {', '.join(role.duties)}")
                print(f"      状态: {status}")

        elif args.role_action == "add":
            role_id = args.role_id
            if not role_id:
                print("\n错误: 需要指定 --role-id")
                return 1

            if role_id in config.roles:
                print(f"\n错误: 角色 {role_id} 已存在")
                return 1

            role = config.add_role(
                role_id=role_id,
                display_name=args.display_name or role_id,
                duties=args.duties or [],
                required_capabilities=args.capabilities or [],
                raci_role=args.raci or "C"
            )
            config.save()
            print(f"\n角色已添加: {role_id}")

        elif args.role_action == "activate":
            role_id = args.role_id
            provider = args.provider

            if not role_id or not provider:
                print("\n错误: 需要指定 --role-id 和 --provider")
                return 1

            if role_id not in config.roles:
                print(f"\n错误: 角色 {role_id} 不存在")
                return 1

            config.activate_role(role_id, provider, args.model_variant)
            config.save()
            print(f"\n角色已激活: {role_id} → {provider}")
            if args.model_variant:
                print(f"  模型变体: {args.model_variant}")

        elif args.role_action == "deactivate":
            role_id = args.role_id
            if not role_id:
                print("\n错误: 需要指定 --role-id")
                return 1

            role = config.roles.get(role_id)
            if not role:
                print(f"\n错误: 角色 {role_id} 不存在")
                return 1

            role.deactivate()
            config.update_binding_status()
            config.save()
            print(f"\n角色已休眠: {role_id}")

    elif cmd == "bind":
        config = get_orchestration_config(workspace)

        print("\n当前绑定:")
        for role in config.roles.values():
            status = role.binding.get("status", "dormant")
            if status == "active":
                provider = role.binding.get("provider", "")
                variant = role.binding.get("model_variant", "")
                variant_display = f" ({variant})" if variant else ""
                print(f"  {role.role_id} → {provider}{variant_display}")

        available = config.get_available_providers()
        print(f"\n可用服务商 ({len(available)} 个):")
        for provider in available:
            print(f"  - {provider.name}")

        print("\n使用方式:")
        print("  orchestration roles activate --role-id <ID> --provider <PROVIDER>")
        print("  orchestration roles activate --role-id <ID> --provider <PROVIDER> --model-variant <VARIANT>")

    elif cmd == "snapshot":
        config = get_orchestration_config(workspace)

        if args.snapshot_action == "list":
            snapshots = config.config.get("snapshots", [])
            print(f"\n快照列表 ({len(snapshots)} 个):")
            for snap in snapshots[-10:]:  # 显示最近 10 个
                print(f"  {snap['snapshot_id']} [{snap['trigger']}] {snap['timestamp']}")

        elif args.snapshot_action == "create":
            snap_id = config.create_snapshot(trigger="manual", note=args.note or "")
            config.save()
            print(f"\n快照已创建: {snap_id}")

        elif args.snapshot_action == "rollback":
            snap_id = args.snapshot_id
            if not snap_id:
                print("\n错误: 需要指定 --snapshot-id")
                return 1

            if config.rollback_to_snapshot(snap_id):
                print(f"\n已回滚到快照: {snap_id}")
            else:
                print(f"\n错误: 快照 {snap_id} 不存在")
                return 1

    elif cmd == "history":
        config = get_orchestration_config(workspace)
        history = config.config.get("history", [])

        limit = args.limit or 20
        print(f"\n变更历史 (最近 {limit} 条):")
        for event in history[-limit:]:
            timestamp = event.get("timestamp", "")
            event_type = event.get("event", "")
            details = event.get("details", {})
            print(f"  [{timestamp}] {event_type}")
            if details:
                for key, value in details.items():
                    print(f"    {key}: {value}")

    elif cmd == "reset":
        config = get_orchestration_config(workspace)

        print("\n⚠️  警告: 此操作将重置 orchestration 配置")
        print("所有角色绑定和自定义命令将丢失")

        confirm = input("确认重置? (yes/no): ").strip().lower()
        if confirm == "yes":
            config._create_default_config()
            print("\n配置已重置")
            print("请运行: orchestration cold-start 重新配置")
        else:
            print("\n取消重置")

    return 0


def main():
    """CLI 主函数"""
    parser = argparse.ArgumentParser(
        description="AI 协作开发系统 - Claude Code + Orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 激活 Claude Code
  ai-collab activate --ai claude

  # 检查文件冲突
  ai-collab check --ai claude --files src/api.ts

  # Orchestration 管理
  ai-collab orchestration status
  ai-collab orchestration cold-start
  ai-collab orchestration detect

  # 角色管理
  ai-collab orchestration roles list
  ai-collab orchestration roles activate --role-id AGENT_EXEC --provider claude_code

  # 快照管理
  ai-collab orchestration snapshot create --note "备份"
  ai-collab orchestration snapshot rollback --snapshot-id snap_001
        """,
    )

    parser.add_argument("-w", "--workspace", help="工作区路径")
    parser.add_argument("-v", "--version", action="version", version="%(prog)s 2.1.0")

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # ============== 原有命令解析器 ==============

    # activate 命令
    activate_parser = subparsers.add_parser("activate", help="激活 AI 协作系统")
    activate_parser.add_argument(
        "--ai",
        choices=["claude", "claude_code", "copilot", "codearts_agent", "codex"],
        default="claude",
        help="AI 类型",
    )
    activate_parser.add_argument(
        "--mode", choices=["cli", "command", "event", "on_save"], default="cli", help="激活模式"
    )
    activate_parser.add_argument("--input", help="自定义激活输入")
    activate_parser.add_argument("--show-rules", action="store_true", help="显示规则内容")

    # check 命令
    check_parser = subparsers.add_parser("check", help="检查文件冲突")
    check_parser.add_argument(
        "--ai", choices=["claude", "copilot", "codearts_agent", "codex"], help="检查的 AI 类型"
    )
    check_parser.add_argument("--files", nargs="*", help="要检查的文件列表")
    check_parser.add_argument(
        "--mode", choices=["on_save", "command", "both"], default="both", help="检查模式"
    )
    check_parser.add_argument("--resolve", action="store_true", help="自动标记冲突")

    # tasks 命令
    tasks_parser = subparsers.add_parser("tasks", help="任务管理")
    tasks_parser.add_argument("subcommand", choices=["list", "register", "update"], help="子命令")
    tasks_parser.add_argument(
        "--status",
        choices=["all", "active", "completed", "pending", "implementing"],
        default="active",
        help="任务状态过滤",
    )
    tasks_parser.add_argument("--task-id", help="任务ID")
    tasks_parser.add_argument(
        "--ai", choices=["claude_code", "copilot", "codearts_agent", "codex"], help="AI 类型"
    )
    tasks_parser.add_argument("--description", help="任务描述")
    tasks_parser.add_argument("--files", nargs="*", help="涉及文件")
    tasks_parser.add_argument("--note", help="备注")

    # status 命令
    status_parser = subparsers.add_parser("status", help="显示系统状态")
    status_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    # ============== 新增 Orchestration 命令解析器 ==============

    orch_parser = subparsers.add_parser("orchestration", help="Orchestration 配置管理")
    orch_parser.add_argument(
        "subcommand",
        choices=["status", "cold-start", "detect", "roles", "bind", "snapshot", "history", "reset"],
        help="子命令"
    )

    # roles 子命令参数
    orch_parser.add_argument("--role-action", choices=["list", "add", "activate", "deactivate"], help="角色操作")
    orch_parser.add_argument("--role-id", help="角色ID (如 AGENT_PERF)")
    orch_parser.add_argument("--display-name", help="角色显示名称")
    orch_parser.add_argument("--duties", nargs="*", help="职责列表")
    orch_parser.add_argument("--capabilities", nargs="*", help="所需能力")
    orch_parser.add_argument("--raci", choices=["R", "A", "C", "I"], help="RACI 角色")
    orch_parser.add_argument("--provider", help="Agent 服务商")
    orch_parser.add_argument("--model-variant", help="模型变体 (SubAgent 模式)")

    # snapshot 子命令参数
    orch_parser.add_argument("--snapshot-action", choices=["list", "create", "rollback"], help="快照操作")
    orch_parser.add_argument("--snapshot-id", help="快照ID")
    orch_parser.add_argument("--note", help="备注")

    # history 参数
    orch_parser.add_argument("--limit", type=int, help="历史记录数量限制")

    args = parser.parse_args()

    # 命令路由
    if args.command == "activate":
        return cmd_activate(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "tasks":
        return cmd_tasks(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "orchestration":
        return cmd_orchestration(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())