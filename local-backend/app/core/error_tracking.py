"""
错误追踪增强模块
统一错误结构化日志、错误聚合、故障归档
"""

import json
import os
import threading
import time
import traceback
import uuid
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class ErrorRecord:
    """结构化错误记录"""

    request_id: str
    timestamp: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    error_type: str
    error_message: str
    error_category: str
    traceback_str: Optional[str]
    client_ip: Optional[str]
    user_agent: Optional[str]
    query_params: Optional[Dict[str, Any]]


class ErrorCategoryClassifier:
    """错误分类器"""

    # 具体分类优先，通用分类在后，但 "other" 应该最后匹配
    SORTED_CATEGORIES = [
        (
            "timeout",
            lambda e, sc: any(
                keyword in e.lower() for keyword in ["timeout", "timed out", "deadline"]
            ),
        ),
        (
            "database",
            lambda e, sc: any(
                keyword in e.lower()
                for keyword in ["database", "sqlite", "sql", "connection", "constraint", "foreign"]
            ),
        ),
        (
            "validation",
            lambda e, sc: any(
                keyword in e.lower()
                for keyword in ["validation", "invalid", "value", "type", "format", "schema"]
            ),
        ),
        (
            "permission",
            lambda e, sc: any(
                keyword in e.lower()
                for keyword in [
                    "permission",
                    "unauthorized",
                    "forbidden",
                    "access denied",
                    "authentication",
                ]
            ),
        ),
        ("other", lambda e, sc: True),  # 默认分类，必须在最后
    ]

    @classmethod
    def classify(cls, error: str, status_code: int) -> str:
        """分类错误

        Args:
            error: 错误消息
            status_code: HTTP 状态码

        Returns:
            错误类别
        """
        # 首先检查具体分类
        for category, classifier in cls.SORTED_CATEGORIES:
            if classifier(error, status_code):
                if category == "other":
                    # 如果没有匹配到具体分类，则返回基于状态码的分类
                    if 400 <= status_code < 500:
                        return "4xx_client"
                    elif 500 <= status_code < 600:
                        return "5xx_server"
                return category

        return "other"

    @classmethod
    def get_error_type(cls, error_message: str) -> str:
        """从错误消息中提取错误类型

        Args:
            error_message: 错误消息

        Returns:
            标准化的错误类型
        """
        # 提取异常类名
        if ": " in error_message:
            type_part = error_message.split(": ")[0]
            # 清理异常类名
            return type_part.strip().replace("[", "").replace("]", "")
        return "Unknown"


class ErrorAggregator:
    """错误聚合器 - 用于错误分类、统计和趋势分析"""

    MAX_RECENT_ERRORS = 1000
    ARCHIVE_THRESHOLD = 50

    def __init__(self):
        self._lock = threading.Lock()
        self._error_records: List[ErrorRecord] = []
        self._error_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "first_seen": None,
                "last_seen": None,
                "affected_endpoints": set(),
                "request_ids": set(),
            }
        )
        self._recent_errors_by_category: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

    def record_error(self, record: ErrorRecord) -> None:
        """记录错误

        Args:
            record: 结构化错误记录
        """
        with self._lock:
            # 添加到记录列表
            self._error_records.append(record)

            # 更新统计
            category = record.error_category
            stats = self._error_stats[category]
            stats["count"] += 1
            if stats["first_seen"] is None:
                stats["first_seen"] = record.timestamp
            stats["last_seen"] = record.timestamp
            stats["affected_endpoints"].add(f"{record.method} {record.path}")
            stats["request_ids"].add(record.request_id)

            # 添加到最近错误队列
            self._recent_errors_by_category[category].append(record)

            # 保持记录列表大小
            if len(self._error_records) > self.MAX_RECENT_ERRORS:
                self._error_records = self._error_records[-self.MAX_RECENT_ERRORS :]

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计

        Returns:
            错误统计信息
        """
        with self._lock:
            total_errors = len(self._error_records)

            # 按类别统计
            by_category = {}
            for category, stats in self._error_stats.items():
                by_category[category] = {
                    "count": stats["count"],
                    "first_seen": stats["first_seen"],
                    "last_seen": stats["last_seen"],
                    "affected_endpoints": len(stats["affected_endpoints"]),
                }

            # 获取Top端点
            endpoint_errors: Dict[str, int] = defaultdict(int)
            for record in self._error_records:
                endpoint = f"{record.method} {record.path}"
                endpoint_errors[endpoint] += 1

            top_endpoints = sorted(endpoint_errors.items(), key=lambda x: x[1], reverse=True)[:10]

            return {
                "total_errors": total_errors,
                "by_category": by_category,
                "top_endpoints": [{"endpoint": ep, "count": count} for ep, count in top_endpoints],
                "timestamp": datetime.now().isoformat(),
            }

    def get_recent_errors(
        self, category: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取最近的错误

        Args:
            category: 错误类别，None 表示所有类别
            limit: 返回数量限制

        Returns:
            错误记录列表
        """
        with self._lock:
            if category:
                records = list(self._recent_errors_by_category.get(category, []))
            else:
                records = self._error_records.copy()

            # 按时间倒序
            records.sort(key=lambda r: r.timestamp, reverse=True)

            # 转换为字典并限制数量
            return [asdict(r) for r in records[:limit]]

    def get_error_trend(self, hours: int = 24) -> Dict[str, List[Dict[str, Any]]]:
        """获取错误趋势

        Args:
            hours: 统计时间范围（小时）

        Returns:
            按时间分组的错误趋势
        """
        with self._lock:
            cutoff = datetime.now() - timedelta(hours=hours)
            trend: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

            for record in self._error_records:
                try:
                    record_time = datetime.fromisoformat(record.timestamp)
                    if record_time < cutoff:
                        continue

                    # 按小时分组
                    hour_key = record_time.strftime("%Y-%m-%d %H:00")
                    trend[hour_key].append(
                        {
                            "category": record.error_category,
                            "endpoint": f"{record.method} {record.path}",
                            "status_code": record.status_code,
                        }
                    )
                except ValueError:
                    continue

            # 生成趋势统计
            trend_stats = {}
            for hour, errors in sorted(trend.items()):
                category_counts: Dict[str, int] = defaultdict(int)
                for error in errors:
                    category_counts[error["category"]] += 1

                trend_stats[hour] = {"total": len(errors), "by_category": dict(category_counts)}

            return trend_stats

    def should_archive(self) -> bool:
        """检查是否应该归档

        Returns:
            是否应该归档
        """
        with self._lock:
            # 需要大于等于阈值才触发归档
            return len(self._error_records) >= self.ARCHIVE_THRESHOLD

    def clear_archived(self, archived_count: int = 0) -> None:
        """清除已归档的记录

        Args:
            archived_count: 已归档的记录数量
        """
        with self._lock:
            if archived_count > 0:
                self._error_records = self._error_records[archived_count:]
            else:
                # 清除所有记录
                for key in self._error_stats:
                    self._error_stats[key] = {
                        "count": 0,
                        "first_seen": None,
                        "last_seen": None,
                        "affected_endpoints": set(),
                        "request_ids": set(),
                    }
                for queue in self._recent_errors_by_category.values():
                    queue.clear()


