"""
单元测试: dispatch_notebooklm 模块

测试 NotebookLM 与派单流程集成功能
"""


from ai_collab.integrations.dispatch_notebooklm import (
    _build_queries_for_task,
    _infer_task_type,
    archive_result_to_notebooklm,
    enrich_dispatch_payload,
    enrich_task_with_notebooklm,
    extract_key_sections,
)


class TestEnrichTaskWithNotebooklm:
    """测试 enrich_task_with_notebooklm 函数"""

    def test_enriches_task_with_context(self):
        """任务字典应被注入 notebooklm_context 字段"""
        task = {"task_id": "TASK-001", "description": "实现用户认证"}
        result = enrich_task_with_notebooklm(task)

        assert "notebooklm_context" in result
        ctx = result["notebooklm_context"]
        assert "technical_docs" in ctx
        assert "historical_solutions" in ctx
        assert "queried_at" in ctx
        assert "notebook_id" in ctx

    def test_preserves_original_task_fields(self):
        """原始任务字段应被保留"""
        task = {"task_id": "TASK-002", "description": "数据库迁移", "priority": "P0"}
        result = enrich_task_with_notebooklm(task)

        assert result["task_id"] == "TASK-002"
        assert result["description"] == "数据库迁移"
        assert result["priority"] == "P0"

    def test_custom_notebook_id(self):
        """应支持自定义 notebook_id"""
        task = {"task_id": "TASK-003", "description": "测试"}
        result = enrich_task_with_notebooklm(task, notebook_id="custom-notebook")

        assert result["notebooklm_context"]["notebook_id"] == "custom-notebook"

    def test_empty_task_fields(self):
        """空任务字段不应导致异常"""
        task = {}
        result = enrich_task_with_notebooklm(task)

        assert "notebooklm_context" in result


class TestEnrichDispatchPayload:
    """测试 enrich_dispatch_payload 函数"""

    def test_enriches_multiple_tasks(self):
        """应批量增强多个任务"""
        candidates = [
            {"task_id": "TASK-001", "description": "任务1"},
            {"task_id": "TASK-002", "description": "任务2"},
        ]
        results, stats = enrich_dispatch_payload(candidates)

        assert len(results) == 2
        assert "notebooklm_context" in results[0]
        assert "notebooklm_context" in results[1]
        assert stats["total"] == 2

    def test_empty_candidates(self):
        """空列表应返回空列表"""
        results, stats = enrich_dispatch_payload([])
        assert results == []
        assert stats["total"] == 0

    def test_single_candidate(self):
        """单个候选任务应正常处理"""
        candidates = [{"task_id": "TASK-001", "description": "单任务"}]
        results, stats = enrich_dispatch_payload(candidates)

        assert len(results) == 1
        assert "notebooklm_context" in results[0]
        assert stats["enriched"] == 1


class TestExtractKeySections:
    """测试 extract_key_sections 函数"""

    def test_extracts_all_sections(self):
        """应提取所有关键章节"""
        content = """# 结果报告

## 执行命令
python3 -m pytest tests/ -v

## 测试结论
所有测试通过

## 风险/回滚
无重大风险
"""
        result = extract_key_sections(content)

        assert "### 执行命令" in result
        assert "python3 -m pytest tests/ -v" in result
        assert "### 测试结论" in result
        assert "所有测试通过" in result
        assert "### 风险/回滚" in result
        assert "无重大风险" in result

    def test_extracts_partial_sections(self):
        """应只提取存在的章节"""
        content = """# 结果报告

## 执行命令
python3 test.py

## 测试结论
部分通过
"""
        result = extract_key_sections(content)

        assert "### 执行命令" in result
        assert "### 测试结论" in result
        assert "### 风险/回滚" not in result

    def test_no_matching_sections(self):
        """无匹配章节时应返回前500字符"""
        content = "这是一段没有标准章节格式的内容" * 50
        result = extract_key_sections(content)

        assert len(result) <= 500

    def test_empty_content(self):
        """空内容应返回空字符串"""
        result = extract_key_sections("")
        assert result == ""


