"""
ai_collab/workspace_guard.py 补测
目标: 77% -> 88%+
覆盖: _normalize_path / _decode_git_quoted_path / _status_type /
      _classify_domain / _read_status_entries 错误路径 /
      inspect_workspace 边界 / stage_domain_changes 边界
"""

import subprocess
from unittest.mock import patch

from ai_collab import workspace_guard as wg

# ============================================================
# _normalize_path
# ============================================================

def test_normalize_path_handles_arrow_rename():
    """git porcelain 改名格式: 'old -> new' -> 取后半部分"""
    assert wg._normalize_path("old_name -> new_name") == "new_name"


def test_normalize_path_strips_quotes():
    assert wg._normalize_path('"path/with spaces.md"') == "path/with spaces.md"


def test_normalize_path_plain():
    assert wg._normalize_path("plain/path.py") == "plain/path.py"


def test_normalize_path_none_safe():
    assert wg._normalize_path("") == ""


# ============================================================
# _decode_git_quoted_path
# ============================================================

def test_decode_git_quoted_octal_escapes():
    """git 把非 ASCII 路径用八进制转义, latin1->utf-8 反转"""
    raw = '"\\346\\255\\242.txt"'
    out = wg._decode_git_quoted_path(raw)
    assert isinstance(out, str)
    assert out.endswith(".txt")
    assert any(ord(ch) > 127 for ch in out)


def test_decode_git_quoted_unquoted_returns_stripped():
    assert wg._decode_git_quoted_path("plain.txt") == "plain.txt"


def test_decode_git_quoted_invalid_inner_returns_safely():
    raw = '"\\999\\888"'
    out = wg._decode_git_quoted_path(raw)
    assert isinstance(out, str)


# ============================================================
# _status_type
# ============================================================

def test_status_type_untracked():
    assert wg._status_type("??") == "untracked"


def test_status_type_deleted():
    assert wg._status_type(" D") == "deleted"


def test_status_type_modified():
    assert wg._status_type(" M") == "modified"


def test_status_type_added():
    assert wg._status_type("A ") == "added"


def test_status_type_renamed():
    assert wg._status_type("R ") == "renamed"


def test_status_type_other_default():
    assert wg._status_type("XX") == "other"


# ============================================================
# _classify_domain
# ============================================================

def test_classify_domain_source():
    assert wg._classify_domain("ai_collab/foo.py") == "source"
    assert wg._classify_domain("tests/unit/test_x.py") == "source"


def test_classify_domain_ops():
    assert wg._classify_domain("collaboration/results/R1.md") == "ops"
    assert wg._classify_domain("logs/foo.log") == "ops"


def test_classify_domain_docs():
    assert wg._classify_domain("docs/architecture.md") == "docs"


def test_classify_domain_root_md_is_docs():
    """根目录 .md 文件算 docs"""
    assert wg._classify_domain("README.md") == "docs"


def test_classify_domain_other():
    assert wg._classify_domain("random.xyz") == "other"


# ============================================================
# _read_status_entries
# ============================================================

def test_read_status_entries_returns_error_when_git_fails(tmp_path):
    fake = subprocess.CompletedProcess(
        args=[], returncode=128, stdout="", stderr="not a git repo"
    )
    with patch.object(wg.subprocess, "run", return_value=fake):
        out = wg._read_status_entries(tmp_path)
    assert out["ok"] is False
    assert "not a git repo" in out["error"]
    assert out["returncode"] == 128


def test_read_status_entries_parses_normal_output(tmp_path):
    fake = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=" M ai_collab/foo.py\n?? new_file.md\n",
        stderr="",
    )
    with patch.object(wg.subprocess, "run", return_value=fake):
        out = wg._read_status_entries(tmp_path)
    assert out["ok"] is True
    assert len(out["entries"]) == 2
    e0 = out["entries"][0]
    assert e0["status"] == "modified"
    assert e0["path"] == "ai_collab/foo.py"
    assert e0["domain"] == "source"
    e1 = out["entries"][1]
    assert e1["status"] == "untracked"


