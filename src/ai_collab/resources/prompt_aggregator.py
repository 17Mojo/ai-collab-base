# Prompt资源聚合器
# src/ai_collab/resources/prompt_aggregator.py

"""
Prompt资源聚合器
从多个平台获取优质Prompt并转换为Pack格式
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests


class PromptSource:
    """Prompt来源定义"""

    PROMPTHERO = "prompthero"
    GITHUB_AWESOME = "github_awesome"
    FLOWGPT = "flowgpt"
    PROMPTBASE = "promptbase"
    LOCAL = "local"


class PromptResourceAggregator:
    """Prompt资源聚合器"""

    def __init__(self, cache_dir: str = "cache/prompts"):
        """
        初始化聚合器

        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = cache_dir
        self._ensure_cache_dir()

        # Prompt来源配置
        self.sources = {
            PromptSource.GITHUB_AWESOME: {
                "url": "https://raw.githubusercontent.com/f/awesome-chatgpt-prompts/main/prompts.csv",
                "format": "csv",
                "enabled": True,
            },
            PromptSource.LOCAL: {"path": "prompts/local", "format": "json", "enabled": True},
        }

    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        os.makedirs(self.cache_dir, exist_ok=True)

    def fetch_all_prompts(self) -> List[Dict[str, Any]]:
        """
        从所有来源获取Prompt

        Returns:
            Prompt列表
        """
        all_prompts = []

        for source_name, source_config in self.sources.items():
            if not source_config.get("enabled", False):
                continue

            try:
                print(f"[聚合器] 从 {source_name} 获取Prompt...")
                prompts = self._fetch_from_source(source_name, source_config)
                all_prompts.extend(prompts)
                print(f"[聚合器] 从 {source_name} 获取了 {len(prompts)} 个Prompt")
            except Exception as e:
                print(f"[聚合器] 从 {source_name} 获取失败: {e}")

        return all_prompts

    def _fetch_from_source(self, source_name: str, source_config: Dict) -> List[Dict[str, Any]]:
        """
        从特定来源获取Prompt

        Args:
            source_name: 来源名称
            source_config: 来源配置

        Returns:
            Prompt列表
        """
        if source_name == PromptSource.GITHUB_AWESOME:
            return self._fetch_from_github_awesome(source_config)
        elif source_name == PromptSource.LOCAL:
            return self._fetch_from_local(source_config)
        else:
            return []

    def _fetch_from_github_awesome(self, config: Dict) -> List[Dict[str, Any]]:
        """
        从GitHub Awesome ChatGPT Prompts获取

        Args:
            config: 配置

        Returns:
            Prompt列表
        """
        url = config["url"]

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # 解析CSV格式
            lines = response.text.strip().split("\n")
            prompts = []

            # 跳过标题行
            for line in lines[1:]:
                parts = line.split(",", 1)
                if len(parts) >= 2:
                    title = parts[0].strip('"')
                    content = parts[1].strip('"') if len(parts) > 1 else ""

                    prompts.append(
                        {
                            "title": title,
                            "content": content,
                            "source": PromptSource.GITHUB_AWESOME,
                            "category": "general",
                            "tags": ["chatgpt", "imported"],
                        }
                    )

            return prompts

        except Exception as e:
            print(f"[聚合器] GitHub获取失败: {e}")
            return []

    def _fetch_from_local(self, config: Dict) -> List[Dict[str, Any]]:
        """
        从本地文件获取

        Args:
            config: 配置

        Returns:
            Prompt列表
        """
        path = config["path"]
        prompts = []

        if not os.path.exists(path):
            return prompts

        for filename in os.listdir(path):
            if filename.endswith(".json"):
                filepath = os.path.join(path, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        prompt_data = json.load(f)
                        prompts.append(prompt_data)
                except Exception as e:
                    print(f"[聚合器] 读取本地文件失败 {filename}: {e}")

        return prompts

    def convert_to_pack(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """
        将Prompt转换为Pack格式

        Args:
            prompt: Prompt数据

        Returns:
            Pack格式数据
        """
        pack = {
            "metadata": {
                "pack_name": prompt.get("title", "未命名Pack"),
                "version": "1.0.0",
                "type": "imported",
                "source": prompt.get("source", "unknown"),
                "created_at": datetime.now().isoformat(),
                "tags": prompt.get("tags", []),
            },
            "workflow": {
                "steps": [
                    {
                        "name": "收集输入",
                        "type": "LOCAL",
                        "inputs": [{"key": "topic", "source": "user_input"}],
                    },
                    {
                        "name": "生成内容",
                        "type": "GENERATION",
                        "template": prompt.get("content", ""),
                        "params": {"max_length": 2000},
                    },
                    {"name": "验证质量", "type": "VALIDATION"},
                ]
            },
            "quality_metrics": {
                "coverage": {"weight": 0.3},
                "creativity": {"weight": 0.2},
                "accuracy": {"weight": 0.3},
                "engagement": {"weight": 0.2},
            },
        }

        return pack

    def save_pack(self, pack: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        保存Pack到文件

        Args:
            pack: Pack数据
            filename: 文件名（可选）

        Returns:
            保存的文件路径
        """
        if not filename:
            # 使用Pack名称生成文件名
            pack_name = pack["metadata"]["pack_name"]
            filename = f"{pack_name.replace(' ', '_').lower()}.json"

        # 保存到packs/imported目录
        output_dir = "packs/imported"
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(pack, f, indent=2, ensure_ascii=False)

        print(f"[聚合器] Pack已保存: {filepath}")
        return filepath

    def batch_convert_and_save(self, prompts: List[Dict[str, Any]]) -> List[str]:
        """
        批量转换并保存Pack

        Args:
            prompts: Prompt列表

        Returns:
            保存的文件路径列表
        """
        saved_files = []

        for i, prompt in enumerate(prompts, 1):
            try:
                pack = self.convert_to_pack(prompt)
                filepath = self.save_pack(pack)
                saved_files.append(filepath)
                print(f"[聚合器] 进度: {i}/{len(prompts)}")
            except Exception as e:
                print(f"[聚合器] 转换失败 {prompt.get('title', 'unknown')}: {e}")

        return saved_files

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计数据
        """
        prompts = self.fetch_all_prompts()

        # 按来源统计
        by_source = {}
        for prompt in prompts:
            source = prompt.get("source", "unknown")
            by_source[source] = by_source.get(source, 0) + 1

        # 按类别统计
        by_category = {}
        for prompt in prompts:
            category = prompt.get("category", "general")
            by_category[category] = by_category.get(category, 0) + 1

        return {
            "total_prompts": len(prompts),
            "by_source": by_source,
            "by_category": by_category,
            "last_updated": datetime.now().isoformat(),
        }


# ==================== 便捷函数 ====================


def fetch_and_convert_prompts():
    """获取并转换所有Prompt"""
    aggregator = PromptResourceAggregator()

    # 获取所有Prompt
    prompts = aggregator.fetch_all_prompts()

    # 批量转换并保存
    saved_files = aggregator.batch_convert_and_save(prompts)

    # 获取统计
    stats = aggregator.get_statistics()

    return {"total_prompts": len(prompts), "saved_packs": len(saved_files), "statistics": stats}


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=== Prompt资源聚合器 ===\n")

    # 创建聚合器
    aggregator = PromptResourceAggregator()

    # 获取所有Prompt
    print("步骤1: 获取Prompt...")
    prompts = aggregator.fetch_all_prompts()
    print(f"获取了 {len(prompts)} 个Prompt\n")

    # 转换并保存
    print("步骤2: 转换并保存Pack...")
    saved_files = aggregator.batch_convert_and_save(prompts)
    print(f"保存了 {len(saved_files)} 个Pack\n")

    # 显示统计
    print("步骤3: 统计信息...")
    stats = aggregator.get_statistics()
    print(f"总计: {stats['total_prompts']} 个Prompt")
    print(f"来源分布: {stats['by_source']}")
    print(f"类别分布: {stats['by_category']}")

    print("\n=== 完成 ===")
