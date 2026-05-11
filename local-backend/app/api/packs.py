"""
Pack API 路由
"""

import os
from typing import Optional, Set

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    BulkErrorItem,
    BulkExecutionCreateRequest,
    BulkExecutionCreateResponse,
    BulkPackCreateRequest,
    BulkPackCreateResponse,
    BulkPackGetRequest,
    BulkPackGetResponse,
    ExecutionCreate,
    ExecutionListResponse,
    ExecutionResponse,
    PackCreate,
    PackListResponse,
    PackResponse,
    PackUpdate,
    QualityMetricCreate,
    QualityMetricResponse,
)
from app.core.cache import get_cache_manager
from app.core.client_tokens import ExpiredTokenError, InvalidTokenError, verify_client_token
from app.core.database import get_db
from app.models.pack import ExecutionHistoryModel, PackModel, QualityMetricModel

router = APIRouter()
PACK_CACHE_TTL_SECONDS = int(os.getenv("PACK_CACHE_TTL_SECONDS", "120"))
METADATA_CACHE_TTL_SECONDS = int(os.getenv("PACK_METADATA_CACHE_TTL_SECONDS", "300"))
METRICS_CACHE_TTL_SECONDS = int(os.getenv("PACK_METRICS_CACHE_TTL_SECONDS", "120"))


def _cache_key_list(skip: int, limit: int, category: Optional[str], search: Optional[str]) -> str:
    return f"packs:list:{skip}:{limit}:{category or ''}:{search or ''}"


def _cache_key_pack(pack_id: str) -> str:
    return f"packs:item:{pack_id}"


def _cache_key_metadata(pack_id: str) -> str:
    return f"packs:metadata:{pack_id}"


def _cache_key_metrics_stats(pack_id: str) -> str:
    return f"packs:metrics:stats:{pack_id}"


def _invalidate_pack_cache(pack_id: Optional[str] = None):
    cache = get_cache_manager()
    cache.delete_prefix("packs:list:")
    if pack_id:
        cache.delete_prefix(_cache_key_pack(pack_id))
        cache.delete_prefix(_cache_key_metadata(pack_id))
        cache.delete_prefix(_cache_key_metrics_stats(pack_id))


# ==================== Pack CRUD ====================