class TestArchiveResultToNotebooklm:
    """测试 archive_result_to_notebooklm 函数"""

    def test_skips_nonexistent_file(self, tmp_path):
        """不存在的文件应跳过"""
        result = archive_result_to_notebooklm(
            task_id="TASK-001",
            result_file=str(tmp_path / "nonexistent.md"),
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "result_file_not_found"

    def test_archives_existing_file(self, tmp_path):
        """存在的文件应尝试归档"""
        result_file = tmp_path / "RESULT_TASK-001.md"
        result_file.write_text(
            """# 结果

## 执行命令
pytest tests/ -v

## 测试结论
全部通过

## 风险/回滚
无风险
"""
        )

        result = archive_result_to_notebooklm(
            task_id="TASK-001",
            result_file=str(result_file),
        )

        # 归档结果应包含 task_id 和 archived_at
        assert result["task_id"] == "TASK-001"
        assert "archived_at" in result
        # 在 MCP 不可用时，add_source 返回 error，但归档流程仍完成
        assert "status" in result

    def test_custom_notebook_id(self, tmp_path):
        """应支持自定义 notebook_id"""
        result_file = tmp_path / "RESULT.md"
        result_file.write_text("## 执行命令\ntest")

        result = archive_result_to_notebooklm(
            task_id="TASK-001",
            result_file=str(result_file),
            notebook_id="custom-notebook",
        )

        assert result["notebook_id"] == "custom-notebook"


class TestInferTaskType:
    """测试 _infer_task_type 函数"""

    def test_bugfix_from_task_id(self):
        """应从 task_id 推断 bugfix 类型"""
        assert _infer_task_type({"task_id": "TASK-FIX-001"}) == "bugfix"
        assert _infer_task_type({"task_id": "TASK-BUG-002"}) == "bugfix"

    def test_test_from_task_id(self):
        """应从 task_id 推断 test 类型"""
        assert _infer_task_type({"task_id": "TASK-TEST-001"}) == "test"
        assert _infer_task_type({"task_id": "TASK-INTEGRATION-001"}) == "test"

    def test_docs_from_task_id(self):
        """应从 task_id 推断 docs 类型"""
        assert _infer_task_type({"task_id": "TASK-DOC-001"}) == "docs"
        assert _infer_task_type({"task_id": "TASK-API-001"}) == "docs"

    def test_research_from_task_id(self):
        """应从 task_id 推断 research 类型"""
        assert _infer_task_type({"task_id": "TASK-RESEARCH-001"}) == "research"
        assert _infer_task_type({"task_id": "TASK-OPT-001"}) == "research"

    def test_implementation_from_description(self):
        """应从 description 推断 implementation 类型"""
        assert _infer_task_type({"description": "实现用户认证"}) == "implementation"
        assert _infer_task_type({"description": "implement caching"}) == "implementation"

    def test_bugfix_from_description(self):
        """应从 description 推断 bugfix 类型"""
        assert _infer_task_type({"description": "修复登录错误"}) == "bugfix"
        assert _infer_task_type({"description": "fix timeout bug"}) == "bugfix"

    def test_test_from_description(self):
        """应从 description 推断 test 类型"""
        assert _infer_task_type({"description": "测试覆盖率提升"}) == "test"
        assert _infer_task_type({"description": "add test coverage"}) == "test"

    def test_docs_from_description(self):
        """应从 description 推断 docs 类型"""
        assert _infer_task_type({"description": "文档更新"}) == "docs"
        assert _infer_task_type({"description": "API documentation"}) == "docs"

    def test_research_from_description(self):
        """应从 description 推断 research 类型"""
        assert _infer_task_type({"description": "优化查询性能"}) == "research"
        assert _infer_task_type({"description": "research best practices"}) == "research"

    def test_default_fallback(self):
        """无法推断时应返回 default"""
        assert _infer_task_type({"task_id": "TASK-XXX", "description": "misc"}) == "default"

    def test_empty_task(self):
        """空任务应返回 default"""
        assert _infer_task_type({}) == "default"

    def test_tags_inference(self):
        """应从 tags 推断类型"""
        assert _infer_task_type({"tags": ["bugfix"]}) == "bugfix"
        assert _infer_task_type({"tags": ["test"]}) == "test"
        assert _infer_task_type({"tags": ["docs"]}) == "docs"


class TestBuildQueriesForTask:
    """测试 _build_queries_for_task 函数"""

    def test_implementation_queries(self):
        """implementation 类型应生成实现相关查询"""
        task = {"task_id": "TASK-001", "description": "实现用户认证"}
        tech, history = _build_queries_for_task(task)

        assert "技术方案" in tech
        assert "架构设计" in tech
        assert "实现任务" in history

    def test_bugfix_queries(self):
        """bugfix 类型应生成修复相关查询"""
        task = {"task_id": "TASK-FIX-001", "description": "登录超时"}
        tech, history = _build_queries_for_task(task)

        assert "根因分析" in tech
        assert "修复方案" in tech
        assert "bug 修复" in history

    def test_test_queries(self):
        """test 类型应生成测试相关查询"""
        task = {"task_id": "TASK-TEST-001", "description": "API 测试"}
        tech, history = _build_queries_for_task(task)

        assert "测试策略" in tech
        assert "覆盖范围" in tech

    def test_docs_queries(self):
        """docs 类型应生成文档相关查询"""
        task = {"task_id": "TASK-DOC-001", "description": "API 文档"}
        tech, history = _build_queries_for_task(task)

        assert "文档结构" in tech
        assert "文档模板" in history

    def test_research_queries(self):
        """research 类型应生成调研相关查询"""
        task = {"task_id": "TASK-OPT-001", "description": "查询优化"}
        tech, history = _build_queries_for_task(task)

        assert "技术调研" in tech
        assert "调研结论" in history

    def test_default_queries(self):
        """default 类型应使用通用查询"""
        task = {"task_id": "TASK-001", "description": "通用任务"}
        tech, history = _build_queries_for_task(task)

        assert "如何实现" in tech
        assert "解决方案" in history

    def test_description_substitution(self):
        """description 应被正确替换到模板中"""
        task = {"task_id": "TASK-001", "description": "Redis 缓存"}
        tech, history = _build_queries_for_task(task)

        assert "Redis 缓存" in tech
