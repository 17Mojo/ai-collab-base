"""
API 性能监控模块

提供 API 性能监控、日志记录和统计功能
"""

import json
import os
import threading
import time
from collections import defaultdict
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        """初始化性能监控器"""
        self._stats: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._enabled = True

    def record_call(
        self,
        endpoint: str,
        method: str,
        duration_ms: float,
        status_code: int,
        error: Optional[str] = None,
    ):
        """
        记录 API 调用

        Args:
            endpoint: 端点路径
            method: HTTP 方法
            duration_ms: 响应时间（毫秒）
            status_code: HTTP 状态码
            error: 错误信息（如果有）
        """
        if not self._enabled:
            return

        key = f"{method}:{endpoint}"

        with self._lock:
            if key not in self._stats:
                self._stats[key] = {
                    "endpoint": endpoint,
                    "method": method,
                    "calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "total_duration_ms": 0,
                    "min_duration_ms": float("inf"),
                    "max_duration_ms": 0,
                    "last_called_at": None,
                    "errors": [],
                    "status_codes": defaultdict(int),
                }

            stats = self._stats[key]
            stats["calls"] += 1
            stats["total_duration_ms"] += duration_ms
            stats["min_duration_ms"] = min(stats["min_duration_ms"], duration_ms)
            stats["max_duration_ms"] = max(stats["max_duration_ms"], duration_ms)
            stats["last_called_at"] = datetime.now().isoformat()
            stats["status_codes"][status_code] += 1

            if status_code >= 400:
                stats["failed_calls"] += 1
                if error:
                    stats["errors"].append(
                        {"error": error, "timestamp": datetime.now().isoformat()}
                    )
                    # 只保留最近10个错误
                    if len(stats["errors"]) > 10:
                        stats["errors"] = stats["errors"][-10:]
            else:
                stats["successful_calls"] += 1

    def get_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        获取性能统计

        Args:
            endpoint: 特定端点，None 表示所有端点

        Returns:
            统计信息字典
        """
        with self._lock:
            if endpoint:
                key_pattern = endpoint
                matching_stats = {k: v for k, v in self._stats.items() if key_pattern in k}
            else:
                matching_stats = self._stats.copy()

        # 计算平均值等衍生指标
        result = {}
        for key, stats in matching_stats.items():
            calls = stats["calls"]
            if calls > 0:
                stats["avg_duration_ms"] = stats["total_duration_ms"] / calls
                stats["success_rate"] = (stats["successful_calls"] / calls) * 100
            else:
                stats["avg_duration_ms"] = 0
                stats["success_rate"] = 0

            # 转换 defaultdict 为普通 dict
            if "status_codes" in stats:
                stats["status_codes"] = dict(stats["status_codes"])

            result[key] = stats

        return result

    def get_summary(self) -> Dict[str, Any]:
        """
        获取总体摘要

        Returns:
            总体统计摘要
        """
        with self._lock:
            total_calls = sum(s["calls"] for s in self._stats.values())
            total_successful = sum(s["successful_calls"] for s in self._stats.values())
            total_duration = sum(s["total_duration_ms"] for s in self._stats.values())

            if total_calls > 0:
                avg_duration = total_duration / total_calls
                overall_success_rate = (total_successful / total_calls) * 100
            else:
                avg_duration = 0
                overall_success_rate = 0

            return {
                "total_endpoints": len(self._stats),
                "total_calls": total_calls,
                "total_successful": total_successful,
                "total_failed": total_calls - total_successful,
                "avg_duration_ms": avg_duration,
                "overall_success_rate": overall_success_rate,
                "monitored_endpoints": list(self._stats.keys()),
                "timestamp": datetime.now().isoformat(),
            }

    def clear(self):
        """清空统计数据"""
        with self._lock:
            self._stats.clear()

    def export_stats(self, output_path: Optional[str] = None) -> str:
        """
        导出统计数据

        Args:
            output_path: 输出文件路径，None 则自动生成

        Returns:
            导出的文件路径
        """
        if not output_path:
            output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs", "performance")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(
                output_dir, f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {"summary": self.get_summary(), "details": self.get_stats()},
                f,
                indent=2,
                ensure_ascii=False,
            )

        return output_path


# 全局性能监控实例
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控实例"""
    return _performance_monitor


