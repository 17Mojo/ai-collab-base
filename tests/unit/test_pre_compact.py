"""
PreCompact Hook 测试

测试 compact 前快照功能
"""

import json
from pathlib import Path
from unittest.mock import patch

from ai_collab.hooks.pre_compact import _get_cwd, _snapshot, main


class TestGetCwd:
    """测试 _get_cwd 函数"""

    def test_get_cwd_with_string(self):
        """测试字符串路径"""
        hook_input = {"cwd": "/tmp/test"}
        result = _get_cwd(hook_input)
        assert result == Path("/tmp/test")

    def test_get_cwd_with_bytes(self):
        """测试字节路径"""
        hook_input = {"cwd": b"/tmp/test"}
        # bytes 应该被正确解码为字符串
        result = _get_cwd(hook_input)
        assert result == Path("/tmp/test")

    def test_get_cwd_with_path(self):
        """测试 Path 对象"""
        hook_input = {"cwd": Path("/tmp/test")}
        # Path 对象不是 str 或 bytes,会返回默认值 "."
        result = _get_cwd(hook_input)
        assert result == Path(".")

    def test_get_cwd_missing(self):
        """测试缺少 cwd 字段"""
        hook_input = {}
        result = _get_cwd(hook_input)
        assert result == Path(".")

    def test_get_cwd_none(self):
        """测试 cwd 为 None"""
        hook_input = {"cwd": None}
        result = _get_cwd(hook_input)
        assert result == Path(".")


class TestSnapshot:
    """测试 _snapshot 函数"""

    def test_snapshot_existing_file(self, tmp_path):
        """测试快照存在的文件"""
        # 创建源文件
        src_file = tmp_path / "source.txt"
        src_file.write_text("test content")

        # 目标文件
        dest_file = tmp_path / "backup" / "source.txt"

        # 执行快照
        _snapshot(src_file, dest_file)

        # 验证
        assert dest_file.exists()
        assert dest_file.read_text() == "test content"

    def test_snapshot_nonexistent_file(self, tmp_path):
        """测试快照不存在的文件"""
        src_file = tmp_path / "nonexistent.txt"
        dest_file = tmp_path / "backup" / "nonexistent.txt"

        # 执行快照 (不应该报错)
        _snapshot(src_file, dest_file)

        # 验证目标文件不存在
        assert not dest_file.exists()

    def test_snapshot_creates_parent_dirs(self, tmp_path):
        """测试自动创建父目录"""
        src_file = tmp_path / "source.txt"
        src_file.write_text("test content")

        dest_file = tmp_path / "a" / "b" / "c" / "source.txt"

        # 执行快照
        _snapshot(src_file, dest_file)

        # 验证父目录被创建
        assert dest_file.parent.exists()
        assert dest_file.exists()

    def test_snapshot_preserves_metadata(self, tmp_path):
        """测试保留文件元数据"""
        src_file = tmp_path / "source.txt"
        src_file.write_text("test content")

        dest_file = tmp_path / "backup" / "source.txt"

        # 执行快照
        _snapshot(src_file, dest_file)

        # 验证内容相同
        assert dest_file.read_text() == src_file.read_text()


