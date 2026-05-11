"""
错误追踪系统测试
测试 ErrorAggregator、FaultArchiver、ErrorCategoryClassifier 等组件
"""

# 直接导入模块
import importlib.util
import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta

import pytest

# 获取项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 加载 error_tracking 模块
error_tracking_path = os.path.join(
    project_root, "local-backend", "app", "core", "error_tracking.py"
)
spec = importlib.util.spec_from_file_location("error_tracking", error_tracking_path)
error_tracking = importlib.util.module_from_spec(spec)
spec.loader.exec_module(error_tracking)

ErrorAggregator = error_tracking.ErrorAggregator
ErrorCategoryClassifier = error_tracking.ErrorCategoryClassifier
FaultArchiver = error_tracking.FaultArchiver
ErrorTracker = error_tracking.ErrorTracker
ErrorRecord = error_tracking.ErrorRecord
generate_request_id = error_tracking.generate_request_id
get_error_aggregator = error_tracking.get_error_aggregator
get_fault_archiver = error_tracking.get_fault_archiver
get_error_tracker = error_tracking.get_error_tracker
track_error_with_request_id = error_tracking.track_error_with_request_id
track_error_with_auto_id = error_tracking.track_error_with_auto_id


class TestErrorCategoryClassifier:
    """测试错误分类器"""

    def test_classify_client_errors(self):
        """测试4xx客户端错误分类"""
        assert ErrorCategoryClassifier.classify("Bad request", 400) == "4xx_client"
        assert ErrorCategoryClassifier.classify("Not found", 404) == "4xx_client"
        assert ErrorCategoryClassifier.classify("Unauthorized", 401) == "permission"
        assert ErrorCategoryClassifier.classify("Forbidden", 403) == "permission"

    def test_classify_server_errors(self):
        """测试5xx服务器错误分类"""
        assert ErrorCategoryClassifier.classify("Internal server error", 500) == "5xx_server"
        assert ErrorCategoryClassifier.classify("Bad gateway", 502) == "5xx_server"
        assert ErrorCategoryClassifier.classify("Service unavailable", 503) == "5xx_server"

    def test_classify_timeout_errors(self):
        """测试超时错误分类"""
        assert ErrorCategoryClassifier.classify("Request timeout", 504) == "timeout"
        assert ErrorCategoryClassifier.classify("Operation timed out", 408) == "timeout"
        assert ErrorCategoryClassifier.classify("Deadline exceeded", 499) == "timeout"

    def test_classify_database_errors(self):
        """测试数据库错误分类"""
        assert ErrorCategoryClassifier.classify("Database connection failed", 500) == "database"
        assert ErrorCategoryClassifier.classify("SQLite constraint error", 400) == "database"
        assert ErrorCategoryClassifier.classify("Foreign key violation", 403) == "database"

    def test_classify_validation_errors(self):
        """测试验证错误分类"""
        assert (
            ErrorCategoryClassifier.classify("Validation error: invalid input", 400) == "validation"
        )
        assert ErrorCategoryClassifier.classify("Invalid value type", 400) == "validation"
        assert ErrorCategoryClassifier.classify("Schema validation failed", 422) == "validation"

    def test_get_error_type(self):
        """测试错误类型提取"""
        type1 = ErrorCategoryClassifier.get_error_type("ValueError: Invalid input")
        assert "ValueError" in type1

        type2 = ErrorCategoryClassifier.get_error_type("KeyError: 'missing_key'")
        assert "KeyError" in type2

        type3 = ErrorCategoryClassifier.get_error_type("Unknown error")
        assert type3 == "Unknown"


