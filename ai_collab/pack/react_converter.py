"""
ReAct Requirement Conversion Layer
Converts Owner natural language requirements to Pack drafts using ReAct pattern
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ReActStage(Enum):
    """ReAct stages"""

    REASON = "reason"
    ACT = "act"
    OBSERVE = "observe"


class ConversionStatus(Enum):
    """Conversion status"""

    IN_PROGRESS = "in_progress"
    READY_FOR_OWNER_REVIEW = "ready_for_owner_review"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass
class ReActTrace:
    """ReAct execution trace"""

    stage: ReActStage
    timestamp: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    reasoning: str
    actions: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)


@dataclass
class ConflictRecord:
    """Conflict record for cross-pack element reuse"""

    element_name: str
    source_packs: List[str]
    conflict_type: str  # naming, semantic, compliance
    description: str
    resolution: Optional[str] = None


@dataclass
class ChangeManifest:
    """Change manifest for conversion"""

    inherited_elements: List[Dict[str, Any]] = field(default_factory=list)
    new_elements: List[Dict[str, Any]] = field(default_factory=list)
    removed_elements: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[ConflictRecord] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Validation report for conversion"""

    schema_valid: bool = False
    compliance_valid: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checks: Dict[str, bool] = field(default_factory=dict)


@dataclass
class ConversionArtifacts:
    """Standard conversion artifacts"""

    draft_pack: Dict[str, Any]
    change_manifest: ChangeManifest
    validation_report: ValidationReport
    traces: List[ReActTrace] = field(default_factory=list)