# ============================================================
# inspect_workspace
# ============================================================

def test_inspect_workspace_returns_error_when_git_fails(tmp_path):
    fake = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="boom"
    )
    with patch.object(wg.subprocess, "run", return_value=fake):
        out = wg.inspect_workspace(tmp_path)
    assert out["ok"] is False
    assert "boom" in out["error"]


def test_inspect_workspace_counts_root_deleted(tmp_path):
    fake = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=" D deleted_root.md\n M ai_collab/x.py\n",
        stderr="",
    )
    with patch.object(wg.subprocess, "run", return_value=fake):
        out = wg.inspect_workspace(tmp_path)
    assert out["ok"] is True
    assert out["root_deleted"] == 1
    assert out["totals"]["modified"] == 1
    assert out["totals"]["deleted"] == 1


def test_inspect_workspace_counts_results_untracked(tmp_path):
    fake = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="?? collaboration/results/R-001.md\n",
        stderr="",
    )
    with patch.object(wg.subprocess, "run", return_value=fake):
        out = wg.inspect_workspace(tmp_path)
    assert out["results_untracked"] == 1


# ============================================================
# run_workspace_guard: git error 路径
# ============================================================

def test_run_workspace_guard_records_warning_when_git_fails(tmp_path):
    """git 失败 + guard 不适用 -> 走 warning 分支, 不 violation"""
    fake = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="fatal: not a git repo"
    )
    with patch.object(wg.subprocess, "run", return_value=fake):
            report = wg.run_workspace_guard(
                workspace=tmp_path,
                command="apply",
                mode="apply",
                guard_config={
                    "enabled": False,
                    "applyOnly": False,
                    "failOnGitError": True,
                },
                force=False,
            )
    assert len(report["violations"]) == 0
    assert any("not a git repo" in w for w in report["warnings"])


# ============================================================
# stage_domain_changes
# ============================================================

def test_stage_domain_changes_unsupported_domain(tmp_path):
    out = wg.stage_domain_changes(
        workspace=tmp_path, domain="hacker-zone", dry_run=True
    )
    assert out["ok"] is False
    assert "unsupported domain" in out["error"]
    assert out["domain"] == "hacker-zone"


def test_stage_domain_changes_git_error(tmp_path):
    """git 失败 -> 返回 ok=False"""
    fake = subprocess.CompletedProcess(
        args=[], returncode=128, stdout="", stderr="git fail"
    )
    with patch.object(wg.subprocess, "run", return_value=fake):
        out = wg.stage_domain_changes(
            workspace=tmp_path, domain="source", dry_run=False
        )
    assert out["ok"] is False


def test_stage_domain_changes_dry_run_skips_git_add(tmp_path):
    """dry_run=True -> 不调用 git add"""
    fake = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=" M ai_collab/foo.py\n", stderr=""
    )
    with patch.object(wg.subprocess, "run", return_value=fake) as mock_run:
        out = wg.stage_domain_changes(
            workspace=tmp_path, domain="source", dry_run=True
        )
    assert out["ok"] is True
    assert mock_run.call_count == 1
    args = mock_run.call_args[0][0]
    assert "status" in args


# ============================================================
# _chunked
# ============================================================

def test_chunked_splits_correctly():
    items = list(range(450))
    chunks = wg._chunked(items, size=200)
    assert len(chunks) == 3
    assert len(chunks[0]) == 200
    assert len(chunks[1]) == 200
    assert len(chunks[2]) == 50


def test_chunked_empty():
    assert wg._chunked([]) == []


def test_chunked_smaller_than_size():
    assert wg._chunked([1, 2, 3], size=10) == [[1, 2, 3]]


# ============================================================
# 模块顶层导出
# ============================================================

def test_module_exports():
    assert callable(wg.inspect_workspace)
    assert callable(wg.run_workspace_guard)
    assert callable(wg.stage_domain_changes)
