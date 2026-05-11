"""
CLI 模块测试
测试 ai_collab/cli.py 的所有命令和功能
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_collab import cli
from ai_collab.activation_handler import ActivationMode
from ai_collab.state_manager import TaskStatus

# ==================== Fixtures ====================


@pytest.fixture
def temp_workspace():
    """创建临时工作区"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_state_manager():
    """Mock StateManager"""
    manager = Mock()
    manager.workspace_path = "/test/workspace"
    manager.get_all_tasks.return_value = []
    manager.get_active_tasks.return_value = []
    manager.register_task.return_value = {
        "task_id": "TEST-001",
        "ai_type": "claude_code",
        "description": "测试任务",
    }
    manager.update_task_status.return_value = None
    manager.check_conflicts.return_value = []
    manager.get_conflicts.return_value = []
    manager.clear_completed_tasks.return_value = {"cleared": 5, "remaining": 10}
    return manager


@pytest.fixture
def mock_activation_handler():
    """Mock ActivationHandler"""
    handler = Mock()
    handler.check_activation.return_value = True
    handler.activate.return_value = {
        "ai_type": "claude_code",
        "session_id": "test-session-123",
        "activation_time": "2026-02-28T12:00:00",
        "mode": "cli",
        "rules_loaded": ["claude_rules.md", "copilot_rules.md"],
        "ack_message": "激活成功",
    }
    handler.get_rules_content.return_value = {"claude_rules.md": "规则内容..."}
    return handler


# ==================== cmd_activate 测试 ====================


class TestCmdActivate:
    """测试 activate 命令"""

    @patch("ai_collab.cli._cli_main.ActivationHandler")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_activate_claude_success(self, mock_set_env, mock_handler_cls, temp_workspace):
        """测试成功激活 Claude Code"""
        # 准备
        mock_handler = Mock()
        mock_handler.check_activation.return_value = True
        mock_handler.activate.return_value = {
            "ai_type": "claude_code",
            "session_id": "test-session",
            "activation_time": "2026-02-28T12:00:00",
            "mode": "cli",
            "rules_loaded": ["claude_rules.md"],
            "ack_message": "激活成功",
        }
        mock_handler_cls.return_value = mock_handler

        args = SimpleNamespace(
            ai="claude", mode="cli", workspace=str(temp_workspace), input=None, show_rules=False
        )

        # 执行
        result = cli.cmd_activate(args)

        # 验证
        assert result == 0
        mock_handler_cls.assert_called_once()
        mock_handler.check_activation.assert_called_once()
        mock_handler.activate.assert_called_once()

    @patch("ai_collab.cli._cli_main.ActivationHandler")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_activate_copilot_success(self, mock_set_env, mock_handler_cls, temp_workspace):
        """测试成功激活 Copilot"""
        # 准备
        mock_handler = Mock()
        mock_handler.check_activation.return_value = True
        mock_handler.activate.return_value = {
            "ai_type": "copilot",
            "session_id": "test-session",
            "activation_time": "2026-02-28T12:00:00",
            "mode": "cli",
            "rules_loaded": ["copilot_rules.md"],
            "ack_message": "激活成功",
        }
        mock_handler_cls.return_value = mock_handler

        args = SimpleNamespace(
            ai="copilot", mode="cli", workspace=str(temp_workspace), input=None, show_rules=False
        )

        # 执行
        result = cli.cmd_activate(args)

        # 验证
        assert result == 0

    @patch("ai_collab.cli._cli_main.ActivationHandler")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_activate_codearts_success(self, mock_set_env, mock_handler_cls, temp_workspace):
        """测试成功激活 CodeArts Agent"""
        mock_handler = Mock()
        mock_handler.check_activation.return_value = True
        mock_handler.activate.return_value = {
            "ai_type": "codearts_agent",
            "session_id": "test-session",
            "activation_time": "2026-03-03T09:00:00",
            "mode": "cli",
            "rules_loaded": ["codearts_agent_rules.md"],
            "ack_message": "激活成功",
        }
        mock_handler_cls.return_value = mock_handler

        args = SimpleNamespace(
            ai="codearts_agent",
            mode="cli",
            workspace=str(temp_workspace),
            input=None,
            show_rules=False,
        )

        result = cli.cmd_activate(args)

        assert result == 0

    def test_activate_unknown_ai(self, temp_workspace):
        """测试激活未知的 AI 类型"""
        args = SimpleNamespace(
            ai="unknown_ai", mode="cli", workspace=str(temp_workspace), input=None, show_rules=False
        )

        # 执行
        result = cli.cmd_activate(args)

        # 验证
        assert result == 1

    @patch("ai_collab.cli._cli_main.ActivationHandler")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_activate_with_custom_input(self, mock_set_env, mock_handler_cls, temp_workspace):
        """测试使用自定义输入激活"""
        # 准备
        mock_handler = Mock()
        mock_handler.check_activation.return_value = True
        mock_handler.activate.return_value = {
            "ai_type": "claude_code",
            "session_id": "test-session",
            "activation_time": "2026-02-28T12:00:00",
            "mode": "cli",
            "rules_loaded": [],
            "ack_message": "激活成功",
        }
        mock_handler_cls.return_value = mock_handler

        args = SimpleNamespace(
            ai="claude",
            mode="cli",
            workspace=str(temp_workspace),
            input="自定义激活输入 2X",
            show_rules=False,
        )

        # 执行
        result = cli.cmd_activate(args)

        # 验证
        assert result == 0
        mock_handler.check_activation.assert_called_once_with("自定义激活输入 2X", ActivationMode.CLI)

    @patch("ai_collab.cli._cli_main.ActivationHandler")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_activate_failure(self, mock_set_env, mock_handler_cls, temp_workspace):
        """测试激活失败"""
        # 准备
        mock_handler = Mock()
        mock_handler.check_activation.return_value = False
        mock_handler_cls.return_value = mock_handler

        args = SimpleNamespace(
            ai="claude", mode="cli", workspace=str(temp_workspace), input=None, show_rules=False
        )

        # 执行
        result = cli.cmd_activate(args)

        # 验证
        assert result == 1


# ==================== cmd_check 测试 ====================


