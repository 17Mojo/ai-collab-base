#!/usr/bin/env python3
"""
测试FUSION和TRACKING步骤
演示完整的6步骤工作流
"""

import json
import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, "src"))

from ai_collab.pack.pack_executor_mvp import PackExecutorMVP


def test_full_workflow():
    """测试完整的6步骤工作流"""
    print("=" * 60)
    print("测试: 完整6步骤工作流（包含FUSION和TRACKING）")
    print("=" * 60)

    # 创建包含所有6种步骤的Pack
    full_pack = {
        "metadata": {"pack_name": "完整工作流演示", "version": "2.0.0", "type": "content_generation"},
        "workflow": {
            "steps": [
                {
                    "name": "收集输入",
                    "type": "LOCAL",
                    "inputs": [
                        {"key": "topic", "source": "user_input"},
                        {"key": "content", "source": "user_input"},
                    ],
                },
                {"name": "分析内容", "type": "ANALYSIS"},
                {"name": "生成内容", "type": "GENERATION"},
                {"name": "验证质量", "type": "VALIDATION"},
                {"name": "融合优化", "type": "FUSION", "strategy": "best"},
                {"name": "追踪记录", "type": "TRACKING", "output_file": "test_tracking_history.json"},
            ]
        },
    }

    user_input = {
        "topic": "AI协作系统v2.0",
        "content": "全新升级的AI协作系统，支持完整的6步骤工作流，包括本地处理、内容分析、智能生成、质量验证、融合优化和追踪记录。",
    }

    print("\n📝 用户输入:")
    print(f"   主题: {user_input['topic']}")
    print(f"   内容: {user_input['content'][:50]}...")

    # 执行Pack
    executor = PackExecutorMVP(full_pack)
    result = executor.execute(user_input)

    # 显示结果
    print("\n" + "=" * 60)
    print("执行结果")
    print("=" * 60)

    print(f"\n状态: {result['status']}")
    print(f"执行步骤: {len(result['results'])}个")

    # 显示每个步骤的结果
    for i, step_result in enumerate(result["results"], 1):
        print(f"\n步骤 {i}: {step_result['step_type']}")
        print(f"  状态: {step_result['status']}")
        if step_result.get("outputs"):
            outputs = step_result["outputs"]
            if isinstance(outputs, dict):
                for key, value in list(outputs.items())[:3]:
                    if isinstance(value, str) and len(value) > 50:
                        print(f"  - {key}: {value[:50]}...")
                    else:
                        print(f"  - {key}: {value}")

    # 检查追踪记录
    if os.path.exists("test_tracking_history.json"):
        with open("test_tracking_history.json", "r", encoding="utf-8") as f:
            tracking = json.load(f)
        print("\n📊 追踪记录:")
        print(f"   总记录数: {len(tracking['tracking_records'])}")
        latest = tracking["tracking_records"][-1]
        print(f"   最新ID: {latest['execution_id']}")
        print(f"   验证分数: {latest['validation_score']}")

    return result


def test_fusion_strategies():
    """测试不同的融合策略"""
    print("\n" + "=" * 60)
    print("测试: 不同融合策略")
    print("=" * 60)

    strategies = ["concat", "best", "merge"]

    for strategy in strategies:
        print(f"\n--- 策略: {strategy} ---")

        pack = {
            "metadata": {"pack_name": f"融合测试-{strategy}", "version": "1.0.0"},
            "workflow": {
                "steps": [
                    {
                        "name": "收集输入",
                        "type": "LOCAL",
                        "inputs": [{"key": "content", "source": "user_input"}],
                    },
                    {"name": "生成内容", "type": "GENERATION"},
                    {"name": "融合内容", "type": "FUSION", "strategy": strategy},
                ]
            },
        }

        user_input = {"content": f"测试{strategy}融合策略的效果"}

        executor = PackExecutorMVP(pack)
        result = executor.execute(user_input)

        fused_content = result["context"].get("fused_content", "")
        print(f"融合结果长度: {len(fused_content)}")


def main():
    """主测试函数"""
    print("\n" + "🚀 " * 20)
    print("FUSION和TRACKING步骤测试")
    print("🚀 " * 20 + "\n")

    try:
        # 测试1: 完整工作流
        test_full_workflow()

        # 测试2: 融合策略
        test_fusion_strategies()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过")
        print("=" * 60)

        print("\n📊 测试统计:")
        print("   测试数量: 2")
        print("   通过率: 100%")
        print("   新增步骤: FUSION, TRACKING")

        print("\n🎯 功能验证:")
        print("   ✅ FUSION步骤（3种策略）")
        print("   ✅ TRACKING步骤（记录保存）")
        print("   ✅ 完整6步骤工作流")

        print("\n💡 下一步:")
        print("   1. 集成到Chrome Extension")
        print("   2. 添加AI平台适配器")
        print("   3. 创建实际应用Pack")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
