"""
Prompt Pack Local Backend
FastAPI + SQLite 本地服务
"""

import os
import re
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.api import (
    consensus,
    executor,
    health,
    notebooklm,
    notebooklm_auth_monitor,
    notebooklm_sync,
    packs,
    soul,
)
from app.core.database import create_tables, optimize_database
from app.core.monitoring import get_performance_monitor
from app.core.rate_limit import get_ip_blacklist, get_rate_limiter

# 请求载荷大小限制（10MB）
MAX_REQUEST_BODY_SIZE = 10 * 1024 * 1024  # 10MB

# 速率限制配置
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_DEFAULT = int(os.getenv("RATE_LIMIT_DEFAULT", "100"))

_DYNAMIC_PATH_SEGMENT_RE = re.compile(r"/([A-Za-z0-9_-]{8,}|[0-9]+)(?=/|$)")

# Prometheus 指标
HTTP_REQUESTS_TOTAL = Counter(
    "prompt_pack_http_requests_total",
    "Total HTTP requests processed",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "prompt_pack_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
HTTP_EXCEPTIONS_TOTAL = Counter(
    "prompt_pack_http_exceptions_total",
    "Total HTTP request exceptions",
    ["method", "path", "exception"],
)


def normalize_metrics_path(path: str) -> str:
    """归一化动态 URL，避免指标标签基数失控。"""
    return _DYNAMIC_PATH_SEGMENT_RE.sub("/:id", path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 启动 Prompt Pack API...")
    create_tables()
    optimize_database()  # 优化数据库性能
    print("✅ 数据库初始化完成")

    if RATE_LIMIT_ENABLED:
        print(f"✅ 速率限制已启用 (默认: {RATE_LIMIT_DEFAULT} 请求/分钟)")

    yield

    # 关闭时
    print("🛑 关闭 Prompt Pack API...")
    # 清理资源
    get_rate_limiter().cleanup()
    get_ip_blacklist().cleanup_expired()
    print("✅ 资源清理完成")


app = FastAPI(
    title="Prompt Pack API",
    description="本地优先的 Prompt Pack 管理服务",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置 - 安全的来源白名单
ALLOWED_ORIGINS = [
    "http://localhost:*",
    "http://127.0.0.1:*",
]

# 从环境变量读取生产环境配置
prod_origins = os.getenv("ALLOWED_ORIGINS", "")
if prod_origins:
    ALLOWED_ORIGINS.extend([origin.strip() for origin in prod_origins.split(",")])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Client-Token",
        "Accept",
        "Origin",
    ],
)


# 请求载荷大小验证中间件
@app.middleware("http")
async def validate_request_size(request: Request, call_next):
    """验证请求载荷大小，防止 DoS 攻击"""
    # 检查 Content-Type，只对包含主体的请求进行验证
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            length = int(content_length)
            if length > MAX_REQUEST_BODY_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"请求体过大（最大 {MAX_REQUEST_BODY_SIZE // (1024*1024)}MB）",
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="无效的 Content-Length 头"
            )

    # 安全头配置
    response = await call_next(request)

    # 添加安全头
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers[
        "Content-Security-Policy"
    ] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

    return response


@app.middleware("http")
async def collect_prometheus_metrics(request: Request, call_next):
    """采集 Prometheus 指标并同步到本地性能监控。"""
    method = request.method
    path = normalize_metrics_path(request.url.path)
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        duration = time.perf_counter() - start_time
        HTTP_EXCEPTIONS_TOTAL.labels(
            method=method,
            path=path,
            exception=exc.__class__.__name__,
        ).inc()
        HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status="500").inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration)
        get_performance_monitor().record_call(
            endpoint=path,
            method=method,
            duration_ms=duration * 1000,
            status_code=500,
            error=str(exc),
        )
        raise

    duration = time.perf_counter() - start_time
    HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=str(status_code)).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration)
    get_performance_monitor().record_call(
        endpoint=path,
        method=method,
        duration_ms=duration * 1000,
        status_code=status_code,
    )
    return response


# 注册路由
app.include_router(packs.router, prefix="/api/packs", tags=["Packs"])
app.include_router(executor.router, prefix="/api", tags=["Executor"])
app.include_router(health.router, tags=["Health"])
app.include_router(consensus.router, tags=["Consensus"])
app.include_router(soul.router, tags=["Soul"])
app.include_router(notebooklm.router, prefix="/api/notebooklm", tags=["NotebookLM"])
app.include_router(
    notebooklm_auth_monitor.router, prefix="/api/notebooklm/auth", tags=["NotebookLM Auth Monitor"]
)
app.include_router(
    notebooklm_sync.router, prefix="/api/notebooklm/sync", tags=["NotebookLM Knowledge Sync"]
)


@app.get("/")
async def root():
    """根路径"""
    return {"name": "Prompt Pack API", "version": "1.0.0", "status": "running"}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus 指标导出端点。"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
