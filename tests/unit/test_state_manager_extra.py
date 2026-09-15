
"""
state_manager.py 补测 - 重点覆盖 VSCode 路径解析与边界
目标: 79% -> 85%+ (217 行未覆盖)
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from ai_collab.state_manager import (
    FileStatus,
    PatchStatus,
    TaskStatus,
    VSCodeIntegration,
    VSCodeStateManager,
)


# ============================================================
# VSCodeStateManager 静态方法 - get_project_state_file
# ============================================================

def test_state_file_uses_workspace_when_available(tmp_path):
    """workspace 存在 -> 用 workspace 拼接 stateFile"""
    with patch.object(VSCodeIntegration, "get_workspace_path", return_value=str(tmp_path)), \
         patch.object(VSCodeIntegration, "get_project_config", return_value={"stateFile": "logs/state.json"}):
        out = VSCodeStateManager.get_project_state_file()
    assert out.endswith("logs/state.json")
    assert str(tmp_path) in out
    assert (tmp_path / "logs").exists()


def test_state_file_uses_cwd_when_workspace_none(tmp_path):
    """workspace=None 但 cwd 有效 -> 用 cwd"""
    with patch.object(VSCodeIntegration, "get_workspace_path", return_value=None), \
         patch.object(VSCodeIntegration, "get_project_config", return_value={"stateFile": "x.json"}), \
         patch.object(VSCodeIntegration, "_is_valid_workspace", return_value=True), \
         patch("os.getcwd", return_value=str(tmp_path)):
        out = VSCodeStateManager.get_project_state_file()
    assert str(tmp_path) in out


def test_state_file_falls_back_to_global_dir():
    """workspace=None 且 cwd 无效 -> 用 ~/.vscode/ai-collab/"""
    home = tempfile.mkdtemp()
    with patch.object(VSCodeIntegration, "get_workspace_path", return_value=None), \
         patch.object(VSCodeIntegration, "get_project_config", return_value={"stateFile": "x.json"}), \
         patch.object(VSCodeIntegration, "_is_valid_workspace", return_value=False), \
         patch("os.getcwd", return_value="/"), \
         patch("os.path.expanduser", return_value=home):
        out = VSCodeStateManager.get_project_state_file()
    assert "ai-collab" in out
    assert "collaboration_state.json" in out


# ============================================================
# VSCodeStateManager.get_issues_file
# ============================================================

def test_issues_file_uses_workspace(tmp_path):
    with patch.object(VSCodeIntegration, "get_workspace_path", return_value=str(tmp_path)):
        out = VSCodeStateManager.get_issues_file()
    assert out.endswith("collaboration_issues.json")
    assert str(tmp_path) in out


def test_issues_file_fallback_global_dir():
    """workspace=None + cwd 无效 -> 全局目录"""
    with patch.object(VSCodeIntegration, "get_workspace_path", return_value=None), \
         patch.object(VSCodeIntegration, "_is_valid_workspace", return_value=False), \
         patch("os.getcwd", return_value="/"), \
         patch("os.path.expanduser", return_value=tempfile.mkdtemp()):
        out = VSCodeStateManager.get_issues_file()
    assert "collaboration_issues.json" in out


# ============================================================
# VSCodeStateManager.get_backup_dir
# ============================================================

def test_backup_dir_uses_workspace(tmp_path):
    """backup 目录: workspace + logs/backups (自动创建)"""
    with patch.object(VSCodeIntegration, "get_workspace_path", return_value=str(tmp_path)):
        out = VSCodeStateManager.get_backup_dir()
    assert out.endswith("backups")
    assert str(tmp_path) in out
    assert os.path.exists(out)


def test_backup_dir_uses_cwd_when_workspace_none(tmp_path):
    """workspace=None + cwd 有效 -> 用 cwd + logs/backups"""
    with patch.object(VSCodeIntegration, "get_workspace_path", return_value=None), \
         patch.object(VSCodeIntegration, "_is_valid_workspace", return_value=True), \
         patch("os.getcwd", return_value=str(tmp_path)):
        out = VSCodeStateManager.get_backup_dir()
    assert out.endswith("backups")


def test_backup_dir_fallback_to_global(tmp_path):
    """workspace=None + cwd 无效 -> 全局目录 ~/.vscode/ai-collab/backups

    直接设环境变量 HOME (Unix) / USERPROFILE (Windows) 让 expanduser 自然走 tmp_path
    """
    import os as _os
    fake_home = str(tmp_path / "fakehome")
    Path(fake_home).mkdir(parents=True, exist_ok=True)
    _os.environ["HOME"] = fake_home
    _os.environ.pop("USERPROFILE", None)
    try:
        with patch.object(VSCodeIntegration, "get_workspace_path", return_value=None), \
             patch.object(VSCodeIntegration, "_is_valid_workspace", return_value=False), \
             patch("os.getcwd", return_value="/"):
            out = VSCodeStateManager.get_backup_dir()
        assert "backups" in out
        assert _os.path.exists(out)
        assert out.startswith(fake_home)
    finally:
        # 清理
        _os.environ.pop("HOME", None)


# ============================================================
# Enum 值校验
# ============================================================

def test_task_status_enum_values():
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.PLANNING.value == "planning"
    assert TaskStatus.IMPLEMENTING.value == "implementing"
    assert TaskStatus.TESTING.value == "testing"
    assert TaskStatus.BLOCKED.value == "blocked"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"
    assert TaskStatus.CANCELLED.value == "cancelled"


def test_patch_status_enum_values():
    assert PatchStatus.PENDING.value == "pending"
    assert PatchStatus.IN_PROGRESS.value == "in_progress"
    assert PatchStatus.COMPLETED.value == "completed"
    assert PatchStatus.BLOCKED.value == "blocked"
    assert PatchStatus.CANCELLED.value == "cancelled"


def test_file_status_enum_values():
    assert FileStatus.CLEAN.value == "clean"
    assert FileStatus.MODIFIED.value == "modified"
    assert FileStatus.CONFLICT.value == "conflict"
    assert FileStatus.LOCKED.value == "locked"


def test_enums_are_string_subclass():
    """Enum 同时继承 str -> 可以直接当字符串用"""
    assert isinstance(TaskStatus.PENDING, str)
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.PENDING + "_suffix" == "pending_suffix"
