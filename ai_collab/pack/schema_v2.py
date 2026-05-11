# Prompt Pack v2.0 Schema
# Status: COMPLETED (v2.0.0)
# Completed: 2026-02-27
# Examples: packs/examples/xiaohongshu_beauty_review.json, packs/examples/generic_content_writer.json

"""
Prompt Pack v2.0 Schema
支持 AI-Roundtable 多 AI 协同、智能工作流、质量追踪
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PackType(Enum):
    """Pack 类型分类"""

    PRODUCTIVITY = "productivity"  # 生产力工具
    CREATIVE = "creative"  # 创意生成
    ANALYSIS = "analysis"  # 数据分析
    BUSINESS = "business"  # 业务场景
    EDUCATION = "education"  # 教育培训
    CUSTOM = "custom"  # 自定义


class StepType(Enum):
    """工作流步骤类型"""

    LOCAL = "local"  # 本地处理（无需 AI）
    ANALYSIS = "analysis"  # 单 AI 分析
    GENERATION = "generation"  # 多 AI 生成
    VALIDATION = "validation"  # 交叉验证
    FUSION = "fusion"  # 智能融合
    TRACKING = "tracking"  # 发布追踪


class TargetPlatform(Enum):
    """目标平台"""

    XIAOHONGSHU = "xiaohongshu"
    WEIBO = "weibo"
    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    GENERIC = "generic"


@dataclass
class PackMetadata:
    """Pack 元数据"""

    pack_id: str
    pack_name: str
    version: str  # SemVer 格式
    type: PackType
    description: str
    designer: str
    created_at: datetime
    updated_at: datetime
    category: Optional[str] = None  # 二级分类（如：美妆、科技、美食）
    tags: List[str] = field(default_factory=list)
    language: str = "zh"
    estimated_efficiency_gain: str = "80%"  # 预期效率提升


@dataclass
class QualityMetric:
    """单个质量指标定义"""

    name: str
    description: str
    check_method: str  # 检查方法标识
    weight: float  # 权重 (0-1)
    min_threshold: float = 0.0  # 最低阈值


@dataclass
class QualityMetrics:
    """质量指标集合"""

    metrics: Dict[str, QualityMetric]
    normalization_method: str = "linear"  # linear, minmax, zscore
    validation_tolerance: float = 0.01  # 权重总和容差

    def get_total_weight(self) -> float:
        """获取权重总和"""
        return sum(m.weight for m in self.metrics.values())

    def validate_weights(self) -> bool:
        """验证权重总和是否为 1.0"""
        total = self.get_total_weight()
        return abs(total - 1.0) <= self.validation_tolerance

    def get_normalized_weights(self) -> Dict[str, float]:
        """
        获取归一化的权重

        Returns:
            Dict[str, float]: 指标名称到归一化权重的映射
        """
        total = self.get_total_weight()
        if total == 0:
            return {name: 0.0 for name in self.metrics}

        if self.normalization_method == "linear":
            return {name: m.weight / total for name, m in self.metrics.items()}
        elif self.normalization_method == "minmax":
            min_w = min(m.weight for m in self.metrics.values())
            max_w = max(m.weight for m in self.metrics.values())
            if max_w - min_w == 0:
                return {name: 1.0 / len(self.metrics) for name in self.metrics}
            # MinMax 归一化到 [0, 1],然后归一化到总和为 1
            normalized_values = {
                name: (m.weight - min_w) / (max_w - min_w) for name, m in self.metrics.items()
            }
            norm_sum = sum(normalized_values.values())
            if norm_sum == 0:
                return {name: 1.0 / len(self.metrics) for name in self.metrics}
            return {name: val / norm_sum for name, val in normalized_values.items()}
        elif self.normalization_method == "zscore":
            weights = [m.weight for m in self.metrics.values()]
            mean = sum(weights) / len(weights)
            std = (sum((w - mean) ** 2 for w in weights) / len(weights)) ** 0.5
            if std == 0:
                return {name: 1.0 / len(self.metrics) for name in self.metrics}
            normalized = {name: (m.weight - mean) / std for name, m in self.metrics.items()}
            # 转换为正权重并归一化
            min_norm = min(normalized.values())
            positive = {name: max(val - min_norm, 0) for name, val in normalized.items()}
            positive_sum = sum(positive.values())
            if positive_sum == 0:
                return {name: 1.0 / len(self.metrics) for name in self.metrics}
            return {name: val / positive_sum for name, val in positive.items()}
        else:
            return {name: m.weight / total for name, m in self.metrics.items()}

    def adjust_weight(self, metric_name: str, new_weight: float) -> bool:
        """
        调整单个指标的权重,并重新分配其他权重

        Args:
            metric_name: 要调整的指标名称
            new_weight: 新的权重值

        Returns:
            bool: 是否成功调整
        """
        if metric_name not in self.metrics:
            return False

        if not 0 <= new_weight <= 1:
            return False

        # 计算其他指标需要分配的总权重
        remaining_weight = 1.0 - new_weight
        current_other_weights = sum(
            m.weight for name, m in self.metrics.items() if name != metric_name
        )

        # 更新目标指标
        self.metrics[metric_name].weight = new_weight

        # 重新分配其他指标
        if current_other_weights > 0 and remaining_weight > 0:
            scale = remaining_weight / current_other_weights
            for name, metric in self.metrics.items():
                if name != metric_name:
                    metric.weight *= scale

        return True

    def add_metric(self, metric: QualityMetric, redistribute: bool = True) -> bool:
        """
        添加新指标,并可选择是否重新分配权重

        Args:
            metric: 要添加的指标
            redistribute: 是否重新分配所有权重

        Returns:
            bool: 是否成功添加
        """
        if metric.name in self.metrics:
            return False

        self.metrics[metric.name] = metric

        if redistribute:
            total = self.get_total_weight()
            if total > 0:
                scale = 1.0 / total
                for name, metric_obj in self.metrics.items():
                    metric_obj.weight *= scale

        return True

    def remove_metric(self, metric_name: str, redistribute: bool = True) -> bool:
        """
        移除指标,并可选择是否重新分配权重

        Args:
            metric_name: 要移除的指标名称
            redistribute: 是否重新分配其他权重

        Returns:
            bool: 是否成功移除
        """
        if metric_name not in self.metrics:
            return False

        removed_weight = self.metrics[metric_name].weight
        del self.metrics[metric_name]

        if redistribute and self.metrics:
            remaining_total = sum(m.weight for m in self.metrics.values())
            if remaining_total > 0:
                scale = (remaining_total + removed_weight) / remaining_total
                for metric_obj in self.metrics.values():
                    metric_obj.weight *= scale

        return True

    def calculate_quality_score(self, metric_scores: Dict[str, float]) -> float:
        """
        根据指标得分计算综合质量分数

        Args:
            metric_scores: 指标名称到得分的映射 (0-100)

        Returns:
            float: 综合质量分数 (0-100)
        """
        normalized_weights = self.get_normalized_weights()
        total_score = 0.0

        for name, weight in normalized_weights.items():
            if name in metric_scores:
                # 考虑最小阈值
                metric = self.metrics[name]
                adjusted_score = max(metric_scores[name], metric.min_threshold * 100)
                total_score += weight * adjusted_score
            else:
                # 缺失指标给予最低分
                total_score += weight * 0.0

        return total_score


@dataclass
class GenerationParams:
    """生成参数配置"""

    # 多样性激发
    diversity_enhancement: bool = True
    output_versions: int = 3
    diversity_dimensions: List[str] = field(
        default_factory=lambda: ["emotional_tone", "narrative_style", "feature_highlighting"]
    )

    # 概率/置信度输出
    confidence_display: bool = True
    critical_facts_only: bool = True

    # 温度参数（如果适用）
    temperature: float = 0.7

    # 输出格式
    output_format: str = "markdown"
    require_code_blocks: bool = False


@dataclass
class WorkflowStep:
    """工作流步骤定义"""

    id: str
    name: str
    type: StepType
    description: str = ""

    # 输入输出
    input_fields: List[str] = field(default_factory=list)
    output_field: str = ""

    # AI 配置
    ai_models: Optional[List[str]] = None  # ["qianwen", "zhipu", "kimi"]
    parallel: bool = False  # 是否并行执行

    # 交叉验证配置
    cross_review: bool = False  # 是否启用交叉验证
    validation_criteria: Optional[List[str]] = None

    # 融合规则
    fusion_rules: Optional[Dict[str, Any]] = None

    # 预估时间
    estimated_time: Optional[int] = None  # 秒

    # 自动触发
    auto_trigger: bool = False
    trigger_delay: Optional[int] = None

    # 其他配置
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """工作流定义"""

    steps: List[WorkflowStep]
    max_parallel_steps: int = 3
    allow_parallel: bool = True

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """获取指定步骤"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None