class ReActConverter:
    """
    ReAct Requirement Converter
    Converts Owner requirements to Pack drafts using ReAct pattern
    """

    def __init__(self):
        self.traces: List[ReActTrace] = []
        self.current_stage: Optional[ReActStage] = None

    def convert(self, requirement: Dict[str, Any]) -> ConversionArtifacts:
        """
        Convert Owner requirement to Pack draft

        Args:
            requirement: Owner requirement form data

        Returns:
            ConversionArtifacts: Standard conversion artifacts
        """
        # Stage 1: Reason
        self._reason_stage(requirement)

        # Stage 2: Act
        draft_pack = self._act_stage(requirement)

        # Stage 3: Observe
        validation_report = self._observe_stage(draft_pack)

        # Build change manifest
        change_manifest = self._build_change_manifest(requirement, draft_pack)

        return ConversionArtifacts(
            draft_pack=draft_pack,
            change_manifest=change_manifest,
            validation_report=validation_report,
            traces=self.traces,
        )

    def _reason_stage(self, requirement: Dict[str, Any]):
        """Reason stage: Analyze requirement and plan conversion"""
        self.current_stage = ReActStage.REASON

        trace = ReActTrace(
            stage=ReActStage.REASON,
            timestamp=datetime.now().isoformat(),
            input_data=requirement,
            output_data={},
            reasoning="Analyzing Owner requirement and planning conversion strategy",
            actions=[
                "Parse requirement structure",
                "Identify target platform",
                "Determine pack type",
                "Plan workflow steps",
            ],
            observations=[
                f"Requirement type: {requirement.get('type', 'unknown')}",
                f"Target platform: {requirement.get('target_platform', 'generic')}",
                f"Complexity level: {requirement.get('complexity', 'medium')}",
            ],
        )

        self.traces.append(trace)

    def _act_stage(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Act stage: Generate Pack draft"""
        self.current_stage = ReActStage.ACT

        # Generate draft pack structure
        draft_pack = {
            "metadata": self._generate_metadata(requirement),
            "domain": self._generate_domain(requirement),
            "example_library": self._generate_example_library(requirement),
            "workflow": self._generate_workflow(requirement),
            "quality_metrics": self._generate_quality_metrics(requirement),
            "runtime_config": self._generate_runtime_config(requirement),
        }

        trace = ReActTrace(
            stage=ReActStage.ACT,
            timestamp=datetime.now().isoformat(),
            input_data=requirement,
            output_data=draft_pack,
            reasoning="Generating Pack draft based on requirement analysis",
            actions=[
                "Generate metadata",
                "Generate domain configuration",
                "Generate example library",
                "Generate workflow steps",
                "Generate quality metrics",
                "Generate runtime config",
            ],
            observations=[
                f"Generated {len(draft_pack['workflow']['steps'])} workflow steps",
                f"Generated {len(draft_pack['quality_metrics']['metrics'])} quality metrics",
            ],
        )

        self.traces.append(trace)

        return draft_pack

    def _observe_stage(self, draft_pack: Dict[str, Any]) -> ValidationReport:
        """Observe stage: Validate draft pack"""
        self.current_stage = ReActStage.OBSERVE

        validation_report = ValidationReport()

        # Schema validation
        try:
            from ai_collab.pack.schema_v2 import PromptPackV2

            PromptPackV2.from_dict(draft_pack)
            validation_report.schema_valid = True
            validation_report.checks["schema_validation"] = True
        except Exception as e:
            validation_report.schema_valid = False
            validation_report.errors.append(f"Schema validation failed: {str(e)}")
            validation_report.checks["schema_validation"] = False

        # Compliance validation
        compliance_errors = self._check_compliance(draft_pack)
        if not compliance_errors:
            validation_report.compliance_valid = True
            validation_report.checks["compliance_validation"] = True
        else:
            validation_report.compliance_valid = False
            validation_report.errors.extend(compliance_errors)
            validation_report.checks["compliance_validation"] = False

        trace = ReActTrace(
            stage=ReActStage.OBSERVE,
            timestamp=datetime.now().isoformat(),
            input_data=draft_pack,
            output_data={
                "schema_valid": validation_report.schema_valid,
                "compliance_valid": validation_report.compliance_valid,
            },
            reasoning="Validating draft pack against schema and compliance rules",
            actions=["Schema validation", "Compliance validation", "Business rule checks"],
            observations=[
                f"Schema valid: {validation_report.schema_valid}",
                f"Compliance valid: {validation_report.compliance_valid}",
                f"Total errors: {len(validation_report.errors)}",
            ],
        )

        self.traces.append(trace)

        return validation_report

    def _generate_metadata(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Generate pack metadata"""
        return {
            "pack_id": f"draft-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "pack_name": requirement.get("name", "Draft Pack"),
            "version": "0.1.0",
            "type": requirement.get("type", "custom"),
            "description": requirement.get("description", ""),
            "designer": requirement.get("owner", "unknown"),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "category": requirement.get("category"),
            "tags": requirement.get("tags", []),
            "language": requirement.get("language", "zh"),
            "estimated_efficiency_gain": requirement.get("efficiency_gain", "80%"),
        }

    def _generate_domain(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Generate domain configuration"""
        return {
            "primary_domain": requirement.get("primary_domain", "general"),
            "secondary_domains": requirement.get("secondary_domains", []),
            "target_platforms": requirement.get("target_platforms", ["generic"]),
            "target_audience": requirement.get("target_audience"),
            "brand_tone": requirement.get("brand_tone"),
            "compliance_rules": requirement.get("compliance_rules", []),
        }

    def _generate_example_library(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Generate example library"""
        return {
            "good_examples": requirement.get("good_examples", []),
            "bad_examples": requirement.get("bad_examples", []),
            "few_shot_template": requirement.get("few_shot_template"),
        }

    def _generate_workflow(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Generate workflow steps"""
        steps = []

        # Add input collection step
        steps.append(
            {
                "id": "step-1",
                "name": "收集输入",
                "type": "local",
                "description": "收集用户输入数据",
                "inputs": requirement.get("inputs", []),
                "outputs": ["user_input"],
            }
        )

        # Add generation step
        steps.append(
            {
                "id": "step-2",
                "name": "生成内容",
                "type": "generation",
                "description": "使用 AI 生成内容",
                "template": requirement.get("template", "生成关于 {topic} 的内容"),
                "params": requirement.get("params", {}),
                "inputs": ["user_input"],
                "outputs": ["generated_content"],
            }
        )

        # Add validation step
        steps.append(
            {
                "id": "step-3",
                "name": "验证内容",
                "type": "validation",
                "description": "验证生成的内容",
                "inputs": ["generated_content"],
                "outputs": ["validated_content"],
            }
        )

        return {
            "steps": steps,
            "error_handling": {"retry_count": 3, "fallback_strategy": "use_default"},
        }

    def _generate_quality_metrics(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Generate quality metrics"""
        return {
            "metrics": {
                "relevance": {
                    "name": "相关性",
                    "description": "内容与主题的相关性",
                    "check_method": "semantic_similarity",
                    "weight": 0.3,
                },
                "quality": {
                    "name": "质量",
                    "description": "内容质量评分",
                    "check_method": "quality_score",
                    "weight": 0.4,
                },
                "compliance": {
                    "name": "合规性",
                    "description": "内容合规性检查",
                    "check_method": "compliance_check",
                    "weight": 0.3,
                },
            },
            "normalization_method": "linear",
            "validation_tolerance": 0.01,
        }

    def _generate_runtime_config(self, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Generate runtime configuration"""
        return {
            "max_execution_time": requirement.get("max_execution_time", 300),
            "enable_caching": requirement.get("enable_caching", True),
            "enable_logging": requirement.get("enable_logging", True),
            "runtime_overrides_whitelist": [
                "style_profile",
                "tone",
                "length",
                "compliance_level",
                "temperature_bias",
            ],
        }

    def _build_change_manifest(
        self, requirement: Dict[str, Any], draft_pack: Dict[str, Any]
    ) -> ChangeManifest:
        """Build change manifest"""
        manifest = ChangeManifest()

        # Check for inherited elements
        if "inherit_from" in requirement:
            for source_pack in requirement["inherit_from"]:
                manifest.inherited_elements.append(
                    {
                        "source_pack": source_pack,
                        "elements": ["workflow", "quality_metrics"],
                        "inheritance_type": "full",
                    }
                )

        # Add new elements
        manifest.new_elements.append(
            {
                "element_type": "metadata",
                "element_name": draft_pack["metadata"]["pack_name"],
                "description": "New pack metadata",
            }
        )

        manifest.new_elements.append(
            {
                "element_type": "workflow",
                "element_name": "main_workflow",
                "description": "Main workflow with 3 steps",
            }
        )

        return manifest

    def _check_compliance(self, draft_pack: Dict[str, Any]) -> List[str]:
        """Check compliance rules"""
        errors = []

        # Check for forbidden words
        forbidden_words = ["违禁词1", "违禁词2"]  # Example
        content = json.dumps(draft_pack, ensure_ascii=False)
        for word in forbidden_words:
            if word in content:
                errors.append(f"发现违禁词: {word}")

        # Check for required fields
        if "metadata" not in draft_pack:
            errors.append("缺少 metadata 字段")
        if "workflow" not in draft_pack:
            errors.append("缺少 workflow 字段")

        return errors

    def _determine_status(self, validation_report: ValidationReport) -> ConversionStatus:
        """Determine conversion status"""
        if validation_report.schema_valid and validation_report.compliance_valid:
            return ConversionStatus.READY_FOR_OWNER_REVIEW
        else:
            return ConversionStatus.BLOCKED


def convert_requirement(requirement: Dict[str, Any]) -> ConversionArtifacts:
    """
    Convert Owner requirement to Pack draft

    Args:
        requirement: Owner requirement form data

    Returns:
        ConversionArtifacts: Standard conversion artifacts
    """
    converter = ReActConverter()
    return converter.convert(requirement)
