"""
集成测试: NotebookLM Studio 产物生成

测试 Chrome Extension 通过 Backend API 生成 Studio 多模态产物
"""

import os
from pathlib import Path

import pytest

# 尝试导入 Backend API 客户端
try:
    import httpx

    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False

try:
    backend_path = Path(__file__).resolve().parents[2] / "local-backend"
    if str(backend_path) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(backend_path))

    SETTINGS_AVAILABLE = True
except ImportError:
    SETTINGS_AVAILABLE = False

NOTEBOOK_ID = "test-studio-integration-notebook"
# BASE_URL 可用环境变量覆盖：本机 8000 长期被外项目（ComfyUI）占用，
# 固定端口会让这组测试永远 skip 或打错服务（N12）。
# CI 与本地真跑时设 STUDIO_TEST_BASE_URL 指向本仓后端实际端口即可。
BACKEND_URL = os.environ.get("STUDIO_TEST_BASE_URL", "http://127.0.0.1:8000")

# Check if backend is reachable
import socket
import urllib.request

BACKEND_REACHABLE = False
try:
    # 既要能 TCP 连接，又要确认端点上跑的**是本仓后端**——不是端口上有个 HTTP 服务就算。
    from urllib.parse import urlparse

    _parsed = urlparse(BACKEND_URL)
    _host, _port = _parsed.hostname or "127.0.0.1", _parsed.port or 80
    s = socket.create_connection((_host, _port), timeout=0.5)
    s.close()
    # 身份判据取本仓真实的响应体标识：
    #   - 路径探 `/health`（本仓 health.router 挂在无 prefix 的 `app.include_router`，
    #     见 main.py:205；本仓**没有** `/api/health`）
    #   - 标识认 `"prompt-pack-api"`（health.py:24 的 `service` 字段）
    #
    # 此前这里探 `/api/health`（本仓没这条路由）且判据是
    # `"ai-collab" in body or r.status == 200`：`ai-collab` 永不匹配本仓响应，
    # `or r.status == 200` 又让**任何**占着 8000 的服务都算「后端可达」⇒
    # 8000 被别的项目占着时，4 条 Studio 测试会去打一个没有
    # `/api/notebooklm/*` 的应用，恒红 404 而不是跳过。
    req = urllib.request.Request(BACKEND_URL.rstrip("/") + "/health")
    with urllib.request.urlopen(req, timeout=1) as r:
        body = r.read().decode(errors="ignore")
        BACKEND_REACHABLE = "prompt-pack-api" in body
except Exception:
    BACKEND_REACHABLE = False


@pytest.fixture
def client():
    """HTTP 客户端 fixture"""
    if not BACKEND_AVAILABLE:
        pytest.skip("httpx not installed")
    # trust_env=False 必须显式关：httpx 默认吃 http_proxy/https_proxy 环境变量，
    # localhost 请求会被发成代理 absolute-form（`POST http%3A//...`），路由 404——
    # 表现为「同 client 首个请求 200、后续全 404」，实为客户端环境污染而非后端缺陷
    # （2026-11-09 N12 真跑实锤，uvicorn 访问日志可见畸形请求行）。
    return httpx.Client(base_url=BACKEND_URL, timeout=30.0, trust_env=False)


@pytest.fixture
def bridge_js_path():
    """Bridge JS 文件路径"""
    path = Path(__file__).resolve().parents[2] / "chrome-extension" / "src" / "background" / "notebooklm-packexecutor-bridge.js"
    if not path.exists():
        pytest.skip("Bridge JS file not found")
    return path


@pytest.fixture
def service_worker_path():
    """Service Worker JS 文件路径"""
    path = Path(__file__).resolve().parents[2] / "chrome-extension" / "src" / "background" / "service-worker.js"
    if not path.exists():
        pytest.skip("Service Worker JS file not found")
    return path


@pytest.fixture
def popup_html_path():
    """Popup HTML 文件路径"""
    path = Path(__file__).resolve().parents[2] / "chrome-extension" / "public" / "popup.html"
    if not path.exists():
        pytest.skip("Popup HTML file not found")
    return path


class TestStudioUI:
    """测试 Studio UI 组件存在"""

    def test_popup_has_studio_panel(self, popup_html_path):
        """Popup HTML 包含 Studio 面板"""
        content = popup_html_path.read_text()
        assert 'id="studio-panel"' in content
        assert 'id="studio-audio"' in content
        assert 'id="studio-video"' in content
        assert 'id="studio-slides"' in content
        assert 'id="generate-studio-btn"' in content
        assert 'id="studio-focus-text"' in content
        assert 'id="studio-status"' in content

    def test_popup_js_has_generate_function(self):
        """Popup JS 包含 generateStudioArtifacts 函数"""
        popup_js = Path(__file__).resolve().parents[2] / "chrome-extension" / "public" / "popup.js"
        content = popup_js.read_text()
        assert "GENERATE_STUDIO_ARTIFACTS" in content
        assert "generateStudioArtifacts" in content
        assert "getSelectedStudioTypes" in content
        assert "displayStudioStatus" in content