@dataclass
class PackExample:
    """Pack 示例"""

    id: str
    input: Dict[str, str]
    output: str
    description: str
    score: float = 100.0
    validation_notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExampleLibrary:
    """示例库"""

    good_examples: List[PackExample] = field(default_factory=list)
    bad_examples: List[PackExample] = field(default_factory=list)
    few_shot_template: str = ""

    def add_good_example(self, example: PackExample):
        self.good_examples.append(example)

    def add_bad_example(self, example: PackExample):
        self.bad_examples.append(example)


@dataclass
class DomainPack:
    """领域特定配置"""

    primary_domain: str  # 主要领域（如：小红书运营）
    secondary_domains: List[str] = field(default_factory=list)

    # 目标平台
    target_platforms: List[TargetPlatform] = field(default_factory=list)

    # 用户画像
    target_audience: Optional[str] = None

    # 品牌调性
    brand_tone: Optional[str] = None  # 如：专业、活泼、温暖

    # 合规要求
    compliance_rules: List[str] = field(default_factory=list)


@dataclass
class OptimizationRules:
    """优化规则"""

    enabled: bool = True
    strategy: str = "feedback_driven"  # feedback_driven, auto, manual
    auto_refine_threshold: float = 60.0  # 低于此分数自动优化
    periodic_review_days: int = 30  # 定期审查周期（天）
    allowed_actions: List[str] = field(
        default_factory=lambda: [
            "auto_refine_low_scoring",
            "periodic_template_optimization",
            "example_library_update",
            "metric_weight_adjustment",
        ]
    )