class TestCmdCheck:
    """测试 check 命令"""

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_check_no_conflicts(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试无冲突"""
        # 准备
        mock_manager = Mock()
        mock_manager.check_conflicts.return_value = []
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            ai="claude",
            files=["test.py"],
            mode="both",
            resolve=False,
            workspace=str(temp_workspace),
        )

        # 执行
        result = cli.cmd_check(args)

        # 验证
        assert result == 0
        mock_manager.check_conflicts.assert_called_once()

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_check_with_conflicts(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试发现冲突"""
        # 准备
        mock_manager = Mock()
        mock_manager.check_conflicts.return_value = [
            {
                "task_id": "TASK-001",
                "ai_type": "copilot",
                "description": "冲突任务",
                "status": "in_progress",
                "overlapping_files": ["test.py"],
                "detected_at": "2026-02-28T12:00:00",
            }
        ]
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            ai="claude",
            files=["test.py"],
            mode="both",
            resolve=False,
            workspace=str(temp_workspace),
        )

        # 执行
        result = cli.cmd_check(args)

        # 验证
        assert result == 1

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_check_with_auto_resolve(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试自动解决冲突"""
        # 准备
        mock_manager = Mock()
        mock_manager.check_conflicts.return_value = [
            {
                "task_id": "TASK-001",
                "ai_type": "copilot",
                "description": "冲突任务",
                "status": "in_progress",
                "overlapping_files": ["test.py"],
                "detected_at": "2026-02-28T12:00:00",
                "conflict_id": "conflict-001",
            }
        ]
        mock_manager.resolve_conflict.return_value = True
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            ai="claude", files=["test.py"], mode="both", resolve=True, workspace=str(temp_workspace)
        )

        # 执行
        result = cli.cmd_check(args)

        # 验证
        assert result == 1
        mock_manager.resolve_conflict.assert_called_once()


# ==================== cmd_tasks 测试 ====================


class TestCmdTasks:
    """测试 tasks 命令"""

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_list_all(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试列出所有任务"""
        # 准备
        mock_manager = Mock()
        mock_manager.get_all_tasks.return_value = [
            {
                "task_id": "TASK-001",
                "ai_type": "claude_code",
                "description": "测试任务1",
                "status": "completed",
                "created_at": "2026-02-28T10:00:00",
            },
            {
                "task_id": "TASK-002",
                "ai_type": "copilot",
                "description": "测试任务2",
                "status": "pending",
                "created_at": "2026-02-28T11:00:00",
            },
        ]
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(subcommand="list", status="all", workspace=str(temp_workspace))

        # 执行
        result = cli.cmd_tasks(args)

        # 验证
        assert result == 0
        mock_manager.get_all_tasks.assert_called_once()

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_list_active(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试列出活跃任务"""
        # 准备
        mock_manager = Mock()
        mock_manager.get_active_tasks.return_value = [
            {
                "task_id": "TASK-001",
                "ai_type": "claude_code",
                "description": "活跃任务",
                "status": "in_progress",
                "created_at": "2026-02-28T10:00:00",
            }
        ]
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(subcommand="list", status="active", workspace=str(temp_workspace))

        # 执行
        result = cli.cmd_tasks(args)

        # 验证
        assert result == 0
        mock_manager.get_active_tasks.assert_called_once()

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_register(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试注册任务"""
        # 准备
        mock_manager = Mock()
        mock_manager.register_task.return_value = {
            "task_id": "TASK-NEW",
            "ai_type": "claude_code",
            "description": "新任务",
        }
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="register",
            task_id="TASK-NEW",
            ai="claude_code",
            description="新任务",
            files=["test.py"],
            workspace=str(temp_workspace),
        )

        # 执行
        result = cli.cmd_tasks(args)

        # 验证
        assert result == 0
        mock_manager.register_task.assert_called_once()

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_list_in_progress_alias(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试 in_progress 过滤兼容 implementing 状态"""
        mock_manager = Mock()
        mock_manager.get_all_tasks.return_value = [
            {"task_id": "TASK-001", "status": "implementing"},
            {"task_id": "TASK-002", "status": "in_progress"},
            {"task_id": "TASK-003", "status": "completed"},
        ]
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="list", status="in_progress", workspace=str(temp_workspace)
        )

        result = cli.cmd_tasks(args)

        assert result == 0
        mock_manager.get_all_tasks.assert_called_once()

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_update_status(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试更新任务状态"""
        # 准备
        mock_manager = Mock()
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="update",
            task_id="TASK-001",
            status="completed",
            note="任务完成",
            workspace=str(temp_workspace),
        )

        # 执行
        result = cli.cmd_tasks(args)

        # 验证
        assert result == 0
        mock_manager.update_task_status.assert_called_once_with(
            "TASK-001",
            TaskStatus.COMPLETED,
            "任务完成",
            actor=None,
        )

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_update_blocked_status(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试更新 blocked 状态"""
        mock_manager = Mock()
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="update",
            task_id="TASK-002",
            status="blocked",
            note="等待依赖",
            workspace=str(temp_workspace),
        )

        result = cli.cmd_tasks(args)

        assert result == 0
        mock_manager.update_task_status.assert_called_once_with(
            "TASK-002",
            TaskStatus.BLOCKED,
            "等待依赖",
            actor=None,
        )

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_takeover(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试接管任务并锁定 owner。"""
        mock_manager = Mock()
        mock_manager.takeover_task.return_value = {
            "task_id": "TASK-LOCK-001",
            "owner": "codex",
            "previous_owner": "codearts_agent",
        }
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="takeover",
            task_id="TASK-LOCK-001",
            owner="codex",
            ai="codex",
            note="codex takeover",
            reason="prevent late agent writes",
            workspace=str(temp_workspace),
        )

        result = cli.cmd_tasks(args)

        assert result == 0
        mock_manager.takeover_task.assert_called_once_with(
            task_id="TASK-LOCK-001",
            owner="codex",
            actor="codex",
            note="codex takeover",
            reason="prevent late agent writes",
            source="cli.tasks.takeover",
        )

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_repair_assignee(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试修复任务 assignee 元数据。"""
        mock_manager = Mock()
        mock_manager.repair_task_assignee.return_value = {
            "task_id": "TASK-REPAIR-001",
            "old_assignee": "codex",
            "new_assignee": "codearts_agent",
        }
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="repair-assignee",
            task_id="TASK-REPAIR-001",
            assignee="codearts_agent",
            ai="codex",
            note="restore controller assignee",
            reason="explicit ACK closeout residual",
            workspace=str(temp_workspace),
        )

        result = cli.cmd_tasks(args)

        assert result == 0
        mock_manager.repair_task_assignee.assert_called_once_with(
            task_id="TASK-REPAIR-001",
            assignee="codearts_agent",
            actor="codex",
            note="restore controller assignee",
            reason="explicit ACK closeout residual",
            source="cli.tasks.repair-assignee",
        )

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_update_returns_error_when_state_manager_rejects(
        self, mock_set_env, mock_manager_cls, temp_workspace
    ):
        """测试 update 在门禁失败时返回错误码"""
        mock_manager = Mock()
        mock_manager.update_task_status.side_effect = ValueError("任务结果门禁失败")
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="update",
            task_id="TASK-003",
            status="completed",
            note="complete",
            workspace=str(temp_workspace),
        )

        result = cli.cmd_tasks(args)

        assert result == 1

    def test_tasks_repair_assignee_requires_assignee(self, temp_workspace):
        """测试 repair-assignee 缺少 assignee 时失败。"""
        args = SimpleNamespace(
            subcommand="repair-assignee",
            task_id="TASK-REPAIR-002",
            assignee=None,
            ai="codex",
            note="",
            reason=None,
            workspace=str(temp_workspace),
        )

        result = cli.cmd_tasks(args)

        assert result == 1

    @patch("ai_collab.cli._cli_main.run_terminal_result_consistency_audit")
    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_validate_contract_non_strict(
        self, mock_set_env, mock_manager_cls, mock_run_audit, temp_workspace
    ):
        """测试工单契约校验（非严格模式）"""
        mock_manager = Mock()
        mock_manager.validate_task_contracts.return_value = {
            "checked_tasks": 1,
            "skipped_tasks": 0,
            "invalid_count": 1,
            "issues": [
                {
                    "task_id": "TASK-INVALID-001",
                    "missing_fields": ["primary_skill"],
                    "invalid_fields": [],
                    "remediation": "fix it",
                }
            ],
        }
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="validate-contract",
            scope="active",
            strict=False,
            workspace=str(temp_workspace),
        )
        result = cli.cmd_tasks(args)
        assert result == 0
        mock_manager.validate_task_contracts.assert_called_once_with(scope="active")
        mock_run_audit.assert_not_called()

    @patch("ai_collab.cli._cli_main.run_terminal_result_consistency_audit")
    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_validate_contract_strict_fails_on_invalid(
        self, mock_set_env, mock_manager_cls, mock_run_audit, temp_workspace
    ):
        """测试工单契约校验（严格模式）"""
        mock_manager = Mock()
        mock_manager.validate_task_contracts.return_value = {
            "checked_tasks": 1,
            "skipped_tasks": 0,
            "invalid_count": 1,
            "issues": [],
        }
        mock_manager_cls.return_value = mock_manager
        mock_run_audit.return_value = {
            "audited_count": 2,
            "consistent_count": 2,
            "mismatch_count": 0,
            "unparseable_count": 0,
            "missing_result_count": 0,
            "issue_count": 0,
            "issues": [],
            "report_file": "logs/task_result_consistency_report.json",
            "summary_file": "collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md",
        }

        args = SimpleNamespace(
            subcommand="validate-contract",
            scope="all",
            strict=True,
            workspace=str(temp_workspace),
        )
        result = cli.cmd_tasks(args)
        assert result == 1
        mock_run_audit.assert_called_once()

    @patch("ai_collab.cli._cli_main.run_terminal_result_consistency_audit")
    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_validate_contract_strict_fails_on_result_consistency_issue(
        self, mock_set_env, mock_manager_cls, mock_run_audit, temp_workspace
    ):
        """测试严格模式下结果一致性问题也会使门禁失败。"""
        mock_manager = Mock()
        mock_manager.validate_task_contracts.return_value = {
            "checked_tasks": 2,
            "skipped_tasks": 0,
            "invalid_count": 0,
            "issues": [],
        }
        mock_manager_cls.return_value = mock_manager
        mock_run_audit.return_value = {
            "audited_count": 5,
            "consistent_count": 4,
            "mismatch_count": 1,
            "unparseable_count": 0,
            "missing_result_count": 0,
            "issue_count": 1,
            "issues": [
                {
                    "task_id": "TASK-MISMATCH-001",
                    "issue_type": "terminal_status_mismatch",
                    "state_status": "completed",
                    "result_header_status": "testing",
                }
            ],
            "report_file": "logs/task_result_consistency_report.json",
            "summary_file": "collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md",
        }

        args = SimpleNamespace(
            subcommand="validate-contract",
            scope="active",
            strict=True,
            workspace=str(temp_workspace),
        )

        result = cli.cmd_tasks(args)

        assert result == 1
        mock_manager.validate_task_contracts.assert_called_once_with(scope="active")
        mock_run_audit.assert_called_once()

    @patch("ai_collab.cli._cli_main.run_terminal_result_consistency_audit")
    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_validate_contract_strict_passes_when_contracts_and_results_are_clean(
        self, mock_set_env, mock_manager_cls, mock_run_audit, temp_workspace
    ):
        """测试严格模式下合同与结果都干净时通过。"""
        mock_manager = Mock()
        mock_manager.validate_task_contracts.return_value = {
            "checked_tasks": 3,
            "skipped_tasks": 0,
            "invalid_count": 0,
            "issues": [],
        }
        mock_manager_cls.return_value = mock_manager
        mock_run_audit.return_value = {
            "audited_count": 7,
            "consistent_count": 7,
            "mismatch_count": 0,
            "unparseable_count": 0,
            "missing_result_count": 0,
            "issue_count": 0,
            "issues": [],
            "report_file": "logs/task_result_consistency_report.json",
            "summary_file": "collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md",
        }

        args = SimpleNamespace(
            subcommand="validate-contract",
            scope="all",
            strict=True,
            workspace=str(temp_workspace),
        )

        result = cli.cmd_tasks(args)

        assert result == 0
        mock_run_audit.assert_called_once()

    @patch("ai_collab.cli._cli_main.run_terminal_result_consistency_audit")
    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_audit_result_consistency(
        self, mock_set_env, mock_manager_cls, mock_run_audit, temp_workspace
    ):
        """测试终态结果一致性审计命令。"""
        mock_manager_cls.return_value = Mock()
        mock_run_audit.return_value = {
            "audited_count": 3,
            "consistent_count": 2,
            "mismatch_count": 1,
            "unparseable_count": 0,
            "missing_result_count": 0,
            "issue_count": 1,
            "issues": [
                {
                    "task_id": "TASK-AUDIT-001",
                    "issue_type": "terminal_status_mismatch",
                    "state_status": "failed",
                    "result_header_status": "completed",
                }
            ],
            "report_file": "logs/task_result_consistency_report.json",
            "summary_file": "collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md",
        }

        args = SimpleNamespace(
            subcommand="audit-result-consistency",
            task_id=None,
            report=None,
            summary=None,
            strict=False,
            workspace=str(temp_workspace),
        )

        result = cli.cmd_tasks(args)

        assert result == 0
        mock_run_audit.assert_called_once()

    @patch("ai_collab.cli._cli_main.run_terminal_result_consistency_audit")
    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_audit_result_consistency_strict_fails(
        self, mock_set_env, mock_manager_cls, mock_run_audit, temp_workspace
    ):
        """测试 strict 模式下有 issue 时返回非零。"""
        mock_manager_cls.return_value = Mock()
        mock_run_audit.return_value = {
            "audited_count": 1,
            "consistent_count": 0,
            "mismatch_count": 1,
            "unparseable_count": 0,
            "missing_result_count": 0,
            "issue_count": 1,
            "issues": [],
            "report_file": "logs/task_result_consistency_report.json",
            "summary_file": "collaboration/monitoring/TASK_RESULT_CONSISTENCY_SUMMARY_latest.md",
        }

        args = SimpleNamespace(
            subcommand="audit-result-consistency",
            task_id=None,
            report=None,
            summary=None,
            strict=True,
            workspace=str(temp_workspace),
        )

        result = cli.cmd_tasks(args)

        assert result == 1

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_migrate_contract_success(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试历史任务契约迁移命令"""
        mock_manager = Mock()
        mock_manager.migrate_task_contracts.return_value = {
            "scope": "all",
            "dry_run": False,
            "total_tasks": 10,
            "legacy_detected": 8,
            "migrated_count": 8,
            "already_compliant": 2,
            "remaining_legacy": 0,
            "migrated_task_ids": ["TASK-A", "TASK-B"],
            "invalid_after_migration_count": 0,
            "invalid_after_migration": [],
            "legacy_branch_eliminated": True,
        }
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="migrate-contract",
            scope="all",
            dry_run=False,
            default_change_id=None,
            migration_reviewer=None,
            workspace=str(temp_workspace),
        )
        result = cli.cmd_tasks(args)
        assert result == 0
        mock_manager.migrate_task_contracts.assert_called_once_with(
            scope="all",
            dry_run=False,
            default_change_id=None,
            reviewer=None,
        )

    def test_tasks_update_missing_task_id(self, temp_workspace):
        """测试更新任务时缺少 task_id"""
        args = SimpleNamespace(
            subcommand="update",
            task_id=None,
            status="completed",
            note="",
            workspace=str(temp_workspace),
        )

        # 执行
        result = cli.cmd_tasks(args)

        # 验证
        assert result == 1


# ==================== cmd_patches 测试 ====================


class TestCmdPatches:
    """测试 patches 命令"""

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_patches_create(self, mock_set_env, mock_manager_cls, temp_workspace):
        mock_manager = Mock()
        mock_manager.register_patch.return_value = {"patch_id": "PATCH-001"}
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="create",
            patch_id="PATCH-001",
            task_id="TASK-001",
            title="fix query",
            description=None,
            files=["a.py"],
            ai="codex",
            note="create",
            status="all",
            workspace=str(temp_workspace),
        )

        result = cli.cmd_patches(args)

        assert result == 0
        mock_manager.register_patch.assert_called_once()

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_patches_claim(self, mock_set_env, mock_manager_cls, temp_workspace):
        mock_manager = Mock()
        mock_manager.list_patches.return_value = [
            {
                "patch_id": "PATCH-CLAIM-001",
                "status": "pending",
                "assignee": "",
                "task_id": "TASK-1",
            }
        ]
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="claim",
            patch_id=None,
            task_id=None,
            title=None,
            description=None,
            files=[],
            ai="codex",
            note="claim",
            status="all",
            workspace=str(temp_workspace),
        )

        result = cli.cmd_patches(args)

        assert result == 0
        mock_manager._save_state.assert_called_once()
        mock_manager.update_patch_status.assert_called_once()


# ==================== cmd_conflicts 测试 ====================


