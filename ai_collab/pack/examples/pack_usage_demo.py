"""
Prompt Pack v2.0 使用示例

This file demonstrates how to use the PromptPackV2 schema.
Generated: 2026-02-27 09:12:00
"""

import json
from datetime import datetime

from ai_collab.pack.schema_v2 import (
    CollaborationConfig,
    DomainPack,
    ExampleLibrary,
    GenerationParams,
    OptimizationRules,
    PackMetadata,
    PackType,
    PerformanceTracking,
    PromptPackV2,
    QualityMetric,
    QualityMetrics,
    StepType,
    TargetPlatform,
    WorkflowDefinition,
    WorkflowStep,
    create_xiaohongshu_base,
)


def example_1_basic_xiaohongshu_pack():
    """
    示例 1: 创建基础小红书 Pack
    """
    print("=" * 60)
    print("示例 1: 创建基础小红书 Pack")
    print("=" * 60)

    # 使用 create_xiaohongshu_base() 创建 Pack
    pack = create_xiaohongshu_base()
    print(f"✅ 创建成功: {pack.metadata.pack_name}")
    print(f"   版本: {pack.metadata.version}")
    print(f"   类型: {pack.metadata.type.value}")
    print(f"   质量指标: {list(pack.quality_metrics.metrics.keys())}")
    print()


def example_2_add_workflow_steps():
    """
    示例 2: 添加工作流步骤
    """
    print("=" * 60)
    print("示例 2: 添加工作流步骤")
    print("=" * 60)

    # 创建 Pack，添加多个 WorkflowStep
    pack = create_xiaohongshu_base()

    # 创建步骤
    step1 = WorkflowStep(
        id="step-1",
        name="文案生成",
        type=StepType.GENERATION,
        description="使用多个 AI 生成不同风格的文案",
        ai_models=["qianwen", "zhipu", "kimi"],
        parallel=True,
        output_field="generated_copies",
    )

    step2 = WorkflowStep(
        id="step-2",
        name="质量验证",
        type=StepType.VALIDATION,
        description="对生成的文案进行质量验证",
        cross_review=True,
        validation_criteria=["originality", "attractiveness", "compliance"],
        output_field="validated_copies",
    )

    # 更新工作流
    pack.workflow.steps = [step1, step2]

    print(f"✅ 添加了 {len(pack.workflow.steps)} 个步骤")
    for step in pack.workflow.steps:
        print(f"   - {step.name} ({step.type.value})")
    print()


def example_3_serialization():
    """
    示例 3: 序列化为 JSON
    """
    print("=" * 60)
    print("示例 3: 序列化为 JSON")
    print("=" * 60)

    pack = create_xiaohongshu_base()
    pack_dict = pack.to_dict()
    pack_json = json.dumps(pack_dict, indent=2, default=str)

    print("✅ 序列化成功，JSON 结构：")
    print(json.dumps({k: type(v).__name__ for k, v in pack_dict.items()}, indent=2))
    print(f"   总大小: {len(pack_json)} 字符")
    print()


def example_4_deserialization():
    """
    示例 4: 从 JSON 反序列化
    """
    print("=" * 60)
    print("示例 4: 从 JSON 反序列化")
    print("=" * 60)

    # 创建原始 Pack
    pack_original = create_xiaohongshu_base()

    # 序列化
    pack_dict = pack_original.to_dict()

    # 反序列化
    pack_restored = PromptPackV2.from_dict(pack_dict)

    print("✅ 反序列化成功")
    print(f"   原始 Pack: {pack_original.metadata.pack_name}")
    print(f"   恢复 Pack: {pack_restored.metadata.pack_name}")
    print(f"   质量指标匹配: {pack_original.metadata.pack_id == pack_restored.metadata.pack_id}")
    print()


def example_5_validation():
    """
    示例 5: 验证 Pack 完整性
    """
    print("=" * 60)
    print("示例 5: 验证 Pack 完整性")
    print("=" * 60)

    pack = create_xiaohongshu_base()

    # 添加工作流步骤使其有效
    step = WorkflowStep(id="step-1", name="示例步骤", type=StepType.ANALYSIS, output_field="output")
    pack.workflow.steps = [step]

    is_valid = pack.validate()

    print(f"✅ 验证结果: {'通过' if is_valid else '失败'}")
    print(f"   元数据完整: {bool(pack.metadata.pack_id and pack.metadata.pack_name)}")
    print(f"   工作流有步骤: {len(pack.workflow.steps) > 0}")
    print(f"   质量权重和: {pack.quality_metrics.get_total_weight():.2f}")
    print()


def example_6_quality_metrics_analysis():
    """
    示例 6: 质量指标分析
    """
    print("=" * 60)
    print("示例 6: 质量指标分析")
    print("=" * 60)

    pack = create_xiaohongshu_base()

    print("✅ 质量指标分析:")
    for name, metric in pack.quality_metrics.metrics.items():
        print(f"   {name}:")
        print(f"     描述: {metric.description}")
        print(f"     权重: {metric.weight:.2%}")
        print(f"     最低阈值: {metric.min_threshold:.0%}")

    total_weight = pack.quality_metrics.get_total_weight()
    print(f"\n   权重总和: {total_weight:.4f} (应为 1.0000)")
    print()


def example_7_custom_pack():
    """
    示例 7: 创建自定义 Pack
    """
    print("=" * 60)
    print("示例 7: 创建完全自定义的 Pack")
    print("=" * 60)

    # TODO: 实现此示例
    # 从头创建一个 Pack

    metadata = PackMetadata(
        pack_id="custom-pack-001",
        pack_name="自定义 Pack 示例",
        version="1.0.0",
        type=PackType.ANALYSIS,
        description="这是一个完全自定义的 Pack",
        designer="Custom Designer",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=["custom", "example"],
    )

    domain = DomainPack(primary_domain="数据分析", target_platforms=[TargetPlatform.GENERIC])

    metrics = QualityMetrics(
        metrics={
            "accuracy": QualityMetric(
                name="accuracy", description="分析准确度", check_method="validation", weight=0.6
            ),
            "completeness": QualityMetric(
                name="completeness", description="分析完整度", check_method="coverage", weight=0.4
            ),
        }
    )

    pack = PromptPackV2(
        metadata=metadata,
        domain=domain,
        workflow=WorkflowDefinition(steps=[]),
        quality_metrics=metrics,
        example_library=ExampleLibrary(),
        generation_params=GenerationParams(),
        optimization=OptimizationRules(),
        performance_tracking=PerformanceTracking(),
        collaboration=CollaborationConfig(),
    )

    print("✅ 自定义 Pack 创建成功")
    print(f"   ID: {pack.metadata.pack_id}")
    print(f"   名称: {pack.metadata.pack_name}")
    print(f"   质量指标: {list(pack.quality_metrics.metrics.keys())}")
    print()


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "Prompt Pack v2.0 使用示例集合" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    # 运行所有示例
    example_1_basic_xiaohongshu_pack()
    example_2_add_workflow_steps()
    example_3_serialization()
    example_4_deserialization()
    example_5_validation()
    example_6_quality_metrics_analysis()
    example_7_custom_pack()

    print()
    print("=" * 60)
    print("✅ 所有示例运行完成！")
    print("=" * 60)
    print()

    # 总结
    print("📋 下一步:")
    print("   1. 运行此示例: python examples/pack_usage_demo.py")
    print("   2. 查看输出")
    print("   3. 修改示例尝试其他功能")
    print("   4. 阅读 schema_v2.README.md 了解更多详情")
    print()