@dataclass
class PerformanceTracking:
    """性能追踪配置"""

    enabled: bool = True
    metrics: List[str] = field(
        default_factory=lambda: [
            "execution_time",
            "generation_success_rate",
            "average_quality_score",
            "user_satisfaction",
        ]
    )
    retention_days: int = 90

    # 发布后追踪
    post_publish_tracking: Optional[Dict[str, Any]] = None
    # {
    #   "enabled": true,
    #   "delay_hours": 24,
    #   "metrics": ["likes", "comments", "shares", "conversion_rate"]
    # }


@dataclass
class CollaborationConfig:
    """团队协作配置"""

    shared_with: List[str] = field(default_factory=list)  # user_ids
    edit_permission: List[str] = field(default_factory=list)
    use_permission: List[str] = field(default_factory=list)
    is_public: bool = False


@dataclass
class PromptPackV2:
    """
    Prompt Pack v2.0 完整定义

    核心理念：标准化生产力模块，而非简单提问模板
    """

    # === 基础信息 ===
    metadata: PackMetadata

    # === 领域配置 ===
    domain: DomainPack

    # === 工作流定义 ===
    workflow: WorkflowDefinition

    # === 质量指标 ===
    quality_metrics: QualityMetrics

    # === 示例库 ===
    example_library: ExampleLibrary

    # === 生成参数 ===
    generation_params: GenerationParams

    # === 优化规则 ===
    optimization: OptimizationRules

    # === 性能追踪 ===
    performance_tracking: PerformanceTracking

    # === 协作配置 ===
    collaboration: CollaborationConfig

    # === 系统提示词（服务器端完整版） ===
    system_prompt: str = ""

    # === 质量验证规则 ===
    quality_validation_rules: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metadata": {
                "pack_id": self.metadata.pack_id,
                "pack_name": self.metadata.pack_name,
                "version": self.metadata.version,
                "type": self.metadata.type.value,
                "description": self.metadata.description,
                "designer": self.metadata.designer,
                "created_at": self.metadata.created_at.isoformat(),
                "updated_at": self.metadata.updated_at.isoformat(),
                "category": self.metadata.category,
                "tags": self.metadata.tags,
                "language": self.metadata.language,
                "estimated_efficiency_gain": self.metadata.estimated_efficiency_gain,
            },
            "domain": {
                "primary_domain": self.domain.primary_domain,
                "secondary_domains": self.domain.secondary_domains,
                "target_platforms": [p.value for p in self.domain.target_platforms],
                "target_audience": self.domain.target_audience,
                "brand_tone": self.domain.brand_tone,
                "compliance_rules": self.domain.compliance_rules,
            },
            "workflow": {
                "steps": [
                    {
                        "id": step.id,
                        "name": step.name,
                        "type": step.type.value,
                        "description": step.description,
                        "input_fields": step.input_fields,
                        "output_field": step.output_field,
                        "ai_models": step.ai_models,
                        "parallel": step.parallel,
                        "cross_review": step.cross_review,
                        "validation_criteria": step.validation_criteria,
                        "fusion_rules": step.fusion_rules,
                        "estimated_time": step.estimated_time,
                        "auto_trigger": step.auto_trigger,
                        "trigger_delay": step.trigger_delay,
                        "config": step.config,
                    }
                    for step in self.workflow.steps
                ],
                "max_parallel_steps": self.workflow.max_parallel_steps,
                "allow_parallel": self.workflow.allow_parallel,
            },
            "quality_metrics": {
                "metrics": {
                    name: {
                        "description": metric.description,
                        "check_method": metric.check_method,
                        "weight": metric.weight,
                        "min_threshold": metric.min_threshold,
                    }
                    for name, metric in self.quality_metrics.metrics.items()
                },
                "normalization_method": self.quality_metrics.normalization_method,
                "validation_tolerance": self.quality_metrics.validation_tolerance,
            },
            "example_library": {
                "good_examples": [
                    {
                        "id": ex.id,
                        "input": ex.input,
                        "output": ex.output,
                        "description": ex.description,
                        "score": ex.score,
                        "validation_notes": ex.validation_notes,
                        "created_at": ex.created_at.isoformat(),
                    }
                    for ex in self.example_library.good_examples
                ],
                "bad_examples": [
                    {
                        "id": ex.id,
                        "input": ex.input,
                        "output": ex.output,
                        "description": ex.description,
                        "score": ex.score,
                        "validation_notes": ex.validation_notes,
                        "created_at": ex.created_at.isoformat(),
                    }
                    for ex in self.example_library.bad_examples
                ],
                "few_shot_template": self.example_library.few_shot_template,
            },
            "generation_params": {
                "diversity_enhancement": self.generation_params.diversity_enhancement,
                "output_versions": self.generation_params.output_versions,
                "diversity_dimensions": self.generation_params.diversity_dimensions,
                "confidence_display": self.generation_params.confidence_display,
                "critical_facts_only": self.generation_params.critical_facts_only,
                "temperature": self.generation_params.temperature,
                "output_format": self.generation_params.output_format,
                "require_code_blocks": self.generation_params.require_code_blocks,
            },
            "optimization": {
                "enabled": self.optimization.enabled,
                "strategy": self.optimization.strategy,
                "auto_refine_threshold": self.optimization.auto_refine_threshold,
                "periodic_review_days": self.optimization.periodic_review_days,
                "allowed_actions": self.optimization.allowed_actions,
            },
            "performance_tracking": {
                "enabled": self.performance_tracking.enabled,
                "metrics": self.performance_tracking.metrics,
                "retention_days": self.performance_tracking.retention_days,
                "post_publish_tracking": self.performance_tracking.post_publish_tracking,
            },
            "collaboration": {
                "shared_with": self.collaboration.shared_with,
                "edit_permission": self.collaboration.edit_permission,
                "use_permission": self.collaboration.use_permission,
                "is_public": self.collaboration.is_public,
            },
            "system_prompt": self.system_prompt,
            "quality_validation_rules": self.quality_validation_rules,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptPackV2":
        """从字典创建"""
        metadata_data = data["metadata"]
        metadata = PackMetadata(
            pack_id=metadata_data["pack_id"],
            pack_name=metadata_data["pack_name"],
            version=metadata_data["version"],
            type=PackType(metadata_data["type"]),
            description=metadata_data["description"],
            designer=metadata_data["designer"],
            created_at=datetime.fromisoformat(metadata_data["created_at"]),
            updated_at=datetime.fromisoformat(metadata_data["updated_at"]),
            category=metadata_data.get("category"),
            tags=metadata_data.get("tags", []),
            language=metadata_data.get("language", "zh"),
            estimated_efficiency_gain=metadata_data.get("estimated_efficiency_gain", "80%"),
        )

        domain_data = data["domain"]
        domain = DomainPack(
            primary_domain=domain_data["primary_domain"],
            secondary_domains=domain_data.get("secondary_domains", []),
            target_platforms=[TargetPlatform(p) for p in domain_data.get("target_platforms", [])],
            target_audience=domain_data.get("target_audience"),
            brand_tone=domain_data.get("brand_tone"),
            compliance_rules=domain_data.get("compliance_rules", []),
        )

        workflow_data = data["workflow"]
        steps = [
            WorkflowStep(
                id=step["id"],
                name=step["name"],
                type=StepType(step["type"]),
                description=step.get("description", ""),
                input_fields=step.get("input_fields", []),
                output_field=step.get("output_field", ""),
                ai_models=step.get("ai_models"),
                parallel=step.get("parallel", False),
                cross_review=step.get("cross_review", False),
                validation_criteria=step.get("validation_criteria"),
                fusion_rules=step.get("fusion_rules"),
                estimated_time=step.get("estimated_time"),
                auto_trigger=step.get("auto_trigger", False),
                trigger_delay=step.get("trigger_delay"),
                config=step.get("config", {}),
            )
            for step in workflow_data["steps"]
        ]
        workflow = WorkflowDefinition(
            steps=steps,
            max_parallel_steps=workflow_data.get("max_parallel_steps", 3),
            allow_parallel=workflow_data.get("allow_parallel", True),
        )

        quality_data = data["quality_metrics"]
        quality_metrics = QualityMetrics(
            metrics={
                name: QualityMetric(
                    name=name,
                    description=metric["description"],
                    check_method=metric["check_method"],
                    weight=metric["weight"],
                    min_threshold=metric.get("min_threshold", 0.0),
                )
                for name, metric in quality_data["metrics"].items()
            },
            normalization_method=quality_data.get("normalization_method", "linear"),
            validation_tolerance=quality_data.get("validation_tolerance", 0.01),
        )

        example_data = data["example_library"]
        example_library = ExampleLibrary(
            few_shot_template=example_data.get("few_shot_template", "")
        )
        for ex in example_data.get("good_examples", []):
            example_library.add_good_example(
                PackExample(
                    id=ex["id"],
                    input=ex["input"],
                    output=ex["output"],
                    description=ex["description"],
                    score=ex["score"],
                    validation_notes=ex.get("validation_notes", ""),
                    created_at=datetime.fromisoformat(ex["created_at"])
                    if "created_at" in ex
                    else datetime.now(),
                )
            )
        for ex in example_data.get("bad_examples", []):
            example_library.add_bad_example(
                PackExample(
                    id=ex["id"],
                    input=ex["input"],
                    output=ex["output"],
                    description=ex["description"],
                    score=ex["score"],
                    validation_notes=ex.get("validation_notes", ""),
                    created_at=datetime.fromisoformat(ex["created_at"])
                    if "created_at" in ex
                    else datetime.now(),
                )
            )

        gen_data = data.get("generation_params", {})
        generation_params = GenerationParams(
            diversity_enhancement=gen_data.get("diversity_enhancement", True),
            output_versions=gen_data.get("output_versions", 3),
            diversity_dimensions=gen_data.get(
                "diversity_dimensions",
                ["emotional_tone", "narrative_style", "feature_highlighting"],
            ),
            confidence_display=gen_data.get("confidence_display", True),
            critical_facts_only=gen_data.get("critical_facts_only", True),
            temperature=gen_data.get("temperature", 0.7),
            output_format=gen_data.get("output_format", "markdown"),
            require_code_blocks=gen_data.get("require_code_blocks", False),
        )

        opt_data = data.get("optimization", {})
        optimization = OptimizationRules(
            enabled=opt_data.get("enabled", True),
            strategy=opt_data.get("strategy", "feedback_driven"),
            auto_refine_threshold=opt_data.get("auto_refine_threshold", 60.0),
            periodic_review_days=opt_data.get("periodic_review_days", 30),
            allowed_actions=opt_data.get(
                "allowed_actions",
                [
                    "auto_refine_low_scoring",
                    "periodic_template_optimization",
                    "example_library_update",
                    "metric_weight_adjustment",
                ],
            ),
        )

        perf_data = data.get("performance_tracking", {})
        performance_tracking = PerformanceTracking(
            enabled=perf_data.get("enabled", True),
            metrics=perf_data.get(
                "metrics",
                [
                    "execution_time",
                    "generation_success_rate",
                    "average_quality_score",
                    "user_satisfaction",
                ],
            ),
            retention_days=perf_data.get("retention_days", 90),
            post_publish_tracking=perf_data.get("post_publish_tracking"),
        )

        collab_data = data.get("collaboration", {})
        collaboration = CollaborationConfig(
            shared_with=collab_data.get("shared_with", []),
            edit_permission=collab_data.get("edit_permission", []),
            use_permission=collab_data.get("use_permission", []),
            is_public=collab_data.get("is_public", False),
        )

        return cls(
            metadata=metadata,
            domain=domain,
            workflow=workflow,
            quality_metrics=quality_metrics,
            example_library=example_library,
            generation_params=generation_params,
            optimization=optimization,
            performance_tracking=performance_tracking,
            collaboration=collaboration,
            system_prompt=data.get("system_prompt", ""),
            quality_validation_rules=data.get("quality_validation_rules", ""),
        )

    def validate(self) -> bool:
        """验证 Pack 结构完整性"""
        if not self.metadata.pack_id or not self.metadata.pack_name:
            return False

        if not self.workflow.steps:
            return False

        # 验证步骤 ID 唯一性
        step_ids = [step.id for step in self.workflow.steps]
        if len(step_ids) != len(set(step_ids)):
            return False

        # 验证质量指标权重总和
        total_weight = self.quality_metrics.get_total_weight()
        if abs(total_weight - 1.0) > self.quality_metrics.validation_tolerance:
            return False

        return True