class TestErrorAggregator:
    """测试错误聚合器"""

    def setup_method(self):
        """每个测试方法前设置"""
        self.aggregator = ErrorAggregator()

    def test_record_error(self):
        """测试错误记录"""
        record = ErrorRecord(
            request_id="req_001",
            timestamp=datetime.now().isoformat(),
            method="GET",
            path="/api/packs",
            status_code=500,
            duration_ms=100.0,
            error_type="Error",
            error_message="Test error",
            error_category="5xx_server",
            traceback_str=None,
            client_ip="127.0.0.1",
            user_agent="Test Client",
            query_params=None,
        )

        self.aggregator.record_error(record)
        stats = self.aggregator.get_error_stats()

        assert stats["total_errors"] == 1
        assert "5xx_server" in stats["by_category"]
        assert stats["by_category"]["5xx_server"]["count"] == 1

    def test_error_stats(self):
        """测试错误统计"""
        errors = [
            ("Database error", 500, "database"),
            ("Validation error", 400, "validation"),
            ("Database error again", 500, "database"),
        ]

        for i, (msg, status, category) in enumerate(errors):
            record = ErrorRecord(
                request_id=f"req_{i}",
                timestamp=datetime.now().isoformat(),
                method="POST",
                path="/api/test",
                status_code=status,
                duration_ms=100.0,
                error_type="Error",
                error_message=msg,
                error_category=category,
                traceback_str=None,
                client_ip="127.0.0.1",
                user_agent="Test",
                query_params=None,
            )
            self.aggregator.record_error(record)

        stats = self.aggregator.get_error_stats()

        assert stats["total_errors"] == 3
        assert stats["by_category"]["database"]["count"] == 2
        assert stats["by_category"]["validation"]["count"] == 1

    def test_recent_errors(self):
        """测试获取最近错误"""
        for i in range(10):
            record = ErrorRecord(
                request_id=f"req_{i}",
                timestamp=datetime.now().isoformat(),
                method="GET",
                path="/api/error",
                status_code=500,
                duration_ms=100.0,
                error_type="Error",
                error_message=f"Error {i}",
                error_category="5xx_server",
                traceback_str=None,
                client_ip="127.0.0.1",
                user_agent="Test",
                query_params=None,
            )
            self.aggregator.record_error(record)

        recent = self.aggregator.get_recent_errors(limit=5)
        assert len(recent) == 5
        # 检查是否按时间倒序
        assert recent[0]["request_id"] == "req_9"

    def test_error_trend(self):
        """测试错误趋势"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        # 添加旧错误
        old_record = ErrorRecord(
            request_id="req_old",
            timestamp=one_hour_ago.isoformat(),
            method="POST",
            path="/api/old",
            status_code=500,
            duration_ms=100.0,
            error_type="Error",
            error_message="Old error",
            error_category="5xx_server",
            traceback_str=None,
            client_ip="127.0.0.1",
            user_agent="Test",
            query_params=None,
        )

        # 添加新错误
        new_record = ErrorRecord(
            request_id="req_new",
            timestamp=now.isoformat(),
            method="GET",
            path="/api/new",
            status_code=400,
            duration_ms=50.0,
            error_type="Error",
            error_message="New error",
            error_category="validation",
            traceback_str=None,
            client_ip="127.0.0.1",
            user_agent="Test",
            query_params=None,
        )

        self.aggregator.record_error(old_record)
        self.aggregator.record_error(new_record)

        trend = self.aggregator.get_error_trend(hours=2)
        assert len(trend) > 0


class TestFaultArchiver:
    """测试故障归档器"""

    def setup_method(self):
        """每个测试方法前设置"""
        # 使用临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.archiver = FaultArchiver(
            output_dir=self.temp_dir, auto_archive_interval_hours=1, archive_threshold=10
        )

    def teardown_method(self):
        """每个测试方法后清理"""
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_archive_now(self):
        """测试立即归档"""
        error_stats = {
            "total_errors": 5,
            "by_category": {"5xx_server": {"count": 5}},
            "top_endpoints": [{"endpoint": "POST /api/test", "count": 5}],
        }
        recent_errors = [
            {
                "request_id": f"req_{i}",
                "timestamp": datetime.now().isoformat(),
                "error_category": "5xx_server",
            }
            for i in range(5)
        ]

        filepath = self.archiver.archive_now(error_stats, recent_errors)

        # 验证文件创建成功
        assert os.path.exists(filepath)

        # 验证文件内容
        with open(filepath, "r") as f:
            data = json.load(f)

        assert data["error_stats"]["total_errors"] == 5
        assert len(data["recent_errors"]) == 5
        assert data["metadata"]["archived_by"] == "manual"

    def test_should_auto_archive(self):
        """测试自动归档时机"""
        # 刚创建时不应该自动归档
        assert not self.archiver.should_auto_archive()

        # 设置一个很旧的最后归档时间
        self.archiver._last_archive_time = datetime.now() - timedelta(hours=2)
        assert self.archiver.should_auto_archive()

    def test_get_archive_summary(self):
        """测试获取归档摘要"""
        # 创建几个归档文件，增加延时确保时间戳不同
        import time

        for i in range(3):
            error_stats = {"total_errors": i + 1, "by_category": {}}
            filepath = self.archiver.archive_now(error_stats, [])
            # 验证文件创建
            assert os.path.exists(filepath)
            time.sleep(0.1)  # 增加延时确保时间戳不同（至少100ms）

        # 获取摘要
        summaries = self.archiver.get_archive_summary()

        assert len(summaries) == 3
        # 检查摘要包含必要字段
        for summary in summaries:
            assert "filename" in summary
            assert "size_bytes" in summary
            assert "total_errors" in summary


class TestErrorTracker:
    """测试错误追踪器"""

    def setup_method(self):
        """每个测试方法前设置"""
        self.aggregator = ErrorAggregator()
        self.archiver = FaultArchiver(
            output_dir=tempfile.mkdtemp(),
            auto_archive_interval_hours=1,
            archive_threshold=5,  # 降低阈值以加快测试
        )
        # 修改聚合器的阈值以匹配归档器
        self.aggregator.ARCHIVE_THRESHOLD = 5
        self.tracker = ErrorTracker(self.aggregator, self.archiver)

    def teardown_method(self):
        """每个测试方法后清理"""
        try:
            shutil.rmtree(self.archiver.output_dir, ignore_errors=True)
        except Exception:
            pass

    def test_track_error(self):
        """测试错误追踪"""
        self.tracker.track_error(
            request_id="req_001",
            method="GET",
            path="/api/test",
            status_code=500,
            duration_ms=100.0,
            error="Test error",
            client_ip="127.0.0.1",
            user_agent="Test Client",
            query_params={"key": "value"},
        )

        stats = self.aggregator.get_error_stats()
        assert stats["total_errors"] == 1

    def test_check_and_archive_no_archive(self):
        """测试不满足归档条件"""
        # 添加少量错误
        self.tracker.track_error(
            request_id="req_001",
            method="GET",
            path="/api/test",
            status_code=500,
            duration_ms=100.0,
            error="Test error",
        )

        # 不应该触发归档
        result = self.tracker.check_and_archive()
        assert result is None

    def test_check_and_archive_with_archive(self):
        """测试满足归档条件"""
        # 添加足够的错误触发归档
        for i in range(self.archiver.archive_threshold):
            self.tracker.track_error(
                request_id=f"req_{i}",
                method="GET",
                path="/api/test",
                status_code=500,
                duration_ms=100.0,
                error=f"Error {i}",
            )

        # 应该触发归档
        result = self.tracker.check_and_archive()
        assert result is not None
        assert os.path.exists(result)


class TestRequestIdGeneration:
    """测试请求ID生成"""

    def test_generate_request_id(self):
        """测试请求ID生成"""
        id1 = generate_request_id()
        id2 = generate_request_id()

        # 验证格式
        assert id1.startswith("req_")
        assert len(id1) > 10

        # 验证唯一性
        assert id1 != id2


class TestGlobalInstances:
    """测试全局实例"""

    def test_get_error_aggregator(self):
        """测试获取全局错误聚合器"""
        aggregator = get_error_aggregator()
        assert isinstance(aggregator, ErrorAggregator)

    def test_get_fault_archiver(self):
        """测试获取全局故障归档器"""
        archiver = get_fault_archiver()
        assert isinstance(archiver, FaultArchiver)

    def test_get_error_tracker(self):
        """测试获取全局错误追踪器"""
        tracker = get_error_tracker()
        assert isinstance(tracker, ErrorTracker)

    def test_track_error_with_request_id(self):
        """测试使用已知request_id记录错误"""
        request_id = "test_req_001"
        track_error_with_request_id(
            request_id=request_id,
            method="GET",
            path="/api/test",
            status_code=500,
            duration_ms=100.0,
            error="Test error",
        )

        stats = get_error_aggregator().get_error_stats()
        assert stats["total_errors"] >= 1

    def test_track_error_with_auto_id(self):
        """测试自动生成request_id记录错误"""
        request_id = track_error_with_auto_id(
            method="GET", path="/api/test", status_code=500, duration_ms=100.0, error="Test error"
        )

        # 验证返回的request_id
        assert request_id is not None
        assert request_id.startswith("req_")

        # 验证错误已记录
        stats = get_error_aggregator().get_error_stats()
        assert stats["total_errors"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