class TestServiceWorkerIntegration:
    """测试 Service Worker 消息处理"""

    def test_service_worker_handles_studio_message(self, service_worker_path):
        """Service Worker 处理 GENERATE_STUDIO_ARTIFACTS 消息"""
        content = service_worker_path.read_text()
        assert "GENERATE_STUDIO_ARTIFACTS" in content
        assert "NotebookLMPackExecutorBridge" in content
        assert "generateArtifact" in content

    def test_service_worker_imports_bridge(self, service_worker_path):
        """Service Worker 导入 Bridge 模块"""
        content = service_worker_path.read_text()
        assert "notebooklm-packexecutor-bridge.js" in content


class TestBridgeRealCall:
    """测试 Bridge 真实调用实现"""

    def test_bridge_has_wait_for_completion(self, bridge_js_path):
        """Bridge 包含 _waitForArtifactCompletion 方法"""
        content = bridge_js_path.read_text()
        assert "_waitForArtifactCompletion" in content

    def test_bridge_has_get_download_url(self, bridge_js_path):
        """Bridge 包含 _getDownloadUrl 方法"""
        content = bridge_js_path.read_text()
        assert "_getDownloadUrl" in content

    def test_bridge_generate_sends_focus_and_language(self, bridge_js_path):
        """Bridge generateArtifact 发送 focus 和 language 参数"""
        content = bridge_js_path.read_text()
        assert "options.focus" in content
        assert "options.language" in content

    def test_bridge_polls_status_endpoint(self, bridge_js_path):
        """Bridge 轮询 /status/ 端点"""
        content = bridge_js_path.read_text()
        assert "/api/notebooklm/status/" in content

    def test_bridge_has_download_url_endpoint(self, bridge_js_path):
        """Bridge 包含 download-url 端点"""
        content = bridge_js_path.read_text()
        assert "/api/notebooklm/download-url/" in content


@pytest.mark.skipif(
    not BACKEND_REACHABLE or not BACKEND_AVAILABLE,
    reason="Backend not running on 127.0.0.1:8000"
)
class TestStudioAPIEndpoints:
    """测试 Studio API 端点（需要 Backend 运行）"""

    @pytest.mark.skipif(not BACKEND_AVAILABLE, reason="httpx not installed")
    def test_studio_audio_generation(self, client):
        """测试 Audio 产物生成"""
        try:
            response = client.post(
                "/api/notebooklm/generate",
                json={"content_type": "audio", "notebook_id": NOTEBOOK_ID},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("success") or data.get("artifact_id")
        except httpx.ConnectError:
            pytest.skip("Backend not running")

    @pytest.mark.skipif(not BACKEND_AVAILABLE, reason="httpx not installed")
    def test_studio_video_generation(self, client):
        """测试 Video 产物生成"""
        try:
            response = client.post(
                "/api/notebooklm/generate",
                json={"content_type": "video", "notebook_id": NOTEBOOK_ID},
            )
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Backend not running")

    @pytest.mark.skipif(not BACKEND_AVAILABLE, reason="httpx not installed")
    def test_studio_slides_generation(self, client):
        """测试 Slides 产物生成"""
        try:
            response = client.post(
                "/api/notebooklm/generate",
                json={"content_type": "slides", "notebook_id": NOTEBOOK_ID},
            )
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Backend not running")

    @pytest.mark.skipif(not BACKEND_AVAILABLE, reason="httpx not installed")
    def test_studio_batch_generation(self, client):
        """测试批量生成 Audio + Video + Slides"""
        try:
            results = []
            for content_type in ["audio", "video", "slides"]:
                response = client.post(
                    "/api/notebooklm/generate",
                    json={"content_type": content_type, "notebook_id": NOTEBOOK_ID},
                )
                results.append(response.status_code)
            assert all(code == 200 for code in results)
        except httpx.ConnectError:
            pytest.skip("Backend not running")

    @pytest.mark.skipif(not BACKEND_AVAILABLE, reason="httpx not installed")
    def test_artifact_download(self, client):
        """测试产物下载"""
        try:
            # 先生成
            gen_response = client.post(
                "/api/notebooklm/generate",
                json={"content_type": "audio", "notebook_id": NOTEBOOK_ID},
            )
            if gen_response.status_code != 200:
                pytest.skip("Generate failed")

            artifact_id = gen_response.json().get("artifact_id")
            if not artifact_id:
                pytest.skip("No artifact_id returned")

            # 再下载
            dl_response = client.get(f"/api/notebooklm/download/{artifact_id}")
            assert dl_response.status_code in (200, 302)
        except httpx.ConnectError:
            pytest.skip("Backend not running")

    @pytest.mark.skipif(not BACKEND_AVAILABLE, reason="httpx not installed")
    def test_studio_invalid_content_type_rejected(self, client):
        """错误路径：非法 content_type 必须 400 拒绝（此前只验过 happy path）"""
        try:
            response = client.post(
                "/api/notebooklm/generate",
                json={"content_type": "not-a-real-type", "notebook_id": NOTEBOOK_ID},
            )
            assert response.status_code == 400
            body = response.json()
            # FastAPI HTTPException 的 detail 必须带回绝理由
            assert "Invalid content_type" in str(body.get("detail", ""))
        except httpx.ConnectError:
            pytest.skip("Backend not running")
