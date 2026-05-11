# 独立测试 Skill - 无外部依赖
# src/ai_collab/skills/simple_skill.py

"""
简单测试 Skill
用于测试 Skills 到 Pack 转换功能

职责:
1. 简单的计算操作
2. 无外部依赖
"""

from datetime import datetime
from typing import Any, Dict, List


class SimpleSkill:
    """简单测试 Skill"""

    def __init__(self):
        """初始化 Simple Skill"""
        self.name = "简单计算器"
        self.version = "1.0.0"
        print(f"[{self.name}] 初始化完成")

    def calculate_sum(self, numbers: List[int]) -> int:
        """
        计算数字总和

        Args:
            numbers: 数字列表

        Returns:
            总和
        """
        return sum(numbers)

    def calculate_average(self, numbers: List[int]) -> float:
        """
        计算数字平均值

        Args:
            numbers: 数字列表

        Returns:
            平均值
        """
        if not numbers:
            return 0.0
        return sum(numbers) / len(numbers)

    def find_max(self, numbers: List[int]) -> int:
        """
        找出最大值

        Args:
            numbers: 数字列表

        Returns:
            最大值
        """
        if not numbers:
            return 0
        return max(numbers)

    def find_min(self, numbers: List[int]) -> int:
        """
        找出最小值

        Args:
            numbers: 数字列表

        Returns:
            最小值
        """
        if not numbers:
            return 0
        return min(numbers)


# ==================== 便捷函数 ====================


def calculate_numbers_stats(numbers: List[int]) -> Dict[str, Any]:
    """计算数字统计信息的便捷函数"""
    skill = SimpleSkill()
    return {
        "sum": skill.calculate_sum(numbers),
        "average": skill.calculate_average(numbers),
        "max": skill.find_max(numbers),
        "min": skill.find_min(numbers),
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    # 测试 Simple Skill
    print("=" * 60)
    print("测试: Simple Skill")
    print("=" * 60)

    skill = SimpleSkill()

    test_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    print(f"\n测试数字: {test_numbers}")
    print(f"总和: {skill.calculate_sum(test_numbers)}")
    print(f"平均值: {skill.calculate_average(test_numbers)}")
    print(f"最大值: {skill.find_max(test_numbers)}")
    print(f"最小值: {skill.find_min(test_numbers)}")

    stats = calculate_numbers_stats(test_numbers)
    print(f"\n完整统计: {stats}")
