"""
端到端集成测试
测试 Chrome Extension + Local Backend 的完整流程
"""

import json
import os
import sys

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestPackWorkflow:
    """Pack 工作流端到端测试"""

    def test_load_pack_from_file(self):
        """测试从文件加载 Pack"""
        pack_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "packs",
            "examples",
            "xiaohongshu_beauty_review.json",
        )

        if not os.path.exists(pack_path):
            pytest.skip("示例 Pack 文件不存在")

        with open(pack_path, encoding="utf-8") as f:
            pack_data = json.load(f)

        assert "metadata" in pack_data
        assert "workflow" in pack_data
        assert pack_data["metadata"]["pack_id"] == "xiaohongshu-beauty-review"

    def test_pack_schema_validation(self):
        """测试 Pack Schema 验证"""
        from ai_collab.pack.schema_v2 import PromptPackV2

        pack_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "packs",
            "examples",
            "xiaohongshu_beauty_review.json",
        )

        if not os.path.exists(pack_path):
            pytest.skip("示例 Pack 文件不存在")

        with open(pack_path, encoding="utf-8") as f:
            pack_data = json.load(f)

        # 反序列化为对象
        pack = PromptPackV2.from_dict(pack_data)

        assert pack.metadata.pack_name == "小红书美妆测评文案生成包"
        assert len(pack.workflow.steps) == 6  # 6 个工作流步骤

    def test_workflow_steps_integrity(self):
        """测试工作流步骤完整性"""
        from ai_collab.pack.schema_v2 import PromptPackV2

        pack_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "packs",
            "examples",
            "xiaohongshu_beauty_review.json",
        )

        if not os.path.exists(pack_path):
            pytest.skip("示例 Pack 文件不存在")

        with open(pack_path, encoding="utf-8") as f:
            pack_data = json.load(f)

        pack = PromptPackV2.from_dict(pack_data)

        # 验证步骤 ID 唯一性
        step_ids = [step.id for step in pack.workflow.steps]
        assert len(step_ids) == len(set(step_ids))

        # 验证步骤类型
        for step in pack.workflow.steps:
            assert step.type.value in [
                "local",
                "analysis",
                "generation",
                "validation",
                "fusion",
                "tracking",
            ]


