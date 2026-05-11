"""
速率限制和防暴力破解模块

提供 API 速率限制、IP 黑名单、防暴力破解功能
"""

import json
import os
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, Request, status


class RateLimiter:
    """速率限制器"""

    def __init__(self, default_limit: int = 100, window_seconds: int = 60):
        """
        初始化速率限制器

        Args:
            default_limit: 默认每窗口请求限制
            window_seconds: 时间窗口（秒）
        """
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[Tuple[float, bool]]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(
        self, identifier: str, limit: Optional[int] = None, window_seconds: Optional[int] = None
    ) -> Tuple[bool, Dict[str, int]]:
        """
        检查是否允许请求

        Args:
            identifier: 唯一标识符（IP、Token等）
            limit: 请求限制，None 使用默认值
            window_seconds: 时间窗口，None 使用默认值

        Returns:
            (是否允许, 限制信息)
        """
        limit = limit or self.default_limit
        window = window_seconds or self.window_seconds
        now = time.time()

        with self._lock:
            # 获取当前窗口的请求记录
            requests = self._requests[identifier]

            # 移除窗口外的请求
            requests[:] = [req for req in requests if req[0] > now - window]

            # 检查是否超过限制
            count = len(requests)
            remaining = max(0, limit - count)
            reset_time = now + window

            # 记录本次请求
            requests.append((now, True))

            limit_info = {
                "limit": limit,
                "remaining": remaining,
                "reset_time": int(reset_time),
                "window_seconds": window_seconds,
                "current_count": count,
            }

            return count < limit, limit_info

    def cleanup(self) -> int:
        """
        清理过期记录

        Returns:
            清理的记录数
        """
        now = time.time()
        with self._lock:
            cleaned = 0
            keys_to_remove = []

            for key, requests in self._requests.items():
                # 移除窗口外的请求
                old_length = len(requests)
                requests[:] = [req for req in requests if req[0] > now - self.window_seconds]
                cleaned += old_length - len(requests)

                # 如果没有有效请求，删除键
                if not requests:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._requests[key]

            return cleaned

    def get_stats(self, identifier: str) -> Dict[str, Any]:
        """
        获取特定标识符的统计信息

        Args:
            identifier: 唯一标识符

        Returns:
            统计信息
        """
        now = time.time()
        with self._lock:
            requests = self._requests[identifier]
            # 获取当前窗口的请求
            recent = [req for req in requests if req[0] > now - self.window_seconds]

            if not recent:
                return {
                    "identifier": identifier,
                    "total_requests": len(requests),
                    "recent_count": 0,
                    "is_limited": False,
                }

            return {
                "identifier": identifier,
                "total_requests": len(requests),
                "recent_count": len(recent),
                "first_request": datetime.fromtimestamp(min(req[0] for req in recent)).isoformat(),
                "last_request": datetime.fromtimestamp(max(req[0] for req in recent)).isoformat(),
                "is_limited": len(recent) >= self.default_limit,
            }