class FaultArchiver:
    """故障归档器 - 定期归档错误数据"""

    def __init__(
        self,
        output_dir: str = "./logs/faults",
        auto_archive_interval_hours: int = 1,
        archive_threshold: int = 50,
    ):
        self.output_dir = output_dir
        self.auto_archive_interval_hours = auto_archive_interval_hours
        self.archive_threshold = archive_threshold
        self._last_archive_time = datetime.now()
        self._lock = threading.Lock()
        os.makedirs(output_dir, exist_ok=True)

    def archive_now(
        self, error_stats: Dict[str, Any] = None, recent_errors: List[Dict[str, Any]] = None
    ) -> str:
        """立即归档错误数据

        Args:
            error_stats: 错误统计
            recent_errors: 最近错误记录

        Returns:
            归档文件路径
        """
        with self._lock:
            # 使用毫秒精度避免文件名冲突
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]  # 精确到毫秒
            filename = f"faults_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)

            archive_data = {
                "archive_timestamp": datetime.now().isoformat(),
                "auto_archive_interval_hours": self.auto_archive_interval_hours,
                "archive_threshold": self.archive_threshold,
                "error_stats": error_stats or {},
                "recent_errors": recent_errors or [],
                "metadata": {
                    "total_errors": len(recent_errors) if recent_errors else 0,
                    "categories_count": len(error_stats.get("by_category", {}))
                    if error_stats
                    else 0,
                    "archived_by": "manual" if error_stats else "auto",
                },
            }

            # 写入归档文件
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(archive_data, f, indent=2, ensure_ascii=False)

            self._last_archive_time = datetime.now()
            return filepath

    def should_auto_archive(self) -> bool:
        """检查是否应该自动归档

        Returns:
            是否应该自动归档
        """
        with self._lock:
            time_since_last = datetime.now() - self._last_archive_time
            return time_since_last >= timedelta(hours=self.auto_archive_interval_hours)

    def get_archive_summary(self) -> List[Dict[str, Any]]:
        """获取归档文件摘要

        Returns:
            归档文件列表
        """
        summaries = []
        try:
            for filename in sorted(os.listdir(self.output_dir), reverse=True):
                if not filename.startswith("faults_") or not filename.endswith(".json"):
                    continue

                filepath = os.path.join(self.output_dir, filename)
                stat_info = os.stat(filepath)

                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                summaries.append(
                    {
                        "filename": filename,
                        "size_bytes": stat_info.st_size,
                        "modified_time": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        "total_errors": data.get("metadata", {}).get("total_errors", 0),
                        "archived_by": data.get("metadata", {}).get("archived_by", "unknown"),
                    }
                )
        except Exception:
            pass

        return summaries