# === 工厂函数 ===


def create_xiaohongshu_base() -> PromptPackV2:
    """创建小红书基础 Pack"""
    metadata = PackMetadata(
        pack_id="xiaohongshu-explosive-copy",
        pack_name="小红书爆文生成包",
        version="2.0.0",
        type=PackType.BUSINESS,
        description="生成符合小红书平台特性的高质量爆纹内容",
        designer="AI Collab Team",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        category="内容运营",
        tags=["小红书", "文案", "爆文", "种草"],
        language="zh",
        estimated_efficiency_gain="80%",
    )

    domain = DomainPack(
        primary_domain="小红书运营",
        secondary_domains=["内容创作", "社交媒体营销"],
        target_platforms=[TargetPlatform.XIAOHONGSHU],
        target_audience="内容运营、美妆博主、品牌方",
        brand_tone="活泼、温暖、真实",
        compliance_rules=["严禁虚假宣传", "禁止诱导点击", "符合平台广告法规范"],
    )

    # 质量指标
    quality_metrics = QualityMetrics(
        metrics={
            "coverage": QualityMetric(
                name="coverage",
                description="卖点覆盖率 - 是否覆盖所有关键卖点",
                check_method="compare_with_required_features",
                weight=0.25,
            ),
            "distinctiveness": QualityMetric(
                name="distinctiveness",
                description="创意度 - 与竞品文案的差异性",
                check_method="semantic_similarity_analysis",
                weight=0.30,
            ),
            "accuracy": QualityMetric(
                name="accuracy",
                description="准确性 - 事实信息的可靠性",
                check_method="fact_verification",
                weight=0.20,
            ),
            "attractiveness": QualityMetric(
                name="attractiveness",
                description="吸引力 - 标题和开头的抓眼程度",
                check_method="clickbait_analysis",
                weight=0.15,
            ),
            "compliance": QualityMetric(
                name="compliance",
                description="规范性 - 平台规范符合度",
                check_method="format_compliance",
                weight=0.10,
            ),
        }
    )

    return PromptPackV2(
        metadata=metadata,
        domain=domain,
        workflow=WorkflowDefinition(steps=[]),
        quality_metrics=quality_metrics,
        example_library=ExampleLibrary(),
        generation_params=GenerationParams(),
        optimization=OptimizationRules(),
        performance_tracking=PerformanceTracking(),
        collaboration=CollaborationConfig(),
    )


if __name__ == "__main__":
    # 测试创建基础 Pack
    pack = create_xiaohongshu_base()
    print(f"Created Pack: {pack.metadata.pack_name}")
    print(f"Version: {pack.metadata.version}")
    print(f"Valid: {pack.validate()}")
    print(f"Quality Metrics: {list(pack.quality_metrics.metrics.keys())}")