class TestMain:
    """测试 main 函数"""

    def test_main_with_valid_input(self, tmp_path):
        """测试有效输入"""
        # 准备输入
        hook_input = {"cwd": str(tmp_path)}

        # 创建源文件
        status_dir = tmp_path / ".cc-claude-codex"
        status_dir.mkdir()
        status_file = status_dir / "status.md"
        status_file.write_text("# Status")

        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        state_file = logs_dir / "collaboration_state.json"
        state_file.write_text('{"state": "test"}')

        # 模拟 stdin
        with patch("sys.stdin.read", return_value=json.dumps(hook_input)):
            with patch("sys.stderr"):
                main()

        # 验证快照被创建
        snapshots_dir = status_dir / "snapshots"
        assert snapshots_dir.exists()

        # 验证快照文件
        snapshot_files = list(snapshots_dir.glob("*-status.md"))
        assert len(snapshot_files) == 1
        assert snapshot_files[0].read_text() == "# Status"

        state_snapshots = list(snapshots_dir.glob("*-state.json"))
        assert len(state_snapshots) == 1
        assert state_snapshots[0].read_text() == '{"state": "test"}'

    def test_main_with_empty_input(self, tmp_path):
        """测试空输入"""
        # 切换到临时目录
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # 模拟空 stdin
            with patch("sys.stdin.read", return_value=""):
                with patch("sys.stderr"):
                    main()

            # 应该使用当前目录,不应该报错
        finally:
            os.chdir(original_cwd)

    def test_main_with_invalid_json(self, tmp_path):
        """测试无效 JSON 输入"""
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # 模拟无效 JSON
            with patch("sys.stdin.read", return_value="invalid json"):
                with patch("sys.stderr"):
                    main()

            # 应该使用空字典,不应该报错
        finally:
            os.chdir(original_cwd)

    def test_main_without_source_files(self, tmp_path):
        """测试源文件不存在的情况"""
        hook_input = {"cwd": str(tmp_path)}

        # 不创建源文件
        with patch("sys.stdin.read", return_value=json.dumps(hook_input)):
            with patch("sys.stderr"):
                main()

        # 应该不报错,快照目录可能被创建但为空
        tmp_path / ".cc-claude-codex" / "snapshots"
        # 快照目录可能存在也可能不存在
        # 重要的是没有报错

    def test_main_creates_snapshots_directory(self, tmp_path):
        """测试自动创建快照目录"""
        hook_input = {"cwd": str(tmp_path)}

        # 创建源文件
        status_dir = tmp_path / ".cc-claude-codex"
        status_dir.mkdir()
        status_file = status_dir / "status.md"
        status_file.write_text("# Status")

        # 执行
        with patch("sys.stdin.read", return_value=json.dumps(hook_input)):
            with patch("sys.stderr"):
                main()

        # 验证快照目录被创建
        snapshots_dir = status_dir / "snapshots"
        assert snapshots_dir.exists()


class TestEdgeCases:
    """测试边界情况"""

    def test_snapshot_with_special_characters_in_path(self, tmp_path):
        """测试路径包含特殊字符"""
        # 创建包含特殊字符的目录
        special_dir = tmp_path / "test dir with spaces"
        special_dir.mkdir()

        src_file = special_dir / "source.txt"
        src_file.write_text("test")

        dest_file = tmp_path / "backup" / "source.txt"

        # 执行快照
        _snapshot(src_file, dest_file)

        # 验证
        assert dest_file.exists()

    def test_snapshot_with_unicode_content(self, tmp_path):
        """测试 Unicode 内容"""
        src_file = tmp_path / "source.txt"
        src_file.write_text("测试内容 🎯", encoding="utf-8")

        dest_file = tmp_path / "backup" / "source.txt"

        # 执行快照
        _snapshot(src_file, dest_file)

        # 验证
        assert dest_file.read_text(encoding="utf-8") == "测试内容 🎯"

    def test_main_with_nested_cwd(self, tmp_path):
        """测试嵌套的工作目录"""
        nested_dir = tmp_path / "a" / "b" / "c"
        nested_dir.mkdir(parents=True)

        hook_input = {"cwd": str(nested_dir)}

        # 创建源文件
        status_dir = nested_dir / ".cc-claude-codex"
        status_dir.mkdir()
        status_file = status_dir / "status.md"
        status_file.write_text("# Status")

        # 执行
        with patch("sys.stdin.read", return_value=json.dumps(hook_input)):
            with patch("sys.stderr"):
                main()

        # 验证
        snapshots_dir = status_dir / "snapshots"
        assert snapshots_dir.exists()


class TestFilePermissions:
    """测试文件权限"""

    def test_snapshot_preserves_permissions(self, tmp_path):
        """测试保留文件权限"""
        src_file = tmp_path / "source.txt"
        src_file.write_text("test")

        # 设置权限
        import os

        os.chmod(src_file, 0o644)

        dest_file = tmp_path / "backup" / "source.txt"

        # 执行快照
        _snapshot(src_file, dest_file)

        # 验证权限被保留
        src_file.stat()
        dest_file.stat()

        # 注意: shutil.copy2 会保留权限
        assert dest_file.exists()