class ErrorTracker:
    """错误追踪器 - 集成ErrorAggregator和FaultArchiver"""

    def __init__(self, error_aggregator: ErrorAggregator, fault_archiver: FaultArchiver):
        self.error_aggregator = error_aggregator
        self.fault_archiver = fault_archiver

    def track_error(
        self,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        error: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        query_params: Optional[Dict[str, Any]] = None,
        include_traceback: bool = False,
    ) -> None:
        """记录错误

        Args:
            request_id: 请求ID
            method: HTTP方法
            path: 路径
            status_code: 状态码
            duration_ms: 响应时间
            error: 错误消息
            client_ip: 客户端IP
            user_agent: 用户代理
            query_params: 查询参数
            include_traceback: 是否包含堆栈跟踪
        """
        # 分类错误
        error_category = ErrorCategoryClassifier.classify(error, status_code)
        error_type = ErrorCategoryClassifier.get_error_type(error)

        # 获取堆栈跟踪
        traceback_str = None
        if include_traceback:
            traceback_str = traceback.format_exc()

        # 创建错误记录
        record = ErrorRecord(
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            error_type=error_type,
            error_message=error,
            error_category=error_category,
            traceback_str=traceback_str,
            client_ip=client_ip,
            user_agent=user_agent,
            query_params=query_params,
        )

        # 记录错误
        self.error_aggregator.record_error(record)

    def check_and_archive(self) -> Optional[str]:
        """检查并执行归档

        Returns:
            归档文件路径，如果未归档则为None
        """
        # 检查自动归档条件
        if self.fault_archiver.should_auto_archive():
            error_stats = self.error_aggregator.get_error_stats()
            if error_stats["total_errors"] > 0:
                recent_errors = self.error_aggregator.get_recent_errors(limit=1000)
                filepath = self.fault_archiver.archive_now(error_stats, recent_errors)
                self.error_aggregator.clear_archived(len(recent_errors))
                return filepath

        # 检查阈值归档条件
        if self.error_aggregator.should_archive():
            error_stats = self.error_aggregator.get_error_stats()
            recent_errors = self.error_aggregator.get_recent_errors(limit=1000)
            filepath = self.fault_archiver.archive_now(error_stats, recent_errors)
            self.error_aggregator.clear_archived(len(recent_errors))
            return filepath

        return None


def generate_request_id() -> str:
    """生成唯一请求ID

    Returns:
        请求ID字符串
    """
    return f"req_{uuid.uuid4().hex[:16]}_{int(time.time() * 1000)}"


# 全局实例
_error_aggregator = ErrorAggregator()
_fault_archiver = FaultArchiver()
_error_tracker = ErrorTracker(_error_aggregator, _fault_archiver)


def get_error_aggregator() -> ErrorAggregator:
    """获取全局错误聚合器"""
    return _error_aggregator


def get_fault_archiver() -> FaultArchiver:
    """获取全局故障归档器"""
    return _fault_archiver


def get_error_tracker() -> ErrorTracker:
    """获取全局错误追踪器"""
    return _error_tracker


def track_error_with_request_id(request_id: str, *args, **kwargs) -> None:
    """使用已知request_id记录错误

    Args:
        request_id: 请求ID
        *args, **kwargs: 传递给ErrorTracker.track_error的参数
    """
    _error_tracker.track_error(request_id, *args, **kwargs)


def track_error_with_auto_id(*args, **kwargs) -> str:
    """自动生成request_id并记录错误

    Args:
        *args, **kwargs: 传递给ErrorTracker.track_error的参数（不包含request_id）

    Returns:
        生成的请求ID
    """
    request_id = generate_request_id()
    _error_tracker.track_error(request_id, *args, **kwargs)
    return request_id


if __name__ == "__main__":
    # 测试错误追踪
    print("🧪 测试错误追踪系统")

    # 生成请求ID
    request_id = generate_request_id()
    print(f"请求ID: {request_id}")

    # 记录错误
    errors = [
        ("Database connection failed", 500, 120.5),
        ("Validation error: invalid email format", 400, 45.2),
        ("Request timeout after 30s", 504, 30000.0),
        ("Permission denied", 403, 25.1),
    ]

    for error_msg, status, duration in errors:
        track_error_with_request_id(
            request_id=request_id,
            method="POST",
            path="/api/packs",
            status_code=status,
            duration_ms=duration,
            error=error_msg,
            client_ip="127.0.0.1",
            user_agent="Test Client",
        )

    # 查看错误统计
    stats = get_error_aggregator().get_error_stats()
    print("\n错误统计:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

    # 测试归档
    print("\n🧪 测试故障归档")
    for _ in range(60):  # 添加足够多的错误触发归档
        track_error_with_auto_id(
            method="GET",
            path="/api/packs/test",
            status_code=500,
            duration_ms=100.0,
            error="Test error",
        )

    archive_path = get_error_tracker().check_and_archive()
    if archive_path:
        print(f"归档完成: {archive_path}")
    else:
        print("未达到归档阈值")

    print("\n归档文件摘要:")
    for summary in get_fault_archiver().get_archive_summary()[:5]:
        print(f"  {summary['filename']}: {summary['total_errors']} errors")