@router.get("/", response_model=PackListResponse)
async def list_packs(
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取 Pack 列表"""
    cache = get_cache_manager()
    cache_key = _cache_key_list(skip=skip, limit=limit, category=category, search=search)
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return PackListResponse.model_validate(cached_payload)

    query = db.query(PackModel).filter(PackModel.is_active.is_(True))

    if category:
        query = query.filter(PackModel.category == category)

    if search:
        query = query.filter(
            PackModel.pack_name.contains(search) | PackModel.description.contains(search)
        )

    total = query.count()
    packs = query.offset(skip).limit(limit).all()

    response = PackListResponse(total=total, packs=[PackResponse.model_validate(p) for p in packs])
    cache.set(cache_key, response.model_dump(mode="json"), ttl=PACK_CACHE_TTL_SECONDS)
    return response


@router.post("/bulk/create", response_model=BulkPackCreateResponse)
async def bulk_create_packs(payload: BulkPackCreateRequest, db: Session = Depends(get_db)):
    """批量创建 Pack（支持部分失败）"""
    created: list[PackResponse] = []
    errors: list[BulkErrorItem] = []
    seen_pack_ids: Set[str] = set()

    for idx, pack in enumerate(payload.packs):
        pack_id = pack.metadata.pack_id

        if pack_id in seen_pack_ids:
            errors.append(
                BulkErrorItem(
                    index=idx,
                    item_id=pack_id,
                    error=f"duplicate pack_id in request: {pack_id}",
                )
            )
            if not payload.continue_on_error:
                break
            continue
        seen_pack_ids.add(pack_id)

        existing = db.query(PackModel).filter(PackModel.pack_id == pack_id).first()
        if existing:
            errors.append(
                BulkErrorItem(
                    index=idx,
                    item_id=pack_id,
                    error=f"Pack with ID {pack_id} already exists",
                )
            )
            if not payload.continue_on_error:
                break
            continue

        db_pack = PackModel(
            pack_id=pack.metadata.pack_id,
            pack_name=pack.metadata.pack_name,
            version=pack.metadata.version,
            type=pack.metadata.type.value,
            description=pack.metadata.description,
            designer=pack.metadata.designer,
            category=pack.metadata.category,
            tags=pack.metadata.tags,
            language=pack.metadata.language,
            pack_data=pack.model_dump(),
        )

        db.add(db_pack)
        db.commit()
        db.refresh(db_pack)
        created.append(PackResponse.model_validate(db_pack))

    if created:
        _invalidate_pack_cache()

    return BulkPackCreateResponse(
        total=len(payload.packs),
        succeeded=len(created),
        failed=len(errors),
        created=created,
        errors=errors,
    )


@router.post("/bulk/get", response_model=BulkPackGetResponse)
async def bulk_get_packs(payload: BulkPackGetRequest, db: Session = Depends(get_db)):
    """批量查询 Pack"""
    if not payload.pack_ids:
        return BulkPackGetResponse(total_requested=0, found=0, missing=[], packs=[])

    query = db.query(PackModel).filter(PackModel.pack_id.in_(payload.pack_ids))
    if not payload.include_inactive:
        query = query.filter(PackModel.is_active.is_(True))

    found_rows = query.all()
    found_map = {pack.pack_id: pack for pack in found_rows}

    packs: list[PackResponse] = []
    missing: list[str] = []
    for pack_id in payload.pack_ids:
        row = found_map.get(pack_id)
        if row is None:
            missing.append(pack_id)
        else:
            packs.append(PackResponse.model_validate(row))

    return BulkPackGetResponse(
        total_requested=len(payload.pack_ids),
        found=len(packs),
        missing=missing,
        packs=packs,
    )


@router.post("/", response_model=PackResponse, status_code=status.HTTP_201_CREATED)
async def create_pack(pack: PackCreate, db: Session = Depends(get_db)):
    """创建 Pack"""
    # 检查是否已存在
    existing = db.query(PackModel).filter(PackModel.pack_id == pack.metadata.pack_id).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pack with ID {pack.metadata.pack_id} already exists",
        )

    # 创建 Pack 数据
    pack_data = pack.model_dump()

    # 创建数据库记录
    db_pack = PackModel(
        pack_id=pack.metadata.pack_id,
        pack_name=pack.metadata.pack_name,
        version=pack.metadata.version,
        type=pack.metadata.type.value,
        description=pack.metadata.description,
        designer=pack.metadata.designer,
        category=pack.metadata.category,
        tags=pack.metadata.tags,
        language=pack.metadata.language,
        pack_data=pack_data,
    )

    db.add(db_pack)
    db.commit()
    db.refresh(db_pack)
    _invalidate_pack_cache(db_pack.pack_id)

    return PackResponse.model_validate(db_pack)


@router.get("/{pack_id}", response_model=PackResponse)
async def get_pack(pack_id: str, db: Session = Depends(get_db)):
    """获取单个 Pack（完整数据 - 双端分发模式的服务端访问）"""
    cache = get_cache_manager()
    cache_key = _cache_key_pack(pack_id)
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return PackResponse.model_validate(cached_payload)

    pack = (
        db.query(PackModel)
        .filter(PackModel.pack_id == pack_id, PackModel.is_active.is_(True))
        .first()
    )

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Pack {pack_id} not found"
        )

    response = PackResponse.model_validate(pack)
    cache.set(cache_key, response.model_dump(mode="json"), ttl=PACK_CACHE_TTL_SECONDS)
    return response


@router.get("/{pack_id}/metadata")
async def get_pack_metadata(pack_id: str, db: Session = Depends(get_db)):
    """
    获取 Pack 元数据（双端分发模式 - 客户端访问）

    双端分发说明:
    - 客户端端（Chrome 扩展）只获取元数据,降低传输成本
    - 服务端端需要时才请求完整 Pack（包含 system_prompt 等敏感信息）
    - 元数据包含: 基础信息、输入输出结构、工作流定义
    - 不包含: system_prompt、验证规则、优化配置等核心逻辑
    """
    cache = get_cache_manager()
    cache_key = _cache_key_metadata(pack_id)
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return cached_payload

    pack = (
        db.query(PackModel)
        .filter(PackModel.pack_id == pack_id, PackModel.is_active.is_(True))
        .first()
    )

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Pack {pack_id} not found"
        )

    pack_data = pack.pack_data or {}

    # 构建元数据响应（仅包含客户端需要的非敏感信息）
    metadata_only = {
        "pack_id": pack.pack_id,
        "pack_name": pack.pack_name,
        "version": pack.version,
        "type": pack.type,
        "description": pack.description,
        "designer": pack.designer,
        "category": pack.category,
        "tags": pack.tags,
        "language": pack.language,
        "execution_count": pack.execution_count,
        "avg_quality_score": getattr(pack, "avg_quality_score", None),
        "estimated_efficiency_gain": pack_data.get("metadata", {}).get(
            "estimated_efficiency_gain", "60%"
        ),
        # 基础领域配置
        "domain": pack_data.get("domain", {}),
        # 工作流定义（客户端需要知道如何执行）
        "workflow": pack_data.get("workflow", {}),
        # 输入输出模式（供客户端构建 UI）
        "input_schema": _extract_input_schema(pack_data),
        "output_schema": _extract_output_schema(pack_data),
        # 版本和更新时间
        "created_at": pack_data.get("metadata", {}).get("created_at"),
        "updated_at": pack_data.get("metadata", {}).get("updated_at"),
        # 质量指标定义（客户端可显示但不需要实现）
        "quality_metrics_definition": {
            name: {
                "description": metric.get("description"),
                "min_threshold": metric.get("min_threshold"),
            }
            for name, metric in pack_data.get("quality_metrics", {}).get("metrics", {}).items()
        },
        # 生成参数（客户端可配置）
        "generation_params": {
            "output_versions": pack_data.get("generation_params", {}).get("output_versions", 1),
            "temperature": pack_data.get("generation_params", {}).get("temperature", 0.7),
            "output_format": pack_data.get("generation_params", {}).get(
                "output_format", "markdown"
            ),
        },
    }

    cache.set(cache_key, metadata_only, ttl=METADATA_CACHE_TTL_SECONDS)
    return metadata_only


@router.post("/{pack_id}/full")
async def get_pack_full(
    pack_id: str,
    client_token: Optional[str] = Header(None, alias="X-Client-Token"),
    db: Session = Depends(get_db),
):
    """
    获取完整 Pack（双端分发模式 - 服务端访问）

    需要认证,返回包含敏感信息的完整 Pack

    安全说明:
    - 此端点仅供可信的服务端组件访问
    - 包含: system_prompt、quality_validation_rules 等核心逻辑
    - 客户端不应直接访问此端点
    - 需要通过 X-Client-Token header 提供有效的客户端令牌
    """
    # 验证客户端令牌
    if not client_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing client token. Please provide X-Client-Token header.",
        )

    try:
        is_valid = verify_client_token(client_token)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid client token"
            )
    except ExpiredTokenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Client token has expired"
        )
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid client token")

    pack = (
        db.query(PackModel)
        .filter(PackModel.pack_id == pack_id, PackModel.is_active.is_(True))
        .first()
    )

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Pack {pack_id} not found"
        )

    # 返回完整的 Pack 数据
    full_pack = {
        "metadata": pack_data.get("metadata", {}) if (pack_data := pack.pack_data) else {},
        "domain": pack_data.get("domain", {}),
        "workflow": pack_data.get("workflow", {}),
        "quality_metrics": pack_data.get("quality_metrics", {}),
        "example_library": pack_data.get("example_library", {}),
        "generation_params": pack_data.get("generation_params", {}),
        "optimization": pack_data.get("optimization", {}),
        "performance_tracking": pack_data.get("performance_tracking", {}),
        "collaboration": pack_data.get("collaboration", {}),
        # 敏感信息 - 仅在此端点返回
        "system_prompt": pack_data.get("system_prompt", ""),
        "quality_validation_rules": pack_data.get("quality_validation_rules", ""),
    }

    return full_pack


@router.put("/{pack_id}", response_model=PackResponse)
async def update_pack(pack_id: str, pack_update: PackUpdate, db: Session = Depends(get_db)):
    """更新 Pack"""
    pack = (
        db.query(PackModel)
        .filter(PackModel.pack_id == pack_id, PackModel.is_active.is_(True))
        .first()
    )

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Pack {pack_id} not found"
        )

    # 更新字段
    update_data = pack_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if value is not None:
            setattr(pack, field, value)

    # 更新 pack_data
    current_data = pack.pack_data or {}
    current_data.update(update_data)
    pack.pack_data = current_data

    db.commit()
    db.refresh(pack)
    _invalidate_pack_cache(pack_id)

    return PackResponse.model_validate(pack)


@router.delete("/{pack_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pack(pack_id: str, db: Session = Depends(get_db)):
    """删除 Pack（软删除）"""
    pack = (
        db.query(PackModel)
        .filter(PackModel.pack_id == pack_id, PackModel.is_active.is_(True))
        .first()
    )

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Pack {pack_id} not found"
        )

    pack.is_active = False
    db.commit()
    _invalidate_pack_cache(pack_id)

    return None


# ==================== Execution History ====================


@router.get("/{pack_id}/executions", response_model=ExecutionListResponse)
async def list_executions(
    pack_id: str, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)
):
    """获取 Pack 执行历史"""
    query = db.query(ExecutionHistoryModel).filter(ExecutionHistoryModel.pack_id == pack_id)

    total = query.count()
    executions = (
        query.order_by(ExecutionHistoryModel.started_at.desc()).offset(skip).limit(limit).all()
    )

    return ExecutionListResponse(
        total=total, executions=[ExecutionResponse.model_validate(e) for e in executions]
    )


@router.post(
    "/{pack_id}/executions", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED
)
async def create_execution(pack_id: str, execution: ExecutionCreate, db: Session = Depends(get_db)):
    """创建执行记录"""
    # 检查 Pack 是否存在
    pack = (
        db.query(PackModel)
        .filter(PackModel.pack_id == pack_id, PackModel.is_active.is_(True))
        .first()
    )

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Pack {pack_id} not found"
        )

    # 创建执行记录
    db_execution = ExecutionHistoryModel(
        pack_id=pack_id, status="pending", input_data=execution.input_data
    )

    db.add(db_execution)

    # 更新 Pack 执行计数
    pack.execution_count += 1

    db.commit()
    db.refresh(db_execution)
    _invalidate_pack_cache(pack_id)

    return ExecutionResponse.model_validate(db_execution)


@router.post("/{pack_id}/executions/bulk-create", response_model=BulkExecutionCreateResponse)
async def bulk_create_executions(
    pack_id: str, payload: BulkExecutionCreateRequest, db: Session = Depends(get_db)
):
    """批量创建执行记录（支持部分失败）"""
    pack = (
        db.query(PackModel)
        .filter(PackModel.pack_id == pack_id, PackModel.is_active.is_(True))
        .first()
    )

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Pack {pack_id} not found"
        )

    executions: list[ExecutionResponse] = []
    errors: list[BulkErrorItem] = []

    for idx, item in enumerate(payload.items):
        if not isinstance(item, dict):
            errors.append(
                BulkErrorItem(
                    index=idx,
                    item_id=None,
                    error="execution item must be an object",
                )
            )
            if not payload.continue_on_error:
                break
            continue

        db_execution = ExecutionHistoryModel(
            pack_id=pack_id,
            status="pending",
            input_data=item,
        )
        db.add(db_execution)
        db.commit()
        db.refresh(db_execution)
        executions.append(ExecutionResponse.model_validate(db_execution))

    if executions:
        pack.execution_count += len(executions)
        db.commit()
        _invalidate_pack_cache(pack_id)

    return BulkExecutionCreateResponse(
        total=len(payload.items),
        succeeded=len(executions),
        failed=len(errors),
        executions=executions,
        errors=errors,
    )


# ==================== Quality Metrics ====================


@router.post(
    "/{pack_id}/metrics", response_model=QualityMetricResponse, status_code=status.HTTP_201_CREATED
)
async def create_metric(pack_id: str, metric: QualityMetricCreate, db: Session = Depends(get_db)):
    """记录质量指标"""
    db_metric = QualityMetricModel(
        pack_id=pack_id,
        execution_id=metric.execution_id,
        metric_name=metric.metric_name,
        score=metric.score,
        details=metric.details,
    )

    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    _invalidate_pack_cache(pack_id)

    return QualityMetricResponse.model_validate(db_metric)


@router.get("/{pack_id}/metrics/stats")
async def get_metrics_stats(pack_id: str, db: Session = Depends(get_db)):
    """获取 Pack 质量指标统计"""
    cache = get_cache_manager()
    cache_key = _cache_key_metrics_stats(pack_id)
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return cached_payload

    metrics = db.query(QualityMetricModel).filter(QualityMetricModel.pack_id == pack_id).all()

    if not metrics:
        empty_payload = {"pack_id": pack_id, "metrics": {}}
        cache.set(cache_key, empty_payload, ttl=METRICS_CACHE_TTL_SECONDS)
        return empty_payload

    # 按指标名称分组统计
    stats = {}
    for m in metrics:
        if m.metric_name not in stats:
            stats[m.metric_name] = {"count": 0, "total_score": 0, "avg_score": 0}
        stats[m.metric_name]["count"] += 1
        stats[m.metric_name]["total_score"] += m.score

    for name in stats:
        count = stats[name]["count"]
        total_score = stats[name]["total_score"]
        # 除零保护：只有在有数据的情况下才计算平均值
        stats[name]["avg_score"] = total_score / count if count > 0 else 0

    payload = {"pack_id": pack_id, "metrics": stats}
    cache.set(cache_key, payload, ttl=METRICS_CACHE_TTL_SECONDS)
    return payload


# ==================== Pack Validation ====================


@router.get("/{pack_id}/validate")
async def validate_pack(pack_id: str, db: Session = Depends(get_db)):
    """
    验证 Pack 结构完整性

    Returns:
        valid: 是否有效
        errors: 错误列表
        warnings: 警告列表
        structure_check: 结构检查详情
    """
    pack = (
        db.query(PackModel)
        .filter(PackModel.pack_id == pack_id, PackModel.is_active.is_(True))
        .first()
    )

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Pack {pack_id} not found"
        )

    pack_data = pack.pack_data or {}
    errors: list[str] = []
    warnings: list[str] = []
    structure_check: dict = {}

    # 1. 元数据检查
    metadata = pack_data.get("metadata", {})
    required_meta = ["pack_id", "pack_name", "version", "type", "description"]
    structure_check["metadata"] = {
        "present": list(metadata.keys()),
        "missing": [f for f in required_meta if f not in metadata],
    }
    if structure_check["metadata"]["missing"]:
        errors.append(f"元数据缺失: {structure_check['metadata']['missing']}")

    # 2. Workflow 检查
    workflow = pack_data.get("workflow", {})
    steps = workflow.get("steps", [])
    structure_check["workflow"] = {
        "steps_count": len(steps),
        "has_parallel": workflow.get("allow_parallel", False),
        "max_parallel": workflow.get("max_parallel_steps", 1),
    }
    if not steps:
        errors.append("Workflow 无步骤定义")
    else:
        # 检查步骤 ID 唯一性
        step_ids = [s.get("id") for s in steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("Workflow 步骤 ID 不唯一")
        # 检查分支目标步骤存在性
        for step in steps:
            branches = step.get("branches", [])
            for branch in branches:
                target_step = branch.get("target_step")
                if target_step and target_step not in step_ids and target_step != "end":
                    errors.append(f"分支目标步骤 '{target_step}' 不存在于 workflow")

    # 3. 分支逻辑检查
    has_branches = any(s.get("branches") for s in steps)
    structure_check["branch_logic"] = {
        "enabled": has_branches,
        "steps_with_branches": sum(1 for s in steps if s.get("branches")),
    }
    if has_branches:
        warnings.append("分支逻辑已启用，请确保 maxIterations 防护设置")

    # 4. Domain 检查
    domain = pack_data.get("domain", {})
    structure_check["domain"] = {
        "primary_domain": domain.get("primary_domain"),
        "target_platforms": domain.get("target_platforms", []),
    }

    valid = len(errors) == 0

    return {
        "pack_id": pack_id,
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "structure_check": structure_check,
        "steps_count": len(steps),
        "has_branches": has_branches,
    }


# ==================== Helper Functions ====================


def _extract_input_schema(pack_data: dict) -> dict:
    """
    从 Pack 数据中提取输入模式

    Args:
        pack_data: Pack 数据字典

    Returns:
        输入模式字典
    """
    input_schema = {}

    workflow = pack_data.get("workflow", {})
    steps = workflow.get("steps", [])

    for step in steps:
        input_fields = step.get("input_fields", [])
        for field in input_fields:
            if field not in input_schema:
                input_schema[field] = {
                    "type": "string",  # 默认为字符串类型
                    "required": True,
                    "description": f"{field} input",
                }

    return input_schema


def _extract_output_schema(pack_data: dict) -> dict:
    """
    从 Pack 数据中提取输出模式

    Args:
        pack_data: Pack 数据字典

    Returns:
        输出模式字典
    """
    output_schema = {}

    workflow = pack_data.get("workflow", {})
    steps = workflow.get("steps", [])

    if steps:
        last_step = steps[-1]
        output_field = last_step.get("output_field", "output")

        output_schema = {
            "primary_field": output_field,
            "type": "string",
            "description": f"Primary output field: {output_field}",
        }

    return output_schema