class TestChromeExtensionFiles:
    """Chrome Extension 文件完整性测试（新架构: chrome-extension/）

    守护 chrome-extension/ 目录下 ESM + service-worker + platform adapters 的真实结构。
    """

    @staticmethod
    def _ext_root():
        return os.path.join(os.path.dirname(__file__), "..", "..", "chrome-extension")

    def test_manifest_exists(self):
        """测试 chrome-extension/manifest.json 存在"""
        manifest_path = os.path.join(self._ext_root(), "manifest.json")
        assert os.path.exists(manifest_path), "chrome-extension/manifest.json 不存在"

    def test_manifest_valid(self):
        """测试 manifest.json 满足 Manifest V3 关键字段"""
        manifest_path = os.path.join(self._ext_root(), "manifest.json")
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["manifest_version"] == 3
        assert "name" in manifest
        assert "version" in manifest
        assert "permissions" in manifest
        # 新架构 permissions
        for required_perm in ("storage", "activeTab", "scripting"):
            assert required_perm in manifest["permissions"], f"缺少权限: {required_perm}"
        # background 是 service_worker (Manifest V3)
        assert manifest["background"]["service_worker"] == "src/background/service-worker.js"
        # content_scripts 单文件注入
        assert len(manifest["content_scripts"]) == 1
        assert manifest["content_scripts"][0]["js"] == ["src/content/content-script.js"]

    def test_content_script_exists(self):
        """测试 src/content/content-script.js 存在（ESM 入口）"""
        path = os.path.join(self._ext_root(), "src", "content", "content-script.js")
        assert os.path.exists(path), "content-script.js 不存在"

    def test_dom_observer_exists(self):
        """测试 src/utils/dom-observer.js 存在（替代旧的 error-recovery.js）"""
        path = os.path.join(self._ext_root(), "src", "utils", "dom-observer.js")
        assert os.path.exists(path), "dom-observer.js 不存在"

    def test_dom_observer_api_methods(self):
        """测试 DOMObserver 暴露完整的观察 API"""
        path = os.path.join(self._ext_root(), "src", "utils", "dom-observer.js")
        with open(path, encoding="utf-8") as f:
            content = f.read()

        for method in ("observeMessages", "observeTypingStatus", "observeInput"):
            assert method in content, f"缺少 {method} 公开方法"
        assert "MutationObserver" in content, "缺少 MutationObserver 基础设施"

    def test_service_worker_exists(self):
        """测试 src/background/service-worker.js 存在（替代 enhanced-message-handler.js）"""
        path = os.path.join(self._ext_root(), "src", "background", "service-worker.js")
        assert os.path.exists(path), "service-worker.js 不存在"

    def test_service_worker_handles_pack_execution(self):
        """测试 Service Worker 处理 Pack 执行相关消息"""
        path = os.path.join(self._ext_root(), "src", "background", "service-worker.js")
        with open(path, encoding="utf-8") as f:
            content = f.read()

        for msg_type in (
            "EXECUTE_PACK",
            "GET_ADAPTER",
            "GET_PACK_STATUS",
            "GET_ALL_PACKS",
            "GENERATE_STUDIO_ARTIFACTS",
        ):
            assert msg_type in content, f"缺少消息类型处理: {msg_type}"
        assert "packExecutor" in content, "缺少 packExecutor 引用"
        assert ".execute(message.packId" in content, "缺少 packExecutor.execute 调用"
        assert "new PackExecutor" in content, "缺少 PackExecutor 构造"

    def test_pack_storage_manager_exists(self):
        """测试 src/background/pack-storage-manager.js 存在"""
        path = os.path.join(self._ext_root(), "src", "background", "pack-storage-manager.js")
        assert os.path.exists(path), "pack-storage-manager.js 不存在"

    def test_pack_storage_manager_api(self):
        """测试 PackStorageManager 关键 API（AES-GCM 已弃用，换为新缓存契约）"""
        path = os.path.join(self._ext_root(), "src", "background", "pack-storage-manager.js")
        with open(path, encoding="utf-8") as f:
            content = f.read()

        for api in ("PackStorageManager", "getStorageInfo", "mergeWithDefaults",
                    "refreshCache", "importPacks", "exportPacks"):
            assert api in content, f"缺少 API: {api}"

    def test_default_packs_registry(self):
        """测试 DEFAULT_PACKS 至少注册 knowledge-query 与 article-writing"""
        path = os.path.join(self._ext_root(), "src", "background", "pack-storage-manager.js")
        with open(path, encoding="utf-8") as f:
            content = f.read()

        assert "knowledge-query" in content, "缺少默认包 knowledge-query"
        assert "article-writing" in content, "缺少默认包 article-writing"

    def test_content_script_initialization_order(self):
        """测试 Content Script 注入配置正确（run_at + 单 content-script.js）"""
        manifest_path = os.path.join(self._ext_root(), "manifest.json")
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        content_scripts = manifest.get("content_scripts", [])
        assert len(content_scripts) == 1, "应只有一个 content_script 注入配置"
        cs = content_scripts[0]
        assert "src/content/content-script.js" in cs["js"]
        assert cs["run_at"] == "document_idle"
        # 必须覆盖至少 5 个 AI 平台域名
        assert len(cs["matches"]) >= 5, "matches 应覆盖至少 5 个平台域名"

    def test_platform_adapter_registry(self):
        """测试 Service Worker 注册 10+ 平台适配器（新架构: adapters 字典 + getAdapter）"""
        path = os.path.join(self._ext_root(), "src", "background", "service-worker.js")
        with open(path, encoding="utf-8") as f:
            content = f.read()

        assert "const adapters = {" in content, "缺少 adapters 注册表"
        assert "function getAdapter" in content, "缺少 getAdapter(url) 函数"
        # 守护实际注册的 10 个平台
        for platform in (
            "claude.ai", "chat.openai.com", "gemini.google.com",
            "qianwen.aliyun.com", "chatglm.cn", "kimi.moonshot.cn",
            "yiyan.baidu.com", "yuanbao.tencent.com", "longcat.ai",
            "chat.deepseek.com",
        ):
            assert platform in content, f"缺少平台适配器: {platform}"

    def test_content_script_error_handling(self):
        """测试 Content Script 错误处理路径（handleInjectText/handleClickSend）"""
        path = os.path.join(self._ext_root(), "src", "content", "content-script.js")
        with open(path, encoding="utf-8") as f:
            content = f.read()

        for fn in ("handleInjectText", "handleClickSend", "handleWaitForResponse", "getPageState"):
            assert fn in content, f"缺少处理函数: {fn}"
        # 新架构错误抛出
        assert "No adapter available" in content, "缺少适配器不可用错误抛出"
        assert "Chat input not found" in content, "缺少输入框未找到错误抛出"

    def test_background_service_worker_registered(self):
        """测试 Background Service Worker 以 module 类型注册"""
        path = os.path.join(self._ext_root(), "src", "background", "service-worker.js")
        assert os.path.exists(path)
        manifest_path = os.path.join(self._ext_root(), "manifest.json")
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["background"].get("type") == "module", "background.type 应为 module"

    def test_background_storage_cache_keys(self):
        """测试 Background 存储 cache 键约定（替代 STORAGE_SCHEMA_VERSION）"""
        path = os.path.join(self._ext_root(), "src", "background", "pack-storage-manager.js")
        with open(path, encoding="utf-8") as f:
            content = f.read()

        assert "cacheKey" in content, "缺少 cacheKey 配置"
        assert "cacheTimestampKey" in content, "缺少 cacheTimestampKey 配置"
        assert "cacheTTL" in content, "缺少 cacheTTL TTL 配置"
        assert "5 * 60 * 1000" in content, "缺少 5 分钟 TTL 默认值"

    def test_settings_handler_api(self):
        """测试设置处理器（替代 options/options.js + getSettings/updateSettings）"""
        path = os.path.join(self._ext_root(), "src", "background", "settings-handler.js")
        assert os.path.exists(path), "settings-handler.js 不存在"
        with open(path, encoding="utf-8") as f:
            content = f.read()

        for token in (
            "DEFAULT_SETTINGS",
            "platforms",
            "execution",
            "timeout",
            "retries",
            "retryDelay",
            "handleSettingsMessage",
            "SETTINGS_UPDATED",
            "GET_SETTINGS",
        ):
            assert token in content, f"缺少设置 API 元素: {token}"

    def test_options_use_background_settings_api(self):
        """测试 Service Worker 暴露 settings 消息总线（替代前端 options.js 直调）"""
        path = os.path.join(self._ext_root(), "src", "background", "service-worker.js")
        with open(path, encoding="utf-8") as f:
            content = f.read()

        assert "SETTINGS_UPDATED" in content, "缺少 SETTINGS_UPDATED 消息处理"
        sw_path = os.path.join(self._ext_root(), "src", "background", "settings-handler.js")
        assert os.path.exists(sw_path), "缺少 settings-handler.js 模块"
        with open(sw_path, encoding="utf-8") as f:
            handler_content = f.read()
        assert "handleSettingsMessage" in handler_content, "缺少 handleSettingsMessage 入口"
        assert "GET_SETTINGS" in handler_content, "settings-handler 缺少 GET_SETTINGS 消息类型"


