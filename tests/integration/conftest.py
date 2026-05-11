"""
测试辅助函数

提供创建测试对象的便捷方法，与实际 schema 完全兼容
"""

from datetime import datetime
from typing import List, Optional


def make_pack_metadata(
    pack_id: str,
    pack_name: str,
    description: str = "Test pack",
    version: str = "1.0.0",
    designer: str = "test",
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
):
    """创建有效的 PackMetadata 对象"""
    from ai_collab.pack.schema_v2 import PackMetadata, PackType

    return PackMetadata(
        pack_id=pack_id,
        pack_name=pack_name,
        version=version,
        type=PackType.CUSTOM,
        description=description,
        designer=designer,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        category=category,
        tags=tags or [],
    )


def make_workflow_step(
    step_id: str,
    name: str,
    step_type: str = "local",
    description: str = "",
    input_fields: Optional[List[str]] = None,
    output_field: Optional[str] = None,
):
    """创建 WorkflowStep 对象"""
    from ai_collab.pack.schema_v2 import StepType, WorkflowStep

    type_map = {
        "local": StepType.LOCAL,
        "analysis": StepType.ANALYSIS,
        "generation": StepType.GENERATION,
        "validation": StepType.VALIDATION,
        "fusion": StepType.FUSION,
        "tracking": StepType.TRACKING,
    }

    return WorkflowStep(
        id=step_id,
        name=name,
        type=type_map.get(step_type, StepType.LOCAL),
        description=description,
        input_fields=input_fields or [],
        output_field=output_field,
    )


def make_workflow(steps: Optional[List] = None):
    """创建 WorkflowDefinition 对象"""
    from ai_collab.pack.schema_v2 import WorkflowDefinition

    return WorkflowDefinition(steps=steps or [])


def make_quality_metrics():
    """创建 QualityMetrics 对象"""
    from ai_collab.pack.schema_v2 import QualityMetric, QualityMetrics

    return QualityMetrics(
        metrics={
            "accuracy": QualityMetric(
                name="accuracy", description="准确性", check_method="auto", weight=0.4
            ),
            "completeness": QualityMetric(
                name="completeness", description="完整性", check_method="auto", weight=0.3
            ),
            "relevance": QualityMetric(
                name="relevance", description="相关性", check_method="auto", weight=0.3
            ),
        }
    )


def make_domain():
    """创建 DomainPack 对象"""
    from ai_collab.pack.schema_v2 import DomainPack, TargetPlatform

    return DomainPack(primary_domain="通用", target_platforms=[TargetPlatform.GENERIC])


def make_example_library():
    """创建 ExampleLibrary 对象"""
    from ai_collab.pack.schema_v2 import ExampleLibrary

    return ExampleLibrary()


def make_generation_params():
    """创建 GenerationParams 对象"""
    from ai_collab.pack.schema_v2 import GenerationParams

    return GenerationParams()


def make_optimization():
    """创建 OptimizationRules 对象"""
    from ai_collab.pack.schema_v2 import OptimizationRules

    return OptimizationRules()


def make_performance_tracking():
    """创建 PerformanceTracking 对象"""
    from ai_collab.pack.schema_v2 import PerformanceTracking

    return PerformanceTracking()


def make_collaboration():
    """创建 CollaborationConfig 对象"""
    from ai_collab.pack.schema_v2 import CollaborationConfig

    return CollaborationConfig()


def make_full_pack(
    pack_id: str, pack_name: str, description: str = "Test pack", steps: Optional[List] = None
):
    """创建完整的 PromptPackV2 对象"""
    from ai_collab.pack.schema_v2 import PromptPackV2

    return PromptPackV2(
        metadata=make_pack_metadata(pack_id, pack_name, description),
        domain=make_domain(),
        workflow=make_workflow(steps),
        quality_metrics=make_quality_metrics(),
        example_library=make_example_library(),
        generation_params=make_generation_params(),
        optimization=make_optimization(),
        performance_tracking=make_performance_tracking(),
        collaboration=make_collaboration(),
    )
