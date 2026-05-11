"""
Prompt Pack 管理器 - 负责 Pack 的加载、依赖解析、上下文注入
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .schema import AITool, PackCategoryType, PackDependencyError, PackManifest, PromptPack


class PackManager:
    """
    Pack 管理器

    负责：
    - Pack 加载和解析
    - 依赖关系解析
    - 上下文注入到 AI 工具
    - 智能推荐最佳 Pack
    """

    def __init__(self, packs_root: Path):
        """
        初始化 Pack 管理器

        Args:
            packs_root: Packs 存储根目录
        """
        self.packs_root = Path(packs_root)
        self._packs_cache: Dict[str, PromptPack] = {}

    def load_pack(self, pack_name: str) -> PromptPack:
        """
        加载 Pack

        Args:
            pack_name: Pack 名称

        Returns:
            PromptPack: 加载的 Pack

        Raises:
            FileNotFoundError: Pack 不存在
            ValueError: Pack 格式错误
        """
        # 检查缓存
        if pack_name in self._packs_cache:
            return self._packs_cache[pack_name]

        pack_path = self.packs_root / pack_name

        if not pack_path.exists():
            raise FileNotFoundError(f"Pack not found: {pack_name}")

        # 加载 manifest
        manifest_path = pack_path / "manifest.json"
        if not manifest_path.exists():
            raise ValueError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        manifest = PackManifest.from_dict(manifest_data)

        # 创建 Pack 对象
        pack = PromptPack(manifest=manifest, root_path=pack_path)

        # 加载所有 .md 和 .txt 规则文件
        for rule_file in pack_path.glob("*.md"):
            with open(rule_file, "r", encoding="utf-8") as f:
                content = f.read()
            pack.add_rule(rule_file.name, content)

        for rule_file in pack_path.glob("*.txt"):
            with open(rule_file, "r", encoding="utf-8") as f:
                content = f.read()
            pack.add_rule(rule_file.name, content)

        # 缓存
        self._packs_cache[pack_name] = pack

        return pack

    def resolve_dependencies(self, pack: PromptPack) -> List[PromptPack]:
        """
        解析 Pack 依赖关系

        Args:
            pack: 要解析的 Pack

        Returns:
            List[PromptPack]: 依赖的 Pack 列表（按依赖顺序）

        Raises:
            PackDependencyError: 依赖解析失败
            PackCompatibilityError: 依赖不兼容
        """
        resolved: List[PromptPack] = []
        visited: Set[str] = set()

        def _resolve(pack_name: str, path: List[str]) -> PromptPack:
            """递归解析依赖"""
            # 检测循环依赖
            if pack_name in path:
                raise PackDependencyError(
                    f"Circular dependency detected: {' -> '.join(path + [pack_name])}"
                )

            if pack_name in visited:
                # 已经解析过
                return self._packs_cache.get(pack_name)

            # 加载 Pack
            sub_pack = self.load_pack(pack_name)

            # 解析其依赖
            new_path = path + [pack_name]
            for dep_name in sub_pack.manifest.dependencies:
                dep_pack = _resolve(dep_name, new_path)
                if dep_pack:
                    resolved.append(dep_pack)

            visited.add(pack_name)
            return sub_pack

        # 解析主 Pack 的依赖
        for dep_name in pack.manifest.dependencies:
            dep_pack = _resolve(dep_name, [pack.manifest.name])
            if dep_pack:
                resolved.append(dep_pack)

        return resolved

    def get_packed_context(
        self,
        pack_name: str,
        tool: AITool,
        include_dependencies: bool = True,
        token_budget: Optional[int] = None,
    ) -> str:
        """
        获取 Pack 及其依赖的完整上下文

        Args:
            pack_name: Pack 名称
            tool: 目标 AI 工具
            include_dependencies: 是否包含依赖 Pack
            token_budget: 可选 token 预算上限

        Returns:
            str: 完整的上下文字符串
        """
        # 加载主 Pack
        pack = self.load_pack(pack_name)

        packs_to_render: List[PromptPack] = [pack]
        if include_dependencies:
            packs_to_render.extend(self.resolve_dependencies(pack))

        # 无预算限制，保持原有行为：全部拼接
        if token_budget is None:
            contexts = [p.to_context(tool) for p in packs_to_render if p.to_context(tool)]
            return "\n\n---\n\n".join(contexts)

        # 有预算时按顺序装箱，超预算则尝试压缩主 Pack 保底输出
        selected_packs: List[PromptPack] = []
        used_tokens = 0
        for candidate in packs_to_render:
            candidate_tokens = self.estimate_pack_tokens(candidate, include_dependencies=False)
            if used_tokens + candidate_tokens <= token_budget:
                selected_packs.append(candidate)
                used_tokens += candidate_tokens

        if not selected_packs and token_budget > 0:
            # 主 Pack 单体超预算时，压缩后至少给出一个可用上下文
            compressed = self.compress_pack_tokens(pack, compression_ratio=0.5)
            if self.estimate_pack_tokens(compressed, include_dependencies=False) <= token_budget:
                selected_packs = [compressed]

        contexts = [p.to_context(tool) for p in selected_packs if p.to_context(tool)]
        return "\n\n---\n\n".join(contexts)

    def list_available_packs(self, category: Optional[PackCategoryType] = None) -> List[str]:
        """
        列出可用的 Pack

        Args:
            category: 可选，按类别过滤

        Returns:
            List[str]: Pack 名称列表
        """
        packs = []

        for pack_dir in self.packs_root.iterdir():
            if not pack_dir.is_dir():
                continue

            manifest_path = pack_dir / "manifest.json"
            if not manifest_path.exists():
                continue

            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                manifest = PackManifest.from_dict(manifest_data)

                if category is None or manifest.category == category:
                    packs.append(manifest.name)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return sorted(packs)

    def get_best_pack(
        self, task_description: str, tool: AITool, category: Optional[PackCategoryType] = None
    ) -> Optional[PromptPack]:
        """
        智能推荐最佳 Pack（基于关键词匹配）

        Args:
            task_description: 任务描述
            tool: 目标 AI 工具
            category: 可选，限制类别

        Returns:
            Optional[PromptPack]: 推荐的 Pack，如果没有匹配则返回 None
        """
        # 转换为小写以便匹配
        task_lower = task_description.lower()

        # 遍历所有可用的 Pack
        available = self.list_available_packs(category)

        for pack_name in available:
            pack = self.load_pack(pack_name)

            # 检查兼容性
            if tool not in pack.manifest.compatible_tools:
                if AITool.UNIVERSAL not in pack.manifest.compatible_tools:
                    continue

            # 关键词匹配
            # 匹配名称
            if pack_name.lower() in task_lower:
                return pack

            # 匹配描述
            if pack.manifest.description.lower() in task_lower:
                return pack

            # 匹配标签
            for tag in pack.manifest.tags:
                if tag.lower() in task_lower:
                    return pack

        return None

    def inject_into_ai_context(self, pack_name: str, current_context: str, tool: AITool) -> str:
        """
        将 Pack 上下文注入到现有的 AI 上下文中

        Args:
            pack_name: Pack 名称
            current_context: 当前上下文
            tool: 目标 AI 工具

        Returns:
            str: 注入后的完整上下文
        """
        packed_context = self.get_packed_context(pack_name, tool)

        if not packed_context:
            return current_context

        # 如果当前上下文为空，直接返回 Pack 上下文
        if not current_context:
            return packed_context

        # 将 Pack 上下文插入到现有上下文之后
        return current_context + "\n\n" + packed_context

    def clear_cache(self):
        """清除 Pack 缓存"""
        self._packs_cache.clear()

    def estimate_pack_tokens(self, pack: PromptPack, include_dependencies: bool = False) -> int:
        """
        估算 Pack 的 token 数量

        Args:
            pack: 要估算的 Pack
            include_dependencies: 是否包含依赖的 token

        Returns:
            估算的 token 数量
        """
        # 简单估算: 每个单词约 1.3 tokens
        total_tokens = 0

        for rule_name, rule_file in pack.rules.items():
            # RuleFile 对象有 content 属性
            if hasattr(rule_file, "content"):
                content = rule_file.content
            else:
                content = str(rule_file)
            words = len(content.split())
            total_tokens += int(words * 1.3)

        if include_dependencies:
            for dep_name in pack.manifest.dependencies:
                try:
                    dep_pack = self.load_pack(dep_name)
                    total_tokens += self.estimate_pack_tokens(dep_pack, include_dependencies=False)
                except Exception:
                    pass

        return total_tokens

    def validate_token_budget(self, packs: List[PromptPack], budget_limit: int) -> bool:
        """
        验证 Pack 列表是否在 token 预算内

        Args:
            packs: Pack 列表
            budget_limit: token 预算限制

        Returns:
            是否在预算内
        """
        total_tokens = sum(self.estimate_pack_tokens(pack) for pack in packs)
        return total_tokens <= budget_limit

    def get_remaining_budget(self, packs: List[PromptPack], total_budget: int) -> int:
        """
        获取剩余 token 预算

        Args:
            packs: Pack 列表
            total_budget: 总 token 预算

        Returns:
            剩余 token 数量
        """
        used_tokens = sum(self.estimate_pack_tokens(pack) for pack in packs)
        return max(0, total_budget - used_tokens)

    def select_packs_within_budget(
        self, packs: List[PromptPack], budget_limit: int
    ) -> List[PromptPack]:
        """
        选择在预算内的 Pack

        Args:
            packs: Pack 列表
            budget_limit: token 预算限制

        Returns:
            在预算内的 Pack 列表
        """
        selected = []
        current_tokens = 0

        for pack in sorted(packs, key=lambda p: self.estimate_pack_tokens(p)):
            pack_tokens = self.estimate_pack_tokens(pack)
            if current_tokens + pack_tokens <= budget_limit:
                selected.append(pack)
                current_tokens += pack_tokens

        return selected

    def optimize_pack_selection(
        self, packs: List[PromptPack], budget_limit: int, target_tags: Optional[List[str]] = None
    ) -> List[PromptPack]:
        """
        优化 Pack 选择

        Args:
            packs: Pack 列表
            budget_limit: token 预算限制
            target_tags: 目标标签列表

        Returns:
            优化后的 Pack 列表
        """
        if target_tags:
            # 优先选择匹配标签的 Pack
            tagged_packs = [p for p in packs if any(tag in p.manifest.tags for tag in target_tags)]
            other_packs = [p for p in packs if p not in tagged_packs]
            packs = tagged_packs + other_packs

        return self.select_packs_within_budget(packs, budget_limit)

    def calculate_token_efficiency(self, pack: PromptPack) -> float:
        """
        计算 Pack 的 token 效率

        Args:
            pack: 要计算的 Pack

        Returns:
            token 效率 (rules / tokens)
        """
        tokens = self.estimate_pack_tokens(pack)
        if tokens == 0:
            return 0.0

        rule_count = len(pack.rules)
        return rule_count / tokens

    def compress_pack_tokens(self, pack: PromptPack, compression_ratio: float = 0.3) -> PromptPack:
        """
        压缩 Pack 的 token 数量

        Args:
            pack: 要压缩的 Pack
            compression_ratio: 压缩比例

        Returns:
            压缩后的 Pack
        """
        # 按词切分后截断，构造新的 Pack，避免修改原对象
        ratio = min(max(compression_ratio, 0.0), 0.95)

        compressed_pack = PromptPack(manifest=pack.manifest, root_path=pack.root_path)

        keep_ratio = 1.0 - ratio
        for rule_name, rule_file in pack.rules.items():
            words = rule_file.content.split()
            if not words:
                compressed_text = ""
            else:
                keep_count = max(1, int(len(words) * keep_ratio))
                compressed_text = " ".join(words[:keep_count])
            compressed_pack.add_rule(
                rule_name, compressed_text, priority=rule_file.priority, enabled=rule_file.enabled
            )

        return compressed_pack

    def inject_with_budget_validation(
        self,
        pack_name: str,
        context: str,
        tool: AITool,
        budget_limit: int,
        include_dependencies: bool = True,
    ) -> Tuple[str, bool]:
        """
        带预算验证的注入

        Args:
            pack_name: Pack 名称
            context: 当前上下文
            tool: 目标 AI 工具
            budget_limit: token 预算限制
            include_dependencies: 是否包含依赖

        Returns:
            (新上下文, 是否有效)
        """
        pack = self.load_pack(pack_name)
        packs = [pack]
        if include_dependencies:
            packs.extend(self.resolve_dependencies(pack))

        is_valid = self.validate_token_budget(packs, budget_limit)
        if not is_valid:
            return context, False

        new_context = self.inject_into_ai_context(pack_name, context, tool)
        return new_context, True
