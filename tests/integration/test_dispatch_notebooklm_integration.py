"""
集成测试: 派单流程与 NotebookLM 集成

测试 agent_dispatch_bridge.py 的 --enrich-notebooklm 功能
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestDispatchBridgeNotebookLMIntegration:
    """测试 dispatch bridge 与 NotebookLM 集成"""

    def test_dry_run_without_enrich(self):
        """测试 dry-run 模式不启用 NotebookLM 增强"""
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/agent_dispatch_bridge.py"),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode == 0
        assert (
            "notebooklm_enriched" not in result.stdout or "notebooklm_enriched=0" in result.stdout
        )

    def test_dry_run_with_enrich_notebooklm(self):
        """测试 dry-run 模式启用 NotebookLM 增强"""
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/agent_dispatch_bridge.py"),
                "--dry-run",
                "--enrich-notebooklm",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode == 0
        # 应该有 notebooklm_enriched 输出
        assert "notebooklm_enriched=" in result.stdout

    def test_report_contains_notebooklm_enriched_field(self):
        """测试报告包含 notebooklm_enriched 字段"""
        # 先运行一次带 enrich 的
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/agent_dispatch_bridge.py"),
                "--dry-run",
                "--enrich-notebooklm",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )

        report_path = ROOT / "logs/task_dispatch_report.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            assert "notebooklm_enriched" in report
            assert isinstance(report["notebooklm_enriched"], int)

    def test_enriched_task_has_context_in_notes(self):
        """测试增强后的任务在 notes 中包含 notebooklm_context"""
        report_path = ROOT / "logs/task_dispatch_report.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))

            if report.get("notebooklm_enriched", 0) > 0:
                # 找到被增强的任务
                for task in report.get("candidate_tasks", []):
                    notes = task.get("notes", [])
                    # 检查是否有 notebooklm_context
                    has_context = any("notebooklm_context" in str(n) for n in notes)
                    if has_context:
                        # 验证 context 结构
                        for note in notes:
                            if "notebooklm_context" in str(note):
                                assert "technical_docs" in str(note)
                                assert "queried_at" in str(note)
                                break
                        break


class TestNotebookLMModeSelection:
    """测试 NotebookLM 模式选择"""

    def test_default_mode_is_fallback(self):
        """测试默认模式是 FALLBACK"""
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/agent_dispatch_bridge.py"),
                "--dry-run",
                "--enrich-notebooklm",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        # FALLBACK 模式会打印回退信息到 stderr
        combined = result.stdout.lower() + result.stderr.lower()
        assert "fallback" in combined or "mock" in combined

    def test_mock_mode(self):
        """测试 MOCK 模式"""
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/agent_dispatch_bridge.py"),
                "--dry-run",
                "--enrich-notebooklm",
                "--notebooklm-mode",
                "MOCK",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert result.returncode == 0


class TestEnrichDispatchPayload:
    """测试 enrich_dispatch_payload 函数"""

    def test_enrich_empty_list(self):
        """测试空列表"""
        from ai_collab.integrations.dispatch_notebooklm import enrich_dispatch_payload

        results, stats = enrich_dispatch_payload([])
        assert results == []
        assert stats["total"] == 0

    def test_enrich_single_task(self):
        """测试单个任务增强"""
        from ai_collab.integrations.dispatch_notebooklm import enrich_dispatch_payload

        task = {
            "task_id": "TEST-001",
            "description": "测试任务",
        }
        results, stats = enrich_dispatch_payload([task])

        assert len(results) == 1
        assert "notebooklm_context" in results[0]
        assert "technical_docs" in results[0]["notebooklm_context"]
        assert "queried_at" in results[0]["notebooklm_context"]
        assert stats["enriched"] == 1

    def test_enrich_multiple_tasks(self):
        """测试多个任务批量增强"""
        from ai_collab.integrations.dispatch_notebooklm import enrich_dispatch_payload

        tasks = [
            {"task_id": "TEST-001", "description": "任务1"},
            {"task_id": "TEST-002", "description": "任务2"},
            {"task_id": "TEST-003", "description": "任务3"},
        ]
        results, stats = enrich_dispatch_payload(tasks)

        assert len(results) == 3
        for task in results:
            assert "notebooklm_context" in task
        assert stats["enriched"] == 3


class TestArchiveResultToNotebookLM:
    """测试结果归档功能"""

    def test_archive_nonexistent_file(self):
        """测试归档不存在的文件"""
        from ai_collab.integrations.dispatch_notebooklm import archive_result_to_notebooklm

        result = archive_result_to_notebooklm(
            "TEST-001",
            "nonexistent/file.md",
        )
        assert result["status"] == "skipped"
        assert result["reason"] == "result_file_not_found"

    def test_archive_existing_file(self, tmp_path):
        """测试归档存在的文件"""
        from ai_collab.integrations.dispatch_notebooklm import archive_result_to_notebooklm

        # 创建临时结果文件
        result_file = tmp_path / "RESULT_TEST.md"
        result_file.write_text(
            """# 结果报告

## 执行命令
pytest tests/

## 测试结论
All tests passed

## 风险/回滚
No risks identified
""",
            encoding="utf-8",
        )

        result = archive_result_to_notebooklm(
            "TEST-001",
            str(result_file),
        )
        assert result["status"] == "archived"
        assert result["task_id"] == "TEST-001"