def monitor_performance(endpoint: str = ""):
    """
    性能监控装饰器

    Args:
        endpoint: 端点路径，如果为空则从函数名推断

    Returns:
        装饰器函数
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            monitor = get_performance_monitor()

            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000

                # 从上下文中获取状态码
                status_code = 200
                if hasattr(result, "status_code"):
                    status_code = result.status_code

                monitor.record_call(
                    endpoint=endpoint or f"/{func.__name__}",
                    method="POST",  # 默认为 POST，可根据实际情况调整
                    duration_ms=duration,
                    status_code=status_code,
                )

                return result

            except Exception as e:
                duration = (time.time() - start_time) * 1000
                monitor.record_call(
                    endpoint=endpoint or f"/{func.__name__}",
                    method="POST",
                    duration_ms=duration,
                    status_code=500,
                    error=str(e),
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            monitor = get_performance_monitor()

            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000

                status_code = 200
                if hasattr(result, "status_code"):
                    status_code = result.status_code

                monitor.record_call(
                    endpoint=endpoint or f"/{func.__name__}",
                    method="GET",  # 默认为 GET
                    duration_ms=duration,
                    status_code=status_code,
                )

                return result

            except Exception as e:
                duration = (time.time() - start_time) * 1000
                monitor.record_call(
                    endpoint=endpoint or f"/{func.__name__}",
                    method="GET",
                    duration_ms=duration,
                    status_code=500,
                    error=str(e),
                )
                raise

        # 检测是否为异步函数
        if hasattr(func, "__code__") and hasattr(func.__code__, "co_flags"):
            # 这是一个 Python 3.5+ 的方式来检测协程函数
            import inspect

            if inspect.iscoroutinefunction(func):
                return async_wrapper
        return sync_wrapper

    return decorator


class APILogger:
    """API 日志记录器"""

    def __init__(self, log_dir: str = "./logs/api"):
        """
        初始化日志记录器

        Args:
            log_dir: 日志目录
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self._current_log_file = self._get_log_file()
        self._lock = threading.Lock()

    def _get_log_file(self) -> str:
        """获取当前日志文件"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.log_dir, f"api_{date_str}.log")

    def log_request(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        body_size: int = 0,
    ):
        """记录 API 请求"""
        with self._lock:
            # 检查是否需要切换到新日期的日志文件
            current_file = self._get_log_file()
            if current_file != self._current_log_file:
                self._current_log_file = current_file

            timestamp = datetime.now().isoformat()

            # 过滤敏感信息
            safe_headers = self._filter_sensitive_headers(headers or {})

            log_entry = {
                "timestamp": timestamp,
                "event": "request",
                "method": method,
                "path": path,
                "query_params": query_params,
                "headers": safe_headers,
                "body_size_bytes": body_size,
            }

            with open(self._current_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def log_response(
        self, method: str, path: str, status_code: int, duration_ms: float, response_size: int = 0
    ):
        """记录 API 响应"""
        with self._lock:
            timestamp = datetime.now().isoformat()

            log_entry = {
                "timestamp": timestamp,
                "event": "response",
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "response_size_bytes": response_size,
            }

            with open(self._current_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def log_error(
        self, method: str, path: str, error: str, status_code: int = 500, duration_ms: float = 0
    ):
        """记录 API 错误"""
        with self._lock:
            timestamp = datetime.now().isoformat()

            log_entry = {
                "timestamp": timestamp,
                "event": "error",
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "error": error,
            }

            with open(self._current_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def _filter_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """过滤敏感头部信息"""
        sensitive_keys = {
            "authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
            "x-client-token",
            "token",
        }

        return {k: "***" if k.lower() in sensitive_keys else v for k, v in headers.items()}


# 全局日志记录器实例
_api_logger = APILogger()


def get_api_logger() -> APILogger:
    """获取全局 API 日志记录器"""
    return _api_logger


if __name__ == "__main__":
    # 测试性能监控
    print("🧪 测试性能监控")

    monitor = get_performance_monitor()

    # 模拟 API 调用
    monitor.record_call("/api/packs", "GET", 50.5, 200)
    monitor.record_call("/api/packs", "GET", 45.2, 200)
    monitor.record_call("/api/packs", "POST", 150.8, 201)
    monitor.record_call("/api/packs", "GET", 300.0, 500, "Internal server error")

    print(f"性能统计摘要: {monitor.get_summary()}")
    print(f"详细统计: {monitor.get_stats()}")

    # 导出统计数据
    export_path = monitor.export_stats()
    print(f"统计数据已导出至: {export_path}")

    # 测试日志记录
    print("\n🧪 测试日志记录")
    logger = get_api_logger()
    logger.log_request("GET", "/api/packs", {"limit": "10"}, {"user-agent": "Test"}, 1024)
    logger.log_response("GET", "/api/packs", 200, 45.5, 2048)
    print(f"日志已记录至: {logger._current_log_file}")
