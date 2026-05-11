# Pack Bulk Operations
# Week 3 Day 2: Pack 批量操作

"""
批量操作模块
支持 Pack 批量创建、更新、归档、删除
"""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .market_api import PackMarketAPI
from .version import PackVersion, VersionType


class OperationType(Enum):
    """操作类型"""

    CREATE = "create"
    UPDATE_VERSION = "update_version"
    ARCHIVE = "archive"
    DELETE = "delete"


class OperationStatus(Enum):
    """操作状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BulkOperation:
    """批量操作"""

    operation_id: str
    operation_type: OperationType
    pack_ids: List[str]
    specs: List[Dict[str, Any]] = field(default_factory=list)
    status: OperationStatus = OperationStatus.PENDING
    results: List[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = field(default_factory=datetime.now)

    @property
    def total(self) -> int:
        """总操作数"""
        return len(self.pack_ids)

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "pack_ids": self.pack_ids,
            "status": self.status.value,
            "results": self.results,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "total": self.total,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BulkOperation":
        """反序列化"""
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        updated_at = (
            datetime.fromisoformat(data.get("updated_at", data.get("created_at")))
            if data.get("updated_at")
            else None
        )

        return cls(
            operation_id=data["operation_id"],
            operation_type=OperationType(data["operation_type"]),
            pack_ids=data["pack_ids"],
            specs=data.get("specs", []),
            status=OperationStatus(data["status"]),
            results=data.get("results", []),
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class BulkOperationResult:
    """批量操作结果"""

    operation_id: str
    total: int
    succeeded: int = 0
    failed: int = 0
    cancelled: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    started_at: Optional[datetime] = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total == 0:
            return 0.0
        return (self.succeeded / self.total) * 100

    def to_dict(self) -> Dict[str, Any]:
        """序列化"""
        return {
            "operation_id": self.operation_id,
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "cancelled": self.cancelled,
            "success_rate": round(self.success_rate, 2),
            "results": self.results,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class BulkOperationEngine:
    """批量操作引擎"""

    def __init__(self, db_path: str = "data/packs.db", max_workers: int = 5):
        """初始化引擎

        Args:
            db_path: 数据库路径
            max_workers: 最大并发数
        """
        self.api = PackMarketAPI(db_path)
        self.max_workers = max_workers
        self._operations: Dict[str, BulkOperation] = {}

    def create_operation(
        self,
        operation_type: OperationType,
        pack_ids: List[str],
        specs: Optional[List[Dict[str, Any]]] = None,
    ) -> BulkOperation:
        """创建批量操作

        Args:
            operation_type: 操作类型
            pack_ids: Pack ID 列表
            specs: 操作规格（用于创建）

        Returns:
            批量操作对象
        """
        operation_id = f"bulk_{operation_type.value}_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        operation = BulkOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            pack_ids=pack_ids.copy(),
            specs=specs.copy() if specs else [],
        )

        self._operations[operation_id] = operation
        return operation

    def get_operation(self, operation_id: str) -> Optional[BulkOperation]:
        """获取操作

        Args:
            operation_id: 操作 ID

        Returns:
            操作对象，不存在返回 None
        """
        return self._operations.get(operation_id)

    def bulk_create(
        self, pack_specs: List[Dict[str, Any]], parallel: bool = True
    ) -> BulkOperationResult:
        """批量创建 Pack

        Args:
            pack_specs: Pack 规格列表
            parallel: 是否并行执行

        Returns:
            操作结果
        """
        pack_ids = []
        for i, spec in enumerate(pack_specs):
            pack_id = f"bulk_create_{i}_{int(time.time())}"
            spec["pack_id"] = pack_id
            pack_ids.append(pack_id)

        operation = self.create_operation(OperationType.CREATE, pack_ids, pack_specs)
        result = BulkOperationResult(
            operation_id=operation.operation_id, total=len(pack_ids), started_at=datetime.now()
        )

        results = self._execute_bulk_operation(operation, parallel)

        result.succeeded = sum(1 for r in results if r["success"])
        result.failed = sum(1 for r in results if not r["success"])
        result.results = results
        result.completed_at = datetime.now()

        # 更新操作状态
        operation.status = OperationStatus.COMPLETED
        operation.results = results

        return result

    def bulk_update_version(
        self, pack_ids: List[str], version_bump: str, parallel: bool = True
    ) -> BulkOperationResult:
        """批量更新版本

        Args:
            pack_ids: Pack ID 列表
            version_bump: 版本升级类型 (major/minor/patch)
            parallel: 是否并行执行

        Returns:
            操作结果
        """
        operation = self.create_operation(OperationType.UPDATE_VERSION, pack_ids)
        result = BulkOperationResult(
            operation_id=operation.operation_id, total=len(pack_ids), started_at=datetime.now()
        )

        results = []

        def update_one(pack_id: str) -> Dict[str, Any]:
            """更新单个 Pack 版本"""
            pack = self.api.get_pack(pack_id)
            if not pack.get("success"):
                return {"pack_id": pack_id, "success": False, "error": "Pack not found"}

            try:
                version_type = VersionType(version_bump.lower())
                current_version = pack["pack"]["version"]
                pack_version = PackVersion.from_string(current_version)

                new_version = pack_version.bump(version_type)

                version_result = self.api.update_pack(pack_id=pack_id, version=str(new_version))

                return {
                    "pack_id": pack_id,
                    "success": version_result["success"],
                    "version": str(new_version),
                    "error": version_result.get("error"),
                }
            except Exception as e:
                return {"pack_id": pack_id, "success": False, "error": str(e)}

        if parallel:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                results = list(executor.map(update_one, pack_ids))
        else:
            results = [update_one(pid) for pid in pack_ids]

        result.succeeded = sum(1 for r in results if r["success"])
        result.failed = sum(1 for r in results if not r["success"])
        result.results = results
        result.completed_at = datetime.now()

        operation.status = OperationStatus.COMPLETED
        operation.results = results

        return result

    def bulk_archive(self, pack_ids: List[str], parallel: bool = True) -> BulkOperationResult:
        """批量归档 Pack

        Args:
            pack_ids: Pack ID 列表
            parallel: 是否并行执行

        Returns:
            操作结果
        """
        from .market import PackStatus

        operation = self.create_operation(OperationType.ARCHIVE, pack_ids)
        result = BulkOperationResult(
            operation_id=operation.operation_id, total=len(pack_ids), started_at=datetime.now()
        )

        def archive_one(pack_id: str) -> Dict[str, Any]:
            """归档单个 Pack"""
            listing = self.api.store.get_listing(pack_id)
            if not listing:
                return {"pack_id": pack_id, "success": False, "error": "Pack not found"}

            # 直接更新 store 中的状态
            listing.status = PackStatus.ARCHIVED
            success = self.api.store.update_listing(listing)

            return {
                "pack_id": pack_id,
                "success": success,
                "error": None if success else "Failed to update pack",
            }

        if parallel:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                results = list(executor.map(archive_one, pack_ids))
        else:
            results = [archive_one(pid) for pid in pack_ids]

        result.succeeded = sum(1 for r in results if r["success"])
        result.failed = sum(1 for r in results if not r["success"])
        result.results = results
        result.completed_at = datetime.now()

        operation.status = OperationStatus.COMPLETED
        operation.results = results

        return result

    def bulk_delete(
        self, pack_ids: List[str], confirm_token: str, parallel: bool = True
    ) -> BulkOperationResult:
        """批量删除 Pack

        Args:
            pack_ids: Pack ID 列表
            confirm_token: 确认令牌
            parallel: 是否并行执行

        Returns:
            操作结果
        """
        # 生成预期令牌
        expected_token = f"delete_{len(pack_ids)}"
        if confirm_token != expected_token:
            return BulkOperationResult(
                operation_id="invalid",
                total=len(pack_ids),
                started_at=datetime.now(),
                completed_at=datetime.now(),
            )

        operation = self.create_operation(OperationType.DELETE, pack_ids)
        result = BulkOperationResult(
            operation_id=operation.operation_id, total=len(pack_ids), started_at=datetime.now()
        )

        def delete_one(pack_id: str) -> Dict[str, Any]:
            """删除单个 Pack"""
            listing = self.api.store.get_listing(pack_id)
            if not listing:
                return {"pack_id": pack_id, "success": False, "error": "Pack not found"}

            # 删除 Pack
            delete_result = self.api.delete_pack(pack_id)

            return {
                "pack_id": pack_id,
                "success": delete_result["success"],
                "error": delete_result.get("message"),
            }

        if parallel:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                results = list(executor.map(delete_one, pack_ids))
        else:
            results = [delete_one(pid) for pid in pack_ids]

        result.succeeded = sum(1 for r in results if r["success"])
        result.failed = sum(1 for r in results if not r["success"])
        result.results = results
        result.completed_at = datetime.now()

        operation.status = OperationStatus.COMPLETED
        operation.results = results

        return result

    def _execute_bulk_operation(
        self, operation: BulkOperation, parallel: bool
    ) -> List[Dict[str, Any]]:
        """执行批量操作（内部方法）"""
        if operation.operation_type != OperationType.CREATE:
            raise ValueError(f"Not implemented for {operation.operation_type}")

        results = []
        pack_specs = operation.specs

        def create_one(spec: Dict[str, Any]) -> Dict[str, Any]:
            """创建单个 Pack"""
            try:
                pack_id = spec.get("pack_id", "unknown")
                pack_name = spec.get("pack_name", "Unnamed Pack")

                result = self.api.create_pack(
                    pack_name=pack_name,
                    version=spec.get("version", "1.0.0"),
                    description=spec.get("description", ""),
                    author=spec.get("author", "bulk_import"),
                    category=spec.get("category", "general"),
                    tags=spec.get("tags", []),
                )

                return {
                    "pack_id": result.get("pack_id", pack_id),
                    "success": result["success"],
                    "error": result.get("message"),
                }
            except Exception as e:
                return {
                    "pack_id": spec.get("pack_id", "unknown"),
                    "success": False,
                    "error": str(e),
                }

        if parallel:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                results = list(executor.map(create_one, pack_specs))
        else:
            results = [create_one(spec) for spec in pack_specs]

        return results

    def get_operation_status(self, operation_id: str) -> BulkOperationResult:
        """获取操作状态

        Args:
            operation_id: 操作 ID

        Returns:
            操作结果
        """
        operation = self.get_operation(operation_id)
        if not operation:
            return BulkOperationResult(
                operation_id=operation_id,
                total=0,
                started_at=datetime.now(),
                completed_at=datetime.now(),
            )

        if operation.status == OperationStatus.RUNNING:
            return BulkOperationResult(
                operation_id=operation_id,
                total=operation.total,
                started_at=operation.created_at,
                completed_at=None,
            )

        if operation.status == OperationStatus.COMPLETED:
            completed = operation.results
            succeeded = sum(1 for r in completed if r.get("success"))

            result = BulkOperationResult(
                operation_id=operation_id,
                total=len(operation.pack_ids),
                succeeded=succeeded,
                failed=len(operation.pack_ids) - succeeded,
                results=completed,
                started_at=operation.created_at,
                completed_at=operation.updated_at,
            )
            return result

        # PENDING 状态
        return BulkOperationResult(
            operation_id=operation_id,
            total=len(operation.pack_ids),
            started_at=operation.created_at,
            completed_at=None,
        )

    def get_all_operations(self) -> List[Dict[str, Any]]:
        """获取所有操作

        Returns:
            操作列表
        """
        return [op.to_dict() for op in self._operations.values()]

    def cancel_operation(self, operation_id: str) -> bool:
        """取消操作

        Args:
            operation_id: 操作 ID

        Returns:
            是否取消成功
        """
        operation = self.get_operation(operation_id)
        if not operation:
            return False

        if operation.status not in [OperationStatus.PENDING, OperationStatus.RUNNING]:
            return False

        operation.status = OperationStatus.CANCELLED
        return True
