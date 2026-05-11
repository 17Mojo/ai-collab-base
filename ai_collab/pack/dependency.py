# Pack Dependency Management
# Week 3 Day 1: Pack 依赖管理系统

"""
Pack 依赖管理模块
支持依赖声明、解析、冲突检测和版本兼容性检查
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .version import PackVersion


class ComparisonOperator(Enum):
    """版本比较操作符"""

    EXACT = "="  # 精确匹配
    GREATER_THAN = ">"  # 大于
    LESS_THAN = "<"  # 小于
    GREATER_EQUAL = ">="  # 大于等于
    LESS_EQUAL = "<="  # 小于等于
    CARET = "^"  # 版本前缀兼容 (1.2.x)
    TILDE = "~"  # 版本范围兼容 (~1.2.3)
    OR = "|"  # 或逻辑
    AND = " &"  # 与逻辑


@dataclass
class PackDependency:
    """Pack 依赖定义"""

    name: str
    version_range: str  # SemVer range (e.g., ">=1.0.0,<2.0.0", "^1.2.0")
    optional: bool = False
    reason: str = ""

    def __post_init__(self):
        """验证依赖配置"""
        if not self.name:
            raise ValueError("Dependency name cannot be empty")
        if not self.version_range:
            raise ValueError("Version range cannot be empty")

        # 验证版本范围格式
        try:
            self._parse_range()
        except Exception as e:
            raise ValueError(f"Invalid version range '{self.version_range}': {e}")

    def _parse_range(self) -> List[Tuple[ComparisonOperator, str]]:
        """解析版本范围

        Returns:
            操作符和版本号列表
        """
        result = []

        # 处理 OR 操作符 |
        or_parts = self.version_range.split("|")
        operators = []

        for part in or_parts:
            operators.append("OR")
            result.append(self._parse_single_range(part.strip()))

        # 处理 AND 操作符 , 或 & 或 空格
        and_parts = []
        for part in or_parts:
            sub_parts = re.split(r"\s*,\s*|\s*&\s*|\s+", part.strip())
            for sub_part in sub_parts:
                if sub_part:
                    and_parts.append(sub_part)

        if len(and_parts) > 1:
            return [(ComparisonOperator.AND, and_parts)]

        # 解析单个范围
        for range_expr in and_parts:
            result.extend(self._parse_single_range(range_expr))

        return result

    def _parse_single_range(self, expr: str) -> Tuple[ComparisonOperator, str]:
        """解析单个范围表达式"""
        expr = expr.strip()

        try:
            # 精确匹配
            if expr.startswith("="):
                return ComparisonOperator.EXACT, expr[1:]

            # 单个版本号 (默认精确匹配)
            if not any(op in expr[:3] for op in ["<", ">", "^", "~"]):
                # 检查是否为有效版本号
                PackVersion.from_string(expr)
                return ComparisonOperator.EXACT, expr

            # 大于
            if expr.startswith(">="):
                return ComparisonOperator.GREATER_EQUAL, expr[2:]
            if expr.startswith(">"):
                return ComparisonOperator.GREATER_THAN, expr[1:]

            # 小于
            if expr.startswith("<="):
                return ComparisonOperator.LESS_EQUAL, expr[2:]
            if expr.startswith("<"):
                return ComparisonOperator.LESS_THAN, expr[1:]

            # 版本前缀兼容 ^1.2.3 -> >=1.2.0 <2.0.0
            if expr.startswith("^"):
                version = PackVersion.from_string(expr[1:])
                return ComparisonOperator.CARET, str(version)

            # 版本范围兼容 ~1.2.3 -> >=1.2.3 <1.3.0
            if expr.startswith("~"):
                version = PackVersion.from_string(expr[1:])
                return ComparisonOperator.TILDE, str(version)

            raise ValueError(f"Unknown range expression: {expr}")

        except Exception as e:
            raise ValueError(f"Failed to parse range '{expr}': {e}")

    def is_compatible_with(self, version: str) -> bool:
        """检查版本是否兼容

        Args:
            version: 版本字符串

        Returns:
            是否兼容
        """
        try:
            target_version = PackVersion.from_string(version)
            return self._check_version(target_version)
        except Exception:
            return False

    def _check_version(self, target_version: PackVersion) -> bool:
        """检查单个版本是否满足范围"""
        range_exprs = self.version_range.split("|")  # OR logic

        for expr in range_exprs:
            if self._check_single_expression(target_version, expr.strip()):
                return True

        return False

    def _check_single_expression(self, target: PackVersion, expr: str) -> bool:
        """检查单个表达式"""
        # 分解 AND 条件
        conditions = re.split(r"\s*,\s*|\s*&\s*", expr)

        for condition in conditions:
            if not self._check_condition(target, condition.strip()):
                return False

        return True

    def _check_condition(self, target: PackVersion, condition: str) -> bool:
        """检查单个条件"""
        operator, version_str = self._parse_single_range(condition)
        other_version = PackVersion.from_string(version_str)

        if operator == ComparisonOperator.EXACT:
            return target == other_version

        if operator == ComparisonOperator.GREATER_THAN:
            return target > other_version

        if operator == ComparisonOperator.GREATER_EQUAL:
            return target >= other_version

        if operator == ComparisonOperator.LESS_THAN:
            return target < other_version

        if operator == ComparisonOperator.LESS_EQUAL:
            return target <= other_version

        if operator == ComparisonOperator.CARET:
            # ^1.2.3 -> >=1.2.0 <2.0.0
            lower = PackVersion(other_version.major, other_version.minor, 0)
            upper = PackVersion(other_version.major + 1, 0, 0)
            return target >= lower and target < upper

        if operator == ComparisonOperator.TILDE:
            # ~1.2.3 -> >=1.2.3 <1.3.0
            lower = other_version
            upper = PackVersion(other_version.major, other_version.minor + 1, 0)
            return target >= lower and target < upper

        return False

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "name": self.name,
            "version_range": self.version_range,
            "optional": self.optional,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackDependency":
        """从字典反序列化"""
        return cls(
            name=data["name"],
            version_range=data["version_range"],
            optional=data.get("optional", False),
            reason=data.get("reason", ""),
        )


@dataclass
class DependencyNode:
    """依赖图节点"""

    pack_id: str
    version: str
    dependencies: List[PackDependency] = field(default_factory=list)
    resolved: bool = False
    depth: int = 0

    def add_dependency(self, dep: PackDependency) -> None:
        """添加依赖"""
        if dep not in self.dependencies:
            self.dependencies.append(dep)

    def requires(self, dep_name: str) -> Optional[PackDependency]:
        """获取指定名称的依赖"""
        for dep in self.dependencies:
            if dep.name == dep_name:
                return dep
        return None

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "pack_id": self.pack_id,
            "version": self.version,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "resolved": self.resolved,
            "depth": self.depth,
        }


@dataclass
class DependencyResult:
    """依赖解析结果"""

    success: bool
    resolved: List[DependencyNode]
    conflicts: List[Dict[str, Any]]
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "success": self.success,
            "resolved": [n.to_dict() for n in self.resolved],
            "conflicts": self.conflicts,
            "errors": self.errors,
        }


class DependencyResolver:
    """依赖解析器"""

    def __init__(self):
        self._registry: Dict[str, List[PackVersion]] = defaultdict(list)  # 可用的 Pack 版本
        self._logger = None

    def register_version(self, pack_id: str, version: str) -> None:
        """注册可用的 Pack 版本

        Args:
            pack_id: Pack ID
            version: 版本号
        """
        self._registry[pack_id].append(PackVersion.from_string(version))
        # 按版本号排序（降序）
        self._registry[pack_id].sort(reverse=True)

    def resolve(self, root: DependencyNode) -> DependencyResult:
        """解析依赖树

        Args:
            root: 根节点

        Returns:
            解析结果
        """
        result = DependencyResult(success=True, resolved=[root], conflicts=[], errors=[])

        resolved_dicts: Dict[str, str] = {root.pack_id: root.version}
        visited: Set[str] = set()
        stack: List[Tuple[DependencyNode, int]] = [(root, 0)]

        while stack:
            current, depth = stack.pop()
            current.depth = depth

            if current.pack_id in visited:
                continue
            visited.add(current.pack_id)

            for dep in current.dependencies:
                conflict = self._check_conflict(dep, resolved_dicts)
                if conflict:
                    result.success = False
                    result.conflicts.append(conflict)
                    continue

                # 查找兼容版本
                compatible_version = self._find_compatible_version(dep.name, dep.version_range)

                if not compatible_version:
                    error = f"No compatible version found for {dep.name} {dep.version_range}"
                    result.errors.append(error)
                    result.success = False
                    continue

                version_str = str(compatible_version)

                # 检查是否已解析
                if dep.name in resolved_dicts:
                    existing_version = resolved_dicts[dep.name]
                    if existing_version != version_str:
                        conflict = {
                            "pack": dep.name,
                            "existing": existing_version,
                            "requested": version_str,
                            "reason": f"Version conflict for {dep.name}",
                        }
                        result.conflicts.append(conflict)
                        result.success = False
                    continue

                # 创建新节点
                new_node = DependencyNode(
                    pack_id=dep.name, version=version_str, resolved=False, depth=depth + 1
                )
                resolved_dicts[dep.name] = version_str
                result.resolved.append(new_node)
                stack.append((new_node, depth + 1))

        # 标记所有已解析
        for node in result.resolved:
            node.resolved = True

        return result

    def _check_conflict(
        self, dep: PackDependency, resolved: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """检查冲突"""
        if dep.name not in resolved:
            return None

        existing_version = resolved[dep.name]
        if not dep.is_compatible_with(existing_version):
            return {
                "pack": dep.name,
                "existing": existing_version,
                "required_range": dep.version_range,
                "reason": f"Existing version {existing_version} does not satisfy {dep.version_range}",
            }

        return None

    def _find_compatible_version(self, pack_id: str, version_range: str) -> Optional[PackVersion]:
        """查找兼容版本

        Args:
            pack_id: Pack ID
            version_range: 版本范围

        Returns:
            兼容的最高版本
        """
        if pack_id not in self._registry:
            return None

        available = self._registry[pack_id]
        temp_dep = PackDependency(name=pack_id, version_range=version_range)

        for version in available:
            if temp_dep.is_compatible_with(str(version)):
                return version

        return None

    def detect_conflicts(self, graph: List[DependencyNode]) -> List[Dict[str, Any]]:
        """检测依赖冲突

        Args:
            graph: 依赖图

        Returns:
            冲突列表
        """
        conflicts = []
        version_map: Dict[str, List[str]] = defaultdict(list)

        # 收集所有版本要求
        for node in graph:
            for dep in node.dependencies:
                version_map[dep.name].append(dep.version_range)

        # 检查冲突
        for pack_id, ranges in version_map.items():
            if len(ranges) > 1:
                # 检查是否有共同兼容版本
                common_range = self._intersect_ranges(ranges)
                if not common_range:
                    conflicts.append(
                        {
                            "pack": pack_id,
                            "conflicting_ranges": ranges,
                            "reason": f"No common version satisfies all ranges: {ranges}",
                        }
                    )

        return conflicts

    def _intersect_ranges(self, ranges: List[str]) -> Optional[str]:
        """计算版本范围交集

        Args:
            ranges: 版本范围列表

        Returns:
            交集范围
        """
        if not ranges:
            return None

        if len(ranges) == 1:
            return ranges[0]

        # 简化实现：检查是否有共同版本
        # 实际实现需要更复杂的区间交集算法
        return ",".join(ranges)  # AND semantics

    def check_compatibility(self, dep: PackDependency, version: str) -> bool:
        """检查版本兼容性

        Args:
            dep: 依赖
            version: 版本号

        Returns:
            是否兼容
        """
        return dep.is_compatible_with(version)

    def topo_sort(self, graph: List[DependencyNode]) -> List[DependencyNode]:
        """拓扑排序，确定加载顺序

        Args:
            graph: 依赖图

        Returns:
            拓扑排序后的节点列表
        """
        # 构建邻接表
        adj: Dict[str, List[str]] = {}
        in_degree: Dict[str, int] = {}

        for node in graph:
            in_degree[node.pack_id] = node.depth
            adj[node.pack_id] = [dep.name for dep in node.dependencies]

        # 使用深度作为拓扑排序依据
        return sorted(graph, key=lambda x: x.depth)

    def get_install_order(self, root: DependencyNode) -> List[str]:
        """获取安装顺序

        Args:
            root: 根节点

        Returns:
            安装顺序的 Pack ID 列表
        """
        result = self.resolve(root)
        if not result.success:
            return []

        sorted_nodes = self.topo_sort(result.resolved)
        return [n.pack_id for n in sorted_nodes]