class TestCmdConflicts:
    """测试 conflicts 命令"""

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_conflicts_list(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试列出冲突"""
        # 准备
        mock_manager = Mock()
        mock_manager.get_conflicts.return_value = [
            {
                "conflict_id": "conflict-001",
                "task_id_1": "TASK-001",
                "ai_type_1": "claude_code",
                "task_id_2": "TASK-002",
                "ai_type_2": "copilot",
                "overlapping_files": ["test.py"],
                "status": "open",
            }
        ]
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(subcommand="list", status=None, workspace=str(temp_workspace))

        # 执行
        result = cli.cmd_conflicts(args)

        # 验证
        assert result == 0
        mock_manager.get_conflicts.assert_called_once()

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_conflicts_resolve(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试解决冲突"""
        # 准备
        mock_manager = Mock()
        mock_manager.resolve_conflict.return_value = True
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="resolve",
            conflict_id="conflict-001",
            resolution="已解决",
            workspace=str(temp_workspace),
        )

        # 执行
        result = cli.cmd_conflicts(args)

        # 验证
        assert result == 0
        mock_manager.resolve_conflict.assert_called_once_with("conflict-001", "已解决")

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_conflicts_resolve_not_found(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试解决不存在的冲突"""
        # 准备
        mock_manager = Mock()
        mock_manager.resolve_conflict.return_value = False
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(
            subcommand="resolve",
            conflict_id="conflict-999",
            resolution="已解决",
            workspace=str(temp_workspace),
        )

        # 执行
        result = cli.cmd_conflicts(args)

        # 验证
        assert result == 1

    def test_conflicts_resolve_missing_id(self, temp_workspace):
        """测试解决冲突时缺少 conflict_id"""
        args = SimpleNamespace(
            subcommand="resolve", conflict_id=None, resolution="", workspace=str(temp_workspace)
        )

        # 执行
        result = cli.cmd_conflicts(args)

        # 验证
        assert result == 1


# ==================== cmd_init 测试 ====================


class TestCmdInit:
    """测试 init 命令"""

    def test_init_creates_directories(self, temp_workspace):
        """测试初始化创建目录"""
        args = SimpleNamespace(workspace=str(temp_workspace))

        # 执行
        result = cli.cmd_init(args)

        # 验证
        assert result == 0
        assert (temp_workspace / ".vscode").exists()
        assert (temp_workspace / "logs" / "activations").exists()
        assert (temp_workspace / "logs" / "claude-code").exists()
        assert (temp_workspace / "logs" / "codearts-agent").exists()
        assert (temp_workspace / "logs" / "copilot").exists()
        assert (temp_workspace / ".vscode" / "ai-collab.json").exists()

    def test_init_creates_config_file(self, temp_workspace):
        """测试初始化创建配置文件"""
        args = SimpleNamespace(workspace=str(temp_workspace))

        # 执行
        result = cli.cmd_init(args)

        # 验证
        assert result == 0
        config_file = temp_workspace / ".vscode" / "ai-collab.json"
        assert config_file.exists()

        import json

        with open(config_file) as f:
            config = json.load(f)

        assert config["version"] == "1.0.0"
        assert config["handoffFile"] == "./logs/handoff_status.json"
        assert "claude_code" in config["enabledAIs"]
        assert "codex" in config["enabledAIs"]
        assert "codearts_agent" in config["enabledAIs"]
        assert config["controller"]["intervalSec"] == 30
        assert config["controller"]["defaultAssignee"] == "codex"
        assert config["controller"]["blockedTimeoutSec"] == 3600
        assert config["controller"]["prewarnRatio"] == 0.8
        assert config["controller"]["history"] == "logs/task_controller_history.jsonl"
        assert config["dispatch"]["includePending"] is False
        assert config["dispatch"]["report"] == "logs/task_dispatch_report.json"
        assert config["dispatch"]["history"] == "logs/task_dispatch_history.jsonl"
        assert config["dispatch"]["state"] == "logs/agent_dispatch_state.json"
        assert (
            config["dispatch"]["orders"]
            == "collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md"
        )
        assert config["receipt"]["report"] == "logs/task_receipt_report.json"
        assert config["receipt"]["history"] == "logs/task_receipt_history.jsonl"
        assert config["receipt"]["state"] == "logs/agent_receipt_state.json"
        assert (
            config["receipt"]["summary"]
            == "collaboration/monitoring/AGENT_RECEIPT_SUMMARY_latest.md"
        )
        assert config["benefit"]["dispatchHistory"] == ["logs/task_dispatch_history.jsonl"]
        assert config["benefit"]["receiptHistory"] == ["logs/task_receipt_history.jsonl"]
        assert config["benefit"]["targetRatio"] == 3.0
        assert config["benefit"]["window"] == 14
        assert config["benefit"]["report"] == "logs/automation_benefit_report.json"
        assert (
            config["benefit"]["output"]
            == "collaboration/monitoring/AUTOMATION_BENEFIT_DASHBOARD_latest.md"
        )
        assert config["trigger"]["report"] == "logs/task_trigger_report.json"
        assert config["trigger"]["history"] == "logs/task_trigger_history.jsonl"
        assert config["trigger"]["outputDir"] == "collaboration/monitoring"
        assert config["trigger"]["payloadPrefix"] == "AGENT_TRIGGER"
        assert config["workspaceGuard"]["enabled"] is True
        assert config["workspaceGuard"]["applyOnly"] is True
        assert config["workspaceGuard"]["requireSourceClean"] is True
        assert config["workspaceGuard"]["dirtyTotalThreshold"] == 120
        assert config["workspaceGuard"]["rootDeletedThreshold"] == 10
        assert config["spawnAgentGuard"]["enabled"] is True
        assert config["spawnAgentGuard"]["allowedLeadAgents"] == ["codex"]
        assert config["spawnAgentGuard"]["requireParentTask"] is True
        assert config["spawnAgentGuard"]["requireWriteSet"] is True
        assert config["spawnAgentGuard"]["allowReadOnly"] is True
        assert ".vscode/ai-collab.json" in config["spawnAgentGuard"]["protectedPaths"]
        assert "collaboration/tasks/" in config["spawnAgentGuard"]["protectedPrefixes"]
        assert (
            config["spawnAgentGuard"]["report"]
            == "logs/workspace_forensics/spawn_agent_guard_latest.json"
        )
        assert (
            config["spawnAgentGuard"]["history"]
            == "logs/workspace_forensics/spawn_agent_guard_history.jsonl"
        )


# ==================== cmd_controller 测试 ====================


class TestCmdController:
    """测试 controller 命令"""

    @patch("ai_collab.cli.subprocess.run")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_controller_uses_config_defaults(
        self, mock_set_env, mock_vscode, mock_run, temp_workspace
    ):
        """测试 controller 使用项目配置默认值"""
        mock_vscode.get_project_config.return_value = {
            "controller": {
                "intervalSec": 12,
                "pendingTimeoutSec": 100,
                "activeTimeoutSec": 50,
                "blockedTimeoutSec": 40,
                "prewarnRatio": 0.75,
                "defaultAssignee": "claude_code",
                "report": "logs/custom_controller_report.json",
                "history": "logs/custom_controller_history.jsonl",
            }
        }
        mock_run.return_value = SimpleNamespace(returncode=0)

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            once=True,
            dry_run=True,
            interval_sec=None,
            max_iterations=None,
            pending_timeout_sec=None,
            active_timeout_sec=None,
            blocked_timeout_sec=None,
            prewarn_ratio=None,
            history=None,
            default_assignee=None,
            report=None,
        )

        result = cli.cmd_controller(args)

        assert result == 0
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "--interval-sec" in cmd and "12" in cmd
        assert "--pending-timeout-sec" in cmd and "100" in cmd
        assert "--active-timeout-sec" in cmd and "50" in cmd
        assert "--blocked-timeout-sec" in cmd and "40" in cmd
        assert "--prewarn-ratio" in cmd and "0.75" in cmd
        assert "--default-assignee" in cmd and "claude_code" in cmd
        assert "--report" in cmd and "logs/custom_controller_report.json" in cmd
        assert "--history" in cmd and "logs/custom_controller_history.jsonl" in cmd
        assert "--once" in cmd
        assert "--dry-run" in cmd

    @patch("ai_collab.cli.subprocess.run")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_controller_cli_args_override_config(
        self, mock_set_env, mock_vscode, mock_run, temp_workspace
    ):
        """测试 controller 参数覆盖配置值"""
        mock_vscode.get_project_config.return_value = {
            "controller": {
                "intervalSec": 12,
                "pendingTimeoutSec": 100,
                "activeTimeoutSec": 50,
                "blockedTimeoutSec": 40,
                "prewarnRatio": 0.75,
                "defaultAssignee": "claude_code",
                "report": "logs/custom_controller_report.json",
                "history": "logs/custom_controller_history.jsonl",
            }
        }
        mock_run.return_value = SimpleNamespace(returncode=7)

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            once=False,
            dry_run=False,
            interval_sec=5,
            max_iterations=3,
            pending_timeout_sec=20,
            active_timeout_sec=10,
            blocked_timeout_sec=8,
            prewarn_ratio=0.66,
            history="logs/override_history.jsonl",
            default_assignee="codex",
            report="logs/override_report.json",
        )

        result = cli.cmd_controller(args)

        assert result == 7
        cmd = mock_run.call_args[0][0]
        assert "--interval-sec" in cmd and "5" in cmd
        assert "--pending-timeout-sec" in cmd and "20" in cmd
        assert "--active-timeout-sec" in cmd and "10" in cmd
        assert "--blocked-timeout-sec" in cmd and "8" in cmd
        assert "--prewarn-ratio" in cmd and "0.66" in cmd
        assert "--default-assignee" in cmd and "codex" in cmd
        assert "--report" in cmd and "logs/override_report.json" in cmd
        assert "--history" in cmd and "logs/override_history.jsonl" in cmd
        assert "--max-iterations" in cmd and "3" in cmd
        assert "--once" not in cmd
        assert "--dry-run" not in cmd


class TestCmdDispatch:
    """测试 dispatch 命令"""

    @patch("ai_collab.cli._cli_main.run_workspace_guard")
    @patch("ai_collab.cli.subprocess.run")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_dispatch_uses_config_defaults(
        self, mock_set_env, mock_vscode, mock_run, mock_guard, temp_workspace
    ):
        """测试 dispatch 使用项目配置默认值"""
        mock_vscode.get_project_config.return_value = {
            "dispatch": {
                "includePending": True,
                "report": "logs/custom_dispatch_report.json",
                "history": "logs/custom_dispatch_history.jsonl",
                "state": "logs/custom_dispatch_state.json",
                "orders": "collaboration/monitoring/CUSTOM_DISPATCH_ORDERS.md",
            }
        }
        mock_guard.return_value = {
            "allowed": True,
            "totals": {"total": 0, "untracked": 0, "deleted": 0, "modified": 0},
            "domains": {"source": 0, "ops": 0, "docs": 0, "other": 0},
            "root_deleted": 0,
            "results_untracked": 0,
            "report_file": "logs/workspace_forensics/workspace_guard_latest.json",
            "history_file": "logs/workspace_forensics/workspace_guard_history.jsonl",
            "warnings": [],
            "violations": [],
        }
        mock_run.return_value = SimpleNamespace(returncode=0)

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=True,
            include_pending=False,
            redispatch=False,
            report=None,
            history=None,
            state=None,
            orders=None,
        )

        result = cli.cmd_dispatch(args)
        assert result == 0

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "--include-pending" in cmd
        assert "--dry-run" in cmd
        assert "--report" in cmd and "logs/custom_dispatch_report.json" in cmd
        assert "--history" in cmd and "logs/custom_dispatch_history.jsonl" in cmd
        assert "--state" in cmd and "logs/custom_dispatch_state.json" in cmd
        assert "--orders" in cmd and "collaboration/monitoring/CUSTOM_DISPATCH_ORDERS.md" in cmd

    @patch("ai_collab.cli._cli_main.run_workspace_guard")
    @patch("ai_collab.cli.subprocess.run")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_dispatch_apply_autosyncs_trigger_payloads(
        self, mock_set_env, mock_vscode, mock_run, mock_guard, temp_workspace
    ):
        """测试 dispatch apply 会自动刷新 per-agent trigger latest，避免旧缓存残留"""
        mock_vscode.get_project_config.return_value = {
            "enabledAIs": ["claude_code", "codearts_agent"],
            "dispatch": {
                "includePending": False,
                "orders": "collaboration/monitoring/CUSTOM_DISPATCH_ORDERS.md",
            },
            "trigger": {
                "outputDir": "collaboration/monitoring",
                "payloadPrefix": "AGENT_TRIGGER",
            },
        }
        mock_guard.return_value = {
            "allowed": True,
            "totals": {"total": 0, "untracked": 0, "deleted": 0, "modified": 0},
            "domains": {"source": 0, "ops": 0, "docs": 0, "other": 0},
            "root_deleted": 0,
            "results_untracked": 0,
            "report_file": "logs/workspace_forensics/workspace_guard_latest.json",
            "history_file": "logs/workspace_forensics/workspace_guard_history.jsonl",
            "warnings": [],
            "violations": [],
        }
        mock_run.return_value = SimpleNamespace(returncode=0)

        orders_file = temp_workspace / "collaboration" / "monitoring" / "CUSTOM_DISPATCH_ORDERS.md"
        orders_file.parent.mkdir(parents=True, exist_ok=True)
        orders_file.write_text(
            """# Agent Dispatch Orders（自动生成）

## 发送给 `Claude` (`claude_code`)

### TASK-C-NEW
```text
claude payload new
```
""",
            encoding="utf-8",
        )

        stale_codearts = (
            temp_workspace
            / "collaboration"
            / "monitoring"
            / "AGENT_TRIGGER_codearts_agent_latest.md"
        )
        stale_codearts.write_text("STALE TASK-OLD", encoding="utf-8")

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=False,
            include_pending=False,
            redispatch=False,
            force_workspace=False,
            report=None,
            history=None,
            state=None,
            orders=None,
        )

        result = cli.cmd_dispatch(args)
        assert result == 0
        mock_run.assert_called_once()

        claude_payload = (
            temp_workspace / "collaboration" / "monitoring" / "AGENT_TRIGGER_claude_code_latest.md"
        )
        codearts_payload = (
            temp_workspace
            / "collaboration"
            / "monitoring"
            / "AGENT_TRIGGER_codearts_agent_latest.md"
        )
        assert claude_payload.exists()
        assert codearts_payload.exists()
        assert "TASK-C-NEW" in claude_payload.read_text(encoding="utf-8")
        codearts_text = codearts_payload.read_text(encoding="utf-8")
        assert "当前无待派发任务" in codearts_text
        assert "TASK-OLD" not in codearts_text

    @patch("ai_collab.cli._cli_main.run_workspace_guard")
    @patch("ai_collab.cli.subprocess.run")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_dispatch_cli_args_override_config(
        self, mock_set_env, mock_vscode, mock_run, mock_guard, temp_workspace
    ):
        """测试 dispatch 参数覆盖配置值"""
        mock_vscode.get_project_config.return_value = {
            "dispatch": {
                "includePending": False,
                "report": "logs/custom_dispatch_report.json",
                "history": "logs/custom_dispatch_history.jsonl",
                "state": "logs/custom_dispatch_state.json",
                "orders": "collaboration/monitoring/CUSTOM_DISPATCH_ORDERS.md",
            }
        }
        mock_guard.return_value = {
            "allowed": True,
            "totals": {"total": 0, "untracked": 0, "deleted": 0, "modified": 0},
            "domains": {"source": 0, "ops": 0, "docs": 0, "other": 0},
            "root_deleted": 0,
            "results_untracked": 0,
            "report_file": "logs/workspace_forensics/workspace_guard_latest.json",
            "history_file": "logs/workspace_forensics/workspace_guard_history.jsonl",
            "warnings": [],
            "violations": [],
        }
        mock_run.return_value = SimpleNamespace(returncode=3)

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=False,
            include_pending=True,
            redispatch=True,
            report="logs/override_dispatch_report.json",
            history="logs/override_dispatch_history.jsonl",
            state="logs/override_dispatch_state.json",
            orders="collaboration/monitoring/OVERRIDE_DISPATCH_ORDERS.md",
        )

        result = cli.cmd_dispatch(args)
        assert result == 3

        cmd = mock_run.call_args[0][0]
        assert "--include-pending" in cmd
        assert "--redispatch" in cmd
        assert "--dry-run" not in cmd
        assert "--report" in cmd and "logs/override_dispatch_report.json" in cmd
        assert "--history" in cmd and "logs/override_dispatch_history.jsonl" in cmd
        assert "--state" in cmd and "logs/override_dispatch_state.json" in cmd
        assert "--orders" in cmd and "collaboration/monitoring/OVERRIDE_DISPATCH_ORDERS.md" in cmd

    @patch("ai_collab.cli._cli_main.run_workspace_guard")
    @patch("ai_collab.cli.subprocess.run")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_dispatch_blocks_when_workspace_guard_denies(
        self, mock_set_env, mock_vscode, mock_run, mock_guard, temp_workspace
    ):
        mock_vscode.get_project_config.return_value = {"dispatch": {}}
        mock_guard.return_value = {
            "allowed": False,
            "totals": {"total": 331, "untracked": 223, "deleted": 69, "modified": 39},
            "domains": {"source": 70, "ops": 84, "docs": 0, "other": 177},
            "root_deleted": 69,
            "results_untracked": 79,
            "report_file": "logs/workspace_forensics/workspace_guard_latest.json",
            "history_file": "logs/workspace_forensics/workspace_guard_history.jsonl",
            "warnings": [],
            "violations": ["dirty_total=331 exceeds threshold=120"],
        }
        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=False,
            include_pending=False,
            redispatch=False,
            force_workspace=False,
            report=None,
            history=None,
            state=None,
            orders=None,
        )
        assert cli.cmd_dispatch(args) == 2
        mock_run.assert_not_called()


class TestCmdTrigger:
    """测试 trigger 命令"""

    @patch("ai_collab.cli._cli_main.cmd_dispatch")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_trigger_generates_agent_payload_files(
        self, mock_set_env, mock_vscode, mock_dispatch, temp_workspace
    ):
        """测试 trigger 生成按 Agent 的派单文件"""
        mock_vscode.get_project_config.return_value = {
            "activationKeyword": "2X",
            "enabledAIs": ["claude_code", "codex", "codearts_agent"],
            "dispatch": {
                "orders": "collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md",
                "report": "logs/task_dispatch_report.json",
            },
            "trigger": {
                "report": "logs/task_trigger_report.json",
                "history": "logs/task_trigger_history.jsonl",
                "outputDir": "collaboration/monitoring",
                "payloadPrefix": "AGENT_TRIGGER",
            },
        }
        mock_dispatch.return_value = 0

        orders_file = (
            temp_workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_latest.md"
        )
        orders_file.parent.mkdir(parents=True, exist_ok=True)
        orders_file.write_text(
            """# Agent Dispatch Orders（自动生成）

## 发送给 `Claude` (`claude_code`)

### TASK-C-001
```text
claude payload
```

## 发送给 `Codex` (`codex`)

### TASK-X-001
```text
codex payload
```

## 发送给 `CodeArts` (`codearts_agent`)

### TASK-A-001
```text
codearts payload
```
""",
            encoding="utf-8",
        )

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            phrase="2X DISPATCH",
            target=None,
            dry_run=True,
            include_pending=False,
            redispatch=False,
            force_workspace=False,
            dispatch_report=None,
            dispatch_history=None,
            dispatch_state=None,
            dispatch_orders=None,
            output_dir=None,
            report=None,
            history=None,
            copy=False,
        )

        result = cli.cmd_trigger(args)
        assert result == 0
        mock_dispatch.assert_called_once()

        claude_payload = (
            temp_workspace / "collaboration" / "monitoring" / "AGENT_TRIGGER_claude_code_latest.md"
        )
        codex_payload = (
            temp_workspace / "collaboration" / "monitoring" / "AGENT_TRIGGER_codex_latest.md"
        )
        codearts_payload = (
            temp_workspace
            / "collaboration"
            / "monitoring"
            / "AGENT_TRIGGER_codearts_agent_latest.md"
        )
        assert claude_payload.exists()
        assert codex_payload.exists()
        assert codearts_payload.exists()
        assert "TASK-C-001" in claude_payload.read_text(encoding="utf-8")
        assert "TASK-X-001" in codex_payload.read_text(encoding="utf-8")
        assert "TASK-A-001" in codearts_payload.read_text(encoding="utf-8")

        trigger_report = json.loads(
            (temp_workspace / "logs" / "task_trigger_report.json").read_text(encoding="utf-8")
        )
        assert trigger_report["trigger_phrase"] == "2X DISPATCH"
        assert len(trigger_report["output_files"]) == 3
        assert (
            "collaboration/monitoring/AGENT_TRIGGER_codex_latest.md"
            in trigger_report["output_files"]
        )

    @patch("ai_collab.cli._cli_main.cmd_dispatch")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_trigger_supports_codex_target(
        self, mock_set_env, mock_vscode, mock_dispatch, temp_workspace
    ):
        mock_vscode.get_project_config.return_value = {
            "activationKeyword": "2X",
            "dispatch": {
                "orders": "collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md",
                "report": "logs/task_dispatch_report.json",
            },
            "trigger": {
                "report": "logs/task_trigger_report.json",
                "history": "logs/task_trigger_history.jsonl",
                "outputDir": "collaboration/monitoring",
                "payloadPrefix": "AGENT_TRIGGER",
            },
        }
        mock_dispatch.return_value = 0

        orders_file = (
            temp_workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_latest.md"
        )
        orders_file.parent.mkdir(parents=True, exist_ok=True)
        orders_file.write_text(
            """# Agent Dispatch Orders（自动生成）

## 发送给 `Codex` (`codex`)

### TASK-X-001
```text
codex payload
```
""",
            encoding="utf-8",
        )

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            phrase="2X DISPATCH CODEX",
            target=None,
            dry_run=True,
            include_pending=False,
            redispatch=False,
            force_workspace=False,
            dispatch_report=None,
            dispatch_history=None,
            dispatch_state=None,
            dispatch_orders=None,
            output_dir=None,
            report=None,
            history=None,
            copy=False,
        )

        result = cli.cmd_trigger(args)
        assert result == 0
        codex_payload = (
            temp_workspace / "collaboration" / "monitoring" / "AGENT_TRIGGER_codex_latest.md"
        )
        assert codex_payload.exists()
        assert "TASK-X-001" in codex_payload.read_text(encoding="utf-8")
        trigger_report = json.loads(
            (temp_workspace / "logs" / "task_trigger_report.json").read_text(encoding="utf-8")
        )
        assert trigger_report["target"] == "codex"
        assert trigger_report["output_files"] == [
            "collaboration/monitoring/AGENT_TRIGGER_codex_latest.md"
        ]

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main.cmd_dispatch")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_trigger_auto_enables_redispatch_for_reopened_tasks(
        self, mock_set_env, mock_vscode, mock_dispatch, mock_state_cls, temp_workspace
    ):
        mock_vscode.get_project_config.return_value = {
            "activationKeyword": "2X",
            "dispatch": {
                "orders": "collaboration/monitoring/AGENT_DISPATCH_ORDERS_latest.md",
                "report": "logs/task_dispatch_report.json",
            },
            "trigger": {
                "report": "logs/task_trigger_report.json",
                "history": "logs/task_trigger_history.jsonl",
                "outputDir": "collaboration/monitoring",
                "payloadPrefix": "AGENT_TRIGGER",
            },
        }
        mock_dispatch.return_value = 0
        mock_state = Mock()
        mock_state.get_all_tasks.return_value = [
            {
                "task_id": "TASK-C-078",
                "status": "implementing",
                "assignee": "claude_code",
            }
        ]
        mock_state_cls.return_value = mock_state

        dispatch_state_file = temp_workspace / "logs" / "agent_dispatch_state.json"
        dispatch_state_file.parent.mkdir(parents=True, exist_ok=True)
        dispatch_state_file.write_text(
            json.dumps(
                {
                    "version": "1.0.0",
                    "items": {
                        "TASK-C-078": {
                            "task_id": "TASK-C-078",
                            "assignee": "claude_code",
                            "dispatch_count": 1,
                        }
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        orders_file = (
            temp_workspace / "collaboration" / "monitoring" / "AGENT_DISPATCH_ORDERS_latest.md"
        )
        orders_file.parent.mkdir(parents=True, exist_ok=True)
        orders_file.write_text(
            """# Agent Dispatch Orders（自动生成）

## 发送给 `Claude` (`claude_code`)

### TASK-C-078
```text
claude payload
```
""",
            encoding="utf-8",
        )

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            phrase="2X DISPATCH CLAUDE",
            target=None,
            dry_run=True,
            include_pending=False,
            redispatch=False,
            force_workspace=False,
            dispatch_report=None,
            dispatch_history=None,
            dispatch_state=None,
            dispatch_orders=None,
            output_dir=None,
            report=None,
            history=None,
            copy=False,
        )

        result = cli.cmd_trigger(args)
        assert result == 0
        dispatch_args = mock_dispatch.call_args[0][0]
        assert dispatch_args.include_pending is True
        assert dispatch_args.redispatch is True

    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_trigger_rejects_invalid_phrase(self, mock_set_env, mock_vscode, temp_workspace):
        """测试 trigger 拒绝非法暗语"""
        mock_vscode.get_project_config.return_value = {"activationKeyword": "2X"}

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            phrase="AX DISPATCH",
            target=None,
            dry_run=True,
            include_pending=False,
            redispatch=False,
            force_workspace=False,
            dispatch_report=None,
            dispatch_history=None,
            dispatch_state=None,
            dispatch_orders=None,
            output_dir=None,
            report=None,
            history=None,
            copy=False,
        )
        assert cli.cmd_trigger(args) == 2

    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_trigger_copy_requires_single_target(self, mock_set_env, mock_vscode, temp_workspace):
        """测试 copy 仅支持单目标"""
        mock_vscode.get_project_config.return_value = {"activationKeyword": "2X"}
        args = SimpleNamespace(
            workspace=str(temp_workspace),
            phrase="2X DISPATCH",
            target="all",
            dry_run=True,
            include_pending=False,
            redispatch=False,
            force_workspace=False,
            dispatch_report=None,
            dispatch_history=None,
            dispatch_state=None,
            dispatch_orders=None,
            output_dir=None,
            report=None,
            history=None,
            copy=True,
        )
        assert cli.cmd_trigger(args) == 2


class TestCmd2X:
    """测试 2x 快捷命令"""

    @patch("ai_collab.cli._cli_main.cmd_trigger")
    def test_2x_claude_maps_to_trigger(self, mock_trigger, temp_workspace):
        mock_trigger.return_value = 0
        args = SimpleNamespace(
            workspace=str(temp_workspace),
            target="claude",
            dry_run=True,
            include_pending=False,
            redispatch=False,
            no_copy=False,
            force_workspace=False,
        )
        result = cli.cmd_2x(args)
        assert result == 0
        call_args = mock_trigger.call_args[0][0]
        assert call_args.phrase == "2X DISPATCH CLAUDE"
        assert call_args.target == "claude_code"
        assert call_args.copy is True

    @patch("ai_collab.cli._cli_main.cmd_trigger")
    def test_2x_codearts_maps_to_trigger(self, mock_trigger, temp_workspace):
        mock_trigger.return_value = 0
        args = SimpleNamespace(
            workspace=str(temp_workspace),
            target="codearts",
            dry_run=False,
            include_pending=True,
            redispatch=True,
            no_copy=False,
            force_workspace=False,
        )
        result = cli.cmd_2x(args)
        assert result == 0
        call_args = mock_trigger.call_args[0][0]
        assert call_args.phrase == "2X DISPATCH CodeArts"
        assert call_args.target == "codearts_agent"
        assert call_args.copy is True
        assert call_args.include_pending is True
        assert call_args.redispatch is True

    @patch("ai_collab.cli._cli_main.cmd_trigger")
    def test_2x_codex_maps_to_trigger(self, mock_trigger, temp_workspace):
        mock_trigger.return_value = 0
        args = SimpleNamespace(
            workspace=str(temp_workspace),
            target="codex",
            dry_run=True,
            include_pending=False,
            redispatch=False,
            no_copy=False,
            dispatch_only=False,
            force_workspace=False,
        )
        result = cli.cmd_2x(args)
        assert result == 0
        call_args = mock_trigger.call_args[0][0]
        assert call_args.phrase == "2X DISPATCH CODEX"
        assert call_args.target == "codex"
        assert call_args.copy is True

    @patch("ai_collab.cli._cli_main.cmd_trigger")
    def test_2x_all_disables_copy(self, mock_trigger, temp_workspace):
        mock_trigger.return_value = 0
        args = SimpleNamespace(
            workspace=str(temp_workspace),
            target="all",
            dry_run=True,
            include_pending=False,
            redispatch=False,
            no_copy=False,
            dispatch_only=False,
            force_workspace=False,
        )
        result = cli.cmd_2x(args)
        assert result == 0
        call_args = mock_trigger.call_args[0][0]
        assert call_args.phrase == "2X DISPATCH"
        assert call_args.target == "all"
        assert call_args.copy is False

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main.cmd_trigger")
    def test_2x_claude_auto_enables_pending_and_redispatch_when_pending_exists(
        self, mock_trigger, mock_state_cls, temp_workspace
    ):
        mock_state = Mock()
        mock_state.get_all_tasks.return_value = [
            {"task_id": "TASK-C-1", "status": "pending", "assignee": "claude_code"},
        ]
        mock_state_cls.return_value = mock_state
        mock_trigger.return_value = 0

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            target="claude",
            dry_run=False,
            include_pending=False,
            redispatch=False,
            no_copy=False,
            dispatch_only=False,
            force_workspace=False,
        )
        result = cli.cmd_2x(args)
        assert result == 0
        call_args = mock_trigger.call_args[0][0]
        assert call_args.target == "claude_code"
        assert call_args.include_pending is True
        assert call_args.redispatch is True

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main.cmd_trigger")
    def test_2x_all_auto_enables_pending_and_redispatch_when_pending_exists(
        self, mock_trigger, mock_state_cls, temp_workspace
    ):
        mock_state = Mock()
        mock_state.get_all_tasks.return_value = [
            {"task_id": "TASK-A-1", "status": "pending", "assignee": "codearts_agent"},
            {"task_id": "TASK-C-1", "status": "pending", "assignee": "claude_code"},
        ]
        mock_state_cls.return_value = mock_state
        mock_trigger.return_value = 0

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            target="all",
            dry_run=True,
            include_pending=False,
            redispatch=False,
            no_copy=False,
            dispatch_only=False,
            force_workspace=False,
        )
        result = cli.cmd_2x(args)
        assert result == 0
        call_args = mock_trigger.call_args[0][0]
        assert call_args.target == "all"
        assert call_args.include_pending is True
        assert call_args.redispatch is True

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main.cmd_trigger")
    def test_2x_claude_auto_enables_redispatch_for_reopened_tasks(
        self, mock_trigger, mock_state_cls, temp_workspace
    ):
        mock_state = Mock()
        mock_state.get_all_tasks.return_value = [
            {"task_id": "TASK-C-078", "status": "implementing", "assignee": "claude_code"},
        ]
        mock_state_cls.return_value = mock_state
        mock_trigger.return_value = 0

        dispatch_state_file = temp_workspace / "logs" / "agent_dispatch_state.json"
        dispatch_state_file.parent.mkdir(parents=True, exist_ok=True)
        dispatch_state_file.write_text(
            json.dumps(
                {
                    "version": "1.0.0",
                    "items": {
                        "TASK-C-078": {
                            "task_id": "TASK-C-078",
                            "assignee": "claude_code",
                            "dispatch_count": 2,
                        }
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            target="claude",
            dry_run=False,
            include_pending=False,
            redispatch=False,
            no_copy=False,
            dispatch_only=False,
            force_workspace=False,
        )
        result = cli.cmd_2x(args)
        assert result == 0
        call_args = mock_trigger.call_args[0][0]
        assert call_args.target == "claude_code"
        assert call_args.include_pending is True
        assert call_args.redispatch is True

    @patch("ai_collab.cli._cli_main.cmd_receipt")
    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main.cmd_trigger")
    def test_2x_all_with_testing_tasks_falls_back_to_receipt(
        self, mock_trigger, mock_state_cls, mock_receipt, temp_workspace
    ):
        mock_state = Mock()
        mock_state.get_all_tasks.return_value = [
            {"task_id": "TASK-1", "status": "testing"},
            {"task_id": "TASK-2", "status": "testing"},
        ]
        mock_state_cls.return_value = mock_state
        mock_receipt.return_value = 0

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            target="all",
            dry_run=False,
            include_pending=False,
            redispatch=False,
            no_copy=False,
            dispatch_only=False,
            force_workspace=False,
        )
        result = cli.cmd_2x(args)
        assert result == 0
        mock_receipt.assert_called_once()
        mock_trigger.assert_not_called()

    @patch("ai_collab.cli._cli_main.cmd_receipt")
    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main.cmd_trigger")
    def test_2x_all_dispatch_only_bypasses_fallback(
        self, mock_trigger, mock_state_cls, mock_receipt, temp_workspace
    ):
        mock_state = Mock()
        mock_state.get_all_tasks.return_value = [{"task_id": "TASK-1", "status": "testing"}]
        mock_state_cls.return_value = mock_state
        mock_trigger.return_value = 0

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            target="all",
            dry_run=True,
            include_pending=False,
            redispatch=False,
            no_copy=False,
            dispatch_only=True,
            force_workspace=False,
        )
        result = cli.cmd_2x(args)
        assert result == 0
        mock_trigger.assert_called_once()
        mock_receipt.assert_not_called()

    def test_2x_invalid_target_returns_2(self, temp_workspace):
        args = SimpleNamespace(
            workspace=str(temp_workspace),
            target="invalid",
            dry_run=True,
            include_pending=False,
            redispatch=False,
            no_copy=False,
            dispatch_only=False,
            force_workspace=False,
        )
        assert cli.cmd_2x(args) == 2


class TestCmdReceipt:
    """测试 receipt 命令"""

    @patch("ai_collab.cli._cli_main.run_workspace_guard")
    @patch("ai_collab.cli.subprocess.run")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_receipt_uses_config_defaults(
        self, mock_set_env, mock_vscode, mock_run, mock_guard, temp_workspace
    ):
        """测试 receipt 使用项目配置默认值"""
        mock_vscode.get_project_config.return_value = {
            "receipt": {
                "report": "logs/custom_receipt_report.json",
                "history": "logs/custom_receipt_history.jsonl",
                "state": "logs/custom_receipt_state.json",
                "summary": "collaboration/monitoring/CUSTOM_RECEIPT_SUMMARY.md",
            }
        }
        mock_guard.return_value = {
            "allowed": True,
            "totals": {"total": 0, "untracked": 0, "deleted": 0, "modified": 0},
            "domains": {"source": 0, "ops": 0, "docs": 0, "other": 0},
            "root_deleted": 0,
            "results_untracked": 0,
            "report_file": "logs/workspace_forensics/workspace_guard_latest.json",
            "history_file": "logs/workspace_forensics/workspace_guard_history.jsonl",
            "warnings": [],
            "violations": [],
        }
        mock_run.return_value = SimpleNamespace(returncode=0)

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=True,
            reclose=False,
            report=None,
            history=None,
            state=None,
            summary=None,
        )

        result = cli.cmd_receipt(args)
        assert result == 0

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "--dry-run" in cmd
        assert "--reclose" not in cmd
        assert "--report" in cmd and "logs/custom_receipt_report.json" in cmd
        assert "--history" in cmd and "logs/custom_receipt_history.jsonl" in cmd
        assert "--state" in cmd and "logs/custom_receipt_state.json" in cmd
        assert "--summary" in cmd and "collaboration/monitoring/CUSTOM_RECEIPT_SUMMARY.md" in cmd

    @patch("ai_collab.cli._cli_main.run_workspace_guard")
    @patch("ai_collab.cli.subprocess.run")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_receipt_cli_args_override_config(
        self, mock_set_env, mock_vscode, mock_run, mock_guard, temp_workspace
    ):
        """测试 receipt 参数覆盖配置值"""
        mock_vscode.get_project_config.return_value = {
            "receipt": {
                "report": "logs/custom_receipt_report.json",
                "history": "logs/custom_receipt_history.jsonl",
                "state": "logs/custom_receipt_state.json",
                "summary": "collaboration/monitoring/CUSTOM_RECEIPT_SUMMARY.md",
            }
        }
        mock_guard.return_value = {
            "allowed": True,
            "totals": {"total": 0, "untracked": 0, "deleted": 0, "modified": 0},
            "domains": {"source": 0, "ops": 0, "docs": 0, "other": 0},
            "root_deleted": 0,
            "results_untracked": 0,
            "report_file": "logs/workspace_forensics/workspace_guard_latest.json",
            "history_file": "logs/workspace_forensics/workspace_guard_history.jsonl",
            "warnings": [],
            "violations": [],
        }
        mock_run.return_value = SimpleNamespace(returncode=2)

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=False,
            reclose=True,
            report="logs/override_receipt_report.json",
            history="logs/override_receipt_history.jsonl",
            state="logs/override_receipt_state.json",
            summary="collaboration/monitoring/OVERRIDE_RECEIPT_SUMMARY.md",
        )

        result = cli.cmd_receipt(args)
        assert result == 2

        cmd = mock_run.call_args[0][0]
        assert "--dry-run" not in cmd
        assert "--reclose" in cmd
        assert "--report" in cmd and "logs/override_receipt_report.json" in cmd
        assert "--history" in cmd and "logs/override_receipt_history.jsonl" in cmd
        assert "--state" in cmd and "logs/override_receipt_state.json" in cmd
        assert "--summary" in cmd and "collaboration/monitoring/OVERRIDE_RECEIPT_SUMMARY.md" in cmd

    @patch("ai_collab.cli._cli_main.run_workspace_guard")
    @patch("ai_collab.cli.subprocess.run")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_receipt_blocks_when_workspace_guard_denies(
        self, mock_set_env, mock_vscode, mock_run, mock_guard, temp_workspace
    ):
        mock_vscode.get_project_config.return_value = {"receipt": {}}
        mock_guard.return_value = {
            "allowed": False,
            "totals": {"total": 331, "untracked": 223, "deleted": 69, "modified": 39},
            "domains": {"source": 70, "ops": 84, "docs": 0, "other": 177},
            "root_deleted": 69,
            "results_untracked": 79,
            "report_file": "logs/workspace_forensics/workspace_guard_latest.json",
            "history_file": "logs/workspace_forensics/workspace_guard_history.jsonl",
            "warnings": [],
            "violations": ["source domain is not clean"],
        }
        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=False,
            reclose=False,
            force_workspace=False,
            report=None,
            history=None,
            state=None,
            summary=None,
        )
        assert cli.cmd_receipt(args) == 2
        mock_run.assert_not_called()

    @patch("ai_collab.cli._cli_main._execute_hygiene_once")
    @patch("ai_collab.cli._cli_main.run_workspace_guard")
    @patch("ai_collab.cli.subprocess.run")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_receipt_generate_reports_refreshes_outputs_without_hygiene(
        self,
        mock_set_env,
        mock_vscode,
        mock_run,
        mock_guard,
        mock_hygiene,
        temp_workspace,
    ):
        mock_vscode.get_project_config.return_value = {
            "receipt": {},
            "workspaceHygiene": {
                "onReceiptClose": False,
            },
        }
        mock_guard.return_value = {
            "allowed": True,
            "totals": {"total": 0, "untracked": 0, "deleted": 0, "modified": 0},
            "domains": {"source": 0, "ops": 0, "docs": 0, "other": 0},
            "root_deleted": 0,
            "results_untracked": 0,
            "report_file": "logs/workspace_forensics/workspace_guard_latest.json",
            "history_file": "logs/workspace_forensics/workspace_guard_history.jsonl",
            "warnings": [],
            "violations": [],
        }
        mock_run.return_value = SimpleNamespace(returncode=0)

        state = cli.StateManager(workspace_path=str(temp_workspace))
        state.register_task(
            task_id="TASK-PENDING-001",
            ai_type="codex",
            description="pending task for report refresh",
            files=["tests/unit/test_cli.py"],
        )
        (temp_workspace / "logs").mkdir(parents=True, exist_ok=True)
        (temp_workspace / "logs" / "custom_receipt_report.json").write_text(
            json.dumps(
                {
                    "completed_count": 0,
                    "error_count": 1,
                    "candidate_count": 4,
                }
            ),
            encoding="utf-8",
        )

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=False,
            reclose=False,
            force_workspace=False,
            report="logs/custom_receipt_report.json",
            history=None,
            state=None,
            summary=None,
        )

        result = cli.cmd_receipt(args)
        assert result == 0
        mock_hygiene.assert_not_called()

        report_json = json.loads(
            (temp_workspace / "logs" / "daily_report.json").read_text(encoding="utf-8")
        )
        assert report_json["ack_stats"]["total_acks"] == 0
        assert report_json["ack_stats"]["failure_count"] == 1
        assert report_json["ack_stats"]["success_rate"] == 0.0
        assert report_json["result_consistency_stats"]["audited_count"] == 0
        assert report_json["result_consistency_stats"]["issue_count"] == 0
        assert report_json["pending_tasks"] == ["TASK-PENDING-001"]

        report_md = (
            temp_workspace / "collaboration" / "monitoring" / "DAILY_REPORT_latest.md"
        ).read_text(encoding="utf-8")
        noop_summary = (
            temp_workspace
            / "collaboration"
            / "monitoring"
            / "NOOP_PENDING_CONFLICT_SUMMARY_latest.md"
        ).read_text(encoding="utf-8")
        noop_report = json.loads(
            (temp_workspace / "logs" / "noop_pending_conflict_report.json").read_text(
                encoding="utf-8"
            )
        )

        assert "失败数: `1`" in report_md
        assert "终态结果一致性统计" in report_md
        assert "`TASK-PENDING-001`" in report_md
        assert "No-Op and Pending Conflict Summary" in noop_summary
        assert noop_report["workspace"] == str(temp_workspace)


class TestCmdRun:
    """测试 run 命令（dispatch -> receipt -> benefit）"""

    @patch("ai_collab.cli._cli_main.cmd_benefit")
    @patch("ai_collab.cli._cli_main.cmd_receipt")
    @patch("ai_collab.cli._cli_main.cmd_dispatch")
    def test_run_executes_three_stages(
        self, mock_dispatch, mock_receipt, mock_benefit, temp_workspace
    ):
        mock_dispatch.return_value = 0
        mock_receipt.return_value = 0
        mock_benefit.return_value = 0

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=True,
            include_pending=False,
            redispatch=False,
            reclose=False,
            force_workspace=False,
            dispatch_report=None,
            dispatch_history=None,
            dispatch_state=None,
            dispatch_orders=None,
            receipt_report=None,
            receipt_history=None,
            receipt_state=None,
            receipt_summary=None,
            benefit_dispatch_history=None,
            benefit_receipt_history=None,
            target_ratio=None,
            window=None,
            benefit_report=None,
            benefit_output=None,
        )
        assert cli.cmd_run(args) == 0
        mock_dispatch.assert_called_once()
        mock_receipt.assert_called_once()
        mock_benefit.assert_called_once()

    @patch("ai_collab.cli._cli_main.cmd_benefit")
    @patch("ai_collab.cli._cli_main.cmd_receipt")
    @patch("ai_collab.cli._cli_main.cmd_dispatch")
    def test_run_stops_when_dispatch_fails(
        self, mock_dispatch, mock_receipt, mock_benefit, temp_workspace
    ):
        mock_dispatch.return_value = 2
        mock_receipt.return_value = 0
        mock_benefit.return_value = 0

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=False,
            include_pending=False,
            redispatch=False,
            reclose=False,
            force_workspace=False,
            dispatch_report=None,
            dispatch_history=None,
            dispatch_state=None,
            dispatch_orders=None,
            receipt_report=None,
            receipt_history=None,
            receipt_state=None,
            receipt_summary=None,
            benefit_dispatch_history=None,
            benefit_receipt_history=None,
            target_ratio=None,
            window=None,
            benefit_report=None,
            benefit_output=None,
        )
        assert cli.cmd_run(args) == 2
        mock_receipt.assert_not_called()
        mock_benefit.assert_not_called()

    @patch("ai_collab.cli._cli_main._generate_reports_and_summaries")
    @patch("ai_collab.cli._cli_main.cmd_benefit")
    @patch("ai_collab.cli._cli_main.cmd_receipt")
    @patch("ai_collab.cli._cli_main.cmd_dispatch")
    def test_run_generate_reports_passes_receipt_report_override(
        self,
        mock_dispatch,
        mock_receipt,
        mock_benefit,
        mock_generate_reports,
        temp_workspace,
    ):
        mock_dispatch.return_value = 0
        mock_receipt.return_value = 0
        mock_benefit.return_value = 0

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=False,
            include_pending=False,
            redispatch=False,
            reclose=False,
            force_workspace=False,
            dispatch_report=None,
            dispatch_history=None,
            dispatch_state=None,
            dispatch_orders=None,
            receipt_report="logs/custom_receipt_report.json",
            receipt_history=None,
            receipt_state=None,
            receipt_summary=None,
            benefit_dispatch_history=None,
            benefit_receipt_history=None,
            target_ratio=None,
            window=None,
            benefit_report=None,
            benefit_output=None,
        )

        assert cli.cmd_run(args) == 0
        mock_generate_reports.assert_called_once_with(
            workspace=str(temp_workspace),
            receipt_report_path="logs/custom_receipt_report.json",
        )


class TestCmdSpawnAgentGuard:
    """测试 spawn-agent-guard 命令"""

    @patch("ai_collab.cli._cli_main.run_spawn_agent_guard")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_spawn_agent_guard_uses_config_defaults(
        self, mock_set_env, mock_vscode, mock_run, temp_workspace
    ):
        mock_vscode.get_project_config.return_value = {
            "spawnAgentGuard": {
                "enabled": True,
                "report": "logs/workspace_forensics/custom_spawn_guard.json",
                "history": "logs/workspace_forensics/custom_spawn_guard_history.jsonl",
            }
        }
        mock_run.return_value = {
            "allowed": True,
            "actor": "codex",
            "mode": "write",
            "parent_task_id": "TASK-001",
            "files": ["ai_collab/cli.py"],
            "warnings": [],
            "violations": [],
            "active_conflicts": [],
            "report_file": "logs/workspace_forensics/custom_spawn_guard.json",
            "history_file": "logs/workspace_forensics/custom_spawn_guard_history.jsonl",
        }

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            actor="codex",
            parent_task="TASK-001",
            files=["ai_collab/cli.py"],
            read_only=False,
            report=None,
            history=None,
        )

        result = cli.cmd_spawn_agent_guard(args)

        assert result == 0
        called = mock_run.call_args.kwargs
        assert called["actor"] == "codex"
        assert called["parent_task_id"] == "TASK-001"
        assert called["files"] == ["ai_collab/cli.py"]
        assert (
            called["config"]["spawnAgentGuard"]["report"]
            == "logs/workspace_forensics/custom_spawn_guard.json"
        )

    @patch("ai_collab.cli._cli_main.run_spawn_agent_guard")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_spawn_agent_guard_blocks_when_guard_denies(
        self, mock_set_env, mock_vscode, mock_run, temp_workspace
    ):
        mock_vscode.get_project_config.return_value = {"spawnAgentGuard": {"enabled": True}}
        mock_run.return_value = {
            "allowed": False,
            "actor": "codex",
            "mode": "write",
            "parent_task_id": "TASK-001",
            "files": ["ai_collab/cli.py"],
            "warnings": [],
            "violations": ["blocked"],
            "active_conflicts": [],
            "report_file": "logs/workspace_forensics/spawn_agent_guard_latest.json",
            "history_file": "logs/workspace_forensics/spawn_agent_guard_history.jsonl",
        }

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            actor="codex",
            parent_task="TASK-001",
            files=["ai_collab/cli.py"],
            read_only=False,
            report=None,
            history=None,
        )

        result = cli.cmd_spawn_agent_guard(args)

        assert result == 2


class TestCmdStage:
    """测试分域安全暂存命令"""

    @patch("ai_collab.cli._cli_main.stage_domain_changes")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_stage_source_runs_with_domain_source(self, mock_set_env, mock_stage, temp_workspace):
        mock_stage.return_value = {
            "ok": True,
            "mode": "dry-run",
            "candidate_count": 3,
            "status_counts": {"untracked": 2, "deleted": 1, "modified": 0},
            "sample_paths": ["ai_collab/a.py"],
            "report_file": "logs/workspace_forensics/stage_source_latest.json",
            "history_file": "logs/workspace_forensics/stage_source_history.jsonl",
        }
        args = SimpleNamespace(workspace=str(temp_workspace), dry_run=True)
        assert cli.cmd_stage_source(args) == 0
        mock_stage.assert_called_once()
        assert mock_stage.call_args.kwargs["domain"] == "source"
        assert mock_stage.call_args.kwargs["dry_run"] is True

    @patch("ai_collab.cli._cli_main.stage_domain_changes")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_stage_ops_runs_with_domain_ops(self, mock_set_env, mock_stage, temp_workspace):
        mock_stage.return_value = {
            "ok": True,
            "mode": "apply",
            "candidate_count": 2,
            "status_counts": {"untracked": 2, "deleted": 0, "modified": 0},
            "sample_paths": ["collaboration/results/RESULT_X.md"],
            "report_file": "logs/workspace_forensics/stage_ops_latest.json",
            "history_file": "logs/workspace_forensics/stage_ops_history.jsonl",
        }
        args = SimpleNamespace(workspace=str(temp_workspace), dry_run=False)
        assert cli.cmd_stage_ops(args) == 0
        assert mock_stage.call_args.kwargs["domain"] == "ops"

    @patch("ai_collab.cli._cli_main.stage_domain_changes")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_stage_docs_returns_error_when_stage_fails(
        self, mock_set_env, mock_stage, temp_workspace
    ):
        mock_stage.return_value = {"ok": False, "error": "git add failed"}
        args = SimpleNamespace(workspace=str(temp_workspace), dry_run=False)
        assert cli.cmd_stage_docs(args) == 1

    @patch("ai_collab.cli._cli_main.stage_domain_changes")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_stage_other_runs_with_domain_other(self, mock_set_env, mock_stage, temp_workspace):
        mock_stage.return_value = {
            "ok": True,
            "mode": "apply",
            "candidate_count": 5,
            "status_counts": {"untracked": 1, "deleted": 0, "modified": 4},
            "sample_paths": [".vscode/tasks.json"],
            "report_file": "logs/workspace_forensics/stage_other_latest.json",
            "history_file": "logs/workspace_forensics/stage_other_history.jsonl",
        }
        args = SimpleNamespace(workspace=str(temp_workspace), dry_run=False)
        assert cli.cmd_stage_other(args) == 0
        assert mock_stage.call_args.kwargs["domain"] == "other"

    @patch("ai_collab.cli._cli_main.stage_domain_changes")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_stage_safe_runs_preview_then_apply(self, mock_set_env, mock_stage, temp_workspace):
        mock_stage.side_effect = [
            {
                "ok": True,
                "mode": "dry-run",
                "candidate_count": 2,
                "status_counts": {"untracked": 1, "deleted": 0, "modified": 1},
                "sample_paths": ["collaboration/monitoring/a.md"],
                "report_file": "logs/workspace_forensics/stage_ops_latest.json",
                "history_file": "logs/workspace_forensics/stage_ops_history.jsonl",
            },
            {
                "ok": True,
                "mode": "dry-run",
                "candidate_count": 0,
                "status_counts": {"untracked": 0, "deleted": 0, "modified": 0},
                "sample_paths": [],
                "report_file": "logs/workspace_forensics/stage_docs_latest.json",
                "history_file": "logs/workspace_forensics/stage_docs_history.jsonl",
            },
            {
                "ok": True,
                "mode": "dry-run",
                "candidate_count": 1,
                "status_counts": {"untracked": 1, "deleted": 0, "modified": 0},
                "sample_paths": [".vscode/tasks.json"],
                "report_file": "logs/workspace_forensics/stage_other_latest.json",
                "history_file": "logs/workspace_forensics/stage_other_history.jsonl",
            },
            {
                "ok": True,
                "mode": "apply",
                "candidate_count": 2,
                "status_counts": {"untracked": 1, "deleted": 0, "modified": 1},
                "sample_paths": ["collaboration/monitoring/a.md"],
                "report_file": "logs/workspace_forensics/stage_ops_latest.json",
                "history_file": "logs/workspace_forensics/stage_ops_history.jsonl",
            },
            {
                "ok": True,
                "mode": "apply",
                "candidate_count": 1,
                "status_counts": {"untracked": 1, "deleted": 0, "modified": 0},
                "sample_paths": [".vscode/tasks.json"],
                "report_file": "logs/workspace_forensics/stage_other_latest.json",
                "history_file": "logs/workspace_forensics/stage_other_history.jsonl",
            },
        ]
        args = SimpleNamespace(workspace=str(temp_workspace), dry_run=False, include_source=False)
        assert cli.cmd_stage_safe(args) == 0
        calls = [(c.kwargs["domain"], c.kwargs["dry_run"]) for c in mock_stage.call_args_list]
        assert calls == [
            ("ops", True),
            ("docs", True),
            ("other", True),
            ("ops", False),
            ("other", False),
        ]

    @patch("ai_collab.cli._cli_main.stage_domain_changes")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_stage_safe_dry_run_only_previews(self, mock_set_env, mock_stage, temp_workspace):
        mock_stage.side_effect = [
            {
                "ok": True,
                "mode": "dry-run",
                "candidate_count": 0,
                "status_counts": {"untracked": 0, "deleted": 0, "modified": 0},
                "sample_paths": [],
                "report_file": "logs/workspace_forensics/stage_ops_latest.json",
                "history_file": "logs/workspace_forensics/stage_ops_history.jsonl",
            },
            {
                "ok": True,
                "mode": "dry-run",
                "candidate_count": 0,
                "status_counts": {"untracked": 0, "deleted": 0, "modified": 0},
                "sample_paths": [],
                "report_file": "logs/workspace_forensics/stage_docs_latest.json",
                "history_file": "logs/workspace_forensics/stage_docs_history.jsonl",
            },
            {
                "ok": True,
                "mode": "dry-run",
                "candidate_count": 0,
                "status_counts": {"untracked": 0, "deleted": 0, "modified": 0},
                "sample_paths": [],
                "report_file": "logs/workspace_forensics/stage_other_latest.json",
                "history_file": "logs/workspace_forensics/stage_other_history.jsonl",
            },
        ]
        args = SimpleNamespace(workspace=str(temp_workspace), dry_run=True, include_source=False)
        assert cli.cmd_stage_safe(args) == 0
        calls = [(c.kwargs["domain"], c.kwargs["dry_run"]) for c in mock_stage.call_args_list]
        assert calls == [("ops", True), ("docs", True), ("other", True)]


class TestCmdBenefit:
    """测试 benefit 命令"""

    @patch("ai_collab.cli.subprocess.run")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_benefit_uses_config_defaults(
        self, mock_set_env, mock_vscode, mock_run, temp_workspace
    ):
        """测试 benefit 使用项目配置默认值"""
        mock_vscode.get_project_config.return_value = {
            "benefit": {
                "dispatchHistory": ["logs/custom_dispatch_history.jsonl"],
                "receiptHistory": ["logs/custom_receipt_history.jsonl"],
                "targetRatio": 4.5,
                "window": 30,
                "report": "logs/custom_benefit_report.json",
                "output": "collaboration/monitoring/CUSTOM_BENEFIT_DASHBOARD.md",
            }
        }
        mock_run.return_value = SimpleNamespace(returncode=0)

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=True,
            dispatch_history=None,
            receipt_history=None,
            target_ratio=None,
            window=None,
            report=None,
            output=None,
        )

        result = cli.cmd_benefit(args)
        assert result == 0

        cmd = mock_run.call_args[0][0]
        assert "--dry-run" in cmd
        assert "--dispatch-history" in cmd and "logs/custom_dispatch_history.jsonl" in cmd
        assert "--receipt-history" in cmd and "logs/custom_receipt_history.jsonl" in cmd
        assert "--target-ratio" in cmd and "4.5" in cmd
        assert "--window" in cmd and "30" in cmd
        assert "--report" in cmd and "logs/custom_benefit_report.json" in cmd
        assert "--output" in cmd and "collaboration/monitoring/CUSTOM_BENEFIT_DASHBOARD.md" in cmd

    @patch("ai_collab.cli.subprocess.run")
    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_benefit_cli_args_override_config(
        self, mock_set_env, mock_vscode, mock_run, temp_workspace
    ):
        """测试 benefit 参数覆盖配置值"""
        mock_vscode.get_project_config.return_value = {
            "benefit": {
                "dispatchHistory": ["logs/custom_dispatch_history.jsonl"],
                "receiptHistory": ["logs/custom_receipt_history.jsonl"],
                "targetRatio": 4.5,
                "window": 30,
                "report": "logs/custom_benefit_report.json",
                "output": "collaboration/monitoring/CUSTOM_BENEFIT_DASHBOARD.md",
            }
        }
        mock_run.return_value = SimpleNamespace(returncode=5)

        args = SimpleNamespace(
            workspace=str(temp_workspace),
            dry_run=False,
            dispatch_history=["logs/override_dispatch_1.jsonl", "logs/override_dispatch_2.jsonl"],
            receipt_history=["logs/override_receipt.jsonl"],
            target_ratio=6.0,
            window=7,
            report="logs/override_benefit_report.json",
            output="collaboration/monitoring/OVERRIDE_BENEFIT_DASHBOARD.md",
        )

        result = cli.cmd_benefit(args)
        assert result == 5

        cmd = mock_run.call_args[0][0]
        assert "--dry-run" not in cmd
        assert cmd.count("--dispatch-history") == 2
        assert cmd.count("--receipt-history") == 1
        assert "--target-ratio" in cmd and "6.0" in cmd
        assert "--window" in cmd and "7" in cmd
        assert "--report" in cmd and "logs/override_benefit_report.json" in cmd
        assert "--output" in cmd and "collaboration/monitoring/OVERRIDE_BENEFIT_DASHBOARD.md" in cmd


# ==================== cmd_status 测试 ====================


class TestCmdStatus:
    """测试 status 命令"""

    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_status_display(
        self, mock_set_env, mock_manager_cls, mock_vscode, temp_workspace, capsys
    ):
        """测试显示系统状态"""
        # 准备
        mock_manager = Mock()
        mock_manager.get_all_tasks.return_value = [
            {"task_id": "TASK-001", "status": "completed", "ai_type": "claude_code"},
            {"task_id": "TASK-002", "status": "in_progress", "ai_type": "copilot"},
        ]
        mock_manager.get_active_tasks.return_value = [
            {"task_id": "TASK-002", "status": "in_progress", "ai_type": "copilot"}
        ]
        mock_manager.get_conflicts.return_value = []
        mock_manager_cls.return_value = mock_manager

        mock_vscode.get_workspace_path.return_value = str(temp_workspace)
        mock_vscode.get_project_config.return_value = {
            "version": "1.0.0",
            "rulesDir": "./rules",
            "logsDir": "./logs",
            "activationKeyword": "2X",
            "enabledAIs": ["claude_code", "copilot"],
            "agentOrchestration": {"autoDetectAgents": True, "operatorFirst": False},
        }
        (temp_workspace / "logs").mkdir(parents=True, exist_ok=True)
        (temp_workspace / "logs" / "agent_ack_bridge_state.json").write_text(
            json.dumps(
                {
                    "version": "1.0.0",
                    "items": {
                        "TASK-001": {
                            "task_id": "TASK-001",
                            "assignee": "claude_code",
                            "result_file": "collaboration/results/RESULT_TASK-001.md",
                            "ack_line": "C.ACK|task=TASK-001|status=ok|result=collaboration/results/RESULT_TASK-001.md",
                            "receipt_completed_at": "2026-03-26T10:00:00+08:00",
                            "bridged_at": "2026-03-26T10:00:05+08:00",
                            "bridge_count": 1,
                            "source": "cli-ack",
                        },
                        "TASK-002": {
                            "task_id": "TASK-002",
                            "assignee": "claude_code",
                            "result_file": "collaboration/results/RESULT_TASK-002.md",
                            "ack_line": "C.ACK|task=TASK-002|status=ok|result=collaboration/results/RESULT_TASK-002.md",
                            "receipt_completed_at": "2026-03-26T10:05:00+08:00",
                            "bridged_at": "2026-03-26T10:05:05+08:00",
                            "bridge_count": 1,
                            "source": "missing_ack_monitor:completed_state_fallback",
                        },
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (temp_workspace / "logs" / "missing_ack_report.json").write_text(
            json.dumps(
                {
                    "generated_at": "2026-03-26T10:10:00+08:00",
                    "stale_explicit_ack_count": 1,
                    "error_count": 0,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (temp_workspace / "logs" / "task_result_consistency_report.json").write_text(
            json.dumps(
                {
                    "generated_at": "2026-03-26T10:11:00+08:00",
                    "audited_count": 7,
                    "issue_count": 0,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (temp_workspace / "logs" / "daily_report.json").write_text(
            json.dumps(
                {
                    "generated_at": "2026-03-26T10:12:00+08:00",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        args = SimpleNamespace(workspace=str(temp_workspace), verbose=False)

        # 执行
        result = cli.cmd_status(args)

        # 验证
        assert result == 0
        captured = capsys.readouterr()
        assert "[治理健康]" in captured.out
        assert "Codex: 1" in captured.out
        assert "legacy copilot: 1" in captured.out
        assert "ACK bridge 记录: 2" in captured.out
        assert "显式 ACK 证据: 1" in captured.out
        assert "可闭环 ACK: 1" in captured.out
        assert "Claude fallback 残留: 1" in captured.out
        assert "显式 ACK 残留任务: 1" in captured.out
        assert "终态结果一致性: issues=0 / audited=7" in captured.out
        assert "日报时间: 2026-03-26T10:12:00+08:00" in captured.out
        assert "[报告健康]" in captured.out
        assert "missing-ack: stale" in captured.out
        assert "result-consistency: stale" in captured.out
        assert "daily-report: stale" in captured.out

    @patch("ai_collab.cli._cli_main.VSCodeIntegration")
    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_status_display_handles_missing_report_files(
        self, mock_set_env, mock_manager_cls, mock_vscode, temp_workspace, capsys
    ):
        """测试 status 在治理报告尚未生成时仍能稳定输出。"""
        mock_manager = Mock()
        mock_manager.get_all_tasks.return_value = []
        mock_manager.get_active_tasks.return_value = []
        mock_manager.get_conflicts.return_value = []
        mock_manager_cls.return_value = mock_manager

        mock_vscode.get_workspace_path.return_value = str(temp_workspace)
        mock_vscode.get_project_config.return_value = {
            "version": "1.0.0",
            "rulesDir": "./rules",
            "logsDir": "./logs",
            "activationKeyword": "2X",
            "enabledAIs": ["claude_code", "codex", "codearts_agent"],
            "agentOrchestration": {},
        }
        (temp_workspace / "logs").mkdir(parents=True, exist_ok=True)
        (temp_workspace / "logs" / "agent_ack_bridge_state.json").write_text(
            json.dumps({"version": "1.0.0", "items": {}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        args = SimpleNamespace(workspace=str(temp_workspace), verbose=False)

        result = cli.cmd_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "显式 ACK 残留任务: 未生成 missing_ack_report" in captured.out
        assert "终态结果一致性: 未生成 task_result_consistency_report" in captured.out
        assert "日报时间: 未生成 daily_report" in captured.out
        assert "missing-ack: missing" in captured.out
        assert "result-consistency: missing" in captured.out
        assert "daily-report: missing" in captured.out


# ==================== cmd_clean 测试 ====================


class TestCmdClean:
    """测试 clean 命令"""

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_clean_logs_and_tasks(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试清理日志和任务"""
        # 准备
        mock_manager = Mock()
        mock_manager.clear_completed_tasks.return_value = {"cleared": 10, "remaining": 5}
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(max_files=20, days=7, workspace=str(temp_workspace))

        # 执行
        result = cli.cmd_clean(args)

        # 验证
        assert result == 0
        mock_manager.clear_completed_tasks.assert_called_once_with(7)


# ==================== _set_workspace_env 测试 ====================


class TestSetWorkspaceEnv:
    """测试 _set_workspace_env 函数"""

    def test_set_workspace_env_with_path(self, temp_workspace):
        """测试设置工作区环境变量"""
        # 执行
        cli._set_workspace_env(str(temp_workspace))

        # 验证
        assert os.environ.get("VSCODE_CWD") == str(temp_workspace)

    def test_set_workspace_env_with_none(self):
        """测试传入 None 时不设置环境变量"""
        # 准备
        original_value = os.environ.get("VSCODE_CWD")

        # 执行
        cli._set_workspace_env(None)

        # 验证
        assert os.environ.get("VSCODE_CWD") == original_value


# ==================== _load_steps_from_file 测试 ====================


class TestLoadStepsFromFile:
    """测试 _load_steps_from_file 函数"""

    def test_load_steps_from_file(self, temp_workspace):
        """测试从文件加载步骤"""
        # 准备
        steps_file = temp_workspace / "steps.txt"
        steps_file.write_text("步骤1\n步骤2\n# 这是注释\n步骤3\n")

        # 执行
        steps = cli._load_steps_from_file(str(steps_file))

        # 验证
        assert steps == ["步骤1", "步骤2", "步骤3"]

    def test_load_steps_from_empty_file(self, temp_workspace):
        """测试从空文件加载步骤"""
        # 准备
        steps_file = temp_workspace / "empty.txt"
        steps_file.write_text("")

        # 执行
        steps = cli._load_steps_from_file(str(steps_file))

        # 验证
        assert steps == []


# ==================== _emit_plan_tasks 测试 ====================


class TestEmitPlanTasks:
    """测试 _emit_plan_tasks 函数"""

    def test_emit_plan_tasks(self, temp_workspace):
        """测试生成计划任务"""
        # 准备
        mock_manager = Mock()
        mock_manager.register_task.return_value = {"task_id": "TASK-001"}

        plan = {
            "utilization_plan": [
                {"agent": "claude_code", "role": "lead", "task": "主导任务"},
                {"agent": "copilot", "role": "support", "task": "支持任务"},
                {"agent": "user", "role": "operator", "task": "用户任务"},
            ]
        }

        # 执行
        created = cli._emit_plan_tasks(
            mock_manager, plan, related_files=["test.py"], task_prefix="TEST"
        )

        # 验证
        assert len(created) == 2  # user 任务被跳过
        assert mock_manager.register_task.call_count == 2
        first_call_kwargs = mock_manager.register_task.call_args_list[0].kwargs
        assert first_call_kwargs["change_id"] == "bugfix/no-spec"
        assert first_call_kwargs["reviewer"] == "codex"
        assert first_call_kwargs["primary_skill"] in {
            "duoai-coordinator",
            "backend-architect",
            "planning-with-files",
            "api-test-pro",
        }
        assert first_call_kwargs["support_skills"] == [
            "planning-with-files",
            "systematic-debugging",
        ]
        assert first_call_kwargs["acceptance_commands"] == [
            "python3 -m ai_collab.cli status -v",
            "python3 -m ai_collab.cli tasks validate-contract --scope active --strict",
        ]
        assert first_call_kwargs["result_file"].startswith("collaboration/results/RESULT_")


class TestEmitPlanPatches:
    """测试 _emit_plan_patches 函数"""

    def test_emit_plan_patches(self, temp_workspace):
        mock_manager = Mock()
        mock_manager.register_patch.return_value = {"patch_id": "PATCH-001"}

        plan = {
            "utilization_plan": [
                {"agent": "codex", "role": "lead", "task": "实现主逻辑"},
                {"agent": "claude_code", "role": "support", "task": "风险审查"},
                {"agent": "user", "role": "operator", "task": "确认验收"},
            ]
        }

        created = cli._emit_plan_patches(
            mock_manager,
            plan,
            task_id="TASK-001",
            related_files=["test.py"],
            patch_prefix="PATCH-TEST",
        )

        assert len(created) == 2
        assert mock_manager.register_patch.call_count == 2


# ==================== main 函数测试 ====================


class TestMain:
    """测试 main 函数"""

    @patch("sys.argv", ["ai-collab"])
    def test_main_no_command(self):
        """测试无命令时显示帮助"""
        result = cli.main()
        assert result == 0

    @patch("sys.argv", ["ai-collab", "status"])
    @patch("ai_collab.cli._cli_main.cmd_status")
    def test_main_status_command(self, mock_cmd):
        """测试 status 命令路由"""
        mock_cmd.return_value = 0
        cli.main()
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "init"])
    @patch("ai_collab.cli._cli_main.cmd_init")
    def test_main_init_command(self, mock_cmd):
        """测试 init 命令路由"""
        mock_cmd.return_value = 0
        cli.main()
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "init", "--workspace", "/tmp/ws"])
    @patch("ai_collab.cli._cli_main.cmd_init")
    def test_main_init_command_accepts_workspace_after_subcommand(self, mock_cmd):
        """测试 init 支持将 --workspace 放在子命令后（兼容写法）"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()
        parsed_args = mock_cmd.call_args.args[0]
        assert parsed_args.workspace == "/tmp/ws"

    @patch("sys.argv", ["ai-collab", "controller", "--once"])
    @patch("ai_collab.cli._cli_main.cmd_controller")
    def test_main_controller_command(self, mock_cmd):
        """测试 controller 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "dispatch", "--dry-run"])
    @patch("ai_collab.cli._cli_main.cmd_dispatch")
    def test_main_dispatch_command(self, mock_cmd):
        """测试 dispatch 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "trigger", "--phrase", "2X DISPATCH"])
    @patch("ai_collab.cli._cli_main.cmd_trigger")
    def test_main_trigger_command(self, mock_cmd):
        """测试 trigger 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "2x", "claude"])
    @patch("ai_collab.cli._cli_main.cmd_2x")
    def test_main_2x_command(self, mock_cmd):
        """测试 2x 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "receipt", "--dry-run"])
    @patch("ai_collab.cli._cli_main.cmd_receipt")
    def test_main_receipt_command(self, mock_cmd):
        """测试 receipt 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "benefit", "--dry-run"])
    @patch("ai_collab.cli._cli_main.cmd_benefit")
    def test_main_benefit_command(self, mock_cmd):
        """测试 benefit 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "run", "--dry-run"])
    @patch("ai_collab.cli._cli_main.cmd_run")
    def test_main_run_command(self, mock_cmd):
        """测试 run 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "workspace-guard", "--dry-run"])
    @patch("ai_collab.cli._cli_main.cmd_workspace_guard")
    def test_main_workspace_guard_command(self, mock_cmd):
        """测试 workspace-guard 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch(
        "sys.argv",
        [
            "ai-collab",
            "spawn-agent-guard",
            "--actor",
            "codex",
            "--parent-task",
            "TASK-001",
            "--read-only",
        ],
    )
    @patch("ai_collab.cli._cli_main.cmd_spawn_agent_guard")
    def test_main_spawn_agent_guard_command(self, mock_cmd):
        """测试 spawn-agent-guard 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "codex", "hooks", "--action", "status"])
    @patch("ai_collab.cli._cli_main.cmd_codex")
    def test_main_codex_hooks_action_alias(self, mock_cmd):
        """测试 codex hooks 支持 --action 兼容别名"""
        mock_cmd.return_value = 0

        result = cli.main()

        assert result == 0
        mock_cmd.assert_called_once()
        parsed_args = mock_cmd.call_args.args[0]
        assert parsed_args.subcommand == "hooks"
        assert parsed_args.hook_action == "status"

    @patch("sys.argv", ["ai-collab", "stage-source", "--dry-run"])
    @patch("ai_collab.cli._cli_main.cmd_stage_source")
    def test_main_stage_source_command(self, mock_cmd):
        """测试 stage-source 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "stage-ops", "--dry-run"])
    @patch("ai_collab.cli._cli_main.cmd_stage_ops")
    def test_main_stage_ops_command(self, mock_cmd):
        """测试 stage-ops 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "stage-docs", "--dry-run"])
    @patch("ai_collab.cli._cli_main.cmd_stage_docs")
    def test_main_stage_docs_command(self, mock_cmd):
        """测试 stage-docs 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "stage-other", "--dry-run"])
    @patch("ai_collab.cli._cli_main.cmd_stage_other")
    def test_main_stage_other_command(self, mock_cmd):
        """测试 stage-other 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "stage-safe", "--dry-run"])
    @patch("ai_collab.cli._cli_main.cmd_stage_safe")
    def test_main_stage_safe_command(self, mock_cmd):
        """测试 stage-safe 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()

    @patch("sys.argv", ["ai-collab", "hygiene", "--dry-run"])
    @patch("ai_collab.cli._cli_main.cmd_hygiene")
    def test_main_hygiene_command(self, mock_cmd):
        """测试 hygiene 命令路由"""
        mock_cmd.return_value = 0
        result = cli.main()
        assert result == 0
        mock_cmd.assert_called_once()


# ==================== 集成测试 ====================


class TestCLIIntegration:
    """CLI 集成测试"""

    @patch("ai_collab.cli._cli_main.ActivationHandler")
    @patch("ai_collab.cli._cli_main.StateManager")
    def test_full_workflow(self, mock_manager_cls, mock_handler_cls, temp_workspace):
        """测试完整工作流：激活 -> 检查 -> 任务"""
        # 1. 初始化
        init_args = SimpleNamespace(workspace=str(temp_workspace))
        assert cli.cmd_init(init_args) == 0

        # 2. 激活
        mock_handler = Mock()
        mock_handler.check_activation.return_value = True
        mock_handler.activate.return_value = {
            "ai_type": "claude_code",
            "session_id": "test-session",
            "activation_time": "2026-02-28T12:00:00",
            "mode": "cli",
            "rules_loaded": [],
            "ack_message": "激活成功",
        }
        mock_handler_cls.return_value = mock_handler

        activate_args = SimpleNamespace(
            ai="claude", mode="cli", workspace=str(temp_workspace), input=None, show_rules=False
        )
        assert cli.cmd_activate(activate_args) == 0

        # 3. 检查冲突
        mock_manager = Mock()
        mock_manager.check_conflicts.return_value = []
        mock_manager_cls.return_value = mock_manager

        check_args = SimpleNamespace(
            ai="claude",
            files=["test.py"],
            mode="both",
            resolve=False,
            workspace=str(temp_workspace),
        )
        assert cli.cmd_check(check_args) == 0

        # 4. 注册任务
        mock_manager.register_task.return_value = {
            "task_id": "TASK-001",
            "ai_type": "claude_code",
            "description": "测试任务",
        }

        task_args = SimpleNamespace(
            subcommand="register",
            task_id="TASK-001",
            ai="claude_code",
            description="测试任务",
            files=["test.py"],
            workspace=str(temp_workspace),
        )
        assert cli.cmd_tasks(task_args) == 0


# ==================== 边界情况测试 ====================


class TestEdgeCases:
    """测试边界情况"""

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_check_no_files_specified(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试检查时未指定文件"""
        # 准备
        mock_manager = Mock()
        mock_manager.check_conflicts.return_value = []
        mock_manager_cls.return_value = mock_manager

        # 创建一些测试文件
        (temp_workspace / "test.py").write_text("# test")
        (temp_workspace / "test.js").write_text("// test")

        args = SimpleNamespace(
            ai="claude", files=[], mode="both", resolve=False, workspace=str(temp_workspace)
        )

        # 执行
        result = cli.cmd_check(args)

        # 验证
        assert result == 0

    @patch("ai_collab.cli._cli_main.StateManager")
    @patch("ai_collab.cli._cli_main._set_workspace_env")
    def test_tasks_list_empty(self, mock_set_env, mock_manager_cls, temp_workspace):
        """测试列出空任务列表"""
        # 准备
        mock_manager = Mock()
        mock_manager.get_all_tasks.return_value = []
        mock_manager_cls.return_value = mock_manager

        args = SimpleNamespace(subcommand="list", status="all", workspace=str(temp_workspace))

        # 执行
        result = cli.cmd_tasks(args)

        # 验证
        assert result == 0

    def test_activate_with_different_modes(self, temp_workspace):
        """测试不同激活模式"""
        modes = ["cli", "command", "event", "on_save"]

        for mode in modes:
            args = SimpleNamespace(
                ai="claude", mode=mode, workspace=str(temp_workspace), input=None, show_rules=False
            )

            # 不应该抛出异常
            try:
                cli.cmd_activate(args)
            except Exception as e:
                pytest.fail(f"Mode {mode} raised exception: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