class BruteForceProtection:
    """防暴力破解保护"""

    def __init__(self, max_attempts: int = 5, block_duration_minutes: int = 30):
        """
        初始化防暴力破解保护

        Args:
            max_attempts: 最大尝试次数
            block_duration_minutes: 封禁时长（分钟）
        """
        self.max_attempts = max_attempts
        self.block_duration = timedelta(minutes=block_duration_minutes)
        self._attempts: Dict[str, List[Tuple[float, bool]]] = defaultdict(list)
        self._blocked_until: Dict[str, float] = {}
        self._lock = threading.Lock()

    def record_attempt(self, identifier: str, success: bool) -> Dict[str, Any]:
        """
        记录登录/认证尝试

        Args:
            identifier: 唯一标识符（用户名、IP等）
            success: 是否成功

        Returns:
            尝试信息字典
        """
        now = time.time()

        with self._lock:
            # 检查是否被封禁
            if identifier in self._blocked_until:
                blocked_until = self._blocked_until[identifier]
                if now < blocked_until:
                    return {
                        "blocked": True,
                        "blocked_until": datetime.fromtimestamp(blocked_until).isoformat(),
                        "remaining_time_seconds": int(blocked_until - now),
                        "attempts": len(self._attempts[identifier]),
                    }
                else:
                    # 封禁已过期，移除
                    del self._blocked_until[identifier]
                    self._attempts[identifier] = []

            # 记录尝试
            self._attempts[identifier].append((now, success))

            # 清除旧的成功尝试
            self._attempts[identifier] = [
                (timestamp, success)
                for timestamp, success in self._attempts[identifier]
                if now - timestamp < 3600  # 保留1小时内的记录
            ]

            # 计算失败次数
            failed_attempts = sum(1 for _, success in self._attempts[identifier] if not success)

            # 检查是否需要封禁
            if failed_attempts >= self.max_attempts:
                self._blocked_until[identifier] = now + self.block_duration.total_seconds()

                return {
                    "blocked": True,
                    "blocked_until": datetime.fromtimestamp(
                        self._blocked_until[identifier]
                    ).isoformat(),
                    "remaining_time_seconds": int(self.block_duration.total_seconds()),
                    "attempts": failed_attempts,
                    "reason": "Too many failed attempts",
                }

            return {
                "blocked": False,
                "attempts": failed_attempts,
                "remaining_attempts": self.max_attempts - failed_attempts,
                "recent_activity": [
                    {"timestamp": datetime.fromtimestamp(ts).isoformat(), "success": success}
                    for ts, success in self._attempts[identifier][-5:]  # 最近5次
                ],
            }

    def is_blocked(self, identifier: str) -> bool:
        """检查标识符是否被封禁"""
        now = time.time()
        with self._lock:
            if identifier not in self._blocked_until:
                return False

            if now >= self._blocked_until[identifier]:
                # 封禁已过期
                del self._blocked_until[identifier]
                return False

            return True

    def unblock(self, identifier: str) -> bool:
        """
        解除封禁

        Args:
            identifier: 唯一标识符

        Returns:
            是否成功解除
        """
        with self._lock:
            if identifier in self._blocked_until:
                del self._blocked_until[identifier]
                return True
            return False

    def reset_attempts(self, identifier: str) -> bool:
        """
        重置尝试记录

        Args:
            identifier: 唯一标识符

        Returns:
            是否成功重置
        """
        with self._lock:
            if identifier in self._attempts:
                del self._attempts[identifier]
                return True
            return False


