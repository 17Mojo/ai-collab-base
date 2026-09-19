"""
Pydantic Schemas for Pack API
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class PackType(str, Enum):
    PRODUCTIVITY = "productivity"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    BUSINESS = "business"
    EDUCATION = "education"
    CUSTOM = "custom"


class StepType(str, Enum):
    LOCAL = "local"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    VALIDATION = "validation"
    FUSION = "fusion"
    TRACKING = "tracking"


# ==================== Pack Schemas ====================


class PackMetadataSchema(BaseModel):
    pack_id: str
    pack_name: str
    version: str = "1.0.0"
    type: PackType = PackType.CUSTOM
    description: str = ""
    designer: str = ""
    category: str | None = None
    tags: list[str] = []
    language: str = "zh"
    estimated_efficiency_gain: str = "80%"
    created_at: str | None = None
    updated_at: str | None = None


class WorkflowStepSchema(BaseModel):
    id: str
    name: str
    type: StepType
    description: str = ""
    input_fields: list[str] = []
    output_field: str = ""
    ai_models: list[str] | None = None
    parallel: bool = False
    estimated_time: int | None = None


class QualityMetricSchema(BaseModel):
    name: str
    description: str
    check_method: str
    weight: float = 0.0
    min_threshold: float = 0.0


class PackCreate(BaseModel):
    """创建 Pack 请求"""

    metadata: PackMetadataSchema
    workflow: dict[str, Any]
    domain: dict[str, Any] | None = None
    quality_metrics: dict[str, Any] | None = None
    example_library: dict[str, Any] | None = None
    generation_params: dict[str, Any] | None = None
    optimization: dict[str, Any] | None = None
    performance_tracking: dict[str, Any] | None = None
    collaboration: dict[str, Any] | None = None
    system_prompt: str | None = ""


class PackUpdate(BaseModel):
    """更新 Pack 请求"""

    pack_name: str | None = None
    description: str | None = None
    workflow: dict[str, Any] | None = None
    quality_metrics: dict[str, Any] | None = None
    example_library: dict[str, Any] | None = None
    generation_params: dict[str, Any] | None = None
    system_prompt: str | None = None
    tags: list[str] | None = None


class PackResponse(BaseModel):
    """Pack 响应"""

    id: str
    pack_id: str
    pack_name: str
    version: str
    type: str
    description: str
    designer: str
    category: str | None
    tags: list[str]
    language: str
    pack_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    execution_count: int

    class Config:
        from_attributes = True


class PackListResponse(BaseModel):
    """Pack 列表响应"""

    total: int
    packs: list[PackResponse]


# ==================== Execution Schemas ====================


class ExecutionCreate(BaseModel):
    """创建执行请求"""

    pack_id: str
    input_data: dict[str, Any] = {}


class ExecutionUpdate(BaseModel):
    """更新执行状态"""

    status: str
    output_data: dict[str, Any] | None = None
    error_message: str | None = None
    step_results: list[dict[str, Any]] | None = None


class ExecutionResponse(BaseModel):
    """执行响应"""

    id: str
    pack_id: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    input_data: dict[str, Any] | None
    output_data: dict[str, Any] | None
    error_message: str | None
    step_results: list[dict[str, Any]] | None

    class Config:
        from_attributes = True


class ExecutionListResponse(BaseModel):
    """执行历史列表"""

    total: int
    executions: list[ExecutionResponse]


# ==================== Quality Schemas ====================


class QualityMetricCreate(BaseModel):
    """创建质量指标"""

    pack_id: str
    execution_id: str
    metric_name: str
    score: float
    details: dict[str, Any] | None = None


class QualityMetricResponse(BaseModel):
    """质量指标响应"""

    id: str
    pack_id: str
    execution_id: str
    metric_name: str
    score: float
    details: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Bulk Schemas ====================


class BulkErrorItem(BaseModel):
    index: int
    item_id: str | None = None
    error: str


class BulkPackCreateRequest(BaseModel):
    packs: list[PackCreate]
    continue_on_error: bool = True


class BulkPackCreateResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    created: list[PackResponse]
    errors: list[BulkErrorItem]


class BulkPackGetRequest(BaseModel):
    pack_ids: list[str]
    include_inactive: bool = False


class BulkPackGetResponse(BaseModel):
    total_requested: int
    found: int
    missing: list[str]
    packs: list[PackResponse]


class BulkExecutionCreateRequest(BaseModel):
    items: list[Any]
    continue_on_error: bool = True


class BulkExecutionCreateResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    executions: list[ExecutionResponse]
    errors: list[BulkErrorItem]


# ==================== Execute Pack Schemas ====================


class ExecutePackRequest(BaseModel):
    """Pack 执行请求"""

    pack_id: str
    platform: str = "generic"
    user_input: str = ""
    enable_knowledge: bool = False
    context: dict[str, Any] | None = None


class StepResultSchema(BaseModel):
    """步骤执行结果"""

    id: str
    type: str
    status: str
    output: str | None = None
    description: str = ""
    branches: list[dict[str, Any]] = []


class ExecutePackResponse(BaseModel):
    """Pack 执行响应"""

    execution_id: str
    pack_id: str
    status: str
    steps: list[StepResultSchema]
    output: str | None = None
    duration_ms: int
    knowledge_sources: list[str] = []
    platform: str = "generic"
    branch_logic_enabled: bool = False


# ==================== Studio Schemas ====================


class GenerateStudioRequest(BaseModel):
    """Studio 产物生成请求"""

    content: str
    artifacts: list[str]  # ['audio', 'video', 'slides']
    focus: str = ""
    notebook_id: str | None = None


class ArtifactSchema(BaseModel):
    """产物信息"""

    type: str
    status: str
    size_mb: int | None = None


class GenerateStudioResponse(BaseModel):
    """Studio 产物生成响应"""

    artifact_id: str
    status: str
    artifacts: list[ArtifactSchema]
    download_urls: dict[str, str]
    focus: str
    content_length: int
    notebook_id: str | None = None


# ==================== Pack Validate Schemas ====================


class StructureCheckSchema(BaseModel):
    """结构检查结果"""

    metadata: dict[str, Any] = {}
    workflow: dict[str, Any] = {}
    branch_logic: dict[str, Any] = {}
    domain: dict[str, Any] = {}


class PackValidateResponse(BaseModel):
    """Pack 验证响应"""

    pack_id: str
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    structure_check: StructureCheckSchema
    steps_count: int
    has_branches: bool


# ==================== Execution Status Schemas ====================


class ExecutionStatusResponse(BaseModel):
    """执行状态响应"""

    execution_id: str
    pack_id: str
    status: str
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