class TestLocalBackendFiles:
    """Local Backend 文件完整性测试"""

    def test_main_app_exists(self):
        """测试主应用文件存在"""
        main_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "local-backend", "app", "main.py"
        )

        assert os.path.exists(main_path), "main.py 不存在"

    def test_docker_config_exists(self):
        """测试 Docker 配置存在"""
        dockerfile_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "local-backend", "Dockerfile"
        )

        compose_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "local-backend", "docker-compose.yml"
        )

        assert os.path.exists(dockerfile_path), "Dockerfile 不存在"
        assert os.path.exists(compose_path), "docker-compose.yml 不存在"


class TestProjectStructure:
    """项目结构测试（新架构: chrome-extension/）"""

    def test_required_directories(self):
        """测试必要目录存在"""
        base_path = os.path.join(os.path.dirname(__file__), "..", "..")

        required_dirs = [
            "chrome-extension/src/content",
            "chrome-extension/src/background",
            "chrome-extension/src/platforms",
            "chrome-extension/src/utils",
            "chrome-extension/public",
            "ai_collab/pack",
            "local-backend/app",
            "local-backend/app/api",
            "packs/examples",
        ]

        for dir_path in required_dirs:
            full_path = os.path.join(base_path, dir_path)
            assert os.path.exists(full_path), f"目录不存在: {dir_path}"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
