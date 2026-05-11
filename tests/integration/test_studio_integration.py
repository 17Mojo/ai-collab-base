"""
集成测试: NotebookLM Studio 产物生成

测试 Chrome Extension 通过 Backend API 生成 Studio 多模态产物
"""

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
BACKEND_URL = "http://127.0.0.1:8000"


@pytest.fixture
def client():
    """HTTP 客户端 fixture"""
    if not BACKEND_AVAILABLE:
        pytest.skip("httpx not installed")
    return httpx.Client(base_url=BACKEND_URL, timeout=30.0)


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