class IPBlacklist:
    """IP 黑名单管理"""

    def __init__(self):
        """初始化 IP 黑名单"""
        self._blacklist: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._storage_file = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "ip_blacklist.json"
        )
        self._load_from_storage()

    def _load_from_storage(self):
        """从文件加载黑名单"""
        if os.path.exists(self._storage_file):
            try:
                with open(self._storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._blacklist = data.get("blacklist", {})
            except Exception:
                self._blacklist = {}

    def _save_to_storage(self):
        """保存黑名单到文件"""
        os.makedirs(os.path.dirname(self._storage_file), exist_ok=True)
        with open(self._storage_file, "w", encoding="utf-8") as f:
            json.dump(
                {"blacklist": self._blacklist, "updated_at": datetime.now().isoformat()},
                f,
                indent=2,
                ensure_ascii=False,
            )

    def add_ip(self, ip_address: str, reason: str, duration_hours: Optional[int] = None) -> bool:
        """
        添加 IP 到黑名单

        Args:
            ip_address: IP 地址
            reason: 封禁原因
            duration_hours: 封禁时长（小时），None 表示永久

        Returns:
            是否成功添加
        """
        with self._lock:
            now = datetime.now()
            self._blacklist[ip_address] = {
                "ip": ip_address,
                "reason": reason,
                "added_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=duration_hours)).isoformat()
                if duration_hours
                else None,
                "is_permanent": duration_hours is None,
            }
            self._save_to_storage()
            return True

    def remove_ip(self, ip_address: str) -> bool:
        """
        从黑名单移除 IP

        Args:
            ip_address: IP 地址

        Returns:
            是否成功移除
        """
        with self._lock:
            if ip_address in self._blacklist:
                del self._blacklist[ip_address]
                self._save_to_storage()
                return True
            return False

    def is_blacklisted(self, ip_address: str) -> bool:
        """
        检查 IP 是否在黑名单中

        Args:
            ip_address: IP 地址

        Returns:
            是否在黑名单中
        """
        with self._lock:
            if ip_address not in self._blacklist:
                return False

            entry = self._blacklist[ip_address]

            # 检查是否过期
            if not entry["is_permanent"] and entry.get("expires_at"):
                expiry = datetime.fromisoformat(entry["expires_at"])
                if datetime.now() >= expiry:
                    # 已过期，移除
                    del self._blacklist[ip_address]
                    self._save_to_storage()
                    return False

            return True

    def get_blacklisted_ips(self) -> List[Dict[str, Any]]:
        """
        获取所有黑名单 IP

        Returns:
            黑名单 IP 列表
        """
        with self._lock:
            # 过滤已过期的临时封禁
            now = datetime.now()
            valid_entries = []

            for ip, entry in self._blacklist.items():
                if entry["is_permanent"] or not entry.get("expires_at"):
                    valid_entries.append(entry)
                else:
                    expiry = datetime.fromisoformat(entry["expires_at"])
                    if now < expiry:
                        valid_entries.append(entry)

            return valid_entries

    def cleanup_expired(self) -> int:
        """
        清理过期的黑名单条目

        Returns:
            清理的条目数
        """
        with self._lock:
            now = datetime.now()
            expired_ips = []

            for ip, entry in list(self._blacklist.items()):
                if not entry["is_permanent"] and entry.get("expires_at"):
                    expiry = datetime.fromisoformat(entry["expires_at"])
                    if now >= expiry:
                        expired_ips.append(ip)

            for ip in expired_ips:
                del self._blacklist[ip]

            if expired_ips:
                self._save_to_storage()

            return len(expired_ips)


# 全局实例
_rate_limiter = RateLimiter(default_limit=100, window_seconds=60)
_brute_force_protection = BruteForceProtection(max_attempts=5, block_duration_minutes=30)
_ip_blacklist = IPBlacklist()


def get_rate_limiter() -> RateLimiter:
    """获取全局速率限制器"""
    return _rate_limiter


def get_brute_force_protection() -> BruteForceProtection:
    """获取全局防暴力破解保护实例"""
    return _brute_force_protection


def get_ip_blacklist() -> IPBlacklist:
    """获取全局 IP 黑名单实例"""
    return _ip_blacklist


async def check_rate_limit(request: Request, limit: int = 100) -> None:
    """
    FastAPI 依赖项：检查速率限制

    Args:
        request: FastAPI 请求对象
        limit: 请求限制

    Raises:
        HTTPException: 超过速率限制
    """
    # 获取客户端 IP
    client_ip = request.client.host if request.client else "unknown"
    limiter = get_rate_limiter()

    # 检查 IP 黑名单
    blacklist = get_ip_blacklist()
    if blacklist.is_blacklisted(client_ip):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您的 IP 地址已被封禁")

    # 检查速率限制
    is_allowed, limit_info = limiter.is_allowed(client_ip, limit=limit)

    if not is_allowed:
        reset_time = datetime.fromtimestamp(limit_info["reset_time"])
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
            headers={
                "X-RateLimit-Limit": str(limit_info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(limit_info["reset_time"]),
                "Retry-After": str(int(reset_time.timestamp() - time.time())),
            },
        )

    # 添加速率限制信息到响应头
    # （需要通过中间件或响应处理来添加）


if __name__ == "__main__":
    # 测试速率限制
    print("🧪 测试速率限制")

    limiter = get_rate_limiter()

    # 模拟请求
    for i in range(10):
        allowed, info = limiter.is_allowed("test-client")
        print(f"请求 {i+1}: {'允许' if allowed else '拒绝'} (剩余: {info['remaining']})")
        time.sleep(0.1)

    # 测试防暴力破解保护
    print("\n🧪 测试防暴力破解保护")

    protection = get_brute_force_protection()

    # 模拟失败登录
    for i in range(6):
        result = protection.record_attempt("test-user", success=False)
        print(
            f"尝试 {i+1}: {'被封禁' if result['blocked'] else '未被封禁'} (剩余尝试: {result.get('remaining_attempts', 'N/A')})"
        )

    # 测试 IP 黑名单
    print("\n🧪 测试 IP 黑名单")

    blacklist = get_ip_blacklist()
    blacklist.add_ip("192.168.1.100", "Test blocking", duration_hours=1)
    print(f"IP 192.168.1.100 是否被黑名单: {blacklist.is_blacklisted('192.168.1.100')}")
    print(f"黑名单 IP 数量: {len(blacklist.get_blacklisted_ips())}")
