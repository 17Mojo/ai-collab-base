"""
Pydantic Schemas for Pack API
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

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
    category: Optional[str] = None
    tags: List[str] = []
    language: str = "zh"
    estimated_efficiency_gain: str = "80%"


class WorkflowStepSchema(BaseModel):
    id: str
    name: str
    type: StepType
    description: str = ""
    input_fields: List[str] = []
    output_field: str = ""
    ai_models: Optional[List[str]] = None
    parallel: bool = False
    estimated_time: Optional[int] = None


class QualityMetricSchema(BaseModel):
    name: str
    description: str
    check_method: str
    weight: float = 0.0
    min_threshold: float = 0.0


class PackCreate(BaseModel):
    """创建 Pack 请求"""

    metadata: PackMetadataSchema
    workflow: Dict[str, Any]
    quality_metrics: Optional[Dict[str, Any]] = None
    example_library: Optional[Dict[str, Any]] = None
    generation_params: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = ""


class PackUpdate(BaseModel):
    """更新 Pack 请求"""

    pack_name: Optional[str] = None
    description: Optional[str] = None
    workflow: Optional[Dict[str, Any]] = None
    quality_metrics: Optional[Dict[str, Any]] = None
    example_library: Optional[Dict[str, Any]] = None
    generation_params: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    tags: Optional[List[str]] = None


class PackResponse(BaseModel):
    """Pack 响应"""

    id: str
    pack_id: str
    pack_name: str
    version: str
    type: str
    description: str
    designer: str
    category: Optional[str]
    tags: List[str]
    language: str
    pack_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    execution_count: int

    class Config:
        from_attributes = True


class PackListResponse(BaseModel):
    """Pack 列表响应"""

    total: int
    packs: List[PackResponse]


# ==================== Execution Schemas ====================


class ExecutionCreate(BaseModel):
    """创建执行请求"""

    pack_id: str
    input_data: Dict[str, Any] = {}


class ExecutionUpdate(BaseModel):
    """更新执行状态"""

    status: str
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    step_results: Optional[List[Dict[str, Any]]] = None


class ExecutionResponse(BaseModel):
    """执行响应"""

    id: str
    pack_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    step_results: Optional[List[Dict[str, Any]]]

    class Config:
        from_attributes = True


class ExecutionListResponse(BaseModel):
    """执行历史列表"""

    total: int
    executions: List[ExecutionResponse]


# ==================== Quality Schemas ====================


class QualityMetricCreate(BaseModel):
    """创建质量指标"""

    pack_id: str
    execution_id: str
    metric_name: str
    score: float
    details: Optional[Dict[str, Any]] = None


class QualityMetricResponse(BaseModel):
    """质量指标响应"""

    id: str
    pack_id: str
    execution_id: str
    metric_name: str
    score: float
    details: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Bulk Schemas ====================


class BulkErrorItem(BaseModel):
    index: int
    item_id: Optional[str] = None
    error: str


class BulkPackCreateRequest(BaseModel):
    packs: List[PackCreate]
    continue_on_error: bool = True


class BulkPackCreateResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    created: List[PackResponse]
    errors: List[BulkErrorItem]


class BulkPackGetRequest(BaseModel):
    pack_ids: List[str]
    include_inactive: bool = False


class BulkPackGetResponse(BaseModel):
    total_requested: int
    found: int
    missing: List[str]
    packs: List[PackResponse]


class BulkExecutionCreateRequest(BaseModel):
    items: List[Any]
    continue_on_error: bool = True


class BulkExecutionCreateResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    executions: List[ExecutionResponse]
    errors: List[BulkErrorItem]


# ==================== Execute Pack Schemas ====================


class ExecutePackRequest(BaseModel):
    """Pack 执行请求"""

    pack_id: str
    platform: str = "generic"
    user_input: str = ""
    enable_knowledge: bool = False
    context: Optional[Dict[str, Any]] = None


class StepResultSchema(BaseModel):
    """步骤执行结果"""

    id: str
    type: str
    status: str
    output: Optional[str] = None
    description: str = ""
    branches: List[Dict[str, Any]] = []


class ExecutePackResponse(BaseModel):
    """Pack 执行响应"""

    execution_id: str
    pack_id: str
    status: str
    steps: List[StepResultSchema]
    output: Optional[str] = None
    duration_ms: int
    knowledge_sources: List[str] = []
    platform: str = "generic"
    branch_logic_enabled: bool = False


# ==================== Studio Schemas ====================


class GenerateStudioRequest(BaseModel):
    """Studio 产物生成请求"""

    content: str
    artifacts: List[str]  # ['audio', 'video', 'slides']
    focus: str = ""
    notebook_id: Optional[str] = None


class ArtifactSchema(BaseModel):
    """产物信息"""

    type: str
    status: str
    size_mb: Optional[int] = None


class GenerateStudioResponse(BaseModel):
    """Studio 产物生成响应"""

    artifact_id: str
    status: str
    artifacts: List[ArtifactSchema]
    download_urls: Dict[str, str]
    focus: str
    content_length: int
    notebook_id: Optional[str] = None


# ==================== Pack Validate Schemas ====================


class StructureCheckSchema(BaseModel):
    """结构检查结果"""

    metadata: Dict[str, Any] = {}
    workflow: Dict[str, Any] = {}
    branch_logic: Dict[str, Any] = {}
    domain: Dict[str, Any] = {}


class PackValidateResponse(BaseModel):
    """Pack 验证响应"""

    pack_id: str
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    structure_check: StructureCheckSchema
    steps_count: int
    has_branches: bool


# ==================== Execution Status Schemas ====================


class ExecutionStatusResponse(BaseModel):
    """执行状态响应"""

    execution_id: str
    pack_id: str
    status: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
