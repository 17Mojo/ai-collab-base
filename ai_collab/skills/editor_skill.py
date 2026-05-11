# 编辑Skill - v1.0 MVP核心模块
# src/ai_collab/skills/editor_skill.py

"""
编辑Skill
核心功能：内容生产专家

职责：
1. 内容策划和创作
2. 文字内容生产
3. 内容质量把控
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ai_collab.engines.consensus_engine import ConsensusEngine
from ai_collab.engines.soul_injection_engine import SoulInjectionEngine


class EditorSkill:
    """编辑Skill - 内容生产专家"""

    def __init__(self):
        """初始化编辑Skill"""
        self.name = "编辑"
        self.role = "内容生产专家"
        self.consensus_engine = ConsensusEngine()
        self.soul_engine = SoulInjectionEngine()

        print(f"[{self.name}] 初始化完成")

    async def create_content(self, topic: str, soul_profile: str = "luoyonghao") -> Dict[str, Any]:
        """
        创建内容

        Args:
            topic: 主题
            soul_profile: 灵魂画像

        Returns:
            内容结果
        """
        print(f"\n[{self.name}] 开始创作内容: {topic}")

        # 1. 生成通识
        consensus_result = await self.consensus_engine.generate_consensus(topic)
        consensus = consensus_result["consensus"]

        # 2. 注入灵魂
        soul_result = self.soul_engine.inject_soul(consensus, soul_profile)

        if not soul_result["success"]:
            return {"success": False, "error": soul_result["error"]}

        # 3. 内容优化
        final_content = self._optimize_content(soul_result["personalized_content"])

        # 4. 质量检查
        quality_check = self._quality_check(final_content)

        # 5. 返回结果
        result = {
            "success": True,
            "topic": topic,
            "content": final_content,
            "consensus": consensus,
            "soul_profile": soul_profile,
            "quality": quality_check,
            "timestamp": datetime.now().isoformat(),
            "created_by": self.name,
        }

        print(f"[{self.name}] 内容创作完成")
        return result

    def _optimize_content(self, content: str) -> str:
        """
        优化内容

        Args:
            content: 原始内容

        Returns:
            优化后的内容
        """
        print(f"[{self.name}] 优化内容...")

        # MVP版本：基础格式化
        # 后续版本：AI优化

        # 添加标题
        optimized = f"# 内容创作\n\n{content}"

        # 添加分隔
        optimized += "\n\n---\n\n"

        # 添加元信息
        optimized += f"*由编辑Skill创作于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"

        return optimized

    def _quality_check(self, content: str) -> Dict[str, Any]:
        """
        质量检查

        Args:
            content: 内容

        Returns:
            质量报告
        """
        print(f"[{self.name}] 质量检查...")

        # MVP版本：基础检查
        # 后续版本：多维度质量评估

        checks = {
            "length": len(content),
            "has_title": content.startswith("#"),
            "has_structure": "##" in content or "【" in content,
            "is_complete": len(content) > 100,
        }

        # 计算质量分数
        score = 0
        if checks["length"] > 200:
            score += 25
        if checks["has_title"]:
            score += 25
        if checks["has_structure"]:
            score += 25
        if checks["is_complete"]:
            score += 25

        return {"score": score, "checks": checks, "passed": score >= 75}

    def get_available_souls(self) -> List[str]:
        """获取可用的灵魂画像"""
        return self.soul_engine.list_profiles()

    def get_soul_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取灵魂画像信息"""
        return self.soul_engine.get_profile(name)


# ==================== 便捷函数 ====================


async def create_content(topic: str, soul_profile: str = "luoyonghao") -> Dict[str, Any]:
    """创建内容的便捷函数"""
    editor = EditorSkill()
    return await editor.create_content(topic, soul_profile)


# ==================== 测试代码 ====================


async def test_editor_skill():
    """测试编辑Skill"""
    print("=" * 60)
    print("测试: 编辑Skill")
    print("=" * 60)

    editor = EditorSkill()

    # 测试1: 列出可用画像
    print("\n可用灵魂画像:")
    for soul in editor.get_available_souls():
        info = editor.get_soul_info(soul)
        print(f"  - {info['name']}: {info['style']}")

    # 测试2: 创建内容
    result = await editor.create_content("知识付费", "luoyonghao")

    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)

    if result["success"]:
        print(f"\n主题: {result['topic']}")
        print(f"画像: {result['soul_profile']}")
        print(f"质量分数: {result['quality']['score']}/100")
        print(f"质量检查: {'通过' if result['quality']['passed'] else '未通过'}")
        print(f"\n内容:\n{result['content']}")
    else:
        print(f"错误: {result['error']}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_editor_skill())
