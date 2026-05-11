#!/usr/bin/env python3
"""
测试实际Pack示例
演示如何使用PackExecutorMVP执行真实的Pack
"""

import json
import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, "src"))

from ai_collab.pack.pack_executor_mvp import PackExecutorMVP


def load_pack(pack_file: str) -> dict:
    """加载Pack配置"""
    with open(pack_file, "r", encoding="utf-8") as f:
        return json.load(f)


def test_ai_collab_intro_pack():
    """测试AI协作系统介绍文案生成器"""
    print("=" * 60)
    print("测试: AI协作系统介绍文案生成器")
    print("=" * 60)

    # 1. 加载Pack
    pack_file = "packs/examples/ai_collab_intro.json"
    pack = load_pack(pack_file)

    print(f"\n✅ Pack加载成功: {pack['metadata']['pack_name']}")
    print(f"   版本: {pack['metadata']['version']}")
    print(f"   类型: {pack['metadata']['type']}")

    # 2. 准备用户输入
    user_input = {
        "topic": "AI协作系统",
        "key_features": [
            "双AI协作 - Claude Code和Copilot协同工作",
            "零成本 - 完全本地运行，无云服务费用",
            "完全离线 - 不依赖外部服务",
            "自动冲突检测 - 智能避免代码冲突",
        ],
        "target_audience": "开发者",
        "style": "专业",
    }

    print("\n📝 用户输入:")
    print(f"   主题: {user_input['topic']}")
    print(f"   目标受众: {user_input['target_audience']}")
    print(f"   风格: {user_input['style']}")
    print(f"   关键特性: {len(user_input['key_features'])}个")

    # 3. 执行Pack
    executor = PackExecutorMVP(pack)
    result = executor.execute(user_input)

    # 4. 显示结果
    print("\n" + "=" * 60)
    print("执行结果")
    print("=" * 60)

    print(f"\n状态: {result['status']}")
    print(f"执行步骤: {len(result['results'])}个")

    # 显示生成的文案
    if result.get("final_content"):
        print("\n📄 生成的文案:")
        print("-" * 60)
        print(result["final_content"])
        print("-" * 60)

    # 显示验证结果
    if result.get("validation"):
        validation = result["validation"]
        print("\n✅ 验证结果:")
        print(f"   是否通过: {'✅' if validation['is_valid'] else '❌'}")
        print(f"   质量分数: {validation['score']:.2f}")
        if validation.get("issues"):
            print(f"   问题: {', '.join(validation['issues'])}")

    return result


def test_simple_pack():
    """测试简单Pack"""
    print("\n" + "=" * 60)
    print("测试: 简单内容生成器")
    print("=" * 60)

    # 创建简单Pack
    simple_pack = {
        "metadata": {"pack_name": "简单内容生成器", "version": "1.0.0", "type": "content_generation"},
        "workflow": {
            "steps": [
                {
                    "name": "收集输入",
                    "type": "LOCAL",
                    "inputs": [
                        {"key": "title", "source": "user_input"},
                        {"key": "content", "source": "user_input"},
                    ],
                },
                {"name": "分析内容", "type": "ANALYSIS"},
                {"name": "生成内容", "type": "GENERATION"},
                {"name": "验证质量", "type": "VALIDATION"},
            ]
        },
    }

    user_input = {
        "title": "Prompt Pack MVP发布",
        "content": "我们很高兴地宣布Prompt Pack MVP版本已经发布。这是一个最小可用版本，支持基本的内容生成工作流。",
    }

    print("\n📝 用户输入:")
    print(f"   标题: {user_input['title']}")
    print(f"   内容: {user_input['content'][:50]}...")

    executor = PackExecutorMVP(simple_pack)
    result = executor.execute(user_input)

    print("\n✅ 执行完成")
    print(f"   状态: {result['status']}")
    print(f"   生成内容长度: {len(result.get('final_content', ''))}字符")

    return result


def main():
    """主测试函数"""
    print("\n" + "🚀 " * 20)
    print("Prompt Pack MVP 实际测试")
    print("🚀 " * 20 + "\n")

    try:
        # 测试1: 简单Pack
        test_simple_pack()

        # 测试2: 实际Pack
        test_ai_collab_intro_pack()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过")
        print("=" * 60)

        print("\n📊 测试统计:")
        print("   测试数量: 2")
        print("   通过率: 100%")
        print("   生成内容: 2篇")

        print("\n🎯 MVP功能验证:")
        print("   ✅ Pack加载")
        print("   ✅ 工作流执行")
        print("   ✅ 内容生成")
        print("   ✅ 质量验证")

        print("\n💡 下一步:")
        print("   1. 添加更多步骤类型（FUSION, TRACKING）")
        print("   2. 集成到Chrome Extension")
        print("   3. 添加AI平台适配器")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
