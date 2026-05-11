"""
Pack Schema v2.0 单元测试
"""

import os
import sys
from datetime import datetime

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ai_collab.pack.schema_v2 import (
    ExampleLibrary,
    PackExample,
    PackMetadata,
    PackType,
    PromptPackV2,
    QualityMetric,
    QualityMetrics,
    StepType,
    WorkflowDefinition,
    WorkflowStep,
    create_xiaohongshu_base,
)


class TestPackMetadata:
    """PackMetadata 测试"""

    def test_create_metadata(self):
        """测试创建元数据"""
        metadata = PackMetadata(
            pack_id="test-pack-001",
            pack_name="测试 Pack",
            version="1.0.0",
            type=PackType.CUSTOM,
            description="测试用 Pack",
            designer="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert metadata.pack_id == "test-pack-001"
        assert metadata.pack_name == "测试 Pack"
        assert metadata.version == "1.0.0"
        assert metadata.type == PackType.CUSTOM

    def test_metadata_with_optional_fields(self):
        """测试带可选字段的元数据"""
        metadata = PackMetadata(
            pack_id="test-pack-002",
            pack_name="测试 Pack 2",
            version="2.0.0",
            type=PackType.BUSINESS,
            description="测试用 Pack 2",
            designer="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            category="内容运营",
            tags=["测试", "示例"],
            language="zh",
        )

        assert metadata.category == "内容运营"
        assert "测试" in metadata.tags
        assert metadata.language == "zh"


class TestWorkflowStep:
    """WorkflowStep 测试"""

    def test_create_step(self):
        """测试创建工作流步骤"""
        step = WorkflowStep(id="step_1", name="测试步骤", type=StepType.LOCAL, description="这是一个测试步骤")

        assert step.id == "step_1"
        assert step.name == "测试步骤"
        assert step.type == StepType.LOCAL
        assert step.parallel is False

    def test_step_with_ai_models(self):
        """测试带 AI 模型的步骤"""
        step = WorkflowStep(
            id="step_2",
            name="AI 分析步骤",
            type=StepType.ANALYSIS,
            ai_models=["qianwen", "zhipu"],
            parallel=True,
        )

        assert step.ai_models == ["qianwen", "zhipu"]
        assert step.parallel is True

    def test_all_step_types(self):
        """测试所有步骤类型"""
        step_types = [
            StepType.LOCAL,
            StepType.ANALYSIS,
            StepType.GENERATION,
            StepType.VALIDATION,
            StepType.FUSION,
            StepType.TRACKING,
        ]

        for step_type in step_types:
            step = WorkflowStep(
                id=f"step_{step_type.value}", name=f"{step_type.value}步骤", type=step_type
            )
            assert step.type == step_type


class TestWorkflowDefinition:
    """WorkflowDefinition 测试"""

    def test_create_workflow(self):
        """测试创建工作流"""
        steps = [
            WorkflowStep(id="step_1", name="步骤1", type=StepType.LOCAL),
            WorkflowStep(id="step_2", name="步骤2", type=StepType.ANALYSIS),
        ]

        workflow = WorkflowDefinition(steps=steps, max_parallel_steps=5)

        assert len(workflow.steps) == 2
        assert workflow.max_parallel_steps == 5
        assert workflow.allow_parallel is True

    def test_get_step_success(self):
        """测试获取步骤 - 成功"""
        steps = [
            WorkflowStep(id="step_1", name="步骤1", type=StepType.LOCAL),
            WorkflowStep(id="step_2", name="步骤2", type=StepType.ANALYSIS),
        ]

        workflow = WorkflowDefinition(steps=steps)
        step = workflow.get_step("step_2")

        assert step is not None
        assert step.id == "step_2"

    def test_get_step_not_found(self):
        """测试获取步骤 - 未找到"""
        steps = [WorkflowStep(id="step_1", name="步骤1", type=StepType.LOCAL)]
        workflow = WorkflowDefinition(steps=steps)

        step = workflow.get_step("nonexistent")

        assert step is None


class TestQualityMetrics:
    """QualityMetrics 测试"""

    def test_create_quality_metrics(self):
        """测试创建质量指标"""
        metrics = QualityMetrics(
            metrics={
                "accuracy": QualityMetric(
                    name="accuracy", description="准确性", check_method="fact_check", weight=0.5
                ),
                "fluency": QualityMetric(
                    name="fluency", description="流畅性", check_method="fluency_check", weight=0.5
                ),
            }
        )

        assert "accuracy" in metrics.metrics
        assert metrics.get_total_weight() == 1.0

    def test_weight_validation(self):
        """测试权重总和验证"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(
                    name="m1", description="指标1", check_method="check1", weight=0.3
                ),
                "m2": QualityMetric(
                    name="m2", description="指标2", check_method="check2", weight=0.3
                ),
            }
        )

        # 权重总和不是 1.0
        assert abs(metrics.get_total_weight() - 0.6) < 0.01

    def test_validate_weights_true(self):
        """测试权重总和验证 - 有效"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(
                    name="m1", description="指标1", check_method="check1", weight=0.5
                ),
                "m2": QualityMetric(
                    name="m2", description="指标2", check_method="check2", weight=0.5
                ),
            }
        )

        assert metrics.validate_weights() is True

    def test_validate_weights_false(self):
        """测试权重总和验证 - 无效"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(
                    name="m1", description="指标1", check_method="check1", weight=0.3
                ),
                "m2": QualityMetric(
                    name="m2", description="指标2", check_method="check2", weight=0.3
                ),
            }
        )

        assert metrics.validate_weights() is False

    def test_get_normalized_weights_linear(self):
        """测试线性归一化"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(
                    name="m1", description="指标1", check_method="check1", weight=0.5
                ),
                "m2": QualityMetric(
                    name="m2", description="指标2", check_method="check2", weight=0.2
                ),
                "m3": QualityMetric(
                    name="m3", description="指标3", check_method="check3", weight=0.3
                ),
            },
            normalization_method="linear",
        )

        normalized = metrics.get_normalized_weights()
        assert abs(sum(normalized.values()) - 1.0) < 0.01

    def test_get_normalized_weights_minmax(self):
        """测试 MinMax 归一化"""
        metrics = QualityMetrics(
            metrics={
                "low": QualityMetric(
                    name="low", description="低", check_method="check1", weight=0.1
                ),
                "mid": QualityMetric(
                    name="mid", description="中", check_method="check2", weight=0.5
                ),
                "high": QualityMetric(
                    name="high", description="高", check_method="check3", weight=0.9
                ),
            },
            normalization_method="minmax",
        )

        normalized = metrics.get_normalized_weights()
        assert abs(sum(normalized.values()) - 1.0) < 0.01

    def test_get_normalized_weights_equal_minmax(self):
        """测试 MinMax 归一化 - 权重相等"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(
                    name="m1", description="指标1", check_method="check1", weight=0.5
                ),
                "m2": QualityMetric(
                    name="m2", description="指标2", check_method="check2", weight=0.5
                ),
            },
            normalization_method="minmax",
        )

        normalized = metrics.get_normalized_weights()
        assert normalized["m1"] == 0.5
        assert normalized["m2"] == 0.5

    def test_get_normalized_weights_zscore(self):
        """测试 Z-score 归一化"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(
                    name="m1", description="指标1", check_method="check1", weight=0.3
                ),
                "m2": QualityMetric(
                    name="m2", description="指标2", check_method="check2", weight=0.5
                ),
                "m3": QualityMetric(
                    name="m3", description="指标3", check_method="check3", weight=0.7
                ),
            },
            normalization_method="zscore",
        )

        normalized = metrics.get_normalized_weights()
        assert abs(sum(normalized.values()) - 1.0) < 0.01

    def test_get_normalized_weights_zero_total(self):
        """测试零总权重归一化"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(
                    name="m1", description="指标1", check_method="check1", weight=0.0
                ),
            }
        )

        normalized = metrics.get_normalized_weights()
        assert normalized == {"m1": 0.0}

    def test_adjust_weight_success(self):
        """测试权重调整 - 成功"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(
                    name="m1", description="指标1", check_method="check1", weight=0.3
                ),
                "m2": QualityMetric(
                    name="m2", description="指标2", check_method="check2", weight=0.7
                ),
            }
        )

        result = metrics.adjust_weight("m1", 0.5)
        assert result is True
        assert metrics.metrics["m1"].weight == 0.5
        assert abs(metrics.get_total_weight() - 1.0) < 0.01

    def test_adjust_weight_invalid_metric(self):
        """测试权重调整 - 无效指标"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(name="m1", description="指标1", check_method="check1", weight=1.0)
            }
        )

        result = metrics.adjust_weight("nonexistent", 0.5)
        assert result is False

    def test_adjust_weight_invalid_range(self):
        """测试权重调整 - 超出范围"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(name="m1", description="指标1", check_method="check1", weight=1.0)
            }
        )

        result = metrics.adjust_weight("m1", 1.5)
        assert result is False

    def test_add_metric(self):
        """测试添加指标"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(name="m1", description="指标1", check_method="check1", weight=0.5)
            }
        )

        new_metric = QualityMetric(name="m2", description="指标2", check_method="check2", weight=0.3)
        result = metrics.add_metric(new_metric, redistribute=True)

        assert result is True
        assert "m2" in metrics.metrics

    def test_add_metric_duplicate(self):
        """测试添加重复指标"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(name="m1", description="指标1", check_method="check1", weight=1.0)
            }
        )

        duplicate = QualityMetric(name="m1", description="指标1", check_method="check1", weight=0.5)
        result = metrics.add_metric(duplicate, redistribute=False)

        assert result is False

    def test_remove_metric(self):
        """测试移除指标"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(
                    name="m1", description="指标1", check_method="check1", weight=0.5
                ),
                "m2": QualityMetric(
                    name="m2", description="指标2", check_method="check2", weight=0.5
                ),
            }
        )

        result = metrics.remove_metric("m1", redistribute=True)

        assert result is True
        assert "m1" not in metrics.metrics
        assert abs(metrics.get_total_weight() - 1.0) < 0.01

    def test_remove_metric_nonexistent(self):
        """测试移除不存在的指标"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(name="m1", description="指标1", check_method="check1", weight=1.0)
            }
        )

        result = metrics.remove_metric("nonexistent", redistribute=False)

        assert result is False

    def test_calculate_quality_score_all_metrics(self):
        """测试质量分数计算 - 所有指标都有分数"""
        metrics = QualityMetrics(
            metrics={
                "accuracy": QualityMetric(
                    name="accuracy",
                    description="准确性",
                    check_method="check1",
                    weight=0.6,
                    min_threshold=0.7,
                ),
                "fluency": QualityMetric(
                    name="fluency",
                    description="流畅性",
                    check_method="check2",
                    weight=0.4,
                    min_threshold=0.6,
                ),
            }
        )

        scores = {"accuracy": 85.0, "fluency": 90.0}
        result = metrics.calculate_quality_score(scores)

        assert 0 <= result <= 100

    def test_calculate_quality_score_with_min_threshold(self):
        """测试质量分数计算 - 应用最小阈值"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(
                    name="m1",
                    description="指标1",
                    check_method="check1",
                    weight=0.5,
                    min_threshold=0.8,
                ),
            }
        )

        scores = {"m1": 60.0}  # 低于阈值
        result = metrics.calculate_quality_score(scores)

        # 应用阈值: max(60, 80) = 80
        assert result == 80.0

    def test_calculate_quality_score_missing_metric(self):
        """测试质量分数计算 - 缺指标给0分"""
        metrics = QualityMetrics(
            metrics={
                "m1": QualityMetric(
                    name="m1", description="指标1", check_method="check1", weight=0.5
                ),
                "m2": QualityMetric(
                    name="m2", description="指标2", check_method="check2", weight=0.5
                ),
            }
        )

        scores = {"m1": 80.0}  # 缺少 m2
        result = metrics.calculate_quality_score(scores)

        # 只有 m1 有效，m2 给0
        assert result == 40.0


class TestPromptPackV2:
    """PromptPackV2 完整测试"""

    def test_create_pack(self):
        """测试创建完整 Pack"""
        pack = create_xiaohongshu_base()

        assert pack.metadata.pack_id == "xiaohongshu-explosive-copy"
        assert pack.metadata.pack_name == "小红书爆文生成包"
        assert pack.domain.primary_domain == "小红书运营"

    def test_pack_to_dict(self):
        """测试 Pack 序列化"""
        pack = create_xiaohongshu_base()
        data = pack.to_dict()

        assert "metadata" in data
        assert "domain" in data
        assert "workflow" in data
        assert "quality_metrics" in data
        assert data["metadata"]["pack_id"] == "xiaohongshu-explosive-copy"

    def test_pack_from_dict(self):
        """测试 Pack 反序列化"""
        pack = create_xiaohongshu_base()
        data = pack.to_dict()

        restored = PromptPackV2.from_dict(data)

        assert restored.metadata.pack_id == pack.metadata.pack_id
        assert restored.metadata.pack_name == pack.metadata.pack_name

    def test_pack_validation(self):
        """测试 Pack 验证"""
        pack = create_xiaohongshu_base()

        # 没有工作流步骤，验证失败
        assert pack.validate() is False

        # 添加步骤后验证
        pack.workflow.steps.append(WorkflowStep(id="step_1", name="测试步骤", type=StepType.LOCAL))

        # 添加步骤后，且质量权重总和为 1.0，验证应通过
        assert pack.validate() is True

    def test_pack_validation_empty_pack_id(self):
        """测试 Pack 验证 - 空 pack_id"""
        pack = create_xiaohongshu_base()
        pack.metadata.pack_id = ""

        assert pack.validate() is False

    def test_pack_validation_empty_name(self):
        """测试 Pack 验证 - 空 pack_name"""
        pack = create_xiaohongshu_base()
        pack.metadata.pack_name = ""

        assert pack.validate() is False

    def test_pack_from_dict_with_optional_fields(self):
        """测试从字典加载 Pack - 带可选字段"""
        data = {
            "metadata": {
                "pack_id": "full-test-pack",
                "pack_name": "完整测试Pack",
                "version": "1.0.0",
                "type": "business",
                "description": "完整测试",
                "designer": "Test",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "category": "测试分类",
                "tags": ["tag1", "tag2"],
                "language": "zh",
                "estimated_efficiency_gain": "70%",
            },
            "domain": {
                "primary_domain": "测试领域",
                "secondary_domains": ["领域1", "领域2"],
                "target_platforms": ["generic"],
                "target_audience": "测试用户",
                "brand_tone": "专业",
                "compliance_rules": ["规则1"],
            },
            "workflow": {
                "steps": [{"id": "step_1", "name": "步骤1", "type": "local", "description": "描述"}],
                "max_parallel_steps": 3,
                "allow_parallel": True,
            },
            "quality_metrics": {
                "metrics": {
                    "m1": {
                        "description": "测试指标",
                        "check_method": "check",
                        "weight": 1.0,
                        "min_threshold": 0.0,
                    }
                },
                "normalization_method": "linear",
                "validation_tolerance": 0.01,
            },
            "example_library": {"good_examples": [], "bad_examples": [], "few_shot_template": ""},
            "generation_params": {
                "diversity_enhancement": True,
                "output_versions": 3,
                "diversity_dimensions": ["test"],
                "confidence_display": True,
                "critical_facts_only": True,
                "temperature": 0.7,
                "output_format": "markdown",
                "require_code_blocks": False,
            },
            "optimization": {
                "enabled": True,
                "strategy": "feedback_driven",
                "auto_refine_threshold": 60.0,
                "periodic_review_days": 30,
                "allowed_actions": ["action1"],
            },
            "performance_tracking": {
                "enabled": True,
                "metrics": ["metric1"],
                "retention_days": 90,
                "post_publish_tracking": None,
            },
            "collaboration": {
                "shared_with": ["user1"],
                "edit_permission": [],
                "use_permission": [],
                "is_public": False,
            },
            "system_prompt": "测试提示词",
            "quality_validation_rules": "验证规则",
        }

        pack = PromptPackV2.from_dict(data)

        assert pack.metadata.pack_id == "full-test-pack"
        assert pack.metadata.category == "测试分类"
        assert "tag1" in pack.metadata.tags
        assert pack.system_prompt == "测试提示词"

    def test_all_pack_types(self):
        """测试所有 Pack 类型"""
        pack_types = [
            PackType.PRODUCTIVITY,
            PackType.CREATIVE,
            PackType.ANALYSIS,
            PackType.BUSINESS,
            PackType.EDUCATION,
            PackType.CUSTOM,
        ]

        for ptype in pack_types:
            pack = create_xiaohongshu_base()
            pack.metadata.type = ptype

            assert pack.metadata.type == ptype


class TestExampleLibrary:
    """ExampleLibrary 测试"""

    def test_add_examples(self):
        """测试添加示例"""
        library = ExampleLibrary()

        good_example = PackExample(
            id="ex_1", input={"topic": "测试"}, output="测试输出", description="好的示例", score=90.0
        )

        bad_example = PackExample(
            id="ex_2", input={"topic": "测试"}, output="不好的输出", description="差的示例", score=30.0
        )

        library.add_good_example(good_example)
        library.add_bad_example(bad_example)

        assert len(library.good_examples) == 1
        assert len(library.bad_examples) == 1


class TestBoundaryScenarios:
    """边界场景测试"""

    def test_empty_metadata_fields(self):
        """测试空值边界场景 - 元数据字段为空"""
        # PackMetadata 是 dataclass，不会自动验证空值
        # 但 Pack.validate() 会检查
        metadata = PackMetadata(
            pack_id="",  # 空 pack_id
            pack_name="Test Pack",
            version="1.0.0",
            type=PackType.CUSTOM,
            description="Test",
            designer="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        pack = create_xiaohongshu_base()
        pack.metadata = metadata

        # Pack.validate() 应该检查空 pack_id 并返回 False
        assert pack.validate() is False

    def test_extra_long_string_fields(self):
        """测试超长字符串字段"""
        long_string = "x" * 10000  # 超长字符串

        metadata = PackMetadata(
            pack_id="test-pack-003",
            pack_name="Test Pack 3",
            version="1.0.0",
            type=PackType.BUSINESS,
            description=long_string,
            designer="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert len(metadata.description) == 10000

    def test_special_characters_in_fields(self):
        """测试特殊字符处理"""
        special_chars = "<script>alert('xss')</script> & \" ' \n \t \r \\ /"

        pack = create_xiaohongshu_base()
        pack.metadata.pack_name = pack.metadata.pack_name + special_chars
        pack.system_prompt = special_chars

        data = pack.to_dict()

        # 特殊字符应被正确序列化
        assert special_chars in data["metadata"]["pack_name"]
        assert special_chars in data["system_prompt"]

    def test_negative_quality_weight(self):
        """测试负权重质量指标"""
        metrics = QualityMetrics(
            metrics={
                "negative": QualityMetric(
                    name="negative", description="负权重指标", check_method="check", weight=-0.5  # 负权重
                )
            }
        )

        # 验证负权重
        assert metrics.get_total_weight() == -0.5

    def test_weight_exceed_one(self):
        """测试超过1的单一权重"""
        metrics = QualityMetrics(
            metrics={
                "large": QualityMetric(
                    name="large", description="大权重指标", check_method="check", weight=1.5  # 超过1
                )
            }
        )

        # 验证大权重
        assert metrics.get_total_weight() == 1.5

    def test_duplicate_step_ids(self):
        """测试重复步骤ID"""
        steps = [
            WorkflowStep(id="step_1", name="步骤1", type=StepType.LOCAL),
            WorkflowStep(id="step_1", name="步骤2", type=StepType.ANALYSIS),  # 重复ID
        ]

        workflow = WorkflowDefinition(steps=steps)
        pack = create_xiaohongshu_base()
        pack.workflow = workflow

        # 验证应失败（重复步骤ID）
        assert pack.validate() is False

    def test_many_workflow_steps(self):
        """测试大量工作流步骤"""

        steps = [
            WorkflowStep(id=f"step_{i}", name=f"步骤{i}", type=StepType.LOCAL)
            for i in range(100)  # 100个步骤
        ]

        workflow = WorkflowDefinition(steps=steps, max_parallel_steps=10)
        pack = create_xiaohongshu_base()
        pack.workflow = workflow

        data = pack.to_dict()
        assert len(data["workflow"]["steps"]) == 100


class TestPerformance:
    """性能测试"""

    def test_large_pack_serialization_time(self):
        """测试大型Pack序列化 - 验证性能可接受"""

        import time

        # 创建大型Pack
        pack = create_xiaohongshu_base()

        # 添加大量工作流步骤
        pack.workflow.steps = [
            WorkflowStep(
                id=f"step_{i}",
                name=f"测试步骤{i}",
                type=StepType.GENERATION,
                ai_models=["qianwen", "zhipu", "kimi"],
                parallel=True,
                input_fields=["input1", "input2", "input3"],
                output_field=f"output_{i}",
                config={"test": "data"},
            )
            for i in range(50)
        ]

        # 添加大量示例
        for i in range(100):
            pack.example_library.add_good_example(
                PackExample(
                    id=f"ex_{i}",
                    input={"topic": f"测试主题{i}"},
                    output=f"测试输出{i}" * 10,
                    description=f"示例{i}",
                    score=85.0,
                )
            )

        # 测量序列化时间
        start = time.time()
        data = pack.to_dict()
        elapsed = time.time() - start

        # 验证结果
        assert len(data["workflow"]["steps"]) == 50
        assert len(data["example_library"]["good_examples"]) == 100
        # 性能验证：应该在合理时间内完成 (<1秒)
        assert elapsed < 1.0, f"序列化耗时 {elapsed:.3f}s，超过预期"

    def test_large_pack_deserialization_time(self):
        """测试大型Pack反序列化 - 验证性能可接受"""

        import time

        # 先创建序列化数据
        pack = create_xiaohongshu_base()
        pack.workflow.steps = [
            WorkflowStep(
                id=f"step_{i}",
                name=f"步骤{i}",
                type=StepType.GENERATION,
                ai_models=["qianwen", "zhipu"],
                parallel=True,
            )
            for i in range(50)
        ]

        for i in range(100):
            pack.example_library.add_good_example(
                PackExample(
                    id=f"ex_{i}",
                    input={"topic": f"测试{i}"},
                    output=f"输出{i}" * 10,
                    description=f"示例{i}",
                    score=90.0,
                )
            )

        serialized_data = pack.to_dict()

        # 测量反序列化时间
        start = time.time()
        restored = PromptPackV2.from_dict(serialized_data)
        elapsed = time.time() - start

        # 验证结果
        assert restored.metadata.pack_id == pack.metadata.pack_id
        assert len(restored.workflow.steps) == 50
        # 性能验证：应该在合理时间内完成 (<1秒)
        assert elapsed < 1.0, f"反序列化耗时 {elapsed:.3f}s，超过预期"

    def test_calculate_quality_score_time(self):
        """测试质量计算 - 验证性能可接受"""

        import time

        # 创建复杂的质量指标集
        metrics = QualityMetrics(
            metrics={
                f"metric_{i}": QualityMetric(
                    name=f"metric_{i}",
                    description=f"指标{i}",
                    check_method=f"check_{i}",
                    weight=1.0 / 20,
                )
                for i in range(20)
            }
        )

        scores = {f"metric_{i}": 85.0 for i in range(20)}

        # 测量计算时间（多次取平均）
        times = []
        for _ in range(10):
            start = time.time()
            result = metrics.calculate_quality_score(scores)
            elapsed = time.time() - start
            times.append(elapsed)

            assert 0 <= result <= 100

        avg_time = sum(times) / len(times)

        # 性能验证：每次计算应该在合理时间内完成 (<10ms)
        assert avg_time < 0.01, f"平均计算耗时 {avg_time*1000:.2f}ms，超过预期"

    def test_weight_adjustment_time(self):
        """测试权重调整 - 验证性能可接受"""

        import time

        metrics = QualityMetrics(
            metrics={
                f"m{i}": QualityMetric(
                    name=f"m{i}", description=f"指标{i}", check_method="check", weight=1.0 / 50
                )
                for i in range(50)
            }
        )

        # 测量调整多个权重的时间
        start = time.time()
        for i in range(50):
            new_weight = (i + 1) / 1275.0  # 确保总和为1
            metrics.adjust_weight(f"m{i}", new_weight)
        elapsed = time.time() - start

        # 验证权重总和
        assert abs(metrics.get_total_weight() - 1.0) < 0.01

        # 性能验证：调整50个权重应该在合理时间内完成 (<100ms)
        assert elapsed < 0.1, f"权重调整耗时 {elapsed*1000:.2f}ms，超过预期"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
